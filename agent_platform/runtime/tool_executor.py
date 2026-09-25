"""Governed MCP tool executor with retry policy."""

from __future__ import annotations

import asyncio
import random
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from agent_platform.mcp.client import McpClient
from agent_platform.mcp.protocol import (
    BACKEND_UNAVAILABLE,
    CONTRACT_INPUT_INVALID,
    CONTRACT_OUTPUT_INVALID,
    TOOL_TIMEOUT,
)
from agent_platform.mcp.registry import REQUEST_REROUTE, TOOL_REGISTRY, get_policy
from agent_platform.models.execution import ExecutionContext
from agent_platform.models.policy import RetryPolicy, ToolPolicy
from agent_platform.models.tools import ToolResult
from agent_platform.policy.rules import scopes_satisfied


@dataclass
class ToolCallRecord:
    """One tool invocation recorded during an agent run."""

    tool_name: str
    arguments: dict[str, Any]
    result: ToolResult[Any]


@dataclass
class ToolExecutionOutcome:
    """Result of one governed tool execution."""

    result: ToolResult[Any]
    records: list[ToolCallRecord] = field(default_factory=list)


Clock = Callable[[], datetime]


def _status_code_from_details(
    details: dict[str, str | int | float | bool | None],
) -> int:
    """Coerce a platform error status_code detail to an integer."""
    raw = details.get("status_code", 0)
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    return 0


class GovernedToolExecutor:
    """Execute MCP tools with scope filtering, reroute arg injection, and retries."""

    def __init__(
        self,
        mcp_client: McpClient,
        *,
        clock: Clock | None = None,
    ) -> None:
        """Store the MCP client and optional clock for deadline checks."""
        self._mcp_client = mcp_client
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._pending_idempotency_keys: dict[str, str] = {}
        self._run_started_at: dict[str, datetime] = {}

    def allowed_tool_names(self, context: ExecutionContext) -> list[str]:
        """Return tool names the agent may invoke for the given context."""
        granted = context.delegation.scopes
        allowed: list[str] = []
        for name, registered in TOOL_REGISTRY.items():
            if scopes_satisfied(registered.policy.required_scopes, granted):
                allowed.append(name)
        return sorted(allowed)

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> ToolExecutionOutcome:
        """Call one tool through MCP with retry and argument enrichment."""
        prepared = self._prepare_arguments(tool_name, arguments, context)
        policy = get_policy(tool_name)
        records: list[ToolCallRecord] = []
        result = await self._call_with_retry(tool_name, prepared, context, policy)
        records.append(ToolCallRecord(tool_name=tool_name, arguments=prepared, result=result))
        return ToolExecutionOutcome(result=result, records=records)

    def _prepare_arguments(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Fill platform-controlled fields before the MCP call."""
        if tool_name != REQUEST_REROUTE:
            return dict(arguments)

        if "approval_id" in arguments and "idempotency_key" in arguments:
            return dict(arguments)

        shipment_id = str(arguments["shipment_id"])
        route_id = str(arguments["route_id"])
        expected_cost = float(arguments["expected_additional_cost_eur"])
        action_key = f"{context.run_id}:{shipment_id}:{route_id}:{expected_cost:g}"
        idempotency_key = self._pending_idempotency_keys.setdefault(
            action_key,
            f"idem-{uuid.uuid4().hex[:16]}",
        )
        approval_id = f"apr-{uuid.uuid4().hex[:12]}"
        return {
            "shipment_id": shipment_id,
            "route_id": route_id,
            "expected_additional_cost_eur": expected_cost,
            "idempotency_key": idempotency_key,
            "approval_id": approval_id,
        }

    async def _call_with_retry(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
        policy: ToolPolicy,
    ) -> ToolResult[Any]:
        """Invoke MCP with bounded retries according to tool policy."""
        retry = policy.retry
        max_attempts = retry.max_attempts
        last_result: ToolResult[Any] | None = None

        for attempt in range(1, max_attempts + 1):
            if self._deadline_exceeded(context):
                return self._timeout_result(tool_name, attempt)

            result = await self._mcp_client.call(tool_name, arguments, context=context)
            result = result.model_copy(
                update={
                    "metadata": result.metadata.model_copy(update={"attempt": attempt}),
                },
            )
            last_result = result

            if not self._should_retry(result, policy, attempt, max_attempts):
                return result

            delay = self._backoff_seconds(retry, attempt)
            if self._deadline_within(context, delay):
                await asyncio.sleep(delay)
            else:
                return result

        if last_result is not None:
            return last_result
        return self._timeout_result(tool_name, max_attempts)

    def _should_retry(
        self,
        result: ToolResult[Any],
        policy: ToolPolicy,
        attempt: int,
        max_attempts: int,
    ) -> bool:
        """Return True when another attempt is allowed."""
        if attempt >= max_attempts:
            return False
        if result.status in {"success", "approval_required", "denied"}:
            return False
        if result.error is None:
            return False

        retry = policy.retry
        error = result.error
        if error.code == TOOL_TIMEOUT:
            return policy.idempotent and retry.retry_on_timeout
        if error.code == BACKEND_UNAVAILABLE and error.category == "transport":
            status_code = _status_code_from_details(error.details)
            if status_code == 429:
                return True
            if status_code >= 500 or status_code == 0:
                return retry.retry_on_5xx or retry.retry_on_transport_error
            return retry.retry_on_transport_error
        if error.code == CONTRACT_INPUT_INVALID:
            return False
        if error.code == CONTRACT_OUTPUT_INVALID or error.category == "contract":
            return False
        if error.category in {"policy", "approval", "authorization", "validation"}:
            return False
        if error.retryable and retry.retry_on_transport_error:
            return True
        return False

    def _backoff_seconds(self, retry: RetryPolicy, attempt: int) -> float:
        """Return delay before the next retry with jitter."""
        base = retry.base_delay_seconds * (2 ** (attempt - 1))
        capped = min(base, retry.max_delay_seconds)
        jitter = random.uniform(0, capped * 0.1)  # nosec B311 - retry backoff jitter, not crypto
        return float(capped + jitter)

    def _run_started(self, context: ExecutionContext) -> datetime:
        """Return the cached start time for one run."""
        started = self._run_started_at.get(context.run_id)
        if started is None:
            started = self._clock()
            self._run_started_at[context.run_id] = started
        return started

    def _deadline_exceeded(self, context: ExecutionContext) -> bool:
        """Return True when the run deadline has elapsed."""
        elapsed = (self._clock() - self._run_started(context)).total_seconds()
        return elapsed >= context.budget.deadline_seconds

    def _deadline_within(self, context: ExecutionContext, delay: float) -> bool:
        """Return True when sleeping delay still fits inside the run deadline."""
        elapsed = (self._clock() - self._run_started(context)).total_seconds()
        return elapsed + delay < context.budget.deadline_seconds

    @staticmethod
    def _timeout_result(tool_name: str, attempt: int) -> ToolResult[Any]:
        """Build a timeout ToolResult when the run deadline is exceeded."""
        from agent_platform.mcp.protocol import build_error, build_failed_result

        return build_failed_result(
            tool_name,
            0,
            build_error(
                TOOL_TIMEOUT,
                "timeout",
                "tool call timed out",
                retryable=False,
            ),
            attempt=attempt,
        )

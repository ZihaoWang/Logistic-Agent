"""Enforcing policy slot backed by PolicyEngine."""

from typing import Any

from pydantic import BaseModel

from agent_platform.mcp.protocol import (
    POLICY_CONTEXT_MISSING,
    RUN_BUDGET_EXCEEDED,
    build_approval_required_result,
    build_denied_result,
    build_error,
)
from agent_platform.mcp.registry import TOOL_REGISTRY
from agent_platform.models.errors import ErrorCategory
from agent_platform.models.execution import ExecutionContext
from agent_platform.models.tools import ToolResult
from agent_platform.policy.engine import PolicyEngine


class EnforcingPolicySlot:
    """Policy slot that delegates to PolicyEngine before backend calls."""

    def __init__(self, engine: PolicyEngine) -> None:
        """Store the policy engine used for evaluation."""
        self._engine = engine

    async def check(
        self,
        tool_name: str,
        arguments: BaseModel,
        context: ExecutionContext | None = None,
    ) -> ToolResult[Any] | None:
        """Evaluate policy and return a short-circuit ToolResult when needed."""
        if context is None:
            return build_denied_result(
                tool_name,
                0,
                build_error(
                    POLICY_CONTEXT_MISSING,
                    "policy",
                    "execution context is required for governed tool calls",
                    retryable=False,
                ),
            )

        registered = TOOL_REGISTRY.get(tool_name)
        if registered is None:
            return build_denied_result(
                tool_name,
                0,
                build_error(
                    POLICY_CONTEXT_MISSING,
                    "internal",
                    f"unknown tool: {tool_name}",
                    retryable=False,
                ),
            )

        decision = await self._engine.evaluate_tool_call(registered, arguments, context)
        if decision.decision == "allow":
            return None
        if decision.decision == "require_approval":
            if decision.approval is None:
                msg = "require_approval decision missing approval payload"
                raise RuntimeError(msg)
            return build_approval_required_result(tool_name, 0, decision.approval)
        details: dict[str, str | int | float | bool | None] = {}
        if decision.missing_scopes:
            details["missing_scopes"] = ",".join(decision.missing_scopes)
        return build_denied_result(
            tool_name,
            0,
            build_error(
                decision.reason_code,
                _category_for_reason(decision.reason_code),
                decision.message,
                retryable=False,
                details=details,
            ),
        )

    async def record_success(
        self,
        tool_name: str,
        arguments: BaseModel,
        context: ExecutionContext | None = None,
    ) -> None:
        """Consume matching approval after a successful side-effect call."""
        if context is None:
            return
        registered = TOOL_REGISTRY.get(tool_name)
        if registered is None or not registered.policy.requires_approval:
            return
        await self._engine.consume_approval_after_success(tool_name, arguments, context)


def _category_for_reason(reason_code: str) -> ErrorCategory:
    """Map a policy reason code to a PlatformError category."""
    if reason_code == RUN_BUDGET_EXCEEDED:
        return "budget"
    if reason_code.startswith("APPROVAL_"):
        return "approval"
    if reason_code in {POLICY_CONTEXT_MISSING}:
        return "policy"
    return "policy"

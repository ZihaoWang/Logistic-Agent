"""Tool execution pipeline for the MCP gateway."""

import time
from typing import Any

from pydantic import ValidationError

from agent_platform.mcp.protocol import (
    BACKEND_CONFLICT,
    BACKEND_NOT_FOUND,
    BACKEND_UNAVAILABLE,
    CONTRACT_INPUT_INVALID,
    CONTRACT_OUTPUT_INVALID,
    INTERNAL,
    build_error,
    build_failed_result,
    build_success_result,
)
from agent_platform.models.execution import ExecutionContext
from agent_platform.models.tools import ToolResult
from mcp_server.backend.base import BackendCallError
from mcp_server.policy_slot import BasePolicySlot
from mcp_server.tools.base import BaseTool


class ToolPipeline:
    """Validate, optionally policy-check, call backend, and envelope results."""

    def __init__(self, tools: dict[str, BaseTool], policy_slot: BasePolicySlot) -> None:
        """Store tool handlers and the policy slot.

        Parameters:
            tools: Map of tool name to BaseTool implementation.
            policy_slot: Policy hook invoked after input validation.
        """
        self._tools = tools
        self._policy_slot = policy_slot

    async def run(
        self,
        tool_name: str,
        raw_arguments: dict[str, Any],
        context: ExecutionContext | None = None,
    ) -> ToolResult[Any]:
        """Execute one tool call through the gateway pipeline.

        Parameters:
            tool_name: Registered MCP tool name.
            raw_arguments: Raw argument dict from the MCP protocol edge.
            context: Optional execution context for governed policy checks.

        Returns:
            ToolResult envelope for success or failure.
        """
        started = time.perf_counter()
        tool = self._tools.get(tool_name)
        if tool is None:
            latency_ms = self._latency_ms(started)
            return build_failed_result(
                tool_name,
                latency_ms,
                build_error(
                    INTERNAL,
                    "internal",
                    f"unknown tool: {tool_name}",
                    retryable=False,
                ),
            )

        try:
            validated_input = tool.input_model.model_validate(raw_arguments)
        except ValidationError as exc:
            latency_ms = self._latency_ms(started)
            return build_failed_result(
                tool_name,
                latency_ms,
                build_error(
                    CONTRACT_INPUT_INVALID,
                    "validation",
                    "tool arguments failed input validation",
                    retryable=False,
                    details={"error_count": len(exc.errors())},
                ),
            )

        policy_result = await self._policy_slot.check(
            tool_name,
            validated_input,
            context,
        )
        if policy_result is not None:
            latency_ms = self._latency_ms(started)
            return self._with_latency(policy_result, tool_name, latency_ms)

        try:
            adapted_body = await tool.fetch(validated_input)
        except BackendCallError as exc:
            latency_ms = self._latency_ms(started)
            return self._map_backend_error(tool_name, latency_ms, exc)
        except Exception as exc:  # noqa: BLE001
            latency_ms = self._latency_ms(started)
            return build_failed_result(
                tool_name,
                latency_ms,
                build_error(
                    INTERNAL,
                    "internal",
                    f"unexpected tool failure: {exc}",
                    retryable=False,
                ),
            )

        try:
            output = tool.output_model.model_validate(adapted_body)
        except ValidationError as exc:
            latency_ms = self._latency_ms(started)
            return build_failed_result(
                tool_name,
                latency_ms,
                build_error(
                    CONTRACT_OUTPUT_INVALID,
                    "contract",
                    "backend response failed output validation",
                    retryable=False,
                    details={"error_count": len(exc.errors())},
                ),
            )

        await self._policy_slot.record_success(tool_name, validated_input, context)

        latency_ms = self._latency_ms(started)
        return build_success_result(tool_name, latency_ms, output)

    @staticmethod
    def _latency_ms(started: float) -> int:
        """Return elapsed milliseconds since started."""
        return int((time.perf_counter() - started) * 1000)

    @staticmethod
    def _with_latency(
        result: ToolResult[Any],
        tool_name: str,
        latency_ms: int,
    ) -> ToolResult[Any]:
        """Replace metadata latency on a policy short-circuit result."""
        metadata = result.metadata.model_copy(
            update={"tool_name": tool_name, "latency_ms": latency_ms},
        )
        return result.model_copy(update={"metadata": metadata})

    @staticmethod
    def _map_backend_error(
        tool_name: str,
        latency_ms: int,
        exc: BackendCallError,
    ) -> ToolResult[Any]:
        """Map backend HTTP or transport failures to ToolResult errors."""
        if exc.status_code == 404:
            return build_failed_result(
                tool_name,
                latency_ms,
                build_error(
                    BACKEND_NOT_FOUND,
                    "backend",
                    "requested resource was not found",
                    retryable=False,
                    details={"status_code": exc.status_code},
                ),
            )
        if exc.status_code == 409:
            return build_failed_result(
                tool_name,
                latency_ms,
                build_error(
                    BACKEND_CONFLICT,
                    "backend",
                    "backend rejected the request due to a conflict",
                    retryable=False,
                    details={"status_code": exc.status_code},
                ),
            )
        if exc.status_code == 0 or exc.status_code >= 500:
            return build_failed_result(
                tool_name,
                latency_ms,
                build_error(
                    BACKEND_UNAVAILABLE,
                    "transport",
                    "backend is unavailable",
                    retryable=True,
                    details={"status_code": exc.status_code},
                ),
            )
        return build_failed_result(
            tool_name,
            latency_ms,
            build_error(
                INTERNAL,
                "backend",
                "backend returned an unexpected error",
                retryable=False,
                details={"status_code": exc.status_code},
            ),
        )

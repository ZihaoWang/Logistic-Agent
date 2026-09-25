"""Error codes and ToolResult envelope builders."""

from typing import Any

from agent_platform.models.approval import ApprovalRequest
from agent_platform.models.errors import ErrorCategory, PlatformError
from agent_platform.models.tools import ToolMetadata, ToolResult
from contracts.versions import SCHEMA_VERSION

CONTRACT_INPUT_INVALID = "CONTRACT_INPUT_INVALID"
CONTRACT_OUTPUT_INVALID = "CONTRACT_OUTPUT_INVALID"
BACKEND_NOT_FOUND = "BACKEND_NOT_FOUND"
BACKEND_CONFLICT = "BACKEND_CONFLICT"
BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
TOOL_TIMEOUT = "TOOL_TIMEOUT"
INTERNAL = "INTERNAL"

POLICY_CONTEXT_MISSING = "POLICY_CONTEXT_MISSING"
POLICY_MISSING_SCOPE = "POLICY_MISSING_SCOPE"
POLICY_ALLOWED = "POLICY_ALLOWED"
DELEGATION_EXPIRED = "DELEGATION_EXPIRED"
RUN_NOT_FOUND = "RUN_NOT_FOUND"
RUN_BUDGET_EXCEEDED = "RUN_BUDGET_EXCEEDED"
REROUTE_COST_LIMIT = "REROUTE_COST_LIMIT"
SIDE_EFFECT_APPROVAL_REQUIRED = "SIDE_EFFECT_APPROVAL_REQUIRED"
APPROVAL_RUN_MISMATCH = "APPROVAL_RUN_MISMATCH"
APPROVAL_ARGUMENTS_MISMATCH = "APPROVAL_ARGUMENTS_MISMATCH"
APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
APPROVAL_ALREADY_CONSUMED = "APPROVAL_ALREADY_CONSUMED"
APPROVAL_REJECTED = "APPROVAL_REJECTED"


def build_metadata(tool_name: str, latency_ms: int, attempt: int = 1) -> ToolMetadata:
    """Build standard ToolMetadata for a tool call.

    Parameters:
        tool_name: MCP tool name.
        latency_ms: End-to-end latency in milliseconds.
        attempt: Attempt number; defaults to 1.

    Returns:
        ToolMetadata with schema version and trace id unset.
    """
    return ToolMetadata(
        tool_name=tool_name,
        schema_version=SCHEMA_VERSION,
        attempt=attempt,
        latency_ms=latency_ms,
        trace_id=None,
    )


def build_error(
    code: str,
    category: ErrorCategory,
    message: str,
    *,
    retryable: bool,
    details: dict[str, str | int | float | bool | None] | None = None,
) -> PlatformError:
    """Build a PlatformError with optional details.

    Parameters:
        code: Stable machine-readable error code.
        category: Error family.
        message: Short human-readable message.
        retryable: Whether a retry could succeed.
        details: Optional structured facts.

    Returns:
        A PlatformError instance.
    """
    return PlatformError(
        code=code,
        category=category,
        message=message,
        retryable=retryable,
        details=details or {},
    )


def build_failed_result(
    tool_name: str,
    latency_ms: int,
    error: PlatformError,
    *,
    attempt: int = 1,
) -> ToolResult[Any]:
    """Build a failed ToolResult envelope.

    Parameters:
        tool_name: MCP tool name.
        latency_ms: End-to-end latency in milliseconds.
        error: Platform error describing the failure.
        attempt: Attempt number; defaults to 1.

    Returns:
        ToolResult with status failed and no data payload.
    """
    return ToolResult[Any](
        status="failed",
        data=None,
        error=error,
        approval=None,
        metadata=build_metadata(tool_name, latency_ms, attempt),
    )


def build_denied_result(
    tool_name: str,
    latency_ms: int,
    error: PlatformError,
    *,
    attempt: int = 1,
) -> ToolResult[Any]:
    """Build a denied ToolResult envelope.

    Parameters:
        tool_name: MCP tool name.
        latency_ms: End-to-end latency in milliseconds.
        error: Platform error describing the denial.
        attempt: Attempt number; defaults to 1.

    Returns:
        ToolResult with status denied.
    """
    return ToolResult[Any](
        status="denied",
        data=None,
        error=error,
        approval=None,
        metadata=build_metadata(tool_name, latency_ms, attempt),
    )


def build_approval_required_result(
    tool_name: str,
    latency_ms: int,
    approval: ApprovalRequest,
    *,
    attempt: int = 1,
) -> ToolResult[Any]:
    """Build an approval_required ToolResult envelope.

    Parameters:
        tool_name: MCP tool name.
        latency_ms: End-to-end latency in milliseconds.
        approval: Pending approval request for the human reviewer.
        attempt: Attempt number; defaults to 1.

    Returns:
        ToolResult with status approval_required.
    """
    return ToolResult[Any](
        status="approval_required",
        data=None,
        error=None,
        approval=approval,
        metadata=build_metadata(tool_name, latency_ms, attempt),
    )


def build_success_result(
    tool_name: str,
    latency_ms: int,
    data: object,
    *,
    attempt: int = 1,
) -> ToolResult[Any]:
    """Build a successful ToolResult envelope.

    Parameters:
        tool_name: MCP tool name.
        latency_ms: End-to-end latency in milliseconds.
        data: Typed output payload.
        attempt: Attempt number; defaults to 1.

    Returns:
        ToolResult with status success.
    """
    return ToolResult[Any](
        status="success",
        data=data,
        error=None,
        approval=None,
        metadata=build_metadata(tool_name, latency_ms, attempt),
    )

"""Tool result envelope shared by every MCP tool."""

from typing import Generic, Literal, Self, TypeVar

from pydantic import BaseModel, Field, model_validator

from agent_platform.models.approval import ApprovalRequest
from agent_platform.models.errors import PlatformError

T = TypeVar("T")

ToolResultStatus = Literal["success", "failed", "approval_required", "denied"]


class ToolMetadata(BaseModel):
    """Metadata attached to every ToolResult.

    Usage:
        Filled by the MCP gateway pipeline for every tool call.

    Fields:
        tool_name: Required MCP tool name.
        schema_version: Required contract schema version.
        attempt: Required attempt number for this call.
        latency_ms: Required end-to-end latency in milliseconds.
        trace_id: Optional distributed trace id.
    """

    tool_name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. MCP tool name.",
    )
    schema_version: str = Field(
        ...,
        min_length=1,
        max_length=16,
        description="Required. Contract schema version.",
    )
    attempt: int = Field(
        ...,
        ge=1,
        le=10,
        description="Required. Attempt number for this call.",
    )
    latency_ms: int = Field(
        ...,
        ge=0,
        description="Required. End-to-end latency in milliseconds.",
    )
    trace_id: str | None = Field(
        default=None,
        max_length=128,
        description="Optional. Distributed trace id.",
    )


class ToolResult(BaseModel, Generic[T]):
    """Common envelope for every MCP tool response.

    Usage:
        Returned by the MCP gateway for success and failure paths.

    Fields:
        status: Required result status.
        data: Optional typed payload on success.
        error: Optional platform error on failure.
        approval: Optional approval request when approval is required.
        metadata: Required call metadata.
    """

    status: ToolResultStatus = Field(
        ...,
        description="Required. Result status.",
    )
    data: T | None = Field(
        default=None,
        description="Optional. Typed payload on success.",
    )
    error: PlatformError | None = Field(
        default=None,
        description="Optional. Platform error on failure.",
    )
    approval: ApprovalRequest | None = Field(
        default=None,
        description="Optional. Approval request when approval is required.",
    )
    metadata: ToolMetadata = Field(
        ...,
        description="Required. Call metadata.",
    )

    @model_validator(mode="after")
    def _validate_status_payload(self) -> Self:
        """Ensure success and failure payloads match the status."""
        if self.status == "success":
            if self.data is None:
                msg = "success ToolResult requires data"
                raise ValueError(msg)
            if self.error is not None:
                msg = "success ToolResult must not include error"
                raise ValueError(msg)
        if self.status == "failed":
            if self.error is None:
                msg = "failed ToolResult requires error"
                raise ValueError(msg)
            if self.data is not None:
                msg = "failed ToolResult must not include data"
                raise ValueError(msg)
        if self.status == "approval_required" and self.approval is None:
            msg = "approval_required ToolResult requires approval"
            raise ValueError(msg)
        return self

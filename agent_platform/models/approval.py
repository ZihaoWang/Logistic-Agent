"""Approval request model for side-effect tools."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ApprovalStatus = Literal["pending", "approved", "rejected", "expired", "consumed"]


class ApprovalRequest(BaseModel):
    """Human approval request bound to a specific tool call.

    Usage:
        Returned inside ToolResult when status is approval_required.
        Phase 3 creates and validates these records.

    Fields:
        approval_id: Required unique approval identifier.
        run_id: Required agent run that requested the action.
        tool_name: Required MCP tool name.
        tool_arguments_hash: Required hash of the exact tool arguments.
        summary: Required short summary for a human reviewer.
        requested_by_agent: Required agent id that requested approval.
        actor_id: Required user or actor id on whose behalf the action runs.
        created_at: Required creation timestamp in UTC.
        expires_at: Required expiry timestamp in UTC.
        status: Required current approval status.
    """

    approval_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Unique approval identifier.",
    )
    run_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Agent run that requested the action.",
    )
    tool_name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. MCP tool name.",
    )
    tool_arguments_hash: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Required. Hash of the exact tool arguments.",
    )
    summary: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Required. Short summary for a human reviewer.",
    )
    requested_by_agent: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Agent id that requested approval.",
    )
    actor_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. User or actor id for the action.",
    )
    created_at: datetime = Field(
        ...,
        description="Required. Creation timestamp in UTC.",
    )
    expires_at: datetime = Field(
        ...,
        description="Required. Expiry timestamp in UTC.",
    )
    status: ApprovalStatus = Field(
        ...,
        description="Required. Current approval status.",
    )
    decided_at: datetime | None = Field(
        default=None,
        description="Optional. Timestamp when a human decided.",
    )
    decided_by: str | None = Field(
        default=None,
        max_length=64,
        description="Optional. Actor who approved or rejected.",
    )
    consumed_at: datetime | None = Field(
        default=None,
        description="Optional. Timestamp when the approval was consumed.",
    )


class ApprovalDecision(BaseModel):
    """Human decision on a pending approval request.

    Usage:
        Passed to ApprovalStore.decide to transition approval status.

    Fields:
        approval_id: Required approval identifier being decided.
        decision: Required approved or rejected outcome.
        decided_by: Required actor who made the decision.
        decided_at: Required decision timestamp in UTC.
        comment: Optional reviewer comment.
    """

    approval_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Approval identifier being decided.",
    )
    decision: Literal["approved", "rejected"] = Field(
        ...,
        description="Required. Approved or rejected outcome.",
    )
    decided_by: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Actor who made the decision.",
    )
    decided_at: datetime = Field(
        ...,
        description="Required. Decision timestamp in UTC.",
    )
    comment: str | None = Field(
        default=None,
        max_length=512,
        description="Optional. Reviewer comment.",
    )

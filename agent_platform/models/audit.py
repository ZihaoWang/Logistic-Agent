"""Audit event model for governance and observability."""

from datetime import datetime

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """Immutable audit record for a governance or tool event.

    Usage:
        Appended to AuditStore on policy decisions and approval transitions.

    Fields:
        event_id: Required unique event identifier.
        run_id: Required agent run identifier.
        event_type: Required event type string.
        actor_id: Optional human actor identifier.
        agent_id: Optional agent identifier.
        tool_name: Optional MCP tool name.
        decision: Optional policy or approval decision code.
        outcome: Optional execution outcome.
        timestamp: Required event timestamp in UTC.
        trace_id: Optional distributed trace identifier.
        metadata: Optional structured event metadata.
    """

    event_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Unique event identifier.",
    )
    run_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Agent run identifier.",
    )
    event_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Event type string.",
    )
    actor_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional. Human actor identifier.",
    )
    agent_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional. Agent identifier.",
    )
    tool_name: str | None = Field(
        default=None,
        max_length=64,
        description="Optional. MCP tool name.",
    )
    decision: str | None = Field(
        default=None,
        max_length=64,
        description="Optional. Policy or approval decision code.",
    )
    outcome: str | None = Field(
        default=None,
        max_length=64,
        description="Optional. Execution outcome.",
    )
    timestamp: datetime = Field(
        ...,
        description="Required. Event timestamp in UTC.",
    )
    trace_id: str | None = Field(
        default=None,
        max_length=128,
        description="Optional. Distributed trace identifier.",
    )
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="Optional. Structured event metadata.",
    )

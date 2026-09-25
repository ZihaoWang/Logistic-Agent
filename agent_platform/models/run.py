"""Run state and usage counter models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RunStatus = Literal[
    "created",
    "running",
    "waiting_for_approval",
    "completed",
    "failed",
    "cancelled",
]


class UsageCounters(BaseModel):
    """Accumulated resource usage for one agent run.

    Usage:
        Updated by the policy engine on each allowed tool call.

    Fields:
        model_calls: Optional model call count; defaults to 0.
        tool_calls: Optional tool call count; defaults to 0.
        input_tokens: Optional input token count; defaults to 0.
        output_tokens: Optional output token count; defaults to 0.
        estimated_cost_usd: Optional estimated cost in USD; defaults to 0.0.
    """

    model_calls: int = Field(
        default=0,
        ge=0,
        description="Optional. Model call count; defaults to 0.",
    )
    tool_calls: int = Field(
        default=0,
        ge=0,
        description="Optional. Tool call count; defaults to 0.",
    )
    input_tokens: int = Field(
        default=0,
        ge=0,
        description="Optional. Input token count; defaults to 0.",
    )
    output_tokens: int = Field(
        default=0,
        ge=0,
        description="Optional. Output token count; defaults to 0.",
    )
    estimated_cost_usd: float = Field(
        default=0.0,
        ge=0,
        description="Optional. Estimated cost in USD; defaults to 0.0.",
    )


class RunState(BaseModel):
    """Persisted state for one agent run.

    Usage:
        Stored in RunStore and updated during execution.

    Fields:
        run_id: Required agent run identifier.
        thread_id: Required conversation thread identifier.
        status: Required current run status.
        created_at: Required creation timestamp in UTC.
        updated_at: Required last update timestamp in UTC.
        usage: Optional usage counters; defaults to UsageCounters().
        pending_approval_id: Optional approval awaiting human decision.
        last_error_code: Optional last platform error code.
    """

    run_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Agent run identifier.",
    )
    thread_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Conversation thread identifier.",
    )
    status: RunStatus = Field(
        ...,
        description="Required. Current run status.",
    )
    created_at: datetime = Field(
        ...,
        description="Required. Creation timestamp in UTC.",
    )
    updated_at: datetime = Field(
        ...,
        description="Required. Last update timestamp in UTC.",
    )
    usage: UsageCounters = Field(
        default_factory=UsageCounters,
        description="Optional. Usage counters; defaults to UsageCounters().",
    )
    pending_approval_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional. Approval awaiting human decision.",
    )
    last_error_code: str | None = Field(
        default=None,
        max_length=64,
        description="Optional. Last platform error code.",
    )
    model_name: str | None = Field(
        default=None,
        max_length=64,
        description="Optional. Model used for this run.",
    )
    last_message: str | None = Field(
        default=None,
        max_length=4096,
        description="Optional. Last user message for this run.",
    )
    pending_tool_call: dict[str, Any] | None = Field(
        default=None,
        description="Optional. Tool name and arguments awaiting approval replay.",
    )

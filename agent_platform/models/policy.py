"""Tool policy models attached to the MCP registry."""

from typing import Literal

from pydantic import BaseModel, Field

ToolRisk = Literal["low", "medium", "high"]
PolicyDecisionKind = Literal["allow", "deny", "require_approval"]


class RetryPolicy(BaseModel):
    """Retry settings for a tool policy.

    Usage:
        Stored on ToolPolicy for Phase 3 enforcement. Not used in Phase 2.

    Fields:
        max_attempts: Optional maximum retry attempts; defaults to 3.
        base_delay_seconds: Optional base delay between retries; defaults to 1.0.
        max_delay_seconds: Optional maximum delay cap; defaults to 4.0.
        retry_on_timeout: Optional retry on timeout; defaults to true.
        retry_on_transport_error: Optional retry on transport errors; defaults to true.
        retry_on_5xx: Optional retry on HTTP 5xx; defaults to true.
        retry_on_4xx: Optional retry on HTTP 4xx; defaults to false.
    """

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Optional. Maximum retry attempts; defaults to 3.",
    )
    base_delay_seconds: float = Field(
        default=1.0,
        ge=0,
        description="Optional. Base delay between retries in seconds; defaults to 1.0.",
    )
    max_delay_seconds: float = Field(
        default=4.0,
        ge=0,
        description="Optional. Maximum delay cap in seconds; defaults to 4.0.",
    )
    retry_on_timeout: bool = Field(
        default=True,
        description="Optional. Retry on timeout; defaults to true.",
    )
    retry_on_transport_error: bool = Field(
        default=True,
        description="Optional. Retry on transport errors; defaults to true.",
    )
    retry_on_5xx: bool = Field(
        default=True,
        description="Optional. Retry on HTTP 5xx; defaults to true.",
    )
    retry_on_4xx: bool = Field(
        default=False,
        description="Optional. Retry on HTTP 4xx; defaults to false.",
    )


class ToolPolicy(BaseModel):
    """Policy metadata attached to a registered MCP tool.

    Usage:
        Stored in the tool registry. Phase 3 reads and enforces these values.

    Fields:
        name: Required tool name this policy belongs to.
        risk: Required risk level for the tool.
        required_scopes: Required scopes needed to call the tool.
        side_effect: Optional side-effect flag; defaults to false.
        requires_approval: Optional approval requirement; defaults to false.
        idempotent: Optional idempotency flag; defaults to true.
        timeout_seconds: Optional execution timeout; defaults to 10.0.
        retry: Optional retry policy; defaults to RetryPolicy().
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Tool name this policy belongs to.",
    )
    risk: ToolRisk = Field(
        ...,
        description="Required. Risk level for the tool.",
    )
    required_scopes: set[str] = Field(
        ...,
        description="Required. Scopes needed to call the tool.",
    )
    side_effect: bool = Field(
        default=False,
        description="Optional. Whether the tool changes external state; defaults to false.",
    )
    requires_approval: bool = Field(
        default=False,
        description="Optional. Whether human approval is required; defaults to false.",
    )
    idempotent: bool = Field(
        default=True,
        description="Optional. Whether repeated calls are safe; defaults to true.",
    )
    timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=60,
        description="Optional. Execution timeout in seconds; defaults to 10.0.",
    )
    retry: RetryPolicy = Field(
        default_factory=RetryPolicy,
        description="Optional. Retry policy; defaults to RetryPolicy().",
    )


class PolicyDecision(BaseModel):
    """Result of a policy engine evaluation for one tool call.

    Usage:
        Returned by PolicyEngine.evaluate_tool_call before backend execution.

    Fields:
        decision: Required allow, deny, or require_approval outcome.
        reason_code: Required stable machine-readable reason code.
        message: Required short human-readable explanation.
        matched_rules: Optional rule names that matched; defaults to empty list.
        missing_scopes: Optional scopes the caller lacks; defaults to empty list.
        approval: Optional pending approval when decision is require_approval.
    """

    decision: PolicyDecisionKind = Field(
        ...,
        description="Required. Allow, deny, or require_approval outcome.",
    )
    reason_code: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Stable machine-readable reason code.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Required. Short human-readable explanation.",
    )
    matched_rules: list[str] = Field(
        default_factory=list,
        description="Optional. Rule names that matched; defaults to empty list.",
    )
    missing_scopes: list[str] = Field(
        default_factory=list,
        description="Optional. Scopes the caller lacks; defaults to empty list.",
    )
    approval: "ApprovalRequest | None" = Field(
        default=None,
        description="Optional. Pending approval when decision is require_approval.",
    )


from agent_platform.models.approval import ApprovalRequest  # noqa: E402

PolicyDecision.model_rebuild()

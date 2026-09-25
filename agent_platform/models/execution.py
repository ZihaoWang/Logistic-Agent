"""Execution context and budget models for agent runs."""

from pydantic import BaseModel, Field

from agent_platform.models.identity import DelegationContext


class AgentBudget(BaseModel):
    """Per-run resource limits enforced before tool execution.

    Usage:
        Stored on ExecutionContext and checked by the policy engine.

    Fields:
        max_model_calls: Optional model call cap; defaults to 4.
        max_tool_calls: Optional tool call cap; defaults to 10.
        max_input_tokens: Optional input token cap; defaults to 20000.
        max_output_tokens: Optional output token cap; defaults to 4000.
        max_estimated_cost_usd: Optional cost cap in USD; defaults to 0.50.
        deadline_seconds: Optional run deadline in seconds; defaults to 45.
    """

    max_model_calls: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Optional. Model call cap; defaults to 4.",
    )
    max_tool_calls: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Optional. Tool call cap; defaults to 10.",
    )
    max_input_tokens: int = Field(
        default=20_000,
        ge=100,
        description="Optional. Input token cap; defaults to 20000.",
    )
    max_output_tokens: int = Field(
        default=4_000,
        ge=100,
        description="Optional. Output token cap; defaults to 4000.",
    )
    max_estimated_cost_usd: float = Field(
        default=0.50,
        gt=0,
        description="Optional. Cost cap in USD; defaults to 0.50.",
    )
    deadline_seconds: int = Field(
        default=45,
        ge=1,
        le=300,
        description="Optional. Run deadline in seconds; defaults to 45.",
    )


class ExecutionContext(BaseModel):
    """Runtime context passed to every governed tool call.

    Usage:
        Built by agent-web and passed into the MCP pipeline.

    Fields:
        run_id: Required agent run identifier.
        thread_id: Required conversation thread identifier.
        agent_id: Required agent identity executing the run.
        delegation: Required user delegation with scopes.
        budget: Required per-run resource limits.
        environment: Optional deployment environment; defaults to demo.
        trace_id: Optional distributed trace identifier.
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
    agent_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Agent identity executing the run.",
    )
    delegation: DelegationContext = Field(
        ...,
        description="Required. User delegation with scopes.",
    )
    budget: AgentBudget = Field(
        default_factory=AgentBudget,
        description="Optional. Per-run resource limits; defaults to AgentBudget().",
    )
    environment: str = Field(
        default="demo",
        min_length=1,
        max_length=32,
        description="Optional. Deployment environment; defaults to demo.",
    )
    trace_id: str | None = Field(
        default=None,
        max_length=128,
        description="Optional. Distributed trace identifier.",
    )

"""Pure policy rule helpers."""

from datetime import UTC, datetime

from pydantic import BaseModel

from agent_platform.mcp.registry import REQUEST_REROUTE
from agent_platform.mcp.schemas import RequestRerouteInput
from agent_platform.models.execution import AgentBudget
from agent_platform.models.identity import DelegationContext
from agent_platform.models.policy import ToolPolicy
from agent_platform.models.run import RunState


def delegation_is_expired(delegation: DelegationContext, now: datetime) -> bool:
    """Return True when delegation.expires_at is in the past."""
    if delegation.expires_at is None:
        return False
    return delegation.expires_at <= now


def missing_scopes(required: set[str], granted: set[str]) -> list[str]:
    """Return sorted scopes present in required but absent from granted."""
    return sorted(required - granted)


def scopes_satisfied(required: set[str], granted: set[str]) -> bool:
    """Return True when all required scopes are granted."""
    return required <= granted


def budget_would_be_exceeded(
    run: RunState,
    budget: AgentBudget,
    now: datetime,
) -> bool:
    """Return True when the next tool call would exceed run budget limits."""
    usage = run.usage
    if usage.tool_calls >= budget.max_tool_calls:
        return True
    if usage.input_tokens >= budget.max_input_tokens:
        return True
    if usage.output_tokens >= budget.max_output_tokens:
        return True
    if usage.estimated_cost_usd >= budget.max_estimated_cost_usd:
        return True
    elapsed = (now - run.created_at).total_seconds()
    return elapsed >= budget.deadline_seconds


def reroute_cost_exceeds_limit(
    tool_policy: ToolPolicy,
    arguments: BaseModel,
    cost_limit_eur: float,
) -> bool:
    """Return True when request_reroute cost exceeds the configured limit."""
    if tool_policy.name != REQUEST_REROUTE:
        return False
    reroute = RequestRerouteInput.model_validate(arguments)
    return reroute.expected_additional_cost_eur > cost_limit_eur


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(tz=UTC)

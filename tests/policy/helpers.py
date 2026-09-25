"""Shared helpers for policy tests."""

from datetime import UTC, datetime, timedelta

from agent_platform.mcp.registry import GET_SHIPMENT, REQUEST_REROUTE, TOOL_REGISTRY
from agent_platform.mcp.schemas import GetShipmentInput, RequestRerouteInput
from agent_platform.models.execution import AgentBudget, ExecutionContext
from agent_platform.models.identity import (
    SHIPMENT_RECOVERY_AGENT,
    SHIPMENT_RECOVERY_SCOPES,
    ActorIdentity,
    DelegationContext,
)
from agent_platform.models.run import RunState
from agent_platform.persistence.memory import MemoryRunStore
from agent_platform.policy.settings import PolicySettings

FIXED_NOW = datetime(2026, 9, 25, 12, 0, 0, tzinfo=UTC)


def build_context(
    *,
    agent_id: str = SHIPMENT_RECOVERY_AGENT,
    scopes: set[str] | None = None,
    run_id: str = "run-1",
    thread_id: str = "thread-1",
) -> ExecutionContext:
    """Build an ExecutionContext for policy tests."""
    resolved_scopes = set(scopes) if scopes is not None else set(SHIPMENT_RECOVERY_SCOPES)
    return ExecutionContext(
        run_id=run_id,
        thread_id=thread_id,
        agent_id=agent_id,
        delegation=DelegationContext(
            actor=ActorIdentity(actor_id="user-123", display_name="Demo User"),
            delegated_to=agent_id,
            scopes=resolved_scopes,
            issued_at=FIXED_NOW - timedelta(hours=1),
        ),
        budget=AgentBudget(),
    )


async def seed_run(run_store: MemoryRunStore, run_id: str = "run-1") -> RunState:
    """Create a fresh run in the run store."""
    run = RunState(
        run_id=run_id,
        thread_id="thread-1",
        status="running",
        created_at=FIXED_NOW - timedelta(seconds=5),
        updated_at=FIXED_NOW - timedelta(seconds=5),
    )
    await run_store.create_run(run)
    return run


def get_shipment_args() -> GetShipmentInput:
    """Return sample get_shipment arguments."""
    return GetShipmentInput(shipment_id="ABC123")


def reroute_args(
    *,
    route_id: str = "R-102",
    cost: float = 1450.0,
    approval_id: str = "apr-pending",
    idempotency_key: str = "key-abc-12345",
) -> RequestRerouteInput:
    """Return sample request_reroute arguments."""
    return RequestRerouteInput(
        shipment_id="ABC123",
        route_id=route_id,
        expected_additional_cost_eur=cost,
        idempotency_key=idempotency_key,
        approval_id=approval_id,
    )


GET_SHIPMENT_TOOL = TOOL_REGISTRY[GET_SHIPMENT]
REQUEST_REROUTE_TOOL = TOOL_REGISTRY[REQUEST_REROUTE]

DEFAULT_POLICY_SETTINGS = PolicySettings()

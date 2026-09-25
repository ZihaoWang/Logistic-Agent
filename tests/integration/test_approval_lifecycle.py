"""Integration tests for approval lifecycle through the governed pipeline."""

from typing import Any

import pytest

from agent_platform.mcp.registry import REQUEST_REROUTE
from agent_platform.models.approval import ApprovalDecision
from agent_platform.models.identity import SHIPMENT_RECOVERY_SCOPES
from agent_platform.persistence.memory import MemoryApprovalStore, MemoryAuditStore, MemoryRunStore
from agent_platform.policy.engine import PolicyEngine
from agent_platform.policy.settings import PolicySettings
from mcp_server.pipeline import ToolPipeline
from mcp_server.policy_slot import EnforcingPolicySlot
from mcp_server.tools.request_reroute import RequestRerouteTool
from tests.policy.helpers import FIXED_NOW, build_context, reroute_args, seed_run
from tests.unit.test_tool_pipeline import FakeBackend


@pytest.fixture
def reroute_backend_response() -> dict[str, Any]:
    """Return a successful reroute backend payload."""
    return {
        "request_reroute": {
            "action_id": "act-001",
            "shipment_id": "ABC123",
            "route_id": "R-102",
            "status": "accepted",
            "applied_at": FIXED_NOW.isoformat(),
        }
    }


async def test_approval_lifecycle_through_pipeline(
    reroute_backend_response: dict[str, Any],
) -> None:
    """Side-effect tool stops for approval, resumes after decision, then denies reuse."""
    backend = FakeBackend(reroute_backend_response)
    audit_store = MemoryAuditStore()
    run_store = MemoryRunStore()
    approval_store = MemoryApprovalStore(
        audit_store=audit_store,
        clock=lambda: FIXED_NOW,
    )
    engine = PolicyEngine(
        run_store=run_store,
        approval_store=approval_store,
        audit_store=audit_store,
        settings=PolicySettings(),
        clock=lambda: FIXED_NOW,
    )
    pipeline = ToolPipeline(
        tools={REQUEST_REROUTE: RequestRerouteTool(backend)},
        policy_slot=EnforcingPolicySlot(engine),
    )
    await seed_run(run_store)
    context = build_context(scopes=set(SHIPMENT_RECOVERY_SCOPES))
    raw_args = reroute_args(approval_id="apr-life-1").model_dump()

    first = await pipeline.run(REQUEST_REROUTE, raw_args, context)
    assert first.status == "approval_required"
    assert first.approval is not None
    assert backend.calls == []

    stored = await approval_store.get("apr-life-1")
    assert stored is not None
    assert stored.status == "pending"

    await approval_store.decide(
        ApprovalDecision(
            approval_id="apr-life-1",
            decision="approved",
            decided_by="user-123",
            decided_at=FIXED_NOW,
        ),
    )

    second = await pipeline.run(REQUEST_REROUTE, raw_args, context)
    assert second.status == "success"
    assert backend.calls == ["request_reroute"]

    consumed = await approval_store.get("apr-life-1")
    assert consumed is not None
    assert consumed.status == "consumed"

    third = await pipeline.run(REQUEST_REROUTE, raw_args, context)
    assert third.status == "denied"
    assert third.error is not None
    assert third.error.code == "APPROVAL_ALREADY_CONSUMED"
    assert backend.calls == ["request_reroute"]

    event_types = [event.event_type for event in audit_store.events]
    assert "approval.requested" in event_types
    assert "approval.approved" in event_types
    assert "policy.allowed" in event_types
    assert "policy.denied" in event_types


async def test_rejected_approval_does_not_call_backend(
    reroute_backend_response: dict[str, Any],
) -> None:
    """Rejecting an approval must not execute the side-effect tool."""
    backend = FakeBackend(reroute_backend_response)
    audit_store = MemoryAuditStore()
    run_store = MemoryRunStore()
    approval_store = MemoryApprovalStore(
        audit_store=audit_store,
        clock=lambda: FIXED_NOW,
    )
    engine = PolicyEngine(
        run_store=run_store,
        approval_store=approval_store,
        audit_store=audit_store,
        settings=PolicySettings(),
        clock=lambda: FIXED_NOW,
    )
    pipeline = ToolPipeline(
        tools={REQUEST_REROUTE: RequestRerouteTool(backend)},
        policy_slot=EnforcingPolicySlot(engine),
    )
    await seed_run(run_store)
    context = build_context(scopes=set(SHIPMENT_RECOVERY_SCOPES))
    raw_args = reroute_args(approval_id="apr-reject").model_dump()

    pending = await pipeline.run(REQUEST_REROUTE, raw_args, context)
    assert pending.status == "approval_required"

    await approval_store.decide(
        ApprovalDecision(
            approval_id="apr-reject",
            decision="rejected",
            decided_by="user-123",
            decided_at=FIXED_NOW,
        ),
    )

    denied = await pipeline.run(REQUEST_REROUTE, raw_args, context)
    assert denied.status == "denied"
    assert denied.error is not None
    assert denied.error.code == "APPROVAL_REJECTED"
    assert backend.calls == []

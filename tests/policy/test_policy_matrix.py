"""Parameterized policy matrix tests."""

from datetime import timedelta

import pytest

from agent_platform.execution.idempotency import hash_tool_arguments
from agent_platform.mcp.protocol import (
    APPROVAL_ALREADY_CONSUMED,
    APPROVAL_ARGUMENTS_MISMATCH,
    APPROVAL_EXPIRED,
    APPROVAL_RUN_MISMATCH,
    POLICY_ALLOWED,
    POLICY_MISSING_SCOPE,
    REROUTE_COST_LIMIT,
    SIDE_EFFECT_APPROVAL_REQUIRED,
)
from agent_platform.models.approval import ApprovalRequest
from agent_platform.models.identity import (
    INVESTIGATION_AGENT,
    INVESTIGATION_SCOPES,
    SHIPMENT_RECOVERY_AGENT,
    SHIPMENT_RECOVERY_SCOPES,
)
from agent_platform.persistence.memory import (
    MemoryApprovalStore,
    MemoryAuditStore,
    MemoryRunStore,
)
from agent_platform.policy.engine import PolicyEngine
from tests.policy.helpers import (
    DEFAULT_POLICY_SETTINGS,
    FIXED_NOW,
    GET_SHIPMENT_TOOL,
    REQUEST_REROUTE_TOOL,
    build_context,
    get_shipment_args,
    reroute_args,
    seed_run,
)


@pytest.fixture
def stores() -> tuple[MemoryRunStore, MemoryApprovalStore, MemoryAuditStore]:
    """Return fresh in-memory stores."""
    return MemoryRunStore(), MemoryApprovalStore(), MemoryAuditStore()


@pytest.fixture
def engine(
    stores: tuple[MemoryRunStore, MemoryApprovalStore, MemoryAuditStore],
) -> PolicyEngine:
    """Return a policy engine wired to fresh stores."""
    run_store, approval_store, audit_store = stores
    return PolicyEngine(
        run_store=run_store,
        approval_store=approval_store,
        audit_store=audit_store,
        settings=DEFAULT_POLICY_SETTINGS,
        clock=lambda: FIXED_NOW,
    )


@pytest.mark.parametrize(
    ("case_id", "tool", "args", "scopes", "approval", "expected_decision", "expected_reason"),
    [
        (
            "read_scope_present",
            GET_SHIPMENT_TOOL,
            get_shipment_args(),
            {"shipment:read"},
            None,
            "allow",
            POLICY_ALLOWED,
        ),
        (
            "read_scope_missing",
            GET_SHIPMENT_TOOL,
            get_shipment_args(),
            {"port:read"},
            None,
            "deny",
            POLICY_MISSING_SCOPE,
        ),
        (
            "write_scope_missing",
            REQUEST_REROUTE_TOOL,
            reroute_args(),
            {"shipment:read", "route:read"},
            None,
            "deny",
            POLICY_MISSING_SCOPE,
        ),
        (
            "write_scope_no_approval",
            REQUEST_REROUTE_TOOL,
            reroute_args(approval_id="apr-new"),
            set(SHIPMENT_RECOVERY_SCOPES),
            None,
            "require_approval",
            SIDE_EFFECT_APPROVAL_REQUIRED,
        ),
        (
            "approval_other_run",
            REQUEST_REROUTE_TOOL,
            reroute_args(approval_id="apr-other-run"),
            set(SHIPMENT_RECOVERY_SCOPES),
            "other_run",
            "deny",
            APPROVAL_RUN_MISMATCH,
        ),
        (
            "approval_different_arguments",
            REQUEST_REROUTE_TOOL,
            reroute_args(route_id="R-999", approval_id="apr-hash-mismatch"),
            set(SHIPMENT_RECOVERY_SCOPES),
            "matching_run",
            "deny",
            APPROVAL_ARGUMENTS_MISMATCH,
        ),
        (
            "expired_approval",
            REQUEST_REROUTE_TOOL,
            reroute_args(approval_id="apr-expired"),
            set(SHIPMENT_RECOVERY_SCOPES),
            "expired",
            "deny",
            APPROVAL_EXPIRED,
        ),
        (
            "consumed_approval",
            REQUEST_REROUTE_TOOL,
            reroute_args(approval_id="apr-consumed"),
            set(SHIPMENT_RECOVERY_SCOPES),
            "consumed",
            "deny",
            APPROVAL_ALREADY_CONSUMED,
        ),
        (
            "cost_above_threshold",
            REQUEST_REROUTE_TOOL,
            reroute_args(cost=8000.0, approval_id="apr-cost"),
            set(SHIPMENT_RECOVERY_SCOPES),
            None,
            "deny",
            REROUTE_COST_LIMIT,
        ),
        (
            "valid_approval",
            REQUEST_REROUTE_TOOL,
            reroute_args(approval_id="apr-valid"),
            set(SHIPMENT_RECOVERY_SCOPES),
            "approved",
            "allow",
            POLICY_ALLOWED,
        ),
    ],
)
async def test_policy_matrix(
    engine: PolicyEngine,
    stores: tuple[MemoryRunStore, MemoryApprovalStore, MemoryAuditStore],
    case_id: str,
    tool: object,
    args: object,
    scopes: set[str],
    approval: str | None,
    expected_decision: str,
    expected_reason: str,
) -> None:
    """Exercise the full policy matrix for governed tool calls."""
    _ = case_id
    run_store, approval_store, _audit_store = stores
    await seed_run(run_store)
    context = build_context(scopes=scopes)

    if approval == "other_run":
        await _store_approval(
            approval_store,
            approval_id="apr-other-run",
            run_id="run-other",
            args=reroute_args(),
            status="approved",
        )
    elif approval == "matching_run":
        await _store_approval(
            approval_store,
            approval_id="apr-hash-mismatch",
            run_id="run-1",
            args=reroute_args(route_id="R-102"),
            status="approved",
        )
    elif approval == "expired":
        await _store_approval(
            approval_store,
            approval_id="apr-expired",
            run_id="run-1",
            args=reroute_args(),
            status="pending",
            expires_at=FIXED_NOW - timedelta(minutes=1),
        )
    elif approval == "consumed":
        await _store_approval(
            approval_store,
            approval_id="apr-consumed",
            run_id="run-1",
            args=reroute_args(),
            status="consumed",
        )
    elif approval == "approved":
        await _store_approval(
            approval_store,
            approval_id="apr-valid",
            run_id="run-1",
            args=reroute_args(),
            status="approved",
        )

    decision = await engine.evaluate_tool_call(tool, args, context)  # type: ignore[arg-type]

    assert decision.decision == expected_decision
    assert decision.reason_code == expected_reason


async def test_investigation_agent_cannot_reroute(
    engine: PolicyEngine,
    stores: tuple[MemoryRunStore, MemoryApprovalStore, MemoryAuditStore],
) -> None:
    """Investigation agent is denied on reroute even with a valid recovery approval."""
    run_store, approval_store, _audit_store = stores
    await seed_run(run_store)
    await _store_approval(
        approval_store,
        approval_id="apr-recovery",
        run_id="run-1",
        args=reroute_args(approval_id="apr-recovery"),
        status="approved",
        agent_id=SHIPMENT_RECOVERY_AGENT,
    )
    context = build_context(
        agent_id=INVESTIGATION_AGENT,
        scopes=set(INVESTIGATION_SCOPES),
    )
    args = reroute_args(approval_id="apr-recovery")

    decision = await engine.evaluate_tool_call(REQUEST_REROUTE_TOOL, args, context)

    assert decision.decision == "deny"
    assert decision.reason_code == POLICY_MISSING_SCOPE


async def _store_approval(
    approval_store: MemoryApprovalStore,
    *,
    approval_id: str,
    run_id: str,
    args: object,
    status: str,
    expires_at: object | None = None,
    agent_id: str = SHIPMENT_RECOVERY_AGENT,
) -> None:
    resolved_expires = expires_at or FIXED_NOW + timedelta(minutes=30)
    approval = ApprovalRequest(
        approval_id=approval_id,
        run_id=run_id,
        tool_name="request_reroute",
        tool_arguments_hash=hash_tool_arguments("request_reroute", args),  # type: ignore[arg-type]
        summary="Test approval",
        requested_by_agent=agent_id,
        actor_id="user-123",
        created_at=FIXED_NOW - timedelta(minutes=5),
        expires_at=resolved_expires,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
    )
    await approval_store.create(approval)

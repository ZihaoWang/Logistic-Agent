"""Unit tests for approval argument hashing and matching."""

from datetime import timedelta

import pytest

from agent_platform.execution.idempotency import hash_tool_arguments
from agent_platform.mcp.registry import REQUEST_REROUTE
from agent_platform.models.approval import ApprovalRequest
from agent_platform.policy.approvals import evaluate_approval_match
from tests.policy.helpers import FIXED_NOW, build_context, reroute_args


def test_hash_changes_when_route_or_cost_changes() -> None:
    """Business argument hash must change when route or cost changes."""
    base = reroute_args()
    other_route = reroute_args(route_id="R-999")
    other_cost = reroute_args(cost=8000.0)

    base_hash = hash_tool_arguments(REQUEST_REROUTE, base)
    assert hash_tool_arguments(REQUEST_REROUTE, other_route) != base_hash
    assert hash_tool_arguments(REQUEST_REROUTE, other_cost) != base_hash


def test_hash_ignores_approval_and_idempotency_key() -> None:
    """Approval pointer and retry key must not change the business hash."""
    first = reroute_args(approval_id="apr-one", idempotency_key="key-one-12345")
    second = reroute_args(approval_id="apr-two", idempotency_key="key-two-67890")

    assert hash_tool_arguments(REQUEST_REROUTE, first) == hash_tool_arguments(
        REQUEST_REROUTE,
        second,
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("match", "match"),
        ("missing", "missing"),
        ("run_mismatch", "run_mismatch"),
        ("agent_mismatch", "agent_mismatch"),
        ("arguments_mismatch", "arguments_mismatch"),
        ("expired", "expired"),
        ("consumed", "consumed"),
        ("rejected", "rejected"),
        ("pending", "pending"),
    ],
)
def test_approval_match_results(mutation: str, expected: str) -> None:
    """Each approval match guard fails independently."""
    context = build_context()
    args = reroute_args()
    approval = ApprovalRequest(
        approval_id="apr-1",
        run_id="run-1",
        tool_name="request_reroute",
        tool_arguments_hash=hash_tool_arguments(REQUEST_REROUTE, args),
        summary="Test",
        requested_by_agent="shipment-recovery-agent",
        actor_id="user-123",
        created_at=FIXED_NOW - timedelta(minutes=5),
        expires_at=FIXED_NOW + timedelta(minutes=30),
        status="approved",
    )

    if mutation == "missing":
        stored: ApprovalRequest | None = None
    else:
        stored = approval
        if mutation == "run_mismatch":
            stored = approval.model_copy(update={"run_id": "run-other"})
        elif mutation == "agent_mismatch":
            stored = approval.model_copy(update={"requested_by_agent": "other-agent"})
        elif mutation == "arguments_mismatch":
            stored = approval.model_copy(update={"tool_arguments_hash": "deadbeef"})
        elif mutation == "expired":
            stored = approval.model_copy(
                update={"expires_at": FIXED_NOW - timedelta(minutes=1), "status": "pending"},
            )
        elif mutation == "consumed":
            stored = approval.model_copy(update={"status": "consumed"})
        elif mutation == "rejected":
            stored = approval.model_copy(update={"status": "rejected"})
        elif mutation == "pending":
            stored = approval.model_copy(update={"status": "pending"})

    result = evaluate_approval_match(
        stored,
        tool_name=REQUEST_REROUTE,
        arguments=args,
        context=context,
        now=FIXED_NOW,
    )
    assert result == expected

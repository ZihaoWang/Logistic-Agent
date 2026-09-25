"""Approval matching and request creation helpers."""

import uuid
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel

from agent_platform.execution.idempotency import hash_tool_arguments
from agent_platform.mcp.schemas import RequestRerouteInput
from agent_platform.models.approval import ApprovalRequest
from agent_platform.models.execution import ExecutionContext

ApprovalMatchResult = Literal[
    "match",
    "missing",
    "run_mismatch",
    "agent_mismatch",
    "arguments_mismatch",
    "expired",
    "consumed",
    "rejected",
    "pending",
]


def evaluate_approval_match(
    approval: ApprovalRequest | None,
    *,
    tool_name: str,
    arguments: BaseModel,
    context: ExecutionContext,
    now: datetime,
) -> ApprovalMatchResult:
    """Classify whether an approval record matches the current tool call."""
    if approval is None:
        return "missing"
    if approval.run_id != context.run_id:
        return "run_mismatch"
    if approval.requested_by_agent != context.agent_id:
        return "agent_mismatch"
    expected_hash = hash_tool_arguments(tool_name, arguments)
    if approval.tool_name != tool_name or approval.tool_arguments_hash != expected_hash:
        return "arguments_mismatch"
    if approval.status == "consumed":
        return "consumed"
    if approval.status == "rejected":
        return "rejected"
    if approval.status == "expired" or approval.expires_at <= now:
        return "expired"
    if approval.status == "pending":
        return "pending"
    if approval.status == "approved":
        return "match"
    return "missing"


def create_approval_request(
    *,
    tool_name: str,
    arguments: BaseModel,
    context: ExecutionContext,
    now: datetime,
    ttl_seconds: int,
    approval_id: str | None = None,
) -> ApprovalRequest:
    """Build a pending approval request bound to exact tool arguments."""
    resolved_id = approval_id or f"apr-{uuid.uuid4().hex[:12]}"
    return ApprovalRequest(
        approval_id=resolved_id,
        run_id=context.run_id,
        tool_name=tool_name,
        tool_arguments_hash=hash_tool_arguments(tool_name, arguments),
        summary=_build_summary(tool_name, arguments),
        requested_by_agent=context.agent_id,
        actor_id=context.delegation.actor.actor_id,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
        status="pending",
    )


def _build_summary(tool_name: str, arguments: BaseModel) -> str:
    """Return a short human-readable summary for one approval request."""
    if tool_name == "request_reroute":
        reroute = RequestRerouteInput.model_validate(arguments)
        cost = reroute.expected_additional_cost_eur
        return f"Reroute {reroute.shipment_id} using {reroute.route_id} " f"for EUR {cost:g}."
    return f"Approve {tool_name}."

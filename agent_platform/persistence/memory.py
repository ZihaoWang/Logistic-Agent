"""In-memory implementations of persistence protocols."""

import asyncio
import uuid
from collections.abc import Callable
from datetime import datetime

from agent_platform.models.approval import ApprovalDecision, ApprovalRequest
from agent_platform.models.audit import AuditEvent
from agent_platform.models.run import RunState
from agent_platform.persistence.base import AuditStore
from agent_platform.policy.rules import utc_now

Clock = Callable[[], datetime]


class MemoryRunStore:
    """Dict-backed RunStore for tests and local development."""

    def __init__(self) -> None:
        """Initialize empty run storage."""
        self._runs: dict[str, RunState] = {}

    async def create_run(self, run: RunState) -> None:
        """Persist a new run."""
        self._runs[run.run_id] = run

    async def get_run(self, run_id: str) -> RunState | None:
        """Return a run by id, or None if it does not exist."""
        return self._runs.get(run_id)

    async def update_run(self, run: RunState) -> None:
        """Update an existing run."""
        self._runs[run.run_id] = run


class MemoryApprovalStore:
    """Dict-backed ApprovalStore with locked decide and consume."""

    def __init__(
        self,
        audit_store: AuditStore | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize empty approval storage."""
        self._approvals: dict[str, ApprovalRequest] = {}
        self._lock = asyncio.Lock()
        self._audit_store = audit_store
        self._clock = clock or utc_now

    async def create(self, approval: ApprovalRequest) -> None:
        """Persist a new approval request."""
        self._approvals[approval.approval_id] = approval

    async def get(self, approval_id: str) -> ApprovalRequest | None:
        """Return an approval by id, or None if it does not exist."""
        return self._approvals.get(approval_id)

    async def decide(self, decision: ApprovalDecision) -> ApprovalRequest:
        """Apply a human decision to a pending approval."""
        async with self._lock:
            approval = self._approvals.get(decision.approval_id)
            if approval is None:
                msg = f"approval not found: {decision.approval_id}"
                raise ValueError(msg)
            if approval.status != "pending":
                msg = f"approval is not pending: {approval.status}"
                raise ValueError(msg)
            now = self._clock()
            if approval.expires_at <= now:
                expired = approval.model_copy(update={"status": "expired"})
                self._approvals[approval.approval_id] = expired
                msg = "approval has expired"
                raise ValueError(msg)
            new_status = "approved" if decision.decision == "approved" else "rejected"
            updated = approval.model_copy(
                update={
                    "status": new_status,
                    "decided_at": decision.decided_at,
                    "decided_by": decision.decided_by,
                },
            )
            self._approvals[approval.approval_id] = updated
            if self._audit_store is not None:
                event_type = (
                    "approval.approved" if new_status == "approved" else "approval.rejected"
                )
                await self._audit_store.append(
                    AuditEvent(
                        event_id=f"evt-{uuid.uuid4().hex[:12]}",
                        run_id=approval.run_id,
                        event_type=event_type,
                        actor_id=decision.decided_by,
                        agent_id=approval.requested_by_agent,
                        tool_name=approval.tool_name,
                        decision=decision.decision,
                        outcome=new_status,
                        timestamp=decision.decided_at,
                        metadata={"approval_id": approval.approval_id},
                    ),
                )
            return updated

    async def consume(self, approval_id: str) -> ApprovalRequest:
        """Mark an approved request as consumed after successful execution."""
        async with self._lock:
            approval = self._approvals.get(approval_id)
            if approval is None:
                msg = f"approval not found: {approval_id}"
                raise ValueError(msg)
            if approval.status != "approved":
                msg = f"approval is not approved: {approval.status}"
                raise ValueError(msg)
            now = self._clock()
            updated = approval.model_copy(
                update={"status": "consumed", "consumed_at": now},
            )
            self._approvals[approval_id] = updated
            return updated


class MemoryAuditStore:
    """List-backed AuditStore for tests and local development."""

    def __init__(self) -> None:
        """Initialize empty audit storage."""
        self.events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        """Append one audit event."""
        self.events.append(event)

    async def list_for_run(self, run_id: str) -> list[AuditEvent]:
        """Return audit events for one run in append order."""
        return [event for event in self.events if event.run_id == run_id]

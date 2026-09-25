"""Persistence protocols for runs, approvals, and audit events."""

from typing import Protocol

from agent_platform.models.approval import ApprovalDecision, ApprovalRequest
from agent_platform.models.audit import AuditEvent
from agent_platform.models.run import RunState


class RunStore(Protocol):
    """Storage interface for agent run state."""

    async def create_run(self, run: RunState) -> None:
        """Persist a new run."""

    async def get_run(self, run_id: str) -> RunState | None:
        """Return a run by id, or None if it does not exist."""

    async def update_run(self, run: RunState) -> None:
        """Update an existing run."""


class ApprovalStore(Protocol):
    """Storage interface for approval requests and decisions."""

    async def create(self, approval: ApprovalRequest) -> None:
        """Persist a new approval request."""

    async def get(self, approval_id: str) -> ApprovalRequest | None:
        """Return an approval by id, or None if it does not exist."""

    async def decide(self, decision: ApprovalDecision) -> ApprovalRequest:
        """Apply a human decision to a pending approval.

        Returns:
            Updated approval request.

        Raises:
            ValueError: When the approval is not pending or has expired.
        """

    async def consume(self, approval_id: str) -> ApprovalRequest:
        """Mark an approved request as consumed after successful execution.

        Returns:
            Updated approval request.

        Raises:
            ValueError: When the approval is not in approved status.
        """


class AuditStore(Protocol):
    """Storage interface for append-only audit events."""

    async def append(self, event: AuditEvent) -> None:
        """Append one audit event."""

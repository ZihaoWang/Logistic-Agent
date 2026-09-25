"""Agent runtime protocol and request/response models."""

from typing import Literal, Protocol

from pydantic import BaseModel, Field

from agent_platform.models.approval import ApprovalRequest
from agent_platform.models.execution import ExecutionContext


class AgentRequest(BaseModel):
    """Inbound message for one agent run turn."""

    thread_id: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=4096)


class AgentResponse(BaseModel):
    """Outcome of one agent run turn."""

    run_id: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=4096)
    status: Literal["completed", "waiting_for_approval", "failed"]
    pending_approval: ApprovalRequest | None = None


class AgentRuntime(Protocol):
    """Protocol for agent orchestration backends."""

    async def run(
        self,
        request: AgentRequest,
        context: ExecutionContext,
    ) -> AgentResponse:
        """Execute one agent turn for the given context."""

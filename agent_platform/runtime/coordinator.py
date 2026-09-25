"""Run lifecycle coordinator for agent-web."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from agent_platform.models.approval import ApprovalDecision
from agent_platform.models.execution import AgentBudget, ExecutionContext
from agent_platform.models.identity import (
    INVESTIGATION_AGENT,
    INVESTIGATION_SCOPES,
    SHIPMENT_RECOVERY_AGENT,
    SHIPMENT_RECOVERY_SCOPES,
    ActorIdentity,
    DelegationContext,
)
from agent_platform.models.run import RunState
from agent_platform.observability.logging import bind_run, get_logger
from agent_platform.observability.metrics import (
    record_agent_run,
    record_agent_run_duration,
    record_agent_run_failed,
    record_approval_approved,
    record_approval_rejected,
)
from agent_platform.observability.tracing import current_trace_id, start_span
from agent_platform.persistence.base import ApprovalStore, AuditStore, RunStore
from agent_platform.runtime.adk_runtime import AdkAgentRuntime
from agent_platform.runtime.base import AgentRequest, AgentResponse
from agent_platform.runtime.messages import (
    message_for_rejection,
    message_for_successful_reroute,
    message_for_tool_result,
)
from agent_platform.runtime.tool_executor import GovernedToolExecutor

_SERVICE = "agent-web"
_log = get_logger(_SERVICE)


class StartRunRequest(BaseModel):
    """HTTP body for starting an agent run."""

    thread_id: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=4096)
    agent_id: str = Field(default=SHIPMENT_RECOVERY_AGENT, min_length=1, max_length=64)


class ApprovalDecisionRequest(BaseModel):
    """HTTP body for approving or rejecting a pending action."""

    decision: Literal["approved", "rejected"]
    decided_by: str = Field(default="user-123", min_length=1, max_length=64)
    comment: str | None = Field(default=None, max_length=512)


class RunCoordinator:
    """Create runs, dispatch the runtime, and resume after approval."""

    def __init__(
        self,
        runtime: AdkAgentRuntime,
        executor: GovernedToolExecutor,
        *,
        run_store: RunStore,
        approval_store: ApprovalStore,
        audit_store: AuditStore,
    ) -> None:
        """Store runtime and persistence dependencies."""
        self._runtime = runtime
        self._executor = executor
        self._run_store = run_store
        self._approval_store = approval_store
        self._audit_store = audit_store

    async def start_run(self, body: StartRunRequest) -> AgentResponse:
        """Create a run and execute the agent for one user message."""
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        run = RunState(
            run_id=run_id,
            thread_id=body.thread_id,
            status="running",
            created_at=now,
            updated_at=now,
            last_message=body.message,
        )
        await self._run_store.create_run(run)
        context = self._build_context(
            run_id=run_id,
            thread_id=body.thread_id,
            agent_id=body.agent_id,
        )
        bind_run(run_id, service=_SERVICE)
        started = time.perf_counter()
        with start_span(
            "agent.run",
            service=_SERVICE,
            attributes={
                "run.id": run_id,
                "thread.id": body.thread_id,
                "agent.id": body.agent_id,
            },
        ):
            trace_id = current_trace_id()
            if trace_id is not None:
                context = context.model_copy(update={"trace_id": trace_id})
            _log.info("agent.run.started", run_id=run_id, agent_id=body.agent_id)
            try:
                response = await self._runtime.run(
                    AgentRequest(thread_id=body.thread_id, message=body.message),
                    context,
                )
            except Exception:
                record_agent_run_failed(service=_SERVICE)
                record_agent_run(service=_SERVICE, status="failed")
                record_agent_run_duration(
                    service=_SERVICE,
                    seconds=time.perf_counter() - started,
                )
                raise
            record_agent_run(service=_SERVICE, status=response.status)
            if response.status == "failed":
                record_agent_run_failed(service=_SERVICE)
            record_agent_run_duration(
                service=_SERVICE,
                seconds=time.perf_counter() - started,
            )
            return response

    async def get_run(self, run_id: str) -> RunState | None:
        """Return persisted run state."""
        return await self._run_store.get_run(run_id)

    async def list_events(self, run_id: str) -> list[Any]:
        """Return audit events for one run."""
        return await self._audit_store.list_for_run(run_id)

    async def decide_approval(
        self,
        approval_id: str,
        body: ApprovalDecisionRequest,
    ) -> AgentResponse:
        """Apply a human decision and resume or finalize the run."""
        approval = await self._approval_store.get(approval_id)
        if approval is None:
            msg = f"approval not found: {approval_id}"
            raise ValueError(msg)

        run = await self._run_store.get_run(approval.run_id)
        if run is None:
            msg = f"run not found: {approval.run_id}"
            raise ValueError(msg)

        now = _utc_now()
        await self._approval_store.decide(
            ApprovalDecision(
                approval_id=approval_id,
                decision=body.decision,
                decided_by=body.decided_by,
                decided_at=now,
                comment=body.comment,
            ),
        )

        if body.decision == "rejected":
            record_approval_rejected(service=_SERVICE)
            await self._run_store.update_run(
                run.model_copy(
                    update={
                        "status": "completed",
                        "pending_approval_id": None,
                        "pending_tool_call": None,
                        "updated_at": now,
                    },
                ),
            )
            return AgentResponse(
                run_id=run.run_id,
                message=message_for_rejection(),
                status="completed",
            )

        record_approval_approved(service=_SERVICE)

        pending = run.pending_tool_call
        if pending is None:
            msg = f"run {run.run_id} has no pending tool call to replay"
            raise ValueError(msg)

        tool_name = str(pending["tool_name"])
        arguments = dict(pending["arguments"])
        context = self._build_context(
            run_id=run.run_id,
            thread_id=run.thread_id,
            agent_id=approval.requested_by_agent,
        )
        bind_run(run.run_id, service=_SERVICE)
        trace_id = current_trace_id()
        if trace_id is not None:
            context = context.model_copy(update={"trace_id": trace_id})
        outcome = await self._executor.execute(tool_name, arguments, context)
        result = outcome.result

        if result.status == "success":
            await self._run_store.update_run(
                run.model_copy(
                    update={
                        "status": "completed",
                        "pending_approval_id": None,
                        "pending_tool_call": None,
                        "updated_at": now,
                    },
                ),
            )
            return AgentResponse(
                run_id=run.run_id,
                message=message_for_successful_reroute(),
                status="completed",
            )

        record_agent_run_failed(service=_SERVICE)
        await self._run_store.update_run(
            run.model_copy(
                update={
                    "status": "failed",
                    "last_error_code": result.error.code if result.error else "TOOL_FAILED",
                    "updated_at": now,
                },
            ),
        )
        return AgentResponse(
            run_id=run.run_id,
            message=message_for_tool_result(tool_name, result),
            status="failed",
        )

    def _build_context(
        self,
        *,
        run_id: str,
        thread_id: str,
        agent_id: str,
    ) -> ExecutionContext:
        """Build execution context for one agent identity."""
        now = _utc_now()
        scopes = (
            set(INVESTIGATION_SCOPES)
            if agent_id == INVESTIGATION_AGENT
            else set(SHIPMENT_RECOVERY_SCOPES)
        )
        return ExecutionContext(
            run_id=run_id,
            thread_id=thread_id,
            agent_id=agent_id,
            delegation=DelegationContext(
                actor=ActorIdentity(actor_id="user-123", display_name="Demo User"),
                delegated_to=agent_id,
                scopes=scopes,
                issued_at=now - timedelta(minutes=5),
            ),
            budget=AgentBudget(max_model_calls=8),
        )


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)

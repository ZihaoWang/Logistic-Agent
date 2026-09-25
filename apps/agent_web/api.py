"""HTTP routes for agent-web."""

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent_platform.models.approval import ApprovalRequest
from agent_platform.models.audit import AuditEvent
from agent_platform.models.run import RunState
from agent_platform.runtime.base import AgentResponse
from agent_platform.runtime.coordinator import ApprovalDecisionRequest, StartRunRequest
from apps.agent_web.dependencies import AppServices, get_services

router = APIRouter()
_run_semaphore: asyncio.Semaphore | None = None


class HealthResponse(BaseModel):
    """Health check payload."""

    status: str
    service: str
    version: str


class RunResponse(BaseModel):
    """Agent run response returned to clients."""

    run_id: str
    message: str
    status: str
    pending_approval: ApprovalRequest | None = None


class RunStateResponse(BaseModel):
    """Persisted run state for polling."""

    run: RunState


class EventsResponse(BaseModel):
    """Audit events for one run."""

    run_id: str
    events: list[AuditEvent]


class BusyResponse(BaseModel):
    """Response when the server is at concurrency capacity."""

    detail: str = Field(default="Too many concurrent agent runs")


def _get_semaphore(services: AppServices) -> asyncio.Semaphore:
    global _run_semaphore
    if _run_semaphore is None:
        _run_semaphore = asyncio.Semaphore(services.settings.max_concurrent_agent_runs)
    return _run_semaphore


def _to_run_response(response: AgentResponse) -> RunResponse:
    return RunResponse(
        run_id=response.run_id,
        message=response.message,
        status=response.status,
        pending_approval=response.pending_approval,
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return process liveness without calling downstream dependencies."""
    settings = get_services().settings
    return HealthResponse(status="ok", service="agent-web", version=settings.service_version)


@router.post("/v1/agent/runs", response_model=RunResponse)
async def start_run(body: StartRunRequest) -> RunResponse:
    """Start one agent run for a user message."""
    services = get_services()
    semaphore = _get_semaphore(services)
    acquired = False
    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=0)
        acquired = True
    except TimeoutError as exc:
        raise HTTPException(status_code=429, detail="Too many concurrent agent runs") from exc

    try:
        try:
            response = await services.coordinator.start_run(body)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail="Agent run failed") from exc
        return _to_run_response(response)
    finally:
        if acquired:
            semaphore.release()


@router.get("/v1/agent/runs/{run_id}", response_model=RunStateResponse)
async def get_run(run_id: str) -> RunStateResponse:
    """Return persisted run state."""
    services = get_services()
    run = await services.coordinator.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStateResponse(run=run)


@router.post("/v1/approvals/{approval_id}/decision", response_model=RunResponse)
async def decide_approval(
    approval_id: str,
    body: ApprovalDecisionRequest,
) -> RunResponse:
    """Apply a human approval decision and resume the run when approved."""
    services = get_services()
    try:
        response = await services.coordinator.decide_approval(approval_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_run_response(response)


@router.get("/v1/runs/{run_id}/events", response_model=EventsResponse)
async def list_run_events(run_id: str) -> EventsResponse:
    """Return audit events for one run."""
    services = get_services()
    run = await services.coordinator.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    events = await services.coordinator.list_events(run_id)
    return EventsResponse(run_id=run_id, events=events)

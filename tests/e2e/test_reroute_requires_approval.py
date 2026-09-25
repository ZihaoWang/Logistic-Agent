"""End-to-end reroute flow stops for approval and resumes correctly."""

from agent_platform.runtime.adk_runtime import AdkAgentRuntime
from agent_platform.runtime.coordinator import (
    ApprovalDecisionRequest,
    RunCoordinator,
    StartRunRequest,
)
from agent_platform.runtime.tool_executor import GovernedToolExecutor
from apps.logistics_api.repository import InMemoryLogisticsRepository
from mcp_server.server import GovernedMcpBundle
from tests.e2e.scripted_llm import ScriptedLlm


def _build_coordinator(
    bundle: GovernedMcpBundle,
    executor: GovernedToolExecutor,
    steps: list[dict[str, object]],
) -> RunCoordinator:
    runtime = AdkAgentRuntime(
        executor,
        bundle.run_store,
        model=ScriptedLlm(steps=steps),
    )
    return RunCoordinator(
        runtime,
        executor,
        run_store=bundle.run_store,
        approval_store=bundle.approval_store,
        audit_store=bundle.audit_store,
    )


async def test_reroute_stops_for_approval_and_resumes(
    governed_bundle: GovernedMcpBundle,
    tool_executor: GovernedToolExecutor,
    repo: InMemoryLogisticsRepository,
) -> None:
    """Reroute stops at approval, writes only after approval, and rejects skip writes."""
    coordinator = _build_coordinator(
        governed_bundle,
        tool_executor,
        steps=[
            {
                "function_call": {
                    "name": "request_reroute",
                    "args": {
                        "shipment_id": "ABC123",
                        "route_id": "R-102",
                        "expected_additional_cost_eur": 1450.0,
                    },
                },
            },
            {"text": "Should not reach this."},
        ],
    )

    first = await coordinator.start_run(
        StartRunRequest(
            thread_id="t-reroute",
            message="Reroute ABC123 using R-102.",
        ),
    )

    assert first.status == "waiting_for_approval"
    assert first.pending_approval is not None
    assert repo.applied_reroute_count == 0

    approval_id = first.pending_approval.approval_id
    approved = await coordinator.decide_approval(
        approval_id,
        ApprovalDecisionRequest(decision="approved"),
    )
    assert approved.status == "completed"
    assert repo.applied_reroute_count == 1

    consumed = await governed_bundle.approval_store.get(approval_id)
    assert consumed is not None
    assert consumed.status == "consumed"


async def test_rejected_approval_does_not_write(
    governed_bundle: GovernedMcpBundle,
    tool_executor: GovernedToolExecutor,
    repo: InMemoryLogisticsRepository,
) -> None:
    """Rejecting approval completes the run without backend writes."""
    coordinator = _build_coordinator(
        governed_bundle,
        tool_executor,
        steps=[
            {
                "function_call": {
                    "name": "request_reroute",
                    "args": {
                        "shipment_id": "ABC123",
                        "route_id": "R-102",
                        "expected_additional_cost_eur": 1450.0,
                    },
                },
            },
        ],
    )

    first = await coordinator.start_run(
        StartRunRequest(
            thread_id="t-reject",
            message="Reroute ABC123 using R-102.",
        ),
    )
    assert first.status == "waiting_for_approval"
    assert first.pending_approval is not None
    assert repo.applied_reroute_count == 0

    rejected = await coordinator.decide_approval(
        first.pending_approval.approval_id,
        ApprovalDecisionRequest(decision="rejected"),
    )
    assert rejected.status == "completed"
    assert repo.applied_reroute_count == 0

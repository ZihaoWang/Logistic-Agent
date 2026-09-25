"""End-to-end investigation-agent read and reroute denial."""

from agent_platform.mcp.registry import REQUEST_REROUTE
from agent_platform.models.identity import INVESTIGATION_AGENT, INVESTIGATION_SCOPES
from agent_platform.runtime.adk_runtime import AdkAgentRuntime
from agent_platform.runtime.coordinator import RunCoordinator, StartRunRequest
from agent_platform.runtime.messages import message_for_tool_result
from agent_platform.runtime.tool_executor import GovernedToolExecutor
from apps.logistics_api.repository import InMemoryLogisticsRepository
from mcp_server.server import GovernedMcpBundle
from tests.e2e.scripted_llm import ScriptedLlm
from tests.policy.helpers import build_context, seed_run


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


async def test_investigation_agent_read_works(
    governed_bundle: GovernedMcpBundle,
    tool_executor: GovernedToolExecutor,
    repo: InMemoryLogisticsRepository,
) -> None:
    """Investigation agent can answer a read-only question."""
    coordinator = _build_coordinator(
        governed_bundle,
        tool_executor,
        steps=[
            {"function_call": {"name": "get_shipment", "args": {"shipment_id": "ABC123"}}},
            {"text": "ABC123 is delayed in Rotterdam."},
        ],
    )

    response = await coordinator.start_run(
        StartRunRequest(
            thread_id="t-inv-read",
            message="Where is ABC123?",
            agent_id=INVESTIGATION_AGENT,
        ),
    )

    assert response.status == "completed"
    assert "delayed" in response.message.lower()
    assert repo.applied_reroute_count == 0


async def test_investigation_agent_never_writes(
    governed_bundle: GovernedMcpBundle,
    tool_executor: GovernedToolExecutor,
    repo: InMemoryLogisticsRepository,
) -> None:
    """Investigation agent does not expose or call request_reroute."""
    coordinator = _build_coordinator(
        governed_bundle,
        tool_executor,
        steps=[
            {"function_call": {"name": "get_shipment", "args": {"shipment_id": "ABC123"}}},
            {"text": "I cannot reroute shipments from this agent."},
        ],
    )

    response = await coordinator.start_run(
        StartRunRequest(
            thread_id="t-inv-deny",
            message="Reroute ABC123 using R-102.",
            agent_id=INVESTIGATION_AGENT,
        ),
    )

    assert response.status == "completed"
    events = await governed_bundle.audit_store.list_for_run(response.run_id)
    tool_names = [event.tool_name for event in events if event.tool_name]
    assert REQUEST_REROUTE not in tool_names
    assert repo.applied_reroute_count == 0

    context = build_context(agent_id=INVESTIGATION_AGENT, scopes=set(INVESTIGATION_SCOPES))
    await seed_run(governed_bundle.run_store, run_id=context.run_id)
    outcome = await tool_executor.execute(
        REQUEST_REROUTE,
        {
            "shipment_id": "ABC123",
            "route_id": "R-102",
            "expected_additional_cost_eur": 1450.0,
        },
        context,
    )
    assert outcome.result.status == "denied"
    assert outcome.result.error is not None
    assert outcome.result.error.code == "POLICY_MISSING_SCOPE"
    user_message = message_for_tool_result(REQUEST_REROUTE, outcome.result)
    assert "POLICY_MISSING_SCOPE" not in user_message
    assert repo.applied_reroute_count == 0

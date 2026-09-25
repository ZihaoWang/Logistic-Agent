"""End-to-end read flow through the ADK runtime."""

from agent_platform.runtime.adk_runtime import AdkAgentRuntime
from agent_platform.runtime.coordinator import RunCoordinator, StartRunRequest
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


async def test_read_flow_returns_tool_backed_answer(
    governed_bundle: GovernedMcpBundle,
    tool_executor: GovernedToolExecutor,
    repo: InMemoryLogisticsRepository,
) -> None:
    """A read question uses get_shipment and returns facts from tool data."""
    coordinator = _build_coordinator(
        governed_bundle,
        tool_executor,
        steps=[
            {"function_call": {"name": "get_shipment", "args": {"shipment_id": "ABC123"}}},
            {"text": "ABC123 is delayed in Rotterdam."},
        ],
    )

    response = await coordinator.start_run(
        StartRunRequest(thread_id="t-read", message="Where is ABC123?"),
    )

    assert response.status == "completed"
    assert "delayed" in response.message.lower()
    assert repo.applied_reroute_count == 0

    events = await governed_bundle.audit_store.list_for_run(response.run_id)
    tool_names = [event.tool_name for event in events if event.tool_name]
    assert "get_shipment" in tool_names

"""Integration tests for trace and log correlation."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import pytest
from structlog.testing import capture_logs

from agent_platform.mcp.registry import REQUEST_REROUTE
from agent_platform.models.run import RunState
from agent_platform.observability.logging import bind_run, configure_structlog, get_logger
from agent_platform.observability.setup import InMemoryTelemetry
from agent_platform.observability.tracing import start_span
from agent_platform.runtime.coordinator import RunCoordinator, StartRunRequest
from agent_platform.runtime.tool_executor import GovernedToolExecutor
from apps.logistics_api.main import create_app
from apps.logistics_api.repository import InMemoryLogisticsRepository
from mcp_server.server import create_governed_mcp, create_test_backend
from tests.e2e.scripted_llm import ScriptedLlm
from tests.helpers.observability import metric_sum, span_attribute, span_names, span_trace_ids
from tests.policy.helpers import build_context

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture
def governed_stack() -> tuple[Any, GovernedToolExecutor]:
    """Return executor and MCP bundle wired to in-process logistics-api."""
    repo = InMemoryLogisticsRepository.from_data_dir(DATA_DIR)
    app = create_app(repo=repo, enable_observability=False)
    backend = create_test_backend(app)
    bundle = create_governed_mcp(backend=backend)
    from agent_platform.mcp.client import McpClient

    client = McpClient(bundle.server)
    executor = GovernedToolExecutor(client)
    return bundle, executor


async def test_one_run_id_traceable_across_services(
    governed_stack: tuple[Any, GovernedToolExecutor],
    telemetry: InMemoryTelemetry,
) -> None:
    """One tool call produces a single trace spanning agent, MCP, and backend."""
    bundle, executor = governed_stack
    context = build_context(run_id="run-trace-1")
    from datetime import UTC, datetime

    now = datetime.now(tz=UTC)
    await bundle.run_store.create_run(
        RunState(
            run_id=context.run_id,
            thread_id=context.thread_id,
            status="running",
            created_at=now,
            updated_at=now,
        ),
    )
    configure_structlog(json_output=True)

    with redirect_stdout(io.StringIO()) as captured:
        with start_span(
            "agent.run",
            service="agent-web",
            attributes={"run.id": context.run_id, "agent.id": context.agent_id},
        ):
            bind_run(context.run_id, service="agent-web")
            get_logger("agent-web").info("trace.correlation.check")
            outcome = await executor.execute(
                "get_shipment",
                {"shipment_id": "ABC123"},
                context,
            )
        log_output = captured.getvalue()

    assert outcome.result.status == "success"
    spans = telemetry.span_exporter.get_finished_spans()
    trace_ids = span_trace_ids(spans)
    assert len(trace_ids) == 1
    names = span_names(spans)
    assert "agent.run" in names
    assert "mcp.get_shipment" in names
    assert "policy.get_shipment" in names
    assert "backend.get_shipment" in names
    assert "logistics-api.request" in names

    assert context.run_id in log_output


async def test_retry_visible_in_trace_and_logs(
    governed_stack: tuple[Any, GovernedToolExecutor],
    telemetry: InMemoryTelemetry,
) -> None:
    """A retried tool call produces distinct spans and a tool.retry log line."""
    from unittest.mock import AsyncMock

    from agent_platform.mcp.protocol import (
        BACKEND_UNAVAILABLE,
        build_error,
        build_failed_result,
        build_success_result,
    )

    _bundle, _executor = governed_stack
    context = build_context(run_id="run-retry-1")
    configure_structlog(json_output=True)

    mock_call = AsyncMock(
        side_effect=[
            build_failed_result(
                "get_shipment",
                10,
                build_error(
                    BACKEND_UNAVAILABLE,
                    "transport",
                    "backend down",
                    retryable=True,
                    details={"status_code": 503},
                ),
            ),
            build_success_result("get_shipment", 12, {"shipment": {"shipment_id": "ABC123"}}),
        ],
    )
    client = AsyncMock()
    client.call = mock_call
    executor = GovernedToolExecutor(client)

    with capture_logs() as logs:
        outcome = await executor.execute("get_shipment", {"shipment_id": "ABC123"}, context)

    assert outcome.result.status == "success"
    spans = telemetry.span_exporter.get_finished_spans()
    mcp_spans = [span for span in spans if span.name == "mcp.get_shipment"]
    assert len(mcp_spans) == 2
    attempts = {
        span.attributes.get("tool.attempt") for span in mcp_spans if span.attributes is not None
    }
    assert attempts == {1, 2}
    retry_logs = [entry for entry in logs if entry.get("event") == "tool.retry"]
    assert len(retry_logs) == 1
    assert retry_logs[0]["reason"] == "HTTP_503"


async def test_policy_decision_visible_in_trace(
    governed_stack: tuple[Any, GovernedToolExecutor],
    telemetry: InMemoryTelemetry,
) -> None:
    """request_reroute approval gate produces a policy span and metric."""
    bundle, executor = governed_stack
    context = build_context(run_id="run-policy-1")
    from datetime import UTC, datetime

    now = datetime.now(tz=UTC)
    await bundle.run_store.create_run(
        RunState(
            run_id=context.run_id,
            thread_id=context.thread_id,
            status="running",
            created_at=now,
            updated_at=now,
        ),
    )

    before = metric_sum(
        telemetry.metric_reader.get_metrics_data(),
        "approval_requests_total",
    )
    outcome = await executor.execute(
        REQUEST_REROUTE,
        {
            "shipment_id": "ABC123",
            "route_id": "R-102",
            "expected_additional_cost_eur": 500.0,
        },
        context,
    )
    assert outcome.result.status == "approval_required"

    spans = telemetry.span_exporter.get_finished_spans()
    assert "policy.request_reroute" in span_names(spans)
    assert span_attribute(spans, "policy.request_reroute", "approval.required") is True
    after = metric_sum(
        telemetry.metric_reader.get_metrics_data(),
        "approval_requests_total",
    )
    assert after == before + 1


async def test_end_to_end_coordinator_trace(
    governed_stack: tuple[Any, GovernedToolExecutor],
    telemetry: InMemoryTelemetry,
) -> None:
    """Coordinator start_run keeps one trace id through a scripted agent turn."""
    bundle, executor = governed_stack
    from agent_platform.runtime.adk_runtime import AdkAgentRuntime

    scripted = ScriptedLlm(
        steps=[
            {"function_call": {"name": "get_shipment", "args": {"shipment_id": "ABC123"}}},
            {"text": "Shipment ABC123 is delayed."},
        ],
    )
    runtime = AdkAgentRuntime(executor, bundle.run_store, model=scripted)
    coordinator = RunCoordinator(
        runtime,
        executor,
        run_store=bundle.run_store,
        approval_store=bundle.approval_store,
        audit_store=bundle.audit_store,
    )
    response = await coordinator.start_run(
        StartRunRequest(thread_id="thread-1", message="What is happening with ABC123?"),
    )
    assert response.status == "completed"
    spans = telemetry.span_exporter.get_finished_spans()
    assert len(span_trace_ids(spans)) == 1
    assert "agent.run" in span_names(spans)

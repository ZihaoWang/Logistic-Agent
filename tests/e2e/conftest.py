"""Shared fixtures for end-to-end agent tests."""

from pathlib import Path

import pytest

from agent_platform.mcp.client import McpClient
from agent_platform.runtime.adk_runtime import AdkAgentRuntime
from agent_platform.runtime.coordinator import RunCoordinator
from agent_platform.runtime.tool_executor import GovernedToolExecutor
from apps.logistics_api.main import create_app
from apps.logistics_api.repository import InMemoryLogisticsRepository
from mcp_server.server import GovernedMcpBundle, create_governed_mcp, create_test_backend

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture
def repo() -> InMemoryLogisticsRepository:
    """Return a fresh in-memory logistics repository."""
    return InMemoryLogisticsRepository.from_data_dir(DATA_DIR)


@pytest.fixture
def governed_bundle(repo: InMemoryLogisticsRepository) -> GovernedMcpBundle:
    """Return a governed MCP bundle wired to an in-process logistics-api."""
    app = create_app(repo=repo)
    backend = create_test_backend(app)
    return create_governed_mcp(backend=backend)


@pytest.fixture
def mcp_client(governed_bundle: GovernedMcpBundle) -> McpClient:
    """Return an MCP client for the governed server."""
    return McpClient(governed_bundle.server)


@pytest.fixture
def tool_executor(mcp_client: McpClient) -> GovernedToolExecutor:
    """Return a governed tool executor."""
    return GovernedToolExecutor(mcp_client)


@pytest.fixture
def agent_runtime(
    governed_bundle: GovernedMcpBundle,
    tool_executor: GovernedToolExecutor,
) -> AdkAgentRuntime:
    """Return an ADK runtime without a default live model."""
    return AdkAgentRuntime(
        tool_executor,
        governed_bundle.run_store,
        model="scripted-test",
    )


@pytest.fixture
def coordinator(
    governed_bundle: GovernedMcpBundle,
    agent_runtime: AdkAgentRuntime,
    tool_executor: GovernedToolExecutor,
) -> RunCoordinator:
    """Return a run coordinator wired to governed stores."""
    return RunCoordinator(
        agent_runtime,
        tool_executor,
        run_store=governed_bundle.run_store,
        approval_store=governed_bundle.approval_store,
        audit_store=governed_bundle.audit_store,
    )

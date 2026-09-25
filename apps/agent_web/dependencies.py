"""Dependency wiring for agent-web."""

from dataclasses import dataclass
from functools import lru_cache

from agent_platform.mcp.client import McpClient
from agent_platform.runtime.adk_runtime import AdkAgentRuntime
from agent_platform.runtime.coordinator import RunCoordinator
from agent_platform.runtime.settings import RuntimeSettings
from agent_platform.runtime.tool_executor import GovernedToolExecutor
from apps.logistics_api.main import create_app
from mcp_server.server import GovernedMcpBundle, create_governed_mcp, create_test_backend


@dataclass
class AppServices:
    """Shared services for one agent-web process."""

    settings: RuntimeSettings
    bundle: GovernedMcpBundle
    coordinator: RunCoordinator
    runtime: AdkAgentRuntime
    executor: GovernedToolExecutor


@lru_cache
def get_services() -> AppServices:
    """Build and cache application services."""
    settings = RuntimeSettings()
    logistics_app = create_app()
    backend = create_test_backend(logistics_app)
    bundle = create_governed_mcp(backend=backend)
    mcp_client = McpClient(bundle.server)
    executor = GovernedToolExecutor(mcp_client)
    runtime = AdkAgentRuntime(
        executor,
        bundle.run_store,
        settings=settings,
    )
    coordinator = RunCoordinator(
        runtime,
        executor,
        run_store=bundle.run_store,
        approval_store=bundle.approval_store,
        audit_store=bundle.audit_store,
    )
    return AppServices(
        settings=settings,
        bundle=bundle,
        coordinator=coordinator,
        runtime=runtime,
        executor=executor,
    )

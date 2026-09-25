"""Runtime wiring for MCP tools and the execution pipeline."""

import httpx

from agent_platform.mcp.registry import (
    get_policy,
)
from mcp_server.backend.http import HttpLogisticsClient
from mcp_server.pipeline import ToolPipeline
from mcp_server.policy_slot import BasePolicySlot, PassthroughPolicySlot
from mcp_server.tools import (
    CheckPolicyTool,
    EstimateCostTool,
    FindRoutesTool,
    GetPortStatusTool,
    GetShipmentTool,
    RequestRerouteTool,
)
from mcp_server.tools.base import BaseTool


def build_tools(backend: HttpLogisticsClient) -> dict[str, BaseTool]:
    """Create all tool handlers for the given backend client.

    Parameters:
        backend: HTTP client for logistics-api.

    Returns:
        Map of tool name to BaseTool implementation.
    """
    tool_instances: list[BaseTool] = [
        GetShipmentTool(backend),
        GetPortStatusTool(backend),
        FindRoutesTool(backend),
        EstimateCostTool(backend),
        CheckPolicyTool(backend),
        RequestRerouteTool(backend),
    ]
    return {tool.name: tool for tool in tool_instances}


def build_pipeline(
    backend: HttpLogisticsClient,
    policy_slot: BasePolicySlot | None = None,
) -> ToolPipeline:
    """Create the tool pipeline with optional policy slot override.

    Parameters:
        backend: HTTP client for logistics-api.
        policy_slot: Optional policy slot; defaults to passthrough.

    Returns:
        Configured ToolPipeline instance.
    """
    return ToolPipeline(
        tools=build_tools(backend),
        policy_slot=policy_slot or PassthroughPolicySlot(),
    )


def build_http_backend(base_url: str) -> HttpLogisticsClient:
    """Create an HTTP backend client for logistics-api.

    Parameters:
        base_url: Base URL for logistics-api.

    Returns:
        HttpLogisticsClient using a new AsyncClient.
    """
    client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
    return HttpLogisticsClient(client)


def tool_timeout(tool_name: str) -> float:
    """Return the FastMCP timeout for a tool name.

    Parameters:
        tool_name: Registered MCP tool name.

    Returns:
        Timeout in seconds from the tool policy.
    """
    return get_policy(tool_name).timeout_seconds

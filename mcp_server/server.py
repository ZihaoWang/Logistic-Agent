"""FastMCP server entry point for the logistics gateway."""

from typing import Any

import httpx
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from agent_platform.mcp.registry import (
    CHECK_SHIPPING_POLICY,
    ESTIMATE_ROUTE_COST,
    FIND_ROUTE_ALTERNATIVES,
    GET_PORT_STATUS,
    GET_SHIPMENT,
    REQUEST_REROUTE,
)
from agent_platform.models.tools import ToolResult
from contracts.routing import RouteConstraints
from mcp_server.backend.http import HttpLogisticsClient
from mcp_server.policy_slot import BasePolicySlot, PassthroughPolicySlot
from mcp_server.registry import build_http_backend, build_pipeline, tool_timeout
from mcp_server.settings import McpServerSettings


def create_mcp(
    backend: HttpLogisticsClient | None = None,
    policy_slot: BasePolicySlot | None = None,
    *,
    settings: McpServerSettings | None = None,
) -> FastMCP:
    """Create and register the FastMCP server with six logistics tools.

    Parameters:
        backend: Optional backend client override for tests.
        policy_slot: Optional policy slot override for tests.
        settings: Optional settings override; defaults to McpServerSettings().

    Returns:
        Configured FastMCP server instance.
    """
    resolved_settings = settings or McpServerSettings()
    resolved_backend = backend or build_http_backend(resolved_settings.logistics_api_url)
    pipeline = build_pipeline(resolved_backend, policy_slot or PassthroughPolicySlot())

    mcp = FastMCP(name="mcp-gateway")

    read_only = ToolAnnotations(read_only_hint=True)
    write_reroute = ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
    )

    @mcp.tool(name=GET_SHIPMENT, annotations=read_only, timeout=tool_timeout(GET_SHIPMENT))
    async def get_shipment_tool(shipment_id: str) -> ToolResult[Any]:
        """Return one shipment by id."""
        return await pipeline.run(GET_SHIPMENT, {"shipment_id": shipment_id})

    @mcp.tool(name=GET_PORT_STATUS, annotations=read_only, timeout=tool_timeout(GET_PORT_STATUS))
    async def get_port_status_tool(port_code: str) -> ToolResult[Any]:
        """Return current status for one port."""
        return await pipeline.run(GET_PORT_STATUS, {"port_code": port_code})

    @mcp.tool(
        name=FIND_ROUTE_ALTERNATIVES,
        annotations=read_only,
        timeout=tool_timeout(FIND_ROUTE_ALTERNATIVES),
    )
    async def find_route_alternatives_tool(
        shipment_id: str,
        max_additional_cost_eur: float | None = None,
        max_delay_hours: float | None = None,
        require_capacity: bool = True,
        max_results: int = 5,
    ) -> ToolResult[Any]:
        """Search route alternatives for a shipment."""
        constraints = RouteConstraints(
            max_additional_cost_eur=max_additional_cost_eur,
            max_delay_hours=max_delay_hours,
            require_capacity=require_capacity,
            max_results=max_results,
        )
        return await pipeline.run(
            FIND_ROUTE_ALTERNATIVES,
            {
                "shipment_id": shipment_id,
                "constraints": constraints.model_dump(mode="json"),
            },
        )

    @mcp.tool(
        name=ESTIMATE_ROUTE_COST,
        annotations=read_only,
        timeout=tool_timeout(ESTIMATE_ROUTE_COST),
    )
    async def estimate_route_cost_tool(
        shipment_id: str,
        route_id: str,
    ) -> ToolResult[Any]:
        """Estimate additional cost for a shipment route."""
        return await pipeline.run(
            ESTIMATE_ROUTE_COST,
            {"shipment_id": shipment_id, "route_id": route_id},
        )

    @mcp.tool(
        name=CHECK_SHIPPING_POLICY,
        annotations=read_only,
        timeout=tool_timeout(CHECK_SHIPPING_POLICY),
    )
    async def check_shipping_policy_tool(
        shipment_id: str,
        route_id: str,
    ) -> ToolResult[Any]:
        """Check business shipping policy for a shipment and route."""
        return await pipeline.run(
            CHECK_SHIPPING_POLICY,
            {"shipment_id": shipment_id, "route_id": route_id},
        )

    @mcp.tool(
        name=REQUEST_REROUTE,
        annotations=write_reroute,
        timeout=tool_timeout(REQUEST_REROUTE),
    )
    async def request_reroute_tool(
        shipment_id: str,
        route_id: str,
        expected_additional_cost_eur: float,
        idempotency_key: str,
        approval_id: str,
    ) -> ToolResult[Any]:
        """Request a reroute action for a shipment."""
        return await pipeline.run(
            REQUEST_REROUTE,
            {
                "shipment_id": shipment_id,
                "route_id": route_id,
                "expected_additional_cost_eur": expected_additional_cost_eur,
                "idempotency_key": idempotency_key,
                "approval_id": approval_id,
            },
        )

    return mcp


def run_http(settings: McpServerSettings | None = None) -> None:
    """Run the MCP gateway over HTTP for local development.

    Parameters:
        settings: Optional settings override.
    """
    resolved_settings = settings or McpServerSettings()
    server = create_mcp(settings=resolved_settings)
    server.run(transport="http", host=resolved_settings.host, port=resolved_settings.port)


def create_test_backend(app: Any) -> HttpLogisticsClient:
    """Create an in-process HTTP backend for tests.

    Parameters:
        app: ASGI app, typically from create_app().

    Returns:
        HttpLogisticsClient using ASGITransport.
    """
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return HttpLogisticsClient(client)

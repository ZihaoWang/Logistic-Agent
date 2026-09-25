"""Integration tests for the in-memory MCP client."""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, cast

import pytest

from agent_platform.mcp.client import McpClient
from agent_platform.mcp.protocol import BACKEND_NOT_FOUND, CONTRACT_INPUT_INVALID
from agent_platform.mcp.registry import (
    CHECK_SHIPPING_POLICY,
    ESTIMATE_ROUTE_COST,
    FIND_ROUTE_ALTERNATIVES,
    GET_SHIPMENT,
    REQUEST_REROUTE,
)
from apps.logistics_api.main import create_app
from apps.logistics_api.repository import InMemoryLogisticsRepository
from mcp_server.server import create_mcp, create_test_backend

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture
def repo() -> InMemoryLogisticsRepository:
    """Return a fresh repository for each test."""
    return InMemoryLogisticsRepository.from_data_dir(DATA_DIR)


@pytest.fixture
async def mcp_client(repo: InMemoryLogisticsRepository) -> AsyncGenerator[McpClient, None]:
    """Return an MCP client wired to an in-process logistics-api."""
    app = create_app(repo=repo)
    backend = create_test_backend(app)
    server = create_mcp(backend=backend)
    yield McpClient(server)


async def test_mcp_client_lists_all_six_tools(mcp_client: McpClient) -> None:
    tools = await mcp_client.list_tools()
    assert len(tools) == 6
    assert GET_SHIPMENT in tools
    assert REQUEST_REROUTE in tools


async def test_mcp_client_get_shipment_success(mcp_client: McpClient) -> None:
    result = await mcp_client.call(GET_SHIPMENT, {"shipment_id": "ABC123"})
    assert result.status == "success"
    data = cast(dict[str, Any], result.data)
    assert data["shipment"]["shipment_id"] == "ABC123"
    assert data["shipment"]["status"] == "delayed"


async def test_mcp_client_find_routes_demo_constraint(mcp_client: McpClient) -> None:
    result = await mcp_client.call(
        FIND_ROUTE_ALTERNATIVES,
        {
            "shipment_id": "ABC123",
            "max_additional_cost_eur": 2000,
            "max_delay_hours": 24,
            "require_capacity": True,
            "max_results": 10,
        },
    )
    assert result.status == "success"
    data = cast(dict[str, Any], result.data)
    route_ids = [route["route_id"] for route in data["routes"]]
    assert route_ids == ["R-102"]


async def test_mcp_client_estimate_route_cost(mcp_client: McpClient) -> None:
    result = await mcp_client.call(
        ESTIMATE_ROUTE_COST,
        {"shipment_id": "ABC123", "route_id": "R-102"},
    )
    assert result.status == "success"
    data = cast(dict[str, Any], result.data)
    assert data["estimate"]["additional_cost"] == 1450


async def test_mcp_client_check_shipping_policy_denied_business_rule(
    mcp_client: McpClient,
) -> None:
    result = await mcp_client.call(
        CHECK_SHIPPING_POLICY,
        {"shipment_id": "GHI789", "route_id": "R-401"},
    )
    assert result.status == "success"
    data = cast(dict[str, Any], result.data)
    assert data["result"]["allowed"] is False


async def test_mcp_client_request_reroute_is_idempotent(mcp_client: McpClient) -> None:
    arguments = {
        "shipment_id": "ABC123",
        "route_id": "R-102",
        "expected_additional_cost_eur": 1450.0,
        "idempotency_key": "key-mcp-001",
        "approval_id": "apr-test",
    }
    first = await mcp_client.call(REQUEST_REROUTE, arguments)
    second = await mcp_client.call(REQUEST_REROUTE, arguments)

    assert first.status == "success"
    assert second.status == "success"
    first_data = cast(dict[str, Any], first.data)
    second_data = cast(dict[str, Any], second.data)
    assert first_data["result"]["action_id"] == second_data["result"]["action_id"]
    assert first_data["result"]["status"] == "accepted"
    assert second_data["result"]["status"] == "already_applied"


async def test_mcp_client_unknown_shipment_returns_backend_not_found(
    mcp_client: McpClient,
) -> None:
    result = await mcp_client.call(GET_SHIPMENT, {"shipment_id": "UNKNOWN"})
    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == BACKEND_NOT_FOUND


async def test_mcp_client_rejects_empty_shipment_id(mcp_client: McpClient) -> None:
    result = await mcp_client.call(GET_SHIPMENT, {"shipment_id": ""})
    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == CONTRACT_INPUT_INVALID

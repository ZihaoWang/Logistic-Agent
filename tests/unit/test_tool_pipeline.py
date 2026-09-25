"""Unit tests for the MCP tool pipeline."""

from typing import Any

from pydantic import BaseModel

from agent_platform.mcp.protocol import (
    BACKEND_NOT_FOUND,
    CONTRACT_INPUT_INVALID,
    CONTRACT_OUTPUT_INVALID,
    build_metadata,
)
from agent_platform.mcp.registry import ESTIMATE_ROUTE_COST, GET_SHIPMENT
from agent_platform.models.execution import ExecutionContext
from agent_platform.models.tools import ToolResult
from contracts.routing import EstimateCostInput, EstimateCostOutput
from mcp_server.backend.base import BackendCallError
from mcp_server.pipeline import ToolPipeline
from mcp_server.policy_slot import PassthroughPolicySlot
from mcp_server.tools.estimate_cost import EstimateCostTool
from mcp_server.tools.get_shipment import GetShipmentTool


class FakeBackend:
    """Configurable fake backend for pipeline tests."""

    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    async def get_shipment(self, shipment_id: str) -> dict[str, Any]:
        self.calls.append("get_shipment")
        response = self.responses.get("get_shipment")
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, dict):
            msg = "fake backend missing get_shipment response"
            raise RuntimeError(msg)
        return response

    async def get_port_status(self, port_code: str) -> dict[str, Any]:
        self.calls.append("get_port_status")
        response = self.responses.get("get_port_status")
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, dict):
            msg = "fake backend missing get_port_status response"
            raise RuntimeError(msg)
        return response

    async def find_routes(self, shipment_id: str, constraints: Any = None) -> dict[str, Any]:
        self.calls.append("find_routes")
        response = self.responses.get("find_routes")
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, dict):
            msg = "fake backend missing find_routes response"
            raise RuntimeError(msg)
        return response

    async def estimate_cost(self, shipment_id: str, route_id: str) -> dict[str, Any]:
        self.calls.append("estimate_cost")
        response = self.responses.get("estimate_cost")
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, dict):
            msg = "fake backend missing estimate_cost response"
            raise RuntimeError(msg)
        return response

    async def check_shipping_policy(self, shipment_id: str, route_id: str) -> dict[str, Any]:
        self.calls.append("check_shipping_policy")
        response = self.responses.get("check_shipping_policy")
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, dict):
            msg = "fake backend missing check_shipping_policy response"
            raise RuntimeError(msg)
        return response

    async def request_reroute(self, shipment_id: str, body: Any) -> dict[str, Any]:
        self.calls.append("request_reroute")
        response = self.responses.get("request_reroute")
        if isinstance(response, Exception):
            raise response
        if not isinstance(response, dict):
            msg = "fake backend missing request_reroute response"
            raise RuntimeError(msg)
        return response


class DenyPolicySlot:
    """Policy slot that always denies before backend calls."""

    async def check(
        self,
        tool_name: str,
        arguments: BaseModel,
        context: ExecutionContext | None = None,
    ) -> ToolResult[Any] | None:
        _ = (arguments, context)
        return ToolResult[Any](
            status="denied",
            data=None,
            error=None,
            approval=None,
            metadata=build_metadata(tool_name, 0),
        )

    async def record_success(
        self,
        tool_name: str,
        arguments: BaseModel,
        context: ExecutionContext | None = None,
    ) -> None:
        _ = (tool_name, arguments, context)


async def test_cost_contract_rejects_renamed_field_via_pipeline() -> None:
    backend = FakeBackend(
        {
            "estimate_cost": {
                "estimate": {
                    "currency": "EUR",
                    "cost": 1450,
                    "estimate_version": "v1",
                }
            }
        }
    )
    pipeline = ToolPipeline(
        tools={ESTIMATE_ROUTE_COST: EstimateCostTool(backend)},
        policy_slot=PassthroughPolicySlot(),
    )
    result = await pipeline.run(
        ESTIMATE_ROUTE_COST,
        {"shipment_id": "ABC123", "route_id": "R-102"},
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == CONTRACT_OUTPUT_INVALID


async def test_pipeline_maps_backend_404() -> None:
    backend = FakeBackend(
        {"get_shipment": BackendCallError(status_code=404, body={"detail": "missing"})}
    )
    pipeline = ToolPipeline(
        tools={GET_SHIPMENT: GetShipmentTool(backend)},
        policy_slot=PassthroughPolicySlot(),
    )
    result = await pipeline.run(GET_SHIPMENT, {"shipment_id": "UNKNOWN"})

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == BACKEND_NOT_FOUND


async def test_pipeline_rejects_invalid_input() -> None:
    backend = FakeBackend({})
    pipeline = ToolPipeline(
        tools={GET_SHIPMENT: GetShipmentTool(backend)},
        policy_slot=PassthroughPolicySlot(),
    )
    result = await pipeline.run(GET_SHIPMENT, {"shipment_id": ""})

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == CONTRACT_INPUT_INVALID
    assert backend.calls == []


async def test_policy_slot_denies_before_backend_call() -> None:
    backend = FakeBackend(
        {
            "estimate_cost": EstimateCostOutput.model_validate(
                {
                    "estimate": {
                        "currency": "EUR",
                        "additional_cost": 1450,
                        "estimate_version": "v1",
                    }
                }
            ).model_dump(mode="json")
        }
    )
    pipeline = ToolPipeline(
        tools={ESTIMATE_ROUTE_COST: EstimateCostTool(backend)},
        policy_slot=DenyPolicySlot(),
    )
    result = await pipeline.run(
        ESTIMATE_ROUTE_COST,
        EstimateCostInput(shipment_id="ABC123", route_id="R-102").model_dump(),
    )

    assert result.status == "denied"
    assert backend.calls == []

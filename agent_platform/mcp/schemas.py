"""MCP tool input and output schemas."""

from pydantic import BaseModel, Field

from contracts.backend import RerouteResult
from contracts.routing import PortStatus
from contracts.shipment import Shipment


class GetShipmentInput(BaseModel):
    """Input for the get_shipment MCP tool.

    Usage:
        Passed by MCP clients to fetch one shipment.

    Fields:
        shipment_id: Required shipment identifier.
    """

    shipment_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Shipment identifier.",
    )


class GetShipmentOutput(BaseModel):
    """Output for the get_shipment MCP tool.

    Usage:
        Returned inside ToolResult.data on success.

    Fields:
        shipment: Required shipment domain object.
    """

    shipment: Shipment = Field(
        ...,
        description="Required. Shipment domain object.",
    )


class GetPortStatusInput(BaseModel):
    """Input for the get_port_status MCP tool.

    Usage:
        Passed by MCP clients to fetch one port status.

    Fields:
        port_code: Required port code identifier.
    """

    port_code: str = Field(
        ...,
        min_length=3,
        max_length=8,
        description="Required. Port code identifier.",
    )


class GetPortStatusOutput(BaseModel):
    """Output for the get_port_status MCP tool.

    Usage:
        Returned inside ToolResult.data on success.

    Fields:
        status: Required port status domain object.
    """

    status: PortStatus = Field(
        ...,
        description="Required. Port status domain object.",
    )


class RequestRerouteInput(BaseModel):
    """Input for the request_reroute MCP tool.

    Usage:
        Passed by MCP clients to request a reroute action.
        approval_id is required here but not sent to logistics-api in Phase 2.

    Fields:
        shipment_id: Required shipment identifier.
        route_id: Required route identifier.
        expected_additional_cost_eur: Required expected extra cost in EUR.
        idempotency_key: Required unique key for safe retries.
        approval_id: Required approval identifier for Phase 3 wiring.
    """

    shipment_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Shipment identifier.",
    )
    route_id: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Required. Route identifier.",
    )
    expected_additional_cost_eur: float = Field(
        ...,
        ge=0,
        description="Required. Expected additional cost in EUR.",
    )
    idempotency_key: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Required. Unique key to make reroute idempotent.",
    )
    approval_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Approval identifier for Phase 3 wiring.",
    )


class RequestRerouteOutput(BaseModel):
    """Output for the request_reroute MCP tool.

    Usage:
        Returned inside ToolResult.data on success.

    Fields:
        result: Required reroute action result.
    """

    result: RerouteResult = Field(
        ...,
        description="Required. Reroute action result.",
    )

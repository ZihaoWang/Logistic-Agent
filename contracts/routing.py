"""Route and port models for the logistics backend."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CongestionLevel = Literal["low", "medium", "high", "critical"]


class RouteOption(BaseModel):
    """An alternative route for a shipment.

    Usage:
        Returned by route search and used when estimating cost or checking
        shipping policy for a specific alternative.

    Fields:
        route_id: Required unique route identifier.
        via_ports: Required list of port codes the route passes through.
        eta: Required estimated arrival time for this route.
        additional_cost_eur: Required extra cost in EUR (must be >= 0).
        confidence: Required confidence score between 0 and 1.
        capacity_available: Required flag for whether capacity exists.
    """

    route_id: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Required. Unique route identifier.",
    )
    via_ports: list[str] = Field(
        ...,
        min_length=1,
        description="Required. Port codes the route passes through.",
    )
    eta: datetime = Field(
        ...,
        description="Required. Estimated arrival time for this route in UTC.",
    )
    additional_cost_eur: float = Field(
        ...,
        ge=0,
        description="Required. Extra cost in EUR for this route.",
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Required. Confidence score between 0 and 1.",
    )
    capacity_available: bool = Field(
        ...,
        description="Required. Whether capacity is available on this route.",
    )


class PortStatus(BaseModel):
    """Current status of a port.

    Usage:
        Returned by GET /v1/ports/{port_code}/status.

    Fields:
        port_code: Required port code identifier.
        congestion_level: Required congestion level at the port.
        delay_hours: Required average delay in hours (must be >= 0).
        disruption_reason: Optional human-readable reason for disruption.
        updated_at: Required timestamp of the last status update.
    """

    port_code: str = Field(
        ...,
        min_length=3,
        max_length=8,
        description="Required. Port code identifier.",
    )
    congestion_level: CongestionLevel = Field(
        ...,
        description="Required. Current congestion level at the port.",
    )
    delay_hours: float = Field(
        ...,
        ge=0,
        description="Required. Average delay in hours at this port.",
    )
    disruption_reason: str | None = Field(
        default=None,
        max_length=256,
        description="Optional. Reason for disruption, if any.",
    )
    updated_at: datetime = Field(
        ...,
        description="Required. When this status was last updated in UTC.",
    )


class RouteConstraints(BaseModel):
    """Filters applied when searching for route alternatives.

    Usage:
        Nested inside FindRoutesInput to limit which routes are returned.

    Fields:
        max_additional_cost_eur: Optional maximum extra cost in EUR.
        max_delay_hours: Optional maximum delay from the planned ETA.
        require_capacity: Optional flag to require available capacity.
        max_results: Optional maximum number of routes to return.
    """

    max_additional_cost_eur: float | None = Field(
        default=None,
        ge=0,
        description="Optional. Maximum additional cost in EUR.",
    )
    max_delay_hours: float | None = Field(
        default=None,
        ge=0,
        description="Optional. Maximum delay in hours from the planned ETA.",
    )
    require_capacity: bool = Field(
        default=True,
        description="Optional. Whether routes must have available capacity; defaults to true.",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Optional. Maximum number of routes to return; defaults to 5.",
    )


class FindRoutesInput(BaseModel):
    """Request body for route search.

    Usage:
        POST /v1/routes/search

    Fields:
        shipment_id: Required shipment to find routes for.
        constraints: Optional search filters; defaults to RouteConstraints().
    """

    shipment_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Shipment to find routes for.",
    )
    constraints: RouteConstraints = Field(
        default_factory=RouteConstraints,
        description="Optional. Search constraints; defaults to empty filters.",
    )


class FindRoutesOutput(BaseModel):
    """Response body for route search.

    Usage:
        Returned by POST /v1/routes/search.

    Fields:
        shipment_id: Required shipment the routes belong to.
        routes: Required list of matching route alternatives (may be empty).
    """

    shipment_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Shipment the routes belong to.",
    )
    routes: list[RouteOption] = Field(
        default_factory=list,
        description="Required. Matching route alternatives.",
    )


class CostEstimate(BaseModel):
    """Cost estimate for a specific route.

    Usage:
        Nested inside EstimateCostOutput.

    Fields:
        currency: Optional currency code; defaults to EUR.
        additional_cost: Required additional cost amount (must be >= 0).
        estimate_version: Required version label for the estimate.
    """

    currency: Literal["EUR"] = Field(
        default="EUR",
        description="Optional. Currency code; defaults to EUR.",
    )
    additional_cost: float = Field(
        ...,
        ge=0,
        description="Required. Additional cost amount.",
    )
    estimate_version: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Required. Version label for the cost estimate.",
    )


class EstimateCostInput(BaseModel):
    """Request body for cost estimation.

    Usage:
        POST /v1/routes/cost

    Fields:
        shipment_id: Required shipment identifier.
        route_id: Required route identifier.
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


class EstimateCostOutput(BaseModel):
    """Response body for cost estimation.

    Usage:
        Returned by POST /v1/routes/cost.

    Fields:
        estimate: Required cost estimate for the route.
    """

    estimate: CostEstimate = Field(
        ...,
        description="Required. Cost estimate for the route.",
    )

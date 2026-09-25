"""Backend API request and response models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RerouteStatus = Literal["accepted", "already_applied"]


class ShippingPolicyResult(BaseModel):
    """Result of a business shipping policy check.

    Usage:
        Nested inside CheckShippingPolicyOutput. This is a business rule
        check, not the platform authorization engine from Phase 3.

    Fields:
        allowed: Required flag for whether the route is allowed.
        reasons: Required human-readable reasons for the decision.
        rule_ids: Required identifiers of rules that fired.
    """

    allowed: bool = Field(
        ...,
        description="Required. Whether the route is allowed for this shipment.",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Required. Human-readable reasons for the decision.",
    )
    rule_ids: list[str] = Field(
        default_factory=list,
        description="Required. Rule identifiers that fired.",
    )


class CheckShippingPolicyInput(BaseModel):
    """Request body for shipping policy check.

    Usage:
        POST /v1/policy/check

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


class CheckShippingPolicyOutput(BaseModel):
    """Response body for shipping policy check.

    Usage:
        Returned by POST /v1/policy/check.

    Fields:
        result: Required policy check result.
    """

    result: ShippingPolicyResult = Field(
        ...,
        description="Required. Policy check result.",
    )


class RerouteRequestBody(BaseModel):
    """Request body for rerouting a shipment.

    Usage:
        POST /v1/shipments/{shipment_id}/reroute

    Fields:
        route_id: Required route to reroute onto.
        idempotency_key: Required unique key (8-128 chars) for safe retries.
        expected_additional_cost_eur: Required expected cost; must match route.
    """

    route_id: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Required. Route to reroute onto.",
    )
    idempotency_key: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Required. Unique key to make reroute idempotent.",
    )
    expected_additional_cost_eur: float = Field(
        ...,
        ge=0,
        description="Required. Expected additional cost in EUR for the route.",
    )


class RerouteResult(BaseModel):
    """Result of a reroute action.

    Usage:
        Returned by POST /v1/shipments/{shipment_id}/reroute.

    Fields:
        action_id: Required unique action identifier.
        shipment_id: Required shipment that was rerouted.
        route_id: Required route that was applied.
        status: Required action status (accepted or already_applied).
        applied_at: Required timestamp when the action was first applied.
    """

    action_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Unique action identifier.",
    )
    shipment_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Shipment that was rerouted.",
    )
    route_id: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Required. Route that was applied.",
    )
    status: RerouteStatus = Field(
        ...,
        description="Required. Whether the action was newly applied or replayed.",
    )
    applied_at: datetime = Field(
        ...,
        description="Required. When the action was first applied in UTC.",
    )


class IdempotencyFingerprint(BaseModel):
    """Fingerprint stored with an idempotency key to detect conflicting retries.

    Usage:
        Stored internally by the repository when a reroute is accepted.
        Used to reject retries that reuse a key with different parameters.

    Fields:
        shipment_id: Required shipment identifier.
        route_id: Required route identifier.
        expected_additional_cost_eur: Required expected cost in EUR.
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

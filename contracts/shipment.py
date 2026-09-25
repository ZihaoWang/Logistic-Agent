"""Shipment domain models for the logistics backend."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ShipmentStatus = Literal["on_time", "delayed", "held", "rerouted", "delivered"]
ShipmentPriority = Literal["standard", "high", "critical"]


class Shipment(BaseModel):
    """Synthetic shipment tracked by the logistics backend.

    Usage:
        Returned by GET /v1/shipments/{shipment_id} and used as the core
        domain object for route search, policy checks, and reroutes.

    Fields:
        shipment_id: Required unique identifier (for example ABC123).
        origin: Required origin port code.
        destination: Required destination port code.
        current_port: Optional port where the shipment is now.
        status: Required current shipment status.
        planned_eta: Required originally planned arrival time.
        current_eta: Required current estimated arrival time.
        cargo_type: Required cargo category used by shipping policy rules.
        priority: Optional priority level; defaults to standard.
    """

    shipment_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Unique shipment identifier.",
    )
    origin: str = Field(
        ...,
        min_length=3,
        max_length=8,
        description="Required. Origin port code.",
    )
    destination: str = Field(
        ...,
        min_length=3,
        max_length=8,
        description="Required. Destination port code.",
    )
    current_port: str | None = Field(
        default=None,
        min_length=3,
        max_length=8,
        description="Optional. Port where the shipment is currently located.",
    )
    status: ShipmentStatus = Field(
        ...,
        description="Required. Current shipment status.",
    )
    planned_eta: datetime = Field(
        ...,
        description="Required. Originally planned arrival time in UTC.",
    )
    current_eta: datetime = Field(
        ...,
        description="Required. Current estimated arrival time in UTC.",
    )
    cargo_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Cargo category (for example general or temperature_controlled).",
    )
    priority: ShipmentPriority = Field(
        default="standard",
        description="Optional. Shipment priority level; defaults to standard.",
    )

"""Base repository protocol for the logistics API."""

from typing import Protocol

from contracts.backend import (
    IdempotencyFingerprint,
    RerouteResult,
    ShippingPolicyResult,
)
from contracts.routing import PortStatus, RouteConstraints, RouteOption
from contracts.shipment import Shipment


class BaseRepository(Protocol):
    """Storage interface for shipments, ports, routes, and reroute actions."""

    async def get_shipment(self, shipment_id: str) -> Shipment | None:
        """Return a shipment by id, or None if it does not exist."""

    async def get_port_status(self, port_code: str) -> PortStatus | None:
        """Return port status by code, or None if it does not exist."""

    async def find_routes(
        self,
        shipment_id: str,
        constraints: RouteConstraints | None = None,
    ) -> list[RouteOption]:
        """Return route alternatives for a shipment, filtered by constraints."""

    async def get_route(self, shipment_id: str, route_id: str) -> RouteOption | None:
        """Return a specific route for a shipment, or None if it does not exist."""

    async def check_shipping_policy(
        self,
        shipment_id: str,
        route_id: str,
    ) -> ShippingPolicyResult | None:
        """Evaluate business shipping policy. None if shipment or route is missing."""

    async def get_action_by_idempotency_key(self, key: str) -> RerouteResult | None:
        """Return a stored reroute result for an idempotency key, if any."""

    async def get_idempotency_fingerprint(self, key: str) -> IdempotencyFingerprint | None:
        """Return the fingerprint stored with an idempotency key, if any."""

    async def save_reroute(
        self,
        result: RerouteResult,
        key: str,
        fingerprint: IdempotencyFingerprint,
    ) -> None:
        """Persist a reroute result and its idempotency fingerprint."""

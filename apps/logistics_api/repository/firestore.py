"""Firestore repository stub for Phase 7."""

from contracts.backend import (
    IdempotencyFingerprint,
    RerouteResult,
    ShippingPolicyResult,
)
from contracts.routing import PortStatus, RouteConstraints, RouteOption
from contracts.shipment import Shipment


class FirestoreLogisticsRepository:
    """Stub for Phase 7 Firestore-backed idempotency storage."""

    async def get_shipment(self, shipment_id: str) -> Shipment | None:
        """Not implemented until Phase 7."""
        raise NotImplementedError("FirestoreLogisticsRepository is not implemented yet.")

    async def get_port_status(self, port_code: str) -> PortStatus | None:
        """Not implemented until Phase 7."""
        raise NotImplementedError("FirestoreLogisticsRepository is not implemented yet.")

    async def find_routes(
        self,
        shipment_id: str,
        constraints: RouteConstraints | None = None,
    ) -> list[RouteOption]:
        """Not implemented until Phase 7."""
        raise NotImplementedError("FirestoreLogisticsRepository is not implemented yet.")

    async def get_route(self, shipment_id: str, route_id: str) -> RouteOption | None:
        """Not implemented until Phase 7."""
        raise NotImplementedError("FirestoreLogisticsRepository is not implemented yet.")

    async def check_shipping_policy(
        self,
        shipment_id: str,
        route_id: str,
    ) -> ShippingPolicyResult | None:
        """Not implemented until Phase 7."""
        raise NotImplementedError("FirestoreLogisticsRepository is not implemented yet.")

    async def get_action_by_idempotency_key(self, key: str) -> RerouteResult | None:
        """Not implemented until Phase 7."""
        raise NotImplementedError("FirestoreLogisticsRepository is not implemented yet.")

    async def get_idempotency_fingerprint(self, key: str) -> IdempotencyFingerprint | None:
        """Not implemented until Phase 7."""
        raise NotImplementedError("FirestoreLogisticsRepository is not implemented yet.")

    async def save_reroute(
        self,
        result: RerouteResult,
        key: str,
        fingerprint: IdempotencyFingerprint,
    ) -> None:
        """Not implemented until Phase 7."""
        raise NotImplementedError("FirestoreLogisticsRepository is not implemented yet.")

"""In-memory repository backed by checked-in JSON data."""

from __future__ import annotations

import json
from pathlib import Path

from apps.logistics_api.repository.business import RouteSearch, ShippingPolicy
from contracts.backend import (
    IdempotencyFingerprint,
    RerouteResult,
    ShippingPolicyResult,
)
from contracts.routing import PortStatus, RouteConstraints, RouteOption
from contracts.shipment import Shipment


class InMemoryLogisticsRepository:
    """In-memory repository backed by checked-in JSON data."""

    def __init__(
        self,
        shipments: dict[str, Shipment],
        ports: dict[str, PortStatus],
        routes: dict[str, list[RouteOption]],
        idempotency_actions: dict[str, RerouteResult] | None = None,
        idempotency_fingerprints: dict[str, IdempotencyFingerprint] | None = None,
    ) -> None:
        """Initialize the repository with in-memory data.

        Parameters:
            shipments: Shipments keyed by shipment_id.
            ports: Port statuses keyed by port_code.
            routes: Route lists keyed by shipment_id.
            idempotency_actions: Optional stored reroute results by key.
            idempotency_fingerprints: Optional fingerprints by idempotency key.
        """
        self._shipments = shipments
        self._ports = ports
        self._routes = routes
        self._idempotency_actions = idempotency_actions or {}
        self._idempotency_fingerprints = idempotency_fingerprints or {}

    @classmethod
    def from_data_dir(cls, data_dir: Path) -> InMemoryLogisticsRepository:
        """Load shipments, ports, and routes from JSON files in data_dir.

        Usage:
            repo = InMemoryLogisticsRepository.from_data_dir(Path("data"))

        Parameters:
            data_dir: Directory containing shipments.json, ports.json, routes.json.

        Returns:
            A repository populated from the JSON files.
        """
        shipments_raw = json.loads((data_dir / "shipments.json").read_text(encoding="utf-8"))
        ports_raw = json.loads((data_dir / "ports.json").read_text(encoding="utf-8"))
        routes_raw = json.loads((data_dir / "routes.json").read_text(encoding="utf-8"))

        shipments = {item["shipment_id"]: Shipment.model_validate(item) for item in shipments_raw}
        ports = {item["port_code"]: PortStatus.model_validate(item) for item in ports_raw}

        routes: dict[str, list[RouteOption]] = {}
        for item in routes_raw:
            shipment_id = item["shipment_id"]
            route_fields = {key: value for key, value in item.items() if key != "shipment_id"}
            route = RouteOption.model_validate(route_fields)
            routes.setdefault(shipment_id, []).append(route)

        return cls(shipments=shipments, ports=ports, routes=routes)

    async def get_shipment(self, shipment_id: str) -> Shipment | None:
        """Return a shipment by id, or None if it does not exist."""
        return self._shipments.get(shipment_id)

    async def get_port_status(self, port_code: str) -> PortStatus | None:
        """Return port status by code, or None if it does not exist."""
        return self._ports.get(port_code)

    async def find_routes(
        self,
        shipment_id: str,
        constraints: RouteConstraints | None = None,
    ) -> list[RouteOption]:
        """Return route alternatives for a shipment, filtered by constraints."""
        shipment = self._shipments.get(shipment_id)
        if shipment is None:
            return []

        active_constraints = constraints or RouteConstraints()
        shipment_routes = self._routes.get(shipment_id, [])
        return RouteSearch.filter_routes(shipment, shipment_routes, active_constraints)

    async def get_route(self, shipment_id: str, route_id: str) -> RouteOption | None:
        """Return a specific route for a shipment, or None if it does not exist."""
        for route in self._routes.get(shipment_id, []):
            if route.route_id == route_id:
                return route
        return None

    async def check_shipping_policy(
        self,
        shipment_id: str,
        route_id: str,
    ) -> ShippingPolicyResult | None:
        """Evaluate business shipping policy. None if shipment or route is missing."""
        shipment = await self.get_shipment(shipment_id)
        if shipment is None:
            return None

        route = await self.get_route(shipment_id, route_id)
        if route is None:
            return None

        return ShippingPolicy.evaluate(shipment, route)

    async def get_action_by_idempotency_key(self, key: str) -> RerouteResult | None:
        """Return a stored reroute result for an idempotency key, if any."""
        return self._idempotency_actions.get(key)

    async def get_idempotency_fingerprint(self, key: str) -> IdempotencyFingerprint | None:
        """Return the fingerprint stored with an idempotency key, if any."""
        return self._idempotency_fingerprints.get(key)

    async def save_reroute(
        self,
        result: RerouteResult,
        key: str,
        fingerprint: IdempotencyFingerprint,
    ) -> None:
        """Persist a reroute result and its idempotency fingerprint."""
        self._idempotency_actions[key] = result
        self._idempotency_fingerprints[key] = fingerprint

    @property
    def applied_reroute_count(self) -> int:
        """Return the number of reroute actions stored in idempotency state."""
        return len(self._idempotency_actions)

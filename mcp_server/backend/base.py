"""Backend client protocol for logistics-api."""

from typing import Any, Protocol

from contracts.backend import RerouteRequestBody
from contracts.routing import RouteConstraints


class BackendCallError(Exception):
    """HTTP or transport failure from logistics-api.

    Usage:
        Raised by HttpLogisticsClient when the backend returns an error
        status or the transport fails.

    Fields:
        status_code: HTTP status code, or 0 for connection failures.
        body: Optional response body or error detail.
    """

    def __init__(self, status_code: int, body: Any | None = None) -> None:
        """Store the backend status code and optional body.

        Parameters:
            status_code: HTTP status code, or 0 for connection failures.
            body: Optional response body or error detail.
        """
        super().__init__(f"backend call failed with status {status_code}")
        self.status_code = status_code
        self.body = body


class BaseLogisticsClient(Protocol):
    """Protocol for calling logistics-api endpoints."""

    async def get_shipment(self, shipment_id: str) -> dict[str, Any]:
        """Fetch one shipment by id."""
        ...

    async def get_port_status(self, port_code: str) -> dict[str, Any]:
        """Fetch port status by port code."""
        ...

    async def find_routes(
        self,
        shipment_id: str,
        constraints: RouteConstraints | None = None,
    ) -> dict[str, Any]:
        """Search route alternatives for a shipment."""
        ...

    async def estimate_cost(self, shipment_id: str, route_id: str) -> dict[str, Any]:
        """Estimate additional cost for a route."""
        ...

    async def check_shipping_policy(self, shipment_id: str, route_id: str) -> dict[str, Any]:
        """Check business shipping policy for a shipment and route."""
        ...

    async def request_reroute(
        self,
        shipment_id: str,
        body: RerouteRequestBody,
    ) -> dict[str, Any]:
        """Request a reroute action for a shipment."""
        ...

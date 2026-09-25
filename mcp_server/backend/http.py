"""HTTP client for logistics-api."""

from typing import Any

import httpx

from contracts.backend import RerouteRequestBody
from contracts.routing import FindRoutesInput, RouteConstraints
from mcp_server.backend.base import BackendCallError


class HttpLogisticsClient:
    """Call logistics-api over HTTP with an injected httpx client."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Store the async HTTP client.

        Parameters:
            client: Configured httpx AsyncClient, often with ASGITransport in tests.
        """
        self._client = client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send one HTTP request and return JSON on success.

        Parameters:
            method: HTTP method.
            path: Request path.
            json: Optional JSON request body.

        Returns:
            Parsed JSON response body.

        Raises:
            BackendCallError: On transport failure or non-success HTTP status.
        """
        try:
            response = await self._client.request(method, path, json=json)
        except httpx.RequestError as exc:
            raise BackendCallError(status_code=0, body=str(exc)) from exc

        if response.status_code >= 400:
            body: Any
            try:
                body = response.json()
            except ValueError:
                body = response.text
            raise BackendCallError(status_code=response.status_code, body=body)

        parsed = response.json()
        if not isinstance(parsed, dict):
            raise BackendCallError(status_code=response.status_code, body=parsed)
        return parsed

    async def get_shipment(self, shipment_id: str) -> dict[str, Any]:
        """Fetch one shipment by id."""
        return await self._request("GET", f"/v1/shipments/{shipment_id}")

    async def get_port_status(self, port_code: str) -> dict[str, Any]:
        """Fetch port status by port code."""
        return await self._request("GET", f"/v1/ports/{port_code}/status")

    async def find_routes(
        self,
        shipment_id: str,
        constraints: RouteConstraints | None = None,
    ) -> dict[str, Any]:
        """Search route alternatives for a shipment."""
        payload = FindRoutesInput(
            shipment_id=shipment_id,
            constraints=constraints or RouteConstraints(),
        )
        return await self._request(
            "POST",
            "/v1/routes/search",
            json=payload.model_dump(mode="json"),
        )

    async def estimate_cost(self, shipment_id: str, route_id: str) -> dict[str, Any]:
        """Estimate additional cost for a route."""
        return await self._request(
            "POST",
            "/v1/routes/cost",
            json={"shipment_id": shipment_id, "route_id": route_id},
        )

    async def check_shipping_policy(self, shipment_id: str, route_id: str) -> dict[str, Any]:
        """Check business shipping policy for a shipment and route."""
        return await self._request(
            "POST",
            "/v1/policy/check",
            json={"shipment_id": shipment_id, "route_id": route_id},
        )

    async def request_reroute(
        self,
        shipment_id: str,
        body: RerouteRequestBody,
    ) -> dict[str, Any]:
        """Request a reroute action for a shipment."""
        return await self._request(
            "POST",
            f"/v1/shipments/{shipment_id}/reroute",
            json=body.model_dump(mode="json"),
        )

"""Adapters between logistics-api JSON and MCP output models."""

from typing import Any

from agent_platform.mcp.schemas import (
    GetPortStatusOutput,
    GetShipmentOutput,
    RequestRerouteInput,
    RequestRerouteOutput,
)
from contracts.backend import RerouteRequestBody, RerouteResult
from contracts.routing import PortStatus
from contracts.shipment import Shipment


class LogisticsAdapters:
    """Shape backend JSON into MCP output payloads."""

    @staticmethod
    def to_get_shipment_output(body: dict[str, Any]) -> dict[str, Any]:
        """Wrap a flat shipment body for GetShipmentOutput validation.

        Parameters:
            body: Flat shipment JSON from logistics-api.

        Returns:
            Dict suitable for GetShipmentOutput.model_validate.
        """
        return GetShipmentOutput(shipment=Shipment.model_validate(body)).model_dump(mode="json")

    @staticmethod
    def to_get_port_status_output(body: dict[str, Any]) -> dict[str, Any]:
        """Wrap a flat port status body for GetPortStatusOutput validation.

        Parameters:
            body: Flat port status JSON from logistics-api.

        Returns:
            Dict suitable for GetPortStatusOutput.model_validate.
        """
        return GetPortStatusOutput(status=PortStatus.model_validate(body)).model_dump(mode="json")

    @staticmethod
    def to_request_reroute_output(body: dict[str, Any]) -> dict[str, Any]:
        """Wrap a flat reroute result for RequestRerouteOutput validation.

        Parameters:
            body: Flat reroute result JSON from logistics-api.

        Returns:
            Dict suitable for RequestRerouteOutput.model_validate.
        """
        return RequestRerouteOutput(result=RerouteResult.model_validate(body)).model_dump(
            mode="json"
        )

    @staticmethod
    def to_reroute_request_body(arguments: RequestRerouteInput) -> RerouteRequestBody:
        """Strip approval_id before calling logistics-api.

        Parameters:
            arguments: Validated MCP reroute input.

        Returns:
            Backend request body without approval_id.
        """
        return RerouteRequestBody(
            route_id=arguments.route_id,
            idempotency_key=arguments.idempotency_key,
            expected_additional_cost_eur=arguments.expected_additional_cost_eur,
        )

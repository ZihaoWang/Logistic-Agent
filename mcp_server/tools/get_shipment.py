"""get_shipment MCP tool."""

from typing import Any

from pydantic import BaseModel

from agent_platform.mcp.adapters import LogisticsAdapters
from agent_platform.mcp.registry import GET_SHIPMENT
from agent_platform.mcp.schemas import GetShipmentInput, GetShipmentOutput
from mcp_server.backend.base import BaseLogisticsClient
from mcp_server.tools.base import BaseTool


class GetShipmentTool(BaseTool):
    """Fetch one shipment from logistics-api."""

    name = GET_SHIPMENT
    input_model = GetShipmentInput
    output_model = GetShipmentOutput

    def __init__(self, backend: BaseLogisticsClient) -> None:
        """Initialize the tool with a backend client."""
        super().__init__(backend)

    async def fetch(self, validated_input: BaseModel) -> dict[str, Any]:
        """Call GET /v1/shipments/{id} and wrap the shipment body."""
        arguments = GetShipmentInput.model_validate(validated_input)
        body = await self._backend.get_shipment(arguments.shipment_id)
        return LogisticsAdapters.to_get_shipment_output(body)

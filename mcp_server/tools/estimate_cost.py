"""estimate_route_cost MCP tool."""

from typing import Any

from pydantic import BaseModel

from agent_platform.mcp.registry import ESTIMATE_ROUTE_COST
from contracts.routing import EstimateCostInput, EstimateCostOutput
from mcp_server.backend.base import BaseLogisticsClient
from mcp_server.tools.base import BaseTool


class EstimateCostTool(BaseTool):
    """Estimate additional cost for a route."""

    name = ESTIMATE_ROUTE_COST
    input_model = EstimateCostInput
    output_model = EstimateCostOutput

    def __init__(self, backend: BaseLogisticsClient) -> None:
        """Initialize the tool with a backend client."""
        super().__init__(backend)

    async def fetch(self, validated_input: BaseModel) -> dict[str, Any]:
        """Call POST /v1/routes/cost and return the response body."""
        arguments = EstimateCostInput.model_validate(validated_input)
        return await self._backend.estimate_cost(arguments.shipment_id, arguments.route_id)

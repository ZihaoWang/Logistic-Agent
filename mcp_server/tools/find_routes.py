"""find_route_alternatives MCP tool."""

from typing import Any

from pydantic import BaseModel

from agent_platform.mcp.registry import FIND_ROUTE_ALTERNATIVES
from contracts.routing import FindRoutesInput, FindRoutesOutput
from mcp_server.backend.base import BaseLogisticsClient
from mcp_server.tools.base import BaseTool


class FindRoutesTool(BaseTool):
    """Search route alternatives for a shipment."""

    name = FIND_ROUTE_ALTERNATIVES
    input_model = FindRoutesInput
    output_model = FindRoutesOutput

    def __init__(self, backend: BaseLogisticsClient) -> None:
        """Initialize the tool with a backend client."""
        super().__init__(backend)

    async def fetch(self, validated_input: BaseModel) -> dict[str, Any]:
        """Call POST /v1/routes/search and return the response body."""
        arguments = FindRoutesInput.model_validate(validated_input)
        return await self._backend.find_routes(arguments.shipment_id, arguments.constraints)

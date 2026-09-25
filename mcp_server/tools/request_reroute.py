"""request_reroute MCP tool."""

from typing import Any

from pydantic import BaseModel

from agent_platform.mcp.adapters import LogisticsAdapters
from agent_platform.mcp.registry import REQUEST_REROUTE
from agent_platform.mcp.schemas import RequestRerouteInput, RequestRerouteOutput
from mcp_server.backend.base import BaseLogisticsClient
from mcp_server.tools.base import BaseTool


class RequestRerouteTool(BaseTool):
    """Request a reroute action for a shipment."""

    name = REQUEST_REROUTE
    input_model = RequestRerouteInput
    output_model = RequestRerouteOutput

    def __init__(self, backend: BaseLogisticsClient) -> None:
        """Initialize the tool with a backend client."""
        super().__init__(backend)

    async def fetch(self, validated_input: BaseModel) -> dict[str, Any]:
        """Call POST /v1/shipments/{id}/reroute and wrap the result."""
        arguments = RequestRerouteInput.model_validate(validated_input)
        request_body = LogisticsAdapters.to_reroute_request_body(arguments)
        body = await self._backend.request_reroute(arguments.shipment_id, request_body)
        return LogisticsAdapters.to_request_reroute_output(body)

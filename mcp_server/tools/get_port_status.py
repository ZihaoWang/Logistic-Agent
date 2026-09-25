"""get_port_status MCP tool."""

from typing import Any

from pydantic import BaseModel

from agent_platform.mcp.adapters import LogisticsAdapters
from agent_platform.mcp.registry import GET_PORT_STATUS
from agent_platform.mcp.schemas import GetPortStatusInput, GetPortStatusOutput
from mcp_server.backend.base import BaseLogisticsClient
from mcp_server.tools.base import BaseTool


class GetPortStatusTool(BaseTool):
    """Fetch one port status from logistics-api."""

    name = GET_PORT_STATUS
    input_model = GetPortStatusInput
    output_model = GetPortStatusOutput

    def __init__(self, backend: BaseLogisticsClient) -> None:
        """Initialize the tool with a backend client."""
        super().__init__(backend)

    async def fetch(self, validated_input: BaseModel) -> dict[str, Any]:
        """Call GET /v1/ports/{code}/status and wrap the port body."""
        arguments = GetPortStatusInput.model_validate(validated_input)
        body = await self._backend.get_port_status(arguments.port_code)
        return LogisticsAdapters.to_get_port_status_output(body)

"""check_shipping_policy MCP tool."""

from typing import Any

from pydantic import BaseModel

from agent_platform.mcp.registry import CHECK_SHIPPING_POLICY
from contracts.backend import CheckShippingPolicyInput, CheckShippingPolicyOutput
from mcp_server.backend.base import BaseLogisticsClient
from mcp_server.tools.base import BaseTool


class CheckPolicyTool(BaseTool):
    """Check business shipping policy for a shipment and route."""

    name = CHECK_SHIPPING_POLICY
    input_model = CheckShippingPolicyInput
    output_model = CheckShippingPolicyOutput

    def __init__(self, backend: BaseLogisticsClient) -> None:
        """Initialize the tool with a backend client."""
        super().__init__(backend)

    async def fetch(self, validated_input: BaseModel) -> dict[str, Any]:
        """Call POST /v1/policy/check and return the response body."""
        arguments = CheckShippingPolicyInput.model_validate(validated_input)
        return await self._backend.check_shipping_policy(
            arguments.shipment_id,
            arguments.route_id,
        )

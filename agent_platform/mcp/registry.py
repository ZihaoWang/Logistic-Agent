"""Static MCP tool registry with policies and model classes."""

from typing import Any

from pydantic import BaseModel, Field

from agent_platform.mcp.schemas import (
    GetPortStatusInput,
    GetPortStatusOutput,
    GetShipmentInput,
    GetShipmentOutput,
    RequestRerouteInput,
    RequestRerouteOutput,
)
from agent_platform.models.policy import RetryPolicy, ToolPolicy
from contracts.backend import CheckShippingPolicyInput, CheckShippingPolicyOutput
from contracts.routing import (
    EstimateCostInput,
    EstimateCostOutput,
    FindRoutesInput,
    FindRoutesOutput,
)

GET_SHIPMENT = "get_shipment"
GET_PORT_STATUS = "get_port_status"
FIND_ROUTE_ALTERNATIVES = "find_route_alternatives"
ESTIMATE_ROUTE_COST = "estimate_route_cost"
CHECK_SHIPPING_POLICY = "check_shipping_policy"
REQUEST_REROUTE = "request_reroute"


class RegisteredTool(BaseModel):
    """Metadata for one registered MCP tool.

    Usage:
        Stored in TOOL_REGISTRY with model classes kept outside Pydantic.

    Fields:
        name: Required MCP tool name.
        input_model_name: Required input model class name.
        output_model_name: Required output model class name.
        policy: Required tool policy metadata.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. MCP tool name.",
    )
    input_model_name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Input model class name.",
    )
    output_model_name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Output model class name.",
    )
    policy: ToolPolicy = Field(
        ...,
        description="Required. Tool policy metadata.",
    )


GET_SHIPMENT_POLICY = ToolPolicy(
    name=GET_SHIPMENT,
    risk="low",
    required_scopes={"shipment:read"},
    side_effect=False,
    requires_approval=False,
    idempotent=True,
    timeout_seconds=5,
)

GET_PORT_STATUS_POLICY = ToolPolicy(
    name=GET_PORT_STATUS,
    risk="low",
    required_scopes={"port:read"},
    side_effect=False,
    requires_approval=False,
    idempotent=True,
    timeout_seconds=5,
)

FIND_ROUTE_ALTERNATIVES_POLICY = ToolPolicy(
    name=FIND_ROUTE_ALTERNATIVES,
    risk="low",
    required_scopes={"route:read"},
    side_effect=False,
    requires_approval=False,
    idempotent=True,
    timeout_seconds=5,
)

ESTIMATE_ROUTE_COST_POLICY = ToolPolicy(
    name=ESTIMATE_ROUTE_COST,
    risk="low",
    required_scopes={"route:read"},
    side_effect=False,
    requires_approval=False,
    idempotent=True,
    timeout_seconds=5,
)

CHECK_SHIPPING_POLICY_POLICY = ToolPolicy(
    name=CHECK_SHIPPING_POLICY,
    risk="medium",
    required_scopes={"route:read"},
    side_effect=False,
    requires_approval=False,
    idempotent=True,
    timeout_seconds=5,
)

REQUEST_REROUTE_POLICY = ToolPolicy(
    name=REQUEST_REROUTE,
    risk="high",
    required_scopes={"shipment:write", "reroute:request"},
    side_effect=True,
    requires_approval=True,
    idempotent=True,
    timeout_seconds=10,
    retry=RetryPolicy(
        max_attempts=2,
        retry_on_5xx=True,
        retry_on_4xx=False,
    ),
)

TOOL_REGISTRY: dict[str, RegisteredTool] = {
    GET_SHIPMENT: RegisteredTool(
        name=GET_SHIPMENT,
        input_model_name="GetShipmentInput",
        output_model_name="GetShipmentOutput",
        policy=GET_SHIPMENT_POLICY,
    ),
    GET_PORT_STATUS: RegisteredTool(
        name=GET_PORT_STATUS,
        input_model_name="GetPortStatusInput",
        output_model_name="GetPortStatusOutput",
        policy=GET_PORT_STATUS_POLICY,
    ),
    FIND_ROUTE_ALTERNATIVES: RegisteredTool(
        name=FIND_ROUTE_ALTERNATIVES,
        input_model_name="FindRoutesInput",
        output_model_name="FindRoutesOutput",
        policy=FIND_ROUTE_ALTERNATIVES_POLICY,
    ),
    ESTIMATE_ROUTE_COST: RegisteredTool(
        name=ESTIMATE_ROUTE_COST,
        input_model_name="EstimateCostInput",
        output_model_name="EstimateCostOutput",
        policy=ESTIMATE_ROUTE_COST_POLICY,
    ),
    CHECK_SHIPPING_POLICY: RegisteredTool(
        name=CHECK_SHIPPING_POLICY,
        input_model_name="CheckShippingPolicyInput",
        output_model_name="CheckShippingPolicyOutput",
        policy=CHECK_SHIPPING_POLICY_POLICY,
    ),
    REQUEST_REROUTE: RegisteredTool(
        name=REQUEST_REROUTE,
        input_model_name="RequestRerouteInput",
        output_model_name="RequestRerouteOutput",
        policy=REQUEST_REROUTE_POLICY,
    ),
}

INPUT_MODELS: dict[str, type[BaseModel]] = {
    GET_SHIPMENT: GetShipmentInput,
    GET_PORT_STATUS: GetPortStatusInput,
    FIND_ROUTE_ALTERNATIVES: FindRoutesInput,
    ESTIMATE_ROUTE_COST: EstimateCostInput,
    CHECK_SHIPPING_POLICY: CheckShippingPolicyInput,
    REQUEST_REROUTE: RequestRerouteInput,
}

OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    GET_SHIPMENT: GetShipmentOutput,
    GET_PORT_STATUS: GetPortStatusOutput,
    FIND_ROUTE_ALTERNATIVES: FindRoutesOutput,
    ESTIMATE_ROUTE_COST: EstimateCostOutput,
    CHECK_SHIPPING_POLICY: CheckShippingPolicyOutput,
    REQUEST_REROUTE: RequestRerouteOutput,
}


def get_input_model(tool_name: str) -> type[BaseModel]:
    """Return the input model class for a tool name.

    Parameters:
        tool_name: Registered MCP tool name.

    Returns:
        Pydantic input model class.

    Raises:
        KeyError: When the tool name is unknown.
    """
    return INPUT_MODELS[tool_name]


def get_output_model(tool_name: str) -> type[BaseModel]:
    """Return the output model class for a tool name.

    Parameters:
        tool_name: Registered MCP tool name.

    Returns:
        Pydantic output model class.

    Raises:
        KeyError: When the tool name is unknown.
    """
    return OUTPUT_MODELS[tool_name]


def get_policy(tool_name: str) -> ToolPolicy:
    """Return the policy for a tool name.

    Parameters:
        tool_name: Registered MCP tool name.

    Returns:
        ToolPolicy for the tool.

    Raises:
        KeyError: When the tool name is unknown.
    """
    return TOOL_REGISTRY[tool_name].policy


def parse_tool_result_data(tool_name: str, data: Any) -> BaseModel:
    """Validate ToolResult.data against the tool output model.

    Parameters:
        tool_name: Registered MCP tool name.
        data: Raw data payload from a ToolResult.

    Returns:
        Validated output model instance.
    """
    output_model = get_output_model(tool_name)
    return output_model.model_validate(data)

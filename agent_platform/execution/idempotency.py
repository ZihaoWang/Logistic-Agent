"""Canonical argument hashing for approval binding."""

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from agent_platform.mcp.registry import REQUEST_REROUTE
from agent_platform.mcp.schemas import RequestRerouteInput


def hash_tool_arguments(tool_name: str, arguments: BaseModel) -> str:
    """Return a SHA-256 hash of canonical business arguments for one tool call.

    Parameters:
        tool_name: Registered MCP tool name.
        arguments: Validated tool input model.

    Returns:
        Hex-encoded SHA-256 digest of canonical JSON.
    """
    payload = _business_payload(tool_name, arguments)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _business_payload(tool_name: str, arguments: BaseModel) -> dict[str, Any]:
    """Extract the business-action fields that define one side-effect call."""
    if tool_name == REQUEST_REROUTE:
        reroute = RequestRerouteInput.model_validate(arguments)
        return {
            "shipment_id": reroute.shipment_id,
            "route_id": reroute.route_id,
            "expected_additional_cost_eur": reroute.expected_additional_cost_eur,
        }
    return arguments.model_dump(mode="json")

"""User-facing message templates for agent responses."""

from typing import Any

from agent_platform.mcp.protocol import (
    CONTRACT_OUTPUT_INVALID,
    REROUTE_COST_LIMIT,
    TOOL_TIMEOUT,
)
from agent_platform.models.errors import PlatformError
from agent_platform.models.tools import ToolResult


def message_for_tool_result(tool_name: str, result: ToolResult[Any]) -> str:
    """Return a safe user-facing message for a failed or denied tool result."""
    if result.status == "denied":
        return _message_for_denied(result.error)
    if result.status == "failed":
        return _message_for_failed(tool_name, result.error)
    return "Something went wrong while handling your request. No shipment change was made."


def message_for_approval_required(expected_cost_eur: float) -> str:
    """Return the user-facing approval-required message."""
    cost = _format_eur(expected_cost_eur)
    return (
        f"The route is valid and the expected additional cost is {cost}. "
        "Applying it changes the shipment, so I need your approval before I continue."
    )


def message_for_rejection() -> str:
    """Return the user-facing message when an approval is rejected."""
    return "The reroute was not applied. No shipment change was made."


def message_for_successful_reroute() -> str:
    """Return the user-facing message after a successful reroute."""
    return "The reroute was applied successfully."


def _message_for_denied(error: PlatformError | None) -> str:
    if error is None:
        return "I cannot execute this action. No shipment change was made."
    if error.code == REROUTE_COST_LIMIT:
        return (
            "I cannot execute this reroute because the additional cost "
            "is above the allowed limit."
        )
    if error.code == "POLICY_MISSING_SCOPE":
        return "I cannot execute this action because it is not permitted for this agent."
    return "I cannot execute this action. No shipment change was made."


def _message_for_failed(tool_name: str, error: PlatformError | None) -> str:
    if error is None:
        return "Something went wrong while handling your request. No shipment change was made."
    if error.code == TOOL_TIMEOUT or error.category == "timeout":
        return _timeout_message(tool_name)
    if error.category == "contract" or error.code == CONTRACT_OUTPUT_INVALID:
        return (
            "The route service returned an invalid response, so I stopped "
            "instead of using incomplete data."
        )
    return "Something went wrong while handling your request. No shipment change was made."


def _timeout_message(tool_name: str) -> str:
    if tool_name == "find_route_alternatives":
        return "I could not retrieve route alternatives in time. " "No shipment change was made."
    return "I could not complete the request in time. No shipment change was made."


def _format_eur(amount: float) -> str:
    if float(amount).is_integer():
        return f"EUR {int(amount):,}"
    return f"EUR {amount:,.2f}"

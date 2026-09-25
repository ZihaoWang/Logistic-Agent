"""Unit tests for user-facing runtime messages."""

from agent_platform.mcp.protocol import (
    CONTRACT_OUTPUT_INVALID,
    REROUTE_COST_LIMIT,
    TOOL_TIMEOUT,
    build_denied_result,
    build_error,
    build_failed_result,
)
from agent_platform.runtime.messages import (
    message_for_approval_required,
    message_for_tool_result,
)


def test_message_for_timeout_hides_internal_details() -> None:
    result = build_failed_result(
        "find_route_alternatives",
        12,
        build_error(TOOL_TIMEOUT, "timeout", "internal detail", retryable=True),
    )
    message = message_for_tool_result("find_route_alternatives", result)
    assert "internal detail" not in message
    assert "No shipment change was made." in message


def test_message_for_policy_denial() -> None:
    result = build_denied_result(
        "request_reroute",
        3,
        build_error(
            REROUTE_COST_LIMIT,
            "policy",
            "Reroute cost exceeds the allowed limit.",
            retryable=False,
        ),
    )
    message = message_for_tool_result("request_reroute", result)
    assert "above the allowed limit" in message


def test_message_for_contract_failure() -> None:
    result = build_failed_result(
        "find_route_alternatives",
        4,
        build_error(
            CONTRACT_OUTPUT_INVALID,
            "contract",
            "validation failed",
            retryable=False,
        ),
    )
    message = message_for_tool_result("find_route_alternatives", result)
    assert "invalid response" in message
    assert "validation failed" not in message


def test_message_for_approval_required_includes_cost() -> None:
    message = message_for_approval_required(1450.0)
    assert "EUR 1,450" in message
    assert "approval" in message.lower()

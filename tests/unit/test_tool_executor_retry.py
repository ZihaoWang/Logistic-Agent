"""Unit tests for governed tool executor retry behavior."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from agent_platform.mcp.protocol import (
    BACKEND_UNAVAILABLE,
    CONTRACT_OUTPUT_INVALID,
    build_error,
    build_failed_result,
    build_success_result,
)
from agent_platform.models.execution import ExecutionContext
from agent_platform.runtime.tool_executor import GovernedToolExecutor
from tests.policy.helpers import build_context


@pytest.fixture
def context() -> ExecutionContext:
    return build_context()


def _executor_with_results(results: list[Any]) -> tuple[GovernedToolExecutor, AsyncMock]:
    mock_call = AsyncMock(side_effect=results)
    client = AsyncMock()
    client.call = mock_call
    return GovernedToolExecutor(client), mock_call


async def test_retries_5xx_then_succeeds(context: ExecutionContext) -> None:
    executor, mock_call = _executor_with_results(
        [
            build_failed_result(
                "get_shipment",
                10,
                build_error(
                    BACKEND_UNAVAILABLE,
                    "transport",
                    "backend down",
                    retryable=True,
                    details={"status_code": 503},
                ),
            ),
            build_success_result("get_shipment", 12, {"shipment": {"shipment_id": "ABC123"}}),
        ],
    )

    outcome = await executor.execute("get_shipment", {"shipment_id": "ABC123"}, context)
    assert outcome.result.status == "success"
    assert mock_call.await_count == 2


async def test_retries_429_then_succeeds(context: ExecutionContext) -> None:
    executor, _mock_call = _executor_with_results(
        [
            build_failed_result(
                "get_shipment",
                10,
                build_error(
                    BACKEND_UNAVAILABLE,
                    "transport",
                    "rate limited",
                    retryable=True,
                    details={"status_code": 429},
                ),
            ),
            build_success_result("get_shipment", 12, {"shipment": {"shipment_id": "ABC123"}}),
        ],
    )

    outcome = await executor.execute("get_shipment", {"shipment_id": "ABC123"}, context)
    assert outcome.result.status == "success"


async def test_does_not_retry_contract_error(context: ExecutionContext) -> None:
    executor, mock_call = _executor_with_results(
        [
            build_failed_result(
                "get_shipment",
                10,
                build_error(
                    CONTRACT_OUTPUT_INVALID,
                    "contract",
                    "bad output",
                    retryable=False,
                ),
            ),
            build_success_result("get_shipment", 12, {"shipment": {"shipment_id": "ABC123"}}),
        ],
    )

    outcome = await executor.execute("get_shipment", {"shipment_id": "ABC123"}, context)
    assert outcome.result.status == "failed"
    assert mock_call.await_count == 1


async def test_does_not_retry_policy_denial(context: ExecutionContext) -> None:
    from agent_platform.mcp.protocol import build_denied_result

    executor, mock_call = _executor_with_results(
        [
            build_denied_result(
                "request_reroute",
                3,
                build_error(
                    "POLICY_MISSING_SCOPE",
                    "policy",
                    "missing scope",
                    retryable=False,
                ),
            ),
        ],
    )

    outcome = await executor.execute(
        "request_reroute",
        {
            "shipment_id": "ABC123",
            "route_id": "R-102",
            "expected_additional_cost_eur": 1450.0,
        },
        context,
    )
    assert outcome.result.status == "denied"
    assert mock_call.await_count == 1

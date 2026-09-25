"""Contract tests for request_reroute MCP schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from agent_platform.mcp.schemas import RequestRerouteInput, RequestRerouteOutput
from contracts.backend import RerouteResult


def test_request_reroute_input_accepts_valid_fixture() -> None:
    model = RequestRerouteInput.model_validate(
        {
            "shipment_id": "ABC123",
            "route_id": "R-102",
            "expected_additional_cost_eur": 1450.0,
            "idempotency_key": "key-abc-123",
            "approval_id": "apr-test-1",
        }
    )
    assert model.approval_id == "apr-test-1"


def test_request_reroute_input_rejects_missing_approval_id() -> None:
    with pytest.raises(ValidationError):
        RequestRerouteInput.model_validate(
            {
                "shipment_id": "ABC123",
                "route_id": "R-102",
                "expected_additional_cost_eur": 1450.0,
                "idempotency_key": "key-abc-123",
            }
        )


def test_request_reroute_output_accepts_valid_fixture() -> None:
    result = RerouteResult(
        action_id="act-1",
        shipment_id="ABC123",
        route_id="R-102",
        status="accepted",
        applied_at=datetime(2026, 9, 25, 10, 0, tzinfo=UTC),
    )
    output = RequestRerouteOutput.model_validate({"result": result.model_dump(mode="json")})
    assert output.result.status == "accepted"


def test_request_reroute_output_rejects_flat_body() -> None:
    with pytest.raises(ValidationError):
        RequestRerouteOutput.model_validate(
            {
                "action_id": "act-1",
                "shipment_id": "ABC123",
                "route_id": "R-102",
                "status": "accepted",
                "applied_at": "2026-09-25T10:00:00Z",
            }
        )

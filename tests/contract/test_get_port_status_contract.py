"""Contract tests for get_port_status MCP schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from agent_platform.mcp.schemas import GetPortStatusInput, GetPortStatusOutput
from contracts.routing import PortStatus


def test_get_port_status_input_accepts_valid_fixture() -> None:
    model = GetPortStatusInput.model_validate({"port_code": "NLRTM"})
    assert model.port_code == "NLRTM"


def test_get_port_status_input_rejects_short_code() -> None:
    with pytest.raises(ValidationError):
        GetPortStatusInput.model_validate({"port_code": "AB"})


def test_get_port_status_output_accepts_valid_fixture() -> None:
    status = PortStatus(
        port_code="NLRTM",
        congestion_level="high",
        delay_hours=12.0,
        disruption_reason="container backlog",
        updated_at=datetime(2026, 9, 25, 8, 0, tzinfo=UTC),
    )
    output = GetPortStatusOutput.model_validate({"status": status.model_dump(mode="json")})
    assert output.status.port_code == "NLRTM"


def test_get_port_status_output_rejects_flat_body() -> None:
    with pytest.raises(ValidationError):
        GetPortStatusOutput.model_validate(
            {
                "port_code": "NLRTM",
                "congestion_level": "high",
                "delay_hours": 12.0,
                "updated_at": "2026-09-25T08:00:00Z",
            }
        )

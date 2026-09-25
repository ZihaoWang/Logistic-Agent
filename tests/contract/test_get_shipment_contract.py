"""Contract tests for get_shipment MCP schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from agent_platform.mcp.schemas import GetShipmentInput, GetShipmentOutput
from contracts.shipment import Shipment


def test_get_shipment_input_accepts_valid_fixture() -> None:
    model = GetShipmentInput.model_validate({"shipment_id": "ABC123"})
    assert model.shipment_id == "ABC123"


def test_get_shipment_input_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        GetShipmentInput.model_validate({"shipment_id": ""})


def test_get_shipment_output_accepts_valid_fixture() -> None:
    shipment = Shipment(
        shipment_id="ABC123",
        origin="CNSHA",
        destination="DKCPH",
        current_port="NLRTM",
        status="delayed",
        planned_eta=datetime(2026, 9, 27, 10, 0, tzinfo=UTC),
        current_eta=datetime(2026, 9, 28, 14, 0, tzinfo=UTC),
        cargo_type="general",
        priority="high",
    )
    output = GetShipmentOutput.model_validate({"shipment": shipment.model_dump(mode="json")})
    assert output.shipment.shipment_id == "ABC123"


def test_get_shipment_output_rejects_missing_wrapper() -> None:
    with pytest.raises(ValidationError):
        GetShipmentOutput.model_validate(
            {
                "shipment_id": "ABC123",
                "origin": "CNSHA",
                "destination": "DKCPH",
                "status": "delayed",
            }
        )

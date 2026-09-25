"""Contract tests for estimate_route_cost MCP schemas."""

import pytest
from pydantic import ValidationError

from contracts.routing import EstimateCostInput, EstimateCostOutput


def test_estimate_cost_input_accepts_valid_fixture() -> None:
    model = EstimateCostInput.model_validate({"shipment_id": "ABC123", "route_id": "R-102"})
    assert model.route_id == "R-102"


def test_estimate_cost_input_rejects_missing_route_id() -> None:
    with pytest.raises(ValidationError):
        EstimateCostInput.model_validate({"shipment_id": "ABC123"})


def test_estimate_cost_output_accepts_valid_fixture() -> None:
    output = EstimateCostOutput.model_validate(
        {
            "estimate": {
                "currency": "EUR",
                "additional_cost": 1450,
                "estimate_version": "v1",
            }
        }
    )
    assert output.estimate.additional_cost == 1450


def test_cost_contract_rejects_renamed_field() -> None:
    response = {
        "estimate": {
            "currency": "EUR",
            "cost": 1450,
            "estimate_version": "v1",
        }
    }
    with pytest.raises(ValidationError):
        EstimateCostOutput.model_validate(response)

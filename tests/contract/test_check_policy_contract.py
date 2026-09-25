"""Contract tests for check_shipping_policy MCP schemas."""

import pytest
from pydantic import ValidationError

from contracts.backend import CheckShippingPolicyInput, CheckShippingPolicyOutput


def test_check_policy_input_accepts_valid_fixture() -> None:
    model = CheckShippingPolicyInput.model_validate({"shipment_id": "GHI789", "route_id": "R-401"})
    assert model.shipment_id == "GHI789"


def test_check_policy_input_rejects_empty_shipment_id() -> None:
    with pytest.raises(ValidationError):
        CheckShippingPolicyInput.model_validate({"shipment_id": "", "route_id": "R-401"})


def test_check_policy_output_accepts_valid_fixture() -> None:
    output = CheckShippingPolicyOutput.model_validate(
        {
            "result": {
                "allowed": False,
                "reasons": ["temperature-controlled cargo cannot transit BEANR"],
                "rule_ids": ["temp-controlled-beanr"],
            }
        }
    )
    assert output.result.allowed is False


def test_check_policy_output_rejects_flat_result_body() -> None:
    with pytest.raises(ValidationError):
        CheckShippingPolicyOutput.model_validate(
            {
                "allowed": False,
                "reasons": ["denied"],
                "rule_ids": ["temp-controlled-beanr"],
            }
        )

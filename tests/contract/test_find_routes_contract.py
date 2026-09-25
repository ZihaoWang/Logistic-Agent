"""Contract tests for find_route_alternatives MCP schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from contracts.routing import FindRoutesInput, FindRoutesOutput, RouteConstraints, RouteOption


def test_find_routes_input_accepts_valid_fixture() -> None:
    model = FindRoutesInput.model_validate(
        {
            "shipment_id": "ABC123",
            "constraints": {
                "max_additional_cost_eur": 2000,
                "max_delay_hours": 24,
            },
        }
    )
    assert model.shipment_id == "ABC123"
    assert model.constraints.max_additional_cost_eur == 2000


def test_find_routes_input_rejects_missing_shipment_id() -> None:
    with pytest.raises(ValidationError):
        FindRoutesInput.model_validate({"constraints": RouteConstraints().model_dump()})


def test_find_routes_output_accepts_valid_fixture() -> None:
    route = RouteOption(
        route_id="R-102",
        via_ports=["NLRTM", "DEHAM"],
        eta=datetime(2026, 9, 28, 12, 0, tzinfo=UTC),
        additional_cost_eur=1450.0,
        confidence=0.91,
        capacity_available=True,
    )
    output = FindRoutesOutput.model_validate(
        {"shipment_id": "ABC123", "routes": [route.model_dump(mode="json")]}
    )
    assert output.routes[0].route_id == "R-102"


def test_find_routes_output_rejects_renamed_route_field() -> None:
    with pytest.raises(ValidationError):
        FindRoutesOutput.model_validate(
            {
                "shipment_id": "ABC123",
                "routes": [
                    {
                        "route_id": "R-102",
                        "via_ports": ["NLRTM"],
                        "eta": "2026-09-28T12:00:00Z",
                        "cost": 1450,
                        "confidence": 0.91,
                        "capacity_available": True,
                    }
                ],
            }
        )

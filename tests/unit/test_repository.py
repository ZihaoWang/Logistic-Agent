"""Unit tests for the in-memory logistics repository."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.logistics_api.repository import (
    InMemoryLogisticsRepository,
    RouteSearch,
    ShippingPolicy,
)
from contracts.backend import IdempotencyFingerprint, RerouteResult
from contracts.routing import RouteConstraints, RouteOption
from contracts.shipment import Shipment

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture
def repo() -> InMemoryLogisticsRepository:
    """Return a fresh repository loaded from the checked-in data files."""
    return InMemoryLogisticsRepository.from_data_dir(DATA_DIR)


async def test_get_shipment_returns_known_shipment(repo: InMemoryLogisticsRepository) -> None:
    shipment = await repo.get_shipment("ABC123")
    assert shipment is not None
    assert shipment.shipment_id == "ABC123"
    assert shipment.status == "delayed"
    assert shipment.current_port == "NLRTM"


async def test_get_shipment_returns_none_for_missing(repo: InMemoryLogisticsRepository) -> None:
    assert await repo.get_shipment("UNKNOWN") is None


async def test_get_port_status_returns_known_port(repo: InMemoryLogisticsRepository) -> None:
    status = await repo.get_port_status("NLRTM")
    assert status is not None
    assert status.port_code == "NLRTM"
    assert status.congestion_level == "high"


async def test_get_port_status_returns_none_for_missing(repo: InMemoryLogisticsRepository) -> None:
    assert await repo.get_port_status("ZZZZZ") is None


async def test_find_routes_returns_all_abc123_routes_without_capacity_filter(
    repo: InMemoryLogisticsRepository,
) -> None:
    constraints = RouteConstraints(require_capacity=False, max_results=10)
    routes = await repo.find_routes("ABC123", constraints)
    route_ids = {route.route_id for route in routes}
    assert route_ids == {"R-102", "R-205", "R-310", "R-118"}


async def test_find_routes_default_constraints_exclude_no_capacity(
    repo: InMemoryLogisticsRepository,
) -> None:
    routes = await repo.find_routes("ABC123")
    route_ids = {route.route_id for route in routes}
    assert route_ids == {"R-102", "R-205", "R-118"}


async def test_find_routes_demo_constraint_returns_only_r102(
    repo: InMemoryLogisticsRepository,
) -> None:
    constraints = RouteConstraints(
        max_additional_cost_eur=2000,
        max_delay_hours=24,
        require_capacity=True,
        max_results=10,
    )
    routes = await repo.find_routes("ABC123", constraints)
    assert [route.route_id for route in routes] == ["R-102"]


async def test_find_routes_does_not_return_other_shipment_routes(
    repo: InMemoryLogisticsRepository,
) -> None:
    routes = await repo.find_routes("ABC123", RouteConstraints(require_capacity=False))
    route_ids = {route.route_id for route in routes}
    assert "R-501" not in route_ids
    assert "R-401" not in route_ids


async def test_shipping_policy_allows_abc123_r102(repo: InMemoryLogisticsRepository) -> None:
    result = await repo.check_shipping_policy("ABC123", "R-102")
    assert result is not None
    assert result.allowed is True
    assert result.rule_ids == ["shipping-policy-ok"]


async def test_shipping_policy_denies_temp_controlled_beanr(
    repo: InMemoryLogisticsRepository,
) -> None:
    result = await repo.check_shipping_policy("GHI789", "R-401")
    assert result is not None
    assert result.allowed is False
    assert result.rule_ids == ["temp-controlled-beanr"]


async def test_shipping_policy_allows_ghi789_r402(repo: InMemoryLogisticsRepository) -> None:
    result = await repo.check_shipping_policy("GHI789", "R-402")
    assert result is not None
    assert result.allowed is True


async def test_shipping_policy_returns_none_for_delivered_shipment_without_route(
    repo: InMemoryLogisticsRepository,
) -> None:
    result = await repo.check_shipping_policy("MNO345", "R-102")
    assert result is None


async def test_save_and_get_reroute_by_idempotency_key(
    repo: InMemoryLogisticsRepository,
) -> None:
    result = RerouteResult(
        action_id="act-1",
        shipment_id="ABC123",
        route_id="R-102",
        status="accepted",
        applied_at=datetime(2026, 9, 25, 10, 0, tzinfo=UTC),
    )
    fingerprint = IdempotencyFingerprint(
        shipment_id="ABC123",
        route_id="R-102",
        expected_additional_cost_eur=1450.0,
    )
    await repo.save_reroute(result, key="key-abc-1", fingerprint=fingerprint)

    stored = await repo.get_action_by_idempotency_key("key-abc-1")
    assert stored is not None
    assert stored.action_id == "act-1"
    assert await repo.get_idempotency_fingerprint("key-abc-1") == fingerprint


def test_route_search_sorts_by_cost_then_route_id() -> None:
    shipment = Shipment.model_validate(
        {
            "shipment_id": "ABC123",
            "origin": "CNSHA",
            "destination": "DKCPH",
            "current_port": "NLRTM",
            "status": "delayed",
            "planned_eta": "2026-09-27T10:00:00Z",
            "current_eta": "2026-09-28T14:00:00Z",
            "cargo_type": "general",
            "priority": "high",
        }
    )
    routes = [
        RouteOption.model_validate(
            {
                "route_id": "R-205",
                "via_ports": ["BEANR"],
                "eta": "2026-09-28T06:00:00Z",
                "additional_cost_eur": 2600.0,
                "confidence": 0.80,
                "capacity_available": True,
            }
        ),
        RouteOption.model_validate(
            {
                "route_id": "R-102",
                "via_ports": ["DEHAM"],
                "eta": "2026-09-28T08:00:00Z",
                "additional_cost_eur": 1450.0,
                "confidence": 0.86,
                "capacity_available": True,
            }
        ),
    ]
    filtered = RouteSearch.filter_routes(
        shipment,
        routes,
        RouteConstraints(require_capacity=False, max_results=10),
    )
    assert [route.route_id for route in filtered] == ["R-102", "R-205"]


def test_shipping_policy_class_evaluates_delivered() -> None:
    shipment = Shipment.model_validate(
        {
            "shipment_id": "MNO345",
            "origin": "NLRTM",
            "destination": "DKCPH",
            "current_port": None,
            "status": "delivered",
            "planned_eta": "2026-09-20T16:00:00Z",
            "current_eta": "2026-09-20T16:00:00Z",
            "cargo_type": "general",
            "priority": "standard",
        }
    )
    route = RouteOption.model_validate(
        {
            "route_id": "R-102",
            "via_ports": ["DEHAM"],
            "eta": "2026-09-28T08:00:00Z",
            "additional_cost_eur": 1450.0,
            "confidence": 0.86,
            "capacity_available": True,
        }
    )
    result = ShippingPolicy.evaluate(shipment, route)
    assert result.allowed is False
    assert result.rule_ids == ["delivered-shipment"]

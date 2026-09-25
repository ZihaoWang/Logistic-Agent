"""Contract tests for the logistics-api HTTP endpoints."""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient

from apps.logistics_api.main import create_app
from apps.logistics_api.repository import BaseRepository, InMemoryLogisticsRepository
from contracts.backend import CheckShippingPolicyOutput, RerouteResult
from contracts.routing import (
    EstimateCostOutput,
    FindRoutesInput,
    FindRoutesOutput,
    PortStatus,
    RouteConstraints,
)
from contracts.shipment import Shipment

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture
def repo() -> InMemoryLogisticsRepository:
    """Return a fresh repository for each test."""
    return InMemoryLogisticsRepository.from_data_dir(DATA_DIR)


@pytest.fixture
async def client(repo: InMemoryLogisticsRepository) -> AsyncGenerator[AsyncClient, None]:
    """Return an async HTTP client bound to the test app."""
    app = create_app(repo=repo)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_get_shipment_returns_typed_model(client: AsyncClient) -> None:
    response = await client.get("/v1/shipments/ABC123")
    assert response.status_code == 200
    shipment = Shipment.model_validate(response.json())
    assert shipment.shipment_id == "ABC123"
    assert shipment.status == "delayed"
    assert shipment.current_port == "NLRTM"


async def test_get_shipment_unknown_returns_404(client: AsyncClient) -> None:
    response = await client.get("/v1/shipments/UNKNOWN")
    assert response.status_code == 404
    assert response.json()["detail"] == "shipment not found"


async def test_get_port_status_returns_typed_model(client: AsyncClient) -> None:
    response = await client.get("/v1/ports/NLRTM/status")
    assert response.status_code == 200
    status = PortStatus.model_validate(response.json())
    assert status.port_code == "NLRTM"
    assert status.congestion_level == "high"


async def test_search_routes_demo_constraint_returns_only_r102(client: AsyncClient) -> None:
    body = FindRoutesInput(
        shipment_id="ABC123",
        constraints=RouteConstraints(
            max_additional_cost_eur=2000,
            max_delay_hours=24,
            require_capacity=True,
            max_results=10,
        ),
    )
    response = await client.post("/v1/routes/search", json=body.model_dump(mode="json"))
    assert response.status_code == 200
    output = FindRoutesOutput.model_validate(response.json())
    assert output.shipment_id == "ABC123"
    assert [route.route_id for route in output.routes] == ["R-102"]


async def test_estimate_cost_returns_typed_model(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/routes/cost",
        json={"shipment_id": "ABC123", "route_id": "R-102"},
    )
    assert response.status_code == 200
    output = EstimateCostOutput.model_validate(response.json())
    assert output.estimate.currency == "EUR"
    assert output.estimate.additional_cost == 1450.0
    assert output.estimate.estimate_version == "v1"


async def test_check_policy_allows_abc123_r102(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/policy/check",
        json={"shipment_id": "ABC123", "route_id": "R-102"},
    )
    assert response.status_code == 200
    output = CheckShippingPolicyOutput.model_validate(response.json())
    assert output.result.allowed is True


async def test_check_policy_denies_ghi789_r401(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/policy/check",
        json={"shipment_id": "GHI789", "route_id": "R-401"},
    )
    assert response.status_code == 200
    output = CheckShippingPolicyOutput.model_validate(response.json())
    assert output.result.allowed is False
    assert output.result.rule_ids == ["temp-controlled-beanr"]


async def test_reroute_is_idempotent(client: AsyncClient) -> None:
    body = {
        "route_id": "R-102",
        "idempotency_key": "key-abc-1",
        "expected_additional_cost_eur": 1450.0,
    }
    first = await client.post("/v1/shipments/ABC123/reroute", json=body)
    second = await client.post("/v1/shipments/ABC123/reroute", json=body)

    assert first.status_code == 200
    assert second.status_code == 200
    first_result = RerouteResult.model_validate(first.json())
    second_result = RerouteResult.model_validate(second.json())
    assert first_result.action_id == second_result.action_id
    assert first_result.status == "accepted"
    assert second_result.status == "already_applied"


async def test_reroute_conflicting_idempotency_key_returns_409(client: AsyncClient) -> None:
    first_body = {
        "route_id": "R-102",
        "idempotency_key": "key-abc-1",
        "expected_additional_cost_eur": 1450.0,
    }
    second_body = {
        "route_id": "R-118",
        "idempotency_key": "key-abc-1",
        "expected_additional_cost_eur": 1100.0,
    }
    first = await client.post("/v1/shipments/ABC123/reroute", json=first_body)
    second = await client.post("/v1/shipments/ABC123/reroute", json=second_body)

    assert first.status_code == 200
    assert second.status_code == 409


async def test_health_does_not_touch_repository() -> None:
    class BrokenRepository:
        async def get_shipment(self, shipment_id: str) -> Any:
            raise RuntimeError("repository should not be called")

        async def get_port_status(self, port_code: str) -> Any:
            raise RuntimeError("repository should not be called")

        async def find_routes(self, shipment_id: str, constraints: Any = None) -> Any:
            raise RuntimeError("repository should not be called")

        async def get_route(self, shipment_id: str, route_id: str) -> Any:
            raise RuntimeError("repository should not be called")

        async def check_shipping_policy(self, shipment_id: str, route_id: str) -> Any:
            raise RuntimeError("repository should not be called")

        async def get_action_by_idempotency_key(self, key: str) -> Any:
            raise RuntimeError("repository should not be called")

        async def get_idempotency_fingerprint(self, key: str) -> Any:
            raise RuntimeError("repository should not be called")

        async def save_reroute(self, result: Any, key: str, fingerprint: Any) -> None:
            raise RuntimeError("repository should not be called")

    app = create_app(repo=cast(BaseRepository, BrokenRepository()))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        response = await http_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "logistics-api"

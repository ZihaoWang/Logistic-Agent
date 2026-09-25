"""HTTP routes for the logistics API."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request

from apps.logistics_api.repository import BaseRepository
from contracts.backend import (
    CheckShippingPolicyInput,
    CheckShippingPolicyOutput,
    IdempotencyFingerprint,
    RerouteRequestBody,
    RerouteResult,
)
from contracts.routing import (
    CostEstimate,
    EstimateCostInput,
    EstimateCostOutput,
    FindRoutesInput,
    FindRoutesOutput,
    PortStatus,
)
from contracts.shipment import Shipment

router = APIRouter()


def get_repository(request: Request) -> BaseRepository:
    """Return the repository stored on the FastAPI app.

    Parameters:
        request: The incoming HTTP request.

    Returns:
        The BaseRepository from app.state.
    """
    app = cast(FastAPI, request.app)
    return cast(BaseRepository, app.state.repository)


RepositoryDep = Annotated[BaseRepository, Depends(get_repository)]


def get_service_version() -> str:
    """Return the service version from GIT_SHA or a local default.

    Returns:
        The git SHA from the environment, or 'dev' when running locally.
    """
    return os.environ.get("GIT_SHA", "dev")


@router.get("/health")
async def health() -> dict[str, str]:
    """Return service health without touching downstream dependencies.

    Returns:
        A dict with status, service name, and version.
    """
    return {
        "status": "ok",
        "service": "logistics-api",
        "version": get_service_version(),
    }


@router.get("/v1/shipments/{shipment_id}")
async def get_shipment(shipment_id: str, repo: RepositoryDep) -> Shipment:
    """Return a shipment by id.

    Parameters:
        shipment_id: The shipment identifier from the URL path.
        repo: Injected logistics repository.

    Returns:
        The Shipment model for the given id.

    Raises:
        HTTPException: 404 when the shipment does not exist.
    """
    shipment = await repo.get_shipment(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    return shipment


@router.get("/v1/ports/{port_code}/status")
async def get_port_status(port_code: str, repo: RepositoryDep) -> PortStatus:
    """Return current status for a port.

    Parameters:
        port_code: The port code from the URL path.
        repo: Injected logistics repository.

    Returns:
        The PortStatus model for the given port.

    Raises:
        HTTPException: 404 when the port does not exist.
    """
    status = await repo.get_port_status(port_code)
    if status is None:
        raise HTTPException(status_code=404, detail="port not found")
    return status


@router.post("/v1/routes/search")
async def search_routes(body: FindRoutesInput, repo: RepositoryDep) -> FindRoutesOutput:
    """Search route alternatives for a shipment.

    Parameters:
        body: Shipment id and optional search constraints.
        repo: Injected logistics repository.

    Returns:
        FindRoutesOutput with matching routes (may be empty).

    Raises:
        HTTPException: 404 when the shipment does not exist.
    """
    shipment = await repo.get_shipment(body.shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="shipment not found")

    routes = await repo.find_routes(body.shipment_id, body.constraints)
    return FindRoutesOutput(shipment_id=body.shipment_id, routes=routes)


@router.post("/v1/routes/cost")
async def estimate_cost(body: EstimateCostInput, repo: RepositoryDep) -> EstimateCostOutput:
    """Estimate additional cost for a specific route.

    Parameters:
        body: Shipment id and route id.
        repo: Injected logistics repository.

    Returns:
        EstimateCostOutput with the cost estimate.

    Raises:
        HTTPException: 404 when the route does not exist for the shipment.
    """
    route = await repo.get_route(body.shipment_id, body.route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="route not found")

    return EstimateCostOutput(
        estimate=CostEstimate(
            currency="EUR",
            additional_cost=route.additional_cost_eur,
            estimate_version="v1",
        )
    )


@router.post("/v1/policy/check")
async def check_policy(
    body: CheckShippingPolicyInput,
    repo: RepositoryDep,
) -> CheckShippingPolicyOutput:
    """Check business shipping policy for a shipment and route.

    Parameters:
        body: Shipment id and route id.
        repo: Injected logistics repository.

    Returns:
        CheckShippingPolicyOutput with the policy result.

    Raises:
        HTTPException: 404 when the shipment or route does not exist.
    """
    result = await repo.check_shipping_policy(body.shipment_id, body.route_id)
    if result is None:
        raise HTTPException(status_code=404, detail="shipment or route not found")

    return CheckShippingPolicyOutput(result=result)


@router.post("/v1/shipments/{shipment_id}/reroute")
async def reroute(
    shipment_id: str,
    body: RerouteRequestBody,
    repo: RepositoryDep,
) -> RerouteResult:
    """Reroute a shipment onto a new route with idempotent behavior.

    Parameters:
        shipment_id: The shipment identifier from the URL path.
        body: Route id, idempotency key, and expected cost.
        repo: Injected logistics repository.

    Returns:
        RerouteResult with action_id and status.

    Raises:
        HTTPException: 404 when shipment or route not found; 409 on conflict.
    """
    fingerprint = IdempotencyFingerprint(
        shipment_id=shipment_id,
        route_id=body.route_id,
        expected_additional_cost_eur=body.expected_additional_cost_eur,
    )

    existing = await repo.get_action_by_idempotency_key(body.idempotency_key)
    if existing is not None:
        stored_fingerprint = await repo.get_idempotency_fingerprint(body.idempotency_key)
        if stored_fingerprint != fingerprint:
            raise HTTPException(
                status_code=409,
                detail="idempotency key reused with different request parameters",
            )
        return existing.model_copy(update={"status": "already_applied"})

    shipment = await repo.get_shipment(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="shipment not found")

    route = await repo.get_route(shipment_id, body.route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="route not found")

    if body.expected_additional_cost_eur != route.additional_cost_eur:
        raise HTTPException(
            status_code=409,
            detail="expected cost does not match route cost",
        )

    if not route.capacity_available:
        raise HTTPException(status_code=409, detail="route has no available capacity")

    policy = await repo.check_shipping_policy(shipment_id, body.route_id)
    if policy is None or not policy.allowed:
        raise HTTPException(status_code=409, detail="shipping policy denied reroute")

    result = RerouteResult(
        action_id=str(uuid.uuid4()),
        shipment_id=shipment_id,
        route_id=body.route_id,
        status="accepted",
        applied_at=datetime.now(UTC),
    )
    await repo.save_reroute(result, key=body.idempotency_key, fingerprint=fingerprint)
    return result

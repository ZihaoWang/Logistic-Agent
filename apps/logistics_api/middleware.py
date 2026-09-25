"""OpenTelemetry middleware for logistics-api."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

from agent_platform.observability.tracing import (
    extract_trace_context,
    get_tracer,
    set_span_attributes,
)

_SERVICE = "logistics-api"


async def trace_requests_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Continue an incoming trace and record one request span."""
    parent = extract_trace_context(dict(request.headers))
    route = request.url.path
    tracer = get_tracer()
    with tracer.start_as_current_span(
        "logistics-api.request",
        context=parent,
        attributes={"service": _SERVICE, "http.route": route},
    ) as span:
        response = await call_next(request)
        set_span_attributes(span, {"backend.status_code": response.status_code})
        return response

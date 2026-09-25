"""OpenTelemetry span helpers with allowlisted attributes."""

from __future__ import annotations

from collections.abc import Generator, Mapping
from contextlib import contextmanager

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import Span, Status, StatusCode
from opentelemetry.util.types import AttributeValue

from agent_platform.observability.redaction import redact

TRACER_NAME = "agent_platform"

ALLOWED_ATTRIBUTES = frozenset(
    {
        "run.id",
        "thread.id",
        "agent.id",
        "tool.name",
        "tool.attempt",
        "tool.status",
        "policy.decision",
        "approval.required",
        "backend.status_code",
        "model.name",
        "model.input_tokens",
        "model.output_tokens",
        "estimated_cost_usd",
        "service",
        "http.route",
    },
)


def get_tracer() -> trace.Tracer:
    """Return the platform tracer."""
    return trace.get_tracer(TRACER_NAME)


def _filter_attributes(attributes: Mapping[str, object] | None) -> dict[str, object]:
    if attributes is None:
        return {}
    redacted = redact(dict(attributes))
    return {key: value for key, value in redacted.items() if key in ALLOWED_ATTRIBUTES}


def _attribute_value(value: object) -> AttributeValue:
    if isinstance(value, str | bool | int | float):
        return value
    return str(value)


def set_span_attributes(span: Span, attributes: Mapping[str, object] | None) -> None:
    """Set only allowlisted, redacted attributes on a span."""
    for key, value in _filter_attributes(attributes).items():
        span.set_attribute(key, _attribute_value(value))


def set_span_error(span: Span, message: str | None = None) -> None:
    """Mark a span as failed."""
    span.set_status(Status(StatusCode.ERROR, message or "error"))


def mark_current_span_error(message: str | None = None) -> None:
    """Mark the active span as failed when one is present."""
    span = trace.get_current_span()
    if span.get_span_context().is_valid:
        set_span_error(span, message)


@contextmanager
def start_span(
    name: str,
    *,
    service: str,
    attributes: Mapping[str, object] | None = None,
) -> Generator[Span, None, None]:
    """Start a span with service label and allowlisted attributes."""
    tracer = get_tracer()
    merged: dict[str, object] = {"service": service}
    if attributes:
        merged.update(attributes)
    with tracer.start_as_current_span(name) as span:
        set_span_attributes(span, merged)
        yield span


def current_trace_id() -> str | None:
    """Return the current trace id as 32-char hex, or None."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx.is_valid:
        return None
    return format(ctx.trace_id, "032x")


def current_span_id() -> str | None:
    """Return the current span id as 16-char hex, or None."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx.is_valid:
        return None
    return format(ctx.span_id, "016x")


def inject_trace_headers(headers: dict[str, str]) -> dict[str, str]:
    """Inject W3C trace context into outgoing HTTP headers."""
    carrier: dict[str, str] = dict(headers)
    inject(carrier)
    return carrier


def extract_trace_context(headers: Mapping[str, str]) -> Context:
    """Extract W3C trace context from incoming HTTP headers."""
    return extract(dict(headers))


def activate_span(
    name: str,
    *,
    service: str,
    attributes: Mapping[str, object] | None = None,
) -> tuple[Span, object]:
    """Start a span and attach it as the current context."""
    tracer = get_tracer()
    merged: dict[str, object] = {"service": service}
    if attributes:
        merged.update(attributes)
    span = tracer.start_span(name)
    set_span_attributes(span, merged)
    token = otel_context.attach(trace.set_span_in_context(span))
    return span, token


def deactivate_span(span: Span, token: object) -> None:
    """Detach context and end a manually activated span."""
    otel_context.detach(token)  # type: ignore[arg-type]
    span.end()

"""structlog processors used by StructuredLogging."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from agent_platform.observability.redaction import REDACTED, is_sensitive_key, redact
from agent_platform.observability.tracing import current_span_id, current_trace_id


def add_correlation_fields(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    event_dict.setdefault("trace_id", current_trace_id())
    event_dict.setdefault("span_id", current_span_id())
    return event_dict


def redact_event_fields(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    redacted = redact({k: v for k, v in event_dict.items() if isinstance(k, str)})
    cleaned: dict[str, Any] = {}
    for key, value in redacted.items():
        if is_sensitive_key(key):
            continue
        if value == REDACTED:
            continue
        cleaned[key] = value
    return cleaned


def rename_event_to_message(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    event = event_dict.pop("event", None)
    if event is not None and "message" not in event_dict:
        event_dict["message"] = event
    return event_dict

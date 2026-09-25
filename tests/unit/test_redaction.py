"""Unit tests for observability redaction."""

from __future__ import annotations

import json
import logging

import structlog

from agent_platform.observability.logging import configure_structlog
from agent_platform.observability.redaction import REDACTED, redact, safe_arguments
from agent_platform.observability.utils.processors import (
    redact_event_fields,
    rename_event_to_message,
)


def test_redaction_removes_sensitive_fields() -> None:
    fields = {"authorization": "Bearer xyz", "shipment_id": "ABC123"}
    result = redact(fields)
    assert result["authorization"] == REDACTED
    assert result["shipment_id"] == "ABC123"


def test_redaction_is_case_insensitive() -> None:
    fields = {"Access_Token": "secret", "API_KEY": "k", "shipment_id": "ABC123"}
    result = redact(fields)
    assert result["Access_Token"] == REDACTED
    assert result["API_KEY"] == REDACTED
    assert result["shipment_id"] == "ABC123"


def test_safe_arguments_for_request_reroute() -> None:
    arguments = {
        "shipment_id": "ABC123",
        "route_id": "R-102",
        "expected_additional_cost_eur": 1450.0,
        "approval_id": "apr-secret",
        "idempotency_key": "idem-secret",
    }
    safe = safe_arguments("request_reroute", arguments)
    assert safe["shipment_id"] == "ABC123"
    assert safe["route_id"] == "R-102"
    assert safe["cost"] == 1450.0
    assert "arguments_hash" in safe
    assert "approval_id" not in safe
    assert "idempotency_key" not in safe


def test_structlog_output_omits_sensitive_keys() -> None:
    structlog.reset_defaults()
    configure_structlog(json_output=True)
    event = {
        "authorization": "Bearer xyz",
        "access_token": "token-value",
        "shipment_id": "ABC123",
        "event": "test.event",
        "service": "test",
    }
    cleaned = rename_event_to_message(
        logging.getLogger("test"),
        "info",
        redact_event_fields(logging.getLogger("test"), "info", event),
    )
    rendered = json.dumps(cleaned).lower()
    assert "authorization" not in rendered
    assert "access_token" not in rendered
    assert "abc123" in rendered

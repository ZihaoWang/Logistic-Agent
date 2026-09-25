"""Central redaction for structured logs and trace attributes."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

_SENSITIVE_PATTERNS = re.compile(
    r"authorization|cookie|access_token|id_token|api_key|secret|password",
    re.IGNORECASE,
)

REDACTED = "***REDACTED***"

_HIGH_RISK_TOOLS = frozenset({"request_reroute"})


def redact(fields: Mapping[str, object]) -> dict[str, object]:
    """Return a copy with sensitive keys replaced by REDACTED."""
    return {
        key: REDACTED if _SENSITIVE_PATTERNS.search(key) else value for key, value in fields.items()
    }


def is_sensitive_key(key: str) -> bool:
    """Return True when a field name matches sensitive patterns."""
    return _SENSITIVE_PATTERNS.search(key) is not None


def safe_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, object]:
    """Return safe log/trace fields for high-risk tool arguments."""
    if tool_name not in _HIGH_RISK_TOOLS:
        return redact({k: v for k, v in arguments.items() if not is_sensitive_key(k)})

    canonical = json.dumps(arguments, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    safe: dict[str, object] = {"arguments_hash": digest}
    if "shipment_id" in arguments:
        safe["shipment_id"] = arguments["shipment_id"]
    if "route_id" in arguments:
        safe["route_id"] = arguments["route_id"]
    cost = arguments.get("expected_additional_cost_eur")
    if cost is not None:
        safe["cost"] = cost
    return safe

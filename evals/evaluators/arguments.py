"""Argument and schema validity evaluators."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from agent_platform.mcp.registry import get_input_model, parse_tool_result_data
from evals.models import ArgumentCheck, CaseTrace, EvalCase


def _resolve_path(arguments: dict[str, Any], path: str) -> Any:
    """Return a nested value from arguments using dotted path notation."""
    current: Any = arguments
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _check_argument(record_args: dict[str, Any], check: ArgumentCheck) -> bool:
    """Return True when one argument check matches a tool call."""
    value = _resolve_path(record_args, check.path)
    if check.equals is not None and value != check.equals:
        return False
    if check.lte is not None:
        if value is None:
            return False
        try:
            if float(value) > check.lte:
                return False
        except (TypeError, ValueError):
            return False
    return True


def score_arguments(case: EvalCase, trace: CaseTrace) -> bool:
    """Return True when every argument check matches at least one tool call."""
    if not case.argument_checks:
        return True
    for check in case.argument_checks:
        matched = False
        for record in trace.records:
            if record.tool_name != check.tool:
                continue
            if _check_argument(record.arguments, check):
                matched = True
                break
        if not matched:
            return False
    return True


def score_schema_validity(trace: CaseTrace) -> bool:
    """Return True when all tool inputs/outputs validate against contracts."""
    for record in trace.records:
        try:
            input_model = get_input_model(record.tool_name)
            input_model.model_validate(record.arguments)
        except (KeyError, ValidationError):
            return False

        result = record.result
        if result.status == "success" and result.data is not None:
            try:
                parse_tool_result_data(record.tool_name, result.data)
            except (KeyError, ValidationError):
                return False
        if result.status == "failed" and result.error is not None:
            if result.error.category == "contract":
                return False
    return True


def tool_result_payloads(trace: CaseTrace) -> str:
    """Serialize successful tool payloads for groundedness checks."""
    payloads: list[Any] = []
    for record in trace.records:
        if record.result.status == "success" and record.result.data is not None:
            payloads.append(record.result.data)
    return json.dumps(payloads, default=str)

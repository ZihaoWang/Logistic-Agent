"""Parse ExecutionContext from FastMCP request metadata."""

from typing import Any

from pydantic import ValidationError

from agent_platform.models.execution import ExecutionContext


def execution_context_from_meta(meta: Any) -> ExecutionContext | None:
    """Return ExecutionContext from client call metadata, or None when absent."""
    if meta is None:
        return None
    payload: dict[str, Any] | None = None
    if isinstance(meta, dict):
        payload = meta.get("execution_context")
    elif hasattr(meta, "execution_context"):
        raw = meta.execution_context
        if isinstance(raw, dict):
            payload = raw
    if payload is None:
        return None
    try:
        return ExecutionContext.model_validate(payload)
    except ValidationError:
        return None

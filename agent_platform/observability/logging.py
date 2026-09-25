"""Structured logging with run/trace correlation and redaction."""

from __future__ import annotations

import logging
from typing import Any

import structlog

from agent_platform.observability.utils.processors import (
    add_correlation_fields,
    redact_event_fields,
    rename_event_to_message,
)

_CONFIGURED = False


def configure_structlog(*, json_output: bool = True) -> None:
    """Configure structlog once for the process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_correlation_fields,
        redact_event_fields,
        rename_event_to_message,
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def bind_run(run_id: str, *, service: str | None = None) -> None:
    """Bind run_id (and optional service) to structlog contextvars."""
    fields: dict[str, str] = {"run_id": run_id}
    if service is not None:
        fields["service"] = service
    structlog.contextvars.bind_contextvars(**fields)


def get_logger(service: str) -> Any:
    """Return a logger with the service field bound."""
    configure_structlog()
    return structlog.get_logger().bind(service=service)

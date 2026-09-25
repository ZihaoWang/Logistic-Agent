"""Pytest configuration shared across the test suite."""

from __future__ import annotations

import pytest

from agent_platform.observability.setup import InMemoryTelemetry, install_in_memory_telemetry

_SESSION_TELEMETRY = install_in_memory_telemetry(service_name="test")


@pytest.fixture(scope="session")
def session_telemetry() -> InMemoryTelemetry:
    """Return the session-wide in-memory telemetry handles."""
    return _SESSION_TELEMETRY


@pytest.fixture
def telemetry(session_telemetry: InMemoryTelemetry) -> InMemoryTelemetry:
    """Return session telemetry with spans cleared between tests."""
    session_telemetry.span_exporter.clear()
    return session_telemetry

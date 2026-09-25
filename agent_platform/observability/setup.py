"""Process-wide OpenTelemetry and structlog configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agent_platform.observability.logging import configure_structlog
from agent_platform.observability.metrics import init_metrics, reset_metrics

_CONFIGURED = False
_in_memory_span_exporter: InMemorySpanExporter | None = None
_in_memory_metric_reader: InMemoryMetricReader | None = None


@dataclass
class InMemoryTelemetry:
    """Handles for test-time span and metric inspection."""

    span_exporter: InMemorySpanExporter
    metric_reader: InMemoryMetricReader


def install_in_memory_telemetry(*, service_name: str = "test") -> InMemoryTelemetry:
    """Replace providers with in-memory exporters for tests."""
    global _CONFIGURED
    global _in_memory_span_exporter
    global _in_memory_metric_reader

    import structlog

    structlog.reset_defaults()
    from agent_platform.observability import logging as obs_logging

    obs_logging._CONFIGURED = False
    reset_metrics()
    _CONFIGURED = False

    span_exporter = InMemorySpanExporter()
    metric_reader = InMemoryMetricReader()
    resource = Resource.create({"service.name": service_name})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    metrics.set_meter_provider(meter_provider)

    configure_structlog(json_output=True)
    init_metrics()

    _in_memory_span_exporter = span_exporter
    _in_memory_metric_reader = metric_reader
    _CONFIGURED = True
    return InMemoryTelemetry(span_exporter=span_exporter, metric_reader=metric_reader)


def configure_observability(service_name: str) -> None:
    """Configure tracing, metrics, and logging once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    resource = Resource.create({"service.name": service_name})
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    tracer_provider = TracerProvider(resource=resource)
    if endpoint:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)),
        )
    trace.set_tracer_provider(tracer_provider)

    metric_readers: list[PeriodicExportingMetricReader | InMemoryMetricReader] = []
    if endpoint:
        metric_readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=endpoint, insecure=True),
            ),
        )
    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)

    configure_structlog(json_output=True)
    init_metrics()
    _CONFIGURED = True


def get_in_memory_span_exporter() -> InMemorySpanExporter | None:
    """Return the test span exporter when installed."""
    return _in_memory_span_exporter


def get_in_memory_metric_reader() -> InMemoryMetricReader | None:
    """Return the test metric reader when installed."""
    return _in_memory_metric_reader

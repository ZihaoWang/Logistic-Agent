"""Test helpers for OpenTelemetry spans and metrics."""

from __future__ import annotations

from collections.abc import Sequence

from opentelemetry.sdk.metrics.export import MetricsData
from opentelemetry.sdk.trace import ReadableSpan


def span_trace_ids(spans: Sequence[ReadableSpan]) -> set[str]:
    """Return normalized trace ids from finished spans."""
    return {format(span.context.trace_id, "032x") for span in spans}


def span_names(spans: Sequence[ReadableSpan]) -> set[str]:
    """Return span names from finished spans."""
    return {span.name for span in spans}


def span_attribute(spans: Sequence[ReadableSpan], name: str, key: str) -> object | None:
    """Return one attribute from the first span with the given name."""
    for span in spans:
        if span.name == name:
            return span.attributes.get(key) if span.attributes else None
    return None


def metric_sum(metrics_data: MetricsData | None, metric_name: str) -> float:
    """Sum all data points for one metric name."""
    if metrics_data is None:
        return 0.0
    total = 0.0
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name != metric_name:
                    continue
                for data_point in metric.data.data_points:
                    raw_value = getattr(data_point, "value", None)
                    if raw_value is None:
                        raw_value = getattr(data_point, "sum", 0)
                    total += float(raw_value or 0)
    return total

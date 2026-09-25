"""Low-cardinality OpenTelemetry metrics for the agent platform."""

from __future__ import annotations

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, Meter

METER_NAME = "agent_platform"

_agent_runs_total: Counter | None = None
_agent_runs_failed_total: Counter | None = None
_agent_run_duration_seconds: Histogram | None = None
_model_calls_total: Counter | None = None
_model_input_tokens_total: Counter | None = None
_model_output_tokens_total: Counter | None = None
_tool_calls_total: Counter | None = None
_tool_failures_total: Counter | None = None
_tool_retries_total: Counter | None = None
_tool_duration_seconds: Histogram | None = None
_policy_denials_total: Counter | None = None
_approval_requests_total: Counter | None = None
_approval_approved_total: Counter | None = None
_approval_rejected_total: Counter | None = None
_budget_exceeded_total: Counter | None = None
_contract_validation_failures_total: Counter | None = None


def _meter() -> Meter:
    return metrics.get_meter(METER_NAME)


def _normalize_tool_name(tool_name: str | None) -> str:
    if not tool_name:
        return "other"
    return tool_name


def _labels(
    *,
    service: str,
    tool_name: str | None = None,
    status: str | None = None,
    error_category: str | None = None,
    model: str | None = None,
) -> dict[str, str]:
    labels: dict[str, str] = {"service": service}
    if tool_name is not None:
        labels["tool_name"] = _normalize_tool_name(tool_name)
    if status is not None:
        labels["status"] = status
    if error_category is not None:
        labels["error_category"] = error_category
    if model is not None:
        labels["model"] = model
    return labels


def reset_metrics() -> None:
    """Clear cached instruments so tests can bind a fresh meter provider."""
    global _agent_runs_total
    global _agent_runs_failed_total
    global _agent_run_duration_seconds
    global _model_calls_total
    global _model_input_tokens_total
    global _model_output_tokens_total
    global _tool_calls_total
    global _tool_failures_total
    global _tool_retries_total
    global _tool_duration_seconds
    global _policy_denials_total
    global _approval_requests_total
    global _approval_approved_total
    global _approval_rejected_total
    global _budget_exceeded_total
    global _contract_validation_failures_total
    _agent_runs_total = None
    _agent_runs_failed_total = None
    _agent_run_duration_seconds = None
    _model_calls_total = None
    _model_input_tokens_total = None
    _model_output_tokens_total = None
    _tool_calls_total = None
    _tool_failures_total = None
    _tool_retries_total = None
    _tool_duration_seconds = None
    _policy_denials_total = None
    _approval_requests_total = None
    _approval_approved_total = None
    _approval_rejected_total = None
    _budget_exceeded_total = None
    _contract_validation_failures_total = None


def init_metrics() -> None:
    """Create metric instruments once."""
    global _agent_runs_total
    global _agent_runs_failed_total
    global _agent_run_duration_seconds
    global _model_calls_total
    global _model_input_tokens_total
    global _model_output_tokens_total
    global _tool_calls_total
    global _tool_failures_total
    global _tool_retries_total
    global _tool_duration_seconds
    global _policy_denials_total
    global _approval_requests_total
    global _approval_approved_total
    global _approval_rejected_total
    global _budget_exceeded_total
    global _contract_validation_failures_total

    if _agent_runs_total is not None:
        return

    meter = _meter()
    _agent_runs_total = meter.create_counter("agent_runs_total")
    _agent_runs_failed_total = meter.create_counter("agent_runs_failed_total")
    _agent_run_duration_seconds = meter.create_histogram(
        "agent_run_duration_seconds",
        unit="s",
    )
    _model_calls_total = meter.create_counter("model_calls_total")
    _model_input_tokens_total = meter.create_counter("model_input_tokens_total")
    _model_output_tokens_total = meter.create_counter("model_output_tokens_total")
    _tool_calls_total = meter.create_counter("tool_calls_total")
    _tool_failures_total = meter.create_counter("tool_failures_total")
    _tool_retries_total = meter.create_counter("tool_retries_total")
    _tool_duration_seconds = meter.create_histogram("tool_duration_seconds", unit="s")
    _policy_denials_total = meter.create_counter("policy_denials_total")
    _approval_requests_total = meter.create_counter("approval_requests_total")
    _approval_approved_total = meter.create_counter("approval_approved_total")
    _approval_rejected_total = meter.create_counter("approval_rejected_total")
    _budget_exceeded_total = meter.create_counter("budget_exceeded_total")
    _contract_validation_failures_total = meter.create_counter(
        "contract_validation_failures_total",
    )


def _require_counter(counter: Counter | None, name: str) -> Counter:
    if counter is None:
        msg = f"{name} is not initialized"
        raise RuntimeError(msg)
    return counter


def _require_histogram(histogram: Histogram | None, name: str) -> Histogram:
    if histogram is None:
        msg = f"{name} is not initialized"
        raise RuntimeError(msg)
    return histogram


def record_agent_run(*, service: str, status: str) -> None:
    init_metrics()
    _require_counter(_agent_runs_total, "agent_runs_total").add(
        1,
        _labels(service=service, status=status),
    )


def record_agent_run_failed(*, service: str) -> None:
    init_metrics()
    _require_counter(_agent_runs_failed_total, "agent_runs_failed_total").add(
        1,
        _labels(service=service),
    )


def record_agent_run_duration(*, service: str, seconds: float) -> None:
    init_metrics()
    _require_histogram(_agent_run_duration_seconds, "agent_run_duration_seconds").record(
        seconds,
        _labels(service=service),
    )


def record_model_call(
    *,
    service: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    init_metrics()
    labels = _labels(service=service, model=model)
    _require_counter(_model_calls_total, "model_calls_total").add(1, labels)
    if input_tokens:
        _require_counter(_model_input_tokens_total, "model_input_tokens_total").add(
            input_tokens,
            labels,
        )
    if output_tokens:
        _require_counter(_model_output_tokens_total, "model_output_tokens_total").add(
            output_tokens,
            labels,
        )


def record_tool_call(
    *,
    service: str,
    tool_name: str,
    status: str,
    duration_seconds: float,
    failed: bool = False,
) -> None:
    init_metrics()
    labels = _labels(service=service, tool_name=tool_name, status=status)
    _require_counter(_tool_calls_total, "tool_calls_total").add(1, labels)
    _require_histogram(_tool_duration_seconds, "tool_duration_seconds").record(
        duration_seconds,
        labels,
    )
    if failed:
        _require_counter(_tool_failures_total, "tool_failures_total").add(1, labels)


def record_tool_retry(*, service: str, tool_name: str) -> None:
    init_metrics()
    _require_counter(_tool_retries_total, "tool_retries_total").add(
        1,
        _labels(service=service, tool_name=tool_name),
    )


def record_policy_denial(*, service: str, tool_name: str) -> None:
    init_metrics()
    _require_counter(_policy_denials_total, "policy_denials_total").add(
        1,
        _labels(service=service, tool_name=tool_name),
    )


def record_approval_request(*, service: str, tool_name: str) -> None:
    init_metrics()
    _require_counter(_approval_requests_total, "approval_requests_total").add(
        1,
        _labels(service=service, tool_name=tool_name),
    )


def record_approval_approved(*, service: str) -> None:
    init_metrics()
    _require_counter(_approval_approved_total, "approval_approved_total").add(
        1,
        _labels(service=service),
    )


def record_approval_rejected(*, service: str) -> None:
    init_metrics()
    _require_counter(_approval_rejected_total, "approval_rejected_total").add(
        1,
        _labels(service=service),
    )


def record_budget_exceeded(*, service: str, tool_name: str) -> None:
    init_metrics()
    _require_counter(_budget_exceeded_total, "budget_exceeded_total").add(
        1,
        _labels(service=service, tool_name=tool_name),
    )


def record_contract_validation_failure(*, service: str, error_category: str) -> None:
    init_metrics()
    _require_counter(
        _contract_validation_failures_total,
        "contract_validation_failures_total",
    ).add(1, _labels(service=service, error_category=error_category))

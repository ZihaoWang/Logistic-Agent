"""Cost metrics extraction."""

from evals.models import CaseTrace


def extract_cost_metrics(trace: CaseTrace) -> dict[str, float | int]:
    """Return usage and latency metrics for one case."""
    usage = trace.usage
    return {
        "model_calls": usage.model_calls,
        "tool_calls": usage.tool_calls,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "estimated_cost_usd": usage.estimated_cost_usd,
        "latency_seconds": trace.latency_seconds,
    }

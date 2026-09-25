"""Tool selection and forbidden-action evaluators."""

from evals.models import CaseTrace, EvalCase


def score_tool_selection(case: EvalCase, trace: CaseTrace) -> bool:
    """Return True when every required tool was called at least once."""
    called = set(trace.tool_names)
    return all(tool in called for tool in case.expected.required_tools)


def score_forbidden_action(case: EvalCase, trace: CaseTrace) -> bool:
    """Return True when no forbidden tool appears in the trace."""
    called = set(trace.tool_names)
    return not any(tool in called for tool in case.expected.forbidden_tools)

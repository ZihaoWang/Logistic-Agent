"""Trajectory evaluator for call order and count."""

from evals.models import CaseTrace, EvalCase


def _is_subsequence(expected: list[str], actual: list[str]) -> bool:
    """Return True when expected appears in order within actual."""
    if not expected:
        return True
    index = 0
    for tool in actual:
        if tool == expected[index]:
            index += 1
            if index == len(expected):
                return True
    return False


def score_trajectory(case: EvalCase, trace: CaseTrace) -> bool:
    """Return True when ordered tools and max call count constraints hold."""
    if case.expected.ordered_tools and not _is_subsequence(
        case.expected.ordered_tools,
        trace.tool_names,
    ):
        return False
    if case.expected.max_tool_calls is not None:
        if len(trace.tool_names) > case.expected.max_tool_calls:
            return False
    return True

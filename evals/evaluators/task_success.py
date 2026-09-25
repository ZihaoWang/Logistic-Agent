"""Task success and groundedness evaluators."""

from evals.evaluators.arguments import score_arguments, tool_result_payloads
from evals.evaluators.tool_selection import score_forbidden_action, score_tool_selection
from evals.models import CaseTrace, EvalCase


def score_groundedness(case: EvalCase, trace: CaseTrace) -> bool:
    """Return True when required facts appear in successful tool payloads."""
    if not case.required_facts:
        return True
    payload_text = tool_result_payloads(trace).lower()
    return all(fact.lower() in payload_text for fact in case.required_facts)


def score_task_success(case: EvalCase, trace: CaseTrace) -> bool:
    """Return True when the case solved the task with structured correctness."""
    if trace.response_status != case.success_status:
        return False
    if not score_tool_selection(case, trace):
        return False
    if not score_forbidden_action(case, trace):
        return False
    if not score_arguments(case, trace):
        return False
    if not score_groundedness(case, trace):
        return False
    return True

"""Test-the-tester cases for the eval regression gate."""

from pathlib import Path

import pytest

from agent_platform.models.identity import INVESTIGATION_AGENT
from evals.runner import (
    DEFAULT_BASELINE as RUNNER_BASELINE,
)
from evals.runner import (
    BrokenPolicyCaseRunner,
    GovernedCaseRunner,
    run_eval_suite,
)


@pytest.fixture
def fixture_agent_that_skips_approval() -> BrokenPolicyCaseRunner:
    """Return a runner that bypasses approval enforcement."""
    return BrokenPolicyCaseRunner()


async def test_runner_fails_on_policy_violation(
    fixture_agent_that_skips_approval: BrokenPolicyCaseRunner,
) -> None:
    """Broken passthrough agent must fail policy compliance on write cases."""
    report = await run_eval_suite(
        fixture_agent_that_skips_approval,
        dataset="policy_cases",
    )
    assert report.policy_compliance < 1.0
    assert report.gate_passed is False


async def test_accept_baseline_does_not_write_on_failure(
    fixture_agent_that_skips_approval: BrokenPolicyCaseRunner,
    tmp_path: Path,
) -> None:
    """A failing run must not update the baseline file."""
    target = tmp_path / "baseline.json"
    report = await run_eval_suite(
        fixture_agent_that_skips_approval,
        dataset="policy_cases",
        baseline_path=target,
    )
    assert report.gate_passed is False
    assert not target.exists()


async def test_investigation_dataset_never_calls_reroute() -> None:
    """Investigation agent eval must never invoke request_reroute."""
    report = await run_eval_suite(
        GovernedCaseRunner(mode="deterministic"),
        dataset="all",
        agent_id=INVESTIGATION_AGENT,
        mode="deterministic",
    )
    assert report.gate_passed is True
    assert all("request_reroute" not in case.tool_names for case in report.cases)
    assert all(case.scores.forbidden_action for case in report.cases)
    assert all(case.scores.policy for case in report.cases)


async def test_deterministic_main_agent_meets_baseline() -> None:
    """Scripted main-agent run must pass the stored baseline gate."""
    report = await run_eval_suite(
        GovernedCaseRunner(mode="deterministic"),
        dataset="all",
        mode="deterministic",
        baseline_path=RUNNER_BASELINE,
    )
    assert report.policy_compliance == 1.0
    assert report.schema_validity == 1.0
    assert report.gate_passed is True

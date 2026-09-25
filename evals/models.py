"""Pydantic models for evaluation cases, traces, and reports."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from agent_platform.models.audit import AuditEvent
from agent_platform.models.run import UsageCounters
from agent_platform.runtime.tool_executor import ToolCallRecord


class ArgumentCheck(BaseModel):
    """Structured argument assertion for one tool call."""

    tool: str
    path: str
    equals: str | float | bool | None = None
    lte: float | None = None


class ExpectedTrajectory(BaseModel):
    """Expected tool-call behavior for one eval case."""

    required_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    ordered_tools: list[str] = Field(default_factory=list)
    max_tool_calls: int | None = None
    requires_approval: bool | None = None


class EvalCase(BaseModel):
    """One evaluation scenario loaded from YAML."""

    case_id: str
    description: str
    user_message: str
    expected: ExpectedTrajectory
    required_facts: list[str] = Field(default_factory=list)
    argument_checks: list[ArgumentCheck] = Field(default_factory=list)
    success_status: Literal["completed", "waiting_for_approval", "failed"] = "completed"
    tags: list[str] = Field(default_factory=list)
    scripted_steps: list[dict[str, Any]] = Field(default_factory=list)


class CaseEvaluatorScores(BaseModel):
    """Per-evaluator pass/fail for one case."""

    tool_selection: bool = False
    forbidden_action: bool = False
    arguments: bool = False
    schema_validity: bool = False
    trajectory: bool = False
    policy: bool = False
    task_success: bool = False
    groundedness: bool = False


class CaseResult(BaseModel):
    """Scored outcome for one eval case."""

    case_id: str
    scores: CaseEvaluatorScores
    tool_names: list[str] = Field(default_factory=list)
    response_status: str = ""
    latency_seconds: float = 0.0
    usage: UsageCounters = Field(default_factory=UsageCounters)


class CaseTrace(BaseModel):
    """Captured execution data for one eval case run."""

    case_id: str
    tool_names: list[str] = Field(default_factory=list)
    records: list[ToolCallRecord] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)
    response_status: str = ""
    usage: UsageCounters = Field(default_factory=UsageCounters)
    latency_seconds: float = 0.0
    applied_reroute_count_before: int = 0
    applied_reroute_count_after: int = 0
    pending_tool_name: str | None = None

    model_config = {"arbitrary_types_allowed": True}


class GateCheck(BaseModel):
    """One baseline comparison check."""

    name: str
    passed: bool
    actual: float
    op: str
    limit: float


class BaselineMetrics(BaseModel):
    """Stored baseline aggregate metrics."""

    dataset_version: str
    model: str
    task_success: float
    tool_selection_accuracy: float
    policy_compliance: float
    schema_validity: float
    avg_tool_calls: float
    avg_estimated_cost_usd: float


class EvalReport(BaseModel):
    """Aggregate report for one eval suite run."""

    dataset_version: str = "v1"
    model: str = "scripted-test"
    agent_id: str = "shipment-recovery-agent"
    mode: str = "deterministic"
    dataset: str = "all"
    case_count: int = 0
    task_success: float = 0.0
    tool_selection_accuracy: float = 0.0
    policy_compliance: float = 0.0
    schema_validity: float = 0.0
    avg_tool_calls: float = 0.0
    avg_estimated_cost_usd: float = 0.0
    avg_latency_seconds: float = 0.0
    gate_passed: bool = False
    gate_checks: list[GateCheck] = Field(default_factory=list)
    cases: list[CaseResult] = Field(default_factory=list)

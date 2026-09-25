"""Deterministic policy engine for governed tool calls."""

import uuid
from collections.abc import Callable
from datetime import datetime

from pydantic import BaseModel

from agent_platform.mcp.protocol import (
    APPROVAL_ALREADY_CONSUMED,
    APPROVAL_ARGUMENTS_MISMATCH,
    APPROVAL_EXPIRED,
    APPROVAL_REJECTED,
    APPROVAL_RUN_MISMATCH,
    DELEGATION_EXPIRED,
    POLICY_ALLOWED,
    POLICY_MISSING_SCOPE,
    REROUTE_COST_LIMIT,
    RUN_BUDGET_EXCEEDED,
    RUN_NOT_FOUND,
    SIDE_EFFECT_APPROVAL_REQUIRED,
)
from agent_platform.mcp.registry import RegisteredTool
from agent_platform.mcp.schemas import RequestRerouteInput
from agent_platform.models.audit import AuditEvent
from agent_platform.models.execution import ExecutionContext
from agent_platform.models.policy import PolicyDecision
from agent_platform.models.run import RunState
from agent_platform.persistence.base import ApprovalStore, AuditStore, RunStore
from agent_platform.policy.approvals import create_approval_request, evaluate_approval_match
from agent_platform.policy.rules import (
    budget_would_be_exceeded,
    delegation_is_expired,
    missing_scopes,
    reroute_cost_exceeds_limit,
    scopes_satisfied,
    utc_now,
)
from agent_platform.policy.settings import PolicySettings

Clock = Callable[[], datetime]


class PolicyEngine:
    """Evaluate tool calls against scopes, budgets, cost limits, and approvals."""

    def __init__(
        self,
        *,
        run_store: RunStore,
        approval_store: ApprovalStore,
        audit_store: AuditStore,
        settings: PolicySettings | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Store dependencies and optional settings overrides."""
        self._run_store = run_store
        self._approval_store = approval_store
        self._audit_store = audit_store
        self._settings = settings or PolicySettings()
        self._clock = clock or utc_now

    async def evaluate_tool_call(
        self,
        tool: RegisteredTool,
        args: BaseModel,
        context: ExecutionContext,
    ) -> PolicyDecision:
        """Evaluate one tool call and return a policy decision."""
        now = self._clock()
        tool_name = tool.name

        if delegation_is_expired(context.delegation, now):
            decision = self._deny(
                DELEGATION_EXPIRED,
                "Delegation has expired.",
                matched_rules=["delegation-expiry"],
            )
            await self._audit(context, tool_name, "policy.denied", decision.reason_code)
            return decision

        if not scopes_satisfied(tool.policy.required_scopes, context.delegation.scopes):
            missing = missing_scopes(tool.policy.required_scopes, context.delegation.scopes)
            decision = self._deny(
                POLICY_MISSING_SCOPE,
                "Caller lacks required scopes.",
                matched_rules=["scope-required"],
                missing_scopes=missing,
            )
            await self._audit(context, tool_name, "policy.denied", decision.reason_code)
            return decision

        run = await self._run_store.get_run(context.run_id)
        if run is None:
            decision = self._deny(
                RUN_NOT_FOUND,
                "Run state was not found.",
                matched_rules=["run-exists"],
            )
            await self._audit(context, tool_name, "policy.denied", decision.reason_code)
            return decision

        if budget_would_be_exceeded(run, context.budget, now):
            decision = self._deny(
                RUN_BUDGET_EXCEEDED,
                "Run budget would be exceeded.",
                matched_rules=["run-budget"],
            )
            await self._audit(context, tool_name, "budget.exceeded", decision.reason_code)
            return decision

        if reroute_cost_exceeds_limit(
            tool.policy,
            args,
            self._settings.reroute_cost_limit_eur,
        ):
            decision = self._deny(
                REROUTE_COST_LIMIT,
                "Reroute cost exceeds the allowed limit.",
                matched_rules=["cost-limit"],
            )
            await self._audit(context, tool_name, "policy.denied", decision.reason_code)
            return decision

        if tool.policy.requires_approval:
            approval_id = _approval_id_from_args(args)
            stored = await self._approval_store.get(approval_id) if approval_id else None
            match = evaluate_approval_match(
                stored,
                tool_name=tool_name,
                arguments=args,
                context=context,
                now=now,
            )

            if match == "match":
                decision = PolicyDecision(
                    decision="allow",
                    reason_code=POLICY_ALLOWED,
                    message="Policy allowed the tool call.",
                    matched_rules=["write-action", "approval-bound"],
                )
                await self._increment_tool_calls(run, now)
                await self._audit(context, tool_name, "policy.allowed", decision.reason_code)
                return decision

            if match == "pending":
                if stored is None:
                    msg = "pending approval match requires a stored record"
                    raise RuntimeError(msg)
                decision = PolicyDecision(
                    decision="require_approval",
                    reason_code=SIDE_EFFECT_APPROVAL_REQUIRED,
                    message="Side-effect action requires human approval.",
                    matched_rules=["write-action", "reroute-approval"],
                    approval=stored,
                )
                await self._audit(
                    context,
                    tool_name,
                    "approval.requested",
                    decision.reason_code,
                )
                return decision

            if match in {"run_mismatch", "agent_mismatch"}:
                code = APPROVAL_RUN_MISMATCH
                decision = self._deny(
                    code,
                    "Approval does not belong to this run or agent.",
                    matched_rules=["approval-run-match"],
                )
                await self._audit(context, tool_name, "policy.denied", decision.reason_code)
                return decision

            if match == "arguments_mismatch":
                decision = self._deny(
                    APPROVAL_ARGUMENTS_MISMATCH,
                    "Approval does not match the requested action arguments.",
                    matched_rules=["approval-arguments-match"],
                )
                await self._audit(context, tool_name, "policy.denied", decision.reason_code)
                return decision

            if match == "expired":
                decision = self._deny(
                    APPROVAL_EXPIRED,
                    "Approval has expired.",
                    matched_rules=["approval-not-expired"],
                )
                await self._audit(context, tool_name, "policy.denied", decision.reason_code)
                return decision

            if match == "consumed":
                decision = self._deny(
                    APPROVAL_ALREADY_CONSUMED,
                    "Approval was already consumed.",
                    matched_rules=["approval-not-consumed"],
                )
                await self._audit(context, tool_name, "policy.denied", decision.reason_code)
                return decision

            if match == "rejected":
                decision = self._deny(
                    APPROVAL_REJECTED,
                    "Approval was rejected.",
                    matched_rules=["approval-not-rejected"],
                )
                await self._audit(context, tool_name, "policy.denied", decision.reason_code)
                return decision

            pending = create_approval_request(
                tool_name=tool_name,
                arguments=args,
                context=context,
                now=now,
                ttl_seconds=self._settings.approval_ttl_seconds,
                approval_id=approval_id if approval_id and stored is None else None,
            )
            await self._approval_store.create(pending)
            run = run.model_copy(
                update={
                    "status": "waiting_for_approval",
                    "pending_approval_id": pending.approval_id,
                    "updated_at": now,
                },
            )
            await self._run_store.update_run(run)
            decision = PolicyDecision(
                decision="require_approval",
                reason_code=SIDE_EFFECT_APPROVAL_REQUIRED,
                message="Side-effect action requires human approval.",
                matched_rules=["write-action", "reroute-approval"],
                approval=pending,
            )
            await self._audit(context, tool_name, "approval.requested", decision.reason_code)
            return decision

        decision = PolicyDecision(
            decision="allow",
            reason_code=POLICY_ALLOWED,
            message="Policy allowed the tool call.",
            matched_rules=["read-action"],
        )
        await self._increment_tool_calls(run, now)
        await self._audit(context, tool_name, "policy.allowed", decision.reason_code)
        return decision

    async def consume_approval_after_success(
        self,
        tool_name: str,
        args: BaseModel,
        context: ExecutionContext,
    ) -> None:
        """Consume a matching approval after a successful side-effect call."""
        approval_id = _approval_id_from_args(args)
        if approval_id is None:
            return
        await self._approval_store.consume(approval_id)
        now = self._clock()
        await self._audit(
            context,
            tool_name,
            "tool.completed",
            "APPROVAL_CONSUMED",
            outcome="success",
            metadata={"approval_id": approval_id},
            timestamp=now,
        )

    async def _increment_tool_calls(self, run: RunState, now: datetime) -> None:
        usage = run.usage.model_copy(update={"tool_calls": run.usage.tool_calls + 1})
        updated = run.model_copy(
            update={
                "usage": usage,
                "status": "running",
                "updated_at": now,
            },
        )
        await self._run_store.update_run(updated)

    async def _audit(
        self,
        context: ExecutionContext,
        tool_name: str,
        event_type: str,
        decision: str,
        *,
        outcome: str | None = None,
        metadata: dict[str, str | int | float | bool | None] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        now = timestamp or self._clock()
        event = AuditEvent(
            event_id=f"evt-{uuid.uuid4().hex[:12]}",
            run_id=context.run_id,
            event_type=event_type,
            actor_id=context.delegation.actor.actor_id,
            agent_id=context.agent_id,
            tool_name=tool_name,
            decision=decision,
            outcome=outcome,
            timestamp=now,
            trace_id=context.trace_id,
            metadata=metadata or {},
        )
        await self._audit_store.append(event)

    @staticmethod
    def _deny(
        reason_code: str,
        message: str,
        *,
        matched_rules: list[str],
        missing_scopes: list[str] | None = None,
    ) -> PolicyDecision:
        return PolicyDecision(
            decision="deny",
            reason_code=reason_code,
            message=message,
            matched_rules=matched_rules,
            missing_scopes=missing_scopes or [],
        )


def _approval_id_from_args(args: BaseModel) -> str | None:
    """Extract approval_id from request_reroute arguments when present."""
    if isinstance(args, RequestRerouteInput):
        return args.approval_id
    approval_id = getattr(args, "approval_id", None)
    if isinstance(approval_id, str) and approval_id:
        return approval_id
    return None

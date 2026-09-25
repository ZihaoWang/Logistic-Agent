"""Google ADK agent runtime adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from opentelemetry.trace import Span

from agent_platform.mcp.registry import (
    CHECK_SHIPPING_POLICY,
    ESTIMATE_ROUTE_COST,
    FIND_ROUTE_ALTERNATIVES,
    GET_PORT_STATUS,
    GET_SHIPMENT,
    REQUEST_REROUTE,
)
from agent_platform.models.approval import ApprovalRequest
from agent_platform.models.execution import ExecutionContext
from agent_platform.observability.metrics import record_model_call
from agent_platform.observability.tracing import activate_span, deactivate_span, set_span_attributes
from agent_platform.persistence.base import RunStore
from agent_platform.runtime.base import AgentRequest, AgentResponse
from agent_platform.runtime.messages import message_for_approval_required, message_for_tool_result
from agent_platform.runtime.settings import RuntimeSettings
from agent_platform.runtime.tool_executor import GovernedToolExecutor, ToolCallRecord

AGENT_INSTRUCTION = """You are a shipment exception assistant.

Use tools for shipment facts. Do not invent shipment, route, port, cost,
or policy information.

Before proposing a reroute:
1. inspect the shipment;
2. inspect relevant disruption information;
3. find route alternatives;
4. estimate cost for the selected route;
5. check shipping policy.

Never claim a reroute was applied unless request_reroute returns success.
If a write action requires approval, explain the exact action and wait.
"""


_SERVICE = "agent-web"


@dataclass
class RunSessionState:
    """Mutable state shared with ADK function tools during one run."""

    context: ExecutionContext
    tool_calls: list[str] = field(default_factory=list)
    records: list[ToolCallRecord] = field(default_factory=list)
    halt_for_approval: bool = False
    pending_approval: ApprovalRequest | None = None
    pending_tool_call: dict[str, Any] | None = None
    failed: bool = False
    failure_message: str | None = None
    model_span: Span | None = None
    model_span_token: object | None = None
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class AdkAgentRuntime:
    """Run governed MCP tools through a Google ADK LlmAgent."""

    def __init__(
        self,
        executor: GovernedToolExecutor,
        run_store: RunStore,
        *,
        model: str | BaseLlm | None = None,
        settings: RuntimeSettings | None = None,
    ) -> None:
        """Store dependencies and optional model override for tests."""
        self._executor = executor
        self._run_store = run_store
        resolved_settings = settings or RuntimeSettings()
        self._settings = resolved_settings
        self._model: str | BaseLlm = model or resolved_settings.model_name
        self._model_name = self._model if isinstance(self._model, str) else self._model.model

    async def run(
        self,
        request: AgentRequest,
        context: ExecutionContext,
    ) -> AgentResponse:
        """Execute one agent turn and return a platform response."""
        session_state = RunSessionState(context=context)
        tools = self._build_tools(session_state)
        agent = LlmAgent(
            name=_adk_node_name(context.agent_id),
            model=self._model,
            instruction=AGENT_INSTRUCTION,
            tools=tools,
            before_model_callback=self._before_model_callback(session_state),
            after_model_callback=self._after_model_callback(session_state),
        )
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="agent-platform",
            session_service=session_service,
        )
        session = await session_service.create_session(
            app_name="agent-platform",
            user_id=context.delegation.actor.actor_id,
        )

        final_text = ""
        async for event in runner.run_async(
            user_id=context.delegation.actor.actor_id,
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=request.message)],
            ),
        ):
            if event.content is not None and event.content.role == "model":
                for part in event.content.parts or []:
                    if part.text:
                        final_text = part.text
            if session_state.halt_for_approval or session_state.failed:
                break

        await self._record_model_usage(
            context.run_id,
            session_state.model_calls,
            session_state.input_tokens,
            session_state.output_tokens,
        )

        if session_state.halt_for_approval and session_state.pending_approval is not None:
            cost = _expected_cost_from_tool_call(session_state.pending_tool_call)
            await self._update_run(
                context.run_id,
                status="waiting_for_approval",
                pending_approval_id=session_state.pending_approval.approval_id,
                pending_tool_call=session_state.pending_tool_call,
            )
            return AgentResponse(
                run_id=context.run_id,
                message=message_for_approval_required(cost),
                status="waiting_for_approval",
                pending_approval=session_state.pending_approval,
            )

        if session_state.failed:
            await self._update_run(
                context.run_id,
                status="failed",
                last_error_code="TOOL_FAILED",
            )
            return AgentResponse(
                run_id=context.run_id,
                message=session_state.failure_message
                or (
                    "Something went wrong while handling your request. "
                    "No shipment change was made."
                ),
                status="failed",
            )

        await self._update_run(context.run_id, status="completed")
        return AgentResponse(
            run_id=context.run_id,
            message=final_text or "I completed the request.",
            status="completed",
        )

    def _before_model_callback(
        self,
        session_state: RunSessionState,
    ) -> Any:
        """Return ADK callback that opens a model.generate span."""

        def callback(_ctx: CallbackContext, _request: LlmRequest) -> LlmResponse | None:
            span, token = activate_span(
                "model.generate",
                service=_SERVICE,
                attributes={
                    "run.id": session_state.context.run_id,
                    "agent.id": session_state.context.agent_id,
                    "model.name": self._model_name,
                },
            )
            session_state.model_span = span
            session_state.model_span_token = token
            return None

        return callback

    def _after_model_callback(
        self,
        session_state: RunSessionState,
    ) -> Any:
        """Return ADK callback that closes model.generate and records metrics."""

        def callback(_ctx: CallbackContext, response: LlmResponse) -> LlmResponse | None:
            input_tokens = 0
            output_tokens = 0
            usage = response.usage_metadata
            if usage is not None:
                input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
                output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
                session_state.model_calls += 1
                session_state.input_tokens += input_tokens
                session_state.output_tokens += output_tokens

            estimated_cost: float | None = None
            if input_tokens or output_tokens:
                estimated_cost = (
                    input_tokens / 1000 * self._settings.model_input_cost_per_1k_tokens_usd
                    + output_tokens / 1000 * self._settings.model_output_cost_per_1k_tokens_usd
                )

            if session_state.model_span is not None:
                attrs: dict[str, object] = {
                    "model.input_tokens": input_tokens,
                    "model.output_tokens": output_tokens,
                }
                if estimated_cost is not None:
                    attrs["estimated_cost_usd"] = round(estimated_cost, 6)
                set_span_attributes(session_state.model_span, attrs)
                if session_state.model_span_token is not None:
                    deactivate_span(session_state.model_span, session_state.model_span_token)
                session_state.model_span = None
                session_state.model_span_token = None

            if session_state.model_calls > 0:
                record_model_call(
                    service=_SERVICE,
                    model=self._model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            return None

        return callback

    def _build_tools(self, session_state: RunSessionState) -> list[Any]:
        """Build ADK function tools filtered by delegation scopes."""
        allowed = set(self._executor.allowed_tool_names(session_state.context))
        tools: list[Any] = []

        if GET_SHIPMENT in allowed:

            async def get_shipment(shipment_id: str) -> str:
                """Return one shipment by id."""
                return await self._invoke_tool(
                    session_state,
                    GET_SHIPMENT,
                    {"shipment_id": shipment_id},
                )

            tools.append(get_shipment)

        if GET_PORT_STATUS in allowed:

            async def get_port_status(port_code: str) -> str:
                """Return current status for one port."""
                return await self._invoke_tool(
                    session_state,
                    GET_PORT_STATUS,
                    {"port_code": port_code},
                )

            tools.append(get_port_status)

        if FIND_ROUTE_ALTERNATIVES in allowed:

            async def find_route_alternatives(
                shipment_id: str,
                max_additional_cost_eur: float | None = None,
                max_delay_hours: float | None = None,
                require_capacity: bool = True,
                max_results: int = 5,
            ) -> str:
                """Search route alternatives for a shipment."""
                return await self._invoke_tool(
                    session_state,
                    FIND_ROUTE_ALTERNATIVES,
                    {
                        "shipment_id": shipment_id,
                        "max_additional_cost_eur": max_additional_cost_eur,
                        "max_delay_hours": max_delay_hours,
                        "require_capacity": require_capacity,
                        "max_results": max_results,
                    },
                )

            tools.append(find_route_alternatives)

        if ESTIMATE_ROUTE_COST in allowed:

            async def estimate_route_cost(shipment_id: str, route_id: str) -> str:
                """Estimate additional cost for a shipment route."""
                return await self._invoke_tool(
                    session_state,
                    ESTIMATE_ROUTE_COST,
                    {"shipment_id": shipment_id, "route_id": route_id},
                )

            tools.append(estimate_route_cost)

        if CHECK_SHIPPING_POLICY in allowed:

            async def check_shipping_policy(shipment_id: str, route_id: str) -> str:
                """Check business shipping policy for a shipment and route."""
                return await self._invoke_tool(
                    session_state,
                    CHECK_SHIPPING_POLICY,
                    {"shipment_id": shipment_id, "route_id": route_id},
                )

            tools.append(check_shipping_policy)

        if REQUEST_REROUTE in allowed:

            async def request_reroute(
                shipment_id: str,
                route_id: str,
                expected_additional_cost_eur: float,
            ) -> str:
                """Request a reroute action for a shipment."""
                return await self._invoke_tool(
                    session_state,
                    REQUEST_REROUTE,
                    {
                        "shipment_id": shipment_id,
                        "route_id": route_id,
                        "expected_additional_cost_eur": expected_additional_cost_eur,
                    },
                )

            tools.append(request_reroute)

        return tools

    async def _invoke_tool(
        self,
        session_state: RunSessionState,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Execute one governed tool call and serialize the result for the model."""
        outcome = await self._executor.execute(
            tool_name,
            arguments,
            session_state.context,
        )
        record = outcome.records[-1]
        session_state.tool_calls.append(tool_name)
        session_state.records.append(record)

        result = outcome.result
        if result.status == "approval_required" and result.approval is not None:
            session_state.halt_for_approval = True
            session_state.pending_approval = result.approval
            session_state.pending_tool_call = {
                "tool_name": tool_name,
                "arguments": record.arguments,
            }
            return json.dumps({"status": "approval_required"})

        if result.status in {"failed", "denied"}:
            session_state.failed = True
            session_state.failure_message = message_for_tool_result(tool_name, result)
            return json.dumps({"status": result.status})

        return json.dumps({"status": "success", "data": result.data}, default=str)

    async def _record_model_usage(
        self,
        run_id: str,
        model_calls: int,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Increment model call counters on the run."""
        if model_calls <= 0:
            return
        run = await self._run_store.get_run(run_id)
        if run is None:
            return
        estimated_cost = (
            input_tokens / 1000 * self._settings.model_input_cost_per_1k_tokens_usd
            + output_tokens / 1000 * self._settings.model_output_cost_per_1k_tokens_usd
        )
        usage = run.usage.model_copy(
            update={
                "model_calls": run.usage.model_calls + model_calls,
                "input_tokens": run.usage.input_tokens + input_tokens,
                "output_tokens": run.usage.output_tokens + output_tokens,
                "estimated_cost_usd": run.usage.estimated_cost_usd + estimated_cost,
            },
        )
        await self._run_store.update_run(
            run.model_copy(
                update={
                    "usage": usage,
                    "model_name": self._model_name,
                },
            ),
        )

    async def _update_run(
        self,
        run_id: str,
        *,
        status: str,
        pending_approval_id: str | None = None,
        pending_tool_call: dict[str, Any] | None = None,
        last_error_code: str | None = None,
    ) -> None:
        """Persist run status updates after an agent turn."""
        run = await self._run_store.get_run(run_id)
        if run is None:
            return
        from agent_platform.policy.rules import utc_now

        updates: dict[str, Any] = {
            "status": status,
            "updated_at": utc_now(),
            "model_name": self._model_name,
        }
        if pending_approval_id is not None:
            updates["pending_approval_id"] = pending_approval_id
        if pending_tool_call is not None:
            updates["pending_tool_call"] = pending_tool_call
        if last_error_code is not None:
            updates["last_error_code"] = last_error_code
        await self._run_store.update_run(run.model_copy(update=updates))


def _adk_node_name(agent_id: str) -> str:
    """Return an ADK-safe node name for a platform agent id."""
    return agent_id.replace("-", "_")


def _expected_cost_from_tool_call(pending_tool_call: dict[str, Any] | None) -> float:
    """Extract expected reroute cost from a stored pending tool call."""
    if pending_tool_call is None:
        return 0.0
    arguments = pending_tool_call.get("arguments", {})
    raw = arguments.get("expected_additional_cost_eur", 0.0)
    return float(raw)

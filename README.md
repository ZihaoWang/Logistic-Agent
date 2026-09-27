# Logistics Agent Platform

A production-oriented reference implementation for building, governing, observing, and evaluating MCP-based AI agents.

The project uses a synthetic logistics scenario: an AI agent investigates shipment delays, searches alternative routes, evaluates rerouting options, and requests human approval before executing side-effect actions.

The focus is not chatbot UX. It is the engineering around production agents:

- typed MCP contracts
- identity- and scope-based tool authorization
- human approval for side effects
- retries, timeouts, budgets, and idempotency
- structured audit events
- OpenTelemetry tracing and metrics
- deterministic agent evaluation and regression gates
- multiple agent identities sharing the same governance layer

> **Status:** Local runtime, governance, observability, and deterministic evaluation are implemented and tested.
> GCP deployment and GitHub CI/CD are in progress.

## Architecture

```mermaid
flowchart LR
    User[User] --> Agent[ADK Agent]

    Agent --> MCP[MCP Gateway]

    MCP --> Policy[Policy Engine]
    Policy --> Approval[Approval Store]

    MCP --> API[Logistics API]
    API --> Repo[(Repository)]

    Agent --> Obs[OpenTelemetry]
    MCP --> Obs
    API --> Obs

    Agent --> Audit[Audit Events]

    Eval[Evaluation Runner] --> Agent
    Eval --> MCP
    Eval --> Policy
```
The agent never accesses logistics data directly. All domain operations go through typed MCP tools and the shared governance layer. Side-effect actions such as rerouting require policy authorization and human approval.

## What is implemented

| Area | Implementation |
|---|---|
| Logistics backend | Deterministic FastAPI service with synthetic shipment, port, and route data |
| MCP | Six typed tools with Pydantic input/output contracts |
| Governance | Identity, scopes, policy checks, tool-call budgets, and approval gates |
| Side effects | Idempotent rerouting protected by argument-bound human approval |
| Agent runtime | Google ADK runtime with governed MCP tool execution |
| Multi-agent | Main agent + read-only investigation agent sharing the same governance layer |
| Reliability | Retry, timeout, quota, and budget enforcement |
| Observability | Structured logs, OpenTelemetry traces, metrics, audit events, run/trace correlation |
| Evaluation | Deterministic scripted agent evaluation with regression baselines |
| Testing | Unit, contract, policy, integration, and end-to-end tests |

## Quick Start

### Prerequisites

You need:

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- Docker and Docker Compose (only required for local observability)

The deterministic test and evaluation paths do **not** require Gemini or GCP
credentials.

### 1. Install

Clone the repository and install the development environment:

```bash
git clone <repository-url>
cd <repository-name>

./scripts/dev.sh install
```

This installs the Python dependencies and Git pre-commit hooks.

### 2. Run static checks and tests

```bash
./scripts/dev.sh lint
./scripts/dev.sh test
```

The lint command runs Ruff, mypy, and Bandit. The test suite covers unit,
contract, policy, integration, and end-to-end behavior.

### 3. Run the deterministic agent evaluation

The evaluation suite uses a scripted model, so no API key is required.

Run the main shipment recovery agent:

```bash
uv run python -m evals.runner \
  --mode deterministic \
  --agent shipment-recovery-agent \
  --dataset all
```

Run the read-only investigation agent:

```bash
uv run python -m evals.runner \
  --mode deterministic \
  --agent investigation-agent \
  --dataset all
```

The suite contains 26 cases covering normal tool use, route comparison,
approval flows, policy violations, adversarial requests, and recovery cases.

Unlike prompt-based tests, these evaluations assert on structured agent
behavior including tool selection, arguments, execution trajectory, policy
compliance, schema validity, task success, and cost.

Both agents execute through the real governed runtime:

```text
Scripted model
    ↓
RunCoordinator
    ↓
GovernedToolExecutor
    ↓
MCP tools
    ↓
PolicyEngine
    ↓
Logistics backend
```

Only the model is replaced by a deterministic scripted implementation.

### 4. Run the logistics API

Start the deterministic logistics backend:

```bash
uv run uvicorn apps.logistics_api.main:app \
  --host 127.0.0.1 \
  --port 8002
```

In another terminal:

```bash
curl -sf http://127.0.0.1:8002/health

curl -sf \
  http://127.0.0.1:8002/v1/shipments/ABC123
```

You can also search for alternative routes:

```bash
curl -sf -X POST \
  http://127.0.0.1:8002/v1/routes/search \
  -H 'Content-Type: application/json' \
  -d '{
    "shipment_id": "ABC123",
    "constraints": {
      "max_additional_cost_eur": 2000,
      "max_delay_hours": 24
    }
  }'
```

All logistics data is synthetic and loaded from the repository.

### 5. Optional: local observability

Start the OpenTelemetry Collector and Jaeger:

```bash
./scripts/dev.sh local-up
```

Configure the application to export traces:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317
```

Run the application and execute a request. Traces can then be inspected in
Jaeger at:

```text
http://127.0.0.1:16686
```

The trace shows the request across the agent, MCP execution, policy decisions,
and backend calls.

Stop the observability stack with:

```bash
./scripts/dev.sh local-down
```

### Live Gemini agent

The live ADK/Gemini path requires either a Gemini API key or Google Cloud
Application Default Credentials.

The deterministic test and evaluation paths above are the recommended way to
explore the repository without external credentials.

## Evaluation

The project treats agent behavior as a testable system rather than relying on exact model wording.

The deterministic evaluation suite runs scripted model behavior through the real MCP, policy, approval, audit, and execution stack.

It currently includes 26 cases evaluated across:

- tool selection
- forbidden actions
- tool arguments
- execution trajectory
- policy compliance
- task success
- factual grounding
- cost

Run the regression suite:

```bash
python -m evals.runner --mode deterministic
```

## Governance and safety

Tool execution is governed independently of the LLM.

Each request carries an execution context containing agent identity, delegated user identity, scopes, budgets, and trace information.

Read operations require explicit scopes. Side-effect operations additionally require policy authorization and a human approval bound to the exact action arguments.

For example:

main-agent
    → shipment:read
    → route:read
    → shipment:reroute
    → approval required

investigation-agent
    → shipment:read
    → port:read
    → route:read
    → reroute denied

The model cannot bypass these controls by changing its prompt or tool-call arguments. Authorization is enforced at the tool execution boundary.

## Observability

Every agent run is correlated across services using trace and run IDs.

The platform currently provides:

- structured JSON logs
- OpenTelemetry traces
- explicit agent and tool spans
- metrics and error categories
- audit events
- agent identity in traces
- local Jaeger visualization

This makes it possible to reconstruct:

User request
→ agent reasoning step
→ MCP tool call
→ policy decision
→ backend request
→ approval / denial
→ final result

## Disclaimer

Synthetic logistics domain. No proprietary code or data.

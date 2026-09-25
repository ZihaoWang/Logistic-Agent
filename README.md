# agent-platform-reference

Reference implementation of a governed logistics agent platform.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package and project manager)
- Python 3.12 (installed automatically by `uv` if missing)

## Quick start

```bash
./scripts/dev.sh install   # install deps and git hooks
./scripts/dev.sh lint      # ruff, mypy, bandit
./scripts/dev.sh test      # pytest
```

Run all pre-commit hooks without committing:

```bash
./scripts/dev.sh precommit
```

## logistics-api (Phase 1)

Start the deterministic logistics backend on port 8002:

```bash
uv run uvicorn apps.logistics_api.main:app --port 8002
```

Demo calls using the synthetic shipment `ABC123`:

```bash
# Health check
curl http://localhost:8002/health

# Get the delayed demo shipment
curl http://localhost:8002/v1/shipments/ABC123

# Port congestion at Rotterdam
curl http://localhost:8002/v1/ports/NLRTM/status

# Find routes under EUR 2000 and within 24 hours of planned ETA
curl -X POST http://localhost:8002/v1/routes/search \
  -H 'Content-Type: application/json' \
  -d '{"shipment_id":"ABC123","constraints":{"max_additional_cost_eur":2000,"max_delay_hours":24}}'

# Estimate cost for the demo route R-102 (EUR 1450)
curl -X POST http://localhost:8002/v1/routes/cost \
  -H 'Content-Type: application/json' \
  -d '{"shipment_id":"ABC123","route_id":"R-102"}'

# Check shipping policy
curl -X POST http://localhost:8002/v1/policy/check \
  -H 'Content-Type: application/json' \
  -d '{"shipment_id":"ABC123","route_id":"R-102"}'

# Reroute (idempotent — repeat with the same idempotency_key returns already_applied)
curl -X POST http://localhost:8002/v1/shipments/ABC123/reroute \
  -H 'Content-Type: application/json' \
  -d '{"route_id":"R-102","idempotency_key":"key-abc-1","expected_additional_cost_eur":1450.0}'
```

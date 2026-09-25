#!/usr/bin/env bash
set -euo pipefail

cmd="${1:-help}"
shift || true

case "$cmd" in
  install)
    uv sync
    uv run pre-commit install
    ;;
  lint)
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy .
    uv run bandit -c pyproject.toml -r agent_platform mcp_server apps
    ;;
  fmt)
    uv run ruff format .
    uv run ruff check --fix .
    ;;
  test)
    uv run pytest "$@"
    ;;
  local-up)
    docker compose up -d
    ;;
  local-down)
    docker compose down
    ;;
  precommit)
    uv run pre-commit run --all-files
    ;;
  help|*)
    cat <<'EOF'
Usage: scripts/dev.sh {install|lint|fmt|test|local-up|local-down|precommit}

Local observability:
  ./scripts/dev.sh local-up
  export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317
  uv run python -m apps.agent_web.main
  Open Jaeger UI at http://127.0.0.1:16686
EOF
    ;;
esac

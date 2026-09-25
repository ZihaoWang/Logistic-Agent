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
  precommit)
    uv run pre-commit run --all-files
    ;;
  help|*)
    echo "Usage: scripts/dev.sh {install|lint|fmt|test|precommit}"
    ;;
esac

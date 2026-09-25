# agent-platform-reference

Reference implementation of a governed logistics agent platform. Phase 0 is
repository scaffolding only — no business logic yet.

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

"""FastAPI application entry point for logistics-api."""

from pathlib import Path

from fastapi import FastAPI

from apps.logistics_api.repository import BaseRepository, InMemoryLogisticsRepository
from apps.logistics_api.routes import router


def default_data_dir() -> Path:
    """Return the path to the checked-in data directory.

    Returns:
        Absolute path to the data/ folder at the repository root.
    """
    return Path(__file__).resolve().parents[2] / "data"


def create_app(repo: BaseRepository | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Usage:
        app = create_app()
        uvicorn apps.logistics_api.main:app --port 8002

    Parameters:
        repo: Optional repository override for tests.

    Returns:
        A configured FastAPI application instance.
    """
    app = FastAPI(title="logistics-api", version="0.1.0")
    app.state.repository = repo or InMemoryLogisticsRepository.from_data_dir(default_data_dir())
    app.include_router(router)
    return app


app = create_app()

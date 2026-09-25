"""FastAPI application entry point for agent-web."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from apps.agent_web.api import router


def create_app() -> FastAPI:
    """Create and configure the agent-web FastAPI application."""
    app = FastAPI(title="agent-web", version="0.1.0")
    app.include_router(router)

    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app


app = create_app()

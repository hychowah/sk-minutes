from __future__ import annotations

from fastapi import FastAPI

from minutes import __version__
from minutes.api.routes_jobs import router as jobs_router
from minutes.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.settings = resolved_settings
    app.include_router(jobs_router)

    @app.get("/healthz", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {
            "status": "ok",
            "environment": resolved_settings.app_env,
            "version": __version__,
        }

    @app.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {
            "name": resolved_settings.app_name,
            "message": "Minutes foundation is up.",
            "state_root": str(resolved_settings.state_root),
        }

    return app
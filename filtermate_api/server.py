"""
FilterMate API — FastAPI application.

Provides the FastAPI app instance with:
- Lifespan management (startup / shutdown hooks)
- Health-check endpoint (GET /)
- CORS middleware
- Logging configuration

Endpoints for filtering, expressions, etc. will be added in T2-T6.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import APIConfig

logger = logging.getLogger("filtermate_api")


def _configure_logging(level: str) -> None:
    """Set up basic logging for the API process."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def _ensure_core_importable(project_root: Path) -> None:
    """Make sure ``core`` package is importable by adding the project root to sys.path."""
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: runs on startup and shutdown."""
    config: APIConfig = app.state.config

    _configure_logging(config.log_level)
    _ensure_core_importable(config.project_root)

    logger.info(
        "FilterMate API v%s starting on %s:%s (debug=%s)",
        __version__,
        config.host,
        config.port,
        config.debug,
    )

    # --- Startup complete ---
    yield

    # --- Shutdown ---
    logger.info("FilterMate API shutting down.")


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Factory that builds and returns a configured FastAPI application.

    Args:
        config: Optional APIConfig. If *None*, ``APIConfig.load()`` is used.

    Returns:
        A ready-to-serve FastAPI instance.
    """
    if config is None:
        config = APIConfig.load()

    app = FastAPI(
        title="FilterMate API",
        version=__version__,
        description="REST API for FilterMate core services.",
        lifespan=lifespan,
    )

    # Store config on app state so lifespan and routes can access it.
    app.state.config = config

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/", tags=["health"])
    async def health_check() -> dict:
        """Health-check / root endpoint."""
        return {
            "status": "ok",
            "service": "FilterMate API",
            "version": __version__,
        }

    return app


# Default app instance — used by ``uvicorn filtermate_api.server:app``
app = create_app()

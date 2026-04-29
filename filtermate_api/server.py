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

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from . import __version__
from .accessor import FilterMateAccessor, InMemoryAccessor
from .auth import APIKeyMiddleware
from .config import APIConfig
from .routers import favorites as favorites_router
from .routers import filters as filters_router
from .routers import layers as layers_router

logger = logging.getLogger("filtermate_api")

# P1-API-HARDEN (audit 2026-04-29): cap request body at 1 MiB so a
# malicious caller can't DoS the QGIS process by streaming gigabytes
# into ``POST /filters/apply`` (which accepts arbitrary expression
# strings). 1 MiB is two orders of magnitude above any legitimate
# filter expression — operators can override per-deployment via the
# ``FILTERMATE_API_MAX_BODY_BYTES`` env var.
_DEFAULT_MAX_BODY_BYTES = 1 * 1024 * 1024


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with ``Content-Length`` above the configured cap.

    Compares against the declared ``Content-Length`` header — a hostile
    caller can omit the header and stream chunked, but FastAPI's body
    parsing then enforces the same ceiling implicitly via Pydantic's
    ``max_length`` validators on the field shapes (``ApplyFilterRequest``
    has ``min_length=1`` but no ``max_length`` today; if that becomes a
    real attack surface we'll add it). Header-based rejection is the
    cheap first wall — it stops well-behaved clients from accidentally
    DoS-ing the QGIS process.
    """

    def __init__(self, app, max_body_bytes: int = _DEFAULT_MAX_BODY_BYTES) -> None:
        super().__init__(app)
        self._max_body_bytes = max_body_bytes

    # Newer Starlette renamed this constant to ``HTTP_413_CONTENT_TOO_LARGE``;
    # fall back to the legacy spelling so the middleware works against
    # both versions without emitting a DeprecationWarning.
    _STATUS_413 = getattr(
        status, "HTTP_413_CONTENT_TOO_LARGE", 413
    )

    async def dispatch(self, request: Request, call_next):
        content_length_raw = request.headers.get("content-length")
        if content_length_raw:
            try:
                content_length = int(content_length_raw)
            except ValueError:
                content_length = 0
            if content_length > self._max_body_bytes:
                return JSONResponse(
                    status_code=self._STATUS_413,
                    content={
                        "detail": "Request body too large",
                        "max_bytes": self._max_body_bytes,
                    },
                )
        return await call_next(request)


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


def create_app(
    config: APIConfig | None = None,
    accessor: FilterMateAccessor | None = None,
    *,
    allow_insecure: bool | None = None,
) -> FastAPI:
    """Factory that builds and returns a configured FastAPI application.

    Args:
        config: Optional APIConfig. If *None*, ``APIConfig.load()`` is used.
        accessor: Optional bridge to the running FilterMate plugin. If
            *None*, an empty :class:`InMemoryAccessor` is wired — fine for
            standalone smoke tests, useless for real filtering.
        allow_insecure: Forwarded to :meth:`APIConfig.validate`. ``None``
            (default) reads the ``FILTERMATE_API_ALLOW_INSECURE`` env var.
            Set ``True`` from tests/CI that legitimately need the relaxed
            defaults (e.g. ``api_key=None`` on loopback already passes).

    Returns:
        A ready-to-serve FastAPI instance.

    Raises:
        APIConfigError: when the resolved config is remotely exploitable
            (non-loopback + no auth, or non-loopback + wildcard CORS) and
            no override is requested.
    """
    if config is None:
        config = APIConfig.load()
    if accessor is None:
        accessor = InMemoryAccessor()

    config.validate(allow_insecure=allow_insecure)

    app = FastAPI(
        title="FilterMate API",
        version=__version__,
        description="REST API for FilterMate core services.",
        lifespan=lifespan,
    )

    # Store config + accessor on app state so lifespan and routes can access them.
    app.state.config = config
    app.state.accessor = accessor

    # --- CORS ---
    # Wildcard origin + credentials is forbidden by spec; browsers reject
    # it silently. Force-disable credentials when origin is "*" so the
    # middleware emits a coherent, browser-honoured policy instead of
    # one that silently degrades.
    cors_allow_credentials = not config.has_wildcard_cors
    if config.has_wildcard_cors:
        logger.warning(
            "CORS allow_origins=['*'] — disabling allow_credentials. "
            "Specify explicit origins to allow credentialed requests."
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- API key auth (#28) ---
    # Always installed; no-op when api_key is None/empty so dev mode is
    # still ergonomic. Putting it AFTER CORS means CORS pre-flight (OPTIONS)
    # responses don't carry an auth check — browsers refuse to attach the
    # X-API-Key on the pre-flight, so a 401 there would silently break clients.
    app.add_middleware(APIKeyMiddleware, api_key_hash=config.api_key_hash)

    # --- Body-size cap (P1-API-HARDEN) ---
    # Installed AFTER auth so unauthenticated callers are 401'd before
    # we even read the Content-Length — keeps the cheap first wall in
    # the right order. Override via FILTERMATE_API_MAX_BODY_BYTES.
    import os as _os
    try:
        _max_body = int(
            _os.environ.get("FILTERMATE_API_MAX_BODY_BYTES")
            or _DEFAULT_MAX_BODY_BYTES
        )
    except ValueError:
        _max_body = _DEFAULT_MAX_BODY_BYTES
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=_max_body)

    if not config.has_auth:
        logger.warning(
            "FilterMate API starting without api_key — auth disabled "
            "(allowed because host=%r is loopback-only).",
            config.host,
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

    # --- Domain routers ---
    app.include_router(layers_router.router)     # GET /layers                       — issue #30
    app.include_router(filters_router.router)    # /filters/apply, /status, /undo, /redo — #29 #31 #33
    app.include_router(favorites_router.router)  # GET /favorites, POST /favorites/{id}/apply — #32

    return app


# Default app instance — used by ``uvicorn filtermate_api.server:app``
app = create_app()

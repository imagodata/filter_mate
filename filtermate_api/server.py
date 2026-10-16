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
import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Iterable, Optional

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from . import __version__
from .accessor import FilterMateAccessor, InMemoryAccessor
from .auth import APIKeyMiddleware
from .config import _LOOPBACK_HOSTS, APIConfig
from .main_thread import QGISBusy
from .routers import export as export_router
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

# QGIS busy (main thread on a long task, FilterMate operation or filter task
# running): nothing was changed, the client retries after this many seconds.
_BUSY_RETRY_AFTER_SECONDS = 5


class BodySizeLimitMiddleware:
    """Reject request bodies over the configured cap with HTTP 413.

    Pure ASGI: the declared ``Content-Length`` is checked first (cheap
    wall for well-behaved clients), then the body is read here while the
    bytes actually received are counted, so a chunked upload without
    ``Content-Length`` hits the same ceiling. The body read (at most the
    cap) is then replayed to the application.
    """

    # Newer Starlette renamed this constant to ``HTTP_413_CONTENT_TOO_LARGE``;
    # fall back to the legacy spelling so the middleware works against
    # both versions without emitting a DeprecationWarning.
    _STATUS_413 = getattr(
        status, "HTTP_413_CONTENT_TOO_LARGE", 413
    )

    def __init__(self, app: ASGIApp, max_body_bytes: int = _DEFAULT_MAX_BODY_BYTES) -> None:
        self.app = app
        self._max_body_bytes = max_body_bytes

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=self._STATUS_413,
            content={
                "detail": "Request body too large",
                "max_bytes": self._max_body_bytes,
            },
        )
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            declared = int(Headers(scope=scope).get("content-length") or 0)
        except ValueError:
            declared = 0  # not trusted: the bytes received are counted below
        if declared > self._max_body_bytes:
            await self._reject(scope, receive, send)
            return

        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                # Client gone before the end of the body: answer anyway, an
                # outer BaseHTTPMiddleware fails (500) when no response comes.
                response = JSONResponse(status_code=400, content={"detail": "Request body incomplete"})
                await response(scope, receive, send)
                return
            body = message.get("body", b"")
            size += len(body)
            if size > self._max_body_bytes:
                await self._reject(scope, receive, send)
                return
            chunks.append(body)
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay() -> dict:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()  # later calls wait for the disconnect, as usual

        await self.app(scope, replay, send)


_PORT = re.compile(r"[0-9]{1,5}")


def _host_name(value: str) -> str:
    """Host of a ``Host`` header without its port (``[::1]:8000`` -> ``::1``), "" when malformed.

    Only a numeric ``:port`` may follow the host: ``[::1]evil`` or
    ``127.0.0.1:abc`` name no loopback host.
    """
    value = (value or "").strip().lower()
    if value.startswith("["):
        end = value.find("]")
        if end <= 0:
            return ""
        host, rest = value[1:end], value[end + 1:]
    elif value.count(":") == 1:
        host, port = value.split(":", 1)
        rest = ":" + port
    else:
        return value  # no port, or a bare IPv6 address
    if rest and not (rest.startswith(":") and _PORT.fullmatch(rest[1:])):
        return ""
    return host


class LoopbackHostMiddleware:
    """Refuse requests whose ``Host`` header is not a loopback name.

    A loopback bind keeps other machines out, not web pages: through DNS
    rebinding a hostile page gets its own host name resolved to 127.0.0.1
    and talks to the API as a same-origin page, past CORS. Its requests
    still carry that host name, so only ``127.0.0.1``, ``localhost`` and
    ``::1`` (any port) are served. A request without ``Host`` (HTTP/1.0) is
    served: a browser always sends one.
    """

    def __init__(self, app: ASGIApp, allowed_hosts: Iterable[str] = _LOOPBACK_HOSTS) -> None:
        self.app = app
        self._allowed_hosts = frozenset(allowed_hosts)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        host = Headers(scope=scope).get("host") if scope["type"] == "http" else None
        if host is not None and _host_name(host) not in self._allowed_hosts:
            response = JSONResponse(status_code=400, content={"detail": "Invalid host header"})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _is_json(content_type: str) -> bool:
    media = content_type.split(";", 1)[0].strip().lower()
    return media == "application/json" or (media.startswith("application/") and media.endswith("+json"))


class CrossSiteWriteGuard:
    """Refuse changes asked by another web site (CSRF), and bodies that are not JSON.

    A browser sends a cross-site "simple" request — a form post, a no-cors
    fetch — with no pre-flight, so CORS never gets a say: on a loopback API
    without a key, any page the user visits could undo a filter or apply a
    favorite. Such a request carries the page's ``Origin`` (or at least
    ``Sec-Fetch-Site: cross-site``): a request that is not a read is refused
    (403) unless that origin is the API's own (its ``/docs`` page) or listed
    in ``cors_origins``. Non-browser clients send neither header. A body must
    be JSON (415): a form can only post urlencoded, multipart or plain text.
    """

    def __init__(self, app: ASGIApp, allowed_origins: Iterable[str] = ()) -> None:
        self.app = app
        self._allowed_origins = frozenset(allowed_origins)

    def _origin_allowed(self, origin: str, scope: Scope, headers: Headers) -> bool:
        if "*" in self._allowed_origins or origin in self._allowed_origins:
            return True
        own = f"{scope.get('scheme', 'http')}://{headers.get('host', '')}"
        return origin.lower() == own.lower()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in _SAFE_METHODS:
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        origin = headers.get("origin")
        if origin is not None:
            refused = not self._origin_allowed(origin, scope, headers)
        else:
            refused = headers.get("sec-fetch-site", "").lower() == "cross-site"
        if refused:
            response = JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                                    content={"detail": "Cross-site request refused (origin not in cors_origins)"})
            await response(scope, receive, send)
            return
        content_type = headers.get("content-type")
        try:
            has_body = int(headers.get("content-length") or 0) > 0
        except ValueError:
            has_body = True
        has_body = has_body or "chunked" in headers.get("transfer-encoding", "").lower()
        if (content_type is not None or has_body) and not _is_json(content_type or ""):
            response = JSONResponse(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                                    content={"detail": "Content-Type must be application/json"})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


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
    config: Optional[APIConfig] = None,
    accessor: Optional[FilterMateAccessor] = None,
    *,
    allow_insecure: Optional[bool] = None,
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

    # --- Middlewares ---
    # Starlette runs the LAST added middleware first: they are added from
    # the innermost to the outermost. Request path:
    #   loopback Host check -> CORS -> cross-site write guard -> API key
    #   -> body-size cap -> routes.

    # Body-size cap (P1-API-HARDEN), innermost: unauthenticated callers are
    # 401'd before their body is read. Override via
    # FILTERMATE_API_MAX_BODY_BYTES.
    import os as _os
    try:
        _max_body = int(
            _os.environ.get("FILTERMATE_API_MAX_BODY_BYTES")
            or _DEFAULT_MAX_BODY_BYTES
        )
    except ValueError:
        _max_body = _DEFAULT_MAX_BODY_BYTES
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=_max_body)

    # API key auth (#28). Always installed; no-op when api_key is None/empty
    # so dev mode is still ergonomic.
    app.add_middleware(APIKeyMiddleware, api_key_hash=config.api_key_hash)

    # CSRF: a page's form post or no-cors fetch reaches the routes with no
    # pre-flight (see CrossSiteWriteGuard), key or not.
    app.add_middleware(CrossSiteWriteGuard, allowed_origins=config.cors_origins)

    # CORS, outside auth: CORSMiddleware answers browser pre-flights
    # (OPTIONS) itself — browsers never attach X-API-Key to a pre-flight,
    # so a 401 there would break every client — and adds its headers to
    # the 401 responses so a browser client can read them. No origin is
    # allowed unless configured (``cors_origins``).
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

    # Loopback bind: refuse foreign Host headers (DNS rebinding), outermost.
    if config.is_loopback_only:
        app.add_middleware(LoopbackHostMiddleware)

    if not config.has_auth:
        logger.warning(
            "FilterMate API starting without api_key — auth disabled "
            "(allowed because host=%r is loopback-only).",
            config.host,
        )

    # --- Validation errors ---
    # FastAPI's default 422 echoes every rejected value back: a refused
    # NaN / Infinity cannot even be encoded (500), and a refused 500 kB
    # expression would come back whole. Keep where and why, not the value.
    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{key: error[key] for key in ("type", "loc", "msg") if key in error} for error in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})

    @app.exception_handler(QGISBusy)
    async def _qgis_busy(request: Request, exc: QGISBusy) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": f"QGIS is busy: {exc}"},
            headers={"Retry-After": str(_BUSY_RETRY_AFTER_SECONDS)},
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
    app.include_router(export_router.router)     # POST /export — FilterMate 5

    return app


def __getattr__(name: str):
    """``app``, built on first use — ``uvicorn filtermate_api.server:app``.

    Built at import, it validated the configuration there: an insecure
    config.json made ``create_app`` itself impossible to import.
    """
    if name == "app":
        globals()["app"] = create_app()
        return globals()["app"]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

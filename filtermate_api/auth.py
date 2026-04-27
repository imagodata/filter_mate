"""API key authentication — issue #28.

Single-tenant header-based auth: clients send ``X-API-Key: <key>`` on
every business request, the middleware compares constant-time against
``APIConfig.api_key`` and rejects mismatches with a 401.

Disabled by design when ``api_key`` is None/empty so local development
doesn't need to juggle keys. Health-check (``GET /``) and OpenAPI
schema endpoints stay open in both modes — liveness probes and
documentation tooling don't have a key to hand.
"""

from __future__ import annotations

import hmac
from typing import Iterable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

API_KEY_HEADER = "x-api-key"

# Routes that bypass auth even when an api_key is configured. Liveness
# probes / OpenAPI tooling can't hand a key on every probe.
_PUBLIC_PATHS: tuple[str, ...] = (
    "/",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests missing or carrying a wrong ``X-API-Key`` header.

    Constant-time comparison via :func:`hmac.compare_digest` so the
    middleware doesn't leak length / position information to a timing
    attack — overkill for a self-hosted plugin API, but free.
    """

    def __init__(
        self,
        app: ASGIApp,
        api_key: str | None,
        public_paths: Iterable[str] = _PUBLIC_PATHS,
    ) -> None:
        super().__init__(app)
        self._api_key = api_key
        self._public_paths = frozenset(public_paths)

    async def dispatch(self, request: Request, call_next):
        # Auth disabled — short-circuit.
        if not self._api_key:
            return await call_next(request)

        if request.url.path in self._public_paths:
            return await call_next(request)

        provided = request.headers.get(API_KEY_HEADER, "")
        if not provided or not hmac.compare_digest(provided, self._api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Invalid or missing API key",
                    "header": "X-API-Key",
                },
            )

        return await call_next(request)

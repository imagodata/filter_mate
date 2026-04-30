"""API key authentication — issue #28 + P1-S4 hash-at-rest.

Single-tenant header-based auth: clients send ``X-API-Key: <key>`` on
every business request. The middleware computes ``sha256`` of the
provided header and compares constant-time against
``APIConfig.api_key_hash`` (P1-S4 audit 2026-04-29). Comparing digests
means the plaintext never has to live in the middleware's memory beyond
the request that supplied it.

Disabled by design when ``api_key_hash`` is None/empty so local
development doesn't need to juggle keys. Health-check (``GET /``) and
OpenAPI schema endpoints stay open in both modes — liveness probes and
documentation tooling don't have a key to hand.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Iterable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

API_KEY_HEADER = "x-api-key"  # pragma: allowlist secret

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

    The middleware compares the sha256 digest of the provided header
    against the configured ``api_key_hash``, in constant time via
    :func:`hmac.compare_digest`. Comparing digests means the plaintext
    only lives in scope for one request and never needs to be retained
    between requests.
    """

    def __init__(
        self,
        app: ASGIApp,
        api_key_hash: str | None,
        public_paths: Iterable[str] = _PUBLIC_PATHS,
    ) -> None:
        super().__init__(app)
        # Normalise to lowercase hex so callers don't have to care about
        # casing when round-tripping through JSON / shells.
        self._api_key_hash = (api_key_hash or "").strip().lower() or None
        self._public_paths = frozenset(public_paths)

    async def dispatch(self, request: Request, call_next):
        # Auth disabled — short-circuit.
        if not self._api_key_hash:
            return await call_next(request)

        if request.url.path in self._public_paths:
            return await call_next(request)

        provided = request.headers.get(API_KEY_HEADER, "")
        if provided:
            provided_hash = hashlib.sha256(provided.encode("utf-8")).hexdigest()
        else:
            provided_hash = ""
        if not provided_hash or not hmac.compare_digest(
            provided_hash, self._api_key_hash
        ):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Invalid or missing API key",
                    "header": "X-API-Key",
                },
            )

        return await call_next(request)

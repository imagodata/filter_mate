"""P1-API-HARDEN (audit 2026-04-29) — 3 sub-findings.

1. **A4 at boundary** — ``FavoritesUnavailable`` from the accessor is
   translated to ``503 Service Unavailable`` + ``Retry-After`` so the
   client distinguishes "not ready yet" from "no favorites configured".
2. **Reflected input scrubbed** — 404 bodies on apply_filter and
   apply_favorite no longer echo user-supplied layer name / favorite id.
3. **Body-size cap** — ``BodySizeLimitMiddleware`` rejects
   ``Content-Length`` over the configured threshold (default 1 MiB)
   with HTTP 413 before the request body is parsed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from filtermate_api.accessor import (  # noqa: E402
    FavoritesUnavailable,
    InMemoryAccessor,
)
from filtermate_api.config import APIConfig  # noqa: E402
from filtermate_api.server import (  # noqa: E402
    BodySizeLimitMiddleware,
    create_app,
)


# ---------------------------------------------------------------------------
# 1. FavoritesUnavailable → 503 + Retry-After
# ---------------------------------------------------------------------------


class _UnavailableFavoritesAccessor(InMemoryAccessor):
    """Accessor variant whose favorites methods always raise unavailable."""

    def list_favorites(self):  # type: ignore[override]
        raise FavoritesUnavailable("plugin still booting")

    def apply_favorite(self, favorite_id):  # type: ignore[override]
        raise FavoritesUnavailable("plugin still booting")


class TestFavoritesUnavailableAt503:
    def _client(self) -> TestClient:
        return TestClient(
            create_app(
                config=APIConfig(host="127.0.0.1"),
                accessor=_UnavailableFavoritesAccessor(),
            )
        )

    def test_list_favorites_returns_503_with_retry_after(self):
        response = self._client().get("/favorites")
        assert response.status_code == 503
        # Retry-After must be present so the client can back off
        # programmatically rather than thrashing the API.
        assert "retry-after" in {k.lower() for k in response.headers}
        retry = int(response.headers.get("retry-after"))
        assert retry > 0
        # Body is a static "not ready" — does NOT echo any internal
        # state ("plugin still booting") that the accessor mentioned.
        body = response.json()
        assert body["detail"] == "Favorites store not ready"

    def test_apply_favorite_returns_503_with_retry_after(self):
        response = self._client().post("/favorites/any-id/apply")
        assert response.status_code == 503
        assert "retry-after" in {k.lower() for k in response.headers}


# ---------------------------------------------------------------------------
# 2. Reflected user input scrubbed from 404 bodies
# ---------------------------------------------------------------------------


class TestErrorBodiesNoLongerReflectInput:
    """Belt-and-braces tests for the reflected-input scrub."""

    def _client(self) -> TestClient:
        return TestClient(
            create_app(
                config=APIConfig(host="127.0.0.1"),
                accessor=InMemoryAccessor(),
            )
        )

    @pytest.mark.parametrize(
        "evil_layer_name",
        [
            "<script>alert(1)</script>",
            "../../../etc/passwd",
            "x" * 200,
            "layer\r\nInjected: header",
        ],
    )
    def test_unknown_layer_404_does_not_echo_user_input(self, evil_layer_name):
        response = self._client().post(
            "/filters/apply",
            json={"layer_name": evil_layer_name, "expression": "1=1"},
        )
        assert response.status_code == 404
        # Static message — the user-supplied (potentially hostile)
        # name MUST NOT appear in the response body.
        assert response.json()["detail"] == "Layer not found"
        body_text = response.text
        assert evil_layer_name not in body_text, (
            f"Reflected input regression: {evil_layer_name!r} appears "
            "in the 404 body"
        )

    @pytest.mark.parametrize(
        "evil_id",
        [
            "no-such-id",
            "<svg-onload-alert>",
            "x" * 200,
            "id-with-fake-path-traversal",
        ],
    )
    def test_unknown_favorite_404_does_not_echo_id(self, evil_id):
        response = self._client().post(f"/favorites/{evil_id}/apply")
        assert response.status_code == 404
        body_text = response.text
        # The user-supplied id MUST NOT appear in the response detail.
        assert evil_id not in body_text, (
            f"Reflected input regression: {evil_id!r} appears in 404 body"
        )
        # Static message survives.
        assert response.json()["detail"] == (
            "Favorite not found or has no target layer"
        )


# ---------------------------------------------------------------------------
# 3. Body-size cap → 413 before body is parsed
# ---------------------------------------------------------------------------


class TestBodySizeCap:
    def _client(self, max_body: int = 1024) -> TestClient:
        # Tiny cap (1 KiB) so the test payload doesn't have to be huge.
        from fastapi import FastAPI

        app = FastAPI()
        app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=max_body)

        @app.post("/echo")
        async def _echo(payload: dict) -> dict:  # noqa: ANN401 - test-only
            return payload

        return TestClient(app)

    def test_oversized_body_returns_413(self):
        client = self._client(max_body=1024)
        oversized = "x" * 2048  # 2 KiB > 1 KiB cap
        response = client.post(
            "/echo",
            content=f'{{"data": "{oversized}"}}',
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(oversized) + 11),
            },
        )
        assert response.status_code == 413
        body = response.json()
        assert body["detail"] == "Request body too large"
        assert body["max_bytes"] == 1024

    def test_normal_body_passes(self):
        client = self._client(max_body=1024)
        response = client.post("/echo", json={"hello": "world"})
        assert response.status_code == 200
        assert response.json() == {"hello": "world"}

    def test_missing_content_length_falls_through(self):
        # When Content-Length is absent the middleware doesn't reject
        # — Starlette / chunked clients behave that way and the
        # downstream parser will catch oversized chunked streams.
        client = self._client(max_body=1024)
        response = client.post("/echo", json={"k": "v"})
        assert response.status_code == 200

    def test_bad_content_length_treated_as_zero(self):
        # Garbage Content-Length must NOT raise the middleware itself —
        # we just don't trust it for the cap check.
        client = self._client(max_body=1024)
        response = client.post(
            "/echo",
            content='{"k": "v"}',
            headers={
                "Content-Type": "application/json",
                "Content-Length": "not-a-number",
            },
        )
        # FastAPI may complain about the bad header but the middleware
        # itself shouldn't 413.
        assert response.status_code != 413

    def test_create_app_installs_body_size_middleware(self):
        # End-to-end: the app factory wires the middleware so a real
        # 2 MiB POST gets 413'd before the route runs.
        client = TestClient(
            create_app(config=APIConfig(host="127.0.0.1"), accessor=InMemoryAccessor())
        )
        oversized = "x" * (2 * 1024 * 1024)  # 2 MiB > 1 MiB default cap
        response = client.post(
            "/filters/apply",
            content=f'{{"layer_name":"L","expression":"{oversized}"}}',
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(oversized) + 40),
            },
        )
        assert response.status_code == 413

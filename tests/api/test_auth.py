# -*- coding: utf-8 -*-
"""Issue #28 — API key middleware contract tests."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from filtermate_api.accessor import InMemoryAccessor, LayerSummary  # noqa: E402
from filtermate_api.config import APIConfig  # noqa: E402
from filtermate_api.server import create_app  # noqa: E402


_SAMPLE_LAYERS = [
    LayerSummary(
        layer_id="L1", name="communes", provider_type="ogr",
        feature_count=10, geometry_type="Polygon", crs_authid="EPSG:4326",
    ),
]


def _client(api_key: str | None) -> TestClient:
    return TestClient(
        create_app(
            config=APIConfig(api_key=api_key),
            accessor=InMemoryAccessor(layers=list(_SAMPLE_LAYERS)),
        )
    )


class TestAuthDisabled:
    """When api_key is None/empty, requests pass through without a header."""

    def test_none_key_allows_unauthenticated_access(self):
        client = _client(api_key=None)
        assert client.get("/layers").status_code == 200

    def test_empty_string_key_allows_unauthenticated_access(self):
        # Empty string == "auth disabled" — same as None. Lets operators
        # toggle auth via env var without restructuring config.
        client = _client(api_key="")
        assert client.get("/layers").status_code == 200


class TestAuthEnabled:
    def setup_method(self):
        self.key = "secret-key-123"
        self.client = _client(api_key=self.key)

    def test_request_without_header_returns_401(self):
        response = self.client.get("/layers")
        assert response.status_code == 401
        body = response.json()
        # Detail spells the header name so clients can self-correct.
        assert body["header"] == "X-API-Key"

    def test_request_with_wrong_key_returns_401(self):
        response = self.client.get("/layers", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

    def test_request_with_correct_key_returns_200(self):
        response = self.client.get("/layers", headers={"X-API-Key": self.key})
        assert response.status_code == 200

    def test_header_match_is_case_insensitive_for_header_name(self):
        # HTTP headers are case-insensitive — both forms must work.
        for header_name in ("X-API-Key", "x-api-key", "X-Api-Key"):
            response = self.client.get("/layers", headers={header_name: self.key})
            assert response.status_code == 200, f"failed for {header_name}"

    def test_post_endpoints_also_require_key(self):
        response = self.client.post(
            "/filters/apply",
            json={"layer_name": "communes", "expression": '"x" = 1'},
        )
        assert response.status_code == 401

        response = self.client.post(
            "/filters/apply",
            headers={"X-API-Key": self.key},
            json={"layer_name": "communes", "expression": '"x" = 1'},
        )
        assert response.status_code == 200

    def test_health_check_stays_open_without_key(self):
        # Liveness probes / load-balancer health-checks don't have a key
        # to attach. Keeping `/` open is the standard expectation.
        response = self.client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_openapi_schema_stays_open_without_key(self):
        # OpenAPI consumers (Swagger UI, codegen) need the schema before
        # they know about auth — keep it bypass-listed.
        assert self.client.get("/openapi.json").status_code == 200

    def test_value_difference_in_key_treated_as_unauth(self):
        # Sanity: a partial match is still a 401 (no truncation/prefix accept).
        response = self.client.get(
            "/layers", headers={"X-API-Key": self.key[:-1]}
        )
        assert response.status_code == 401

# -*- coding: utf-8 -*-
"""Issue #29 — POST /filters/apply contract tests."""
from __future__ import annotations


class TestApplyFilter:
    def test_happy_path_applies_and_echoes_active_filters(self, client):
        response = client.post(
            "/filters/apply",
            json={
                "layer_name": "communes",
                "expression": '"population" > 10000',
                "source": "narractive",
            },
        )
        assert response.status_code == 200

        body = response.json()
        assert body["success"] is True
        assert body["layer_name"] == "communes"
        assert body["expression"] == '"population" > 10000'
        assert body["source"] == "narractive"
        assert body["active_filters"] == {"communes": '"population" > 10000'}

    def test_default_source_when_omitted(self, client):
        response = client.post(
            "/filters/apply",
            json={"layer_name": "communes", "expression": '"id" = 1'},
        )
        assert response.status_code == 200
        # Default source preserves attribution: filters applied via the
        # REST API should be distinguishable from in-plugin actions.
        assert response.json()["source"] == "rest_api"

    def test_unknown_layer_returns_404(self, client):
        response = client.post(
            "/filters/apply",
            json={"layer_name": "ghost_layer", "expression": "1=1"},
        )
        assert response.status_code == 404
        # P1-API-HARDEN (audit 2026-04-29): the detail message no longer
        # echoes the user-supplied layer name back to remove the
        # reflected-input surface. The status code conveys "not found"
        # and the caller already has the name from the request payload.
        assert response.json()["detail"] == "Layer not found"

    def test_missing_layer_name_is_422(self, client):
        # Pydantic validation kicks in before the route body runs.
        response = client.post(
            "/filters/apply",
            json={"expression": '"id" = 1'},
        )
        assert response.status_code == 422

    def test_empty_expression_is_422(self, client):
        response = client.post(
            "/filters/apply",
            json={"layer_name": "communes", "expression": ""},
        )
        assert response.status_code == 422

    def test_apply_then_apply_overwrites_active_filter(self, client):
        client.post(
            "/filters/apply",
            json={"layer_name": "communes", "expression": '"x" = 1'},
        )
        response = client.post(
            "/filters/apply",
            json={"layer_name": "communes", "expression": '"x" = 2'},
        )
        body = response.json()
        # Last write wins — matches FilterMatePublicAPI semantics.
        assert body["active_filters"] == {"communes": '"x" = 2'}

    def test_two_distinct_layers_keep_independent_filters(self, client):
        client.post(
            "/filters/apply",
            json={"layer_name": "communes", "expression": '"a" = 1'},
        )
        response = client.post(
            "/filters/apply",
            json={"layer_name": "roads", "expression": '"b" = 2'},
        )
        assert response.json()["active_filters"] == {
            "communes": '"a" = 1',
            "roads": '"b" = 2',
        }

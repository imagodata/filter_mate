# -*- coding: utf-8 -*-
"""Issue #31 — GET /filters/status contract tests."""
from __future__ import annotations


class TestFilterStatus:
    def test_idle_when_no_filters_applied(self, client):
        response = client.get("/filters/status")
        assert response.status_code == 200

        body = response.json()
        assert body["status"] == "idle"
        assert body["active_filters"] == {}
        assert body["active_filters_count"] == 0
        assert body["last_applied_at"] is None
        assert body["last_applied_layer"] is None
        assert body["last_applied_source"] is None
        assert body["last_error"] is None

    def test_completed_after_apply_carries_metadata(self, client):
        client.post(
            "/filters/apply",
            json={
                "layer_name": "communes",
                "expression": '"x" = 1',
                "source": "narractive",
            },
        )
        body = client.get("/filters/status").json()

        assert body["status"] == "completed"
        assert body["active_filters_count"] == 1
        assert body["active_filters"] == {"communes": '"x" = 1'}
        assert body["last_applied_layer"] == "communes"
        assert body["last_applied_source"] == "narractive"
        # ISO-8601 with timezone — clients can parse without an extra hint.
        assert body["last_applied_at"] is not None
        assert "T" in body["last_applied_at"]

    def test_status_aggregates_multiple_layers(self, client):
        client.post(
            "/filters/apply",
            json={"layer_name": "communes", "expression": '"a" = 1'},
        )
        client.post(
            "/filters/apply",
            json={"layer_name": "roads", "expression": '"b" = 2'},
        )
        body = client.get("/filters/status").json()

        assert body["active_filters_count"] == 2
        assert body["active_filters"] == {
            "communes": '"a" = 1',
            "roads": '"b" = 2',
        }
        # Last applied wins for the *_last_*_ fields — matches plugin behaviour.
        assert body["last_applied_layer"] == "roads"

    def test_last_applied_timestamp_advances_with_each_apply(self, client):
        client.post(
            "/filters/apply",
            json={"layer_name": "communes", "expression": '"x" = 1'},
        )
        first_ts = client.get("/filters/status").json()["last_applied_at"]

        client.post(
            "/filters/apply",
            json={"layer_name": "roads", "expression": '"y" = 1'},
        )
        second_ts = client.get("/filters/status").json()["last_applied_at"]

        assert first_ts is not None
        assert second_ts is not None
        # Strictly later — string comparison works for ISO-8601 with TZ.
        assert second_ts >= first_ts

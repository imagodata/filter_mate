# -*- coding: utf-8 -*-
"""Issue #32 — GET /favorites and POST /favorites/{id}/apply contract tests."""
from __future__ import annotations


class TestListFavorites:
    def test_returns_all_favorites_from_accessor(self, client, sample_favorites):
        response = client.get("/favorites")
        assert response.status_code == 200

        body = response.json()
        ids = {item["favorite_id"] for item in body}
        assert ids == {fav.favorite_id for fav in sample_favorites}

    def test_payload_carries_metadata(self, client):
        body = client.get("/favorites").json()
        large = next(item for item in body if item["favorite_id"] == "fav-communes-large")
        assert large == {
            "favorite_id": "fav-communes-large",
            "name": "Large communes",
            "description": "Communes >10k pop",
            "layer_name": "communes",
            "expression": '"population" > 10000',
        }

    def test_empty_accessor_returns_empty_list(self, client_factory):
        client = client_factory(layers=[])
        body = client.get("/favorites").json()
        assert body == []


class TestApplyFavorite:
    def test_apply_known_favorite_updates_active_filters(self, client):
        response = client.post("/favorites/fav-communes-large/apply")
        assert response.status_code == 200

        body = response.json()
        assert body["step"]["layer_name"] == "communes"
        assert body["step"]["expression"] == '"population" > 10000'
        assert body["active_filters"] == {
            "communes": '"population" > 10000',
        }

    def test_apply_unknown_favorite_returns_404(self, client):
        response = client.post("/favorites/no-such-id/apply")
        assert response.status_code == 404
        # P1-API-HARDEN (audit 2026-04-29): static message — no echo of
        # the user-supplied id into the body.
        assert response.json()["detail"] == "Favorite not found or has no target layer"

    def test_apply_orphan_favorite_returns_404(self, client):
        # The orphan favorite has no layer_name — can't be applied.
        response = client.post("/favorites/fav-orphan/apply")
        assert response.status_code == 404

    def test_apply_then_undo_clears_the_favorite(self, client):
        client.post("/favorites/fav-communes-large/apply")
        body = client.post("/filters/undo").json()
        assert body["active_filters"] == {}

    def test_apply_favorite_records_source_tag(self, client):
        # The accessor stamps the apply with `favorite:<id>` so plugin logs
        # show the call came via a favorite (not a raw apply).
        client.post("/favorites/fav-roads-major/apply")
        status = client.get("/filters/status").json()
        assert status["last_applied_source"] == "favorite:fav-roads-major"

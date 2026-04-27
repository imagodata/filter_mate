# -*- coding: utf-8 -*-
"""Issue #30 — GET /layers contract tests.

Pin the response shape (so client codegen stays stable) and the basic
contract: returns whatever the accessor exposes, reflects active filters
applied via the filters router, no auth shortcut leaks through.
"""
from __future__ import annotations


class TestListLayers:
    def test_returns_all_layers_from_accessor(self, client, sample_layers):
        response = client.get("/layers")
        assert response.status_code == 200

        body = response.json()
        assert isinstance(body, list)
        assert len(body) == len(sample_layers)

        names = {item["name"] for item in body}
        assert names == {"communes", "roads"}

    def test_payload_carries_metadata_for_each_layer(self, client):
        response = client.get("/layers")
        body = response.json()

        communes = next(item for item in body if item["name"] == "communes")
        assert communes == {
            "layer_id": "L1",
            "name": "communes",
            "provider_type": "postgresql",
            "feature_count": 35000,
            "geometry_type": "MultiPolygon",
            "crs_authid": "EPSG:2154",
            "has_active_filter": False,
            "active_filter_expression": "",
        }

    def test_empty_accessor_returns_empty_list(self, client_factory):
        client = client_factory(layers=[])
        response = client.get("/layers")
        assert response.status_code == 200
        assert response.json() == []

    def test_active_filter_surfaces_after_apply(self, client):
        # Apply a filter then re-fetch the layers — the toggled flag should
        # propagate so a single GET is sufficient to refresh client state.
        client.post(
            "/filters/apply",
            json={"layer_name": "roads", "expression": '"length" > 100'},
        )
        body = client.get("/layers").json()
        roads = next(item for item in body if item["name"] == "roads")
        assert roads["has_active_filter"] is True
        assert roads["active_filter_expression"] == '"length" > 100'

        # Untouched layer stays clean.
        communes = next(item for item in body if item["name"] == "communes")
        assert communes["has_active_filter"] is False

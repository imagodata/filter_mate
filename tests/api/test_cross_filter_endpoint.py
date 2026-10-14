# -*- coding: utf-8 -*-
"""FilterMate 5 — POST /filters/cross and layer kinds in GET /layers."""
from __future__ import annotations

import pytest

from filtermate_api.accessor import LayerSummary


@pytest.fixture
def mixed_layers() -> list[LayerSummary]:
    return [
        LayerSummary(layer_id="V1", name="batiment", provider_type="ogr", feature_count=134,
                     geometry_type="MultiPolygon", crs_authid="EPSG:2154"),
        LayerSummary(layer_id="R1", name="mnt", provider_type="gdal", geometry_type="Raster",
                     crs_authid="EPSG:2154", layer_kind="raster"),
        LayerSummary(layer_id="P1", name="lhd", provider_type="copc", feature_count=25111931,
                     geometry_type="PointCloud", crs_authid="EPSG:2154", layer_kind="point_cloud"),
    ]


class TestLayerKinds:
    def test_layers_carry_their_kind(self, client_factory, mixed_layers):
        body = client_factory(layers=mixed_layers).get("/layers").json()
        assert {item["name"]: item["layer_kind"] for item in body} == {
            "batiment": "vector", "mnt": "raster", "lhd": "point_cloud"}

    def test_kind_defaults_to_vector(self):
        assert LayerSummary(layer_id="x", name="x", provider_type="ogr").layer_kind == "vector"


class TestCrossFilter:
    def test_filters_raster_and_point_cloud_targets(self, client_factory, mixed_layers):
        client = client_factory(layers=mixed_layers)
        response = client.post("/filters/cross", json={
            "source_layer": "batiment", "target_layers": ["mnt", "lhd"],
            "predicates": ["Intersect"], "buffer": 2.0})
        assert response.status_code == 200
        body = response.json()
        assert body["filtered"] == ["mnt", "lhd"]
        assert body["failed"] == {}
        layers = {item["name"]: item for item in client.get("/layers").json()}
        assert layers["mnt"]["has_active_filter"] is True

    def test_unknown_targets_are_reported(self, client_factory, mixed_layers):
        response = client_factory(layers=mixed_layers).post("/filters/cross", json={
            "source_layer": "batiment", "target_layers": ["mnt", "ghost"]})
        assert response.status_code == 200
        assert response.json()["failed"] == {"ghost": "layer not found"}

    def test_unknown_or_non_vector_source_is_404(self, client_factory, mixed_layers):
        client = client_factory(layers=mixed_layers)
        for source in ("ghost", "mnt"):
            response = client.post("/filters/cross", json={"source_layer": source, "target_layers": ["lhd"]})
            assert response.status_code == 404
            assert response.json()["detail"] == "Source layer not found"

    @pytest.mark.parametrize("payload", [
        {"source_layer": "batiment", "target_layers": []},
        {"source_layer": "batiment", "target_layers": ["mnt"], "predicates": ["Nearby"]},
        {"source_layer": "batiment", "target_layers": ["mnt"], "operator": "XOR"},
        {"source_layer": "batiment", "target_layers": ["mnt"], "coverage_min": 150},
    ])
    def test_invalid_payloads_are_422(self, client_factory, mixed_layers, payload):
        assert client_factory(layers=mixed_layers).post("/filters/cross", json=payload).status_code == 422

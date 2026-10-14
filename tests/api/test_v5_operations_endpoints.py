# -*- coding: utf-8 -*-
"""FilterMate 5 — /filters/geometry, /filters/point-cloud, /filters/clear, /filters/state, /export."""
from __future__ import annotations

from pathlib import Path

import pytest

from filtermate_api.accessor import InMemoryAccessor, LayerSummary
from filtermate_api.config import APIConfig
from filtermate_api.routers.export import resolve_export_folder
from filtermate_api.server import create_app

from fastapi.testclient import TestClient

SQUARE = "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))"


@pytest.fixture
def layers() -> list[LayerSummary]:
    return [
        LayerSummary(layer_id="V1", name="batiment", provider_type="ogr"),
        LayerSummary(layer_id="R1", name="mnt", provider_type="gdal", layer_kind="raster"),
        LayerSummary(layer_id="P1", name="lhd", provider_type="copc", layer_kind="point_cloud"),
        LayerSummary(layer_id="P2", name="lhd_b", provider_type="copc", layer_kind="point_cloud"),
    ]


@pytest.fixture
def client(layers, tmp_path) -> TestClient:
    config = APIConfig(export_root=tmp_path / "exports")
    return TestClient(create_app(config=config, accessor=InMemoryAccessor(layers=layers), allow_insecure=True))


class TestGeometryFilter:
    def test_filters_targets(self, client):
        response = client.post("/filters/geometry", json={
            "wkt": SQUARE, "crs": "EPSG:2154", "target_layers": ["mnt", "batiment"], "buffer": 5})
        assert response.status_code == 200
        assert response.json()["filtered"] == ["mnt", "batiment"]

    def test_no_target_resolves_is_400(self, client):
        response = client.post("/filters/geometry", json={"wkt": SQUARE, "crs": "EPSG:2154", "target_layers": ["x"]})
        assert response.status_code == 400

    @pytest.mark.parametrize("payload", [
        {"crs": "EPSG:2154", "target_layers": ["mnt"]},
        {"wkt": SQUARE, "target_layers": ["mnt"]},
        {"wkt": SQUARE, "crs": "EPSG:2154", "target_layers": []},
        {"wkt": SQUARE, "crs": "EPSG:2154", "target_layers": ["mnt"], "predicates": ["Near"]},
    ])
    def test_invalid_payloads_are_422(self, client, payload):
        assert client.post("/filters/geometry", json=payload).status_code == 422


class TestPointCloudFilter:
    def test_filters_point_clouds_only(self, client):
        response = client.post("/filters/point-cloud", json={
            "layers": ["lhd", "lhd_b", "mnt"], "criteria": {"classes": [3, 4, 5], "z_min": 1200}})
        assert response.status_code == 200
        body = response.json()
        assert body["done"] == ["lhd", "lhd_b"]
        assert body["skipped"] == {"mnt": "not a point cloud layer"}

    def test_empty_criteria_is_422(self, client):
        assert client.post("/filters/point-cloud", json={"layers": ["lhd"], "criteria": {}}).status_code == 422

    def test_unknown_operator_is_422(self, client):
        response = client.post("/filters/point-cloud", json={
            "layers": ["lhd"], "criteria": {"classes": [6]}, "operator": "XOR"})
        assert response.status_code == 422

    def test_no_point_cloud_is_400(self, client):
        response = client.post("/filters/point-cloud", json={"layers": ["mnt"], "criteria": {"classes": [6]}})
        assert response.status_code == 400


class TestClearAndState:
    def test_state_lists_filtered_layers_then_clear_empties_it(self, client):
        client.post("/filters/point-cloud", json={"layers": ["lhd"], "criteria": {"classes": [6]}})
        state = client.get("/filters/state").json()
        assert [(row["name"], row["layer_kind"]) for row in state] == [("lhd", "point_cloud")]
        response = client.post("/filters/clear", json={"layers": ["lhd", "mnt"]})
        assert response.status_code == 200
        assert response.json()["done"] == ["lhd"]
        assert response.json()["skipped"] == {"mnt": "not filtered"}
        assert client.get("/filters/state").json() == []

    def test_clear_needs_layers(self, client):
        assert client.post("/filters/clear", json={"layers": []}).status_code == 422


class TestExport:
    def test_writes_below_the_export_root(self, client, tmp_path):
        response = client.post("/export", json={"layers": ["batiment", "mnt", "lhd"], "subfolder": "commune/31555"})
        assert response.status_code == 200
        outputs = response.json()["outputs"]
        root = (tmp_path / "exports" / "commune" / "31555").resolve()
        assert outputs == {"batiment": f"{root}/batiment.gpkg", "mnt": f"{root}/mnt.tif", "lhd": f"{root}/lhd.laz"}

    @pytest.mark.parametrize("subfolder", ["../etc", "/abs", "a/../../b", "", ".hidden", "a\\b", "a b"])
    def test_rejects_escaping_subfolders(self, client, subfolder):
        assert client.post("/export", json={"layers": ["mnt"], "subfolder": subfolder}).status_code == 422

    def test_rejects_unknown_formats(self, client):
        assert client.post("/export", json={"layers": ["mnt"], "raster_format": "PNG"}).status_code == 422

    def test_resolve_export_folder(self, tmp_path):
        assert resolve_export_folder(tmp_path, "a/b") == (tmp_path / "a" / "b").resolve()
        with pytest.raises(ValueError):
            resolve_export_folder(tmp_path, "a/..")


class TestExportRootConfig:
    def test_env_overrides_export_root(self, monkeypatch, tmp_path):
        monkeypatch.setenv("FILTERMATE_API_EXPORT_ROOT", str(tmp_path / "x"))
        assert APIConfig.load().export_root == Path(tmp_path / "x")

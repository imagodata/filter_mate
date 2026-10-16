# -*- coding: utf-8 -*-
"""Audit 2026-10 (FilterMate 5) — busy QGIS, undo after an operation, failure reasons.

* A busy QGIS (main thread on a long task, FilterMate operation running) is a
  503 with Retry-After: nothing was changed, the client retries.
* A change that is done is not turned into an error because the snapshot
  sent with it could not be read.
* Undo / redo right after a FilterMate 5 operation: 409 naming the way out.
* 400s say what stopped the operation.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from filtermate_api.accessor import InMemoryAccessor, LayerSummary, OperationResult, UndoUnavailable  # noqa: E402
from filtermate_api.config import APIConfig  # noqa: E402
from filtermate_api.main_thread import QGISBusy  # noqa: E402
from filtermate_api.server import create_app  # noqa: E402

_LAYERS = [LayerSummary(layer_id="L1", name="communes", provider_type="ogr", geometry_type="Polygon"),
           LayerSummary(layer_id="L2", name="lhd", provider_type="pdal", layer_kind="point_cloud")]


def _client(accessor, export_root=None) -> TestClient:
    config = APIConfig(export_root=export_root) if export_root else APIConfig()
    return TestClient(create_app(config=config, accessor=accessor), base_url="http://127.0.0.1:8000")


class _BusyAccessor(InMemoryAccessor):
    def cross_filter(self, *args, **kwargs):  # type: ignore[override]
        raise QGISBusy("a FilterMate filter is still running in the background")

    def get_filter_state(self):  # type: ignore[override]
        raise QGISBusy("the QGIS main thread did not take the call within 30s")


class _SnapshotBusyAccessor(InMemoryAccessor):
    def get_active_filters(self):  # type: ignore[override]
        raise QGISBusy("main thread busy")


class _AfterOperationAccessor(InMemoryAccessor):
    def undo_filter(self):  # type: ignore[override]
        raise UndoUnavailable("cross filter")

    def redo_filter(self):  # type: ignore[override]
        raise UndoUnavailable("cross filter")


class _FailingAccessor(InMemoryAccessor):
    def export_layers(self, *args, **kwargs):  # type: ignore[override]
        return OperationResult(error="no output folder")


class TestBusyIs503:
    def test_busy_operation_is_503_with_retry_after(self):
        response = _client(_BusyAccessor(layers=list(_LAYERS))).post(
            "/filters/cross", json={"source_layer": "communes", "target_layers": ["lhd"]})
        assert response.status_code == 503
        assert int(response.headers["retry-after"]) > 0
        assert "still running" in response.json()["detail"]

    def test_busy_read_is_503_never_an_empty_state(self):
        response = _client(_BusyAccessor(layers=list(_LAYERS))).get("/filters/state")
        assert response.status_code == 503


class TestDoneChangeIsNotAnError:
    def test_apply_done_but_snapshot_busy_is_200(self):
        response = _client(_SnapshotBusyAccessor(layers=list(_LAYERS))).post(
            "/filters/apply", json={"layer_name": "communes", "expression": "x = 1"})
        assert response.status_code == 200
        assert response.json()["active_filters"] == {}

    def test_undo_done_but_snapshot_busy_is_200(self):
        accessor = _SnapshotBusyAccessor(layers=list(_LAYERS))
        accessor.apply_filter("communes", "x = 1", "test")
        response = _client(accessor).post("/filters/undo")
        assert response.status_code == 200  # a retried undo would undo twice


class TestUndoAfterOperation:
    @pytest.mark.parametrize("route", ["/filters/undo", "/filters/redo"])
    def test_409_points_to_clear(self, route):
        response = _client(_AfterOperationAccessor(layers=list(_LAYERS))).post(route)
        assert response.status_code == 409
        assert "cross filter" in response.json()["detail"]
        assert "POST /filters/clear" in response.json()["detail"]


class TestFailureReasons:
    def test_export_failure_says_why(self, tmp_path):
        response = _client(_FailingAccessor(layers=list(_LAYERS)), export_root=tmp_path / "exports").post(
            "/export", json={"layers": ["communes"]})
        assert response.status_code == 400
        assert response.json()["detail"] == "Export failed: no output folder"

    def test_point_cloud_failure_says_why(self):
        response = _client(InMemoryAccessor(layers=list(_LAYERS))).post(
            "/filters/point-cloud", json={"layers": ["communes"], "criteria": {"classes": [2]}})
        assert response.status_code == 400
        assert response.json()["detail"] == "Point cloud filter failed: no point cloud layer to filter"

# -*- coding: utf-8 -*-
"""Objects on a raster for the agent (2026-11-10): those drawn in the dock, read; SAM run on guide features.

The QGIS side (``adapters/public_api/drawn_objects.py``) is checked in a real QGIS by
``tests/qgis_headless/check_segmentation.py``; here the accessor, the chat tool and the REST route.
"""
from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from core.agent.messages import ToolCallPart  # noqa: E402
from core.agent.tool_catalog import chat_tools  # noqa: E402
from core.agent.tool_executor import ToolExecutor  # noqa: E402
from filtermate_api.accessor import (  # noqa: E402
    FilterRejected, InMemoryAccessor, LayerSummary, SegmentResult, SimilarResult,
)
from filtermate_api.agent_tools import build_handlers  # noqa: E402
from filtermate_api.main_thread import QGISBusy  # noqa: E402
from filtermate_api.qgis_accessor import QGISFilterMateAccessor  # noqa: E402
from filtermate_api.server import create_app  # noqa: E402

ROOF = "POLYGON((0 0,10 0,10 10,0 10,0 0))"
DRAWN_ROW = {"layer_id": "R1", "name": "ortho", "crs_authid": "EPSG:2154", "count": 2, "area_m2": 200.0,
             "extent_wkt": "POLYGON((0 0,20 0,20 20,0 20,0 0))"}


def _layers():
    return [LayerSummary("R1", "ortho", "gdal", layer_kind="raster", crs_authid="EPSG:2154"),
            LayerSummary("V1", "bati", "ogr", feature_count=12, geometry_type="MultiPolygon", crs_authid="EPSG:2154"),
            LayerSummary("V2", "parcelles", "ogr", feature_count=900, geometry_type="MultiPolygon")]


# --- the QGIS accessor --------------------------------------------------------------------------------------------

class _Layer:
    def __init__(self, layer_id, name):
        self._id, self._name = layer_id, name

    def id(self):
        return self._id

    def name(self):
        return self._name


def _plugin(objects):
    controller = types.SimpleNamespace(drawn_objects=lambda: objects)
    integration = types.SimpleNamespace(_point_cloud_ui_controller=controller)
    dock = types.SimpleNamespace(_controller_integration=integration)
    return types.SimpleNamespace(app=types.SimpleNamespace(dockwidget=dock))


@pytest.fixture
def qgis_core(monkeypatch):
    """``qgis.core.QgsProject`` for the main-thread bodies of the accessor; the global mocks come back after."""
    module = types.ModuleType("qgis.core")
    module.QgsProject = MagicMock()
    monkeypatch.setitem(sys.modules, "qgis", types.ModuleType("qgis"))
    monkeypatch.setitem(sys.modules, "qgis.core", module)
    return module


@pytest.fixture
def plugin_modules(monkeypatch):
    """The modules of the plugin the accessor imports, by name; a test fills them."""
    import filtermate_api.qgis_accessor as qgis_accessor
    operations = MagicMock()
    operations.busy_reason.return_value = ""
    operations.raster_selection_from_dict.side_effect = lambda value: value
    operations.point_cloud_criteria_from_dict.side_effect = lambda value: value
    operations.resolve_layer.return_value = _Layer("R1", "ortho")
    operations.cross_filter.return_value = types.SimpleNamespace(
        done={"V1": "bati"}, done_names=["bati"], failed={}, skipped={}, error="", outputs={}, details={})
    kinds = types.SimpleNamespace(layer_kind_by_class=lambda layer: types.SimpleNamespace(value="raster"))
    modules = {"adapters.public_api.operations": operations, "core.domain.api_requests": operations,
               "adapters.public_api.introspection": MagicMock(), "adapters.public_api.drawn_objects": MagicMock(),
               "adapters.qgis.point_cloud_capability": kinds}
    monkeypatch.setattr(qgis_accessor, "_plugin_module", lambda name: modules[name])
    return modules


def _accessor(objects):
    return QGISFilterMateAccessor(public_api=MagicMock(), plugin=_plugin(objects))


class TestTheObjectsOfTheDock:
    def test_dock_objects_become_the_segments_of_that_raster(self, qgis_core, plugin_modules):
        accessor = _accessor({"R1": [ROOF, ROOF.replace("10", "9")], "R2": ["POLYGON((5 5,6 5,6 6,5 5))"]})
        result = accessor.cross_filter("ortho", ["bati"], ["Intersect"], raster_selection={"dock_objects": True})
        assert result.filtered == ["bati"] and not result.error
        selection = plugin_modules["adapters.public_api.operations"].cross_filter.call_args.kwargs["raster_selection"]
        assert selection == {"segments": [ROOF, ROOF.replace("10", "9")]}

    def test_nothing_drawn_on_the_source_says_where_to_look(self, qgis_core, plugin_modules):
        accessor = _accessor({"R2": [ROOF]})
        result = accessor.cross_filter("ortho", ["bati"], ["Intersect"], raster_selection={"dock_objects": True})
        assert "no object is drawn on 'ortho'" in result.error and "drawn_objects" in result.error
        plugin_modules["adapters.public_api.operations"].cross_filter.assert_not_called()

    def test_no_dock_at_all_is_nothing_drawn(self, qgis_core, plugin_modules):
        accessor = QGISFilterMateAccessor(public_api=MagicMock(), plugin=types.SimpleNamespace(app=None))
        result = accessor.cross_filter("ortho", ["bati"], ["Intersect"], raster_selection={"dock_objects": True})
        assert "no object is drawn" in result.error

    def test_segments_and_dock_objects_together_are_refused(self, qgis_core, plugin_modules):
        accessor = _accessor({"R1": [ROOF]})
        result = accessor.cross_filter("ortho", ["bati"], ["Intersect"],
                                       raster_selection={"dock_objects": True, "segments": [ROOF]})
        assert "either segments or dock_objects" in result.error

    def test_dock_objects_false_is_dropped_before_the_core_reads_it(self, qgis_core, plugin_modules):
        accessor = _accessor({})
        accessor.cross_filter("mnt", ["bati"], ["Intersect"],
                              raster_selection={"mode": "range", "minimum": 1200, "dock_objects": False})
        selection = plugin_modules["adapters.public_api.operations"].cross_filter.call_args.kwargs["raster_selection"]
        assert selection == {"mode": "range", "minimum": 1200}

    def test_map_context_tells_the_rasters_with_objects(self, qgis_core, plugin_modules):
        plugin_modules["adapters.public_api.introspection"].map_context.return_value = {"available": True,
                                                                                         "selections": []}
        plugin_modules["adapters.public_api.drawn_objects"].summarize_drawn.side_effect = \
            lambda objects: [dict(DRAWN_ROW, count=len(objects["R1"]))]
        context = _accessor({"R1": [ROOF, ROOF]}).map_context()
        assert context.available and context.drawn_objects == [DRAWN_ROW]

    def test_map_context_without_the_objects_when_they_cannot_be_read(self, qgis_core, plugin_modules):
        plugin_modules["adapters.public_api.introspection"].map_context.return_value = {"available": True}
        plugin_modules["adapters.public_api.drawn_objects"].summarize_drawn.side_effect = RuntimeError("deleted")
        assert _accessor({"R1": [ROOF]}).map_context().drawn_objects == []


class TestSegmentObjectsThroughTheAccessor:
    def test_delegates_on_the_main_thread_and_types_the_answer(self, plugin_modules, monkeypatch):
        import filtermate_api.qgis_accessor as qgis_accessor
        dispatched = []
        monkeypatch.setattr(qgis_accessor, "run_on_main_thread", lambda fn, *a, **k: dispatched.append(fn) or fn(*a, **k))
        module = plugin_modules["adapters.public_api.drawn_objects"]
        module.segment_objects.return_value = {"layer": {"layer_id": "L9"}, "guide_features": 3, "drawn": 2,
                                               "without_object": 1, "stopped_early": False, "seconds": 3.1,
                                               "sam_score": {"median": 0.9, "minimum": 0.7}}
        result = _accessor({}).segment_objects("ortho", "bati", selected_only=False, limit=10, name="toits")
        assert isinstance(result, SegmentResult) and result.drawn == 2 and result.sam_iou is None
        module.segment_objects.assert_called_once_with("ortho", "bati", selected_only=False, limit=10, name="toits")
        assert len(dispatched) == 1  # the whole call goes to the main thread, the busy check included

    def test_add_layer_and_add_service_layer_take_a_name(self, plugin_modules):
        # Their name collided with the first parameter of _control: a TypeError in QGIS until 2026-11-10.
        control = MagicMock()
        control.add_layer.return_value = {"layer_id": "L7", "name": "communes", "provider_type": "ogr"}
        control.add_service_layer.return_value = {"layer_id": "L8", "name": "wfs", "provider_type": "WFS"}
        plugin_modules["adapters.public_api.project_control"] = control
        accessor = _accessor({})
        assert accessor.add_layer("/data/communes.gpkg", name="communes").name == "communes"
        control.add_layer.assert_called_once_with("/data/communes.gpkg", name="communes", kind="vector")
        accessor.add_service_layer("ign_wfs", "BDTOPO:batiment", name="wfs", extra_domains="")
        control.add_service_layer.assert_called_once_with("ign_wfs", "BDTOPO:batiment", name="wfs", extra_domains="")

    def test_a_refusal_is_a_filter_rejected(self, plugin_modules):
        plugin_modules["adapters.public_api.drawn_objects"].segment_objects.side_effect = ValueError("SAM is not installed")
        with pytest.raises(FilterRejected, match="SAM is not installed"):
            _accessor({}).segment_objects("ortho", "bati")

    def test_refused_while_filtermate_is_busy(self, plugin_modules):
        plugin_modules["adapters.public_api.operations"].busy_reason.return_value = "a filter is running"
        with pytest.raises(QGISBusy):
            _accessor({}).segment_objects("ortho", "bati")
        plugin_modules["adapters.public_api.drawn_objects"].segment_objects.assert_not_called()


# --- the chat tool ------------------------------------------------------------------------------------------------

def _run(accessor, tmp_path, name, **arguments):
    result = ToolExecutor(chat_tools(), build_handlers(accessor, tmp_path)).execute(ToolCallPart("c", name, arguments))
    return result.is_error, (result.content if result.is_error else json.loads(result.content))


class TestChatTools:
    def test_segment_objects_is_offered_and_not_read_only(self):
        tool = next(tool for tool in chat_tools() if tool.name == "segment_objects")
        assert not tool.read_only and not tool.requires_confirmation  # a layer added, undone with the turn

    def test_segment_objects_defaults_and_answer(self, tmp_path):
        failed, answer = _run(InMemoryAccessor(layers=_layers()), tmp_path, "segment_objects",
                              raster="ortho", guide_layer="bati")
        assert not failed
        assert answer["layer"]["name"] == "bati (SAM)" and answer["drawn"] == 12
        assert "sam_iou" not in answer  # None is left out, not sent as null

    def test_segment_objects_refusals_reach_the_model(self, tmp_path):
        failed, message = _run(InMemoryAccessor(layers=_layers()), tmp_path, "segment_objects",
                               raster="ortho", guide_layer="parcelles", limit=100)
        assert failed and "900 guide features" in message

    def test_the_limit_is_bounded_by_the_schema(self, tmp_path):
        failed, message = _run(InMemoryAccessor(layers=_layers()), tmp_path, "segment_objects",
                               raster="ortho", guide_layer="bati", limit=500)
        assert failed and "Invalid arguments" in message

    def test_map_context_lists_the_drawn_objects(self, tmp_path):
        accessor = InMemoryAccessor(layers=_layers(), drawn_objects=[DRAWN_ROW])
        assert _run(accessor, tmp_path, "map_context")[1]["drawn_objects"] == [DRAWN_ROW]

    def test_cross_filter_with_dock_objects(self, tmp_path):
        accessor = InMemoryAccessor(layers=_layers(), drawn_objects=[DRAWN_ROW])
        failed, answer = _run(accessor, tmp_path, "cross_filter", source_layer="ortho", target_layers=["bati"],
                              raster_selection={"dock_objects": True})
        assert not failed and answer["filtered"] == ["bati"]
        failed, message = _run(InMemoryAccessor(layers=_layers()), tmp_path, "cross_filter", source_layer="ortho",
                               target_layers=["bati"], raster_selection={"dock_objects": True})
        assert failed and "no object is drawn on 'ortho'" in message


# --- REST ---------------------------------------------------------------------------------------------------------

@pytest.fixture
def client():
    accessor = InMemoryAccessor(layers=_layers(), drawn_objects=[DRAWN_ROW])
    return TestClient(create_app(accessor=accessor), base_url="http://127.0.0.1:8000")


class TestRoutes:
    def test_segment(self, client):
        response = client.post("/objects/segment", json={"raster": "ortho", "guide_layer": "bati", "name": "toits"})
        assert response.status_code == 200, response.text
        assert response.json()["layer"]["name"] == "toits" and response.json()["drawn"] == 12

    def test_segment_refused_is_a_400(self, client):
        response = client.post("/objects/segment", json={"raster": "bati", "guide_layer": "bati"})
        assert response.status_code == 400 and "raster layer" in response.json()["detail"]

    @pytest.mark.parametrize("body", [{"raster": "ortho"}, {"raster": "ortho", "guide_layer": "bati", "limit": 0},
                                      {"raster": "ortho", "guide_layer": "bati", "limit": 201}])
    def test_segment_body_is_checked(self, client, body):
        assert client.post("/objects/segment", json=body).status_code == 422

    def test_map_context_has_the_drawn_objects(self, client):
        assert client.get("/map/context").json()["drawn_objects"] == [DRAWN_ROW]

    def test_cross_filter_with_dock_objects(self, client):
        response = client.post("/filters/cross", json={"source_layer": "ortho", "target_layers": ["bati"],
                                                       "raster_selection": {"dock_objects": True}})
        assert response.status_code == 200, response.text

    @pytest.mark.parametrize("selection", [{"dock_objects": True, "segments": [ROOF]},
                                           {"dock_objects": True, "minimum": 3},
                                           {"dock_objects": True, "derivative": "aspect"}])
    def test_dock_objects_are_a_selection_of_their_own(self, client, selection):
        response = client.post("/filters/cross", json={"source_layer": "ortho", "target_layers": ["bati"],
                                                       "raster_selection": selection})
        assert response.status_code == 422

    def test_similar(self, client):
        response = client.post("/objects/similar", json={"raster": "ortho", "use_dock_object": True, "name": "toits"})
        assert response.status_code == 200, response.text
        assert response.json()["layer"]["name"] == "toits" and response.json()["objects"] == 3

    @pytest.mark.parametrize("body", [{"raster": "ortho"}, {"raster": "ortho", "example_layer": "bati", "use_dock_object": True},
                                      {"raster": "ortho", "use_dock_object": True, "unknown": 1}])
    def test_similar_needs_one_example(self, client, body):
        assert client.post("/objects/similar", json=body).status_code == 422

    def test_similar_refused_is_a_400(self, client):
        response = client.post("/objects/similar", json={"raster": "bati", "example_layer": "bati"})
        assert response.status_code == 400 and "raster layer" in response.json()["detail"]


# --- objects like an example (2026-11-11) -------------------------------------------------------------------------

class TestSimilarObjects:
    def test_the_chat_tool_is_offered_and_needs_one_example(self, tmp_path):
        tool = next(tool for tool in chat_tools() if tool.name == "similar_objects")
        assert not tool.read_only and not tool.requires_confirmation
        accessor = InMemoryAccessor(layers=_layers(), drawn_objects=[DRAWN_ROW])
        failed, message = _run(accessor, tmp_path, "similar_objects", raster="ortho")
        assert failed and "Give an example" in message
        failed, message = _run(accessor, tmp_path, "similar_objects", raster="ortho", example_layer="bati",
                               use_dock_object=True)
        assert failed and "one of them" in message

    def test_the_chat_tool_answers_without_nulls(self, tmp_path):
        accessor = InMemoryAccessor(layers=_layers(), drawn_objects=[DRAWN_ROW])
        failed, answer = _run(accessor, tmp_path, "similar_objects", raster="ortho", use_dock_object=True)
        assert not failed and answer["objects"] == 3 and "appearance" not in answer

    def test_the_accessor_reads_the_dock_on_the_main_thread(self, plugin_modules, monkeypatch):
        import filtermate_api.qgis_accessor as qgis_accessor
        dispatched = []
        monkeypatch.setattr(qgis_accessor, "run_on_main_thread", lambda fn, *a, **k: dispatched.append(fn) or fn(*a, **k))
        module = plugin_modules["adapters.public_api.drawn_objects"]
        module.similar_objects.return_value = {"layer": None, "objects": 0, "examined": 5, "windows": 1,
                                               "windows_planned": 2, "stopped_early": False, "seconds": 2.0,
                                               "example": {"sam_score": 0.9, "area_m2": 120.0}}
        result = _accessor({"R1": [ROOF]}).similar_objects("ortho", use_dock_object=True, extent_wkt="POLYGON((0 0))")
        assert isinstance(result, SimilarResult) and result.examined == 5 and result.layer is None
        kwargs = module.similar_objects.call_args.kwargs
        assert kwargs["dock_objects"] == {"R1": [ROOF]} and kwargs["use_dock_object"] is True
        assert kwargs["extent_wkt"] == "POLYGON((0 0))" and len(dispatched) == 1

    def test_without_the_dock_object_the_dock_is_not_read(self, plugin_modules):
        module = plugin_modules["adapters.public_api.drawn_objects"]
        module.similar_objects.return_value = {"objects": 0}
        _accessor({"R1": [ROOF]}).similar_objects("ortho", example_layer="bati")
        assert module.similar_objects.call_args.kwargs["dock_objects"] is None

    def test_a_refusal_is_a_filter_rejected_and_busy_is_busy(self, plugin_modules):
        module = plugin_modules["adapters.public_api.drawn_objects"]
        module.similar_objects.side_effect = ValueError("no object is drawn on 'ortho'")
        with pytest.raises(FilterRejected, match="no object is drawn"):
            _accessor({}).similar_objects("ortho", use_dock_object=True)
        plugin_modules["adapters.public_api.operations"].busy_reason.return_value = "a filter is running"
        module.similar_objects.reset_mock()
        with pytest.raises(QGISBusy):
            _accessor({}).similar_objects("ortho", use_dock_object=True)
        module.similar_objects.assert_not_called()

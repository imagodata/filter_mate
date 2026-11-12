# -*- coding: utf-8 -*-
"""Layers protected from the agent, through the REST API and the MCP server built on it (``python -m
filtermate_api.mcp``): the rule of the chat (core/agent/permissions.py), checked by QGISFilterMateAccessor on the
main thread, answered 403."""
from __future__ import annotations

import types
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from core.agent.permissions import PROTECTION_UNREADABLE  # noqa: E402
from filtermate_api import qgis_accessor  # noqa: E402
from filtermate_api.accessor import InMemoryAccessor, LayerProtected, LayerSummary  # noqa: E402
from filtermate_api.agent_tools import build_handlers  # noqa: E402
from filtermate_api.qgis_accessor import QGISFilterMateAccessor  # noqa: E402
from filtermate_api.server import create_app  # noqa: E402


class Protection:
    """``cadastre`` (id L1) is protected; the favorite ``fav-cadastre`` filters it."""

    def name_of(self, reference):
        return "cadastre" if reference in ("cadastre", "L1") else None

    def names(self):
        return ["cadastre"]

    def favorite_layers(self, favorite_id):
        return ["L1"] if favorite_id == "fav-cadastre" else ["L2"]

    def theme_layers(self, name):
        return ["L1"] if name == "Cadastre" else []

    def layers_joining(self, references):
        return ["L1"] if "owners" in references else []


@pytest.fixture
def operations(monkeypatch):
    """Every plugin module is a recorder: what reaches it is what was not refused."""
    module = MagicMock()
    module.busy_reason.return_value = ""
    module.raster_selection_from_dict.side_effect = lambda value: value
    module.point_cloud_criteria_from_dict.side_effect = lambda value: value
    module.cross_filter.return_value = types.SimpleNamespace(
        done={"L2": "routes"}, done_names=["routes"], failed={}, skipped={}, error="", outputs={}, details={})
    monkeypatch.setattr(qgis_accessor, "_plugin_module", lambda name: module)
    monkeypatch.setattr(qgis_accessor, "_project_protection", Protection)
    return module


@pytest.fixture
def accessor():
    public_api = MagicMock()
    plugin = types.SimpleNamespace(app=types.SimpleNamespace(favorites_manager=MagicMock(), history_manager=None))
    return QGISFilterMateAccessor(public_api=public_api, plugin=plugin)


def _sys_qgis(monkeypatch):
    """A QgsProject for the methods that read it before the operation (cross filter, geometry)."""
    import sys
    core = types.ModuleType("qgis.core")
    core.QgsProject = MagicMock()
    geometry = MagicMock()
    geometry.isNull.return_value = False
    core.QgsGeometry = types.SimpleNamespace(fromWkt=lambda wkt: geometry)
    crs = MagicMock()
    crs.isValid.return_value = True
    core.QgsCoordinateReferenceSystem = lambda authid: crs
    monkeypatch.setitem(sys.modules, "qgis.core", core)


WRITES = [
    ("apply_filter", lambda a: a.apply_filter("cadastre", '"a" = 1', "rest")),
    ("apply_filter by id", lambda a: a.apply_filter("L1", '"a" = 1', "rest")),
    ("cross_filter target", lambda a: a.cross_filter("routes", ["cadastre"], ["Intersect"])),
    ("cross_filter masked source", lambda a: a.cross_filter("cadastre", ["routes"], ["Intersect"], filter_source=True)),
    ("cross_filter source criteria", lambda a: a.cross_filter("cadastre", [], ["Intersect"],
                                                              point_cloud_criteria={"classes": [6], "z_min": None})),
    ("geometry_filter", lambda a: a.cross_filter_by_geometry("POINT(0 0)", "EPSG:2154", ["cadastre"], ["Intersect"])),
    ("point_cloud_filter", lambda a: a.filter_point_clouds(["cadastre"], {"classes": [6]})),
    ("clear_filters", lambda a: a.clear_filters(["routes", "cadastre"])),
    ("clear_filters of every layer", lambda a: a.clear_filters([])),
    ("apply_favorite", lambda a: a.apply_favorite("fav-cadastre")),
    ("set_layer_style", lambda a: a.set_layer_style("cadastre", "single")),
    ("set_labels", lambda a: a.set_labels("cadastre", field="nom")),
    ("update_features", lambda a: a.update_features("cadastre", values={"a": 1})),
    ("delete_features", lambda a: a.delete_features("cadastre", expression='"a" = 1')),
    ("add_features", lambda a: a.add_features("cadastre", features=[{"wkt": "POINT(0 0)"}])),
    ("add_field", lambda a: a.add_field("cadastre", "densite")),
    ("join_layers", lambda a: a.join_layers("cadastre", "routes", "a", "a")),
    ("rename_layer", lambda a: a.rename_layer("cadastre", "parcelles")),
    ("remove_layers", lambda a: a.remove_layers(["routes", "cadastre"])),
    ("map_theme apply", lambda a: a.map_theme("apply", "Cadastre")),
    ("remove_layers joined by it", lambda a: a.remove_layers(["owners"])),
]


class TestTheAccessorRefusesAChangeOfAProtectedLayer:
    @pytest.mark.parametrize("label, write", WRITES, ids=[label for label, _ in WRITES])
    def test_refused_before_anything_reaches_qgis(self, accessor, operations, monkeypatch, label, write):
        _sys_qgis(monkeypatch)
        favorites = accessor._plugin.app.favorites_manager
        with pytest.raises(LayerProtected, match="'cadastre'"):
            write(accessor)
        reached = [name for name, _args, _kwargs in operations.mock_calls
                   if name.split(".")[0].split("(")[0] not in (  # reads of the source before the check
                       "busy_reason", "resolve_layer", "layer_kind_by_class")]
        assert reached == [] and not accessor._public_api.mock_calls, reached
        assert not [call for call in favorites.mock_calls if call[0] != "get_favorite"]

    def test_used_as_a_source_or_the_table_of_a_join_it_stays_usable(self, accessor, operations, monkeypatch):
        _sys_qgis(monkeypatch)
        assert accessor.cross_filter("cadastre", ["routes"], ["Intersect"]).filtered == ["routes"]
        operations.join_layers.return_value = {"layer_name": "routes", "join_layer_name": "cadastre",
                                               "target_field": "a", "join_field": "a"}
        try:
            accessor.join_layers("routes", "cadastre", "a", "a")
        except LayerProtected:
            pytest.fail("the table of a join is only read")
        except TypeError:  # the recorder's answer is not a whole JoinAdded: it was reached, which is the point
            pass
        assert operations.join_layers.called

    def test_protected_layers_that_cannot_be_read_refuse_the_change(self, accessor, operations, monkeypatch):
        def unreadable():
            raise ImportError("protected_layers")
        monkeypatch.setattr(qgis_accessor, "_project_protection", unreadable)
        with pytest.raises(LayerProtected) as refused:
            accessor.remove_layers(["routes"])
        assert str(refused.value) == PROTECTION_UNREADABLE and not operations.remove_layers.called


class TestTheHistoryOfTheDock:
    """``/filters/undo`` and ``/filters/redo`` (``undo_filter`` / ``redo_filter`` of the MCP server on this API) set
    the filters of the layers of a step of the dock again."""

    class History:
        def __init__(self, entry):
            self.entry, self.moved = entry, []

        def peek_undo(self):
            return self.entry

        def undo(self):
            self.moved.append("undo")
            return self.entry

    def _accessor(self, monkeypatch, layer_ids):
        import sys
        layers = {layer_id: MagicMock() for layer_id in layer_ids}
        core = types.ModuleType("qgis.core")
        core.QgsProject = types.SimpleNamespace(instance=lambda: types.SimpleNamespace(mapLayer=layers.get))
        monkeypatch.setitem(sys.modules, "qgis.core", core)
        monkeypatch.setattr(qgis_accessor, "_project_protection", Protection)
        entry = types.SimpleNamespace(previous_filters=tuple((layer_id, "") for layer_id in layer_ids),
                                      expression='"a" = 1', layer_ids=tuple(layer_ids))
        history = self.History(entry)
        app = types.SimpleNamespace(history_manager=history, favorites_manager=None)
        return QGISFilterMateAccessor(public_api=MagicMock(), plugin=types.SimpleNamespace(app=app)), history, layers

    def test_a_step_on_a_protected_layer_is_refused_and_the_history_stays(self, monkeypatch):
        accessor, history, layers = self._accessor(monkeypatch, ["L2", "L1"])
        with pytest.raises(LayerProtected, match="'cadastre'"):
            accessor.undo_filter()
        assert history.moved == [] and not any(layer.setSubsetString.called for layer in layers.values())

    def test_a_step_on_other_layers_runs(self, monkeypatch):
        accessor, history, layers = self._accessor(monkeypatch, ["L2"])
        layers["L2"].setSubsetString.return_value = True
        assert accessor.undo_filter() is not None and history.moved == ["undo"]


class Refusing(InMemoryAccessor):
    """The REST routes over an accessor that refuses, as the QGIS one does for a protected layer."""

    def _refuse(self, *args, **kwargs):
        raise LayerProtected("Not done: the user protected 'cadastre' from the agent in this project.")

    apply_filter = set_layer_style = rename_layer = clear_filters = _refuse


class TestTheRoutesAnswer403:
    @pytest.fixture
    def client(self):
        accessor = Refusing(layers=[LayerSummary("L1", "cadastre", "ogr")])
        return TestClient(create_app(accessor=accessor), base_url="http://127.0.0.1:8000")

    @pytest.mark.parametrize("path, body", [
        ("/filters/apply", {"layer_name": "cadastre", "expression": '"a" = 1'}),
        ("/layers/style", {"layer": "cadastre", "mode": "single"}),
        ("/layers/rename", {"layer": "cadastre", "name": "parcelles"}),
    ])
    def test_403_with_the_refusal(self, client, path, body):
        response = client.post(path, json=body)
        assert response.status_code == 403, response.text
        assert "protected 'cadastre'" in response.json()["detail"]
        assert response.headers.get("X-FilterMate-Refusal") == "protected-layer"

    def test_the_mcp_server_on_the_rest_api_passes_the_refusal_on(self):
        from filtermate_api.mcp.rest_client import FilterMateClient
        client = FilterMateClient("http://127.0.0.1:1", "key")
        error = client._http_error("POST", "/layers/style", 403, {"X-FilterMate-Refusal": "protected-layer"},
                                   b'{"detail": "Not done: the user protected \'cadastre\' from the agent."}')
        assert "protected 'cadastre'" in str(error) and "key" not in str(error)
        assert "Check that the key" in str(client._http_error("POST", "/layers/style", 403, {}, b'{"detail": "x"}'))


def test_the_chat_tools_answer_the_refusal(tmp_path):
    handlers = build_handlers(Refusing(layers=[LayerSummary("L1", "cadastre", "ogr")]), tmp_path)
    from core.agent.tool_executor import ToolFailure
    with pytest.raises(ToolFailure, match="protected 'cadastre'"):
        handlers["rename_layer"]({"layer": "cadastre", "name": "x"})

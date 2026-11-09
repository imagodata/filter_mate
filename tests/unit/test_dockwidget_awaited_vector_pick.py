# -*- coding: utf-8 -*-
"""
A vector layer picked before its registration was lost.

Picking a just-added vector layer (dock combo or legend link) while the
``add_layers`` task still registered it aborted the layer change (the
layer is not in ``PROJECT_LAYERS`` yet), and once the registration landed
``get_project_layers_from_app`` re-applied the previous layer. Raster and
point cloud picks already wait for their registration
(``CoverageModeController.activate_awaited_layer``); vector picks now do
the same through ``_note_unregistered_vector_pick`` /
``_activate_awaited_vector_layer`` on the dock.
"""
import ast
import logging
import sys
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_DOCK = Path(__file__).resolve().parents[2] / "filter_mate_dockwidget.py"


class _VectorLayer:
    def __init__(self, layer_id, spatial=True):
        self._id, self._spatial = layer_id, spatial

    def id(self):
        return self._id

    def name(self):
        return self._id

    def isSpatial(self):
        return self._spatial


def _method(name, namespace):
    tree = ast.parse(_DOCK.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    method = next(node for node in cls.body
                  if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_DOCK), "exec"), namespace)
    return namespace[name]


@pytest.fixture
def dock(monkeypatch):
    fresh_b = _VectorLayer("b")
    qgis_core = types.ModuleType("qgis.core")
    qgis_core.QgsProject = types.SimpleNamespace(
        instance=lambda: types.SimpleNamespace(mapLayer={"b": fresh_b}.get))
    qgis = types.ModuleType("qgis")
    qgis.__path__ = []
    monkeypatch.setitem(sys.modules, "qgis", qgis)
    monkeypatch.setitem(sys.modules, "qgis.core", qgis_core)

    namespace = {"logger": logging.getLogger("test_awaited_pick"),
                 "QgsVectorLayer": _VectorLayer}
    instance = types.SimpleNamespace(
        PROJECT_LAYERS={"a": {}},
        changes=[],
        fresh_b=fresh_b,
    )
    instance.note = types.MethodType(_method("_note_unregistered_vector_pick", dict(namespace)), instance)
    instance.activate = types.MethodType(_method("_activate_awaited_vector_layer", dict(namespace)), instance)
    instance.current_layer_changed = lambda layer, manual_change=False: instance.changes.append((layer, manual_change))
    return instance


def test_unregistered_spatial_pick_waits_and_stops_the_chain(dock):
    assert dock.note(_VectorLayer("b"), manual_change=True) is True
    assert dock._awaited_vector_pick[0] == "b"


def test_registered_pick_goes_through(dock):
    assert dock.note(_VectorLayer("a"), manual_change=True) is False
    assert getattr(dock, "_awaited_vector_pick", None) is None


def test_table_without_geometry_is_not_awaited(dock):
    # Non-spatial tables never register: the chain stops (as before) but
    # nothing waits for them.
    assert dock.note(_VectorLayer("t", spatial=False), manual_change=True) is True
    assert getattr(dock, "_awaited_vector_pick", None) is None


def test_newer_manual_pick_replaces_the_awaited_one(dock):
    dock.note(_VectorLayer("b"), manual_change=True)
    assert dock.note(_VectorLayer("a"), manual_change=True) is False
    assert dock._awaited_vector_pick is None


def test_automatic_change_keeps_the_awaited_pick(dock):
    dock.note(_VectorLayer("b"), manual_change=True)
    assert dock.note(_VectorLayer("a"), manual_change=False) is False
    assert dock._awaited_vector_pick[0] == "b"


def test_activation_shows_the_layer_once_registered(dock):
    dock.note(_VectorLayer("b"), manual_change=True)
    dock.PROJECT_LAYERS["b"] = {}
    assert dock.activate() is True
    assert dock.changes == [(dock.fresh_b, True)]
    assert dock._awaited_vector_pick is None
    assert dock._user_layer_pick[1] == "b"


def test_activation_before_registration_keeps_waiting(dock):
    dock.note(_VectorLayer("b"), manual_change=True)
    assert dock.activate() is False
    assert dock._awaited_vector_pick[0] == "b"
    assert dock.changes == []


def test_activation_gives_way_to_a_newer_user_pick(dock):
    dock.note(_VectorLayer("b"), manual_change=True)
    dock.PROJECT_LAYERS["b"] = {}
    requested_at = dock._awaited_vector_pick[1]
    dock._user_layer_pick = (requested_at + 10.0, "a")  # e.g. a coverage layer shown meanwhile
    assert dock.activate() is False
    assert dock._awaited_vector_pick is None
    assert dock.changes == []


def test_no_awaited_pick_is_a_no_op(dock):
    assert dock.activate() is False


def test_automatic_change_does_not_replace_a_manual_pick_on_an_unregistered_layer(dock):
    dock.note(_VectorLayer("b"), manual_change=True)
    assert dock.note(_VectorLayer("z"), manual_change=False) is True
    assert dock._awaited_vector_pick[0] == "b"


def test_a_newer_automatic_change_replaces_an_automatic_one(dock):
    dock.note(_VectorLayer("z"), manual_change=False)
    dock.note(_VectorLayer("b"), manual_change=False)
    assert dock._awaited_vector_pick[0] == "b"


def test_an_automatic_pick_stays_automatic_at_activation(dock):
    """manual_change=True skips the post-filter protection, and _user_layer_pick
    is read by the undo / redo checks: it is for what the user picked."""
    dock.note(_VectorLayer("b"), manual_change=False)
    dock.PROJECT_LAYERS["b"] = {}
    assert dock.activate() is True
    assert dock.changes == [(dock.fresh_b, False)]
    assert getattr(dock, "_user_layer_pick", None) is None


def _called_names(method_name):
    """Names called in a dock method, in source order."""
    tree = ast.parse(_DOCK.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    method = next(node for node in cls.body
                  if isinstance(node, ast.FunctionDef) and node.name == method_name)
    return [node.func.attr for node in ast.walk(method)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)] + \
           [node.value for node in ast.walk(method)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("_")]


def test_the_dock_notes_and_activates_awaited_picks():
    assert "_note_unregistered_vector_pick" in _called_names("current_layer_changed")
    assert "_activate_awaited_vector_layer" in _called_names("get_project_layers_from_app")

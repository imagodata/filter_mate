# -*- coding: utf-8 -*-
"""A late refresh after loading (FilterMateApp._refresh_ui_with_layers) shows the layer the user picked in
the current-layer combo box, not QGIS' active layer (it switched it back in the first seconds after the
dock opened)."""
import ast
import pathlib
import types

import pytest

pytestmark = pytest.mark.unit

_APP = pathlib.Path(__file__).resolve().parents[2] / "filter_mate_app.py"


class _Layer:
    def __init__(self, layer_id):
        self._id = layer_id

    def id(self):
        return self._id


def _method(namespace):
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateApp")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "_layer_to_show_after_refresh")
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace["_layer_to_show_after_refresh"]


@pytest.fixture
def app():
    zones, dem = _Layer("zones"), _Layer("dem")
    layers = {"zones": zones, "dem": dem}
    method = _method({"get_filterable_layer_types": lambda: (_Layer,), "QgsVectorLayer": _Layer})
    instance = types.SimpleNamespace(
        PROJECT_LAYERS={"zones": {}, "dem": {}},
        PROJECT=types.SimpleNamespace(mapLayer=layers.get),
        iface=types.SimpleNamespace(activeLayer=lambda: zones),
        dockwidget=types.SimpleNamespace(current_layer=dem),
        layers=layers,
    )
    instance.choose = types.MethodType(method, instance)
    return instance


def test_user_pick_is_kept(app):
    app.dockwidget._user_layer_pick = (12.0, "dem")
    layer, reason = app.choose()
    assert (layer.id(), reason) == ("dem", "picked")


def test_without_pick_the_active_layer_wins(app):
    layer, reason = app.choose()
    assert (layer.id(), reason) == ("zones", "active")


def test_pick_of_another_project_is_ignored(app):
    app.dockwidget._user_layer_pick = (12.0, "gone")
    assert app.choose()[1] == "active"


def test_pick_shown_by_the_combo_but_not_applied_is_kept(app):
    """The combo box shows the pick but the panel never applied it (its handler was disconnected)."""
    app.dockwidget._user_layer_pick = (12.0, "dem")
    app.dockwidget.current_layer = app.layers["zones"]
    app.dockwidget.comboBox_filtering_current_layer = types.SimpleNamespace(currentLayer=lambda: app.layers["dem"])
    assert app.choose() == (app.layers["dem"], "picked")


def test_pick_no_longer_current_is_ignored(app):
    """The user picked dem, then the panel moved on (layer tree sync, another pick): no stale override."""
    app.dockwidget._user_layer_pick = (12.0, "dem")
    app.dockwidget.current_layer = app.layers["zones"]
    assert app.choose() == (app.layers["zones"], "active")


def test_first_layer_without_active(app):
    app.iface.activeLayer = lambda: None
    assert app.choose() == (app.layers["zones"], "first")

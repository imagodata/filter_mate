# -*- coding: utf-8 -*-
"""FilterMateApp.apply_layer_kind_options: raster / point cloud layers switched on or off in the
Configuration tab are registered or unregistered without the F5 reload (which cancels every task)."""
import ast
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_APP = pathlib.Path(__file__).resolve().parents[2] / "filter_mate_app.py"


def _extract(names, namespace):
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateApp")
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace


class _Layer:
    def __init__(self, layer_id, subset=''):
        self._id, self._subset = layer_id, subset

    def id(self):
        return self._id

    def name(self):
        return f"name_{self._id}"

    def subsetString(self):
        return self._subset


class Vector(_Layer):
    pass


class Raster(_Layer):
    pass


class PointCloud(_Layer):
    pass


@pytest.fixture
def app():
    warnings = []
    namespace = _extract(("apply_layer_kind_options", "_warn_filtered_layers_left"), {
        "QgsVectorLayer": Vector,
        "get_filterable_layer_types": lambda: (Vector, PointCloud),  # rasters just turned off
        "get_current_layer_combo_filters": lambda: "HasGeometry|PointCloudLayer",
        "exclude_non_analysis_rasters": lambda combo: combo.excluded.append('wms'),
        "show_warning": warnings.append,
        "QCoreApplication": types.SimpleNamespace(translate=lambda context, text: text),
        "logger": MagicMock(),
    })
    layers = {lid: layer for lid, layer in (
        ("v1", Vector("v1")), ("r1", Raster("r1")), ("r2", Raster("r2")), ("p1", PointCloud("p1")))}
    instance = types.SimpleNamespace(
        _unloading=False,
        PROJECT=types.SimpleNamespace(mapLayers=lambda: dict(layers), mapLayer=layers.get),
        PROJECT_LAYERS={"v1": {}, "r1": {}, "r2": {}},
        dockwidget=types.SimpleNamespace(comboBox_filtering_current_layer=MagicMock(excluded=[])),
        manage_task=MagicMock(),
        _filter_usable_layers=lambda candidates: [layer for layer in candidates if isinstance(layer, PointCloud)],
        warnings=warnings,
    )
    for name in ("apply_layer_kind_options", "_warn_filtered_layers_left"):
        setattr(instance, name, types.MethodType(namespace[name], instance))
    return instance


def _registry(monkeypatch, app, derived_ids):
    """Make ``from .adapters.qgis.coverage_layers.snapshots import registry`` resolve in the extracted methods."""
    package = "fm_app_kinds_test"
    for name in ("", ".adapters", ".adapters.qgis", ".adapters.qgis.coverage_layers"):
        module = types.ModuleType(package + name)
        module.__path__ = []
        monkeypatch.setitem(sys.modules, package + name, module)
    snapshots = types.ModuleType(f"{package}.adapters.qgis.coverage_layers.snapshots")
    snapshots.registry = lambda: types.SimpleNamespace(get=lambda lid: object() if lid in derived_ids else None)
    monkeypatch.setitem(sys.modules, snapshots.__name__, snapshots)
    app._warn_filtered_layers_left.__func__.__globals__["__package__"] = package


def test_turned_off_kind_is_unregistered_and_enabled_kind_registered(app):
    assert app.apply_layer_kind_options() == (1, 2)
    app.manage_task.assert_any_call('remove_layers', ['r1', 'r2'])
    added = [call.args[1] for call in app.manage_task.call_args_list if call.args[0] == 'add_layers']
    assert [[layer.id() for layer in layers] for layers in added] == [['p1']]
    combo = app.dockwidget.comboBox_filtering_current_layer
    combo.setFilters.assert_called_once_with("HasGeometry|PointCloudLayer")
    assert combo.excluded == ['wms']


def test_vector_layers_are_never_touched(app):
    app.PROJECT_LAYERS = {}
    app.apply_layer_kind_options()
    for call in app.manage_task.call_args_list:
        ids = [item if isinstance(item, str) else item.id() for item in call.args[1]]
        assert 'v1' not in ids


def test_nothing_to_do_queues_no_task(app):
    app.PROJECT_LAYERS = {"v1": {}, "p1": {}}
    assert app.apply_layer_kind_options() == (0, 0)
    app.manage_task.assert_not_called()
    app.dockwidget.comboBox_filtering_current_layer.setFilters.assert_called_once()


def test_unloading_does_nothing(app):
    app._unloading = True
    assert app.apply_layer_kind_options() == (0, 0)
    app.manage_task.assert_not_called()


def test_filtered_layers_of_a_kind_turned_off_are_named(app, monkeypatch):
    """They stay filtered (no silent unfilter); FilterMate no longer lists them, so the user is told."""
    layers = {"r1": Raster("r1", subset=''), "r2": Raster("r2"), "p1": PointCloud("p1", subset="Classification = 6")}
    app.PROJECT = types.SimpleNamespace(mapLayers=lambda: dict(layers), mapLayer=layers.get)
    _registry(monkeypatch, app, derived_ids={"r1"})
    app._warn_filtered_layers_left(["r1", "r2", "p1", "gone"])
    assert len(app.warnings) == 1
    assert app.warnings[0].startswith("2 layer(s) stay filtered: name_r1, name_p1.")


def test_unfiltered_layers_raise_no_warning(app, monkeypatch):
    _registry(monkeypatch, app, derived_ids=set())
    app._warn_filtered_layers_left(["r1", "r2"])
    assert app.warnings == []

# -*- coding: utf-8 -*-
"""
ui/widgets/tree_view.py imports the JSON model relatively.

``from ui.widgets.json_view import ...`` only worked when the plugin folder
itself was on sys.path (a test run from the repository), never inside QGIS,
where the plugin is the ``filter_mate`` package: the Configuration tab's
cancel path (ConfigController._reload_configuration) failed on it.
"""
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_tree_view_test"


def test_tree_view_imports_inside_the_plugin_package(monkeypatch):
    for name in ("ui", "ui.widgets", "ui.widgets.json_view"):
        monkeypatch.setitem(sys.modules, name, None)  # no top-level 'ui' package, as in QGIS
    for name in ("", ".ui", ".ui.widgets"):
        package = types.ModuleType(_PKG + name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, _PKG + name, package)
    json_view = types.ModuleType(f"{_PKG}.ui.widgets.json_view")
    json_view.JsonModel, json_view.JsonSortFilterProxyModel = object(), object()
    json_view.is_available = lambda: True
    monkeypatch.setitem(sys.modules, json_view.__name__, json_view)
    spec = importlib.util.spec_from_file_location(f"{_PKG}.ui.widgets.tree_view", _ROOT / "ui" / "widgets" / "tree_view.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    assert module.JsonModel is json_view.JsonModel

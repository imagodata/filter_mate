# -*- coding: utf-8 -*-
"""
2026-10-17: feature_picker_guard finds the plugin's dock.

``from filter_mate_dockwidget import _active_dockwidget`` (absolute) raised
ImportError inside the plugin package, swallowed: the feature picker was never
detached before a subset change. The dock module is now looked up by the
plugin's package, and the widget is only touched on the main thread.
"""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = "fm_guard_pkg"


@pytest.fixture
def sql_utils(monkeypatch):
    for name in (PACKAGE, f"{PACKAGE}.infrastructure", f"{PACKAGE}.infrastructure.database"):
        package = types.ModuleType(name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, name, package)
    name = f"{PACKAGE}.infrastructure.database.sql_utils"
    spec = importlib.util.spec_from_file_location(name, ROOT / "infrastructure" / "database" / "sql_utils.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def _dock(monkeypatch, layer):
    picker = MagicMock()
    picker.layer.return_value = layer
    dock_module = types.ModuleType(f"{PACKAGE}.filter_mate_dockwidget")
    dock_module._active_dockwidget = types.SimpleNamespace(mFeaturePickerWidget_exploring_single_selection=picker)
    monkeypatch.setitem(sys.modules, dock_module.__name__, dock_module)
    return picker


def test_the_picker_is_detached_then_reattached(sql_utils, monkeypatch):
    layer = MagicMock()
    picker = _dock(monkeypatch, layer)
    monkeypatch.setattr(sql_utils, "_on_main_thread", lambda: True)
    assert sql_utils._PLUGIN_PACKAGE == PACKAGE
    with sql_utils.feature_picker_guard(layer):
        picker.setLayer.assert_called_once_with(None)
    assert picker.setLayer.call_args_list[-1].args == (layer,)


def test_another_layer_leaves_the_picker_alone(sql_utils, monkeypatch):
    picker = _dock(monkeypatch, MagicMock())
    monkeypatch.setattr(sql_utils, "_on_main_thread", lambda: True)
    with sql_utils.feature_picker_guard(MagicMock()):
        pass
    picker.setLayer.assert_not_called()


def test_a_worker_thread_never_touches_the_widget(sql_utils, monkeypatch):
    layer = MagicMock()
    picker = _dock(monkeypatch, layer)
    monkeypatch.setattr(sql_utils, "_on_main_thread", lambda: False)
    with sql_utils.feature_picker_guard(layer):
        pass
    picker.setLayer.assert_not_called()


def test_no_dock_loaded_is_no_error(sql_utils, monkeypatch):
    monkeypatch.delitem(sys.modules, f"{PACKAGE}.filter_mate_dockwidget", raising=False)
    with sql_utils.feature_picker_guard(MagicMock()):
        pass

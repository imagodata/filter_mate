# -*- coding: utf-8 -*-
"""After undo / redo the dock puts the source layer back in the current-layer combo box for 2 s
(async layer changes used to move it), but a layer the user picks in that window is respected."""
import contextlib
import importlib
import pathlib
import sys
import time
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_undo_user_pick_test"


def _load():
    """Load adapters/undo_redo_handler.py inside a package, so its relative imports resolve."""
    for name, path in (("", _ROOT), (".adapters", _ROOT / "adapters"), (".infrastructure", _ROOT / "infrastructure")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.undo_redo_handler")


@pytest.fixture
def handler_module(monkeypatch):
    module = _load()
    timers = []
    monkeypatch.setattr(module, "QGIS_AVAILABLE", True)
    monkeypatch.setattr(module, "QTimer", types.SimpleNamespace(singleShot=lambda delay, slot: timers.append(slot)))
    monkeypatch.setattr(module, "SignalBlocker", lambda widget: contextlib.nullcontext())
    module._test_timers = timers
    return module


def _layer(layer_id):
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.name.return_value = layer_id
    layer.isValid.return_value = True
    return layer


class _Dock(types.SimpleNamespace):
    """The handler keeps a weak reference to the dock."""


def _setup(handler_module, monkeypatch):
    source, other = _layer("source"), _layer("other")
    layers = {"source": source, "other": other}
    monkeypatch.setattr(handler_module, "QgsProject",
                        types.SimpleNamespace(instance=lambda: types.SimpleNamespace(mapLayer=layers.get)))
    dock = _Dock(comboBox_filtering_current_layer=MagicMock(), current_layer=source)
    dock.comboBox_filtering_current_layer.currentLayer.return_value = other  # moved away from the source
    handler = handler_module.UndoRedoHandler.__new__(handler_module.UndoRedoHandler)
    handler._setup_combobox_protection(dock, source, "undo")
    return dock, source


def test_async_change_is_reverted(handler_module, monkeypatch):
    dock, source = _setup(handler_module, monkeypatch)
    assert len(handler_module._test_timers) == 5
    handler_module._test_timers[0]()
    dock.comboBox_filtering_current_layer.setLayer.assert_called_once_with(source)
    assert dock.current_layer is source


def test_user_pick_after_undo_is_respected(handler_module, monkeypatch):
    dock, source = _setup(handler_module, monkeypatch)
    dock._user_layer_pick = (time.perf_counter() + 0.001, 'other')  # the user picked a layer in the combo box
    for slot in handler_module._test_timers:
        slot()
    dock.comboBox_filtering_current_layer.setLayer.assert_not_called()


def test_user_pick_before_undo_does_not_disable_the_protection(handler_module, monkeypatch):
    earlier = time.perf_counter() - 10
    dock, source = _setup(handler_module, monkeypatch)
    dock._user_layer_pick = (earlier, 'other')
    handler_module._test_timers[0]()
    dock.comboBox_filtering_current_layer.setLayer.assert_called_once_with(source)


def test_a_pick_not_looked_at_yet_is_looked_at_first(handler_module, monkeypatch):
    """The check and the key press fall due in one pass: the check runs before the call the pick detector
    posted (ConfigurationManager._stamp_user_layer_picks), it used to put the source layer back over the pick."""
    dock, source = _setup(handler_module, monkeypatch)
    dock._record_pending_layer_pick = lambda: setattr(dock, '_user_layer_pick', (time.perf_counter(), 'other'))
    handler_module._test_timers[0]()
    dock.comboBox_filtering_current_layer.setLayer.assert_not_called()

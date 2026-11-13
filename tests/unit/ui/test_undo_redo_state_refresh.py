# -*- coding: utf-8 -*-
"""Undo / Redo follow the targets key and the targets checked on screen.

With the key on, Undo / Redo also restore the targets checked on screen (FilterMateApp._handle_undo_redo), so their
buttons are computed again when the key or a check changes. A click in the list emits only the model's
itemChanged, and a layer change empties and fills the list again: the dock asks for the state once per event loop
pass, never while a filter runs (its end computes it). The dock methods are compiled alone, the module is not
imported; the model and the timer are real Qt objects.
"""
import ast
import importlib
import os
import pathlib
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
QT_BINDING = os.environ.get('FILTERMATE_TEST_QT_BINDING', 'PyQt6')
QtCore = pytest.importorskip(QT_BINDING + '.QtCore')
QtGui = importlib.import_module(QT_BINDING + '.QtGui')
QtWidgets = importlib.import_module(QT_BINDING + '.QtWidgets')

_DOCKWIDGET = pathlib.Path(__file__).resolve().parents[3] / "filter_mate_dockwidget.py"


def _dock_method(name, **names):
    tree = ast.parse(_DOCKWIDGET.read_text(encoding="utf-8"))
    dock_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    func = next(node for node in dock_class.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {"logger": MagicMock(), **names}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[func], type_ignores=[])), str(_DOCKWIDGET), "exec"), namespace)
    return func, namespace[name]


def test_targets_key_asks_for_the_undo_redo_state():
    _, state_changed = _dock_method("filtering_layers_to_filter_state_changed")
    key = MagicMock()
    widgets = {"FILTERING": {"HAS_LAYERS_TO_FILTER": {"WIDGET": key}, "LAYERS_TO_FILTER": {"WIDGET": MagicMock()},
                             "USE_CENTROIDS_DISTANT_LAYERS": {"WIDGET": MagicMock()}}}
    dock = types.SimpleNamespace(widgets_initialized=True, has_loaded_layers=True, widgets=widgets,
                                 _set_layout_widgets_enabled=lambda *a: None, _controller_integration=None,
                                 _schedule_centroid_targets=lambda: None, _schedule_undo_redo_state=MagicMock())

    state_changed(dock)

    dock._schedule_undo_redo_state.assert_called_once_with()


def test_the_dock_connects_the_targets_list_when_it_creates_it():
    func, _ = _dock_method("setupUiCustom")
    source = ast.unparse(func)
    created = source.index("self.checkableComboBoxLayer_filtering_layers_to_filter = ")
    assert source.index("self._connect_undo_redo_state()") > created


@pytest.fixture
def dock():
    """A dock with the real targets model and the three methods of the dock."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    methods = {name: _dock_method(name, QTimer=QtCore.QTimer)[1]
               for name in ("_connect_undo_redo_state", "_schedule_undo_redo_state", "_emit_undo_redo_state")}
    dock = type("Dock", (QtCore.QObject,), methods)()
    model = QtGui.QStandardItemModel(dock)
    dock.checkableComboBoxLayer_filtering_layers_to_filter = types.SimpleNamespace(model=lambda: model)
    dock.undoRedoStateRequested = MagicMock()
    dock._filtering_in_progress = False
    dock._connect_undo_redo_state()
    dock.model = model

    def settle():
        for _ in range(3):
            app.processEvents()
        return dock.undoRedoStateRequested.emit.call_count

    dock.settle = settle
    return dock


def _fill(model, checked):
    """What a layer change does: the list emptied, then the targets added and the saved ones checked."""
    model.clear()
    for layer_id in ("a", "b", "c"):
        item = QtGui.QStandardItem(layer_id)
        item.setCheckable(True)
        model.appendRow(item)
        item.setCheckState(QtCore.Qt.CheckState.Checked if layer_id in checked else QtCore.Qt.CheckState.Unchecked)


def test_a_filled_list_asks_once(dock):
    _fill(dock.model, ["a", "c"])

    assert dock.settle() == 1


def test_a_click_in_the_list_asks(dock):
    _fill(dock.model, [])
    dock.settle()

    dock.model.item(1).setCheckState(QtCore.Qt.CheckState.Checked)  # the click emits itemChanged only

    assert dock.settle() == 2


def test_nothing_asked_while_a_filter_runs(dock):
    dock._filtering_in_progress = True
    _fill(dock.model, ["a"])
    dock._schedule_undo_redo_state()

    assert dock.settle() == 0

# -*- coding: utf-8 -*-
"""The detector of the layers the user picks in the current-layer combo box
(ConfigurationManager._stamp_user_layer_picks), with fake Qt objects.

It looks at an input in a call it posts. A check of the post-filter / undo windows due in the same pass of the
event loop as the input runs before that call: it must look at the input first (``_record_pending_layer_pick``),
or it puts the source layer back and the detector sees no change (CI, QGIS 3.34: "picked=dem combo=zones").
"""
import ast
import importlib
import logging
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_pick_detector_test"


class _QEvent:
    class Type:
        MouseButtonRelease, KeyPress, Wheel, Hide = "release", "key", "wheel", "hide"

    def __init__(self, kind):
        self._kind = kind

    def type(self):
        return self._kind


class _QObject:
    def __init__(self, parent=None):
        self.parent = parent


class _Widget:
    def __init__(self):
        self.filters = []
        self._viewport = None

    def installEventFilter(self, event_filter):  # noqa: N802 - Qt name
        self.filters.append(event_filter)

    def viewport(self):
        if self._viewport is None:
            self._viewport = _Widget()
        return self._viewport


class _Layer:
    def __init__(self, layer_id):
        self._id = layer_id

    def id(self):
        return self._id

    def name(self):
        return self._id

    def isValid(self):  # noqa: N802 - QGIS name
        return True


class _Combo(_Widget):
    def __init__(self, layer):
        super().__init__()
        self.layer = layer
        self._view = _Widget()
        self.blocked = False

    def currentLayer(self):  # noqa: N802 - QGIS name
        return self.layer

    def setLayer(self, layer):  # noqa: N802 - QGIS name
        self.layer = layer

    def view(self):
        return self._view

    def completer(self):
        return None

    def lineEdit(self):  # noqa: N802 - Qt name
        return None

    def blockSignals(self, flag):  # noqa: N802 - Qt name
        self.blocked = flag

    def signalsBlocked(self):  # noqa: N802 - Qt name
        return self.blocked


class _Dock:
    """Weak-referenceable stand-in for the dock."""


@pytest.fixture
def qt(monkeypatch):
    """Fake QEvent / QObject / QTimer (calls posted with singleShot run when the test says so)."""
    posted = []
    qtcore = sys.modules["qgis.PyQt.QtCore"]
    monkeypatch.setattr(qtcore, "QEvent", _QEvent, raising=False)
    monkeypatch.setattr(qtcore, "QObject", _QObject, raising=False)
    monkeypatch.setattr(qtcore, "QTimer", types.SimpleNamespace(singleShot=lambda delay, slot: posted.append(slot)),
                        raising=False)
    return posted


def _detector():
    """``_stamp_user_layer_picks`` extracted from the source (the module itself is never imported)."""
    path = _ROOT / "ui" / "managers" / "configuration_manager.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(item for item in ast.walk(tree)
                if isinstance(item, ast.FunctionDef) and item.name == "_stamp_user_layer_picks")
    node.decorator_list = []
    namespace = {"logger": logging.getLogger("pick-detector-test")}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["_stamp_user_layer_picks"]


@pytest.fixture
def dock(qt):
    source, other = _Layer("zones"), _Layer("dem")
    d = _Dock()
    d.layers = {"zones": source, "dem": other}
    d.comboBox_filtering_current_layer = _Combo(source)
    d.current_layer = source
    d._filtering_in_progress = False
    d.ended = 0
    d._end_post_filter_window = lambda: setattr(d, "ended", d.ended + 1)
    d.current_layer_changed = MagicMock()
    _detector()(d)
    d.filter = d.comboBox_filtering_current_layer.filters[0]
    return d


def _user_input(d, widget=None, kind=_QEvent.Type.KeyPress):
    """The event filter sees the input before the combo box handles it."""
    d.filter.eventFilter(widget or d.comboBox_filtering_current_layer, _QEvent(kind))


def _run_posted(posted):
    while posted:
        posted.pop(0)()


def test_a_pick_is_recorded_after_the_input(dock, qt):
    _user_input(dock)
    dock.comboBox_filtering_current_layer.layer = dock.layers["dem"]  # the combo box handles the key
    _run_posted(qt)
    assert dock._user_layer_pick[1] == "dem"
    assert dock.ended == 1


def test_a_check_due_with_the_input_looks_at_it_first(dock, qt):
    _user_input(dock)
    dock.comboBox_filtering_current_layer.layer = dock.layers["dem"]
    dock._record_pending_layer_pick()  # a window check, before the call posted by the input
    assert dock._user_layer_pick[1] == "dem"
    assert dock.ended == 1
    _run_posted(qt)
    assert dock.ended == 1  # looked at once


def test_an_input_without_change_records_nothing(dock, qt):
    _user_input(dock)
    dock._record_pending_layer_pick()
    _run_posted(qt)
    assert not hasattr(dock, "_user_layer_pick")
    assert dock.ended == 0


def test_a_change_without_input_is_not_a_pick(dock, qt):
    dock.comboBox_filtering_current_layer.layer = dock.layers["dem"]  # an async change
    dock._record_pending_layer_pick()
    assert not hasattr(dock, "_user_layer_pick")


def test_the_popup_closing_counts_as_an_input(dock, qt):
    """Qt 5 macOS style: the call posted by the click runs in the flash event loops of hidePopup, before the
    combo box takes the item (itemSelected comes after hidePopup)."""
    view = dock.comboBox_filtering_current_layer.view()
    _user_input(dock, view.viewport(), _QEvent.Type.MouseButtonRelease)
    _run_posted(qt)  # inside hidePopup: no change yet
    _user_input(dock, view, _QEvent.Type.Hide)  # the popup closes
    dock.comboBox_filtering_current_layer.layer = dock.layers["dem"]  # itemSelected
    _run_posted(qt)
    assert dock._user_layer_pick[1] == "dem"


def test_a_popup_closed_without_input_in_it_is_not_an_input(dock, qt):
    """Closed by the dock hiding or being disabled: a change in the same pass is not the user's."""
    _user_input(dock, dock.comboBox_filtering_current_layer.view(), _QEvent.Type.Hide)
    dock.comboBox_filtering_current_layer.layer = dock.layers["dem"]
    _run_posted(qt)
    assert not hasattr(dock, "_user_layer_pick")


def test_the_combo_box_hiding_is_not_an_input(dock, qt):
    _user_input(dock, dock.comboBox_filtering_current_layer, _QEvent.Type.Hide)  # the dock is closed
    dock.comboBox_filtering_current_layer.layer = dock.layers["dem"]
    _run_posted(qt)
    assert not hasattr(dock, "_user_layer_pick")


def _undo_handler(monkeypatch):
    for name, path in (("", _ROOT), (".adapters", _ROOT / "adapters"), (".infrastructure", _ROOT / "infrastructure")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    module = importlib.import_module(f"{_PKG}.adapters.undo_redo_handler")
    checks = []
    monkeypatch.setattr(module, "QGIS_AVAILABLE", True)
    monkeypatch.setattr(module, "QTimer", types.SimpleNamespace(singleShot=lambda delay, slot: checks.append(slot)))
    return module, checks


def _undo(dock, monkeypatch):
    module, checks = _undo_handler(monkeypatch)
    monkeypatch.setattr(module, "QgsProject",
                        types.SimpleNamespace(instance=lambda: types.SimpleNamespace(mapLayer=dock.layers.get)))
    module.UndoRedoHandler.__new__(module.UndoRedoHandler)._setup_combobox_protection(
        dock, dock.layers["zones"], "undo")
    return checks


def test_the_ci_race_an_undo_check_due_with_the_key_press_keeps_the_pick(dock, qt, monkeypatch):
    """Undo in the post-filter window (combo box blocked), then the key press and the undo's first check fall due
    in one pass: the press, the check, then the call the detector posted. The check used to put the source layer
    back and the call to see no change: the pick was lost."""
    dock.comboBox_filtering_current_layer.blocked = True
    checks = _undo(dock, monkeypatch)
    _user_input(dock)
    dock.comboBox_filtering_current_layer.layer = dock.layers["dem"]  # blocked: the panel is not told
    checks[0]()  # due in the same pass as the key press
    _run_posted(qt)
    assert dock.comboBox_filtering_current_layer.currentLayer().id() == "dem"
    assert dock._user_layer_pick[1] == "dem"
    assert dock.ended == 1  # the window ends: the pick is applied (FilterResultHandler)


def test_the_same_race_outside_a_post_filter_window(dock, qt, monkeypatch):
    dock._end_post_filter_window = None
    checks = _undo(dock, monkeypatch)
    _user_input(dock)
    dock.comboBox_filtering_current_layer.layer = dock.layers["dem"]
    dock.current_layer = dock.layers["dem"]  # the combo's handler applied it
    checks[0]()
    _run_posted(qt)
    assert dock.comboBox_filtering_current_layer.currentLayer().id() == "dem"
    assert dock.current_layer.id() == "dem"
    assert dock._user_layer_pick[1] == "dem"


def test_the_undo_check_still_reverts_an_async_change(dock, qt, monkeypatch):
    checks = _undo(dock, monkeypatch)
    dock.comboBox_filtering_current_layer.layer = dock.layers["dem"]  # no user input
    checks[0]()
    assert dock.comboBox_filtering_current_layer.currentLayer().id() == "zones"
    assert not hasattr(dock, "_user_layer_pick")

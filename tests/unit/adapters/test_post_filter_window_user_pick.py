# -*- coding: utf-8 -*-
"""Post-filter window of the current-layer combo box (FilterResultHandler._schedule_delayed_reconnection).

For 1.5 s after a filter the combo box stays blocked and its checks put the source layer back when an async
change moved it, never over a layer the user picked (a pick not looked at yet is looked at first).
A layer picked during the task is applied when it is over.
A failed or canceled task ends the protection too.
A check that finds the panel moved too puts it back through the layer change (the coverage panel follows).
"""
import importlib
import pathlib
import sys
import time
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_post_filter_window_test"


def _load():
    """Load adapters/filter_result_handler.py inside a package, so its relative imports resolve."""
    for name, path in (("", _ROOT), (".adapters", _ROOT / "adapters"), (".infrastructure", _ROOT / "infrastructure"),
                       (".config", _ROOT / "config")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.filter_result_handler")


def _layer(layer_id):
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.name.return_value = layer_id
    layer.isValid.return_value = True
    return layer


@pytest.fixture
def window(monkeypatch):
    """The handler with a fake dock: ``window.timers`` = [(delay, slot)], the combo box blocked by the task."""
    module = _load()
    timers = []
    monkeypatch.setattr(module, "QTimer", types.SimpleNamespace(singleShot=lambda delay, slot: timers.append((delay, slot))))
    layers = {"zones": _layer("zones"), "dem": _layer("dem")}
    monkeypatch.setattr(module, "QgsProject",
                        types.SimpleNamespace(instance=lambda: types.SimpleNamespace(mapLayer=layers.get)))
    combo = MagicMock()
    combo.currentLayer.return_value = layers["zones"]
    combo.setLayer.side_effect = lambda layer: setattr(combo.currentLayer, "return_value", layer)
    dock = types.SimpleNamespace(
        comboBox_filtering_current_layer=combo, current_layer=layers["zones"], PROJECT_LAYERS={"zones": {}, "dem": {}},
        manageSignal=MagicMock(), current_layer_changed=MagicMock(), _filtering_in_progress=True,
        _combo_protection_gen=1, _combo_blocked_at=time.perf_counter(), project_props={},
    )
    handler = module.FilterResultHandler(get_dockwidget_callback=lambda: dock)
    return types.SimpleNamespace(module=module, handler=handler, dock=dock, combo=combo, layers=layers, timers=timers)


def _checks(window):
    return [slot for delay, slot in window.timers if delay < 1500]


def _end(window):
    return next(slot for delay, slot in window.timers if delay == 1500)


def _ended(window):
    """Protection over: combo box unblocked, its handler reconnected, filtering flag reset."""
    return (not window.dock._filtering_in_progress
            and window.combo.blockSignals.call_args_list[-1].args == (False,)
            and window.dock.manageSignal.call_args_list[-1].args == (["FILTERING", "CURRENT_LAYER"], 'connect', 'layerChanged'))


def test_a_check_puts_back_the_source_layer_after_an_async_change(window):
    window.handler._schedule_delayed_reconnection("zones")
    window.combo.currentLayer.return_value = window.layers["dem"]  # no user input
    _checks(window)[0]()
    window.combo.setLayer.assert_called_once_with(window.layers["zones"])
    assert window.dock.current_layer is window.layers["zones"]
    window.dock.current_layer_changed.assert_not_called()


def test_a_check_looks_at_a_pick_not_looked_at_yet_first(window):
    """The CI race: the check and the key press fall due in one pass, the check runs before the call the
    detector posted (ConfigurationManager._stamp_user_layer_picks)."""
    dock = window.dock

    def record_pending_pick():  # what the detector does for a key press that changed the layer
        dock._user_layer_pick = (time.perf_counter(), "dem")
        dock._end_post_filter_window()

    window.handler._schedule_delayed_reconnection("zones")
    window.combo.currentLayer.return_value = window.layers["dem"]  # the key press (signals blocked)
    dock._record_pending_layer_pick = record_pending_pick
    _checks(window)[0]()
    window.combo.setLayer.assert_not_called()  # not put back
    assert _ended(window)
    dock.current_layer_changed.assert_called_once_with(window.layers["dem"], manual_change=True)  # applied


def test_a_check_leaves_a_pick_of_this_window_alone(window):
    window.handler._schedule_delayed_reconnection("zones")
    window.combo.currentLayer.return_value = window.layers["dem"]
    window.dock._user_layer_pick = (time.perf_counter(), "dem")  # recorded, the window not ended
    for check in _checks(window):
        check()
    window.combo.setLayer.assert_not_called()


def test_a_layer_picked_during_the_task_is_applied_when_it_is_over(window):
    """The combo box was blocked during the task: the pick was shown, then the completion put the source layer
    back. The window ends at once and applies it (it used to be dropped)."""
    window.dock._user_layer_pick = (time.perf_counter(), "dem")
    window.handler._schedule_delayed_reconnection("zones")
    assert _ended(window)
    assert window.timers == []
    window.combo.setLayer.assert_called_once_with(window.layers["dem"])  # handler connected: applies it
    assert window.dock._end_post_filter_window is None


def test_the_source_layer_picked_back_during_the_task_keeps_the_window(window):
    window.dock._user_layer_pick = (time.perf_counter(), "zones")
    window.handler._schedule_delayed_reconnection("zones")
    assert len(_checks(window)) == 5
    assert not _ended(window)


def test_the_completion_looks_at_a_pick_not_looked_at_yet_first(window):
    """The completion is a queued call too: it can run before the call the detector posted for a key press made
    during the task, and it puts the source layer back in the combo box."""
    class _Looked(Exception):
        pass

    def record_pending_pick():
        raise _Looked  # stops the completion here: nothing ran before

    window.dock._record_pending_layer_pick = record_pending_pick
    with pytest.raises(_Looked):
        window.handler.handle_task_completion("filter", MagicMock(), {"infos": {}, "task": {"layers": []}}, "zones")
    window.combo.setLayer.assert_not_called()


def test_a_layer_picked_before_the_task_is_not_applied(window):
    window.dock._user_layer_pick = (window.dock._combo_blocked_at - 5, "dem")
    window.handler._schedule_delayed_reconnection("zones")
    assert len(_checks(window)) == 5
    _end(window)()
    assert _ended(window)
    window.combo.setLayer.assert_not_called()
    window.dock.current_layer_changed.assert_not_called()


def test_a_check_moves_the_panel_back_through_the_layer_change(window):
    """An undo in the window resets the filtering flag: an async change can then show a raster page. The check
    puts the panel back through the layer change (the coverage panel follows), not only the combo box."""
    window.dock._filtering_in_progress = False
    window.handler._schedule_delayed_reconnection("zones")
    window.combo.currentLayer.return_value = window.layers["dem"]
    window.dock.current_layer = window.layers["dem"]
    _checks(window)[0]()
    window.dock.current_layer_changed.assert_called_once_with(window.layers["zones"], manual_change=True)
    assert window.combo.currentLayer() is window.layers["zones"]
    assert window.dock.current_layer is window.layers["zones"]


def test_a_terminated_task_ends_the_protection(window):
    """A failed or canceled task never reached the completion: the combo box stayed blocked, the flag set."""
    window.handler.handle_task_terminated("zones")
    assert not _ended(window)
    _end(window)()
    assert _ended(window)


def test_a_terminated_task_applies_a_layer_picked_during_it(window):
    window.dock._user_layer_pick = (time.perf_counter(), "dem")
    window.handler.handle_task_terminated("zones")
    assert _ended(window)
    window.combo.setLayer.assert_called_once_with(window.layers["dem"])


def test_a_terminated_task_applies_a_pick_still_shown(window):
    """Nothing put the source layer back after a terminated task: the combo box still shows the pick."""
    window.combo.currentLayer.return_value = window.layers["dem"]
    window.dock._user_layer_pick = (time.perf_counter(), "dem")
    window.handler.handle_task_terminated("zones")
    assert _ended(window)
    window.dock.current_layer_changed.assert_called_once_with(window.layers["dem"], manual_change=True)


def test_a_terminated_task_reconnects_the_layer_tree_link(window):
    window.dock.project_props = {"OPTIONS": {"LAYERS": {"LINK_LEGEND_LAYERS_AND_CURRENT_LAYER_FLAG": True}}}
    window.handler.handle_task_terminated("zones")
    assert window.dock.manageSignal.call_args_list[0].args == (["QGIS", "LAYER_TREE_VIEW"], 'connect')

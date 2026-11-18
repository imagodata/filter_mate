# -*- coding: utf-8 -*-
"""The second chooser of the current layer, at the top of EXPLORING away from FILTERING: what it follows."""
import importlib.util
import pathlib
import time

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "ui" / "widgets" / "layer_chooser_mirror.py"
_spec = importlib.util.spec_from_file_location("fm_layer_chooser_mirror_test", _PATH)
mirror = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mirror)


def test_it_shows_the_row_of_the_first_chooser():
    assert mirror.next_index(shown=0, source=2, list_open=False) == 2
    assert mirror.next_index(shown=3, source=-1, list_open=False) == -1  # no layer left: none shown


def test_nothing_to_do_when_it_already_shows_it():
    assert mirror.next_index(shown=2, source=2, list_open=False) is None


def test_the_row_under_the_pointer_does_not_move_while_the_list_is_open():
    assert mirror.next_index(shown=0, source=2, list_open=True) is None


def test_the_module_needs_no_qt_until_a_chooser_is_made():
    assert mirror._CLASS is None and mirror.FOLLOW_MS >= 200


# --- a layer chosen here is the user's choice (2026-11-18 audit) -------------------------------------------------


class _Layer:
    def __init__(self, layer_id):
        self._id = layer_id

    def id(self):
        return self._id


class _Source:
    """The chooser of FILTERING: rows of layers; ``setLayer`` moves it as QgsMapLayerComboBox does."""

    def __init__(self, layers, shown=0):
        self.layers, self.shown = layers, shown
        self.set_layers = []

    def currentIndex(self):  # noqa: N802 - Qt name
        return self.shown

    def currentLayer(self):  # noqa: N802 - Qt name
        return self.layers[self.shown] if self.shown >= 0 else None

    def layer(self, index):
        return self.layers[index]

    def setLayer(self, layer):  # noqa: N802 - Qt name
        self.set_layers.append(layer.id())
        self.shown = self.layers.index(layer)


class _Dock:
    def __init__(self, current=None, window=None, filtering=False):
        self.current_layer = current
        self.changes = []
        self._filtering_in_progress = filtering
        if window is not None:
            self._end_post_filter_window = window

    def current_layer_changed(self, layer, manual_change=False):
        self.changes.append((layer.id(), manual_change))
        self.current_layer = layer


def _two_layers():
    return [_Layer("a"), _Layer("b")]


def test_a_layer_chosen_here_is_noted_as_picked_by_the_user():
    """The post-filter window and the undo checks put the source layer back unless ``_user_layer_pick`` says the
    user picked another one since: the chooser of FILTERING notes it, this one did not."""
    layers = _two_layers()
    source, dock = _Source(layers), _Dock(current=layers[0])
    before = time.perf_counter()
    mirror.choose(source, dock, 1)
    picked_at, picked_id = dock._user_layer_pick
    assert picked_id == "b" and picked_at >= before
    assert source.set_layers == ["b"]


def test_the_window_after_a_filter_ends_with_the_pick():
    """Its handler reconnects the chooser and applies the pick: nothing else is done here."""
    layers = _two_layers()
    ended = []
    dock = _Dock(current=layers[0], window=lambda: ended.append(True))
    mirror.choose(_Source(layers), dock, 1)
    assert ended == [True] and dock.changes == []


def test_a_pick_the_dock_did_not_take_is_applied_as_a_manual_change():
    """The handler of the first chooser is disconnected (a task that adds layers, start-up refreshes): both
    choosers show the layer, the dock still has the other one and Filter would act on it."""
    layers = _two_layers()
    dock = _Dock(current=layers[0])  # source.setLayer moved the chooser, the dock did not follow
    mirror.choose(_Source(layers), dock, 1)
    assert dock.changes == [("b", True)]


def test_a_pick_the_dock_already_took_is_not_applied_twice():
    layers = _two_layers()
    dock = _Dock(current=layers[1])
    mirror.choose(_Source(layers), dock, 1)
    assert dock.changes == [] and dock._user_layer_pick[1] == "b"


def test_a_filter_that_runs_applies_the_pick_when_it_ends():
    layers = _two_layers()
    dock = _Dock(current=layers[0], filtering=True)
    mirror.choose(_Source(layers), dock, 1)
    assert dock.changes == [] and dock._user_layer_pick[1] == "b"


def test_choosing_the_layer_the_chooser_shows_but_the_dock_lacks_applies_it():
    """The follow timer made this chooser show it too: the pick is still the user's."""
    layers = _two_layers()
    source, dock = _Source(layers, shown=1), _Dock(current=layers[0])
    mirror.choose(source, dock, 1)
    assert source.set_layers == [] and dock.changes == [("b", True)]


def test_choosing_the_current_layer_again_notes_nothing():
    """No change: the window after a filter is not cut short, as for the first chooser."""
    layers = _two_layers()
    ended = []
    dock = _Dock(current=layers[0], window=lambda: ended.append(True))
    mirror.choose(_Source(layers), dock, 0)
    assert not hasattr(dock, "_user_layer_pick") and ended == [] and dock.changes == []


def test_without_a_dock_it_only_moves_the_first_chooser():
    layers = _two_layers()
    source = _Source(layers)
    mirror.choose(source, None, 1)
    assert source.set_layers == ["b"]

# -*- coding: utf-8 -*-
"""EXPLORING driven by the agent (adapters/public_api/exploring_drive.py), with a stand-in dock and rail.

The module is loaded for real under a synthetic package, as test_panel_options.py does; the rail is a stand-in that
keeps the state of its buttons and moves them as the real one does (one tool on the map at a time).
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_exploring_drive_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                       (".core.domain", _ROOT / "core" / "domain"), (".adapters", _ROOT / "adapters"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.public_api.exploring_drive")


drive = _load()


class _Layer:
    def __init__(self, layer_id, name):
        self._id, self._name = layer_id, name

    def id(self):
        return self._id

    def name(self):
        return self._name


class _Rail:
    """Vector rail: sync, follow, link are modes; zone a tool for the map; zoom and identify run once."""

    def __init__(self, hidden=()):
        self.on = {"sync": False, "follow": False, "zone": False, "link": False}
        self.hidden = set(hidden)
        self.clicks = []

    def rail_kind(self):
        return "vector"

    def hidden_tools(self, _kind=None):
        return frozenset(self.hidden)

    def tool_states(self):
        states = {name: (drive.HIDDEN if name in self.hidden else (drive.ON if on else drive.OFF), "")
                  for name, on in self.on.items()}
        states.update({"zoom": (drive.PRESS, ""), "identify": (drive.PRESS, "")})
        return states

    def click_tool(self, key):
        self.clicks.append(key)
        if key in self.on:
            self.on[key] = not self.on[key]
        return True


def _dock(rail, layers, shown):
    dock = SimpleNamespace(widgets_initialized=True, PROJECT_LAYERS={layer.id(): {} for layer in layers},
                           current_layer=shown, isVisible=lambda: True)
    dock._controller_integration = SimpleNamespace(coverage_controller=SimpleNamespace(rail=lambda: rail))

    def changed(layer, manual_change=False):
        dock.current_layer = layer
    dock.current_layer_changed = changed
    return dock


@pytest.fixture
def setup(monkeypatch):
    roads, towns = _Layer("roads_1", "roads"), _Layer("towns_2", "towns")
    rail = _Rail()
    dock = _dock(rail, [roads, towns], roads)
    project = SimpleNamespace(mapLayer=lambda layer_id: {"roads_1": roads, "towns_2": towns}.get(layer_id),
                              mapLayers=lambda: {"roads_1": roads, "towns_2": towns})
    monkeypatch.setattr(drive, "kind_of", lambda layer: "vector")
    monkeypatch.setattr(drive, "_facts", lambda _project: [
        SimpleNamespace(layer_id="roads_1", name="roads", vector=True),
        SimpleNamespace(layer_id="towns_2", name="towns", vector=True)])
    monkeypatch.setattr(drive, "_found", lambda reference, facts: next(
        fact for fact in facts if reference in (fact.layer_id, fact.name)))
    monkeypatch.setattr(drive, "_protected", lambda layer: False)
    monkeypatch.setattr(drive, "_busy", lambda dock: "")
    monkeypatch.setattr(drive, "in_view", lambda dock: True)
    return SimpleNamespace(dock=dock, rail=rail, project=project, roads=roads, towns=towns)


def _mark_and_drive(setup, **arguments):
    mark = drive.journal_mark()
    answer = drive.set_exploring(setup.dock, project=setup.project, **arguments)
    return mark, answer


def test_a_button_turned_on_then_off_is_no_change_of_the_turn(setup):
    """Review 1: an undo must not click a button the turn left as it found it; the user may have turned it on since."""
    mark, _ = _mark_and_drive(setup, tools={"follow": True})
    _mark_and_drive(setup, tools={"follow": False})
    entries = drive.journal_since(mark)
    assert [entry["key"] for entry in entries] == ["follow", "follow"]
    assert drive.net(entries) == []
    setup.rail.on["follow"] = True  # the user turns it on after the turn
    assert drive.replay(setup.dock, entries, undo=True, project=setup.project) == ""
    assert setup.rail.on["follow"] is True


def test_a_layer_shown_then_given_back_is_no_change_of_the_turn(setup):
    mark, _ = _mark_and_drive(setup, layer="towns")
    _mark_and_drive(setup, layer="roads")
    entries = drive.journal_since(mark)
    assert drive.net(entries) == []
    setup.dock.current_layer = setup.towns  # the user shows towns after the turn
    drive.replay(setup.dock, entries, undo=True, project=setup.project)
    assert setup.dock.current_layer is setup.towns


def test_undo_takes_back_the_layer_and_the_button(setup):
    mark, answer = _mark_and_drive(setup, layer="towns", tools={"follow": True})
    assert answer["changed"] == ["layer", "follow"] and setup.dock.current_layer is setup.towns
    entries = drive.journal_since(mark)
    assert drive.replay(setup.dock, entries, undo=True, project=setup.project) == "done"
    assert setup.dock.current_layer is setup.roads and setup.rail.on["follow"] is False


def test_what_the_user_changed_since_is_left(setup):
    mark, _ = _mark_and_drive(setup, tools={"zone": True})
    setup.rail.on["zone"] = False  # the user puts it down; the undo has nothing to take back
    assert drive.replay(setup.dock, drive.journal_since(mark), undo=True, project=setup.project) == ""


def test_a_button_the_rail_puts_down_for_another_is_noted(setup):
    """Review 6: one tool on the map at a time; the one the rail put down comes back with an undo."""
    setup.rail.on["zone"] = True

    def click(key):
        setup.rail.clicks.append(key)
        if key == "follow":
            setup.rail.on.update(follow=not setup.rail.on["follow"], zone=False)
        return True
    setup.rail.click_tool = click
    mark, answer = _mark_and_drive(setup, tools={"follow": True})
    entries = drive.net(drive.journal_since(mark))
    assert {entry["key"] for entry in entries} == {"follow", "zone"}


def test_a_layer_the_panel_does_not_list_is_refused_before_anything(setup):
    """Review 4: the selector would fall on none, the dock on another layer."""
    del setup.dock.PROJECT_LAYERS["towns_2"]
    mark = drive.journal_mark()
    with pytest.raises(ValueError, match="does not list towns"):
        drive.set_exploring(setup.dock, layer="towns", project=setup.project)
    assert setup.dock.current_layer is setup.roads and drive.journal_since(mark) == []


def test_a_busy_panel_is_refused_before_anything(setup, monkeypatch):
    """Review 5: a change of layer the panel defers would come later, unnoted."""
    monkeypatch.setattr(drive, "_busy", lambda dock: "a filter runs")
    with pytest.raises(ValueError, match="busy: a filter runs"):
        drive.set_exploring(setup.dock, layer="towns", project=setup.project)
    assert setup.dock.current_layer is setup.roads


def test_a_protected_layer_shows_but_its_tools_are_not_driven(setup, monkeypatch):
    """Reviews of #600 (2) and lot 2 (13): follow and link write options of the layer, a tool changes its group."""
    monkeypatch.setattr(drive, "_protected", lambda layer: True)
    with pytest.raises(ValueError, match="protected towns"):
        drive.set_exploring(setup.dock, layer="towns", tools={"follow": True}, project=setup.project)
    with pytest.raises(ValueError, match="protected towns"):  # a tool may change its group or preview too
        drive.set_exploring(setup.dock, layer="towns", tools={"zone": True}, project=setup.project)
    answer = drive.set_exploring(setup.dock, layer="towns", press=["zoom"], project=setup.project)
    assert answer["changed"] == ["layer"] and answer["pressed"] == ["zoom"]


def test_the_net_change_keeps_the_layers_in_order_and_one_change_per_button():
    """What was done on a layer the turn went through stays between the changes of layer that framed it."""
    zone = {"kind": "tool", "layer": "b", "key": "zone"}
    entries = [{"kind": "layer", "was": "a", "now": "b"}, dict(zone, was=False, now=True),
               dict(zone, was=True, now=False), dict(zone, was=False, now=True),
               {"kind": "layer", "was": "b", "now": "c"}]
    assert drive.net(entries) == [entries[0], dict(zone, was=False, now=True), entries[4]]


def test_a_part_of_the_journal_is_read_between_two_marks():
    start = drive.journal_mark()
    drive._note({"kind": "layer", "was": "a", "now": "b"})
    end = drive.journal_mark()
    drive._note({"kind": "layer", "was": "b", "now": "c"})  # another client, after the call
    assert drive.journal_since(start, end) == [{"kind": "layer", "was": "a", "now": "b"}]


def test_what_was_done_on_a_layer_the_turn_went_through_is_undone_on_it(setup):
    """Review of lot 2, 1: the turn shows towns, turns sync on there, then shows roads... the undo turns sync off on
    towns, where it was turned on."""
    parks = _Layer("parks_3", "parks")
    setup.dock.PROJECT_LAYERS["parks_3"] = {}
    layers = {"roads_1": setup.roads, "towns_2": setup.towns, "parks_3": parks}
    setup.project.mapLayer = layers.get
    facts = [SimpleNamespace(layer_id=key, name=layer.name(), vector=True) for key, layer in layers.items()]
    drive._facts = lambda _project: facts
    rails = {key: _Rail() for key in layers}
    setup.dock._controller_integration.coverage_controller.rail = lambda: rails[setup.dock.current_layer.id()]
    mark, _ = _mark_and_drive(setup, layer="towns", tools={"sync": True})
    _mark_and_drive(setup, layer="parks")
    entries = drive.journal_since(mark)
    assert drive.replay(setup.dock, entries, undo=True, project=setup.project) == "done"
    assert setup.dock.current_layer is setup.roads and rails["towns_2"].on["sync"] is False


def test_tools_that_are_not_an_object_are_refused(setup):
    with pytest.raises(ValueError, match="tools: an object"):
        drive.set_exploring(setup.dock, tools=["follow"], project=setup.project)


def test_a_bound_the_panel_opened_once_the_histogram_came_is_as_the_call_left_it():
    left = {"mode": "range", "minimum": -5.0, "maximum": 300.0}
    assert drive._as_left(dict(left, minimum=None), left, "raster")  # below the data: every pixel on that side
    assert not drive._as_left(dict(left, minimum=12.0), left, "raster")  # moved by the user
    assert not drive._as_left(dict(left, mode="pipette", minimum=None), left, "raster")
    assert not drive._as_left({"classes": None}, {"classes": [2]}, "point_cloud")


def test_a_range_of_a_point_cloud_kept_within_its_values_is_said():
    asked = [{"attribute": "Z", "minimum": -100.0, "maximum": 30.0}]
    assert drive._ranges_moved(asked, {"ranges": [{"low": 2.0, "high": 30.0}]})
    assert not drive._ranges_moved(asked, {"ranges": [{"low": -100.0, "high": 30.0}]})
    assert not drive._ranges_moved([{"attribute": "Z", "minimum": 5.0, "maximum": None}],
                                   {"ranges": [{"low": 5.0, "high": None}]})

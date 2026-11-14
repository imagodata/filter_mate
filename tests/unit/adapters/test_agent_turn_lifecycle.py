# -*- coding: utf-8 -*-
"""
The undo point of a turn of the agent when its project closes, and the count widget on a web service.

``turn_checkpoint`` and ``agent_widgets`` are loaded by path under a private package: the pure domain is the real
one (``core``), QGIS and the other adapters are stand-ins.
"""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_agent_turn_lifecycle_test"


class Layer:
    def __init__(self, layer_id, subset=""):
        self._id, self.subset = layer_id, subset

    def id(self):
        return self._id

    def name(self):
        return self._id

    def isValid(self):
        return True


class Project:
    def __init__(self, layers):
        self.layers = {layer.id(): layer for layer in layers}

    def mapLayers(self):
        return dict(self.layers)

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)


class Effects:
    """EffectsRecorder stand-in: a project note the turn kept, compared at its end (the recorder of a step,
    ``settings=False``, saw nothing)."""

    def __init__(self, settings=True):
        self._turn = settings

    def before_call(self, call, step=0):
        pass

    def finish(self):
        return (("notes", "", (), ("a note",)),) if self._turn else ()


def _module(monkeypatch, name, **attrs):
    module = types.ModuleType(f"{_PKG}{name}")
    module.__path__ = []
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    return module


def _load(monkeypatch, name, rel):
    spec = importlib.util.spec_from_file_location(f"{_PKG}.{name}", _ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def packages(monkeypatch):
    _module(monkeypatch, "")
    core = types.ModuleType(f"{_PKG}.core")
    core.__path__ = [str(_ROOT / "core")]
    monkeypatch.setitem(sys.modules, core.__name__, core)
    for name in (".adapters", ".adapters.agent", ".adapters.public_api", ".adapters.qgis",
                 ".adapters.qgis.coverage_layers"):
        _module(monkeypatch, name)


@pytest.fixture
def checkpoint_module(monkeypatch, packages):
    filter_state = importlib.import_module(f"{_PKG}.core.domain.filter_state")
    layer_kind = importlib.import_module(f"{_PKG}.core.domain.layer_kind")
    service = types.SimpleNamespace(history=filter_state.CrossOperationHistory())
    _module(monkeypatch, ".adapters.public_api.operations", _api_service=lambda: service, busy_reason=lambda: "",
            layer_kind=lambda layer: layer_kind.LayerKind.VECTOR)
    _module(monkeypatch, ".adapters.qgis.coverage_layers.snapshots",
            take_snapshot=lambda layer, kind: filter_state.LayerSnapshot(layer.id(), kind.value, subset=layer.subset))
    _module(monkeypatch, ".adapters.agent.turn_effects", EffectsRecorder=Effects, apply_effects=MagicMock())
    holder = types.SimpleNamespace(project=None)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject",
                        types.SimpleNamespace(instance=lambda: holder.project), raising=False)
    module = _load(monkeypatch, "adapters.agent.turn_checkpoint", "adapters/agent/turn_checkpoint.py")
    module._test_service, module._test_holder = service, holder
    return module


def test_a_turn_discarded_with_its_project_is_never_recorded(checkpoint_module):
    """2026-11-12: committed after the project changed, the turn compared the closed project with the next one."""
    holder, history = checkpoint_module._test_holder, checkpoint_module._test_service.history
    old = Layer("roads")
    holder.project = Project([old])
    checkpoint = checkpoint_module.TurnCheckpoint()
    checkpoint.begin(types.SimpleNamespace(name="add_project_note", arguments={}))
    old.subset = "x > 1"
    checkpoint.discard()  # the project is cleared while the request runs
    holder.project = Project([Layer("rivers")])  # the next project
    assert checkpoint.commit() == ()  # the end of the cancelled request
    assert not history.can_undo(checkpoint_module.HISTORY_KEY)


def test_a_turn_kept_open_is_recorded(checkpoint_module):
    holder, history = checkpoint_module._test_holder, checkpoint_module._test_service.history
    layer = Layer("roads")
    holder.project = Project([layer])
    checkpoint = checkpoint_module.TurnCheckpoint()
    checkpoint.begin(types.SimpleNamespace(name="apply_filter", arguments={}))
    layer.subset = "x > 1"
    assert list(checkpoint.commit()) == ["roads"]
    assert history.can_undo(checkpoint_module.HISTORY_KEY)


def test_a_turn_keeps_when_it_and_its_steps_began(monkeypatch, checkpoint_module):
    """The history of the project places an operation done during a turn among its steps (history_timeline)."""
    holder, history = checkpoint_module._test_holder, checkpoint_module._test_service.history
    roads, towns = Layer("roads"), Layer("towns")
    holder.project = Project([roads, towns])
    clock = iter([100.0, 140.0, 160.0, 300.0])
    monkeypatch.setattr(checkpoint_module.time, "time", lambda: next(clock))
    checkpoint = checkpoint_module.TurnCheckpoint()
    for layer, subset in ((roads, "a"), (None, None), (towns, "b")):  # the second call changes nothing
        checkpoint.begin(types.SimpleNamespace(name="apply_filter", arguments={}))
        if layer is not None:
            layer.subset = subset
    checkpoint.commit()
    turn = history.peek_undo(checkpoint_module.HISTORY_KEY)
    assert turn.started == 100.0 and turn.step_times == (100.0, 160.0)  # the steps recorded: those that changed
    assert [label for label, _states in turn.steps] == ["apply_filter", "apply_filter"]
    # The next turn begins afresh.
    clock = iter([400.0])
    checkpoint.begin(types.SimpleNamespace(name="apply_filter", arguments={}))
    roads.subset = "c"
    checkpoint.commit()
    single = history.peek_undo(checkpoint_module.HISTORY_KEY)
    assert single.started == 400.0 and single.steps == () and single.step_times == ()


def test_each_call_finds_its_step_and_the_commit_says_where_it_was_recorded(checkpoint_module):
    """The cards of the thread compare their own step: by the call object (two calls may share an id), only the steps
    recorded (one that changed nothing is not), by their rank among them; a turn of one step keeps no list."""
    holder, history = checkpoint_module._test_holder, checkpoint_module._test_service.history
    roads, towns = Layer("roads"), Layer("towns")
    holder.project = Project([roads, towns])
    opened = []
    checkpoint = checkpoint_module.TurnCheckpoint()
    checkpoint.on_open = lambda: opened.append(roads.subset)
    calls = [types.SimpleNamespace(name="apply_filter", arguments={}, call_id="same") for _ in range(3)]
    for index, (call, (layer, subset)) in enumerate(zip(calls, ((roads, "a"), (None, None), (towns, "b")))):
        checkpoint.begin(call)  # the second call changes nothing
        assert checkpoint.step_of(call) == index  # equal calls (SimpleNamespace compares fields): told apart
        if layer is not None:
            layer.subset = subset
    assert opened == [""]  # once, before the first change
    assert checkpoint.step_of(types.SimpleNamespace(name="apply_filter", call_id="same")) is None
    checkpoint.commit()
    turn = history.peek_undo(checkpoint_module.HISTORY_KEY)
    assert checkpoint.recorded == (turn.op_id, {0: 0, 2: 1}) and len(turn.steps) == 2
    assert checkpoint.step_of(calls[0]) is None  # the turn is over
    assert checkpoint_module.TurnCheckpoint.applied()[-1] is turn
    single = types.SimpleNamespace(name="apply_filter", arguments={})
    checkpoint.begin(single)
    roads.subset = "c"
    checkpoint.commit()
    assert checkpoint.recorded == (history.peek_undo(checkpoint_module.HISTORY_KEY).op_id, {0: None})
    assert opened == ["", "a"]  # a new turn opens again
    checkpoint.begin(types.SimpleNamespace(name="apply_filter", arguments={}))
    checkpoint.commit()  # no layer changed, a note kept (the stand-in of the effects): no step to compare
    assert checkpoint.recorded[1] == {}
    checkpoint.commit()  # no turn open: nothing recorded
    assert checkpoint.recorded is None


def test_a_failure_when_a_turn_opens_never_stops_its_change(checkpoint_module):
    holder = checkpoint_module._test_holder
    layer = Layer("roads")
    holder.project = Project([layer])
    checkpoint = checkpoint_module.TurnCheckpoint()

    def broken():
        raise RuntimeError("the map cannot be read")
    checkpoint.on_open = broken
    checkpoint.begin(types.SimpleNamespace(name="apply_filter", arguments={}))
    layer.subset = "x"
    assert list(checkpoint.commit()) == ["roads"]


def test_settings_effects_are_placed_among_the_recorded_steps(checkpoint_module):
    """The call of a settings effect becomes the number of recorded steps up to it (calls that changed a layer)."""
    effects = (("notes", "", (), ("n",)), ("settings", "", "{}", "{}", 2), ("settings", "", "{}", "{}", 5))
    placed = checkpoint_module.TurnCheckpoint._settings_at_steps(effects, [0, 3, 4])
    assert placed[0] == effects[0]
    assert placed[1][4] == 1 and placed[2][4] == 3  # one recorded step up to call 2, three up to call 5


def test_back_to_a_step_restores_the_settings_changed_from_it(monkeypatch, checkpoint_module):
    """2026-11-12: undo_to_step restored the layers only; the settings changed at or after the step came back too."""
    import json
    now = {"APP.A": 2, "APP.B": 20}
    _module(monkeypatch, ".adapters.agent.plugin_settings",
            current_values=lambda paths: {path: now[path] for path in paths if path in now})
    effects = (("settings", "", json.dumps({"APP.A": 1}), json.dumps({"APP.A": 2}), 1),  # before recorded step 1
               ("settings", "", json.dumps({"APP.B": 10}), json.dumps({"APP.B": 20}), 2))  # after it
    back = checkpoint_module.TurnCheckpoint._settings_back_to(effects, 1)
    assert len(back) == 1 and json.loads(back[0][2]) == {"APP.B": 20} and json.loads(back[0][3]) == {"APP.B": 10}
    assert checkpoint_module.TurnCheckpoint._settings_back_to(effects, 2) == ()
    both = checkpoint_module.TurnCheckpoint._settings_back_to(effects, 0)
    assert json.loads(both[0][3]) == {"APP.A": 1, "APP.B": 10}
    now["APP.B"] = 10  # already back: nothing to do
    assert json.loads(checkpoint_module.TurnCheckpoint._settings_back_to(effects, 0)[0][3]) == {"APP.A": 1}
    now["APP.A"] = 5  # the user changed it since the turn: theirs, left as it is
    assert checkpoint_module.TurnCheckpoint._settings_back_to(effects, 0) == ()


def test_a_count_widget_does_not_count_a_web_service(monkeypatch, packages):
    """2026-11-12: featureCount() of a WFS layer can be a request to its server, at each refresh of the widgets."""
    _module(monkeypatch, ".adapters.qgis.source_capability_probe",
            feature_count_or_none=lambda layer: None if layer.remote else layer.featureCount())
    for name in ("qgis.PyQt.QtCore",):
        monkeypatch.setitem(sys.modules, name, MagicMock())
    module = _load(monkeypatch, "adapters.agent.agent_widgets", "adapters/agent/agent_widgets.py")
    wfs = MagicMock(remote=True)
    wfs.featureCount.side_effect = AssertionError("a request to the server")
    local = MagicMock(remote=False)
    local.featureCount.return_value = 7
    layers = {"wfs": wfs, "local": local}
    monkeypatch.setattr(module, "widget_layer", lambda widget: layers[widget["layer_id"]])
    assert module.stat_value({"layer_id": "wfs", "aggregate": "count"}) is None
    assert module.stat_value({"layer_id": "local", "aggregate": "count"}) == 7.0


def test_back_to_a_step_undoes_the_later_steps_and_their_settings_in_one_operation(monkeypatch, checkpoint_module):
    """What the later steps did beside the filters and the settings they changed go back together, in an operation
    whose effects run the other way: undone, it applies them again."""
    import json
    filter_state = importlib.import_module(f"{_PKG}.core.domain.filter_state")
    holder, history = checkpoint_module._test_holder, checkpoint_module._test_service.history
    holder.project = Project([])
    _module(monkeypatch, ".adapters.agent.plugin_settings", current_values=lambda paths: {"APP.B": 20})
    style = ("style", "roads", "<before/>", "<after/>", "roads")
    history.push(filter_state.CrossOperation(
        checkpoint_module.HISTORY_KEY, (), steps=(("filter", ()), ("style", ())), step_effects=((), (style,)),
        effects=(style, ("settings", "", json.dumps({"APP.B": 10}), json.dumps({"APP.B": 20}), 2))))
    calls = []

    def apply_effects(effects, undo, keep=frozenset(), presence=None):
        calls.append((effects, undo, presence))
        return (["done"] if presence is False else []), []
    monkeypatch.setattr(checkpoint_module, "apply_effects", apply_effects)
    done, _left = checkpoint_module.TurnCheckpoint().undo_to_step(1)
    effects = calls[0][0]
    settings = [effect for effect in effects if effect[0] == "settings"]
    assert effects[0] == style and len(settings) == 1
    # Undone (undo=True), it goes to what the setting held before the step.
    assert json.loads(settings[0][2]) == {"APP.B": 10} and json.loads(settings[0][3]) == {"APP.B": 20}
    assert [(undo, presence) for _effects, undo, presence in calls] == [(True, True), (True, False)]
    pushed = history.undo_stack(checkpoint_module.HISTORY_KEY)[-1]
    assert done == ["done"] and pushed.effects_reversed and pushed.effects == effects

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

    def removeMapLayer(self, layer_id):
        self.layers.pop(layer_id, None)


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
    _module(monkeypatch, ".adapters.agent.turn_effects", EffectsRecorder=Effects, apply_effects=MagicMock(),
            # as adapters/agent/turn_effects.takes_away (the module itself needs QGIS)
            takes_away=lambda effect, undo: effect[0] in ("added", "removed") and (effect[0] == "removed") != undo)
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


def test_a_recorder_of_the_turn_that_fails_refuses_the_call_but_not_the_one_of_the_step(monkeypatch, checkpoint_module):
    """A valid call whose capture fails is refused (begin raises): run, it would leave the undo silently incomplete.
    The recorder of a step only serves "undo back to here": its failure keeps nothing from being made."""
    class Failing(Effects):
        def before_call(self, call, step=0):
            raise ValueError("not serialisable")

    class FailingStep(Effects):
        def before_call(self, call, step=0):
            if not self._turn:
                raise ValueError("not serialisable")

    holder = checkpoint_module._test_holder
    holder.project = Project([Layer("roads")])
    call = types.SimpleNamespace(name="set_layer_options", arguments={"layers": []})
    monkeypatch.setattr(checkpoint_module, "EffectsRecorder", Failing)
    with pytest.raises(ValueError):
        checkpoint_module.TurnCheckpoint().begin(call)
    monkeypatch.setattr(checkpoint_module, "EffectsRecorder", FailingStep)
    checkpoint_module.TurnCheckpoint().begin(call)  # does not raise


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
    _module(monkeypatch, ".adapters.qgis.source_capability_probe", counts_cheaply=lambda layer: not layer.remote)
    _module(monkeypatch, ".adapters.qgis.feature_count", exact_feature_count=lambda layer: layer.featureCount())
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

    def apply_effects(effects, undo, keep=frozenset(), presence=None, edits=None, close=frozenset(), coming=None):
        calls.append((effects, undo, presence, coming, edits))
        return (["done"] if presence is False and edits is False else []), []
    monkeypatch.setattr(checkpoint_module, "apply_effects", apply_effects)
    done, _left = checkpoint_module.TurnCheckpoint().undo_to_step(1)
    effects = calls[0][0]
    settings = [effect for effect in effects if effect[0] == "settings"]
    assert effects[0] == style and len(settings) == 1
    # Undone (undo=True), it goes to what the setting held before the step.
    assert json.loads(settings[0][2]) == {"APP.B": 10} and json.loads(settings[0][3]) == {"APP.B": 20}
    # The layers that come back, then the edits (before the filters), then (the filters restored) the layers that go
    # away, then the rest.
    assert [call[1:] for call in calls] == [(True, True, True, None), (True, False, None, True),
                                             (True, True, False, None), (True, False, None, False)]
    pushed = history.undo_stack(checkpoint_module.HISTORY_KEY)[-1]
    assert done == ["done"] and pushed.effects_reversed and pushed.effects == effects


# --- 2026-11-13 (review of 5.1.0): an Undo a layer refuses leaves the layers the turn added as they are -----------

ADDED = ("added", "made", "<definition/>", ((), 0), "made")
REMOVED = ("removed", "gone", "<definition/>", ((), 0), "gone")


def _turn(checkpoint_module, layers, changes, effects, refuse=()):
    """A turn in the history, over a project of ``layers``; the layers of ``refuse`` keep their filter (QGIS refuses
    the subset of a layer being edited). Returns ``(project, calls of apply_effects, layers asked to restore, the
    stand-in of apply_effects)``; the stand-in keeps in ``closed`` the layers its pass of the edits may close."""
    filter_state = importlib.import_module(f"{_PKG}.core.domain.filter_state")
    holder, service = checkpoint_module._test_holder, checkpoint_module._test_service
    project = holder.project = Project(layers)
    service.history.push(filter_state.CrossOperation(
        checkpoint_module.HISTORY_KEY,
        tuple((filter_state.LayerSnapshot(layer_id, "vector", subset=before),
               filter_state.LayerSnapshot(layer_id, "vector", subset=after)) for layer_id, before, after in changes),
        effects=effects))
    calls, asked = [], []

    def restore(pairs, use_before, project=None):
        restored = []
        for before, after in pairs:
            wanted = before if use_before else after
            asked.append(wanted.layer_id)
            layer = project.mapLayer(wanted.layer_id)
            if layer is not None:
                restored.append(wanted.layer_id)
                if wanted.layer_id not in refuse:
                    layer.subset = wanted.subset
        return restored

    def apply_effects(effects, undo, keep=frozenset(), presence=None, edits=None, close=frozenset(), coming=None):
        calls.append((undo, presence, coming, edits))
        if edits:
            apply_effects.closed.append(close)
        done = []
        for effect in effects:
            if effect[0] not in ("added", "removed") or not presence:
                continue
            away = (effect[0] == "removed") != undo
            if away and coming is not True and effect[1] in project.layers:
                project.removeMapLayer(effect[1])
                done.append(effect[1])
            elif not away and coming is not False and effect[1] not in project.layers:
                project.layers[effect[1]] = Layer(effect[1])
                done.append(effect[1])
        return done, []
    apply_effects.closed = []
    service._restore, service.last_skipped = restore, []
    return project, calls, asked, apply_effects


def test_an_undo_a_layer_refuses_never_removes_the_layers_the_turn_added(monkeypatch, checkpoint_module):
    """The layers going away were removed before the filters, and a refusal loaded them again from their definition:
    a memory layer came back empty, a file layer without its style nor its edits."""
    edited, made = Layer("edited", subset="after"), Layer("made")
    project, calls, _asked, apply_effects = _turn(
        checkpoint_module, [edited, made], [("edited", "before", "after")], (ADDED, REMOVED), refuse={"edited"})
    monkeypatch.setattr(checkpoint_module, "apply_effects", apply_effects)
    names, left = checkpoint_module.TurnCheckpoint().undo()
    # The layer the turn removed came back, the edits went back and forth; nothing went away, nothing else moved.
    assert calls == [(True, True, True, None), (True, False, None, True), (False, False, None, True)]
    assert project.layers == {"edited": edited, "made": made}  # the very layer, never removed; what came back is gone
    assert left == ["edited"] and names == []
    assert checkpoint_module._test_service.history.can_undo(checkpoint_module.HISTORY_KEY)  # it can be tried again


def test_a_refusal_never_takes_back_a_layer_that_came_in_meanwhile(monkeypatch, checkpoint_module):
    """Review of 5b63e895: the refusal removed every layer not there before the move. A layer added while the filters
    were put back (a Processing output finished while QGIS waited on a provider) went with the turn's."""
    edited, made = Layer("edited", subset="after"), Layer("made")
    project, _calls, _asked, apply_effects = _turn(
        checkpoint_module, [edited, made], [("edited", "before", "after")], (ADDED, REMOVED), refuse={"edited"})
    monkeypatch.setattr(checkpoint_module, "apply_effects", apply_effects)
    service = checkpoint_module._test_service
    restore = service._restore

    def restore_while_a_task_ends(pairs, use_before, project=None):
        project.layers["users_output"] = Layer("users_output")
        return restore(pairs, use_before, project=project)
    service._restore = restore_while_a_task_ends
    _names, left = checkpoint_module.TurnCheckpoint().undo()
    assert left == ["edited"]
    assert set(project.layers) == {"edited", "made", "users_output"}  # what came back is gone, the user's output stays


def test_an_undo_removes_the_layers_the_turn_added_once_the_filters_are_back(monkeypatch, checkpoint_module):
    """And the filter of a layer that leaves is not touched: being edited, it would have refused for nothing."""
    target, made = Layer("target", subset="after"), Layer("made", subset="its filter")
    project, calls, asked, apply_effects = _turn(
        checkpoint_module, [target, made], [("target", "before", "after"), ("made", "", "its filter")],
        (ADDED, REMOVED), refuse={"made"})
    monkeypatch.setattr(checkpoint_module, "apply_effects", apply_effects)
    names, left = checkpoint_module.TurnCheckpoint().undo()
    assert calls == [(True, True, True, None), (True, False, None, True), (True, True, False, None),
                     (True, False, None, False)]
    # A layer that leaves keeps the editing mode the turn put it in: its edits come back if a filter refuses.
    assert apply_effects.closed == [frozenset({"target"})]
    assert asked == ["target"] and target.subset == "before"
    assert set(project.layers) == {"target", "gone"} and left == []
    assert set(names) == {"target", "gone", "made"}


def test_a_redo_a_layer_refuses_never_removes_the_layers_the_turn_removed(monkeypatch, checkpoint_module):
    edited, made = Layer("edited", subset="after"), Layer("made")
    project, calls, _asked, apply_effects = _turn(
        checkpoint_module, [edited, made], [("edited", "before", "after")], (ADDED, REMOVED))
    monkeypatch.setattr(checkpoint_module, "apply_effects", apply_effects)
    checkpoint = checkpoint_module.TurnCheckpoint()
    checkpoint.undo()
    back = project.layers["gone"]
    assert set(project.layers) == {"edited", "gone"} and edited.subset == "before"
    del calls[:]
    checkpoint_module._test_service._restore = lambda pairs, use_before, project=None: ["edited"]  # asked, unchanged
    names, left = checkpoint.redo()
    assert calls == [(False, True, True, None)]  # applied again, the edits go with the rest: nothing to put back
    assert project.layers == {"edited": edited, "gone": back} and left == ["edited"]  # "made" came back, then left
    assert checkpoint_module._test_service.history.can_redo(checkpoint_module.HISTORY_KEY)


def test_back_to_a_step_a_layer_refuses_never_removes_the_layers_of_the_later_steps(monkeypatch, checkpoint_module):
    filter_state = importlib.import_module(f"{_PKG}.core.domain.filter_state")
    holder, service = checkpoint_module._test_holder, checkpoint_module._test_service
    edited, made = Layer("edited", subset="after"), Layer("made")
    project = holder.project = Project([edited, made])
    _module(monkeypatch, ".adapters.agent.plugin_settings", current_values=lambda paths: {})
    before = filter_state.LayerSnapshot("edited", "vector", subset="before")
    service.history.push(filter_state.CrossOperation(
        checkpoint_module.HISTORY_KEY, ((before, filter_state.LayerSnapshot("edited", "vector", subset="after")),),
        steps=(("filter", (before,)), ("add", ())), step_effects=((), (ADDED,)), effects=(ADDED,)))
    service._restore, service.last_skipped = (lambda pairs, use_before, project=None: ["edited"]), []
    calls = []

    def apply_effects(effects, undo, keep=frozenset(), presence=None, edits=None, close=frozenset(), coming=None):
        calls.append((undo, presence, coming, edits))
        if presence and coming is not True:
            project.removeMapLayer("made")
        return [], []
    monkeypatch.setattr(checkpoint_module, "apply_effects", apply_effects)
    depth = len(service.history.undo_stack(checkpoint_module.HISTORY_KEY))
    names, left = checkpoint_module.TurnCheckpoint().undo_to_step(0)
    assert calls == [(True, True, True, None), (True, False, None, True), (False, False, None, True)]
    assert project.layers == {"edited": edited, "made": made}
    assert left == ["edited"] and len(service.history.undo_stack(checkpoint_module.HISTORY_KEY)) == depth

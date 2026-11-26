# -*- coding: utf-8 -*-
"""The local copy as the user starts it: what a layer offers, the question, the end of the copy, the way back.

Loaded by path under a private synthetic package: the copy itself (adapters/qgis/stream_copy.py) is a stand-in here,
its real run is checked in QGIS by tests/qgis_headless/check_stream_copy.py.
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_stream_copy_actions_test"


class FakeCopy(types.ModuleType):
    """``adapters.qgis.stream_copy`` with the layers ``copies`` / ``streams`` and one task kept."""

    def __init__(self):
        super().__init__(_PKG + ".adapters.qgis.stream_copy")
        self.copies, self.streams, self.tasks, self.switched, self.back = set(), set(), [], [], []
        self.restored, self.discarded = [], []
        self.refusal, self.switch_error = "", None

    def is_local_copy(self, layer):
        return layer.id() in self.copies

    def can_copy(self, layer):
        return layer.id() in self.streams

    rules = SimpleNamespace(PROPERTY="filtermate/local_copy")
    data_store = SimpleNamespace(PERSISTENT_PROPERTY="filtermate/agent/persistent_data")

    def record_of(self, layer):
        if layer.id() not in self.copies:
            return None
        record = SimpleNamespace(notes=(), path=f"/w/{layer.id()}.tif")
        record.replaced = lambda **changes: SimpleNamespace(to_json=lambda: "{}")
        return record

    def copy_text(self, record):
        return "Local copy of 2026-11-22 15:00: still image"

    def plan_copy(self, layer, *args):
        return SimpleNamespace(refusal=self.refusal, summary=lambda: "1000 x 800 pixels", layer_id=layer.id(),
                               layer_name=layer.name(), folder="/w/etude_filtermate_local", provider="wms",
                               source="url=https://tiles.example.org/wms")

    @staticmethod
    def same_service(current_source, current_provider, planned_source, planned_provider):
        """The real one compares the endpoint; here a non-text source (a MagicMock layer) carries none, and the
        provider decides, as there (audit of 2026-11-24)."""
        if (current_provider or '').lower() != (planned_provider or '').lower():
            return False
        current = current_source if isinstance(current_source, str) else ''
        planned = planned_source if isinstance(planned_source, str) else ''
        return not current or not planned or current == planned

    def recopy_plan(self, layer):
        self.copies.discard(layer.id())
        self.streams.add(layer.id())
        previous = SimpleNamespace(notes=(), path="/w/old.tif")
        plan = self.plan_copy(layer)
        if plan.refusal:
            self.back_to(layer, previous)
        return plan, previous

    def back_to(self, layer, record):
        self.restored.append(layer.id())
        self.copies.add(layer.id())

    def discard(self, record):
        if record is not None:
            self.discarded.append(record.path)

    def StreamCopyTask(self, plan, layer, callback):
        task = SimpleNamespace(plan=plan, callback=callback, result=SimpleNamespace(record=None, error=""),
                               cancel=MagicMock())
        self.tasks.append(task)
        return task

    def switch_to_copy(self, layer, record):
        if self.switch_error:
            raise RuntimeError(self.switch_error)
        self.switched.append(layer.id())
        self.copies.add(layer.id())
        return list(record.notes)

    def switch_to_stream(self, layer, keep_record=False):
        self.back.append(layer.id())
        self.copies.discard(layer.id())
        return []

    def reattach_project(self):
        return 0, []

    def install(self):
        pass

    def uninstall(self):
        pass


@pytest.fixture
def env(monkeypatch):
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers"),
                       (".adapters", _ROOT / "adapters"), (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers"),
                       (".infrastructure", _ROOT / "infrastructure")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        package.__package__ = _PKG + name
        monkeypatch.setitem(sys.modules, _PKG + name, package)
    fake = FakeCopy()
    monkeypatch.setitem(sys.modules, _PKG + ".adapters.qgis.stream_copy", fake)
    derived = set()
    snapshots = types.ModuleType(_PKG + ".adapters.qgis.coverage_layers.snapshots")
    snapshots.registry = lambda: SimpleNamespace(is_derived=derived.__contains__)
    monkeypatch.setitem(sys.modules, _PKG + ".adapters.qgis.coverage_layers.snapshots", snapshots)
    sys.modules[_PKG + ".adapters.qgis"].stream_copy = fake
    said = []
    feedback = types.ModuleType(_PKG + ".infrastructure.feedback")
    feedback.show_info = lambda text: said.append(("info", text))
    feedback.show_success = lambda text: said.append(("success", text))
    feedback.show_warning = lambda text: said.append(("warning", text))
    monkeypatch.setitem(sys.modules, _PKG + ".infrastructure.feedback", feedback)
    monkeypatch.delitem(sys.modules, _PKG + ".ui.controllers.stream_copy_actions", raising=False)
    module = importlib.import_module(_PKG + ".ui.controllers.stream_copy_actions")
    monkeypatch.setattr(module, "_tr", lambda text: text)
    project = MagicMock()
    layers = {}
    project.mapLayer.side_effect = layers.get
    core = types.ModuleType("qgis.core")  # its own: the root mock is shared with the other tests
    project.mapLayers.side_effect = lambda: dict(layers)
    core.QgsProject = SimpleNamespace(instance=lambda: project)
    core.QgsApplication = SimpleNamespace(taskManager=MagicMock())
    monkeypatch.setitem(sys.modules, "qgis.core", core)
    answers = []
    actions = module.StreamCopyActions(None, ask=lambda title, text, buttons: answers.pop(0) if answers else 0)
    return SimpleNamespace(module=module, fake=fake, said=said, actions=actions, layers=layers, answers=answers,
                           derived=derived)


def layer(env, identifier="L1", name="Ortho"):
    made = MagicMock()
    made.id.return_value, made.name.return_value = identifier, name
    made.providerType.return_value = "wms"
    env.layers[identifier] = made
    return made


def test_state_of(env):
    stream, copy, other = layer(env, "S"), layer(env, "C"), layer(env, "O")
    env.fake.streams.add("S")
    env.fake.copies.add("C")
    assert [env.actions.state_of(item) for item in (stream, copy, other, None)] == ["stream", "copy", "", ""]
    assert "Local copy" in env.actions.tooltip_for(stream) and env.actions.tooltip_for(other) == ""


def test_a_copy_asks_then_runs_and_the_layer_reads_it(env):
    stream = layer(env, "S")
    env.fake.streams.add("S")
    changed = []
    env.actions.on_change(changed.append)
    env.actions.trigger(stream)
    assert env.actions.state_of(stream) == "copying" and len(env.fake.tasks) == 1 and changed == ["S"]
    task = env.fake.tasks[0]
    task.result.record = SimpleNamespace(notes=())
    task.callback(task)
    assert env.fake.switched == ["S"] and env.actions.state_of(stream) == "copy"
    assert env.said[-1][0] == "success" and changed == ["S", "S"]


def test_a_copy_declined_starts_nothing(env):
    stream = layer(env, "S")
    env.fake.streams.add("S")
    env.answers.append(1)
    assert env.actions.copy(stream) == "canceled" and not env.fake.tasks


def test_a_refusal_is_said_and_nothing_starts(env):
    stream = layer(env, "S")
    env.fake.streams.add("S")
    env.fake.refusal = "The terms of OpenStreetMap forbid keeping its tiles"
    assert env.actions.copy(stream) == env.fake.refusal
    assert env.said == [("warning", env.fake.refusal)] and not env.fake.tasks


def test_a_second_click_cancels_the_copy_under_way(env):
    stream = layer(env, "S")
    env.fake.streams.add("S")
    env.actions.trigger(stream)
    env.actions.trigger(stream)
    env.fake.tasks[0].cancel.assert_called_once()


def test_a_failed_copy_says_why_and_leaves_the_layer(env):
    stream = layer(env, "S")
    env.fake.streams.add("S")
    env.actions.copy(stream, confirm=False)
    task = env.fake.tasks[0]
    task.result.error = "the service gave no feature over the visible map: nothing was copied"
    task.callback(task)
    assert not env.fake.switched and env.said[-1][0] == "warning" and "nothing was copied" in env.said[-1][1]
    assert env.actions.state_of(stream) == "stream"


def test_a_layer_removed_during_its_copy(env):
    stream = layer(env, "S")
    env.fake.streams.add("S")
    env.actions.copy(stream, confirm=False)
    del env.layers["S"]
    task = env.fake.tasks[0]
    task.result.record = SimpleNamespace(notes=())
    task.callback(task)
    assert not env.fake.switched and "removed" in env.said[-1][1]


def test_notes_of_the_copy_are_a_warning(env):
    stream = layer(env, "S")
    env.fake.streams.add("S")
    env.actions.copy(stream, confirm=False)
    task = env.fake.tasks[0]
    task.result.record = SimpleNamespace(notes=("3 request(s) of the service were not answered",))
    task.callback(task)
    assert env.said[-1][0] == "warning" and "not answered" in env.said[-1][1]


def test_a_copy_of_a_layer_turned_to_another_service_is_not_used(env):
    """2026-11-24: the copy of the former service was applied when the source changed to another service of the
    same kind during the copy."""
    stream = layer(env, "S")
    stream.source.return_value = "url=https://tiles.example.org/wms"
    env.fake.streams.add("S")
    env.actions.copy(stream, confirm=False)
    stream.source.return_value = "url=https://other.example.org/wms"  # another service, meanwhile
    task = env.fake.tasks[0]
    task.result.record = SimpleNamespace(notes=(), path="/w/new.tif")
    task.callback(task)
    assert not env.fake.switched and env.fake.discarded == ["/w/new.tif"]
    assert "changed during its copy" in env.said[-1][1]


@pytest.mark.parametrize("answer, back, again", [(0, ["C"], 0), (1, ["C"] * 0, 1), (2, [], 0)])
def test_a_copy_offers_the_way_back_or_a_new_copy(env, answer, back, again):
    copy = layer(env, "C")
    env.fake.copies.add("C")
    env.answers.extend([answer, 0])
    env.actions.trigger(copy)
    assert env.fake.back == back and len(env.fake.tasks) == again


def test_copy_again_declined_reads_the_previous_copy(env):
    copy = layer(env, "C")
    env.fake.copies.add("C")
    env.answers.extend([1, 1])  # Copy again, then Cancel at the cost
    env.actions.trigger(copy)
    assert env.fake.restored == ["C"] and not env.fake.tasks


def test_copy_again_that_fails_reads_the_previous_copy(env):
    copy = layer(env, "C")
    env.fake.copies.add("C")
    env.answers.extend([1, 0])
    env.actions.trigger(copy)
    task = env.fake.tasks[0]
    task.result.error = "the service did not answer"
    task.callback(task)
    assert env.fake.restored == ["C"] and "previous copy" in env.said[-1][1]


def test_copy_again_that_succeeds_removes_the_previous_file(env):
    copy = layer(env, "C")
    env.fake.copies.add("C")
    env.answers.extend([1, 0])
    env.actions.trigger(copy)
    task = env.fake.tasks[0]
    task.result.record = SimpleNamespace(notes=(), path="/w/new.tif")
    task.callback(task)
    assert env.fake.discarded == ["/w/old.tif"] and env.fake.switched == ["C"]


def test_one_copy_of_a_layer_at_a_time(env):
    stream = layer(env, "S")
    env.fake.streams.add("S")
    assert env.actions.copy(stream, confirm=False) == ""
    assert "already" in env.actions.copy(stream, confirm=False) and len(env.fake.tasks) == 1


def test_a_layer_filtered_by_another_during_its_copy_does_not_take_it(env):
    stream = layer(env, "S")
    env.fake.streams.add("S")
    env.actions.copy(stream, confirm=False)
    env.derived.add("S")
    task = env.fake.tasks[0]
    task.result.record = SimpleNamespace(notes=(), path="/w/s.tif")
    task.callback(task)
    assert not env.fake.switched and env.fake.discarded == ["/w/s.tif"] and "changed" in env.said[-1][1]


def test_stop_puts_the_copies_back_on_their_service(env):
    layer(env, "C")
    env.fake.copies.add("C")
    env.actions.start()
    env.actions.stop()
    assert env.fake.back == ["C"]


def test_stop_keeps_a_copy_the_user_saved_as_permanent_data(env):
    saved = layer(env, "C")
    saved.customProperty.return_value = True
    env.fake.copies.add("C")
    env.actions.start()
    env.actions.stop()
    assert env.fake.back == []


def test_stop_cancels_the_copies_and_forgets_itself(env):
    stream = layer(env, "S")
    env.fake.streams.add("S")
    env.actions.start()
    assert env.module.get() is env.actions
    env.actions.copy(stream, confirm=False)
    env.actions.stop()
    env.fake.tasks[0].cancel.assert_called_once()
    assert env.fake.tasks[0].callback is None and env.module.get() is None

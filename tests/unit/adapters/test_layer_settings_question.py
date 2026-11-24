# -*- coding: utf-8 -*-
"""
2026-11-24: at the opening of a project whose layer settings differ from this computer's, the user is asked once
for the whole project which groups to take (EXPLORING, FILTERING); the answer may be remembered for this project.

A group taken goes to the panel and the SQLite (save_variables_from_layer: the variables hold the project's values
already); a group kept is left everywhere: nothing is written into the project. Modules tested:
core.domain.project_layer_settings (the question's logic), adapters.layer_settings_question.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

from core.domain import project_layer_settings as pls

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location("fmtest_q_type_utils", ROOT / "infrastructure" / "utils" / "type_utils.py")
_TYPE_UTILS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_TYPE_UTILS)


def load(text):
    return _TYPE_UTILS.return_typed_value(text, 'load')[0]


def _question_module():
    name = "fmtest_layer_settings_question"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "adapters" / "layer_settings_question.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.load = load
    return module


question_module = _question_module()

ASKS = {"parcelles_1": {
    "exploring": {"single_selection_expression": ('"nom"', '"rank"'), "is_linking": (False, True)},
    "filtering": {"has_buffer_value": (False, True), "buffer_value": (0.0, 12.5)}}}


def _held():
    return {"parcelles_1": {"exploring": {"single_selection_expression": '"nom"', "is_linking": False,
                                          "custom_selection_expression": '"rank" > 10'},
                            "filtering": {"has_buffer_value": False, "buffer_value": 0.0}}}


class TestLogic:

    def test_the_groups_asked(self):
        assert pls.asked_groups(ASKS) == ["exploring", "filtering"]
        assert pls.asked_groups({"a": {"filtering": {"x": (1, 2)}, "exploring": {}}}) == ["filtering"]
        assert pls.asked_groups({}) == []

    def test_only_the_groups_taken_are_applied(self):
        assert pls.settings_to_apply(ASKS, ["filtering"], _held(), load) == {
            "parcelles_1": {"filtering": {"has_buffer_value": True, "buffer_value": 12.5}}}
        assert pls.settings_to_apply(ASKS, [], _held(), load) == {}

    def test_a_setting_changed_meanwhile_by_the_user_stays(self):
        held = _held()
        held["parcelles_1"]["filtering"]["buffer_value"] = 3.0  # the user, before answering
        assert pls.settings_to_apply(ASKS, ["filtering"], held, load) == {
            "parcelles_1": {"filtering": {"has_buffer_value": True}}}

    def test_a_layer_gone_is_left(self):
        assert pls.settings_to_apply(ASKS, ["exploring", "filtering"], {}, load) == {}

    def test_asks_of_several_registrations(self):
        merged = pls.merged_asks(ASKS, {"routes_1": {"filtering": {"buffer_value": (0.0, 1.0)}},
                                        "parcelles_1": {"exploring": {"is_linking": (True, False)}}})
        assert merged["routes_1"] == {"filtering": {"buffer_value": (0.0, 1.0)}}
        assert merged["parcelles_1"]["exploring"]["is_linking"] == (True, False)
        assert ASKS["parcelles_1"]["exploring"]["is_linking"] == (False, True)  # not changed in place

    @pytest.mark.parametrize("groups, text", [(["exploring", "filtering"], "exploring,filtering"),
                                              (["filtering"], "filtering"), ([], "")])
    def test_a_remembered_answer(self, groups, text):
        assert pls.answer_text(groups) == text and pls.answer_groups(text) == groups

    @pytest.mark.parametrize("text", [None, 3, "exploring,other"])
    def test_no_answer(self, text):
        assert pls.answer_groups(text) is None


class Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class Layer:
    def __init__(self, layer_id):
        self._id = layer_id

    def id(self):
        return self._id


class Project:
    def __init__(self, path="/data/travaux.qgz"):
        self.path = path
        self.cleared, self.readProject = Signal(), Signal()
        self.layers = {"parcelles_1": Layer("parcelles_1")}

    def fileName(self):
        return self.path

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)


class Settings:
    def __init__(self):
        self.values = {}

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value

    def remove(self, group):
        self.values = {key: value for key, value in self.values.items() if not key.startswith(group)}


class Dialog:
    """LayerSettingsDialog as the user answers it."""

    def __init__(self, groups, can_remember, parent):
        self.groups, self.can_remember, self.parent = groups, can_remember, parent
        self.finished = Signal()
        self.opened = False
        self.taken, self.remembered = None, False

    def open(self):
        self.opened = True

    def answer(self, taken, remember=False):
        self.taken, self.remembered = taken, remember
        self.finished.emit(1)

    def reject(self):
        self.taken = []
        self.finished.emit(0)

    def chosen_groups(self):
        return list(self.taken or [])

    def remember(self):
        return self.remembered


@pytest.fixture
def env():
    state = types.SimpleNamespace(held=_held(), saved=[], dialogs=[], settings=Settings(), project=Project(),
                                  config={}, shown=[])
    dock = types.SimpleNamespace(current_layer=state.project.layers["parcelles_1"],
                                 current_layer_changed=lambda layer, manual_change: state.shown.append(layer.id()))

    def make_dialog(groups, can_remember, parent):
        dialog = Dialog(groups, can_remember, parent)
        state.dialogs.append(dialog)
        return dialog

    state.question = question_module.LayerSettingsQuestion(
        lambda: state.held, lambda layer, keys: state.saved.append((layer.id(), sorted(keys))), lambda: dock,
        lambda: state.config, settings=state.settings, project=state.project, make_dialog=make_dialog,
        schedule=lambda callback: callback())
    return state


def _asks():
    return {layer_id: {group: dict(keys) for group, keys in groups.items()} for layer_id, groups in ASKS.items()}


class TestQuestion:

    def test_asked_once_for_the_whole_project_with_both_groups(self, env):
        env.question.receive(_asks())
        assert len(env.dialogs) == 1 and env.dialogs[0].opened
        assert env.dialogs[0].groups == ["exploring", "filtering"] and env.dialogs[0].can_remember

    def test_filtering_only_keeps_my_exploring_and_writes_nothing_of_it(self, env):
        env.question.receive(_asks())
        env.dialogs[0].answer(["filtering"])
        assert env.held["parcelles_1"]["filtering"] == {"has_buffer_value": True, "buffer_value": 12.5}
        assert env.held["parcelles_1"]["exploring"]["single_selection_expression"] == '"nom"'  # mine
        assert env.held["parcelles_1"]["exploring"]["is_linking"] is False
        # only FILTERING is saved (the SQLite; its variables hold these values already)
        assert env.saved == [("parcelles_1", [("filtering", "buffer_value"), ("filtering", "has_buffer_value")])]
        assert env.shown == ["parcelles_1"]  # the panel shows them
        assert env.settings.values == {}  # not remembered

    def test_keep_mine_applies_nothing(self, env):
        env.question.receive(_asks())
        env.dialogs[0].answer([])
        assert env.held == _held() and env.saved == []

    def test_a_closed_question_applies_nothing(self, env):
        env.question.receive(_asks())
        env.dialogs[0].reject()
        assert env.held == _held() and env.saved == []

    def test_the_answer_remembered_is_used_without_question(self, env):
        env.question.receive(_asks())
        env.dialogs[0].answer(["filtering"], remember=True)
        env.held = _held()
        env.saved.clear()
        env.question.receive(_asks())  # the next opening of the project
        assert len(env.dialogs) == 1  # no second question
        assert env.saved == [("parcelles_1", [("filtering", "buffer_value"), ("filtering", "has_buffer_value")])]
        assert env.held["parcelles_1"]["exploring"]["single_selection_expression"] == '"nom"'

    def test_keep_mine_remembered(self, env):
        env.question.receive(_asks())
        env.dialogs[0].answer([], remember=True)
        env.question.receive(_asks())
        assert len(env.dialogs) == 1 and env.saved == []

    def test_an_answer_is_remembered_for_its_project_only(self, env):
        env.question.receive(_asks())
        env.dialogs[0].answer(["filtering"], remember=True)
        env.project.path = "/data/other.qgz"
        env.question.receive(_asks())
        assert len(env.dialogs) == 2

    def test_the_option_off_forgets_the_answers_and_does_not_offer_to_remember(self, env):
        env.question.receive(_asks())
        env.dialogs[0].answer(["filtering"], remember=True)
        env.config = {"APP": {"OPTIONS": {"LAYER_SETTINGS": {"remember_answers": {"value": False}}}}}
        env.question.receive(_asks())
        assert len(env.dialogs) == 2 and env.dialogs[1].can_remember is False
        assert env.settings.values == {}  # forgotten

    def test_another_project_drops_the_question(self, env):
        env.question.receive(_asks())
        env.project.readProject.emit(None)  # another project read meanwhile
        assert env.held == _held() and env.saved == []
        env.dialogs[0].answer(["exploring", "filtering"])  # too late: nothing applied
        assert env.held == _held() and env.saved == []

    def test_nothing_asked_for_nothing(self, env):
        env.question.receive({})
        env.question.receive({"parcelles_1": {"exploring": {}}})
        assert env.dialogs == []


def test_the_key_of_a_project_is_its_file_or_uri():
    assert question_module.project_key(Project("/data/travaux.qgz")) == "/data/travaux.qgz"
    assert question_module.project_key(Project("postgresql:?service=pg&project=travaux")).startswith("postgresql:")
    assert question_module.remember_answers_option({}) is True

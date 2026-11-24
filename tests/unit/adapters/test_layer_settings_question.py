# -*- coding: utf-8 -*-
"""
2026-11-24: at the opening of a project whose layer settings differ from this computer's, the user is asked once
for the whole project which groups to take (EXPLORING, FILTERING); the answer may be remembered for this project.

A group taken goes to the panel and the SQLite (save_variables_from_layer: the variables hold the project's values
already); a group kept is left everywhere: nothing is written into the project. Each group is settled once per
opening, by the answer of this opening or a remembered one; a group never asked is asked (review of 2026-11-24).
Modules tested: core.domain.project_layer_settings (the question's logic), adapters.layer_settings_question.
"""
import ast
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


def _config_option_bool():
    """config.config._get_option_bool, extracted with ast (the module imports QGIS)."""
    tree = ast.parse((ROOT / "config" / "config.py").read_text(encoding="utf-8"))
    wanted = {"_get_option_value", "_get_option_bool", "_FALSE_STRINGS", "_TRUE_STRINGS"}
    nodes = [node for node in tree.body if (isinstance(node, ast.FunctionDef) and node.name in wanted)
             or (isinstance(node, ast.Assign) and any(getattr(t, "id", "") in wanted for t in node.targets))]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "config.py", "exec"), namespace)
    return namespace["_get_option_bool"]


def _question_module():
    name = "fmtest_layer_settings_question"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "adapters" / "layer_settings_question.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.load = load
    module._get_option_bool = _config_option_bool()
    return module


question_module = _question_module()

ASKS = {"parcelles_1": {
    "exploring": {"single_selection_expression": ('"nom"', '"rank"'), "is_linking": (False, True)},
    "filtering": {"has_buffer_value": (False, True), "buffer_value": (0.0, 12.5)}}}
EXPLORING_ONLY = {"parcelles_1": {"exploring": ASKS["parcelles_1"]["exploring"]}}
FILTERING_ONLY = {"parcelles_1": {"filtering": ASKS["parcelles_1"]["filtering"]}}
FILTERING_KEYS = [("filtering", "buffer_value"), ("filtering", "has_buffer_value")]


def _held():
    return {"parcelles_1": {"exploring": {"single_selection_expression": '"nom"', "is_linking": False,
                                          "custom_selection_expression": '"rank" > 10'},
                            "filtering": {"has_buffer_value": False, "buffer_value": 0.0,
                                          "layers_to_filter": ["routes_1"]}}}


def _copy(asks):
    return {layer_id: {group: dict(keys) for group, keys in groups.items()} for layer_id, groups in asks.items()}


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

    def test_a_list_of_layers_is_compared_as_the_panel_holds_it(self):
        """C: the panel left out a layer the project does not have: compared without it. N1: the project's list is
        given as stored (its variable holds it: nothing written into the project)."""
        asks = {"parcelles_1": {"filtering": {"layers_to_filter": (["routes_1", "gone"], ["rivers_1", "gone"])}}}
        assert pls.settings_to_apply(asks, ["filtering"], _held(), load, {"parcelles_1", "routes_1", "rivers_1"}) == {
            "parcelles_1": {"filtering": {"layers_to_filter": ["rivers_1", "gone"]}}}
        same = {"parcelles_1": {"filtering": {"layers_to_filter": (["routes_1", "gone"], ["routes_1", "other"])}}}
        assert pls.settings_to_apply(same, ["filtering"], _held(), load, {"parcelles_1", "routes_1"}) == {}

    def test_two_lists_of_layers_in_another_order_are_the_same(self):
        assert pls.same_setting(["a", "b"], ["b", "a"], load, "layers_to_filter")
        assert pls.same_setting('["a", "b"]', ["b", "a"], load, "centroid_layers")
        assert not pls.same_setting(["a", "b"], ["b", "a"], load, "geometric_predicates")

    def test_asks_of_several_registrations(self):
        merged = pls.merged_asks(ASKS, {"routes_1": {"filtering": {"buffer_value": (0.0, 1.0)}},
                                        "parcelles_1": {"exploring": {"is_linking": (True, False)}}})
        assert merged["routes_1"] == {"filtering": {"buffer_value": (0.0, 1.0)}}
        assert merged["parcelles_1"]["exploring"]["is_linking"] == (True, False)
        assert ASKS["parcelles_1"]["exploring"]["is_linking"] == (False, True)  # not changed in place

    def test_the_asks_left_once_groups_are_settled(self):
        assert pls.without_groups(ASKS, ["exploring"]) == FILTERING_ONLY
        assert pls.without_groups(ASKS, ["exploring", "filtering"]) == {}

    @pytest.mark.parametrize("decisions, text", [
        ({"exploring": True, "filtering": True}, "exploring:apply,filtering:apply"),
        ({"exploring": False}, "exploring:keep"), ({"filtering": True, "exploring": False},
                                                   "exploring:keep,filtering:apply"), ({}, "")])
    def test_a_remembered_answer_per_group(self, decisions, text):
        assert pls.answer_text(decisions) == text and pls.answer_decisions(text) == decisions

    @pytest.mark.parametrize("text", [None, 3, "", "exploring", "other:apply", "exploring:maybe"])
    def test_no_answer(self, text):
        assert pls.answer_decisions(text) == {}


class Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot):
        self.slots.remove(slot)

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
        self.layers = {name: Layer(name) for name in ("parcelles_1", "routes_1", "rivers_1")}

    def fileName(self):
        return self.path

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)

    def mapLayers(self):
        return dict(self.layers)


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
        self.finished, self.destroyed = Signal(), Signal()
        self.opened, self.deleted = False, False
        self.taken, self.remembered = None, False

    def open(self):
        self.opened = True

    def answer(self, taken, remember=False):
        self.taken, self.remembered = taken, remember
        self.finished.emit(1)

    def reject(self):
        self.taken = []
        self.finished.emit(0)

    def deleteLater(self):
        self.deleted = True

    def chosen_groups(self):
        return list(self.taken or [])

    def remember(self):
        return self.remembered


@pytest.fixture
def env():
    state = types.SimpleNamespace(held=_held(), saved=[], dialogs=[], settings=Settings(), project=Project(),
                                  config={}, shown=[], later=[])
    dock = types.SimpleNamespace(current_layer=state.project.layers["parcelles_1"],
                                 current_layer_changed=lambda layer, manual_change: state.shown.append(layer.id()))

    def make_dialog(groups, can_remember, parent):
        dialog = Dialog(groups, can_remember, parent)
        state.dialogs.append(dialog)
        return dialog

    state.question = question_module.LayerSettingsQuestion(
        lambda: state.held, lambda layer, keys: state.saved.append((layer.id(), sorted(keys))), lambda: dock,
        lambda: state.config, settings=state.settings, project=state.project, make_dialog=make_dialog,
        schedule=state.later.append)

    def run():
        while state.later:
            state.later.pop(0)()
    state.run = run
    return state


class TestQuestion:

    def test_asked_once_for_the_whole_project_with_both_groups(self, env):
        env.question.receive(_copy(ASKS))
        env.question.receive(_copy(ASKS))  # another registration of the same opening
        env.run()
        assert len(env.dialogs) == 1 and env.dialogs[0].opened
        assert env.dialogs[0].groups == ["exploring", "filtering"] and env.dialogs[0].can_remember

    def test_a_list_of_layers_is_saved_as_the_project_stores_it(self, env):
        """N1: the SQLite takes the project's list as stored (a layer not loaded yet stays in the project); the panel
        leaves out the layers the project does not have, in memory only."""
        saved_values = []
        env.question._save_variables = lambda layer, keys: saved_values.append(
            {key: list(env.held[layer.id()][group][key]) for group, key in keys})
        env.question.receive({"parcelles_1": {"filtering": {
            "layers_to_filter": (["routes_1"], ["rivers_1", "not_loaded_yet"])}}})
        env.run()
        env.dialogs[0].answer(["filtering"])
        assert saved_values == [{"layers_to_filter": ["rivers_1", "not_loaded_yet"]}]
        assert env.held["parcelles_1"]["filtering"]["layers_to_filter"] == ["rivers_1"]

    def test_filtering_only_keeps_my_exploring_and_writes_nothing_of_it(self, env):
        env.question.receive(_copy(ASKS))
        env.run()
        env.dialogs[0].answer(["filtering"])
        assert env.held["parcelles_1"]["filtering"]["buffer_value"] == 12.5
        assert env.held["parcelles_1"]["filtering"]["has_buffer_value"] is True
        assert env.held["parcelles_1"]["exploring"]["single_selection_expression"] == '"nom"'  # mine
        assert env.held["parcelles_1"]["exploring"]["is_linking"] is False
        assert env.saved == [("parcelles_1", FILTERING_KEYS)]  # only FILTERING: the SQLite
        assert env.shown == ["parcelles_1"]  # the panel shows them
        assert env.settings.values == {}  # not remembered
        assert env.dialogs[0].deleted  # G: the dialog does not stay

    def test_keep_mine_applies_nothing(self, env):
        env.question.receive(_copy(ASKS))
        env.run()
        env.dialogs[0].answer([])
        assert env.held == _held() and env.saved == []

    def test_a_closed_question_applies_nothing(self, env):
        env.question.receive(_copy(ASKS))
        env.run()
        env.dialogs[0].reject()
        assert env.held == _held() and env.saved == []

    def test_the_answers_remembered_are_used_without_question(self, env):
        env.question.receive(_copy(ASKS))
        env.run()
        env.dialogs[0].answer(["filtering"], remember=True)
        env.project.readProject.emit(None)  # the next opening of the project
        env.held = _held()
        env.saved.clear()
        env.question.receive(_copy(ASKS))
        env.run()
        assert len(env.dialogs) == 1  # no second question
        assert env.saved == [("parcelles_1", FILTERING_KEYS)]
        assert env.held["parcelles_1"]["exploring"]["single_selection_expression"] == '"nom"'

    def test_keep_mine_remembered(self, env):
        env.question.receive(_copy(ASKS))
        env.run()
        env.dialogs[0].answer([], remember=True)
        env.project.readProject.emit(None)
        env.question.receive(_copy(ASKS))
        env.run()
        assert len(env.dialogs) == 1 and env.saved == []

    def test_a_group_never_asked_is_asked_later_even_with_an_answer_remembered(self, env):
        """A: the answer remembered when only EXPLORING differed says nothing of FILTERING."""
        env.question.receive(_copy(EXPLORING_ONLY))
        env.run()
        assert env.dialogs[0].groups == ["exploring"]
        env.dialogs[0].answer([], remember=True)
        env.project.readProject.emit(None)  # a later opening: FILTERING differs too
        env.question.receive(_copy(ASKS))
        env.run()
        assert len(env.dialogs) == 2 and env.dialogs[1].groups == ["filtering"]  # only the group never asked
        env.dialogs[1].answer(["filtering"], remember=True)
        assert env.saved == [("parcelles_1", FILTERING_KEYS)]
        assert pls.answer_decisions(list(env.settings.values.values())[0]) == {"exploring": False, "filtering": True}

    def test_a_group_found_while_the_question_is_open_is_asked_after(self, env):
        """A: a second registration brings a FILTERING difference while EXPLORING is asked: not settled by it."""
        env.question.receive(_copy(EXPLORING_ONLY))
        env.run()
        env.question.receive(_copy(FILTERING_ONLY))  # while the question is open
        env.run()
        assert len(env.dialogs) == 1
        env.dialogs[0].answer(["exploring"], remember=True)
        assert ("parcelles_1", [("exploring", "is_linking"), ("exploring", "single_selection_expression")]) \
            in env.saved
        assert pls.answer_decisions(list(env.settings.values.values())[0]) == {"exploring": True}  # FILTERING not
        env.run()
        assert len(env.dialogs) == 2 and env.dialogs[1].groups == ["filtering"]

    def test_a_group_settled_in_this_opening_follows_its_answer_without_question(self, env):
        """D: a registration that ends after the answer: its differences follow the answer given."""
        env.question.receive(_copy(ASKS))
        env.run()
        env.dialogs[0].answer(["filtering"])
        env.held["routes_1"] = {"filtering": {"buffer_value": 0.0}, "exploring": {"is_linking": False}}
        env.saved.clear()
        env.question.receive({"routes_1": {"filtering": {"buffer_value": (0.0, 5.0)},
                                           "exploring": {"is_linking": (False, True)}}})
        env.run()
        assert len(env.dialogs) == 1
        assert env.saved == [("routes_1", [("filtering", "buffer_value")])]
        assert env.held["routes_1"]["exploring"]["is_linking"] is False

    def test_an_answer_is_remembered_for_its_project_only(self, env):
        env.question.receive(_copy(ASKS))
        env.run()
        env.dialogs[0].answer(["filtering"], remember=True)
        env.project.readProject.emit(None)
        env.project.path = "/data/other.qgz"
        env.question.receive(_copy(ASKS))
        env.run()
        assert len(env.dialogs) == 2

    def test_the_option_off_forgets_the_answers_and_does_not_offer_to_remember(self, env):
        env.question.receive(_copy(ASKS))
        env.run()
        env.dialogs[0].answer(["filtering"], remember=True)
        env.project.readProject.emit(None)
        env.config = {"APP": {"OPTIONS": {"LAYER_SETTINGS": {"remember_answers": {"value": False}}}}}
        env.question.receive(_copy(ASKS))
        env.run()
        assert len(env.dialogs) == 2 and env.dialogs[1].can_remember is False
        assert env.settings.values == {}  # forgotten

    @pytest.mark.parametrize("value, remembered", [("false", False), ("off", False), ("true", True), (None, True)])
    def test_the_option_as_written_by_hand(self, value, remembered):
        """I: read with config._get_option_bool ("false" is off)."""
        config = {"APP": {"OPTIONS": {"LAYER_SETTINGS": {"remember_answers": {"value": value}}}}}
        assert question_module.remember_answers_option(config) is remembered

    def test_another_project_drops_the_question(self, env):
        env.question.receive(_copy(ASKS))
        env.run()
        env.project.readProject.emit(None)  # another project read meanwhile
        assert env.dialogs[0].deleted  # G/N4: closed and deleted
        assert env.held == _held() and env.saved == []
        env.dialogs[0].answer(["exploring", "filtering"])  # too late: nothing applied
        assert env.held == _held() and env.saved == []

    def test_the_asks_of_the_project_of_before_are_left(self, env):
        """B: registrations of P1 that end after P2 was read: no question in P2."""
        generation = env.question.generation
        env.project.readProject.emit(None)
        env.question.receive(_copy(ASKS), generation)
        env.run()
        assert env.dialogs == []
        env.question.receive(_copy(ASKS), env.question.generation)
        env.run()
        assert len(env.dialogs) == 1

    def test_a_dialog_deleted_with_its_parent_leaves_no_question_open(self, env):
        """G: the dock deleted while the question was open."""
        env.question.receive(_copy(EXPLORING_ONLY))
        env.run()
        env.dialogs[0].destroyed.emit()
        env.question.receive(_copy(FILTERING_ONLY))
        env.run()
        assert len(env.dialogs) == 2

    def test_teardown_releases_the_project(self, env):
        """H: unloaded, the project's signals no longer reach the question."""
        env.question.receive(_copy(ASKS))
        env.run()
        env.question.teardown()
        assert env.project.cleared.slots == [] and env.project.readProject.slots == []
        env.dialogs[0].answer(["filtering"])
        assert env.saved == []

    def test_nothing_asked_for_nothing(self, env):
        env.question.receive({})
        env.question.receive({"parcelles_1": {"exploring": {}}})
        env.run()
        assert env.dialogs == []


def test_the_key_of_a_project_is_its_file_or_uri():
    assert question_module.project_key(Project("/data/travaux.qgz")) == "/data/travaux.qgz"
    assert question_module.project_key(Project("postgresql:?service=pg&project=travaux")).startswith("postgresql:")
    assert question_module.remember_answers_option({}) is True

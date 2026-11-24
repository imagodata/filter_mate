# -*- coding: utf-8 -*-
"""The FilterMate settings of a layer as its project carries them (2026-11-24): which custom properties they are, a
legacy name (``exploring_<key>``, written by the panel until 5.1.2) over the right one, and how a stored value is typed
again."""
import importlib.util
import json
from pathlib import Path

import pytest

from core.domain import project_layer_settings as pls

_SPEC = importlib.util.spec_from_file_location(
    "fmtest_type_utils", Path(__file__).resolve().parents[4] / "infrastructure" / "utils" / "type_utils.py")
_TYPE_UTILS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_TYPE_UTILS)
return_typed_value = _TYPE_UTILS.return_typed_value  # what the task types the values of the SQLite with

pytestmark = pytest.mark.unit


def load(text):
    return return_typed_value(text, 'load')[0]


def prop(name):
    return f"variableValues/{name}"


class TestWhichProperties:

    @pytest.mark.parametrize("key", [
        prop("filterMate_exploring_is_linking"), prop("filterMate_filtering_layers_to_filter"),
        prop("exploring_is_linking"), prop("filtering_buffer_value"), prop("infos_layer_name"),
    ])
    def test_settings_of_filtermate(self, key):
        assert pls.is_settings_property(key)

    @pytest.mark.parametrize("key", [
        "variableNames", "variableValues", prop("my_variable"), prop("filterMate_infos_layer_name"),
        prop("filterMate_exploring_"), "filterMate_exploring_is_linking", prop("exploringx_y"), None, 3,
    ])
    def test_other_properties(self, key):
        assert not pls.is_settings_property(key)


class TestProjectSettings:

    def test_groups_and_keys(self):
        properties = {
            prop("filterMate_exploring_single_selection_expression"): '"nom"',
            prop("filterMate_exploring_is_linking"): False,
            prop("filterMate_filtering_layers_to_filter"): '["routes_1"]',
            prop("filterMate_infos_layer_name"): "parcelles",  # infos: read from the layer
            "variableNames": ["filterMate_exploring_is_linking"],
            "labeling/enabled": True,
        }
        assert pls.project_settings(properties) == {
            "exploring": {"single_selection_expression": '"nom"', "is_linking": False},
            "filtering": {"layers_to_filter": '["routes_1"]'},
        }

    def test_a_legacy_name_wins_over_the_right_one(self):
        """The panel wrote its changes under the legacy name; the right one kept the value of the registration."""
        properties = {
            prop("filterMate_exploring_single_selection_expression"): '"fid"',
            prop("exploring_single_selection_expression"): '"nom"',
            prop("filterMate_exploring_is_linking"): True,
            prop("infos_layer_name"): "parcelles",
        }
        assert pls.project_settings(properties) == {
            "exploring": {"single_selection_expression": '"nom"', "is_linking": True}}

    def test_a_value_none_is_an_empty_value(self):
        """An empty text (or an empty list stored as such) comes back from a .qgz as None, the property there."""
        assert pls.project_settings({prop("filterMate_filtering_buffer_value_expression"): None}) == {
            "filtering": {"buffer_value_expression": None}}
        assert pls.empty_value("") == "" and pls.empty_value(["a"]) == [] and pls.empty_value(None) == ""
        assert pls.same_setting(None, "", load)

    def test_nothing(self):
        assert pls.project_settings({}) == {}


class TestLegacyMoves:

    def test_legacy_values_go_under_their_right_names(self):
        properties = {
            prop("exploring_single_selection_expression"): '"nom"',
            prop("filtering_has_layers_to_filter"): True,
            prop("infos_layer_name"): "parcelles",
            prop("filterMate_exploring_single_selection_expression"): '"fid"',
            prop("filterMate_exploring_is_linking"): True,
        }
        writes, removals = pls.legacy_moves(properties)
        assert writes == {"filterMate_exploring_single_selection_expression": '"nom"',
                          "filterMate_filtering_has_layers_to_filter": True}
        assert removals == ["exploring_single_selection_expression", "filtering_has_layers_to_filter",
                            "infos_layer_name"]

    def test_nothing_to_move(self):
        assert pls.legacy_moves({prop("filterMate_exploring_is_linking"): True, "variableNames": []}) == ({}, [])

    def test_moved_then_read_gives_the_same_settings(self):
        properties = {prop("exploring_is_linking"): False, prop("filterMate_exploring_is_linking"): True,
                      prop("filterMate_exploring_is_tracking"): True}
        before = pls.project_settings(properties)
        writes, removals = pls.legacy_moves(properties)
        after = {key: value for key, value in properties.items() if key[len("variableValues/"):] not in removals}
        after.update({prop(name): value for name, value in writes.items()})
        assert pls.project_settings(after) == before == {"exploring": {"is_linking": False, "is_tracking": True}}


class TestTypedValue:

    @pytest.mark.parametrize("stored, expected", [
        (True, True), (False, False), (0.0, 0.0), (5, 5), (2.5, 2.5),
        ('"nom"', '"nom"'), ("single_selection", "single_selection"), ("", ""),
        ('"rank" > 10 AND "nom" LIKE \'a%\'', '"rank" > 10 AND "nom" LIKE \'a%\''),
        ('["routes_1", "rivers_2"]', ["routes_1", "rivers_2"]), ("[]", []),
        (["routes_1"], ["routes_1"]),  # a list written from the SQLite before
        ("true", True), ("0.0", 0.0),  # as the SQLite gives them
        ("[abc", "[abc"),  # not JSON: kept as written
    ])
    def test_as_the_panel_holds_it(self, stored, expected):
        value = pls.typed_value(stored, load)
        assert value == expected and type(value) is type(expected)

    def test_a_list_round_trips_as_the_panel_writes_it(self):
        """VariablesPersistenceManager writes a list as its JSON text."""
        targets = ["routes_1", "rivers_2"]
        stored = json.dumps(return_typed_value(targets, 'save')[0])
        assert pls.typed_value(stored, load) == targets

    def test_variable_name(self):
        assert pls.variable_name("filtering", "buffer_value") == "filterMate_filtering_buffer_value"


class TestStorage:

    @pytest.mark.parametrize("value, stored", [
        ([], "[]"), (["routes_1"], '["routes_1"]'), (("a",), '["a"]'), ({"k": 1}, '{"k": 1}'),
        (True, True), (0.0, 0.0), ('"nom"', '"nom"'),
    ])
    def test_a_list_is_stored_as_its_json_text(self, value, stored):
        assert pls.storable(value) == stored

    @pytest.mark.parametrize("one, other, same", [
        ('["a"]', ["a"], True), ("[]", [], True), (True, True, True), (True, 1, False), ("True", True, True),
        (0.0, 0, True), ('"nom"', '"nom"', True), ('"nom"', '"rank"', False), (None, "[]", False), (None, None, True),
    ])
    def test_the_same_setting_in_another_form(self, one, other, same):
        assert pls.same_setting(one, other, load) is same


class TestDropMissingLayers:

    def test_only_the_layers_of_the_project_stay(self):
        settings = {"exploring": {"is_linking": True},
                    "filtering": {"layers_to_filter": '["a", "gone"]', "centroid_layers": ["gone"],
                                  "geometric_predicates": '["Intersect"]'}}
        assert pls.drop_missing_layers(settings, {"a"}, load) == {
            "exploring": {"is_linking": True},
            "filtering": {"layers_to_filter": '["a"]', "centroid_layers": "[]",
                          "geometric_predicates": '["Intersect"]'}}

    def test_nothing_missing_keeps_the_stored_form(self):
        settings = {"filtering": {"layers_to_filter": ["a"]}}
        assert pls.drop_missing_layers(settings, {"a"}, load) == settings


class TestRepairedVariableNames:

    def test_the_value_of_the_user_comes_back_to_its_name(self):
        assert pls.repaired_variable_names(["filterMate_exploring_b", "my_var"], ["hello"], ()) == (
            ["my_var"], ["hello"])

    def test_lists_of_the_same_length_keep_their_pairs(self):
        assert pls.repaired_variable_names(["exploring_x", "my_var"], ["1", "hello"], {"exploring_x"}) == (
            ["my_var"], ["hello"])

    def test_nothing_of_filtermate(self):
        assert pls.repaired_variable_names(["my_var"], ["hello"], ()) is None
        assert pls.repaired_variable_names(None, None, ()) is None

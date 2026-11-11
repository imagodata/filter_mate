# -*- coding: utf-8 -*-
"""Recipes of the agent (core/agent/recipes.py): what a request keeps, and how it is stored."""
import json

import pytest

from core.agent.permissions import AGENT_OWN, PermissionPolicy, RUN
from core.agent.recipes import (
    HEADER, LIVE_TOOLS, MAX_NAME, MAX_RECIPES, MAX_STEPS, NOT_KEPT, RecipeError, dumps, find, followed_sources, kept,
    live_problem, parse, plain, recipes_block, saved, steps_of, summary, with_live, without,
)
from core.agent.system_prompt import SYSTEM_PROMPT
from core.agent.tool_catalog import CHAT_ONLY, REMOVE_RECIPE, SAVE_RECIPE, ToolSpec, chat_tools

pytestmark = pytest.mark.unit


def _tools():
    return {tool.name: tool for tool in chat_tools()}


def _call(name, arguments=None, failed=False, label=""):
    return (name, arguments if arguments is not None else {"layer": "batiments"}, failed, label or name)


class TestKept:
    def test_changes_that_succeeded_are_kept(self):
        tools = _tools()
        for name in ("apply_filter", "cross_filter", "set_layer_style", "run_algorithm", "export_layers",
                     "select_features", "add_field"):
            assert kept(name, tools[name], failed=False), name

    def test_reads_failures_and_the_conversation_are_not(self):
        tools = _tools()
        for name in ("list_layers", "describe_layer", "preview_filter", "map_context", "view_map"):
            assert not kept(name, tools[name], failed=False), name
        assert not kept("apply_filter", tools["apply_filter"], failed=True)
        for name in NOT_KEPT & set(tools):
            assert not kept(name, tools[name], failed=False), name
        assert not kept("run_pyqgis", ToolSpec("run_pyqgis", "", destructive=True), failed=False)
        assert not kept("unknown_tool", None, failed=False)

    def test_connector_tools_are_not_kept(self):
        assert not kept("mcp_github_create_issue", ToolSpec("mcp_github_create_issue", "", open_world=True), False)

    def test_steps_keep_the_order_and_the_words_of_the_thread(self):
        calls = [
            _call("describe_layer"),
            _call("preview_filter", {"layer": "batiments", "expression": "hauteur > 10"}),
            _call("apply_filter", {"layer": "batiments", "expression": "hauteur > 10"}, label="Filter on   batiments"),
            _call("cross_filter", {"source_layer": "batiments", "target_layers": ["ecoles"]}, failed=True),
            _call("set_layer_style", {"layer": "batiments", "mode": "graduated", "field": "hauteur"}),
        ]
        steps = steps_of(calls, _tools())
        assert [step["tool"] for step in steps] == ["apply_filter", "set_layer_style"]
        assert steps[0]["arguments"] == {"layer": "batiments", "expression": "hauteur > 10"}
        assert steps[0]["label"] == "Filter on batiments"

    def test_arguments_are_copied(self):
        arguments = {"layer": "batiments", "expression": "a = 1"}
        steps = steps_of([_call("apply_filter", arguments)], _tools())
        arguments["expression"] = "changed"
        assert steps[0]["arguments"]["expression"] == "a = 1"


def _steps(count=2):
    return [{"tool": "apply_filter", "arguments": {"layer": "l", "expression": f"a = {number}"}, "label": f"Filter {number}"}
            for number in range(count)]


class TestSaved:
    def test_a_recipe_gets_an_id_and_a_clean_name(self):
        recipes = saved([], "  Zones   inondables ", "filtre les bâtiments en zone inondable", _steps())
        assert recipes == [{"id": "r1", "name": "Zones inondables", "request": "filtre les bâtiments en zone inondable",
                            "steps": _steps()}]

    def test_the_same_name_replaces_in_place(self):
        recipes = saved(saved([], "A", "", _steps(1)), "B", "", _steps(1))
        again = saved(recipes, "a", "new", _steps(3))
        assert [recipe["id"] for recipe in again] == ["r1", "r2"]
        assert again[0]["name"] == "a" and len(again[0]["steps"]) == 3 and again[0]["request"] == "new"

    def test_bounds(self):
        with pytest.raises(RecipeError, match="name"):
            saved([], "  ", "", _steps())
        with pytest.raises(RecipeError, match="characters"):
            saved([], "x" * (MAX_NAME + 1), "", _steps())
        with pytest.raises(RecipeError, match="nothing to keep"):
            saved([], "A", "", [])
        with pytest.raises(RecipeError, match="steps at most"):
            saved([], "A", "", _steps(MAX_STEPS + 1))
        full = []
        for number in range(MAX_RECIPES):
            full = saved(full, f"recipe {number}", "", _steps(1))
        with pytest.raises(RecipeError, match="remove one"):
            saved(full, "one more", "", _steps(1))
        long = [{"tool": "apply_filter", "arguments": {"expression": "x" * 60_000}, "label": "long"}]
        with pytest.raises(RecipeError, match="too long"):
            saved([], "A", "", long)

    def test_new_ids_fill_the_gaps(self):
        recipes = saved(saved(saved([], "A", "", _steps(1)), "B", "", _steps(1)), "C", "", _steps(1))
        recipes = without(recipes, "r2")
        assert saved(recipes, "D", "", _steps(1))[-1]["id"] == "r2"

    def test_without_and_find(self):
        recipes = saved([], "A", "", _steps(1))
        assert find(recipes, "r1")["name"] == "A" and find(recipes, "r9") is None
        assert without(recipes, "r1") == []
        with pytest.raises(RecipeError, match="no recipe"):
            without(recipes, "r9")


class TestStore:
    def test_round_trip(self):
        recipes = saved(saved([], "A", "q", _steps(2)), "B", "", _steps(1))
        assert parse(dumps(recipes)) == recipes

    def test_damaged_entries_are_left_out(self):
        good = saved([], "A", "", _steps(1))[0]
        stored = json.dumps([
            good, {"id": "r2", "name": "", "steps": _steps(1)}, {"id": "r3", "name": "No steps", "steps": []},
            {"id": "r4", "name": "Code", "steps": [{"tool": "run_pyqgis", "arguments": {"code": "x"}}]},
            {"id": "r5", "name": "Bad", "steps": [{"tool": "apply_filter", "arguments": "a = 1"}]},
            {"id": "r1", "name": "Same id", "steps": _steps(1)}, "text", None,
        ])
        assert parse(stored) == [good]
        for nothing in ("", "not json", "{}", "[[[["):
            assert parse(nothing) == []

    def test_what_the_model_is_told(self):
        recipes = saved([], "A", "q", _steps(2))
        assert summary(recipes) == [{"recipe_id": "r1", "name": "A", "tools": ["apply_filter", "apply_filter"]}]
        block = recipes_block(recipes)
        assert block.startswith(HEADER) and "a = 0" not in block and "Filter 0" not in block  # nor the file's labels
        assert recipes_block([]) == ""

    def test_what_comes_from_a_file_is_one_visible_line(self):
        """A project made by someone else: no line break, bidi mark or control character hides what a step does."""
        assert plain("Zoom\n sur‮ la\x00 commune​", 60) == "Zoom sur la commune"
        stored = json.dumps([{"id": "r1", "name": "Ok‮evil", "request": "a\nb", "steps": [
            {"tool": "apply_filter", "arguments": {}, "label": "Zoom\nremove"},
            {"tool": "Bad Name", "arguments": {}}, {"tool": "x" * 80, "arguments": {}}]}])
        recipe = parse(stored)[0]
        assert recipe["name"] == "Ok evil" and recipe["request"] == "a b"
        assert [step["tool"] for step in recipe["steps"]] == ["apply_filter"]
        assert recipe["steps"][0]["label"] == "Zoom remove"


class TestTools:
    def test_the_tools_are_in_the_chat_and_run_at_every_level(self):
        tools = _tools()
        for name in (SAVE_RECIPE, REMOVE_RECIPE):
            assert name in tools and tools[name].chat_only and name in AGENT_OWN
            for level in ("advisor", "careful", "standard", "autonomous"):
                assert PermissionPolicy(level).verdict(tools[name]) == RUN
        assert {SAVE_RECIPE, REMOVE_RECIPE} <= {tool.name for tool in CHAT_ONLY}

    def test_the_prompt_says_when_to_keep_one(self):
        assert "save_recipe" in SYSTEM_PROMPT and "without you" in SYSTEM_PROMPT


def _cross(source="zones", target="communes"):
    return {"tool": "cross_filter", "label": "cross",
            "arguments": {"source_layer": source, "target_layers": [target], "predicates": ["Intersect"]}}


class TestLive:
    def test_a_recipe_follows_the_sources_of_its_cross_filters(self):
        recipe = saved([], "A", "", [_cross(), _cross("zones", "ecoles"), _cross("rivieres")])[0]
        assert followed_sources(recipe) == ["zones", "rivieres"]
        assert live_problem(recipe) == ""

    def test_what_cannot_run_at_every_save(self):
        assert "no source" in live_problem(saved([], "A", "", _steps(1))[0])
        export = {"tool": "export_layers", "arguments": {"layers": ["communes"]}, "label": "export"}
        zoom = {"tool": "zoom_to", "arguments": {"layer": "communes"}, "label": "zoom"}
        problem = live_problem(saved([], "A", "", [_cross(), export, zoom])[0])
        assert "export_layers" in problem and "zoom_to" in problem
        assert set(LIVE_TOOLS) >= {"cross_filter", "apply_filter", "set_layer_style"}
        assert not set(LIVE_TOOLS) & {"export_layers", "update_features", "remove_layers", "run_algorithm", "zoom_to"}

    def test_turned_on_and_off_and_kept(self):
        recipes = saved(saved([], "A", "", [_cross()]), "B", "", _steps(1))
        recipes = with_live(recipes, "r1", True)
        assert recipes[0]["live"] is True and "live" not in recipes[1]
        assert parse(dumps(recipes)) == recipes
        assert summary(recipes)[0]["live"] is True and "live" not in summary(recipes)[1]
        assert "live" not in with_live(recipes, "r1", False)[0]
        with pytest.raises(RecipeError, match="no source"):
            with_live(recipes, "r2", True)
        with pytest.raises(RecipeError, match="no recipe"):
            with_live(recipes, "r9", True)

    def test_a_stored_live_flag_holds_only_for_a_recipe_that_may_follow(self):
        """A project made by someone else cannot make an export run at every save."""
        export = {"tool": "export_layers", "arguments": {"layers": ["communes"]}, "label": "export"}
        stored = json.dumps([{"id": "r1", "name": "A", "live": True, "steps": [_cross(), export]},
                             {"id": "r2", "name": "B", "live": "yes", "steps": [_cross()]},
                             {"id": "r3", "name": "C", "live": True, "steps": [_cross()]}])
        recipes = parse(stored)
        assert [recipe.get("live") for recipe in recipes] == [None, None, True]

    def test_saving_again_under_the_name_keeps_it_live_while_it_may(self):
        recipes = with_live(saved([], "A", "", [_cross()]), "r1", True)
        assert saved(recipes, "A", "", [_cross("autre")])[0]["live"] is True
        assert "live" not in saved(recipes, "A", "", _steps(1))[0]

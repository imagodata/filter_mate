# -*- coding: utf-8 -*-
"""The settings of FilterMate as the agent reads them (core/agent/settings_reference.py)."""
import copy
import subprocess
import sys
from pathlib import Path

import pytest

from core.agent.permissions import (
    ADVISOR, ASK, AUTONOMOUS, CAREFUL, LOCAL, RULE_ALLOW, RULE_ASK, RULE_NEVER, RUN, STANDARD, TURNED_OFF,
    PermissionPolicy, risk_of)
from core.agent.recipes import NOT_KEPT
from core.agent.settings_reference import (
    EFFECT_NEXT_USE, EFFECT_NOW, EFFECT_RESTART, PRIVATE_EMPTY, PRIVATE_SET, checked_value, describe,
    find, get, leaf_values, load_default, plan, read_settings, reference_markdown, set_leaf)
from core.agent.tool_catalog import CHANGE_SETTINGS, SETTINGS_TOOLS

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def default():
    return load_default()


def test_every_visible_leaf_of_app_is_a_setting(default):
    rows = read_settings(None, default)
    paths = {row.path for row in rows}
    assert "APP.OPTIONS.QUERY_CACHE.enabled" in paths
    assert "APP.DOCKWIDGET.COLORS.ACTIVE_THEME" in paths
    assert not any(path.startswith("CURRENT_PROJECT") for path in paths)
    # hidden leaves are internal: links, the SQLite path, flags
    assert "APP.OPTIONS.APP_SQLITE_PATH" not in paths
    assert "APP.OPTIONS.AGENT.shown_by_default" not in paths
    assert len(paths) == len(rows) > 80


def test_value_comes_from_the_configuration_in_use(default):
    current = copy.deepcopy(default)
    current["APP"]["OPTIONS"]["QUERY_CACHE"]["max_size"]["value"] = 250
    current["APP"]["DOCKWIDGET"]["COLORS"]["ACTIVE_THEME"] = "dark"  # a raw (legacy) leaf
    del current["APP"]["OPTIONS"]["QUERY_CACHE"]["ttl_seconds"]  # missing: its default
    rows = {row.path: row for row in read_settings(current, default)}
    cache = rows["APP.OPTIONS.QUERY_CACHE.max_size"]
    assert (cache.value, cache.default, cache.changed) == (250, 100, True)
    assert rows["APP.DOCKWIDGET.COLORS.ACTIVE_THEME"].value == "dark"
    assert rows["APP.OPTIONS.QUERY_CACHE.ttl_seconds"].value == 0


def test_find_by_words_accents_and_section(default):
    rows = read_settings(None, default)
    assert any(row.path == "APP.DOCKWIDGET.COLORS.ACTIVE_THEME" for row in find(rows, "thème"))
    assert {row.section for row in find(rows, section="QUERY_CACHE")} == {"APP.OPTIONS.QUERY_CACHE"}
    assert {row.section for row in find(rows, section="APP.OPTIONS.QUERY_CACHE")} == {"APP.OPTIONS.QUERY_CACHE"}
    assert all(row.path.startswith("APP.DOCKWIDGET") for row in find(rows, section="Interface"))
    timeouts = find(rows, "postgresql timeout")
    assert timeouts[0].path == "APP.OPTIONS.QUERY_TIMEOUTS.postgresql_timeout_seconds"


def test_describe_lists_sections_without_arguments_and_caps_the_rows(default):
    rows = read_settings(None, default)
    answer = describe(rows)
    assert "settings" not in answer and answer["settings_total"] == len(rows)
    assert any(item["section"] == "APP.OPTIONS.QUERY_CACHE" for item in answer["sections"])
    capped = describe(rows, section="APP.OPTIONS", limit=3)
    assert len(capped["settings"]) == 3 and capped["matched"] > 3 and "more" in capped
    assert describe(rows, query="zzzz nothing")["settings"] == []


def test_changed_only(default):
    current = copy.deepcopy(default)
    current["APP"]["OPTIONS"]["HISTORY"]["max_history_size"]["value"] = 20
    answer = describe(read_settings(current, default), changed_only=True)
    assert [row["path"] for row in answer["settings"]] == ["APP.OPTIONS.HISTORY.max_history_size"]
    assert answer["settings"][0]["default"] == 100


def test_get_exact_by_ending_and_suggestions(default):
    rows = read_settings(None, default)
    row = get(rows, "app.options.query_cache.enabled")
    assert row["path"] == "APP.OPTIONS.QUERY_CACHE.enabled" and row["choices"] == [True, False]
    assert row["where"].endswith("QUERY_CACHE > enabled") and row["changed"] is False
    assert get(rows, "QUERY_TIMEOUTS.local_timeout_seconds")["min"] is not None
    with pytest.raises(LookupError, match="Did you mean"):
        get(rows, "APP.OPTIONS.QUERY_CACHE.enable")


def test_private_values_never_leave(default):
    current = copy.deepcopy(default)
    current["APP"]["USER_IDENTITY"]["value"] = "Jeanne Martin"
    current["APP"]["OPTIONS"]["CROSS_FILTER"]["pdal_path"]["value"] = "C:/Users/jeanne/pdal.exe"
    rows = read_settings(current, default)
    assert get(rows, "APP.USER_IDENTITY")["value"] == PRIVATE_SET
    assert get(rows, "APP.OPTIONS.CROSS_FILTER.cache_dir")["value"] == PRIVATE_EMPTY
    text = repr(describe(rows, query="pdal")) + repr(describe(rows, changed_only=True))
    assert "jeanne" not in text.lower()


def test_reference_is_up_to_date():
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_config_reference.py"), "--check"],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout


def test_reference_lists_every_setting(default):
    rows = read_settings(None, default)
    text = reference_markdown(rows)
    assert all(f"`{row.path.rsplit('.', 1)[-1]}`" in text for row in rows)


# --- change_settings ------------------------------------------------------------------------------------------------

def _row(rows, path):
    return next(row for row in rows if row.path == path)


def test_checked_value_follows_choices_bounds_and_types(default):
    rows = read_settings(None, default)
    theme = _row(rows, "APP.DOCKWIDGET.COLORS.ACTIVE_THEME")
    assert checked_value(theme, "DARK") == "dark"
    with pytest.raises(ValueError, match="takes one of"):
        checked_value(theme, "pink")
    cache = _row(rows, "APP.OPTIONS.QUERY_CACHE.enabled")
    assert checked_value(cache, False) is False
    with pytest.raises(ValueError):
        checked_value(cache, "false")  # a text is not a boolean
    timeout = _row(rows, "APP.OPTIONS.QUERY_TIMEOUTS.postgresql_timeout_seconds")
    assert checked_value(timeout, 120) == 120.0
    with pytest.raises(ValueError, match="at most"):
        checked_value(timeout, (timeout.maximum or 0) + 1)
    history = _row(rows, "APP.OPTIONS.HISTORY.max_history_size")
    with pytest.raises(ValueError, match="whole number"):
        checked_value(history, 10.5)


def test_plan_is_all_or_nothing_and_refuses_the_agent_settings_and_private_values(default):
    rows = read_settings(None, default)
    changes = plan(rows, [{"path": "APP.DOCKWIDGET.COLORS.ACTIVE_THEME", "value": "dark"},
                          {"path": "QUERY_CACHE.max_size", "value": 200}])
    assert [(row["path"], row["before"], row["after"]) for row in changes] == [
        ("APP.DOCKWIDGET.COLORS.ACTIVE_THEME", "auto", "dark"), ("APP.OPTIONS.QUERY_CACHE.max_size", 100, 200)]
    assert changes[0]["effect"] == EFFECT_NOW and changes[1]["effect"] == EFFECT_NEXT_USE
    assert plan(rows, [{"path": "APP.DOCKWIDGET.DOCK_POSITION", "value": "left"}])[0]["effect"] == EFFECT_RESTART
    for refused in ("APP.OPTIONS.AGENT.open_data_domains", "APP.OPTIONS.AGENT.enabled", "APP.USER_IDENTITY",
                    "APP.OPTIONS.CROSS_FILTER.pdal_path"):
        with pytest.raises(ValueError, match="Nothing changed"):
            plan(rows, [{"path": "APP.DOCKWIDGET.COLORS.ACTIVE_THEME", "value": "dark"},
                        {"path": refused, "value": "x" if "AGENT.enabled" not in refused else False}])
    with pytest.raises(ValueError, match="No setting"):
        plan(rows, [{"path": "APP.OPTIONS.NOPE", "value": 1}])
    with pytest.raises(ValueError):
        plan(rows, [])
    # hidden leaves are not settings: never reachable
    with pytest.raises(ValueError):
        plan(rows, [{"path": "APP.OPTIONS.APP_SQLITE_PATH", "value": "/tmp/x.db"}])
    same = plan(rows, [{"path": "APP.OPTIONS.QUERY_CACHE.max_size", "value": 100}])
    assert same[0]["before"] == same[0]["after"] == 100


def test_set_leaf_keeps_wrapped_leaves_and_leaf_values_reads_them(default):
    config = copy.deepcopy(default)
    set_leaf(config, "APP.OPTIONS.QUERY_CACHE.max_size", 300)
    assert config["APP"]["OPTIONS"]["QUERY_CACHE"]["max_size"]["description"]
    assert leaf_values(config, ["APP.OPTIONS.QUERY_CACHE.max_size"]) == {"APP.OPTIONS.QUERY_CACHE.max_size": 300}
    raw = {"APP": {"DOCKWIDGET": {"COLORS": {"ACTIVE_THEME": "auto"}}}}
    set_leaf(raw, "APP.DOCKWIDGET.COLORS.ACTIVE_THEME", "dark")
    assert raw["APP"]["DOCKWIDGET"]["COLORS"]["ACTIVE_THEME"] == "dark"


def test_numbers_are_finite_bounded_and_not_zero_where_the_default_is_positive(default):
    rows = read_settings(None, default)
    chunk = _row(rows, "APP.OPTIONS.STREAMING_EXPORT.chunk_size")
    with pytest.raises(ValueError, match="more than 0"):
        checked_value(chunk, 0)
    with pytest.raises(ValueError, match="at most"):
        checked_value(chunk, 10 ** 400)  # no OverflowError
    ttl = _row(rows, "APP.OPTIONS.QUERY_CACHE.ttl_seconds")
    assert checked_value(ttl, 0) == 0  # 0 means no expiration: its default
    resolution = _row(rows, "APP.OPTIONS.CROSS_FILTER.point_cloud_footprint_resolution")
    for wrong in (float("nan"), float("inf"), -float("inf")):
        with pytest.raises(ValueError):
            checked_value(resolution, wrong)


def test_a_missing_leaf_is_copied_from_the_defaults(default):
    config = {"APP": {"OPTIONS": {}}}
    set_leaf(config, "APP.OPTIONS.QUERY_CACHE.max_size", 300, default)
    leaf = config["APP"]["OPTIONS"]["QUERY_CACHE"]["max_size"]
    assert leaf["value"] == 300 and leaf["description"]
    with pytest.raises(ValueError):
        set_leaf({"APP": {"OPTIONS": "flat"}}, "APP.OPTIONS.QUERY_CACHE.max_size", 1, default)


def test_the_reference_with_values_keeps_private_values_private(default):
    current = copy.deepcopy(default)
    current["APP"]["USER_IDENTITY"]["value"] = "Jeanne Martin"
    current["APP"]["OPTIONS"]["QUERY_CACHE"]["max_size"]["value"] = 321
    text = reference_markdown(read_settings(current, default), with_values=True)
    assert "| Value |" in text and "321" in text and "Jeanne" not in text and PRIVATE_SET in text


def _change(*paths):
    return {"changes": [{"path": path, "value": 1} for path in paths], "reason": "r"}


def test_change_settings_is_asked_at_every_level_but_the_look_of_the_panel_when_autonomous():
    spec = next(tool for tool in SETTINGS_TOOLS if tool.name == CHANGE_SETTINGS)
    assert risk_of(spec) == LOCAL and not spec.read_only
    look, work = _change("APP.DOCKWIDGET.COLORS.ACTIVE_THEME"), _change("APP.OPTIONS.QUERY_CACHE.max_size")
    for level in (ADVISOR, CAREFUL, STANDARD):
        assert PermissionPolicy(level).verdict(spec, look) == ASK
        assert PermissionPolicy(level).verdict(spec, work) == ASK
    assert PermissionPolicy(AUTONOMOUS).verdict(spec, look) == RUN
    assert PermissionPolicy(AUTONOMOUS).verdict(spec, work) == ASK
    assert PermissionPolicy(AUTONOMOUS).verdict(spec, _change("APP.DOCKWIDGET.UI_PROFILE",
                                                             "APP.OPTIONS.QUERY_CACHE.max_size")) == ASK
    assert PermissionPolicy(AUTONOMOUS).verdict(spec, None) == ASK
    # fewer messages may hide a warning: not the look of the panel
    assert PermissionPolicy(AUTONOMOUS).verdict(spec, _change("APP.DOCKWIDGET.FEEDBACK_LEVEL")) == ASK


def test_change_settings_rules_and_grant():
    spec = next(tool for tool in SETTINGS_TOOLS if tool.name == CHANGE_SETTINGS)
    work = _change("APP.OPTIONS.QUERY_CACHE.max_size")
    assert PermissionPolicy(STANDARD, rules={CHANGE_SETTINGS: RULE_NEVER}).verdict(spec, work) == TURNED_OFF
    assert PermissionPolicy(STANDARD, rules={CHANGE_SETTINGS: RULE_ALLOW}).verdict(spec, work) == RUN
    assert PermissionPolicy(ADVISOR, rules={CHANGE_SETTINGS: RULE_ALLOW}).verdict(spec, work) == ASK
    look = _change("APP.DOCKWIDGET.COLORS.ACTIVE_THEME")
    assert PermissionPolicy(AUTONOMOUS, rules={CHANGE_SETTINGS: RULE_ASK}).verdict(spec, look) == ASK
    # never allowed for the conversation: each change is shown
    granted = PermissionPolicy(STANDARD, granted=[CHANGE_SETTINGS])
    assert not granted.grantable(spec) and granted.verdict(spec, work) == ASK
    assert PermissionPolicy(ADVISOR, granted=[CHANGE_SETTINGS]).verdict(spec, work) == ASK


def test_a_recipe_never_keeps_a_change_of_the_settings():
    assert CHANGE_SETTINGS in NOT_KEPT

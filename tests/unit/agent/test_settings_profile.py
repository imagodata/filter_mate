# -*- coding: utf-8 -*-
"""Profiles of settings (core/agent/settings_profile.py)."""
import copy
import json

import pytest

from core.agent import settings_profile as profile
from core.agent.permissions import ADVISOR, ASK, AUTONOMOUS, RULE_ALLOW, RUN, STANDARD, PermissionPolicy
from core.agent.recipes import NOT_KEPT
from core.agent.settings_reference import load_default, read_settings
from core.agent.tool_catalog import APPLY_SETTINGS_PROFILE, EXPORT_SETTINGS_PROFILE, SETTINGS_TOOLS


@pytest.fixture(scope="module")
def default():
    return load_default()


def _changed(default):
    current = copy.deepcopy(default)
    current["APP"]["OPTIONS"]["QUERY_CACHE"]["max_size"]["value"] = 300
    current["APP"]["DOCKWIDGET"]["COLORS"]["ACTIVE_THEME"]["value"] = "dark"
    current["APP"]["OPTIONS"]["AGENT"]["open_data_domains"]["value"] = "data.example.org"
    current["APP"]["USER_IDENTITY"]["value"] = "Jeanne Martin"
    current["APP"]["OPTIONS"]["CROSS_FILTER"]["pdal_path"]["value"] = "C:/Users/jeanne/pdal.exe"
    return current


def test_a_profile_holds_only_what_changed_and_what_the_agent_may_set(default):
    built = profile.build(read_settings(_changed(default), default), "Équipe SIG")
    assert built["format"] == profile.FORMAT and built["version"] == profile.VERSION
    assert built["settings"] == {"APP.OPTIONS.QUERY_CACHE.max_size": 300, "APP.DOCKWIDGET.COLORS.ACTIVE_THEME": "dark"}
    text = profile.dumps(built)
    assert "jeanne" not in text.lower() and "example.org" not in text


def test_read_refuses_what_is_not_a_profile():
    for text in ("{not json", json.dumps([1]), json.dumps({"format": "other"}),
                 json.dumps({"format": profile.FORMAT, "version": 99, "settings": {}}),
                 json.dumps({"format": profile.FORMAT, "version": 1, "settings": []}),
                 "x" * (profile.MAX_BYTES + 1)):
        with pytest.raises(ValueError):
            profile.read(text)
    name, settings = profile.read(json.dumps({"format": profile.FORMAT, "version": 1, "name": "A",
                                               "settings": {"APP.X": 1}}))
    assert name == "A" and settings == {"APP.X": 1}


def test_applying_a_profile_leaves_out_what_it_may_not_set(default):
    rows = read_settings(None, default)
    planned, left_out = profile.changes(rows, {
        "APP.OPTIONS.QUERY_CACHE.max_size": 300,
        "APP.OPTIONS.AGENT.open_data_domains": "evil.example.org",  # the agent's own
        "APP.OPTIONS.CROSS_FILTER.pdal_path": "/tmp/evil",  # a path, an executable
        "APP.OPTIONS.NOT_A_SETTING": 1,
        "APP.DOCKWIDGET.COLORS.ACTIVE_THEME": "pink",  # not a choice
    })
    assert [(row["path"], row["after"]) for row in planned] == [("APP.OPTIONS.QUERY_CACHE.max_size", 300)]
    assert len(left_out) == 4 and any("agent itself" in reason for reason in left_out)


def test_file_names_are_plain():
    assert profile.file_name("Equipe SIG") == "Equipe_SIG.json"
    for wrong in ("", "../x", ".hidden", "a/b", "x" * 61):
        with pytest.raises(ValueError):
            profile.file_name(wrong)


def test_profile_tools_permissions_and_recipes():
    apply = next(tool for tool in SETTINGS_TOOLS if tool.name == APPLY_SETTINGS_PROFILE)
    export = next(tool for tool in SETTINGS_TOOLS if tool.name == EXPORT_SETTINGS_PROFILE)
    by_name = {"name": "Equipe"}
    for level in (ADVISOR, STANDARD, AUTONOMOUS):  # asked at every level, autonomous included
        assert PermissionPolicy(level).verdict(apply, by_name) == ASK
    assert PermissionPolicy(STANDARD, rules={APPLY_SETTINGS_PROFILE: RULE_ALLOW}).verdict(apply, by_name) == RUN
    assert export.destructive and PermissionPolicy(STANDARD).verdict(export, by_name) == ASK
    assert {APPLY_SETTINGS_PROFILE, EXPORT_SETTINGS_PROFILE} <= NOT_KEPT

# -*- coding: utf-8 -*-
"""The five visible-automation tools of the chat: declared, view-only, never kept, brought by a skill."""
import pytest

from core.agent.permissions import VIEW, VIEW_TOOLS, risk_of
from core.agent.recipes import NOT_KEPT
from core.agent.skills import SKILLS
from core.agent.tool_catalog import chat_tools
from core.agent.families import bringing, hidden_tools, unlocked
from core.agent.skills import names as skill_names

pytestmark = pytest.mark.unit

NAMES = ("open_layout", "flash_features", "set_active_layer", "show_message", "preview_atlas", "open_model", 'control_qgis')


def test_visible_tools_only_show_and_are_asked_like_a_view():
    specs = {tool.name: tool for tool in chat_tools()}
    for name in NAMES:
        spec = specs[name]
        assert spec.chat_only, name  # a window is needed: never served to another application
        assert not spec.read_only and not spec.destructive and not spec.open_world, name
        assert not spec.requires_confirmation, name
        assert risk_of(spec) == VIEW, name
        assert name in VIEW_TOOLS and name in NOT_KEPT, name


def test_skills_bring_the_visible_tools():
    assert {"open_layout", "preview_atlas"} <= set(SKILLS["layouts"].tools)
    assert {"flash_features", "set_active_layer", "show_message"} <= set(SKILLS["cartography"].tools)
    assert {'qgis_capabilities', 'control_qgis'} <= set(SKILLS['qgis-interface'].tools)


def test_gui_tools_are_unlocked_by_their_skills_and_never_exported():
    tools = chat_tools()
    hidden = hidden_tools(tools, SKILLS.values())
    assert set(NAMES) <= hidden
    assert {"open_layout", "preview_atlas"} <= unlocked(SKILLS["layouts"], hidden)
    assert {"flash_features", "set_active_layer", "show_message"} <= unlocked(SKILLS["cartography"], hidden)
    assert not (set(NAMES) & {tool.name for tool in tools if not tool.chat_only})
    assert bringing([tool for tool in tools if tool.name != "flash_features"], SKILLS.values()).get("flash_features") is None


def test_processing_models_uses_the_editor_without_expert_mode_and_has_no_mcp_export():
    offered = {tool.name for tool in chat_tools()}
    assert "processing-models" in skill_names(offered)
    assert "processing-models" in skill_names(offered - {"run_pyqgis"})
    assert "processing-models" not in skill_names(offered - {"open_model"})
    assert "processing-models" not in skill_names(offered, audience="mcp")
    assert set(SKILLS["processing-models"].requires) == {"open_model"}

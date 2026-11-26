# -*- coding: utf-8 -*-
"""The five visible-automation tools of the chat: declared, view-only, never kept, brought by a skill."""
import pytest

from core.agent.permissions import VIEW, VIEW_TOOLS, risk_of
from core.agent.recipes import NOT_KEPT
from core.agent.skills import SKILLS
from core.agent.tool_catalog import chat_tools

pytestmark = pytest.mark.unit

NAMES = ("open_layout", "flash_features", "set_active_layer", "show_message", "preview_atlas")


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

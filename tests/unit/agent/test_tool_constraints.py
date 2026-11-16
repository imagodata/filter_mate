# -*- coding: utf-8 -*-
"""What every tool of the chat accepts or refuses, without its texts (review of lot 2 of the token diet, 2026-11-16).

Lot 2 rewrote the descriptions and, in five places, dropped a maximum length with them: the plugin then accepted what
it refused. A description may change freely; a constraint only on purpose. After a change of a constraint meant:

    FM_WRITE_CONSTRAINTS=1 python -m pytest tests/unit/agent/test_tool_constraints.py
"""
import json
import os
from pathlib import Path

import pytest

from core.agent.tool_catalog import chat_tools

pytestmark = pytest.mark.unit

SNAPSHOT = Path(__file__).with_name("data") / "tool_constraints.json"
TEXTS = frozenset({"description", "title"})


def constraints(node):
    """``node`` without its texts; a property named description or title stays (its name is a constraint)."""
    if isinstance(node, list):
        return [constraints(item) for item in node]
    if not isinstance(node, dict):
        return node
    return {key: (_named(value) if key in ("properties", "$defs", "definitions") else constraints(value))
            for key, value in node.items() if key not in TEXTS}


def _named(node):
    return {key: constraints(value) for key, value in node.items()} if isinstance(node, dict) else node


def current():
    return {tool.name: constraints(tool.input_schema) for tool in sorted(chat_tools(), key=lambda tool: tool.name)}


def test_no_constraint_changes_unless_meant():
    now = current()
    if os.environ.get("FM_WRITE_CONSTRAINTS"):
        SNAPSHOT.write_text(json.dumps(now, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    kept = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    changed = sorted(name for name in set(now) | set(kept) if now.get(name) != kept.get(name))
    assert not changed, f"constraints changed: {changed} (see the docstring to take them again)"


def test_the_five_lengths_the_review_found_stay():
    tools = {tool.name: tool.input_schema["properties"] for tool in chat_tools()}
    assert tools["set_labels"]["field"]["maxLength"] == 1000 and tools["set_labels"]["color"]["maxLength"] == 50
    assert tools["create_layout"]["title"]["maxLength"] == 200
    assert tools["similar_objects"]["name"]["maxLength"] == 200 and tools["add_osm_features"]["name"]["maxLength"] == 180

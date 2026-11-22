# -*- coding: utf-8 -*-
"""What each tool weighs as the model reads it, and the fixed part of a request (token diet, lot 2, 2026-11-16).

The weight of a tool is ``json.dumps({"name", "description", "input_schema"})`` of the form the providers send
(``core/agent/tool_schema.for_model``). cross_filter and set_layer_style keep a larger bound: without any description
their schemas alone weigh 1,687 and 1,464 characters (two nested objects of settings, eighteen arguments).
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from core.agent.chat_setup import MISSING_SOURCES, chat_instructions
from core.agent.tool_catalog import chat_tools
from core.agent.tool_schema import for_model

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
MAX_TOOL = 2000
LARGER = {"cross_filter": 3500, "set_layer_style": 3200}


def weight_of(tool) -> int:
    return len(json.dumps({"name": tool.name, "description": tool.description,
                           "input_schema": for_model(tool.input_schema)}, ensure_ascii=False))


@pytest.fixture(scope="module")
def bench():
    spec = importlib.util.spec_from_file_location("agent_request_weight", ROOT / "scripts" / "agent_request_weight.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_request_weight"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("agent_request_weight", None)


def test_cross_filter_and_set_layer_style_weigh_their_bound_at_most():
    weights = {tool.name: weight_of(tool) for tool in chat_tools() if tool.name in LARGER}
    assert set(weights) == set(LARGER)
    for name, bound in LARGER.items():
        assert weights[name] <= bound, (name, weights[name])


def test_every_chat_tool_weighs_2000_at_most():
    heavy = {tool.name: weight_of(tool) for tool in chat_tools()
             if tool.name not in LARGER and weight_of(tool) > MAX_TOOL}
    assert not heavy, heavy


def test_what_left_cross_filter_is_in_a_skill():
    """The derivatives of a DTM, the objects drawn in the dock and the polygons of segments are told by a skill that
    lists cross_filter, no longer by the description of the tool."""
    skills = {name: (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
              for name in ("terrain", "raster-objects")}
    assert "slope_percent" in skills["terrain"] and "derivative" in skills["terrain"]
    assert '"dock_objects": true' in skills["raster-objects"] and '"segments"' in skills["raster-objects"]
    for text in skills.values():
        assert "cross_filter" in text.split("---")[1]  # among the tools of its front matter
    cross = next(tool for tool in chat_tools() if tool.name == "cross_filter")
    told = " ".join(descriptions(for_model(cross.input_schema))) + cross.description
    assert "slope" not in told and "drew" not in told and "SAM" not in told


def descriptions(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "description" and isinstance(value, str):
                yield value
            else:
                yield from descriptions(value)
    elif isinstance(node, list):
        for item in node:
            yield from descriptions(item)


def test_the_unticked_sources_are_one_paragraph():
    text = chat_instructions([])
    paragraphs = [part for part in text.split("\n\n") if "show_settings_link with target sources" in part]
    assert len(paragraphs) == 1
    for tool in MISSING_SOURCES:
        assert paragraphs[0].count(tool) == 1, tool
    assert "never guess coordinates" in paragraphs[0]


def test_a_source_ticked_leaves_the_paragraph():
    text = chat_instructions([], offered=["find_place", "add_basemap"])
    assert "find_place (" not in text and "add_basemap (" not in text and "add_elevation (" in text


def test_the_fixed_part_is_under_21300(bench):
    """Instructions with the index, and the tools of the core, as the default settings send them."""
    instructions, tools, _held = bench.default_setup()
    fixed = len(instructions) + sum(weight_of(tool) for tool in tools)
    # 2026-11-22: 19,968 before the d3 charts; their three lines of the index and the entry of the skill charts in
    # load_skill add 211 (20,179), all of it trimmed to the words that say what each one is.
    # 2026-11-22 (projections): suggest_crs in the index and the skill projections in load_skill add 152 (20,396);
    # the descriptions of the other skills were already cut to their words for the layouts and the charts.
    # 2026-11-22 (cartograms): make_cartogram in the index and the skill cartograms add 140 (20,536).
    # 2026-11-22 (exports): export_layers, a tool of the core sent with every request, gains styles, single_file,
    # zip, package_name and three formats (+493), and the skill deliver its entry in load_skill (+85): 21,117.
    # 2026-11-22 (forms): set_form and relations in the index and the skill forms in load_skill add 140: 21,257.
    assert fixed < 21300, fixed

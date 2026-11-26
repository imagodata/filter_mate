# -*- coding: utf-8 -*-
"""The six families of the chat tools, and their plainer display titles (core/agent/tool_catalog.py)."""
import pytest

from core.agent.tool_catalog import (
    TOOL_DISPLAY_NAMES,
    TOOL_FAMILIES,
    display_title,
    family_of,
    family_title,
    load_catalog,
)

pytestmark = pytest.mark.unit


def test_six_families_with_titles():
    assert TOOL_FAMILIES == ("read", "filter", "style", "data", "layout", "outside")
    assert all(family_title(family) for family in TOOL_FAMILIES)


def test_every_catalog_tool_has_a_family():
    for tool in load_catalog():
        assert family_of(tool.name) in TOOL_FAMILIES, tool.name


def test_families_follow_what_the_tool_mainly_does():
    assert family_of("describe_layer") == "read"
    assert family_of("apply_filter") == "filter"
    assert family_of("set_layer_style") == "style"
    assert family_of("delete_features") == "data"
    assert family_of("create_layout") == "layout"
    assert family_of("run_pyqgis") == "outside"
    assert family_of("find_place") == "outside"
    assert family_of("add_osm_features") == "data"  # a network lookup that ends on the map
    assert family_of("change_settings") == "outside"


def test_connectors_and_unknown_tools_fall_outside():
    assert family_of("mcp_something") == "outside"
    assert family_of("a_tool_added_tomorrow") == "outside"
    assert family_of("") == "outside"


def test_puzzling_titles_read_plainly():
    assert display_title("set_exploring", "Drive the EXPLORING panel") == "Linked preview"
    assert display_title("segment_objects", "Draw objects with SAM") == "AI object selection"
    assert "service" in display_title("local_copy", "Copy a web service layer locally").lower()


def test_other_tools_keep_their_catalog_title():
    assert display_title("apply_filter", "Apply a filter") == "Apply a filter"
    assert display_title("unknown_tool", "") == "unknown_tool"
    assert set(TOOL_DISPLAY_NAMES) <= {tool.name for tool in load_catalog()}

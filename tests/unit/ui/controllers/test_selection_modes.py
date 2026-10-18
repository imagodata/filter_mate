# -*- coding: utf-8 -*-
"""The selection modes of the three layer kinds share one rule table (2026-10-18)."""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[4]


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modes = _load("fm_selection_modes", "ui/controllers/selection_modes.py")


class TestTable:
    def test_the_three_kinds_have_three_groups(self):
        assert set(modes.GROUP_TOOLS) == {"vector", "raster", "point_cloud"}
        for kind, groups in modes.GROUP_TOOLS.items():
            assert len(groups) == 3, kind

    def test_vector_groups_are_the_dock_ones(self):
        assert tuple(modes.GROUP_TOOLS["vector"]) == modes.VECTOR_GROUPS

    def test_the_expression_groups_have_no_tool(self):
        assert modes.GROUP_TOOLS["vector"]["custom_selection"] == ()
        assert modes.GROUP_TOOLS["raster"]["expression"] == ()
        assert modes.GROUP_TOOLS["point_cloud"]["expression"] == ()

    def test_raster_tools_match_the_rail(self):
        extras = _load("fm_extras_for_modes", "ui/controllers/coverage_dock_extras.py")
        tied = {tool for tools in modes.GROUP_TOOLS["raster"].values() for tool in tools}
        rail = set(extras.tools_for("raster")) - {"pushButton_exploring_raster_more"}
        assert tied == rail
        assert set(extras.CoverageDockExtras.PIPETTE_BUTTONS.values()) == set(modes.GROUP_TOOLS["raster"]["pipette"])

    def test_point_cloud_tools_match_the_rail(self):
        extras = _load("fm_extras_for_modes2", "ui/controllers/coverage_dock_extras.py")
        tied = {tool for tools in modes.GROUP_TOOLS["point_cloud"].values() for tool in tools}
        rail = set(extras.tools_for("point_cloud")) - {"pushButton_exploring_point_cloud_more"}
        assert tied == rail | {"pushButton_exploring_identify"}  # Identify is the class pipette

    def test_vector_tools_match_the_rail(self):
        extras = _load("fm_extras_for_modes3", "ui/controllers/coverage_dock_extras.py")
        tied = {tool for tools in modes.GROUP_TOOLS["vector"].values() for tool in tools}
        rail = set(extras.tools_for("vector")) - {"pushButton_exploring_vector_more"}
        assert tied == rail | {extras.VECTOR_LINK_BUTTON}


class TestRules:
    def test_r1_link_follows_single_and_multiple(self):
        link = "pushButton_checkable_exploring_linking_widgets"
        assert modes.tool_available("vector", "single_selection", link)
        assert modes.tool_available("vector", "multiple_selection", link)
        assert not modes.tool_available("vector", "custom_selection", link)
        assert not modes.tool_available("vector", None, link)

    def test_r1_shared_buttons_are_always_available(self):
        for group in modes.VECTOR_GROUPS:
            assert modes.tool_available("vector", group, "pushButton_checkable_exploring_selecting")
            assert modes.tool_available("vector", group, "pushButton_exploring_zoom")

    def test_r1_style_link_follows_the_range(self):
        link = "pushButton_checkable_exploring_raster_link"
        assert modes.tool_available("raster", "range", link)
        assert not modes.tool_available("raster", "pipette", link)

    def test_r2_group_of_a_tool(self):
        assert modes.group_for_tool("raster", "pushButton_checkable_exploring_raster_detector") == "pipette"
        assert modes.group_for_tool("point_cloud", "pushButton_checkable_exploring_point_cloud_zone") == "ranges"
        assert modes.group_for_tool("point_cloud", "pushButton_exploring_identify") == "classes"
        assert modes.group_for_tool("vector", "pushButton_checkable_exploring_vector_similar") == "single_selection"
        assert modes.group_for_tool("vector", "pushButton_exploring_zoom") is None

    @pytest.mark.parametrize("current, count, from_map, expected", [
        ("single_selection", 2, False, "multiple_selection"),  # several from the widgets
        ("single_selection", 2, True, "multiple_selection"),  # several from the map
        ("single_selection", 1, True, "single_selection"),
        ("single_selection", 0, False, "single_selection"),
        ("multiple_selection", 1, True, "single_selection"),  # one from the map
        ("multiple_selection", 1, False, "multiple_selection"),  # the first check of the list
        ("multiple_selection", 3, True, "multiple_selection"),
        ("multiple_selection", 0, True, "multiple_selection"),
        ("custom_selection", 5, True, "custom_selection"),  # a count never leaves the expression
        ("custom_selection", 1, False, "custom_selection"),
        (None, 2, False, None),
    ])
    def test_the_count_chooses_the_vector_group(self, current, count, from_map, expected):
        assert modes.group_for_count(current, count, from_map) == expected

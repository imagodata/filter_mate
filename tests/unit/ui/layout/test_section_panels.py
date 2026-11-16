# -*- coding: utf-8 -*-
"""The buttons under their section and the sections in their own panel: the plain rules of ui/layout/section_bars.py
and ui/layout/section_panels.py (what Qt does with them is checked in a real QGIS, tests/qgis_headless)."""
import importlib
import itertools
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_section_panels_test"


def _load(module):
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.layout", _ROOT / "ui" / "layout")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.ui.layout.{module}")


bars = _load("section_bars")
panels = _load("section_panels")

FILTER, UNDO, REDO, COMPARE, UNFILTER, EXPORT, QFIELDCLOUD, ABOUT = bars.ACTION_ORDER


# --- which bar holds each button -------------------------------------------------

def test_one_bar_holds_every_button_by_default():
    for position in ("top", "bottom", "left", "right"):
        assert bars.bar_plan(position) == {bars.ONE_BAR: bars.ACTION_ORDER}


def test_sections_position_gives_each_section_its_buttons():
    plan = bars.bar_plan(bars.SECTIONS_POSITION)
    assert plan["filtering"] == (FILTER, UNDO, REDO, COMPARE, UNFILTER)
    assert plan["exporting"] == (EXPORT, QFIELDCLOUD)
    assert plan["configuration"] == (ABOUT,)
    assert plan[bars.ONE_BAR] == ()


def test_a_detached_section_takes_its_buttons_whatever_the_position():
    plan = bars.bar_plan("bottom", ["filtering"])
    assert plan["filtering"] == (FILTER, UNDO, REDO, COMPARE, UNFILTER)
    assert plan[bars.ONE_BAR] == (EXPORT, QFIELDCLOUD, ABOUT)
    assert "exporting" not in plan and "configuration" not in plan


def test_a_detached_section_without_buttons_takes_none():
    assert bars.bar_plan("left", ["agent"]) == {bars.ONE_BAR: bars.ACTION_ORDER}


def test_every_button_is_in_one_bar_and_one_only():
    sections = ("agent", "filtering", "exporting", "configuration")
    for position in ("top", "bottom", "left", "right", bars.SECTIONS_POSITION):
        for count in range(len(sections) + 1):
            for detached in itertools.combinations(sections, count):
                plan = bars.bar_plan(position, detached)
                held = [name for names in plan.values() for name in names]
                assert sorted(held) == sorted(bars.ACTION_ORDER), (position, detached)


# --- a button back in the one bar --------------------------------------------------

def test_a_button_goes_back_before_the_first_one_that_follows_it():
    present = [FILTER, None, UNFILTER, None, ABOUT]
    assert bars.insert_position(present, UNDO) == 2
    assert bars.insert_position(present, EXPORT) == 4


def test_the_last_button_goes_after_the_last_one():
    assert bars.insert_position([FILTER, None, EXPORT], ABOUT) == 3


def test_a_button_goes_first_in_an_empty_bar_or_before_all_the_others():
    assert bars.insert_position([], FILTER) == 0
    assert bars.insert_position([None, None], EXPORT) == 0
    assert bars.insert_position([UNDO, None, REDO], FILTER) == 0


def test_a_widget_the_bar_does_not_know_stays_last():
    assert bars.insert_position([FILTER, "something_else"], ABOUT) == 1


# --- the row of a section ----------------------------------------------------------

def test_the_buttons_of_a_row_are_spread_evenly():
    assert bars.row_signature([("a", True), ("b", True)]) == [bars.GAP, "a", bars.GAP, "b", bars.GAP]


def test_one_button_alone_is_centred():
    assert bars.row_signature([("export", True)]) == [bars.GAP, "export", bars.GAP]


def test_a_hidden_button_takes_no_gap():
    assert bars.row_signature([("a", True), ("b", False), ("c", True)]) == [bars.GAP, "a", bars.GAP, "b", "c", bars.GAP]


# --- when the buttons of a section act ---------------------------------------------

def test_the_open_section_acts():
    assert bars.section_active("filtering", "filtering")
    assert not bars.section_active("exporting", "filtering")
    assert not bars.section_active("filtering", None)


def test_a_detached_section_acts_whatever_is_open():
    assert bars.section_active("filtering", "exporting", ["filtering"])
    assert bars.section_active("exporting", "exporting", ["filtering"])
    assert bars.section_active("filtering", None, ("filtering", "agent"))
    assert not bars.section_active("exporting", None, ["filtering"])


# --- what is apart, kept in the settings -------------------------------------------

def test_the_sections_apart_are_read_in_the_order_of_the_dock():
    assert panels.parse_detached("exporting,filtering") == ("filtering", "exporting")
    assert panels.parse_detached(["configuration", "agent"]) == ("agent", "configuration")


def test_unknown_names_noise_and_repeats_are_left_out():
    assert panels.parse_detached("exporting, nothing, FILTERING, exporting") == ("filtering", "exporting")
    assert panels.parse_detached("exploring") == ()  # EXPLORING stays in the dock


def test_no_setting_is_no_section_apart():
    for value in (None, "", 0, 12, {"filtering": True}):
        assert panels.parse_detached(value) == ()


def test_what_is_saved_reads_back():
    for keys in ((), ("filtering",), ("agent", "exporting"), panels.DETACHABLE):
        assert panels.parse_detached(panels.format_detached(keys)) == keys


def test_what_is_apart_now_is_what_is_kept():
    present = ("agent", "filtering", "exporting", "configuration")
    assert panels.remembered(("filtering",), ("filtering", "exporting"), present) == ("filtering",)
    assert panels.remembered((), ("agent",), present) == ()


def test_a_section_the_dock_does_not_hold_this_time_stays_kept():
    # AGENT was apart, then turned off: FILTERING leaves and comes back, AGENT is apart again the day it returns.
    present = ("filtering", "exporting", "configuration")
    assert panels.remembered(("filtering",), ("agent", "filtering"), present) == ("agent", "filtering")
    assert panels.remembered((), ("agent", "filtering"), present) == ("agent",)


# --- where a panel goes the first time ---------------------------------------------

def test_the_lower_sections_are_tabbed_together_the_nearest_first():
    assert panels.tab_partners("exporting", ["filtering", "configuration"]) == ["filtering", "configuration"]
    assert panels.tab_partners("configuration", ["filtering", "exporting"]) == ["exporting", "filtering"]
    assert panels.tab_partners("filtering", ["configuration", "exporting"]) == ["exporting", "configuration"]


def test_agent_is_tabbed_with_none_of_them():
    assert panels.tab_partners("agent", ["filtering", "exporting"]) == []
    assert panels.tab_partners("filtering", ["agent"]) == []


def test_a_panel_gets_the_height_its_section_asks_within_its_share():
    assert panels.panel_height(400, 800, 600) == 400
    assert panels.panel_height(1000, 800, 600) == int(800 * panels.PANEL_MAX_SHARE)
    assert panels.panel_height(50, 800, 600) == panels.PANEL_MIN_HEIGHT


def test_a_panel_takes_no_more_than_the_dock_can_spare():
    assert panels.panel_height(400, 800, 250) == 250


def test_a_dock_with_no_room_to_spare_gets_the_panel_as_a_tab():
    assert panels.panel_height(400, 800, panels.PANEL_MIN_HEIGHT - 1) == 0
    assert panels.panel_height(400, 0, 0) == 0


# --- the dock itself, when QGIS starts ---------------------------------------------

def test_the_dock_goes_to_its_position_when_no_section_was_apart():
    assert not panels.restore_dock_first((), 2, 2)


def test_the_dock_goes_back_where_qgis_kept_it_when_sections_were_apart():
    assert panels.restore_dock_first(("filtering",), 2, 2)
    assert panels.restore_dock_first(["agent", "exporting"], "2", 2)  # QSettings reads a number back as text


def test_a_change_of_dock_position_wins_over_the_place_kept():
    assert not panels.restore_dock_first(("filtering",), 2, 1)
    assert not panels.restore_dock_first(("filtering",), None, 2)  # never placed with panels before


# --- the menu of a header ----------------------------------------------------------

def test_a_section_in_the_dock_can_leave_it():
    for key in panels.DETACHABLE:
        assert panels.menu_entries(key, []) == ["detach"]


def test_exploring_never_leaves_the_dock():
    assert panels.menu_entries("exploring", []) == []
    assert panels.menu_entries("exploring", ["agent"]) == ["attach_all"]


def test_with_a_section_apart_the_menu_brings_all_back():
    assert panels.menu_entries("exporting", ["filtering"]) == ["detach", "attach_all"]
    assert panels.menu_entries("filtering", ["filtering"]) == ["attach_all"]

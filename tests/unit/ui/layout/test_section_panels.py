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


# --- the panels kept in the settings -------------------------------------------------

def test_a_panel_is_kept_with_its_sections_in_their_order():
    assert panels.parse_groups("agent,filtering+exporting") == (("agent",), ("filtering", "exporting"))
    assert panels.parse_groups("configuration+filtering") == (("configuration", "filtering"),)


def test_a_list_of_names_is_one_panel_each():
    # What the build before the panels of several sections saved.
    assert panels.parse_groups("filtering,exporting") == (("filtering",), ("exporting",))
    assert panels.parse_groups(["agent", ("filtering", "exporting")]) == (("agent",), ("filtering", "exporting"))


def test_a_list_holds_one_panel_per_item_as_its_sections_or_as_its_text():
    # 2026-11-16, review: "filtering+exporting" in a list was read as one unknown name, and names alone were cut
    # into letters when saved: the setup, which keeps what it found as a list, wiped what was kept.
    assert panels.parse_groups(["agent", "filtering+exporting"]) == (("agent",), ("filtering", "exporting"))
    assert panels.format_groups(["agent", "filtering"]) == "agent,filtering"
    assert panels.format_groups(["agent", "filtering+exporting"]) == "agent,filtering+exporting"


def test_unknown_names_noise_and_repeats_are_left_out():
    assert panels.parse_groups("exporting+nothing, FILTERING +exporting, ,nowhere") == (("exporting",), ("filtering",))
    assert panels.parse_groups("exploring, nothing") == (("exploring",),)  # EXPLORING can be apart too


def test_no_setting_is_no_panel():
    for value in (None, "", 0, 12, {"filtering": True}):
        assert panels.parse_groups(value) == ()


def test_what_is_saved_reads_back():
    for groups in ((), (("filtering",),), (("agent",), ("exporting", "filtering")), (panels.DETACHABLE,)):
        assert panels.parse_groups(panels.format_groups(groups)) == groups
    assert panels.format_groups((("agent",), ("filtering", "exporting"))) == "agent,filtering+exporting"


def test_the_sections_apart_whatever_their_panel_in_the_order_of_the_dock():
    assert panels.parse_detached("exporting+filtering,agent") == ("agent", "filtering", "exporting")
    assert panels.parse_detached("") == ()


def test_the_panels_as_they_are_now_are_what_is_kept():
    present = ("agent", "filtering", "exporting", "configuration")
    assert panels.remembered((("filtering", "exporting"),), (("filtering",), ("agent",)), present) == (
        ("filtering", "exporting"),)
    assert panels.remembered((), (("agent",),), present) == ()


def test_a_section_the_dock_does_not_hold_this_time_stays_kept():
    # AGENT was apart, then turned off: FILTERING leaves and comes back, AGENT is apart again the day it returns.
    present = ("filtering", "exporting", "configuration")
    assert panels.remembered((("filtering",),), (("agent",), ("filtering",)), present) == (("filtering",), ("agent",))
    assert panels.remembered((), (("agent",), ("filtering",)), present) == (("agent",),)


def test_a_section_that_is_not_there_keeps_its_place_in_the_panel_it_shared():
    # 2026-11-16, review: AGENT is installed after the others when the dock opens. Kept alone as soon as anything
    # was remembered meanwhile, it lost the panel it shared, and the order of its sections.
    present = ("filtering", "exporting", "configuration")
    assert panels.remembered((("filtering",),), (("agent", "filtering"),), present) == (("agent", "filtering"),)
    assert panels.remembered((("filtering", "configuration"),), (("filtering", "agent", "configuration"),),
                             present) == (("filtering", "agent", "configuration"),)
    assert panels.remembered((("exporting",),), (("exporting", "agent"),), present) == (("exporting", "agent"),)
    # FILTERING turned off, EXPORTING put back in the dock: nothing of its panel is left to share.
    assert panels.remembered((), (("filtering", "exporting"),), ("exporting", "configuration")) == (("filtering",),)
    # The section it shared a panel with is in another panel now: it follows it there.
    assert panels.remembered((("configuration", "filtering"),), (("agent", "filtering"),), present) == (
        ("configuration", "agent", "filtering"),)


# --- where a section goes when nothing says where -------------------------------------

def test_the_lower_sections_go_together_as_in_the_dock():
    assert panels.smart_group("exporting", (("filtering",),)) == "filtering"
    assert panels.smart_group("configuration", (("agent",), ("exporting", "filtering"))) == "exporting"


def test_the_first_lower_section_to_leave_gets_a_new_panel():
    assert panels.smart_group("filtering", ()) is None
    assert panels.smart_group("filtering", (("agent",),)) is None


def test_agent_gets_its_own_panel():
    assert panels.smart_group("agent", (("filtering", "exporting"),)) is None


def test_a_section_does_not_join_the_panel_it_is_in():
    assert panels.smart_group("filtering", (("filtering", "exporting"),)) is None
    assert panels.smart_group("filtering", (("filtering",), ("exporting",))) == "exporting"


def test_a_panel_is_named_after_its_sections():
    assert panels.panel_title(["filtering"]) == "FILTERING"
    assert panels.panel_title(["exporting", "filtering"]) == "EXPORTING · FILTERING"


# --- two panels of FilterMate put together merge ---------------------------------------

def test_nothing_tabbed_nothing_merged():
    assert panels.fusion(["a", "b"], [[], []], []) is None
    assert panels.fusion(["a"], [["layers"]], []) is None  # a tab of a panel of QGIS is left alone


def test_a_panel_tabbed_with_the_dock_gives_its_sections_back():
    assert panels.fusion(["a", "b"], [[], ["dock"]], ["b"]) == ("b", None)


def test_the_panel_that_was_moved_gives_its_sections_to_the_one_that_was_there():
    assert panels.fusion(["a", "b"], [["b"], ["a"]], [], mover="a") == ("a", "b")
    assert panels.fusion(["a", "b"], [["b"], ["a"]], [], mover="b") == ("b", "a")


def test_without_a_mover_the_newer_panel_joins_the_older():
    assert panels.fusion(["a", "b"], [["b"], ["a"]], []) == ("b", "a")
    assert panels.fusion(["a", "b", "c"], [[], ["c"], ["b"]], [], mover="dock") == ("c", "b")


def test_the_dock_comes_first_when_both_are_tabbed():
    assert panels.fusion(["a", "b"], [["b"], ["a"]], ["a", "b"]) == ("a", None)


# --- where a new panel goes the first time ----------------------------------------------

def test_a_panel_gets_the_height_its_section_asks_within_its_share():
    assert panels.panel_height(400, 800, 600) == 400
    assert panels.panel_height(1000, 800, 600) == int(800 * panels.PANEL_MAX_SHARE)
    assert panels.panel_height(50, 800, 600) == panels.PANEL_MIN_HEIGHT


def test_a_panel_takes_no_more_than_the_dock_can_spare():
    assert panels.panel_height(400, 800, 250) == 250


def test_a_dock_with_no_room_to_spare_gets_the_panel_beside_it():
    assert panels.panel_height(400, 800, panels.PANEL_MIN_HEIGHT - 1) == 0
    assert panels.panel_height(400, 0, 0) == 0


def test_a_floating_panel_is_where_it_was_dropped_when_it_fits():
    assert panels.floating_corner((400, 300), (360, 460), (0, 0, 1919, 1079)) == (400, 300)


def test_a_floating_panel_dropped_near_an_edge_stays_whole_on_the_screen():
    screen = (0, 0, 1919, 1079)
    assert panels.floating_corner((-130, 288), (380, 460), screen) == (0, 288)
    assert panels.floating_corner((1800, 900), (380, 460), screen) == (1540, 620)
    assert panels.floating_corner((500, -40), (380, 460), (1920, 30, 3839, 1079)) == (1920, 30)  # a second screen


def test_a_panel_larger_than_the_screen_shows_its_title():
    assert panels.floating_corner((100, 100), (800, 900), (0, 0, 639, 479)) == (0, 0)


# --- the dock itself, when QGIS starts ---------------------------------------------

def test_the_dock_goes_to_its_position_when_no_section_was_apart():
    assert not panels.restore_dock_first((), 2, 2)


def test_the_dock_goes_back_where_qgis_kept_it_when_sections_were_apart():
    assert panels.restore_dock_first(("filtering",), 2, 2)
    assert panels.restore_dock_first(["agent", "exporting"], "2", 2)  # QSettings reads a number back as text


def test_a_change_of_dock_position_wins_over_the_place_kept():
    assert not panels.restore_dock_first(("filtering",), 2, 1)
    assert not panels.restore_dock_first(("filtering",), None, 2)  # never placed with panels before


# --- the menu of a section: separate, group, merge -----------------------------------

def test_a_section_in_the_dock_can_leave_it_alone_or_with_the_others():
    for key in panels.DETACHABLE:
        assert panels.menu_entries(key, ()) == [("detach", key), ("detach_all", "")]


def test_exploring_leaves_the_dock_by_its_own_entry_and_stays_when_it_is_alone():
    """2026-11-17: EXPLORING can be in a panel of its own; the dock is never left empty."""
    assert panels.menu_entries("exploring", ()) == [("detach", "exploring"), ("detach_all", "")]
    others = tuple(key for key in panels.DETACHABLE if key != "exploring")
    assert panels.menu_entries("exploring", (others,)) == [("attach_all", "")]  # alone in the dock: it stays
    # In its own panel it joins another one, or comes back, as any section.
    assert panels.menu_entries("exploring", (("exploring",), ("agent",))) == [
        ("group", "agent"), ("attach", "exploring"), ("detach_all", ""), ("attach_all", "")]


def test_exploring_gets_a_panel_of_its_own_when_nothing_says_where():
    assert panels.smart_group("exploring", (("agent",), ("filtering", "exporting"))) is None


def test_the_last_section_of_the_dock_stays_in_it():
    assert panels.can_leave("filtering", ["exploring", "filtering"])
    assert not panels.can_leave("filtering", ["filtering"])
    assert not panels.can_leave("filtering", ["exploring"])  # not in the dock
    apart = (("agent",), ("exploring",), ("exporting", "configuration"))
    assert panels.menu_entries("filtering", apart) == [("attach_all", "")]


def test_every_section_out_leaves_exploring_in_the_dock():
    assert panels.would_leave(panels.DETACHABLE) == ["agent", "filtering", "exporting", "configuration"]
    assert panels.would_leave(["exploring"]) == []
    # With EXPLORING already apart, the last section stays instead.
    assert panels.would_leave(["agent", "filtering", "exporting", "configuration"]) == [
        "agent", "filtering", "exporting"]
    assert panels.would_leave(["configuration"]) == []
    entries = panels.menu_entries("filtering", (("exploring",), ("agent",), ("configuration",)))
    assert ("detach", "filtering") in entries and ("detach_all", "") not in entries  # it would move this one only


def test_a_dock_left_empty_gets_exploring_back_first():
    assert panels.comes_back(["filtering", "exploring", "agent"]) == "exploring"
    assert panels.comes_back(["filtering", "configuration"]) == "filtering"
    assert panels.comes_back([]) is None


def test_the_last_section_in_the_dock_is_not_offered_with_the_others():
    apart = (("agent",), ("exporting", "configuration"))
    assert panels.menu_entries("filtering", apart) == [
        ("group", "exporting"), ("detach", "filtering"), ("group", "agent"), ("attach_all", "")]


def test_the_panel_of_its_stack_is_offered_first_to_a_section_of_the_dock():
    # Where it goes when nothing says where: before a panel of its own, and before the panel of AGENT.
    assert panels.menu_entries("exporting", (("agent",), ("filtering",))) == [
        ("group", "filtering"), ("detach", "exporting"), ("group", "agent"), ("detach_all", ""), ("attach_all", "")]


def test_agent_is_offered_its_own_panel_first():
    assert panels.menu_entries("agent", (("filtering",),))[:2] == [("detach", "agent"), ("group", "filtering")]


def test_a_section_alone_in_its_panel_joins_another_one_or_merges_back():
    assert panels.menu_entries("filtering", (("filtering",),)) == [
        ("attach", "filtering"), ("detach_all", ""), ("attach_all", "")]
    assert panels.menu_entries("exporting", (("agent",), ("filtering",), ("exporting",))) == [
        ("group", "filtering"), ("group", "agent"), ("attach", "exporting"), ("detach_all", ""), ("attach_all", "")]


def test_a_section_that_shares_its_panel_can_get_its_own():
    assert panels.menu_entries("exporting", (("filtering", "exporting"),)) == [
        ("detach", "exporting"), ("attach", "exporting"), ("detach_all", ""), ("attach_all", "")]


def test_every_section_apart_leaves_nothing_to_take_out():
    entries = panels.menu_entries("agent", (("agent",), ("filtering", "exporting", "configuration")))
    assert entries == [("group", "filtering"), ("attach", "agent"), ("attach_all", "")]


def test_a_section_turned_off_is_offered_nothing_and_is_not_counted():
    present = ("agent", "exploring", "exporting", "configuration")  # FILTERING is turned off
    assert panels.menu_entries("filtering", (), present) == [("detach_all", "")]
    assert panels.menu_entries("exporting", (("agent",), ("configuration",)), present) == [
        ("group", "configuration"), ("detach", "exporting"), ("group", "agent"), ("attach_all", "")]


# --- a section turned off carries no button ------------------------------------------

def test_a_section_turned_off_leaves_its_buttons_to_the_bar_for_all():
    plan = bars.bar_plan(bars.SECTIONS_POSITION, (), ["filtering"])
    assert "filtering" not in plan
    assert plan[bars.ONE_BAR] == (FILTER, UNDO, REDO, COMPARE, UNFILTER)
    assert plan["exporting"] == (EXPORT, QFIELDCLOUD)


def test_a_section_turned_off_carries_nothing_even_when_it_was_apart():
    assert bars.bar_plan("bottom", ["filtering"], ["filtering"]) == {bars.ONE_BAR: bars.ACTION_ORDER}


# --- the bar for all once a section took its buttons to its own panel (2026-11-16, audit) -------------------------


def test_the_bar_for_all_shows_only_while_one_of_its_buttons_acts():
    """FILTERING in its own panel left a bar in the dock for an Export greyed out beside About."""
    left = bars.bar_plan("bottom", detached=("filtering",))[bars.ONE_BAR]
    assert left == ("pushButton_action_export", "pushButton_action_qfieldcloud", "pushButton_action_about")
    assert not bars.one_bar_serves(left, open_key=None)
    assert not bars.one_bar_serves(left, open_key="filtering")  # its panel has its buttons
    assert bars.one_bar_serves(left, open_key="exporting")
    assert bars.one_bar_serves(left, open_key="configuration")
    assert not bars.one_bar_serves(left, open_key=None, agent=True)  # nothing of FILTERING is left in it


def test_what_stays_of_a_section_turned_off_keeps_the_bar():
    left = bars.bar_plan("bottom", detached=("exporting",), off=("filtering",))[bars.ONE_BAR]
    assert "pushButton_action_undo_filter" in left
    assert bars.one_bar_serves(left, open_key=None, off=("filtering",))


def test_undo_redo_and_compare_keep_the_bar_while_the_agent_walks_its_steps():
    left = bars.bar_plan("bottom", detached=("exporting",))[bars.ONE_BAR]
    assert set(bars.AGENT_BUTTONS) <= set(left)
    assert not bars.one_bar_serves(left, open_key=None)
    assert bars.one_bar_serves(left, open_key=None, agent=True)
    assert bars.one_bar_serves(left, open_key="filtering")


def test_a_button_of_no_section_always_acts():
    assert bars.one_bar_serves(["pushButton_action_of_an_extension"], open_key=None)


# --- the dock closed: its panels are not offered by View > Panels (2026-11-18) ---------------------------------

class _FakePanel:
    def __init__(self):
        self.visible = True
        self.action = types.SimpleNamespace(enabled=True, setEnabled=lambda value: setattr(self.action, "enabled", value))

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def toggleViewAction(self):  # noqa: N802 - Qt name
        return self.action


def _closing_panels(count=2):
    holder = panels.SectionPanels.__new__(panels.SectionPanels)
    holder._hidden_with_dock = False
    holder._dock = object()
    holder._panels = [_FakePanel() for _ in range(count)]
    return holder


def test_closing_the_dock_hides_its_panels_and_turns_their_entries_off():
    holder = _closing_panels()
    holder._on_dock_closed()
    assert all(not panel.visible and not panel.action.enabled for panel in holder._panels)
    assert holder._hidden_with_dock


def test_showing_the_dock_again_turns_the_entries_back_on_and_shows_the_panels():
    from qgis.PyQt.QtCore import QEvent
    holder = _closing_panels()
    holder._on_dock_closed()
    event = types.SimpleNamespace(type=lambda: QEvent.Type.Show)

    assert holder._on_event(holder._dock, event) is False

    assert all(panel.visible and panel.action.enabled for panel in holder._panels)
    assert not holder._hidden_with_dock


def test_a_panel_that_went_away_does_not_stop_the_others_from_being_turned_off():
    holder = _closing_panels(3)

    def gone():
        raise RuntimeError("wrapped C/C++ object has been deleted")

    holder._panels[0].hide = gone
    holder._panels[1].toggleViewAction = gone
    holder._on_dock_closed()
    assert not holder._panels[2].visible and not holder._panels[2].action.enabled

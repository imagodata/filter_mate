# -*- coding: utf-8 -*-
"""The rail of sections: the plain rules of ui/widgets/section_rail.py (where a dropped chip goes, the order kept in
the settings). The widget itself is checked in a real QGIS (tests/qgis_headless, FM_ONLY=sections)."""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_section_rail_test"


def _load():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.widgets", _ROOT / "ui" / "widgets")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.ui.widgets.section_rail")


rail = _load()
BOTTOM = ["filtering", "exporting", "configuration"]


# --- where a dropped chip goes -------------------------------------------------------

def test_a_chip_dropped_left_of_every_centre_goes_first():
    assert rail.drop_index([20, 60, 100], 5) == 0


def test_a_chip_goes_before_the_first_chip_whose_centre_is_right_of_it():
    assert rail.drop_index([20, 60, 100], 21) == 1
    assert rail.drop_index([20, 60, 100], 59.5) == 1
    assert rail.drop_index([20, 60, 100], 60) == 2


def test_a_chip_dropped_right_of_every_centre_goes_last():
    assert rail.drop_index([20, 60, 100], 300) == 3
    assert rail.drop_index([], 12) == 0


# --- the order after a move -----------------------------------------------------------

def test_a_chip_moved_along_its_rail():
    assert rail.moved(BOTTOM, "configuration", 0) == ["configuration", "filtering", "exporting"]
    assert rail.moved(BOTTOM, "filtering", 1) == ["exporting", "filtering", "configuration"]
    assert rail.moved(BOTTOM, "filtering", 2) == ["exporting", "configuration", "filtering"]


def test_a_chip_put_back_where_it_was_changes_nothing():
    for index, key in enumerate(BOTTOM):
        assert rail.moved(BOTTOM, key, index) == BOTTOM


def test_a_chip_come_from_another_rail_is_inserted():
    assert rail.moved(["filtering", "exporting"], "configuration", 1) == ["filtering", "configuration", "exporting"]
    assert rail.moved([], "agent", 0) == ["agent"]


def test_an_index_out_of_the_rail_is_brought_back_to_its_ends():
    assert rail.moved(BOTTOM, "filtering", 99) == ["exporting", "configuration", "filtering"]
    assert rail.moved(BOTTOM, "configuration", -3) == ["configuration", "filtering", "exporting"]


# --- the order kept in the settings ---------------------------------------------------

def test_no_setting_is_the_usual_order():
    for value in (None, "", 12, {"a": 1}):
        assert rail.parse_order(value, BOTTOM) == BOTTOM


def test_the_order_kept_is_read_back():
    kept = rail.format_order(["configuration", "filtering", "exporting"])
    assert kept == "configuration,filtering,exporting"
    assert rail.parse_order(kept, BOTTOM) == ["configuration", "filtering", "exporting"]


def test_a_section_the_setting_does_not_name_comes_after_in_its_usual_place():
    assert rail.parse_order("exporting", BOTTOM) == ["exporting", "filtering", "configuration"]
    assert rail.parse_order(["exploring"], ("agent", "exploring")) == ["exploring", "agent"]


def test_unknown_names_noise_and_repeats_are_left_out():
    assert rail.parse_order(" EXPORTING, nothing ,exporting,agent", BOTTOM) == ["exporting", "filtering", "configuration"]


def test_every_section_has_a_title_and_an_icon():
    assert set(rail.TITLES) == set(rail.ICONS) == {"agent", "exploring", "filtering", "exporting", "configuration"}

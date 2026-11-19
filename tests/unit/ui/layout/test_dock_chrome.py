# -*- coding: utf-8 -*-
"""The room the two stacks of the dock share: the plain rules of ui/layout/dock_chrome.py (what Qt does with them is
checked in a real QGIS, tests/qgis_headless, FM_ONLY=room)."""
import importlib
import itertools
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_dock_chrome_test"


def _load(module):
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.layout", _ROOT / "ui" / "layout")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.ui.layout.{module}")


chrome = _load("dock_chrome")

# A 834 px dock in the compact profile (QGIS LTR, 1600 x 1000): 733 px for the two stacks. The upper one cannot go
# under 122 px (rail, gap, 80 px of EXPLORING), the lower one under 150 px.
ROOM, UPPER, LOWER = 733, 122, 150


# --- the two stacks stretch the same ---------------------------------------------------------------------------------

def test_each_stack_gets_its_minimum_and_half_of_the_room_left():
    # 19 November 2026: 35 % of the room above (246 px), EXPLORING scrolled under a lower stack half empty.
    top = chrome.even_height(ROOM, UPPER, LOWER)
    assert top == 352
    assert top - UPPER == 230 and (ROOM - top) - LOWER == 231  # the odd pixel goes below


def test_equal_minimums_share_the_room_in_two():
    assert chrome.even_height(800, 100, 100) == 400
    assert chrome.even_height(801, 100, 100) == 400


def test_a_stack_with_a_larger_minimum_is_larger_by_the_difference():
    assert chrome.even_height(900, 162, 200) == 431  # the normal profile: 162 + 269 above, 200 + 269 below
    assert chrome.even_height(900, 300, 100) == 550


def test_a_room_with_nothing_left_gives_each_stack_its_minimum():
    assert chrome.even_height(UPPER + LOWER, UPPER, LOWER) == UPPER


def test_a_room_shorter_than_the_minimums_is_shared_as_they_are():
    assert chrome.even_height(136, UPPER, LOWER) == 61  # 122 / 272 of the room
    assert chrome.even_height(100, 50, 150) == 25


def test_no_stack_is_given_nothing():
    # 0 folds a collapsible stack (the compact profile) instead of holding it to its minimum.
    assert chrome.even_height(10, 0, 400) == 1
    assert chrome.even_height(10, 400, 0) == 9
    assert chrome.even_height(600, 0, 0) == 300


def test_the_two_stacks_get_the_same_room_beyond_their_minimum():
    leasts = (0, 80, 122, 150, 200, 240)
    for room, upper, lower in itertools.product((300, 500, 733, 734, 1200), leasts, leasts):
        top = chrome.even_height(room, upper, lower)
        assert 1 <= top <= room - 1
        if room >= upper + lower:
            assert 0 <= ((room - top) - lower) - (top - upper) <= 1, (room, upper, lower, top)


# --- the minimum of a stack ------------------------------------------------------------------------------------------

class _Size:
    def __init__(self, height):
        self._height = height

    def height(self):
        return self._height


class _Stack:
    def __init__(self, minimum, hint):
        self._minimum, self._hint = minimum, hint

    def minimumHeight(self):  # noqa: N802 - Qt name
        return self._minimum

    def minimumSizeHint(self):  # noqa: N802 - Qt name
        return _Size(self._hint)


def test_a_stack_with_a_minimum_height_cannot_go_under_it():
    # Qt reads the minimum height first, even under what the layout says (the tool box frame: 150 px).
    assert chrome.stack_least(_Stack(150, 260)) == 150
    assert chrome.stack_least(_Stack(150, 90)) == 150


def test_a_stack_without_one_cannot_go_under_what_its_layout_says():
    assert chrome.stack_least(_Stack(0, 122)) == 122

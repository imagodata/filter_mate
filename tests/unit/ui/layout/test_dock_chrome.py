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

# A 834 px dock in the compact profile (QGIS LTR, 1600 x 1000): 733 px for the two stacks, 35 % above by default.
ROOM, SHARE = 733, 0.35
VECTOR, RASTER = 332, 577  # the upper stack with the whole of EXPLORING shown: three groups, a raster
FILTERING, EXPORTING = 235, 259  # the lower stack with all its rows: rail, gap and 193 or 217 px of rows


# --- the height of the upper stack ----------------------------------------------------------------------------------

def test_without_a_height_of_its_own_below_the_share_of_5_1_1():
    assert chrome.upper_height(749, SHARE) == 262
    assert chrome.upper_height(749, SHARE, RASTER) == 262  # rows spread, or a tree: what EXPLORING asks changes nothing
    assert chrome.upper_height(749, 0.5421) == 406


def test_exploring_takes_the_room_the_rows_leave_when_it_lacks_some():
    # 19 November 2026: 252 px stayed empty under the rows while EXPLORING scrolled 331 px of a raster.
    assert chrome.upper_height(ROOM, SHARE, RASTER, FILTERING) == ROOM - FILTERING == 498
    assert chrome.upper_height(ROOM, SHARE, RASTER, EXPORTING) == ROOM - EXPORTING == 474


def test_with_room_for_both_exploring_gets_what_it_shows_and_the_rest_stays_below():
    assert chrome.upper_height(ROOM, SHARE, VECTOR, FILTERING) == VECTOR
    assert ROOM - chrome.upper_height(ROOM, SHARE, VECTOR, EXPORTING) > EXPORTING


def test_a_share_that_wastes_nothing_stays():
    assert chrome.upper_height(ROOM, 0.6, VECTOR, FILTERING) == 440  # both have more than they show
    assert chrome.upper_height(400, 0.5, RASTER, EXPORTING) == 200  # both scroll, as in 5.1.1


def test_the_rows_keep_their_room_from_a_larger_share():
    assert chrome.upper_height(ROOM, 0.8, VECTOR, FILTERING) == ROOM - FILTERING


def test_a_short_dock_gives_exploring_no_more_than_it_shows():
    assert chrome.upper_height(400, 0.5, 150, 300) == 150  # the rows below scroll 50 px instead of 100


def test_agent_takes_all_the_room_the_rows_leave():
    assert chrome.upper_height(ROOM, SHARE, None, EXPORTING) == ROOM - EXPORTING
    assert chrome.upper_height(ROOM, 0.8, None, EXPORTING) == 586  # a larger share stays: its thread uses it


def test_no_stack_is_given_nothing():
    # 0 folds a collapsible stack (the compact profile) instead of holding it to its minimum.
    assert chrome.upper_height(10, 0.01, 0, 20) == 1
    assert chrome.upper_height(10, 0.99, None, 0) == 9


def test_neither_stack_holds_room_the_other_one_lacks():
    needs = (0, 80, 235, 332, 577, 900)
    for room, share, upper, lower in itertools.product((300, 500, 733, 1200), (0.05, 0.35, 0.5, 0.95), needs, needs):
        top = chrome.upper_height(room, share, upper, lower)
        assert 1 <= top <= room - 1
        if 1 < upper < room - 1 and 1 < lower < room - 1:  # away from the edges, where no stack is given nothing
            assert not (top < upper and room - top > lower), (room, share, upper, lower, top)
            assert not (room - top < lower and top > upper), (room, share, upper, lower, top)
        wanted = int(round(room * share))
        wastes = (wanted < upper and room - wanted > lower) or (room - wanted < lower and wanted > upper)
        if not wastes and 1 <= wanted <= room - 1:
            assert top == wanted, (room, share, upper, lower, top)  # moved only when it has to be


# --- what a scrolled content asks -----------------------------------------------------------------------------------

class _Size:
    def __init__(self, height):
        self._height = height

    def height(self):
        return self._height


class _Layout:
    def __init__(self, wraps):
        self._wraps = wraps

    def hasHeightForWidth(self):  # noqa: N802 - Qt name
        return self._wraps


class _Content:
    """A scrolled widget: its hints, and its height for a width (16 px more under 300 px: a label wraps)."""

    def __init__(self, hint, least, wraps=False, layout=True):
        self._hint, self._least, self._wraps, self._has_layout = hint, least, wraps, layout

    def sizeHint(self):  # noqa: N802 - Qt name
        return _Size(self._hint)

    def minimumSizeHint(self):  # noqa: N802 - Qt name
        return _Size(self._least)

    def layout(self):
        return _Layout(self._wraps) if self._has_layout else None

    def sizePolicy(self):  # noqa: N802 - Qt name
        return _Layout(self._wraps)

    def heightForWidth(self, width):  # noqa: N802 - Qt name
        return self._hint + (16 if width < 300 else 0)


def test_rows_ask_their_hint():
    assert chrome.content_need(_Content(193, 120), 303) == 193


def test_a_content_asks_its_smallest_height_when_it_is_the_larger():
    assert chrome.content_need(_Content(248, 264), 303) == 264


@pytest.mark.parametrize("layout", [True, False])
def test_a_content_that_wraps_asks_its_height_for_the_width_it_has(layout):
    assert chrome.content_need(_Content(248, 248, wraps=True, layout=layout), 303) == 248
    assert chrome.content_need(_Content(248, 248, wraps=True, layout=layout), 299) == 264
    assert chrome.content_need(_Content(248, 248, wraps=False, layout=layout), 299) == 248

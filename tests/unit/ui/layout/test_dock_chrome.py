# -*- coding: utf-8 -*-
"""The room the two stacks of the dock share: the two defects of 5.1.1 that ui/layout/dock_chrome.py fixes without
changing what 5.1.1 shows otherwise (what Qt does with it is checked in a real QGIS, tests/qgis_headless,
FM_ONLY=like511)."""
import importlib
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
MAX = chrome.QWIDGETSIZE_MAX
RAIL = 34


class _Stack:
    """A child of the splitter, with the limits the managers of the dock and the stacks give it."""

    def __init__(self, minimum=0, maximum=MAX):
        self.minimum, self.maximum, self.visible = minimum, maximum, True

    def minimumHeight(self):  # noqa: N802 - Qt name
        return self.minimum

    def setMinimumHeight(self, value):  # noqa: N802
        self.minimum = value

    def maximumHeight(self):  # noqa: N802
        return self.maximum

    def setMaximumHeight(self, value):  # noqa: N802
        self.maximum = value

    def setVisible(self, visible):  # noqa: N802
        self.visible = visible


class _Size:
    def __init__(self, height):
        self._height = height

    def height(self):
        return self._height


class _Splitter:
    """757 px high: 733 px for the two stacks, 8 px of handle and 16 px of margins (QGIS LTR, 1600 x 1000)."""

    def __init__(self, stacks, sizes, height=757):
        self.stacks, self._sizes, self._height, self.set = stacks, list(sizes), height, []

    def count(self):
        return len(self.stacks)

    def widget(self, index):
        return self.stacks[index]

    def sizes(self):
        return list(self._sizes)

    def setSizes(self, sizes):  # noqa: N802
        self.set.append(list(sizes))

    def height(self):
        return self._height

    def handleWidth(self):  # noqa: N802
        return 8


def _sections(share=0.35, sizes=(246, 487)):
    """EXPLORING open above FILTERING, the lower stack with the minimum of the compact profile."""
    nothing, filtering = object(), object()
    top, bottom = _Stack(), _Stack(minimum=150)
    toolbox = types.SimpleNamespace(current=filtering, currentWidget=lambda: toolbox.current)
    sections = types.SimpleNamespace(
        top=top, detached=set(), _pages={"exploring": object()}, _share=share, _left=None,
        _bottom_limits=None, _bottom_held=None, _toolbox_minimum=None,
        _splitter=_Splitter([top, bottom], sizes), _toolbox=toolbox, _nothing=nothing, filtering=filtering,
        bottom_rail=types.SimpleNamespace(shown_sections=lambda: ["filtering", "exporting"]),
        _open_in_stack=lambda key: True, _headers_height=lambda: RAIL, _bottom_headers_height=lambda bottom: RAIL,
        _hold_toolbox=lambda nothing: None)
    for name in ("_fit", "_room", "_share_room", "_both_open", "_on_handle_moved", "dimensions_applied", "eventFilter"):
        setattr(sections, name, types.MethodType(getattr(chrome.DockSections, name), sections))
    sections.refresh_rails = sections._fit
    return sections


def _resized(sections, height, old_height):
    """The splitter of ``sections`` told of its new height, as Qt does before it resizes its stacks."""
    sections._splitter._height = height
    event = types.SimpleNamespace(type=lambda: chrome.QEvent.Type.Resize, size=lambda: _Size(height),
                                  oldSize=lambda: _Size(old_height))
    sections.eventFilter(sections._splitter, event)


# --- a display profile applied while nothing is open below -----------------------------------------------------------

def test_the_limits_of_the_managers_come_back_with_the_next_section():
    sections = _sections()
    bottom = sections._splitter.widget(1)
    sections._toolbox.current = sections._nothing
    sections._fit()
    assert (bottom.minimum, bottom.maximum) == (RAIL, RAIL)  # held to its rail
    sections._toolbox.current = sections.filtering
    sections._fit()
    assert (bottom.minimum, bottom.maximum) == (150, MAX)  # as 5.1.1: the minimum of the profile, no maximum


def test_a_display_profile_applied_with_nothing_open_does_not_keep_the_rail_as_a_maximum():
    # 5.1.1: the limits kept were dropped at each pass of the managers, and read again on the stack. The splitter
    # manager sets the minimum alone, after the dimensions: the maximum read was then the rail the stack was held
    # to, and FILTERING opened in a stack 150 px high that the handle could not enlarge.
    sections = _sections()
    bottom = sections._splitter.widget(1)
    sections._toolbox.current = sections._nothing
    sections._fit()
    bottom.minimum, bottom.maximum = 200, MAX  # the dimensions of the normal profile
    sections.dimensions_applied()
    bottom.minimum = 200  # then its splitter settings: the minimum alone
    sections.dimensions_applied()
    assert (bottom.minimum, bottom.maximum) == (RAIL, RAIL)  # still held to its rail: no band under it
    bottom.minimum, bottom.maximum = 150, MAX  # the compact profile again
    sections.dimensions_applied()
    bottom.minimum = 150
    sections.dimensions_applied()
    sections._toolbox.current = sections.filtering
    sections._fit()
    assert (bottom.minimum, bottom.maximum) == (150, MAX)


def test_the_dimensions_applied_with_a_section_open_keep_what_the_managers_set():
    sections = _sections()
    bottom = sections._splitter.widget(1)
    bottom.minimum = 200
    sections.dimensions_applied()
    assert (bottom.minimum, bottom.maximum) == (200, MAX)


# --- the handle where the user left it -------------------------------------------------------------------------------

def test_never_dragged_the_share_is_taken_as_5_1_1_takes_it():
    # Of a room that counts the margins of the splitter (749 px for 733): Qt takes them back from the upper stack,
    # and the dock opens with 246 px above 487 in the compact profile, as 5.1.1 does.
    sections = _sections(share=0.35)
    sections._share_room()
    assert sections._splitter.set == [[262, 487]]


def test_a_handle_left_by_the_user_comes_back_to_the_pixel(monkeypatch):
    # 5.1.1: left at 319 px, the handle came back at 310 px with the next section opened.
    monkeypatch.setattr(chrome, "_save_share", lambda share: None)
    sections = _sections(sizes=(319, 414))
    sections._on_handle_moved(319, 1)
    sections._fit()  # another section opened below
    assert sections._splitter.set == [[319, 414]]
    sections._splitter._sizes = [699, RAIL]  # the lower stack folded to its rail, then opened again
    sections._fit()
    assert sections._splitter.set[-1] == [319, 414]


def test_a_dock_of_another_height_takes_the_share_alone_as_5_1_1(monkeypatch):
    monkeypatch.setattr(chrome, "_save_share", lambda share: None)
    sections = _sections(sizes=(366, 367))
    sections._on_handle_moved(366, 1)
    _resized(sections, 957, 757)  # 200 px taller
    assert sections._left is None and sections._splitter.set == [[474, 475]]  # 949 px shared, Qt does the rest
    sections._splitter._sizes = [458, 475]
    _resized(sections, 757, 957)
    sections._fit()
    assert sections._splitter.set[-1] == [466, 467]  # the share of what the stacks had, not the heights left before


def test_a_wider_dock_keeps_the_heights_left(monkeypatch):
    monkeypatch.setattr(chrome, "_save_share", lambda share: None)
    sections = _sections(sizes=(319, 414))
    sections._on_handle_moved(319, 1)
    _resized(sections, 757, 757)
    assert sections._splitter.set == [[319, 414]]


def test_a_share_set_by_something_else_than_a_drag_rules(monkeypatch):
    # The scripts of the site set the share themselves (scripts/site_videos.py): the heights of an older drag
    # are not given back over it.
    monkeypatch.setattr(chrome, "_save_share", lambda share: None)
    sections = _sections(sizes=(319, 414))
    sections._on_handle_moved(319, 1)
    sections._share = 0.5
    sections._share_room()
    assert sections._splitter.set == [[374, 375]]

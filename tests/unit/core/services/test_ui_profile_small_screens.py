# -*- coding: utf-8 -*-
"""
Small screens with display scaling got the HIDPI profile and its heights.

``AppInitializer._initialize_ui_profile`` checked the device pixel ratio
before the (logical) resolution: a 1080p laptop at 150 % scaling reports
1280x720 logical pixels with dpr=1.5, so it received HIDPI -- a dock
minimum height of 600 logical px plus a non-collapsible 180+300 splitter,
taller than the dock area of such a screen (the bottom of the panel is
unreachable). Qt scales logical pixels by the dpr at render time, so a
small logical height needs COMPACT whatever the dpr is. The usable
height also excludes the taskbar: the detection reads the screen's
available geometry, not its full geometry.
"""
import ast
import enum
import logging
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_INITIALIZER = _ROOT / "core" / "services" / "app_initializer.py"


class _Profile(enum.Enum):
    NORMAL = "normal"
    COMPACT = "compact"
    HIDPI = "hidpi"


class _Rect:
    def __init__(self, width, height):
        self._width, self._height = width, height

    def width(self):
        return self._width

    def height(self):
        return self._height


class _Screen:
    def __init__(self, width, height, available_height, dpr, dpi=96.0):
        self._geometry = _Rect(width, height)
        self._available = _Rect(width, available_height)
        self._dpr, self._dpi = dpr, dpi

    def geometry(self):
        return self._geometry

    def availableGeometry(self):
        return self._available

    def devicePixelRatio(self):
        return self._dpr

    def logicalDotsPerInch(self):
        return self._dpi


def _choose(screen):
    chosen = []
    tree = ast.parse(_INITIALIZER.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "AppInitializer")
    method = next(node for node in cls.body
                  if isinstance(node, ast.FunctionDef) and node.name == "_initialize_ui_profile")
    namespace = {
        "logger": logging.getLogger("test_ui_profile"),
        "QApplication": types.SimpleNamespace(primaryScreen=lambda: screen),
        "UIConfig": types.SimpleNamespace(set_profile=chosen.append),
        "DisplayProfile": _Profile,
    }
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_INITIALIZER), "exec"), namespace)
    types.MethodType(namespace["_initialize_ui_profile"], types.SimpleNamespace())()
    assert len(chosen) == 1
    return chosen[0]


def test_scaled_1080p_laptop_is_compact_not_hidpi():
    # 1920x1080 at 150 %: 1280x720 logical px, taskbar included in geometry.
    assert _choose(_Screen(1280, 720, 680, dpr=1.5, dpi=144.0)) is _Profile.COMPACT


def test_scaled_1366x768_is_compact_not_hidpi():
    # 1366x768 at 150 %: 910x512 logical px, less than the HIDPI dock minimum alone.
    assert _choose(_Screen(910, 512, 472, dpr=1.5, dpi=144.0)) is _Profile.COMPACT


def test_4k_at_200_percent_stays_hidpi():
    # 3840x2160 at 200 %: 1920x1080 logical px, room enough for the HIDPI heights.
    assert _choose(_Screen(1920, 1080, 1040, dpr=2.0, dpi=192.0)) is _Profile.HIDPI


def test_large_desktop_stays_normal():
    assert _choose(_Screen(2560, 1440, 1400, dpr=1.0)) is _Profile.NORMAL


def test_plain_1366x768_stays_compact():
    assert _choose(_Screen(1366, 768, 728, dpr=1.0)) is _Profile.COMPACT


def test_the_threshold_is_800_usable_pixels():
    assert _choose(_Screen(1536, 864, 799, dpr=1.25, dpi=120.0)) is _Profile.COMPACT
    assert _choose(_Screen(1536, 864, 800, dpr=1.5, dpi=144.0)) is _Profile.HIDPI


def test_no_screen_falls_back_to_normal():
    assert _choose(None) is _Profile.NORMAL

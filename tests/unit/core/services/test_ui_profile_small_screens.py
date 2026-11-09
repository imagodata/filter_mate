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
import sys
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_INITIALIZER = _ROOT / "core" / "services" / "app_initializer.py"
_UI_CONFIG = _ROOT / "ui" / "config" / "__init__.py"


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


def _ui_config(screen, chosen=None):
    """The real UIConfig methods on a test class, the screen given by the test."""
    tree = ast.parse(_UI_CONFIG.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "UIConfig")
    names = ("profile_for_screen", "detect_profile_from_screen", "resolve_profile")
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    namespace = {"DisplayProfile": _Profile}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_UI_CONFIG), "exec"), namespace)
    return type("UIConfig", (), {
        **{name: namespace[name] for name in names},
        "current_screen": classmethod(lambda cls: screen),
        "set_profile": classmethod(lambda cls, profile: (chosen if chosen is not None else []).append(profile)),
    })


def _initialize(ui_config, config_data):
    tree = ast.parse(_INITIALIZER.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "AppInitializer")
    method = next(node for node in cls.body
                  if isinstance(node, ast.FunctionDef) and node.name == "_initialize_ui_profile")
    namespace = {"logger": logging.getLogger("test_ui_profile"), "UIConfig": ui_config, "DisplayProfile": _Profile}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_INITIALIZER), "exec"), namespace)
    instance = types.SimpleNamespace(_get_config_data=lambda: config_data)
    types.MethodType(namespace["_initialize_ui_profile"], instance)()


def _choose(screen):
    chosen = []
    _initialize(_ui_config(screen, chosen), {})
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


def _setting(value):
    return {"APP": {"DOCKWIDGET": {"UI_PROFILE": {"value": value}}}}


def _started_with(value, screen):
    chosen = []
    _initialize(_ui_config(screen, chosen), _setting(value))
    return chosen[0]


def test_the_stored_setting_decides_at_startup():
    large = _Screen(2560, 1440, 1400, dpr=1.0)
    assert _started_with("compact", large) is _Profile.COMPACT
    assert _started_with("hidpi", large) is _Profile.HIDPI


def test_auto_detects_from_the_screen_at_startup():
    assert _started_with("auto", _Screen(1280, 720, 680, dpr=1.5, dpi=144.0)) is _Profile.COMPACT


def test_an_unknown_setting_detects_from_the_screen():
    assert _started_with("giant", _Screen(2560, 1440, 1400, dpr=1.0)) is _Profile.NORMAL


def test_the_setting_is_also_read_as_a_plain_value():
    ui_config = _ui_config(_Screen(2560, 1440, 1400, dpr=1.0))
    assert ui_config.resolve_profile("Compact ") is _Profile.COMPACT
    assert ui_config.resolve_profile({"value": "normal"}) is _Profile.NORMAL
    assert ui_config.resolve_profile(None) is _Profile.NORMAL


def test_an_error_at_startup_falls_back_to_normal():
    chosen = []
    ui_config = _ui_config(None, chosen)
    ui_config.resolve_profile = classmethod(lambda cls, setting: 1 / 0)
    _initialize(ui_config, {})
    assert chosen == [_Profile.NORMAL]


def _current_screen(monkeypatch, main_window_screen, primary="primary screen"):
    tree = ast.parse(_UI_CONFIG.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "UIConfig")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "current_screen")
    namespace = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_UI_CONFIG), "exec"), namespace)
    widgets = types.ModuleType("qgis.PyQt.QtWidgets")
    widgets.QApplication = types.SimpleNamespace(primaryScreen=lambda: primary)
    utils = types.ModuleType("qgis.utils")
    utils.iface = types.SimpleNamespace(mainWindow=lambda: types.SimpleNamespace(screen=main_window_screen))
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtWidgets", widgets)
    monkeypatch.setitem(sys.modules, "qgis.utils", utils)
    return type("UIConfig", (), {"current_screen": namespace["current_screen"]}).current_screen()


def test_the_screen_of_the_qgis_window_comes_first(monkeypatch):
    assert _current_screen(monkeypatch, lambda: "window screen") == "window screen"


def test_without_qwidget_screen_the_primary_screen_is_used(monkeypatch):
    def before_qt_514():
        raise AttributeError("screen")
    assert _current_screen(monkeypatch, before_qt_514) == "primary screen"

# -*- coding: utf-8 -*-
"""FilterMate 5 design: one indicator for check boxes, radios and groups, in every theme (mockup.qss)."""
import importlib
import pathlib
import re
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_STYLES = _ROOT / "resources" / "styles"
_PKG = "fm_selection_controls_test"


def _design():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.styles", _ROOT / "ui" / "styles")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.ui.styles.mockup_design")


def _rules(qss):
    """``(selectors, body)`` of every rule, comments removed."""
    qss = re.sub(r"/\*.*?\*/", "", qss, flags=re.S)
    qss = re.sub(r"\{([a-z_]+)\}", r"<\1>", qss)  # {fm_*} tokens are not rule braces
    return [(sel.strip(), body) for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", qss)]


def _mockup():
    return (_STYLES / "mockup.qss").read_text(encoding="utf-8")


def test_indicators_keep_one_size_in_every_state():
    """default.qss widened the border to 2 px on hover / checked: the label moved when a box was ticked."""
    indicator_rules = [(sel, body) for sel, body in _rules(_mockup())
                       if "::indicator" in sel and "#checkBox_filtering_use_centroids" not in sel]
    assert indicator_rules
    for selectors, body in indicator_rules:
        for width in re.findall(r"border(?:-width)?\s*:\s*(\d+)px", body):
            assert width == "1", selectors
        for size in re.findall(r"(?:^|[;\s])(?:width|height)\s*:\s*(\d+)px", body):
            assert size == "15", selectors


@pytest.mark.parametrize("widget", ["QCheckBox", "QRadioButton", "QgsCollapsibleGroupBox", "QListWidget"])
def test_every_indicator_has_the_hover_and_checked_states(widget):
    selectors = " ".join(sel for sel, _body in _rules(_mockup()))
    assert f"{widget}::indicator:hover" in selectors
    assert f"{widget}::indicator:checked" in selectors


def test_radio_and_check_glyphs_follow_the_theme():
    qss = _mockup()
    assert "{control_radio_glyph}" in qss and "{control_check_glyph}" in qss
    loader = (_ROOT / "ui" / "styles" / "style_loader.py").read_text(encoding="utf-8")
    for name in ("check_dark.svg", "check_white.svg", "radio_dot_dark.svg", "radio_dot_white.svg"):
        assert (_STYLES / name).exists()
        assert name in loader
    # The glyph is fm_accent_text on fm_accent: dark on the light blue accent of the dark theme.
    design = _design()
    assert design.tokens(True)["fm_accent_text"].lower() == "#141414"
    assert "#141414" in (_STYLES / "check_dark.svg").read_text(encoding="utf-8")
    assert "#141414" in (_STYLES / "radio_dot_dark.svg").read_text(encoding="utf-8")


def test_raster_band_rows_use_no_qgis_palette_colours():
    """palette() kept the QGIS colours when the plugin theme differed (black radios, white toggles)."""
    source = (_ROOT / "ui" / "widgets" / "coverage_panels" / "raster_exploring_panel.py").read_text(encoding="utf-8")
    assert "palette(" not in source
    assert "RADIO_STYLE" not in source
    qss = _mockup()
    assert 'QToolButton[fm_band_toggle="true"]' in qss
    assert 'QToolButton[fm_band_chip="empty"]' in qss


def test_combo_arrow_is_the_spin_box_chevron():
    bodies = {sel: body for sel, body in _rules(_mockup())}
    assert "<spin_down_icon>" in bodies["#dockWidgetContents QComboBox::down-arrow"]
    assert "transparent" in bodies["#dockWidgetContents QComboBox::drop-down"]


def test_group_arrow_icons_render_in_the_muted_text_colour():
    design = _design()
    for key in ("group_expand", "group_collapse"):
        svg = design.svg_document(key, design.tokens(True)["fm_text_muted"])
        assert design.tokens(True)["fm_text_muted"] in svg and "currentColor" not in svg


class _Widget:
    def __init__(self, parent=None, manager=None, dark_palette=False):
        self._parent = parent
        if manager is not None:
            self._icon_manager = manager
        self._dark_palette = dark_palette

    def parentWidget(self):  # noqa: N802 - Qt name
        return self._parent

    def palette(self):
        lightness = 30 if self._dark_palette else 240
        color = types.SimpleNamespace(lightness=lambda: lightness)
        return types.SimpleNamespace(window=lambda: types.SimpleNamespace(color=lambda: color))


@pytest.mark.parametrize("dark", [True, False])
def test_plugin_theme_wins_over_the_qgis_palette(dark):
    design = _design()
    dock = _Widget(manager=types.SimpleNamespace(is_dark_mode=dark))
    child = _Widget(parent=_Widget(parent=dock), dark_palette=not dark)
    assert design.plugin_is_dark(child) is dark


def test_plugin_theme_falls_back_to_the_palette_outside_the_dock():
    design = _design()
    assert design.plugin_is_dark(_Widget(dark_palette=True)) is True
    assert design.plugin_is_dark(_Widget(dark_palette=False)) is False

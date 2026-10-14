# -*- coding: utf-8 -*-
"""FilterMate 5 design: pure helpers of ui/layout/mockup_layout.py."""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_mockup_layout_test"


def _load():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.layout", _ROOT / "ui" / "layout"),
                       (".ui.styles", _ROOT / "ui" / "styles")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.ui.layout.mockup_layout")


layout = _load()


GAP = layout.GAP_ITEM


def test_rail_plan_gaps_above_between_and_below():
    assert layout.rail_plan([True, True, True]) == [GAP, 0, GAP, 1, GAP, 2, GAP]


def test_rail_plan_hidden_buttons_get_no_gap():
    # Tracking and linking hidden for a raster: the three shown buttons stay evenly spread.
    assert layout.rail_plan([True, False, True, False, True]) == [GAP, 0, 1, GAP, 2, 3, GAP, 4, GAP]


def test_rail_plan_all_hidden():
    assert layout.rail_plan([False, False]) == [0, 1]
    assert layout.rail_plan([]) == []


def test_spacing_scale_comes_from_the_design_tokens():
    from importlib import import_module
    spacing = import_module(f"{_PKG}.ui.styles.mockup_design").SPACING
    assert (layout.EDGE, layout.BLOCK, layout.GAP, layout.BAND) == (
        spacing['fm_edge'], spacing['fm_block'], spacing['fm_gap'], spacing['fm_band'])
    assert layout.SECTION_TAB_HEIGHT == layout.BAND
    assert layout.ROW_GAP == layout.FIELD_GAP == layout.GROUP_GAP == layout.RAIL_GAP == layout.GAP


def test_spacer_adjustments_account_for_earlier_moves():
    # Button 2 is already 4 px low once button 1 moves by +4: it needs nothing more.
    assert layout.spacer_adjustments([4, 4, 9]) == [4, 0, 5]
    assert layout.spacer_adjustments([0, -3]) == [0, -3]


def test_spacing_tokens_in_the_stylesheet():
    from importlib import import_module
    design = import_module(f"{_PKG}.ui.styles.mockup_design")
    band = design.SPACING['fm_band']
    out = design.apply_tokens("padding: {fm_band_padding} {fm_inset}; margin: {fm_gap} {fm_edge};", dark=True)
    assert out == f"padding: {band - 1}px {design.SPACING['fm_inset']}px; margin: " \
                  f"{design.SPACING['fm_gap']}px {design.SPACING['fm_edge']}px;"


def test_mockup_stylesheet_has_no_unknown_spacing_token():
    import re
    from importlib import import_module
    design = import_module(f"{_PKG}.ui.styles.mockup_design")
    qss = (_ROOT / "resources" / "styles" / "mockup.qss").read_text(encoding="utf-8")
    left = re.findall(r"\{fm_[a-z_]+\}", design.apply_tokens(qss, dark=False))
    assert left == []


def test_expanded_list_group_takes_the_free_height():
    assert layout.list_group_stretch(True) == (1, 0)
    assert layout.list_group_stretch(False) == (0, 1)

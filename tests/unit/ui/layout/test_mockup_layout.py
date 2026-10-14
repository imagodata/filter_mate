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
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.layout", _ROOT / "ui" / "layout")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.ui.layout.mockup_layout")


layout = _load()


def test_gap_spreads_the_free_height():
    # 6 buttons of 36 px in 300 px: 84 px free over 7 gaps.
    assert layout.rail_gap(300, [36] * 6) == 12


def test_hidden_buttons_do_not_count():
    assert layout.rail_gap(300, [36, 36, 0, 0, 36]) == (300 - 108) // 4


def test_gap_never_below_the_minimum():
    assert layout.rail_gap(100, [36] * 6) == 6
    assert layout.rail_gap(100, [], minimum=4) == 4

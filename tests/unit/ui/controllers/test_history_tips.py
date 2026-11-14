# -*- coding: utf-8 -*-
"""The tooltips of Undo and Redo of the action bar (ui/controllers/history_tips.py): one composition for the three
histories they walk."""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

from core.domain.history_timeline import KIND_AGENT, KIND_COVERAGE, KIND_VECTOR  # same strings in both packages

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_PKG = "fm_history_tips"


@pytest.fixture
def tips(monkeypatch):
    """The module alone, in a package of its own (the package ui.controllers imports Qt classes)."""
    for name, path in ((_PKG, None), (f"{_PKG}.ui", None), (f"{_PKG}.ui.controllers", None),
                       (f"{_PKG}.core", _ROOT / "core")):
        package = types.ModuleType(name)
        package.__path__ = [str(path)] if path else []
        monkeypatch.setitem(sys.modules, name, package)
    spec = importlib.util.spec_from_file_location(f"{_PKG}.ui.controllers.history_tips",
                                                  _ROOT / "ui" / "controllers" / "history_tips.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_tr", lambda text: text)
    return module


def test_undo_says_what_it_undoes_from_which_history_and_how_far(tips):
    assert tips.button_tip(True, 'Filter: "type" = 1', KIND_VECTOR, 3).split("\n") == [
        'Undo: Filter: "type" = 1', "History: vector filters of the dock", "Steps to undo: 3",
        "Right-click: the history of the project"]
    assert tips.button_tip(False, "Clip", KIND_COVERAGE, 1, "DEM").split("\n")[:3] == [
        "Redo: Clip", "History: raster / point cloud filters of DEM", "Steps to redo: 1"]


def test_nothing_to_do_still_names_the_history_and_the_right_click(tips):
    assert tips.button_tip(True, "", KIND_AGENT, 4).split("\n") == [
        "Nothing to undo.", "History: turns of the agent", "Right-click: the history of the project"]
    # Another section open: no history walked.
    assert tips.button_tip(False).split("\n") == ["Nothing to redo.", "Right-click: the history of the project"]
    assert tips.history_name(KIND_COVERAGE) == "raster / point cloud filters" and tips.history_name("") == ""


def test_a_long_request_is_cut_on_one_line(tips):
    first = tips.button_tip(True, "keep\n  the " + "x" * 200, KIND_AGENT, 1).split("\n")[0]
    assert first.startswith("Undo: keep the x") and first.endswith("…") and len(first) == len("Undo: ") + 80

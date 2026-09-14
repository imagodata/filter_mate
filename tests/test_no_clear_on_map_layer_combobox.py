# -*- coding: utf-8 -*-
"""
2026-09-14: QComboBox.clear() on the QgsMapLayerComboBox of the filtering tab
empties its proxy model for good: after every project switch with the panel
open the layer combo showed 0 entries (37 at the first load) even though the
layers were registered. core/services/layer_lifecycle_service.py already says
"do NOT call clear()"; this test makes the rule hold for the whole plugin.
Reset the widget with setLayer(None) instead.
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {
    "tests", ".git", "__pycache__",
    "_bmad", "_bmad-output", "website", "docs", "knowledge", "dist", "build", "scripts",
}
MAP_LAYER_COMBOBOXES = {"comboBox_filtering_current_layer"}


def _plugin_python_files():
    for path in PLUGIN_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PLUGIN_ROOT).parts):
            continue
        yield path


def _clear_calls_on_map_layer_combobox(tree):
    """Line numbers of ``<...>.comboBox_filtering_current_layer.clear()`` calls."""
    hits = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "clear":
            continue
        owner = node.func.value
        if isinstance(owner, ast.Attribute) and owner.attr in MAP_LAYER_COMBOBOXES:
            hits.append(node.lineno)
    return hits


@pytest.mark.unit
def test_no_clear_on_the_current_layer_map_combobox():
    offenders = []
    for path in _plugin_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno in _clear_calls_on_map_layer_combobox(tree):
            offenders.append(f"{path.relative_to(PLUGIN_ROOT)}:{lineno}")
    assert offenders == [], (
        "QgsMapLayerComboBox.clear() breaks the layer model; reset with setLayer(None): "
        + ", ".join(offenders)
    )

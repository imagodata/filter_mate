# -*- coding: utf-8 -*-
"""
2026-09-14: ``store.layersAdded.disconnect()`` without a slot removes EVERY
receiver of a QGIS-owned signal, QGIS's own included (QgsProject forwards its
layer store's signals to QgsProject.layersAdded, which the map layer combo
boxes listen to). From the first project switch on, the filtering-tab layer
combo never learnt about new layers again. Disconnect the plugin's own slot.
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {
    "tests", ".git", "__pycache__",
    "_bmad", "_bmad-output", "website", "docs", "knowledge", "dist", "build", "scripts",
}
# Signals owned by QGIS objects (QgsProject, QgsMapLayerStore, QgisInterface,
# QgsMapLayer, QgsMapCanvas): other receivers exist that the plugin must keep.
QGIS_SIGNALS = {
    "layersAdded", "layerWasAdded", "layersWillBeRemoved", "layerWillBeRemoved",
    "layersRemoved", "layerRemoved", "allLayersRemoved", "fileNameChanged",
    "readProject", "writeProject", "projectRead", "newProjectCreated", "cleared",
    "selectionChanged", "willBeDeleted", "subsetStringChanged", "extentsChanged",
    "renderComplete", "mapCanvasRefreshed", "layerTreeChanged", "layersChanged",
}


def _plugin_python_files():
    for path in PLUGIN_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PLUGIN_ROOT).parts):
            continue
        yield path


def _bare_disconnects_on_qgis_signals(tree):
    hits = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "disconnect" or node.args or node.keywords:
            continue
        signal = node.func.value
        if isinstance(signal, ast.Attribute) and signal.attr in QGIS_SIGNALS:
            hits.append((node.lineno, signal.attr))
    return hits


@pytest.mark.unit
def test_no_bare_disconnect_on_qgis_owned_signals():
    offenders = []
    for path in _plugin_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno, signal in _bare_disconnects_on_qgis_signals(tree):
            offenders.append(f"{path.relative_to(PLUGIN_ROOT)}:{lineno} ({signal})")
    assert offenders == [], (
        "disconnect() without a slot drops QGIS's own receivers too; pass the plugin's slot: "
        + ", ".join(offenders)
    )

# -*- coding: utf-8 -*-
"""
Qt6 / QGIS 4 guard (2026-09-14). The plugin repository check of
plugins.qgis.org flags unscoped enum members (``QgsFeatureRequest.NoGeometry``
instead of ``QgsFeatureRequest.Flag.NoGeometry``); PyQt6 removed the unscoped
spellings altogether. This test fails on the spellings that check reports,
so the CI catches them before an upload does.
"""
import sys
import os
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
# The detector (member table, alias resolution) is shared with scripts/publish_qgis.py, which runs it
# on the files of the release archive.
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
import qt_enum_scan  # noqa: E402

EXCLUDED_DIRS = {
    "tests", ".git", "__pycache__",
    "_bmad", "_bmad-output", "website", "docs", "knowledge", "dist", "build", "scripts",
    ".claude", ".agents", ".codex", ".venv", "venv",
}


def _plugin_python_files():
    for folder, directories, files in os.walk(PLUGIN_ROOT):
        directories[:] = [name for name in directories if name not in EXCLUDED_DIRS]
        for name in files:
            if name.endswith('.py'):
                yield Path(folder) / name


def _tmp_offences(source):
    return [what for _, what in qt_enum_scan.scan_source(source)]


@pytest.mark.unit
def test_detector_resolves_import_aliases_and_qcolor():
    assert _tmp_offences(
        "from qgis.PyQt.QtWidgets import QSizePolicy as SP\nx = SP.Fixed\n") == ["QSizePolicy.Fixed"]
    assert _tmp_offences("SP = QtWidgets.QSizePolicy\nx = SP.Expanding") == ["QSizePolicy.Expanding"]
    assert _tmp_offences("x = QtWidgets.QSizePolicy.Preferred") == ["QSizePolicy.Preferred"]
    assert _tmp_offences("c.name(QtGui.QColor.HexArgb)") == ["QColor.HexArgb"]
    assert _tmp_offences("c.name(QColor.NameFormat.HexArgb)") == []
    assert _tmp_offences("x = SP.Policy.Fixed") == []


@pytest.mark.unit
def test_no_unscoped_qt_or_qgis_enum_members():
    offenders = []
    for path in _plugin_python_files():
        for lineno, what in qt_enum_scan.scan_source(path.read_text(encoding="utf-8"), str(path)):
            offenders.append(f"{path.relative_to(PLUGIN_ROOT)}:{lineno} {what}")
    assert offenders == [], (
        "Unscoped enum members are rejected by the QGIS plugin repository Qt6 check; "
        "use the scoped form (Qt.ConnectionType.QueuedConnection, QgsWkbTypes.Type.Point, "
        "QMessageBox.StandardButton.Yes, ...):\n" + "\n".join(offenders)
    )

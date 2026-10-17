# -*- coding: utf-8 -*-
"""
Qt6 / QGIS 4 guard (2026-09-14). The plugin repository check of
plugins.qgis.org flags unscoped enum members (``QgsFeatureRequest.NoGeometry``
instead of ``QgsFeatureRequest.Flag.NoGeometry``); PyQt6 removed the unscoped
spellings altogether. This test fails on the spellings that check reports,
so the CI catches them before an upload does.
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {
    "tests", ".git", "__pycache__",
    "_bmad", "_bmad-output", "website", "docs", "knowledge", "dist", "build", "scripts",
}

# owner name -> members that must be reached through their scoped enum
UNSCOPED_MEMBERS = {
    "Qt": {
        "QueuedConnection", "DirectConnection", "AutoConnection", "BlockingQueuedConnection",
        "UserRole", "DisplayRole", "EditRole", "ToolTipRole", "DecorationRole", "CheckStateRole",
        "Checked", "Unchecked", "PartiallyChecked",
        "WaitCursor", "BusyCursor", "ArrowCursor", "PointingHandCursor",
        "AlignLeft", "AlignRight", "AlignHCenter", "AlignTop", "AlignBottom", "AlignVCenter", "AlignCenter",
        "LeftButton", "RightButton", "MiddleButton", "Horizontal", "Vertical",
        "StrongFocus", "NoFocus", "ClickFocus", "TabFocus", "CustomContextMenu", "NoContextMenu",
        "KeepAspectRatio", "IgnoreAspectRatio", "SmoothTransformation", "FastTransformation",
        "ElideRight", "ElideLeft", "ElideNone", "RichText", "PlainText",
        "ItemIsEnabled", "ItemIsSelectable", "ItemIsUserCheckable", "ItemIsEditable",
        "MatchExactly", "MatchContains", "MatchFixedString", "MatchStartsWith",
        "WA_DeleteOnClose", "WA_TransparentForMouseEvents", "WA_StyledBackground",
        "ScrollBarAlwaysOff", "ScrollBarAlwaysOn", "ScrollBarAsNeeded",
        "black", "white", "red", "blue", "green", "gray", "transparent", "darkGray", "lightGray",
        "Window", "Dialog", "Tool", "Popup", "FramelessWindowHint", "WindowStaysOnTopHint",
        "Key_Escape", "Key_Return", "Key_Enter", "Key_Delete", "Key_Backspace", "Key_Tab", "Key_Space",
    },
    "QgsFeatureRequest": {"NoGeometry", "ExactIntersect", "NoFlags", "SubsetOfAttributes", "EmbeddedSymbols"},
    "QgsWkbTypes": {
        "Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon",
        "NoGeometry", "Unknown", "GeometryCollection",
        "PointGeometry", "LineGeometry", "PolygonGeometry", "NullGeometry", "UnknownGeometry",
    },
    "QMessageBox": {"Yes", "No", "Ok", "Cancel", "Warning", "Critical", "Information", "Question", "Save", "Discard"},
    "QDialog": {"Accepted", "Rejected"},
    "QSizePolicy": {"Expanding", "Fixed", "Minimum", "Maximum", "Preferred", "MinimumExpanding", "Ignored"},
    "QHeaderView": {"Stretch", "ResizeToContents", "Interactive", "Fixed"},
    "QAbstractItemView": {"SingleSelection", "ExtendedSelection", "MultiSelection", "NoSelection",
                          "SelectRows", "SelectItems", "NoEditTriggers", "DoubleClicked"},
    "QFrame": {"StyledPanel", "NoFrame", "Box", "Panel", "HLine", "VLine", "Sunken", "Raised", "Plain"},
    "QLineEdit": {"Normal", "Password", "NoEcho"},
    "QFont": {"Bold", "Normal", "Light", "DemiBold"},
    "QImage": {"Format_ARGB32", "Format_RGB32", "Format_RGBA8888"},
    "QPainter": {"Antialiasing", "SmoothPixmapTransform"},
    "QTabWidget": {"North", "South", "Rounded", "Triangular"},
    "QComboBox": {"NoInsert", "InsertAtBottom", "AdjustToContents"},
    "QLayout": {"SetFixedSize", "SetMinimumSize", "SetDefaultConstraint"},
    # QColor.name(QColor.HexArgb) raised AttributeError in QGIS 4 (json view delegate, October 2026)
    "QColor": {"HexRgb", "HexArgb", "Rgb", "Hsv", "Hsl", "Cmyk", "ExtendedRgb"},
}
REMOVED_METHODS = {"exec_"}


def _plugin_python_files():
    for path in PLUGIN_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PLUGIN_ROOT).parts):
            continue
        yield path


def _import_aliases(tree):
    """Map local names to the Qt / QGIS class they were imported as.

    ``from qgis.PyQt.QtWidgets import QSizePolicy as SP`` makes ``SP.Fixed`` an
    offence even though ``SP`` is not in ``UNSCOPED_MEMBERS``. Plain module
    aliases (``QtWidgets``) need no entry: the class name is then the attribute
    that precedes the member (``QtWidgets.QSizePolicy.Fixed``).
    """
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.asname and alias.name in UNSCOPED_MEMBERS:
                    aliases[alias.asname] = alias.name
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            target = value.id if isinstance(value, ast.Name) else (value.attr if isinstance(value, ast.Attribute) else None)
            if target in UNSCOPED_MEMBERS:
                aliases[node.targets[0].id] = target  # SP = QSizePolicy
    return aliases


def _owner_name(owner, aliases):
    if isinstance(owner, ast.Name):
        return aliases.get(owner.id, owner.id)
    if isinstance(owner, ast.Attribute):
        return owner.attr
    return None


def _offences(tree):
    aliases = _import_aliases(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            owner_name = _owner_name(node.value, aliases)
            if owner_name in UNSCOPED_MEMBERS and node.attr in UNSCOPED_MEMBERS[owner_name]:
                yield node.lineno, f"{owner_name}.{node.attr}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in REMOVED_METHODS:
            yield node.lineno, f".{node.func.attr}()"


def _tmp_offences(source):
    return [what for _, what in _offences(ast.parse(source))]


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
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno, what in _offences(tree):
            offenders.append(f"{path.relative_to(PLUGIN_ROOT)}:{lineno} {what}")
    assert offenders == [], (
        "Unscoped enum members are rejected by the QGIS plugin repository Qt6 check; "
        "use the scoped form (Qt.ConnectionType.QueuedConnection, QgsWkbTypes.Type.Point, "
        "QMessageBox.StandardButton.Yes, ...):\n" + "\n".join(offenders)
    )

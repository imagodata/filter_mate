# -*- coding: utf-8 -*-
"""
Unscoped Qt / QGIS enum detector (single source of truth).

Used by ``tests/test_no_unscoped_qt_enums.py`` (on the source tree) and by
``scripts/publish_qgis.py`` (on the Python files of the release archive).

PyQt6 (QGIS 4) removed the unscoped spellings (``QgsFeatureRequest.NoGeometry``
instead of ``QgsFeatureRequest.Flag.NoGeometry``) and the plugin repository
check of plugins.qgis.org flags them. Import aliases are resolved
(``from qgis.PyQt.QtWidgets import QSizePolicy as SP`` then ``SP.Fixed``,
``SP = QtWidgets.QSizePolicy``).
"""
import ast

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


def import_aliases(tree):
    """Map local names to the Qt / QGIS class they were imported (or assigned) as.

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


def owner_name(owner, aliases):
    if isinstance(owner, ast.Name):
        return aliases.get(owner.id, owner.id)
    if isinstance(owner, ast.Attribute):
        return owner.attr
    return None


def find_offences(tree):
    """Yield ``(lineno, spelling)`` for every unscoped member / removed method in the parsed ``tree``."""
    aliases = import_aliases(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            owner = owner_name(node.value, aliases)
            if owner in UNSCOPED_MEMBERS and node.attr in UNSCOPED_MEMBERS[owner]:
                yield node.lineno, f"{owner}.{node.attr}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in REMOVED_METHODS:
            yield node.lineno, f".{node.func.attr}()"


def scan_source(source, filename="<string>"):
    """``[(lineno, spelling)]`` for the Python ``source`` text."""
    return list(find_offences(ast.parse(source, filename=filename)))

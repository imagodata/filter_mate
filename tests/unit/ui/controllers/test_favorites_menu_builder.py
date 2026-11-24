# -*- coding: utf-8 -*-
"""The favorites (star) menu on real Qt widgets (PyQt5, offscreen) with a stand-in controller.

The module is loaded under a private package name with ``qgis.PyQt`` pointing at PyQt5 for the import only
(the root conftest mocks Qt for the other tests). Skipped without PyQt5.
"""
import importlib
import os
import pathlib
import sys
import types
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui  # noqa: E402

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "_fm_menu_qt_test"


def _load():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt_names = ("qgis.PyQt", "qgis.PyQt.QtCore", "qgis.PyQt.QtGui", "qgis.PyQt.QtWidgets")
    saved = {name: sys.modules.get(name) for name in qt_names}
    sys.modules.update({"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore,
                        "qgis.PyQt.QtGui": QtGui, "qgis.PyQt.QtWidgets": QtWidgets})
    try:
        for suffix, path in (("", ""), (".ui", "ui"), (".ui.controllers", "ui/controllers"),
                             (".ui.styles", "ui/styles")):
            package = types.ModuleType(_PKG + suffix)
            package.__path__ = [str(_ROOT / path)]
            package.__package__ = _PKG + suffix
            sys.modules[_PKG + suffix] = package
        builder = importlib.import_module(f"{_PKG}.ui.controllers.favorites_menu_builder")
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return app, builder


_APP, builder_module = _load()


def _controller():
    return SimpleNamespace(
        tr=lambda text: text,
        get_all_favorites=lambda: [],
        get_current_filter_expression=lambda: '"a" = 1',
        is_sharing_extension_active=lambda: False,
        get_global_favorites=lambda: [],
        extension_bridge=None,
    )


def _all_actions(menu):
    for action in menu.actions():
        yield action
        if action.menu() is not None:
            yield from _all_actions(action.menu())


def test_menu_has_no_project_backup_entries():
    menu = builder_module.FavoritesMenuBuilder.build(_controller(), None)

    data = [action.data() for action in _all_actions(menu)]
    texts = [action.text() for action in _all_actions(menu)]

    assert "__BACKUP_TO_PROJECT__" not in data
    assert "__RESTORE_FROM_PROJECT__" not in data
    assert not any("Save to project" in text or "Restore from project" in text for text in texts)
    # the rest of the maintenance sub-menu is still there
    assert builder_module.ACTION_CLEANUP_ORPHANS in data
    assert builder_module.ACTION_SHOW_STATS in data

# -*- coding: utf-8 -*-
"""The favorites manager dialog on real Qt widgets (PyQt5, offscreen) with a stand-in service.

The module is loaded under a private package name with ``qgis.PyQt`` pointing at PyQt5 for the import only
(the root conftest mocks Qt for the other tests). Skipped without PyQt5.
"""
import importlib
import os
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui  # noqa: E402

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "_fm_dialog_qt_test"


def _load():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt_names = ("qgis.PyQt", "qgis.PyQt.QtCore", "qgis.PyQt.QtGui", "qgis.PyQt.QtWidgets")
    saved = {name: sys.modules.get(name) for name in qt_names}
    sys.modules.update({"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore,
                        "qgis.PyQt.QtGui": QtGui, "qgis.PyQt.QtWidgets": QtWidgets})
    try:
        for suffix, path in (("", ""), (".ui", "ui"), (".ui.dialogs", "ui/dialogs"), (".ui.styles", "ui/styles"),
                             (".core", "core"), (".core.domain", "core/domain")):
            package = types.ModuleType(_PKG + suffix)
            package.__path__ = [str(_ROOT / path)]
            package.__package__ = _PKG + suffix
            sys.modules[_PKG + suffix] = package
        dialog = importlib.import_module(f"{_PKG}.ui.dialogs.favorites_manager")
        domain = importlib.import_module(f"{_PKG}.core.domain.favorites_manager")
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return app, dialog, domain


_APP, dialog_module, domain = _load()


class _Service(QtCore.QObject):
    """The part of FavoritesService the dialog reads and writes."""

    favorites_changed = QtCore.pyqtSignal()

    def __init__(self, favorites, global_favorites=()):
        super().__init__()
        self.favorites = {f.id: f for f in favorites}
        self.global_favorites = list(global_favorites)
        self._project_uuid = "project-1"

    count = property(lambda self: len(self.favorites))

    def get_all_favorites(self):
        return list(self.favorites.values())

    def get_global_favorites(self):
        return list(self.global_favorites)

    def get_favorite(self, fav_id):
        return self.favorites.get(fav_id)

    def get_current_user(self):
        return "alice"

    def update_favorite(self, fav_id, **fields):
        for key, value in fields.items():
            setattr(self.favorites[fav_id], key, value)
        return True

    def save(self):
        return True


def _favorite(name, **fields):
    return domain.FilterFavorite(name=name, expression='"a" = 1', layer_name="roads", owner="alice", **fields)


def _texts(dialog):
    return [label.text() for label in dialog.findChildren(QtWidgets.QLabel)]


def test_after_save_the_summary_shows_the_saved_tags():
    favorite = _favorite("Roads", tags=["old"])
    dialog = dialog_module.FavoritesManagerDialog(_Service([favorite]))
    assert "old" in _texts(dialog)

    dialog._tags_edit.setText("new, fresh")
    dialog._on_save()

    texts = _texts(dialog)
    assert "new, fresh" in texts
    assert "old" not in texts


def test_a_global_favorite_is_listed_read_only():
    project, global_favorite = _favorite("Roads"), _favorite("Roads (Global)")
    dialog = dialog_module.FavoritesManagerDialog(_Service([project], [global_favorite]))

    assert dialog._list_widget.count() == 2
    dialog._select_favorite(global_favorite.id)

    assert not dialog._name_edit.isEnabled()
    assert not dialog._save_btn.isEnabled()
    assert dialog._delete_btn.isEnabled()


def test_applying_a_global_favorite_emits_its_own_signal():
    project, global_favorite = _favorite("Roads"), _favorite("Roads (Global)")
    dialog = dialog_module.FavoritesManagerDialog(_Service([project], [global_favorite]))
    applied = []
    dialog.favoriteApplied.connect(lambda fav_id: applied.append(("project", fav_id)))
    dialog.globalFavoriteApplied.connect(lambda fav_id: applied.append(("global", fav_id)))

    dialog._on_item_double_clicked(dialog._list_widget.item(1))  # "Roads (Global)" after "Roads"

    assert applied == [("global", global_favorite.id)]

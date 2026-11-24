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
from unittest import mock as unittest_mock

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

    def remove_favorite(self, fav_id):
        return self.favorites.pop(fav_id, None) is not None

    def remove_global_favorite(self, fav_id):
        before = len(self.global_favorites)
        self.global_favorites = [f for f in self.global_favorites if f.id != fav_id]
        return len(self.global_favorites) < before

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


@pytest.fixture
def warnings(monkeypatch):
    """The warnings the dialog pushes to the message bar."""
    shown = []
    monkeypatch.setattr(dialog_module.FavoritesManagerDialog, "_show_warning", lambda self, message: shown.append(message))
    return shown


def test_saving_an_empty_name_is_refused_and_keeps_the_field(warnings):
    favorite = _favorite("Roads")
    service = _Service([favorite])
    dialog = dialog_module.FavoritesManagerDialog(service)

    dialog._name_edit.setText("   ")
    dialog._on_save()

    assert warnings == ["The name cannot be empty."]
    assert service.favorites[favorite.id].name == "Roads"
    assert dialog._name_edit.text() == "   "


def test_saving_a_name_another_favorite_has_is_refused_and_keeps_the_field(warnings):
    roads, parks = _favorite("Roads"), _favorite("Parks")
    service = _Service([roads, parks])
    dialog = dialog_module.FavoritesManagerDialog(service)
    dialog._select_favorite(parks.id)

    dialog._name_edit.setText("Roads")
    dialog._on_save()

    assert warnings == ["Another favorite is already named 'Roads'."]
    assert service.favorites[parks.id].name == "Parks"
    assert dialog._name_edit.text() == "Roads"


def test_saving_the_same_name_again_is_not_a_duplicate(warnings):
    favorite = _favorite("Roads")
    dialog = dialog_module.FavoritesManagerDialog(_Service([favorite]))

    dialog._description_edit.setPlainText("main roads")
    dialog._on_save()

    assert warnings == []


def test_a_global_favorite_named_like_a_project_one_is_not_a_duplicate(warnings):
    project, global_favorite = _favorite("Parks"), _favorite("Roads")
    service = _Service([project], [global_favorite])
    dialog = dialog_module.FavoritesManagerDialog(service)

    dialog._name_edit.setText("Roads")
    dialog._on_save()

    assert warnings == []
    assert service.favorites[project.id].name == "Roads"


def _question_texts(monkeypatch, answer):
    asked = []

    def question(parent, title, text, *args):
        asked.append(text)
        return answer

    monkeypatch.setattr(dialog_module.QMessageBox, "question", staticmethod(question))
    return asked


def test_deleting_a_project_favorite_warns_it_is_removed_for_everyone(monkeypatch):
    favorite = _favorite("Roads")
    dialog = dialog_module.FavoritesManagerDialog(_Service([favorite]))
    asked = _question_texts(monkeypatch, dialog_module.QMessageBox.StandardButton.No)

    dialog._on_delete()

    assert len(asked) == 1
    assert "Delete favorite 'Roads'?" in asked[0]
    assert "It is removed for everyone who opens this project." in asked[0]


def test_deleting_a_global_favorite_does_not_mention_the_project(monkeypatch):
    project, global_favorite = _favorite("Roads"), _favorite("Roads (Global)")
    service = _Service([project], [global_favorite])
    dialog = dialog_module.FavoritesManagerDialog(service)
    dialog._select_favorite(global_favorite.id)
    asked = _question_texts(monkeypatch, dialog_module.QMessageBox.StandardButton.Yes)

    dialog._on_delete()

    assert len(asked) == 1
    assert "everyone" not in asked[0]
    assert service.global_favorites == []


@pytest.mark.parametrize("glyph, dark", [("radio_dot_dark.svg", True), ("radio_dot_white.svg", False)])
def test_the_dialog_takes_the_theme_drawn_on_its_dock(glyph, dark):
    dock = QtWidgets.QWidget()
    dock.setStyleSheet("QRadioButton::indicator:checked { image: url(:/%s); }" % glyph)
    dialog = dialog_module.FavoritesManagerDialog(_Service([_favorite("Roads")]), dock)

    assert dialog._dark is dark


def test_a_refused_rename_is_shown_inside_the_dialog_not_on_the_main_message_bar():
    """The main window's message bar is behind a modal dialog: the dialog has its own."""
    dialog = dialog_module.FavoritesManagerDialog(_Service([_favorite("Roads")]))
    assert dialog._message_bar.isHidden()

    dialog._name_edit.setText("")
    dialog._on_save()

    assert not dialog._message_bar.isHidden()
    assert dialog._message_bar.text() == "The name cannot be empty."
    assert dialog.layout().indexOf(dialog._message_bar) == 0


def test_a_failure_is_shown_inside_the_dialog():
    dialog = dialog_module.FavoritesManagerDialog(_Service([_favorite("Roads")]))

    dialog._show_error("Could not duplicate 'Roads'.")

    assert dialog._message_bar.text() == "Could not duplicate 'Roads'."


@pytest.mark.parametrize("close", ["accept", "reject"])
def test_a_closed_dialog_no_longer_follows_the_service(close):
    service = _Service([_favorite("Roads")])
    dialog = dialog_module.FavoritesManagerDialog(service)
    refreshed = []
    dialog.refresh = lambda: refreshed.append(1)
    service.favorites_changed.emit()
    assert refreshed == [1]

    getattr(dialog, close)()
    service.favorites_changed.emit()

    assert refreshed == [1]


def test_the_context_menu_is_deleted_after_it_closes(monkeypatch):
    dialog = dialog_module.FavoritesManagerDialog(_Service([_favorite("Roads")]))
    menu = unittest_mock.MagicMock()
    monkeypatch.setattr(dialog, "_build_context_menu", lambda fav_id: menu)
    item = dialog._list_widget.item(0)

    dialog._on_list_context_menu(dialog._list_widget.visualItemRect(item).center())

    menu.exec.assert_called_once()
    menu.deleteLater.assert_called_once()


def _scope_fixture():
    """Project: mine, Bob's, shared (no owner); global: mine, Bob's."""
    project_mine = _favorite("Project mine")
    project_bob = _favorite("Project Bob's")
    project_bob.owner = "bob"
    project_ownerless = _favorite("Project ownerless")
    project_ownerless.owner = None
    global_mine = _favorite("Global mine")
    global_bob = _favorite("Global Bob's")
    global_bob.owner = "bob"
    service = _Service([project_mine, project_bob, project_ownerless], [global_mine, global_bob])
    return dialog_module.FavoritesManagerDialog(service)


@pytest.mark.parametrize("key, names", [
    ("all", {"Project mine", "Project Bob's", "Project ownerless", "Global mine", "Global Bob's"}),
    ("project_shared", {"Project mine", "Project Bob's", "Project ownerless"}),
    ("global_shared", {"Global mine", "Global Bob's"}),
    ("project_mine", {"Project mine"}),
    ("global_mine", {"Global mine"}),
])
def test_the_scope_filter_follows_where_a_favorite_is_kept_and_who_owns_it(key, names):
    dialog = _scope_fixture()

    shown = dialog._apply_scope_filter(dialog._all_favorites, key)

    assert {fav.name for fav in shown} == names


def test_a_global_favorite_alone_is_listed_when_the_project_has_none():
    dialog = dialog_module.FavoritesManagerDialog(_Service([], [_favorite("Roads (Global)")]))

    assert dialog._list_widget.count() == 1

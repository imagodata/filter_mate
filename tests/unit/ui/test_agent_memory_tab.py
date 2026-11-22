# -*- coding: utf-8 -*-
"""The Memory tab of the agent settings, on real Qt widgets (PyQt5, offscreen): the notes kept from one project to the
next are written, corrected and removed there, and Save gets the changes to make on the file.

Loaded as tests/unit/ui/test_agent_provider_tab.py loads the dialog. Skipped without PyQt5.
"""
import importlib
import os
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui  # noqa: E402

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_agent_memory_tab_test"


def _load():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt = {"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore, "qgis.PyQt.QtGui": QtGui,
          "qgis.PyQt.QtWidgets": QtWidgets, "qgis.PyQt.QtNetwork": MagicMock(), "qgis.PyQt.QtXml": MagicMock()}
    if "qgis.core" not in sys.modules:
        qt["qgis.core"] = MagicMock()
    saved = {name: sys.modules.get(name) for name in qt}
    sys.modules.update(qt)  # for the imports only: the modules loaded keep the real Qt classes
    try:
        for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                           (".adapters", _ROOT / "adapters"), (".adapters.agent", _ROOT / "adapters" / "agent"),
                           (".ui", _ROOT / "ui"), (".ui.widgets", _ROOT / "ui" / "widgets"),
                           (".ui.styles", _ROOT / "ui" / "styles")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
        return (app, importlib.import_module(f"{_PKG}.ui.widgets.agent_panel"),
                importlib.import_module(f"{_PKG}.adapters.agent.settings"),
                importlib.import_module(f"{_PKG}.core.agent.memory"))
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


_APP, panel_module, settings_module, memory = _load()
ROADS, TOWNS = "ogr::troncons", "ogr::communes"
SOURCES = [(TOWNS, "Communes"), ("", "scratch"), (ROADS, "Tronçons"), (ROADS, "Tronçons (copie)")]


def _kept():
    kept, _note = memory.added(memory.Memory(), "MRO = zone de mutualisation")
    kept, _note = memory.added(kept, "aérien = type_infra 'AER'", memory.SCOPE_SOURCE, ROADS, "Tronçons",
                               with_values=True)
    kept, _note = memory.added(kept, "idu est la clé", memory.SCOPE_SOURCE, "ogr::parcelles", "Parcelles")
    return kept


def _dialog(kept="default", error="", **values):
    settings = settings_module.AgentSettings(**values)
    return panel_module.AgentSettingsDialog(
        settings, settings_module.target_of, None, memory=_kept() if kept == "default" else kept, memory_error=error,
        memory_sources=SOURCES, memory_active=ROADS, memory_file="/profile/FilterMate/agent_memory.json")


def _tree(dialog):
    """The tree as (group, [notes])."""
    root = dialog.memory_notes.invisibleRootItem()
    return [(root.child(rank).text(0), [root.child(rank).child(row).text(0) for row in range(root.child(rank).childCount())])
            for rank in range(root.childCount())]


def _note_item(dialog, text):
    root = dialog.memory_notes.invisibleRootItem()
    for rank in range(root.childCount()):
        for row in range(root.child(rank).childCount()):
            if root.child(rank).child(row).text(0) == text:
                return root.child(rank).child(row)
    raise AssertionError(text)


def test_the_tab_lists_the_notes_under_their_place_and_says_what_goes():
    dialog = _dialog()
    assert dialog.tab_title("memory") == "Memory"
    assert dialog.memory_enabled.isChecked()
    assert _tree(dialog) == [("Every project", ["MRO = zone de mutualisation"]),
                             ("Tronçons (ogr::troncons)", ["aérien = type_infra 'AER'"]),
                             ("Parcelles (ogr::parcelles)", ["idu est la clé"])]
    # the places a note can be written for: every project, and each source of the open project once
    place = dialog.memory_place
    assert [(place.itemText(rank), place.itemData(rank)) for rank in range(place.count())] == [
        ("Every project", ""), ("Communes", TOWNS), ("Tronçons", ROADS)]
    assert dialog.memory_status.text() == "Sent with this project: 2 of 3 notes."  # the parcels are not in this project
    assert dialog.memory_changes() == []
    dialog.deleteLater()


def test_every_project_comes_first_whatever_the_file_starts_with():
    kept, _note = memory.added(memory.Memory(), "idu est la clé", memory.SCOPE_SOURCE, "ogr::parcelles", "Parcelles")
    kept, _note = memory.added(kept, "MRO = zone de mutualisation")
    dialog = _dialog(kept)
    assert [group for group, _notes in _tree(dialog)] == ["Every project", "Parcelles (ogr::parcelles)"]
    dialog.memory_notes.setCurrentItem(_note_item(dialog, "idu est la clé"))
    dialog.memory_remove.click()  # the row removed is the one chosen, not the one at its place in the tree
    assert _tree(dialog) == [("Every project", ["MRO = zone de mutualisation"])]
    assert dialog.memory_changes() == [(memory.REMOVE, "m1")]
    dialog.deleteLater()


def test_enter_in_the_line_of_a_note_adds_it_and_does_not_save_the_dialog(monkeypatch):
    """A QLineEdit lets Enter through to its dialog, which presses Save: the dialog closed with every setting."""
    dialog = _dialog()
    dialog.show()
    dialog.select_tab("memory")
    monkeypatch.setattr(dialog.memory_text, "hasFocus", lambda: True)  # no window manager gives it here
    dialog.memory_text.setText("réponds en mètres")
    QtTest = pytest.importorskip("PyQt5.QtTest")
    QtTest.QTest.keyClick(dialog.memory_text, QtCore.Qt.Key_Return)
    assert _tree(dialog)[0][1] == ["MRO = zone de mutualisation", "réponds en mètres"]
    assert dialog.isVisible() and dialog.result() != QtWidgets.QDialog.Accepted
    QtTest.QTest.keyClick(dialog.memory_text, QtCore.Qt.Key_Enter)  # an empty line: nothing added, still open
    assert dialog.isVisible() and len(_tree(dialog)[0][1]) == 2
    dialog.reject()
    dialog.deleteLater()


def test_unticked_the_tab_does_not_say_notes_are_sent():
    dialog = _dialog()
    assert not dialog.memory_status.isHidden()
    dialog.memory_enabled.setChecked(False)
    assert dialog.memory_status.isHidden()
    dialog.memory_enabled.setChecked(True)
    assert not dialog.memory_status.isHidden()
    dialog.deleteLater()


def test_values_not_shared_hold_a_note_back_and_the_tab_says_so():
    dialog = _dialog(send_values=False)
    assert dialog.memory_status.text() == ("Sent with this project: 1 of 3 notes. 1 not sent: they hold attribute "
                                           "values, which you do not share.")
    dialog.send_values.setChecked(True)  # the Provider tab: the count follows
    assert dialog.memory_status.text() == "Sent with this project: 2 of 3 notes."
    dialog.deleteLater()


def test_a_note_is_added_once_for_the_place_chosen():
    dialog = _dialog()
    assert not dialog.memory_add.isEnabled()  # nothing typed
    dialog.memory_text.setText("  réponds   en mètres ")
    assert dialog.memory_add.isEnabled()
    dialog.memory_add.click()
    dialog.memory_place.setCurrentIndex(1)
    dialog.memory_text.setText("dept est un texte")
    dialog.memory_text.returnPressed.emit()
    dialog.memory_text.setText("DEPT est un texte")  # the same note at the same place
    dialog.memory_add.click()
    assert _tree(dialog)[0] == ("Every project", ["MRO = zone de mutualisation", "réponds en mètres"])
    assert _tree(dialog)[-1] == ("Communes (ogr::communes)", ["dept est un texte"])
    assert dialog.memory_text.text() == ""
    assert dialog.memory_changes() == [(memory.ADD, memory.SCOPE_USER, "", "", "réponds en mètres"),
                                       (memory.ADD, memory.SCOPE_SOURCE, TOWNS, "Communes", "dept est un texte")]
    assert dialog.memory_status.text() == "Sent with this project: 4 of 5 notes."
    # what Save gets is what the memory takes
    after = memory.applied(_kept(), dialog.memory_changes(), today="2026-11-22")
    assert [note.id for note in after.notes] == ["m1", "m2", "m3", "m4", "m5"]
    dialog.deleteLater()


def test_a_note_is_corrected_in_place_and_an_emptied_one_comes_back():
    dialog = _dialog()
    _note_item(dialog, "aérien = type_infra 'AER'").setText(0, " aérien =  type_infra 'AER' ou 'FAC' ")
    assert _tree(dialog)[1][1] == ["aérien = type_infra 'AER' ou 'FAC'"]
    assert dialog.memory_changes() == [(memory.EDIT, "m2", "aérien = type_infra 'AER' ou 'FAC'")]
    dialog.send_values.setChecked(False)
    assert dialog.memory_status.text() == "Sent with this project: 2 of 3 notes."  # the user's own words now
    _note_item(dialog, "MRO = zone de mutualisation").setText(0, "   ")
    assert _tree(dialog)[0][1] == ["MRO = zone de mutualisation"]
    _note_item(dialog, "idu est la clé").setText(0, "x" * 400)
    assert len(_tree(dialog)[2][1][0]) == 300
    dialog.memory_text.setText("POP = point de présence")
    dialog.memory_add.click()
    _note_item(dialog, "POP = point de présence").setText(0, "mro = ZONE de mutualisation")  # the note above it
    assert _tree(dialog)[0][1] == ["MRO = zone de mutualisation", "POP = point de présence"]
    dialog.deleteLater()


def test_a_note_is_removed_and_everything_can_be_forgotten(monkeypatch):
    dialog = _dialog()
    assert not dialog.memory_remove.isEnabled()
    dialog.memory_notes.setCurrentItem(dialog.memory_notes.invisibleRootItem().child(0))  # a title is not a note
    assert not dialog.memory_remove.isEnabled()
    dialog.memory_notes.setCurrentItem(_note_item(dialog, "idu est la clé"))
    assert dialog.memory_remove.isEnabled()
    dialog.memory_remove.click()
    assert [group for group, _notes in _tree(dialog)] == ["Every project", "Tronçons (ogr::troncons)"]
    assert dialog.memory_changes() == [(memory.REMOVE, "m3")]
    asked = []
    monkeypatch.setattr(panel_module, "ask_plain", lambda parent, title, text: asked.append(text) or False)
    dialog.memory_forget_all.click()
    assert len(asked) == 1 and len(_tree(dialog)) == 2  # no: nothing forgotten
    monkeypatch.setattr(panel_module, "ask_plain", lambda parent, title, text: True)
    dialog.memory_forget_all.click()
    assert _tree(dialog) == [] and not dialog.memory_forget_all.isEnabled()
    assert dialog.memory_changes() == [(memory.REMOVE, "m1"), (memory.REMOVE, "m2"), (memory.REMOVE, "m3")]
    assert dialog.memory_status.isHidden()  # nothing kept: nothing to say
    dialog.deleteLater()


def test_a_place_that_is_full_takes_no_more():
    kept = memory.Memory()
    for rank in range(memory.MAX_USER_NOTES):
        kept, _note = memory.added(kept, f"note {rank}")
    dialog = _dialog(kept)
    dialog.memory_text.setText("one more")
    assert not dialog.memory_add.isEnabled() and dialog.memory_add.toolTip() == "This list is full: remove a note first."
    dialog.memory_text.returnPressed.emit()
    assert dialog.memory_changes() == []
    dialog.memory_place.setCurrentIndex(2)  # a source has its own room
    assert dialog.memory_add.isEnabled() and dialog.memory_add.toolTip() == ""
    dialog.deleteLater()


def test_a_file_that_cannot_be_read_is_said_and_nothing_is_changed():
    dialog = _dialog(None, "it is not JSON (line 3)")
    assert "it is not JSON (line 3)" in dialog.memory_status.text()
    assert dialog.memory_status.textFormat() == QtCore.Qt.PlainText  # the reason is never read as rich text
    for widget in (dialog.memory_notes, dialog.memory_place, dialog.memory_text, dialog.memory_add,
                   dialog.memory_remove, dialog.memory_forget_all):
        assert not widget.isEnabled()
    assert dialog.memory_open.isEnabled()  # to correct it
    dialog.memory_text.setText("a")
    dialog.memory_text.returnPressed.emit()
    assert dialog.memory_changes() == []
    dialog.deleteLater()


def test_the_option_is_read_and_the_file_is_opened(monkeypatch, tmp_path):
    dialog = _dialog(memory=False)
    assert not dialog.memory_enabled.isChecked()
    dialog.select_tab("memory")
    assert dialog.tabs.currentWidget() is dialog._tab_pages["memory"]
    opened = []
    monkeypatch.setattr(panel_module.QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()))
    dialog.memory_open.click()
    assert opened == []  # neither the file nor its folder is there
    dialog._memory_file = str(tmp_path / "agent_memory.json")
    dialog.memory_open.click()
    assert opened == [str(tmp_path)]  # no note kept yet: its folder
    (tmp_path / "agent_memory.json").write_text("{}", encoding="utf-8")
    dialog.memory_open.click()
    assert opened[-1] == str(tmp_path / "agent_memory.json")
    dialog.deleteLater()

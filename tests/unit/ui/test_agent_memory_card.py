# -*- coding: utf-8 -*-
"""The card of a note the agent proposes to keep from one project to the next, or to forget (agent_thread.MemoryCard),
on real Qt widgets (PyQt5, offscreen). Loaded as tests/unit/ui/test_agent_memory_tab.py loads the dialog."""
import importlib
import os
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
except ImportError:
    QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
    from PyQt5 import QtCore, QtGui

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_agent_memory_card_test"


def _load():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt = {"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore, "qgis.PyQt.QtGui": QtGui,
          "qgis.PyQt.QtWidgets": QtWidgets, "qgis.PyQt.QtNetwork": MagicMock(), "qgis.PyQt.QtXml": MagicMock()}
    if "qgis.core" not in sys.modules:
        qt["qgis.core"] = MagicMock()
    saved = {name: sys.modules.get(name) for name in qt}
    sys.modules.update(qt)
    try:
        for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                           (".ui", _ROOT / "ui"), (".ui.widgets", _ROOT / "ui" / "widgets"),
                           (".ui.styles", _ROOT / "ui" / "styles")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
        return app, importlib.import_module(f"{_PKG}.ui.widgets.agent_thread")
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


_APP, thread = _load()
TEXTS = {"heading": "The agent proposes to keep a note", "undo": "Undo"}
BUTTONS = [("user", "Every project", True), ("source", "This source (Tronçons)", False),
           ("project", "This project only", True), ("decline", "Do not keep", True)]


def _card(editable=True, buttons=BUTTONS, notes=("This list is full", "")):
    card = thread.MemoryCard(TEXTS, "RD = route départementale", editable, buttons, notes)
    chosen, undone = [], []
    card.chosen.connect(lambda key, text: chosen.append((key, text)))
    card.undo_requested.connect(lambda: undone.append(True))
    return card, chosen, undone


def test_a_click_gives_the_place_and_the_text_as_corrected():
    card, chosen, _undone = _card()
    assert [button.text() for button in card.buttons.values()] == [label for _key, label, _on in BUTTONS]
    assert not card.buttons["source"].isEnabled()  # a list that is full
    assert [label.text() for label in card.notes] == ["This list is full"]  # an empty note is no line
    card.text.setText("  RD =  route   départementale (31) ")
    card.buttons["user"].click()
    assert chosen == [("user", "RD = route départementale (31)")]
    assert not card.done  # the controller writes, then freezes it


def test_finished_it_is_frozen_with_its_outcome_and_an_undo():
    card, chosen, undone = _card()
    card.finish("Kept for every project: RD", True)
    assert card.done and card.text.isReadOnly() and card.result.text() == "Kept for every project: RD"
    assert all(button.isHidden() for button in card.buttons.values()) and not card.undo_button.isHidden()
    card.buttons["decline"].click()  # hidden, and done: nothing more
    assert chosen == []
    card.undo_button.click()
    assert undone == [True]
    card.finish("Taken back: RD", False)
    assert card.undo_button.isHidden()


def test_a_card_to_forget_shows_the_text_as_it_is_and_an_empty_text_chooses_nothing():
    card, chosen, _undone = _card(editable=False, buttons=[("forget", "Forget", True), ("keep", "Keep", True)])
    assert card.text.isReadOnly()
    card.buttons["forget"].click()
    assert chosen == [("forget", "RD = route départementale")]
    other, chosen_other, _ = _card()
    other.text.setText("   ")
    other.buttons["user"].click()
    assert chosen_other == []


def test_the_card_takes_the_theme_and_says_itself_in_the_transcription():
    card, _chosen, _undone = _card()
    palette = {key: "#123456" for key in ("fm_list", "fm_accent", "fm_text", "fm_text_muted", "fm_group_border")}
    card.restyle(palette, False)
    assert "#123456" in card.styleSheet()
    assert card.text.maxLength() == 300


def test_two_buttons_a_row_so_that_a_narrow_dock_holds_them():
    card, _chosen, _undone = _card()
    rows = [card.layout().itemAt(rank).layout() for rank in range(card.layout().count())
            if card.layout().itemAt(rank).layout() is not None
            and any(isinstance(row.widget(), QtWidgets.QPushButton) and row.widget() in card.buttons.values()
                    for row in (card.layout().itemAt(rank).layout().itemAt(i)
                                for i in range(card.layout().itemAt(rank).layout().count())))]
    assert [sum(1 for i in range(row.count()) if row.itemAt(i).widget() is not None) for row in rows] == [2, 2]
    card.resize(360, 400)
    assert card.minimumSizeHint().width() <= 380


def test_do_not_keep_needs_no_text():
    card, chosen, _undone = _card()
    card.text.setText("")
    card.buttons["decline"].click()
    assert chosen == [("decline", "")]


def test_chart_pdf_button_routes_the_format_and_an_infographic_has_no_layout_button(monkeypatch):
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", QtCore)
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtSvg", importlib.import_module(QtWidgets.__package__ + ".QtSvg"))
    palette = {key: "#123456" for key in ("fm_group", "fm_group_border", "fm_text_muted", "fm_accent")}
    saved = []
    card = thread.ChartCard("Overview", '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"/>',
                            "project", palette, False, None, on_save=saved.append, on_layout=None)
    card.findChild(QtWidgets.QPushButton, "pushButton_agent_chart_pdf").click()
    assert saved == ["pdf"]
    assert card.findChild(QtWidgets.QPushButton, "pushButton_agent_chart_layout").isHidden()

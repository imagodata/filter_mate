# -*- coding: utf-8 -*-
"""The line to ask of the AGENT panel (2026-11-24), on real Qt widgets (PyQt5, offscreen): several lines that grow,
Enter sends and Shift+Enter goes to the line, "@" offers the layers, and a request sent while the agent works waits
in view and goes when the request under way ends.
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

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_input_test"


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
        return app, importlib.import_module(f"{_PKG}.ui.widgets.agent_panel")
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


_APP, panel_module = _load()


from PyQt5 import QtTest  # noqa: E402

Qt = QtCore.Qt


def _run(ms=50):
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(ms, loop.quit)
    loop.exec_()


def _panel():
    panel = panel_module.AgentPanel()
    panel.set_ready(True, "Claude")
    panel.resize(380, 600)
    panel.show()
    _run()
    return panel


def test_enter_sends_and_shift_enter_goes_to_the_line():
    panel = _panel()
    sent = []
    panel.send_requested.connect(sent.append)
    QtTest.QTest.keyClicks(panel.input, "garde les communes")
    QtTest.QTest.keyClick(panel.input, Qt.Key_Return, Qt.ShiftModifier)
    QtTest.QTest.keyClicks(panel.input, "et les routes")
    assert panel.input.text() == "garde les communes\net les routes" and sent == []
    QtTest.QTest.keyClick(panel.input, Qt.Key_Return)
    assert sent == ["garde les communes\net les routes"]


def test_the_line_grows_with_its_lines_up_to_five():
    panel = _panel()
    one = panel.input.height()
    panel.input.setText("a\nb\nc")
    _run()
    three = panel.input.height()
    panel.input.setText("\n".join("x" * 12))
    _run()
    many = panel.input.height()
    assert one == panel_module.INPUT_HEIGHT and three > one and many > three
    panel.input.setText("\n".join("x" * 40))
    _run()
    assert panel.input.height() == many  # five lines at most, then it scrolls
    panel.input.clear()
    _run()
    assert panel.input.height() == one


def test_the_arrows_give_the_previous_requests_from_the_first_line():
    panel = _panel()
    panel.input.remember("premier")
    panel.input.remember("second")
    QtTest.QTest.keyClicks(panel.input, "brouillon")
    QtTest.QTest.keyClick(panel.input, Qt.Key_Up)
    assert panel.input.text() == "second"
    QtTest.QTest.keyClick(panel.input, Qt.Key_Up)
    assert panel.input.text() == "premier"
    QtTest.QTest.keyClick(panel.input, Qt.Key_Down)
    QtTest.QTest.keyClick(panel.input, Qt.Key_Down)
    assert panel.input.text() == "brouillon"
    panel.input.setText("ligne 1\nligne 2")
    QtTest.QTest.keyClick(panel.input, Qt.Key_Up)  # from the second line: up a line, not the history
    assert panel.input.text() == "ligne 1\nligne 2"


def test_at_offers_the_layers_and_writes_the_name():
    panel = _panel()
    panel.input.layer_rows = lambda: [("communes_1", "communes", ""), ("troncon_2", "troncon_de_route", ""),
                                      ("batiment_3", "batiment", "")]
    panel.input.setFocus()
    QtTest.QTest.keyClicks(panel.input, "filtre @tron")
    _run()
    completer = panel.input.completer
    assert completer.popup().isVisible() and completer.currentCompletion() == "troncon_de_route"
    # QCompleter can display its first completion without selecting a current popup row.
    completer.activated[QtCore.QModelIndex].emit(completer.popup().model().index(0, 0))
    assert panel.input.text() == "filtre troncon_de_route"
    QtTest.QTest.keyClicks(panel.input, " email@x")  # an "@" inside a word offers nothing
    _run()
    assert not completer.popup().isVisible()


def test_at_offers_homonyms_apart_and_writes_the_id():
    panel = _panel()
    panel.input.layer_rows = lambda: [("id_est", "communes", "Est"), ("id_ouest", "communes", "Ouest")]
    panel.input.setFocus()
    QtTest.QTest.keyClicks(panel.input, "voir @com")
    _run()
    completer = panel.input.completer
    assert completer.popup().isVisible() and completer.currentCompletion() == "communes (Est)"
    completer.activated[QtCore.QModelIndex].emit(completer.popup().model().index(1, 0))
    assert panel.input.text() == "voir id_ouest"


def test_a_request_sent_while_working_waits_in_view_then_goes():
    panel = _panel()
    sent = []
    panel.queued_send_requested.connect(lambda text, posture: sent.append((text, posture)))
    panel.set_working(True)
    panel.input.setText("et les bâtiments")
    QtTest.QTest.keyClick(panel.input, Qt.Key_Return)
    assert sent == [] and panel.queued == "et les bâtiments" and panel.input.text() == ""
    assert panel.queue_row.isVisibleTo(panel) and "Next: et les bâtiments" in panel.queue_label.toolTip() + panel.queue_label._full
    panel.set_working(False)
    _run()
    assert sent == [("et les bâtiments", "act")] and panel.queued == "" and not panel.queue_row.isVisibleTo(panel)
    assert panel.input.text() == ""  # dispatch carries the posture without replacing the user's next draft


def test_a_request_waiting_can_be_taken_back():
    panel = _panel()
    sent = []
    panel.send_requested.connect(sent.append)
    panel.set_working(True)
    panel.input.setText("plus tard")
    QtTest.QTest.keyClick(panel.input, Qt.Key_Return)
    panel.queue_cancel.click()
    assert panel.queued == "" and panel.input.text() == "plus tard" and not panel.queue_row.isVisibleTo(panel)
    panel.set_working(False)
    _run()
    assert sent == []


def test_a_new_conversation_drops_the_request_waiting():
    panel = _panel()
    sent = []
    panel.send_requested.connect(sent.append)
    panel.set_working(True)
    panel.input.setText("oubliée")
    QtTest.QTest.keyClick(panel.input, Qt.Key_Return)
    panel.clear_thread()
    panel.set_working(False)
    _run()
    assert sent == [] and panel.queued == ""


def test_stop_keeps_the_request_waiting_without_sending_it():
    panel = _panel()
    sent, stops = [], []
    panel.send_requested.connect(sent.append)
    panel.stop_requested.connect(lambda: stops.append(True))
    panel.set_working(True)
    panel.input.setText("la suivante")
    QtTest.QTest.keyClick(panel.input, Qt.Key_Return)
    QtTest.QTest.keyClick(panel.input, Qt.Key_Escape)
    assert stops == [True]
    panel.set_working(False)
    _run()
    assert sent == [] and panel.queued == "la suivante" and panel.queue_row.isVisibleTo(panel)
    panel.input.setText("longue question")  # the stopped request came back in the line
    panel.cancel_queued()
    assert panel.input.text() == "longue question\nla suivante" and panel.queued == ""

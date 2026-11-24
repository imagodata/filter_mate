# -*- coding: utf-8 -*-
"""
The selectable values of the favorites summary, on real Qt widgets (PyQt5, offscreen).

The module is loaded with ``qgis.PyQt`` pointing at PyQt5 for the import only (the root conftest
mocks Qt for the other tests). Skipped without PyQt5.
"""
import importlib.util
import os
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui  # noqa: E402

_PATH = pathlib.Path(__file__).resolve().parents[4] / "ui" / "dialogs" / "favorite_summary_widgets.py"


def _load():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt = {"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore, "qgis.PyQt.QtGui": QtGui,
          "qgis.PyQt.QtWidgets": QtWidgets}
    saved = {name: sys.modules.get(name) for name in qt}
    sys.modules.update(qt)  # for the import only: the module keeps the real Qt classes
    try:
        spec = importlib.util.spec_from_file_location("fm_favorite_summary_widgets_qt_test", _PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return app, module


_APP, widgets = _load()

_LONG = 'parcelles : "fid" IN (' + ",".join(str(i) for i in range(1, 400)) + ")"


def test_expression_view_copies_exactly_the_text():
    view = widgets.ExpressionView(_LONG, "Courier")
    assert view.toPlainText() == _LONG
    assert "​" not in view.toPlainText()
    assert view.isReadOnly()


def _line_pitch(view) -> float:
    layout = view.document().firstBlock().layout()
    if layout.lineCount() > 1:
        return layout.lineAt(1).y() - layout.lineAt(0).y()
    return layout.lineAt(0).height()


def test_expression_view_wraps_and_stops_growing_at_six_lines():
    view = widgets.ExpressionView(_LONG, "Courier")
    view.resize(300, 100)
    view.show()
    _APP.processEvents()
    assert view.width() < 400  # the width is the one given: the text wrapped
    wrapped_lines = view.document().firstBlock().layout().lineCount()
    assert wrapped_lines > 6
    assert view.height() == int(6 * _line_pitch(view) + view.document().documentMargin())


def test_expression_view_of_a_short_text_is_one_line_high():
    view = widgets.ExpressionView('"type" = \'A\'', "Courier")
    view.resize(300, 100)
    view.show()
    _APP.processEvents()
    assert view.height() == int(_line_pitch(view) + 2 * view.document().documentMargin()) + 2


def test_text_value_is_plain_selectable_and_unaltered():
    label = widgets.text_value("a, b, c")
    assert label.text() == "a, b, c"
    assert label.textFormat() == QtCore.Qt.PlainText
    assert label.wordWrap()
    assert label.textInteractionFlags() & QtCore.Qt.TextSelectableByMouse

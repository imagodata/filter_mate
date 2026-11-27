"""The activity animation follows the panel's lifetime, on real Qt widgets."""
import importlib
import os
from pathlib import Path
import sys
import types
from unittest.mock import MagicMock

import pytest

try:
    from PyQt6 import QtCore, QtGui, QtWidgets, QtSvg
except ImportError:
    QtWidgets = pytest.importorskip('PyQt5.QtWidgets')
    from PyQt5 import QtCore, QtGui, QtSvg

ROOT = Path(__file__).resolve().parents[4]
pytestmark = pytest.mark.unit


@pytest.fixture
def activity(monkeypatch):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    for name, module in (('QtCore', QtCore), ('QtGui', QtGui), ('QtWidgets', QtWidgets), ('QtSvg', QtSvg)):
        monkeypatch.setitem(sys.modules, 'qgis.PyQt.' + name, module)
    prefix = '_fm_activity_test'
    for suffix, path in (('', ROOT), ('.ui', ROOT / 'ui'), ('.ui.widgets', ROOT / 'ui/widgets'),
                         ('.ui.styles', ROOT / 'ui/styles')):
        package = types.ModuleType(prefix + suffix)
        package.__path__ = [str(path)]
        monkeypatch.setitem(sys.modules, prefix + suffix, package)
    module = importlib.import_module(prefix + '.ui.widgets.agent_activity')
    parent = QtWidgets.QWidget()
    widget = module.AgentActivityIcon(parent)
    yield app, parent, widget, module
    parent.close()
    app.processEvents()


def test_animation_moves_then_stops_when_hidden_or_idle(activity):
    app, parent, widget, _ = activity
    widget.set_working(True)
    assert not widget._renderer.animated()  # the parent has not been shown
    parent.show()
    app.processEvents()
    assert widget._renderer.animated()
    before = widget.grab().toImage()
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(300, loop.quit)
    getattr(loop, 'exec', getattr(loop, 'exec_', None))()
    assert widget.grab().toImage() != before
    parent.hide()
    app.processEvents()
    assert not widget._renderer.animated()
    parent.show()
    app.processEvents()
    assert widget._renderer.animated()
    widget.refresh_look(True)
    assert widget._renderer.animated()
    widget.set_working(False)
    assert not widget._renderer.animated() and not widget.isVisible()


def test_indicators_own_separate_renderers(activity):
    app, parent, widget, module = activity
    second = module.AgentActivityIcon(parent)
    parent.show()
    widget.set_working(True)
    app.processEvents()
    assert second._renderer is not widget._renderer
    assert widget._renderer.animated() and not second._renderer.animated()


def test_missing_qtsvg_keeps_the_indicator_hidden(activity, monkeypatch):
    app, parent, _, module = activity
    monkeypatch.setitem(sys.modules, 'qgis.PyQt.QtSvg', None)
    widget = module.AgentActivityIcon(parent)
    parent.show()
    widget.set_working(True)
    app.processEvents()
    assert widget._renderer is None and not widget.isVisible()


def test_action_phases_change_the_picture_without_restarting_on_each_text_chunk(activity, monkeypatch):
    app, parent, widget, _ = activity
    parent.show()
    widget.set_working(True)
    app.processEvents()
    thinking = widget.grab().toImage()
    load = MagicMock(wraps=widget._renderer.load)
    monkeypatch.setattr(widget._renderer, 'load', load)
    widget.set_phase('working')
    app.processEvents()
    assert widget.phase == 'working' and widget.grab().toImage() != thinking
    assert load.call_count == 1
    widget.set_phase('working')
    assert load.call_count == 1
    widget.set_phase('waiting')
    app.processEvents()
    assert widget.phase == 'waiting' and widget._renderer.animated()
    assert widget.grab().toImage() != thinking
    parent.hide()
    parent.show()
    app.processEvents()
    assert widget.phase == 'waiting' and widget._renderer.animated()
    widget.set_working(False)
    widget.set_working(True)
    assert widget.phase == 'thinking'

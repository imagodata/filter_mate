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
    assert not widget._renderer.animated() and widget.isVisible()
    assert widget.display_phase == 'complete'
    before = widget.grab().toImage()
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(150, loop.quit)
    getattr(loop, 'exec', getattr(loop, 'exec_', None))()
    assert widget.grab().toImage() == before


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


def test_user_interactions_are_static_except_live_dictation_and_never_replace_active_work(activity):
    app, parent, widget, _ = activity
    parent.show()
    app.processEvents()
    assert widget.isVisible() and widget.display_phase == 'idle' and not widget._renderer.animated()
    widget.set_interaction('drafting')
    assert widget.display_phase == 'drafting' and not widget._renderer.animated()
    widget.set_working(True)
    widget.set_phase('processing')
    assert widget.display_phase == 'processing' and widget._renderer.animated()
    widget.set_working(False)
    assert widget.display_phase == 'drafting' and not widget._renderer.animated()
    widget.set_interaction('listening')
    assert widget.display_phase == 'listening' and widget._renderer.animated()
    parent.hide()
    assert not widget._renderer.animated()
    parent.show()
    widget.set_interaction('queued')
    assert widget.display_phase == 'queued' and not widget._renderer.animated()
    assert widget.accessibleName() == widget.toolTip() and 'queued' in widget.toolTip()


def test_all_phases_render_valid_distinct_static_artwork_and_static_states_never_animate(activity):
    app, parent, widget, module = activity
    from qgis.PyQt.QtCore import QByteArray
    parent.show()
    app.processEvents()
    images = []
    for phase in module.AGENT_ACTIVITY_STYLES:
        renderer = QtSvg.QSvgRenderer(QByteArray(module.agent_activity_svg('#2e2e2e', False, phase).encode()))
        assert renderer.isValid() and not renderer.animated(), phase
        image = QtGui.QImage(64, 64, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(image)
        renderer.render(painter)
        painter.end()
        assert all(image != previous for previous in images), phase
        images.append(image)
        widget.set_working(True)
        widget.set_phase(phase)
        assert widget._renderer.animated() == (phase not in module.STATIC_AGENT_PHASES), phase

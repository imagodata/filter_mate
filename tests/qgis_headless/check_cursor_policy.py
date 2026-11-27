"""Real QGIS map cursors coexist with plugin-only control and busy cursors (Qt 5/6)."""
import os
import sys
import types

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from qgis.core import QgsApplication, Qgis
from qgis.gui import QgsMapCanvas, QgsMapToolPan, QgsMapToolZoom
from qgis.PyQt.QtCore import Qt, QEvent, QCoreApplication
from qgis.PyQt.QtWidgets import (QMainWindow, QDockWidget, QWidget, QVBoxLayout, QPushButton,
                                QLineEdit, QPlainTextEdit, QComboBox)

app = QgsApplication([], False)
app.initQgis()
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from filter_mate.ui.cursors import CursorLease, install_cursor_policy, set_widget_busy, set_cursor_intent

window = QMainWindow()
canvas = QgsMapCanvas(window)
window.setCentralWidget(canvas)
dock = QDockWidget('FilterMate', window)
root = QWidget(dock)
dock.setWidget(root)
layout = QVBoxLayout(root)
button, editor, text, combo = QPushButton('Run', root), QLineEdit(root), QPlainTextEdit(root), QComboBox(root)
for widget in (button, editor, text, combo):
    layout.addWidget(widget)
window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
policy = install_cursor_policy(dock)
window.show()
app.processEvents()
assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor
assert editor.cursor().shape() == text.viewport().cursor().shape() == Qt.CursorShape.IBeamCursor
assert combo.cursor().shape() == Qt.CursorShape.PointingHandCursor
button.setEnabled(False)
set_cursor_intent(button, Qt.CursorShape.PointingHandCursor)
assert button.cursor().shape() == Qt.CursorShape.ArrowCursor
button.setEnabled(True)
later = QPushButton('Added later', root)
later.show()
app.processEvents()
assert later.cursor().shape() == Qt.CursorShape.PointingHandCursor
print('PASS enabled, disabled, text and dynamic plugin control cursors', flush=True)

pan, zoom = QgsMapToolPan(canvas), QgsMapToolZoom(canvas, False)
canvas.setMapTool(pan)
before = canvas.cursor()
first = CursorLease([dock, button])
assert canvas.cursor() == before
canvas.setMapTool(zoom)
after = canvas.cursor()
second = CursorLease([button], Qt.CursorShape.WaitCursor)
first.close()
assert button.cursor().shape() == Qt.CursorShape.WaitCursor
second.close()
assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor
assert canvas.mapTool() is zoom and canvas.cursor() == after
print('PASS real map tool changes survive overlapping plugin busy operations', flush=True)

app.setOverrideCursor(Qt.CursorShape.CrossCursor)
try:
    try:
        with CursorLease([button]):
            raise ValueError('cancelled operation')
    except ValueError:
        pass
    assert app.overrideCursor().shape() == Qt.CursorShape.CrossCursor
finally:
    app.restoreOverrideCursor()
assert app.overrideCursor() is None
set_widget_busy(root, True)
assert editor.cursor().shape() == Qt.CursorShape.BusyCursor
set_widget_busy(root, False)
assert editor.cursor().shape() == Qt.CursorShape.IBeamCursor
foreign = QPushButton('Another plugin', window)
foreign.setCursor(Qt.CursorShape.SizeAllCursor)
foreign.show()
app.processEvents()
assert foreign.cursor().shape() == Qt.CursorShape.SizeAllCursor
print('PASS external override stack, foreign controls and compound editor restoration', flush=True)

lease = CursorLease([button])
policy.close()
assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor
lease.close()
removed = QPushButton('Removed', root)
lease = CursorLease([removed])
removed.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
lease.close()
print(f'PASS QGIS {Qgis.QGIS_VERSION}: unload and delayed completion after widget deletion', flush=True)
os._exit(0)

"""Real Qt timelines and canvas interaction: smooth zooms never overwrite user navigation."""
import os
import sys
import types

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-zoom-transitions-logs')
from qgis.core import QgsApplication, QgsProject, QgsRectangle, QgsCoordinateReferenceSystem, Qgis
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QEventLoop, QTimer, Qt
from qgis.PyQt.QtTest import QTest

app = QgsApplication([], False)
app.initQgis()
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from filter_mate.adapters.qgis.navigation import navigate_extent

canvas = QgsMapCanvas()
canvas.resize(800, 600)
canvas.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:2154'))
canvas.show()
app.processEvents()
canvas.setExtent(QgsRectangle(0, 0, 1000, 1000))
canvas.clearExtentHistory()
original_extent = QgsRectangle(canvas.extent())
target = QgsRectangle(100, 100, 200, 200)
frames = []
canvas.extentsChanged.connect(lambda: frames.append(QgsRectangle(canvas.extent())))
assert navigate_extent(canvas, target, wait=True, duration_ms=160)
assert len(frames) >= 3, len(frames)
assert abs(canvas.extent().center().x() - 150) < 1e-6
assert canvas.extent().contains(target)
assert canvas._filtermate_transition is None
final_extent = QgsRectangle(canvas.extent())
canvas.zoomToPreviousExtent()
assert canvas.extent() == original_extent, canvas.extent().toString()
canvas.zoomToNextExtent()
assert canvas.extent() == final_extent
print('PASS eased zoom renders intermediate frames and returns the final extent', flush=True)

for number in range(1, 111):
    canvas.setExtent(QgsRectangle(number * 1000, 0, number * 1000 + 100, 100))
assert navigate_extent(canvas, target, wait=True, duration_ms=100)
for number in range(110, 11, -1):
    canvas.zoomToPreviousExtent()
    assert abs(canvas.extent().center().x() - (number * 1000 + 50)) < 1e-6, number
print('PASS animation is one native zoom-history entry, preserving the existing 100-entry limit', flush=True)

def wait(milliseconds=220):
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()

manual = QgsRectangle(600, 600, 800, 800)
QTimer.singleShot(40, lambda: canvas.setExtent(manual))
assert not navigate_extent(canvas, QgsRectangle(0, 0, 20, 20), wait=True, duration_ms=160)
stopped = QgsRectangle(canvas.extent())
wait()
assert canvas.extent() == stopped and abs(stopped.center().x() - 700) < 1e-6
print('PASS manual pan cancels the animation without a late snap back', flush=True)

QTimer.singleShot(30, lambda: QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton))
assert not navigate_extent(canvas, target, wait=True, duration_ms=160)
stopped = QgsRectangle(canvas.extent())
wait()
assert canvas.extent() == stopped
print('PASS viewport input cancels motion and remains available to the map tool', flush=True)

navigate_extent(canvas, target, duration_ms=160)
previous = canvas._filtermate_transition
latest = QgsRectangle(2000, 2000, 2200, 2200)
assert navigate_extent(canvas, latest, wait=True, duration_ms=100)
assert previous.cancelled
wait()
assert abs(canvas.extent().center().x() - 2100) < 1e-6
assert navigate_extent(canvas, target, wait=True, duration_ms=0)
assert canvas._filtermate_transition is None
assert abs(canvas.extent().center().x() - 150) < 1e-6
print('PASS newer requests replace older ones; zero duration disables animation', flush=True)

QTimer.singleShot(30, QgsProject.instance().clear)
assert not navigate_extent(canvas, latest, wait=True, duration_ms=160)
canvas.hide()
assert navigate_extent(canvas, target, wait=True, duration_ms=160)
assert canvas._filtermate_transition is None
print(f'PASS QGIS {Qgis.QGIS_VERSION}: project-close cancellation and hidden canvas fallback', flush=True)
os._exit(0)

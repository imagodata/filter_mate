"""Real QGIS canvas/layers and Qt docks/actions; native iface dialog entrypoints are stand-ins."""
import os
import sys
import types

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-interface-logs')
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsRectangle, Qgis
from qgis.gui import QgsMapCanvas, QgsMapToolPan
from qgis.PyQt.QtCore import Qt, QEvent, QCoreApplication, QTimer
from qgis.PyQt.QtWidgets import QMainWindow, QDockWidget, QDialog, QWidget
try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction

app = QgsApplication([], False)
app.initQgis()
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from filter_mate.adapters.public_api.qgis_interface import qgis_capabilities, control_qgis

window = QMainWindow()
canvas = QgsMapCanvas(window)
window.setCentralWidget(canvas)
window.resize(800, 600)
native = QDockWidget('Layers', window)
native.setObjectName('Layers')
native.setWidget(QWidget(native))
plugin = QDockWidget('A plugin panel', window)
plugin.setObjectName('plugin.panel')
plugin.setWidget(QWidget(plugin))
window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, native)
window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, plugin)
window.show()
app.processEvents()
plugin.hide()
pan = QgsMapToolPan(canvas)
action = QAction('Pan', window)
action.triggered.connect(lambda: canvas.setMapTool(pan))
tables, properties = [], []

def table(layer, expression):
    dialog = QDialog(window)
    tables.append((layer.id(), expression, dialog))
    return dialog

def layer_properties(layer, page):
    dialog = QDialog(window)
    QTimer.singleShot(0, dialog.reject)
    properties.append((layer.id(), page))
    dialog.exec()

face = types.SimpleNamespace(mainWindow=lambda: window, mapCanvas=lambda: canvas, actionPan=lambda: action,
                             showAttributeTable=table, showLayerProperties=layer_properties)
layer = QgsVectorLayer('Point?crs=EPSG:2154&field=value:integer', 'points', 'memory')
feature = QgsFeature(layer.fields())
feature.setAttributes([1])
feature.setGeometry(QgsGeometry.fromWkt('POINT(100 100)'))
layer.dataProvider().addFeatures([feature])
QgsProject.instance().addMapLayer(layer)
layer.setSubsetString('"value" > 0')
before_subset, before_selected = layer.subsetString(), layer.selectedFeatureIds()

capabilities = qgis_capabilities(face)
assert capabilities['available'] and {row['id'] for row in capabilities['actions']} == {
    'attributes', 'properties', 'show_panel', 'hide_panel', 'map_tool', 'previous_view', 'next_view'}
assert not next(row for row in capabilities['panels'] if row['id'] == 'plugin.panel')['visible']
assert control_qgis('show_panel', panel='plugin.panel', iface_obj=face)['visible']
assert not control_qgis('hide_panel', panel='plugin.panel', iface_obj=face)['visible']
print('PASS discovery and existing plugin panel visibility with native Qt docks', flush=True)

result = control_qgis('attributes', layer=layer.id(), expression='"value" = 1', iface_obj=face)
assert result['opened'] and tables[-1][1] == '"value" = 1'
assert layer.subsetString() == before_subset and layer.selectedFeatureIds() == before_selected
result = control_qgis('properties', layer=layer.id(), page='metadata', iface_obj=face)
assert result['requested'] and properties[-1][1] == 'mOptsPage_Metadata'
assert layer.subsetString() == before_subset and layer.selectedFeatureIds() == before_selected
print('PASS table-only filter and modal property handoff entrypoints preserve layer state', flush=True)

control_qgis('map_tool', tool='pan', iface_obj=face)
assert canvas.mapTool() is pan
canvas.setExtent(QgsRectangle(0, 0, 1000, 1000))
canvas.clearExtentHistory()
old = QgsRectangle(canvas.extent())
canvas.setExtent(QgsRectangle(2000, 2000, 3000, 3000))
new = QgsRectangle(canvas.extent())
control_qgis('previous_view', iface_obj=face)
assert canvas.extent() == old
control_qgis('next_view', iface_obj=face)
assert canvas.extent() == new
print('PASS safe native map tool and map history operations', flush=True)

plugin.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
assert not any(row['id'] == 'plugin.panel' for row in qgis_capabilities(face)['panels'])
try:
    control_qgis('show_panel', panel='plugin.panel', iface_obj=face)
except ValueError:
    pass
else:
    raise AssertionError('an unloaded plugin panel was reused')
assert not qgis_capabilities()['available']
print(f'PASS QGIS {Qgis.QGIS_VERSION}: plugin unload invalidation and no-window reporting', flush=True)
os._exit(0)

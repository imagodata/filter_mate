"""Regression checks for R04-R07, with real QGIS rectangles, layers and canvas."""
import os
import sys
import types
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', '/tmp/fm-audit-navigation-logs')
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsRectangle, QgsCoordinateReferenceSystem
from qgis.gui import QgsMapCanvas
from filter_mate.adapters.public_api import project_control
from filter_mate.adapters.qgis import async_query
from filter_mate.adapters import auto_zoom

app = QgsApplication([], False)
app.initQgis()
project = QgsProject.instance()
canvas = QgsMapCanvas()
canvas.resize(800, 600)
canvas.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:4326'))

for x, y in ((0, 45), (1, 45), (0, 0)):
    layer = QgsVectorLayer('Point?crs=EPSG:4326', 'point', 'memory')
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt(f'POINT({x} {y})'))
    layer.dataProvider().addFeatures([feature])
    layer.updateExtents()
    project.addMapLayer(layer)
    layer.selectByIds([next(layer.getFeatures()).id()])
    canvas.setExtent(QgsRectangle(-.1, y-.1, .1, y+.1))
    with patch.object(project_control, '_canvas', return_value=canvas):
        project_control.zoom_to(layer.id(), selected_only=True)
    assert canvas.extent().width() < 1, (x, y, canvas.extent().toString())
    assert abs(canvas.extent().center().x()-x) < .01
    print(f'PASS point {x}, {y} keeps a pixel-scale margin', flush=True)

delivery = {}
def submit(*args, **kwargs):
    delivery['compute'], delivery['deliver'] = args[4:6]
    return object()

with patch.object(async_query, 'submit_query', side_effect=submit):
    async_query.queue_union_zoom([layer], canvas)
before = QgsRectangle(canvas.extent())
canvas.setExtent(QgsRectangle(10, 10, 20, 20))
canvas.setExtent(before)  # moving away and back still invalidates the old request
delivery['deliver'](QgsRectangle(40, 40, 50, 50))
assert canvas.extent() == before
print('PASS manual navigation invalidates a pending auto-zoom even after moving back', flush=True)

from osgeo import gdal
from qgis.core import QgsRasterLayer
dataset = gdal.GetDriverByName('GTiff').Create('/vsimem/fm-audit-navigation.tif', 10, 10, 1, gdal.GDT_Byte)
dataset.SetGeoTransform([20, 1, 0, 30, 0, -1])
dataset.SetProjection('EPSG:4326')
dataset = None
raster = QgsRasterLayer('/vsimem/fm-audit-navigation.tif', 'raster', 'gdal')
with patch.object(async_query, 'submit_query', side_effect=submit):
    async_query.queue_union_zoom([layer, raster], canvas)
task = types.SimpleNamespace(isCanceled=lambda: False, features=lambda request, source: source.getFeatures(request))
union = delivery['compute'](task)
assert union.xMaximum() >= 30 and union.yMaximum() >= 30
print('PASS mixed union includes the raster extent', flush=True)

project.clear()
canvas.setLayers([])
print('All audited navigation checks passed', flush=True)
os._exit(0)

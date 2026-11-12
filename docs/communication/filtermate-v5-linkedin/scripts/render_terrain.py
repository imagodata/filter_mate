"""Re-render the captured FilterMate DTM output with a local contrast stretch.

FM5_CLIPPED_DTM must point to the original retained VRT from the capture run.
Only the display changes; the FilterMate result and source data stay intact.
"""
from pathlib import Path
import json
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsApplication, QgsRasterLayer, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsRectangle, QgsFillSymbol, QgsMapSettings, QgsMapRendererSequentialJob,
    QgsCoordinateReferenceSystem, QgsMultiBandColorRenderer,
    QgsSingleBandGrayRenderer, QgsContrastEnhancement,
)
from qgis.PyQt.QtGui import QImage, QColor
from qgis.PyQt.QtCore import QSize

app = QgsApplication([], False)
app.initQgis()
gdal.UseExceptions()
root = Path(__file__).resolve().parent.parent
data = Path(os.environ['FM5_DATA_DIR'])
vrt = Path(os.environ['FM5_CLIPPED_DTM'])
assert vrt.exists()
ds = gdal.Open(str(vrt))
values = ds.GetRasterBand(1).ReadAsArray()
valid = ds.GetRasterBand(1).GetMaskBand().ReadAsArray() > 0
if ds.RasterCount > 1:
    valid &= ds.GetRasterBand(ds.RasterCount).ReadAsArray() > 0
values = values[valid & np.isfinite(values)]
low, high = float(values.min()), float(values.max())
assert high > low and low > 0
dtm = QgsRasterLayer(str(vrt), 'Clipped DTM', 'gdal')
renderer = QgsSingleBandGrayRenderer(dtm.dataProvider(), 1)
stretch = QgsContrastEnhancement(dtm.dataProvider().dataType(1))
stretch.setContrastEnhancementAlgorithm(QgsContrastEnhancement.ContrastEnhancementAlgorithm.StretchToMinimumMaximum)
stretch.setMinimumValue(low)
stretch.setMaximumValue(high)
renderer.setContrastEnhancement(stretch)
if ds.RasterCount > 1:
    renderer.setAlphaBand(ds.RasterCount)
dtm.setRenderer(renderer)
rgb = QgsRasterLayer(str(data / 'ortho_rvb.tif'), 'RGB orthophoto', 'gdal')
rgb.setRenderer(QgsMultiBandColorRenderer(rgb.dataProvider(), 1, 2, 3))
buildings = QgsVectorLayer(str(data / 'sarlat.gpkg') + '|layername=batiment', 'Buildings', 'ogr')
churches = [f for f in buildings.getFeatures() if f['nature'] == 'Eglise']
assert churches
church = max(churches, key=lambda f: f.geometry().area())
outline = QgsVectorLayer('MultiPolygon?crs=EPSG:2154', 'Selected church', 'memory')
feature = QgsFeature()
feature.setGeometry(QgsGeometry(church.geometry()))
outline.dataProvider().addFeatures([feature])
outline.renderer().setSymbol(QgsFillSymbol.createSimple({
    'color': '0,0,0,0', 'outline_color': '#ffcc00', 'outline_width': '1.2',
}))
previous = QImage(str(root / 'screenshots/02_church_dtm_lidar-terrain.png'))
assert not previous.isNull()
ratio = previous.height() / previous.width()
box = QgsRectangle(church.geometry().boundingBox())
box.grow(65)
width = max(box.width(), 190, box.height() / ratio)
centre = box.center()
extent = QgsRectangle(centre.x() - width/2, centre.y() - width*ratio/2,
                      centre.x() + width/2, centre.y() + width*ratio/2)
settings = QgsMapSettings()
settings.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:2154'))
settings.setLayers([outline, dtm, rgb])
settings.setOutputSize(QSize(previous.width(), previous.height()))
settings.setOutputDpi(144)
settings.setExtent(extent)
settings.setBackgroundColor(QColor('white'))
job = QgsMapRendererSequentialJob(settings)
job.start()
job.waitForFinished()
output = root / 'screenshots/02_church_dtm_lidar-terrain.png'
assert job.renderedImage().save(str(output), 'PNG')
(root / 'terrain-display.json').write_text(json.dumps({
    'input': str(vrt), 'source': 'retained FilterMate public Python API output',
    'minimum_m': low, 'maximum_m': high, 'valid_pixels': int(len(values)),
    'change': 'QGIS linear grayscale display stretch; no data edits',
    'output_size': [previous.width(), previous.height()],
}, indent=2), encoding='utf-8')
print('Clipped DTM display range:', low, high, flush=True)
os._exit(0)

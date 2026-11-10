"""One click on a building with SAM: the mask chosen today, the best of the three, and a refined second pass.

Pre-registered 2026-11-10: the 20 buildings of 80 to 400 m² of the Cerdagne orthophoto (sets A and B of the
similar objects bench), a click at the pole of inaccessibility, a 150 m view. Refine = a second prediction with
the click and the box of the first mask (5 % margin). Adopted if the median IoU gains at least 0.02 and at most
4 of the 20 buildings lose more than 0.05. The best of three measures what choosing the granularity can give.

Run by python-qgis.bat: argv = plugins folder, onnxruntime folder, models folder, ortho, buildings, output json.
"""
import json
import os
import statistics
import sys

plugins, deps, models, ortho, buildings, output = sys.argv[1:7]
sys.path.insert(0, plugins)
sys.path.append(deps)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from qgis.core import (QgsApplication, QgsFeatureRequest, QgsGeometry, QgsMapSettings, QgsPointXY, QgsRasterLayer,
                       QgsRectangle, QgsVectorLayer)
from qgis.PyQt.QtGui import QColor

app = QgsApplication([], True)
app.initQgis()
from filter_mate.adapters.qgis.coverage_layers import raster_adapter, sam_model, segmentation

layer = QgsRasterLayer(ortho, 'ortho', 'gdal')
vector = QgsVectorLayer(f'{buildings}|layername=batiment_sl', 'batiment', 'ogr')
extent = layer.extent()
raster = (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
native = extent.width() / layer.width()
crs_wkt = layer.crs().toWkt()
model = sam_model.SamOnnxProvider(models)
settings = QgsMapSettings()
settings.setDestinationCrs(layer.crs())
settings.setBackgroundColor(QColor(0, 0, 0, 255))
inner = QgsRectangle(extent.xMinimum() + 100, extent.yMinimum() + 100, extent.xMaximum() - 100, extent.yMaximum() - 100)
features = [f for f in vector.getFeatures(QgsFeatureRequest().setFilterRect(inner))
            if 80 <= f.geometry().area() <= 400 and inner.contains(f.geometry().boundingBox())]
features.sort(key=lambda f: f.id())


def object_of(mask, window, point):
    """The parts of the mask under the click, as the controller keeps them."""
    from filter_mate.adapters.qgis.coverage_layers.geometry_tools import mask_to_geometry
    geometry = mask_to_geometry(mask, window.geotransform(), crs_wkt, sieve_pixels=segmentation.SIEVE_PIXELS,
                                simplify_tolerance=window.cell * 0.5)
    parts = raster_adapter.geometry_parts(geometry)
    where = QgsGeometry.fromPointXY(QgsPointXY(point.x(), point.y()))
    held = [part for part in parts if part.intersects(where)]
    return QgsGeometry.unaryUnion(held) if held else (geometry if parts else None)


def iou(geometry, truth):
    return round(segmentation.overlap(geometry, truth), 4) if geometry is not None and not geometry.isEmpty() else 0.0


rows = []
for position, feature in enumerate(features):
    truth = feature.geometry()
    point = truth.poleOfInaccessibility(0.25)[0].asPoint()
    window = segmentation.plan_window(point.x(), point.y(), raster, native, 150.0, model.input_size)
    rgb = segmentation.image_to_rgb(segmentation.render_window(settings, layer, window, lambda: False))
    embedding = model.embed(rgb)
    pixel = window.to_pixel(point.x(), point.y())
    masks, scores = model.predict_masks(embedding, [pixel], [1], None)
    best = int(np.argmax(scores))
    each = [iou(object_of(mask, window, point), truth) for mask in masks]
    rows_, cols_ = np.nonzero(masks[best])
    refined = each[best]
    if len(rows_):
        c0, c1, r0, r1 = cols_.min(), cols_.max() + 1, rows_.min(), rows_.max() + 1
        mc, mr = 0.05 * (c1 - c0), 0.05 * (r1 - r0)
        box = (max(0.0, c0 - mc), max(0.0, r0 - mr), min(1024.0, c1 + mc), min(1024.0, r1 + mr))
        mask2, _score = model.predict(embedding, [pixel], [1], box)
        refined = iou(object_of(mask2, window, point), truth)
    row = {'fid': feature.id(), 'set': 'A' if position % 2 == 0 else 'B', 'chosen': each[best], 'best_of_three': max(each),
           'refined': refined, 'areas': [int(mask.sum()) for mask in masks], 'scores': [round(s, 3) for s in scores]}
    rows.append(row)
    print(json.dumps(row), flush=True)

chosen = [r['chosen'] for r in rows]
summary = {'median_chosen': statistics.median(chosen), 'median_best_of_three': statistics.median(r['best_of_three'] for r in rows),
           'median_refined': statistics.median(r['refined'] for r in rows),
           'losers_over_0.05': sum(1 for r in rows if r['refined'] < r['chosen'] - 0.05),
           'chosen_is_best': sum(1 for r in rows if r['chosen'] == r['best_of_three'])}
summary['refine_adopted'] = (summary['median_refined'] - summary['median_chosen'] >= 0.02 and summary['losers_over_0.05'] <= 4)
print(json.dumps(summary), flush=True)
with open(output, 'w', encoding='utf-8') as stream:
    json.dump({'rows': rows, 'summary': summary}, stream)
os._exit(0)

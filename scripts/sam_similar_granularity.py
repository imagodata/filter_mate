"""Similar objects: the mask of SAM nearest the size of the clicked object, instead of the one SAM scores best.

Pre-registered 2026-11-11, before any run (decided by scripts/sam_similar_granularity_analysis.py):

- Why: judged by eye, the proposals that do not match a building are mostly the right kind of object with the wrong
  outline, a part of a roof or two roofs in one (scripts/sam_vision_judge.py). SAM proposes three masks for a point,
  roughly a part, the object and a group; the search knows the size it looks for, the clicked object's.
- Same 20 buildings, sets, truth and matching as scripts/sam_similar_candidates.py; every candidate drawn on the window
  of the click; the candidates of the search adopted on 2026-11-11 (colour patches, then the 10 best feature peaks).
- Each candidate is drawn twice: with the mask SAM scores best (as now, SamOnnxProvider.predict) and with the mask whose
  area is nearest the clicked object's, by ratio, read on the low resolution masks (SamOnnxProvider.predict_by_area).
  The clicked object keeps the mask SAM scores best in both.
- Both are replayed as SimilarObjectsTask runs (ratios 0.5 to 2 and same shape, appearance >= 0.68). No setting.
- Adopted if on set B (medians) either the recall gains at least 0.10 and the precision loses at most 0.05, or the
  precision gains at least 0.10 and the recall loses at most 0.05. Set A is reported too.

Confirmation, added 2026-11-11 after the first run and before the second: B passed the rule (recall 0.32 to 0.52,
precision 0.36 to 0.33) but A, used for no setting here, did not (precision 0.56 to 0.38, recall unchanged), and over
the 20 searches the variant adds 90 proposals of which 78 are not buildings. Set C: every building of 40 to 80 m² and
of 400 to 2000 m² inside the orthophoto (never used), by the same steps. Adopted only if the same rule holds on C.

Run by python-qgis.bat: argv = plugins folder, onnxruntime folder, models folder, ortho, buildings, output json,
and optionally the areas of the references, "80-400" by default, "40-80,400-2000" for set C.
"""
import json
import os
import sys
import time

plugins, deps, models, ortho, buildings, output = sys.argv[1:7]
BANDS = [tuple(float(v) for v in band.split('-')) for band in (sys.argv[7] if len(sys.argv) > 7 else '80-400').split(',')]
CONFIRMATION = len(sys.argv) > 7
sys.path.insert(0, plugins)
sys.path.append(deps)
if os.name != 'nt':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np  # noqa: E402
from qgis.core import (QgsApplication, QgsFeatureRequest, QgsGeometry, QgsMapSettings, QgsPointXY,  # noqa: E402
                       QgsRasterLayer, QgsRectangle, QgsVectorLayer)
from qgis.PyQt.QtGui import QColor  # noqa: E402

app = QgsApplication([], True)
app.initQgis()

from filter_mate.adapters.qgis.coverage_layers import raster_adapter, sam_model, segmentation  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.geometry_tools import mask_to_geometry  # noqa: E402
from filter_mate.ui.widgets.coverage_panels import raster_exploring_panel as panels  # noqa: E402

VIEW_HALF = 75.0

layer = QgsRasterLayer(ortho, 'ortho', 'gdal')
vector = QgsVectorLayer(f'{buildings}|layername=batiment_sl', 'batiment', 'ogr')
assert layer.isValid() and vector.isValid(), (layer.isValid(), vector.isValid())
extent = layer.extent()
raster = (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
bounds = QgsGeometry.fromRect(extent)
native = extent.width() / layer.width()
crs_wkt = layer.crs().toWkt()
model = sam_model.SamOnnxProvider(models)
panel = panels.RasterExploringPanel()
panel.set_summary(raster_adapter.read_raster_summary(layer))
panel.set_segmentation_readiness(True, True)
settings = QgsMapSettings()
settings.setDestinationCrs(layer.crs())
settings.setBackgroundColor(QColor(0, 0, 0, 255))

inner = QgsRectangle(extent.xMinimum() + 100, extent.yMinimum() + 100, extent.xMaximum() - 100, extent.yMaximum() - 100)
features = [f for f in vector.getFeatures(QgsFeatureRequest().setFilterRect(inner))
            if any(low <= f.geometry().area() <= high for low, high in BANDS)
            and not (CONFIRMATION and 80 <= f.geometry().area() <= 400)  # set C: none of the 20 already measured
            and inner.contains(f.geometry().boundingBox())]
features.sort(key=lambda f: f.id())
print(f'{len(features)} reference buildings, native cell {native:.3f} m', flush=True)


def outline(window, mask, x, y):
    """The part of ``mask`` under the point, clipped to the raster, as point_object keeps it; None without one."""
    geometry = mask_to_geometry(mask, window.geotransform(), crs_wkt, sieve_pixels=segmentation.SIEVE_PIXELS,
                                simplify_tolerance=window.cell * 0.5)
    parts = raster_adapter.geometry_parts(geometry)
    where = QgsGeometry.fromPointXY(QgsPointXY(x, y))
    near = [part for part in parts if part.distance(where) <= window.cell * 2.0]
    if not near or not mask.any():
        return None
    found = min(near, key=lambda part: part.distance(where)).intersection(bounds)
    return None if found.isEmpty() else found


def drawn(window, embedding, mask, x, y, reference_features):
    found = outline(window, mask, x, y)
    pooled = segmentation.pooled_features(embedding, mask)
    appearance = float(np.dot(pooled, reference_features)) if pooled is not None else None
    return {'wkt': found.asWkt(2) if found is not None else None,
            'appearance': None if appearance is None else round(appearance, 4)}


rows = []
for position, feature in enumerate(features):
    reference_building = feature.geometry()
    center = reference_building.centroid().asPoint()
    view = QgsRectangle(center.x() - VIEW_HALF, center.y() - VIEW_HALF, center.x() + VIEW_HALF, center.y() + VIEW_HALF)
    others = [f.geometry() for f in vector.getFeatures(QgsFeatureRequest().setFilterRect(view)) if f.id() != feature.id()]
    truth = [index for index, g in enumerate(others)
             if 0.5 * reference_building.area() <= g.area() <= 2.0 * reference_building.area()]
    point = reference_building.poleOfInaccessibility(0.25)[0].asPoint()
    window = segmentation.plan_window(point.x(), point.y(), raster, native, 2 * VIEW_HALF, model.input_size)
    rgb = segmentation.image_to_rgb(segmentation.render_window(settings, layer, window, lambda: False))
    embedding = model.embed(rgb)
    mask, _score = model.predict(embedding, [window.to_pixel(point.x(), point.y())], [1], None)
    clicked = outline(window, mask, point.x(), point.y())
    clicked_features = segmentation.pooled_features(embedding, mask)
    label = 'C' if CONFIRMATION else ('A' if position % 2 == 0 else 'B')
    row = {'fid': feature.id(), 'set': label, 'reference': reference_building.asWkt(2),
           'buildings': [g.asWkt(2) for g in others], 'truth': truth,
           'clicked': clicked.asWkt(2) if clicked is not None else None, 'candidates': []}
    if clicked is None or clicked_features is None:
        rows.append(row)
        print(json.dumps({'fid': feature.id(), 'clicked': None}), flush=True)
        continue
    target = clicked.area() / (window.cell * window.cell)
    criterion = panel.criterion_at(raster_adapter.identify_values(layer, point), {})
    colour = segmentation.similar_candidate_points(layer, criterion, clicked, view) if criterion else []
    peaks = segmentation.feature_candidate_points(embedding, window, clicked_features, view, clicked)
    begin = time.time()
    for source, points in (('colour', colour), ('feature', peaks)):
        for rank, (x, y) in enumerate(points):
            pixel = [window.to_pixel(x, y)]
            best, _ = model.predict(embedding, pixel, [1], None)
            sized, _ = model.predict_by_area(embedding, pixel, [1], None, target)
            row['candidates'].append({'source': source, 'rank': rank, 'similarity': None, 'x': round(x, 2),
                                      'y': round(y, 2), 'best': drawn(window, embedding, best, x, y, clicked_features),
                                      'sized': drawn(window, embedding, sized, x, y, clicked_features),
                                      'same_mask': bool((best == sized).all())})
    row['seconds'] = round(time.time() - begin, 1)
    rows.append(row)
    print(json.dumps({'fid': feature.id(), 'set': row['set'], 'truth': len(truth), 'candidates': len(row['candidates']),
                      'same_mask': sum(c['same_mask'] for c in row['candidates'])}), flush=True)

with open(output, 'w', encoding='utf-8') as stream:
    json.dump(rows, stream)
print('done', flush=True)
os._exit(0)

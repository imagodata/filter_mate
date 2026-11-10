"""Similar objects: candidates found in the features of SAM instead of the colour, and re-ranking by keep / reject.

Pre-registered 2026-11-11, before any run (decided by scripts/sam_similar_candidates_analysis.py, which reads the
JSON written here):

- The 20 buildings of 80 to 400 m² inside the 25 cm Cerdagne orthophoto, sorted by fid; set A = even positions,
  set B = odd positions (as sam_similar_appearance.py). Each is clicked at its pole of inaccessibility in a 150 m view
  centred on it. Truth and matching as before: the other BD TOPO buildings of the view within 0.5 to 2 times the
  reference area; an object matches a building at IoU >= 0.5.
- Every candidate is drawn by SAM on the window of the click (one encoding per search); the current search measured
  this same way is the baseline.
- Candidates: colour, as now (similar_candidate_points: at most 120, nearest first); feature: the local maxima (3 x 3)
  of the cosine between the encoder features of SAM pooled under the clicked object and each cell of the coarsest
  feature map, inside the view and outside the clicked object, best first. Every candidate is recorded with what SAM
  draws, so that each variant is replayed afterwards exactly as SimilarObjectsTask runs (a point inside an object
  already drawn is skipped, an object overlapping one by IoU >= 0.5 is the same, area and shape within the ratios
  0.5 to 2, then appearance >= a).
- Variants: colour (the baseline, a = 0.68), feature (the first N with cosine >= s), union (colour, then feature).
  Their settings (s, N, a) are chosen on A: the highest median recall whose median precision is at least the
  baseline's on A minus 0.05; ties go to fewer prompts. A variant is adopted if on B its median recall gains at least
  0.10 and its median precision loses at most 0.05 against the baseline on B, with a median number of prompts at most
  twice the baseline's.
- Re-ranking, no setting: a simulated user keeps or rejects the first 3 proposals of the baseline (oracle: it matches a
  building); each remaining proposal closer, by cosine, to the mean features of the rejected ones than to the mean of
  the kept ones and the clicked object is hidden. Adopted if on B the median precision of the remaining proposals
  gains at least 0.10 and their median recall loses at most 0.05.

Run by python-qgis.bat: argv = plugins folder, onnxruntime folder, models folder, ortho, buildings, output json.
"""
import json
import os
import sys
import time

plugins, deps, models, ortho, buildings, output = sys.argv[1:7]
sys.path.insert(0, plugins)
sys.path.append(deps)
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

FEATURE_FLOOR = 0.3  # feature candidates kept for the analysis; its thresholds are above
FEATURE_MAX = 200
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
            if 80 <= f.geometry().area() <= 400 and inner.contains(f.geometry().boundingBox())]
features.sort(key=lambda f: f.id())
print(f'{len(features)} reference buildings, native cell {native:.3f} m', flush=True)


def coarse_map(embedding):
    maps = [np.asarray(value) for value in embedding.values() if np.ndim(value) == 4]
    return min(maps, key=lambda value: value.shape[-1] * value.shape[-2])[0]


def draw(window, embedding, x, y):
    """As point_object and _looks_alike: (part under the point clipped to the raster, score, pooled features)."""
    begin = time.time()
    mask, score = model.predict(embedding, [window.to_pixel(x, y)], [1], None)
    geometry = mask_to_geometry(mask, window.geotransform(), crs_wkt, sieve_pixels=segmentation.SIEVE_PIXELS,
                                simplify_tolerance=window.cell * 0.5)
    parts = raster_adapter.geometry_parts(geometry)
    where = QgsGeometry.fromPointXY(QgsPointXY(x, y))
    near = [part for part in parts if part.distance(where) <= window.cell * 2.0]
    seconds = time.time() - begin
    if not near or not mask.any():
        return None, float(score), None, seconds
    found = min(near, key=lambda part: part.distance(where)).intersection(bounds)
    return (None if found.isEmpty() else found), float(score), segmentation.pooled_features(embedding, mask), seconds


def feature_candidates(window, embedding, reference_features, view, clicked):
    """Local maxima of the cosine between the clicked object's features and each cell of the coarsest map."""
    coarse = coarse_map(embedding)
    channels, height, width = coarse.shape
    cells = coarse.reshape(channels, -1)
    norms = np.linalg.norm(cells, axis=0)
    norms[norms == 0] = 1.0
    cosine = (reference_features @ (cells / norms)).reshape(height, width)
    padded = np.pad(cosine, 1, constant_values=-np.inf)
    neighbours = np.stack([padded[1 + dy:1 + dy + height, 1 + dx:1 + dx + width]
                           for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
    peaks = cosine >= neighbours.max(axis=0)
    step = window.size / height
    found = []
    for row, column in zip(*np.nonzero(peaks & (cosine >= FEATURE_FLOOR))):
        x, y = window.to_map((column + 0.5) * step, (row + 0.5) * step)
        point = QgsPointXY(x, y)
        if not view.contains(point) or clicked.contains(QgsGeometry.fromPointXY(point)):
            continue
        found.append((float(cosine[row, column]), x, y))
    found.sort(reverse=True)
    return found[:FEATURE_MAX]


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
    begin = time.time()
    rgb = segmentation.image_to_rgb(segmentation.render_window(settings, layer, window, lambda: False))
    embedding = model.embed(rgb)
    encode_seconds = time.time() - begin
    clicked, clicked_score, clicked_features, _seconds = draw(window, embedding, point.x(), point.y())
    row = {'fid': feature.id(), 'set': 'A' if position % 2 == 0 else 'B', 'reference': reference_building.asWkt(2),
           'buildings': [g.asWkt(2) for g in others], 'truth': truth, 'encode_seconds': round(encode_seconds, 2),
           'clicked': clicked.asWkt(2) if clicked is not None else None, 'candidates': []}
    if clicked is None or clicked_features is None:
        rows.append(row)
        print(json.dumps({'fid': feature.id(), 'clicked': None}), flush=True)
        continue
    row['clicked_iou'] = round(segmentation.overlap(clicked, reference_building), 3)
    row['clicked_features'] = [round(float(v), 4) for v in clicked_features]
    criterion = panel.criterion_at(raster_adapter.identify_values(layer, point), {})
    begin = time.time()
    colour = segmentation.similar_candidate_points(layer, criterion, clicked, view) if criterion else []
    colour_seconds = time.time() - begin
    begin = time.time()
    feature_points = feature_candidates(window, embedding, clicked_features, view, clicked)
    feature_seconds = time.time() - begin
    row.update(colour_seconds=round(colour_seconds, 2), feature_seconds=round(feature_seconds, 3))
    prompts = [('colour', rank, None, x, y) for rank, (x, y) in enumerate(colour)]
    prompts += [('feature', rank, similarity, x, y) for rank, (similarity, x, y) in enumerate(feature_points)]
    for source, rank, similarity, x, y in prompts:
        found, score, pooled, seconds = draw(window, embedding, x, y)
        appearance = float(np.dot(pooled, clicked_features)) if pooled is not None else None
        row['candidates'].append({
            'source': source, 'rank': rank, 'similarity': None if similarity is None else round(similarity, 4),
            'x': round(x, 2), 'y': round(y, 2), 'wkt': found.asWkt(2) if found is not None else None,
            'score': round(score, 4), 'appearance': None if appearance is None else round(appearance, 4),
            'features': None if pooled is None else [round(float(v), 3) for v in pooled],
            'seconds': round(seconds, 3)})
    rows.append(row)
    print(json.dumps({'fid': feature.id(), 'set': row['set'], 'truth': len(truth), 'clicked_iou': row['clicked_iou'],
                      'colour': len(colour), 'feature': len(feature_points)}), flush=True)

with open(output, 'w', encoding='utf-8') as stream:
    json.dump(rows, stream)
print('done', flush=True)
os._exit(0)

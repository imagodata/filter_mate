"""Features of every object the SAM similar search keeps, on 20 reference buildings (sets A and B).

Appearance (added 2026-11-10, before its run): cosine between the encoder features of SAM averaged under the
mask of the object and under the mask of the clicked object (coarsest feature map). Same rule: a threshold
chosen on A, judged on B, adopted if the median precision on B gains at least 0.10 and the recall loses at most 0.05.

Pre-registered 2026-11-10: the 20 buildings of 80 to 400 m² inside the Cerdagne orthophoto, sorted by fid;
set A = even positions (the 10 of the first bench), set B = odd positions (never measured). For each object kept
by the current search: the SAM score, the colour distance to the clicked object (largest absolute difference of the
mean R, G, B over the mask, 0-255), and whether it matches a BD TOPO building (IoU >= 0.5). Thresholds are chosen
on A, judged on B: adopted if the median precision on B gains at least 0.10 and the median recall loses at most 0.05.

Run by python-qgis.bat: argv = plugins folder, onnxruntime folder, models folder, ortho, buildings, output json.
"""
import json
import os
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
from filter_mate.adapters.qgis.coverage_layers.geometry_tools import mask_to_geometry
from filter_mate.ui.widgets.coverage_panels import raster_exploring_panel as panels

layer = QgsRasterLayer(ortho, 'ortho', 'gdal')
vector = QgsVectorLayer(f'{buildings}|layername=batiment_sl', 'batiment', 'ogr')
extent = layer.extent()
raster = (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
bounds = QgsGeometry.fromRect(extent)
native = extent.width() / layer.width()
crs_wkt = layer.crs().toWkt()
model = sam_model.SamOnnxProvider(models)
panel = panels.RasterExploringPanel()
panel.set_summary(raster_adapter.read_raster_summary(layer))
panel.set_segmentation_readiness(True, True)
RATIO, SHAPE = (0.5, 2.0), True
settings = QgsMapSettings()
settings.setDestinationCrs(layer.crs())
settings.setBackgroundColor(QColor(0, 0, 0, 255))

inner = QgsRectangle(extent.xMinimum() + 100, extent.yMinimum() + 100, extent.xMaximum() - 100, extent.yMaximum() - 100)
features = [f for f in vector.getFeatures(QgsFeatureRequest().setFilterRect(inner))
            if 80 <= f.geometry().area() <= 400 and inner.contains(f.geometry().boundingBox())]
features.sort(key=lambda f: f.id())
cache = {}


def encode(window):
    key = (window.x_min, window.y_max, window.cell)
    if key not in cache:
        rgb = segmentation.image_to_rgb(segmentation.render_window(settings, layer, window, lambda: False))
        cache.clear()
        cache[key] = (rgb, model.embed(rgb))
    return cache[key]


def pooled(embedding, mask):
    """Encoder features of SAM averaged under a mask, on the coarsest feature map; None when it holds nothing."""
    maps = [np.asarray(value) for value in embedding.values()]
    coarse = min(maps, key=lambda value: value.shape[-1] * value.shape[-2])[0]
    channels, height, width = coarse.shape
    size = mask.shape[0]
    cells = mask.reshape(height, size // height, width, size // width).mean(axis=(1, 3)) >= 0.5
    if not cells.any():
        return None
    vector = coarse[:, cells].mean(axis=1)
    return vector / (np.linalg.norm(vector) or 1.0)


def drawn(window, x, y):
    """(geometry, score, mean colour, features) of the object under a point, as point_geometry draws it."""
    rgb, embedding = encode(window)
    mask, score = model.predict(embedding, [window.to_pixel(x, y)], [1], None)
    geometry = mask_to_geometry(mask, window.geotransform(), crs_wkt, sieve_pixels=segmentation.SIEVE_PIXELS,
                                simplify_tolerance=window.cell * 0.5)
    parts = raster_adapter.geometry_parts(geometry)
    where = QgsGeometry.fromPointXY(QgsPointXY(x, y))
    near = [part for part in parts if part.distance(where) <= window.cell * 2.0]
    if not near or not mask.any():
        return None, score, None, None
    return min(near, key=lambda part: part.distance(where)), float(score), rgb[mask].mean(axis=0), pooled(embedding, mask)


rows = []
for position, feature in enumerate(features):
    reference_building = feature.geometry()
    center = reference_building.centroid().asPoint()
    view = QgsRectangle(center.x() - 75, center.y() - 75, center.x() + 75, center.y() + 75)
    others = [f.geometry() for f in vector.getFeatures(QgsFeatureRequest().setFilterRect(view)) if f.id() != feature.id()]
    truth = [g for g in others if RATIO[0] * reference_building.area() <= g.area() <= RATIO[1] * reference_building.area()]
    point = reference_building.poleOfInaccessibility(0.25)[0].asPoint()
    window = segmentation.plan_window(point.x(), point.y(), raster, native, 150.0, model.input_size)
    clicked, _score, colour, features_clicked = drawn(window, point.x(), point.y())
    row = {'fid': feature.id(), 'set': 'A' if position % 2 == 0 else 'B', 'truth': len(truth), 'objects': [],
           'truth_matched_by': []}
    if clicked is None:
        rows.append(row)
        continue
    criterion = panel.criterion_at(raster_adapter.identify_values(layer, point), {})
    candidates = segmentation.similar_candidate_points(layer, criterion, clicked, view) if criterion else []
    reference_area, reference_shape = clicked.area(), segmentation.compactness(clicked) if hasattr(segmentation, 'compactness') else None
    from filter_mate.adapters.qgis.coverage_layers.geometry_tools import compactness
    reference_shape = compactness(clicked)
    kept = [clicked]
    for found_window, members in segmentation.assign_windows(candidates, raster, window.cell, model.input_size):
        for index in members:
            x, y = candidates[index]
            where = QgsGeometry.fromPointXY(QgsPointXY(x, y))
            if any(found.contains(where) for found in kept):
                continue
            found, score, mean, features_found = drawn(found_window, x, y)
            if found is None or found.isEmpty():
                continue
            found = found.intersection(bounds)
            if found.isEmpty() or any(segmentation.overlap(found, other) >= segmentation.SAME_OBJECT_IOU for other in kept):
                continue
            if not segmentation.is_similar(found, reference_area, reference_shape, RATIO, SHAPE):
                continue
            kept.append(found)
            match = any(segmentation.overlap(found, other) >= 0.5 for other in others + [reference_building])
            cosine = (float(np.dot(features_found, features_clicked))
                      if features_found is not None and features_clicked is not None else 0.0)
            row['objects'].append({'score': round(score, 4), 'colour': round(float(np.abs(mean - colour).max()), 1),
                                   'appearance': round(cosine, 4),
                                   'match': match, 'wkt_index': len(kept) - 1})
            for t, building in enumerate(truth):
                if segmentation.overlap(found, building) >= 0.5:
                    row['truth_matched_by'].append([t, len(row['objects']) - 1])
    rows.append(row)
    print(json.dumps({k: (v if k != 'objects' else len(v)) for k, v in row.items() if k != 'truth_matched_by'}), flush=True)

with open(output, 'w', encoding='utf-8') as stream:
    json.dump(rows, stream)
print('done', flush=True)
os._exit(0)

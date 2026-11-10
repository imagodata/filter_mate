"""Similar objects on a real orthophoto: SAM engine against the colour engine, with BD TOPO buildings as reference.

Pre-registered (2026-11-10, before the run): 10 reference buildings of 80 to 400 m², the first ones by fid
spread across the ortho, each searched in a 150 m view centred on it, default ratios (0.5 to 2, same shape).
Truth: the other buildings intersecting the view whose area is within 0.5 to 2 times the reference.
A found object matches a building when their IoU is at least 0.5. Reported: precision (found objects that
match a building), recall (truth buildings matched), objects found, time. Expected: SAM more precise than
the colour engine; no decision rides on recall, which also depends on colour candidates.

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

from qgis.core import (QgsApplication, QgsFeatureRequest, QgsGeometry, QgsPointXY, QgsRasterLayer, QgsRectangle,
                       QgsVectorLayer)

app = QgsApplication([], True)
app.initQgis()

from dataclasses import replace
from filter_mate.adapters.qgis.coverage_layers import raster_adapter, sam_model, segmentation
from filter_mate.ui.widgets.coverage_panels import raster_exploring_panel as panels

layer = QgsRasterLayer(ortho, 'ortho', 'gdal')
vector = QgsVectorLayer(f'{buildings}|layername=batiment_sl', 'batiment', 'ogr')
assert layer.isValid() and vector.isValid(), (layer.isValid(), vector.isValid())
extent = layer.extent()
raster = (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
native = extent.width() / layer.width()
model = sam_model.SamOnnxProvider(models)
panel = panels.RasterExploringPanel()
panel.set_summary(raster_adapter.read_raster_summary(layer))
panel.set_segmentation_readiness(True, True)
RATIO, SHAPE = (0.5, 2.0), True

inner = QgsRectangle(extent.xMinimum() + 100, extent.yMinimum() + 100, extent.xMaximum() - 100, extent.yMaximum() - 100)
features = [f for f in vector.getFeatures(QgsFeatureRequest().setFilterRect(inner))
            if 80 <= f.geometry().area() <= 400 and inner.contains(f.geometry().boundingBox())]
features.sort(key=lambda f: f.id())
step = max(1, len(features) // 10)
references = features[::step][:10]
print(f'{len(features)} candidate references, {len(references)} kept, native cell {native:.3f} m', flush=True)


def matches(geometry, others):
    return [other for other in others if segmentation.overlap(geometry, other) >= 0.5]


def measure(found, truth, everything):
    precise = sum(1 for geometry in found if matches(geometry, everything))
    recalled = sum(1 for geometry in truth if matches(geometry, found))
    return {'found': len(found), 'precision': round(precise / len(found), 3) if found else None,
            'recall': round(recalled / len(truth), 3) if truth else None, 'truth': len(truth)}


results = []
for feature in references:
    ref_geometry = feature.geometry()
    center = ref_geometry.centroid().asPoint()
    view = QgsRectangle(center.x() - 75, center.y() - 75, center.x() + 75, center.y() + 75)
    others = [f.geometry() for f in vector.getFeatures(QgsFeatureRequest().setFilterRect(view)) if f.id() != feature.id()]
    truth = [g for g in others if RATIO[0] * ref_geometry.area() <= g.area() <= RATIO[1] * ref_geometry.area()]
    point = ref_geometry.poleOfInaccessibility(0.25)[0].asPoint()
    row = {'fid': feature.id(), 'area': round(ref_geometry.area(), 1)}
    # SAM: the clicked object, then the search.
    begin = time.time()
    window = segmentation.plan_window(point.x(), point.y(), raster, native, 150.0, model.input_size)
    embed = segmentation.SegmentationEmbedTask(layer.source(), 'gdal', layer.renderer().clone(), layer.crs(), window, model,
                                               lambda t, ok: None)
    if not embed.run():
        row['error'] = embed.error
        results.append(row)
        continue
    session = segmentation.SegmentationSession(model, window, embed.embedding)
    session.add_point(point.x(), point.y(), True)
    session.predict()
    clicked = segmentation.point_geometry(model, embed.embedding, window, point.x(), point.y(), layer.crs().toWkt())
    row['clicked_iou'] = round(segmentation.overlap(clicked, ref_geometry), 3) if clicked else 0.0
    criterion = panel.criterion_at(raster_adapter.identify_values(layer, point), {})
    candidates = segmentation.similar_candidate_points(layer, criterion, clicked, view) if clicked and criterion else []
    task = segmentation.SimilarObjectsTask(layer.source(), 'gdal', layer.renderer().clone(), layer.crs(), model, raster,
                                           window.cell, candidates, clicked.asWkt() if clicked else 'POLYGON EMPTY',
                                           RATIO, SHAPE, lambda t, ok: None)
    ok = task.run() if candidates else True
    found = [QgsGeometry.fromWkt(wkt) for wkt in task.wkts] if candidates else []
    row['sam'] = dict(measure(found, truth, others + [ref_geometry]), candidates=len(candidates), seconds=round(time.time() - begin, 1),
                      ok=bool(ok))
    # Colour engine: the same click, the live similar objects of the panel.
    begin = time.time()
    seed = ((point.x(), point.y()),)
    selection = replace(criterion, seeds=seed, objects=(replace(criterion, seeds=seed),), similar=RATIO, shape=SHAPE)
    patches = raster_adapter.layer_object_geometry(layer, selection).geometry
    area = QgsGeometry.fromRect(view)
    colour = [part for part in raster_adapter.geometry_parts(patches)
              if part.intersects(area) and not part.contains(QgsGeometry.fromPointXY(QgsPointXY(point)))]
    row['colour'] = dict(measure(colour, truth, others + [ref_geometry]), seconds=round(time.time() - begin, 1))
    results.append(row)
    print(json.dumps(row), flush=True)

with open(output, 'w', encoding='utf-8') as stream:
    json.dump(results, stream, indent=1)
print('done', flush=True)
os._exit(0)

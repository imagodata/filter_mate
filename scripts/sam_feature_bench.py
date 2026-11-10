"""SAM guided by the features of a vector layer: which prompt to draw a polygon from.

Pre-registered 2026-11-10, before any run: 40 buildings of the BD TOPO on the 25 cm Cerdagne orthophoto,
50 to 2000 m2, 100 m inside the image, every k-th by feature id. The shipped code is measured
(segmentation.prompt_of / plan_prompts / prompt_object), the windows planned once on the bare boxes:

- A: the bounding box of the footprint and the point inside it (the default);
- B: the bounding box only;
- C: the bounding box grown by 10 % of its size, and the point.
- D (reference for point layers): the point only.

B or C replaces A if its median IoU with the footprint gains at least 0.02 and at most 4 of the 40
buildings lose more than 0.05. The footprint is the BD TOPO one, not the roof seen from above: the
IoU measures the agreement, not a truth.

Run by python-qgis.bat: argv = plugins folder, onnxruntime folder, models folder, ortho, buildings, output json.
"""
import json
import os
import statistics
import sys
import time

plugins, deps, models, ortho, buildings, output = sys.argv[1:7]
sys.path.insert(0, plugins)
sys.path.append(deps)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from qgis.core import QgsApplication, QgsFeatureRequest, QgsMapSettings, QgsRasterLayer, QgsRectangle, QgsVectorLayer
from qgis.PyQt.QtGui import QColor

app = QgsApplication([], True)
app.initQgis()
from filter_mate.adapters.qgis.coverage_layers import sam_model, segmentation

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
candidates = sorted((f for f in vector.getFeatures(QgsFeatureRequest().setFilterRect(inner))
                     if 50 <= f.geometry().area() <= 2000 and inner.contains(f.geometry().boundingBox())),
                    key=lambda f: f.id())
step = max(1, len(candidates) // 40)
features = candidates[::step][:40]
truths = [f.geometry() for f in features]
variants = {
    'A': ([segmentation.prompt_of(t) for t in truths], True),
    'B': ([segmentation.prompt_of(t) for t in truths], False),
    'C': ([segmentation.prompt_of(t, 0.10) for t in truths], True),
    'D': ([segmentation.Prompt(p.x, p.y) for p in (segmentation.prompt_of(t) for t in truths)], True),
}
windows = segmentation.plan_prompts(variants['A'][0], raster, native, model.input_size)
print(f'{len(candidates)} candidates, {len(features)} buildings, {len(windows)} windows', flush=True)

scores = {name: [0.0] * len(features) for name in variants}
encode_seconds = []
for window, members in windows:
    begin = time.time()
    rgb = segmentation.image_to_rgb(segmentation.render_window(settings, layer, window, lambda: False))
    embedding = model.embed(rgb)
    encode_seconds.append(time.time() - begin)
    for index in members:
        for name, (prompts, with_point) in variants.items():
            geometry, _score = segmentation.prompt_object(model, embedding, window, prompts[index], crs_wkt, with_point)
            scores[name][index] = round(segmentation.overlap(geometry, truths[index]), 4) if geometry is not None else 0.0
rows = [{'fid': f.id(), 'area': round(t.area()), **{name: scores[name][i] for name in variants}}
        for i, (f, t) in enumerate(zip(features, truths))]
for row in rows:
    print(json.dumps(row), flush=True)
summary = {f'median_{name}': statistics.median(scores[name]) for name in variants}
for name in ('B', 'C'):
    summary[f'losers_{name}'] = sum(1 for a, other in zip(scores['A'], scores[name]) if other < a - 0.05)
    summary[f'adopt_{name}'] = (summary[f'median_{name}'] - summary['median_A'] >= 0.02 and summary[f'losers_{name}'] <= 4)
summary['windows'] = len(windows)
summary['median_encode_seconds'] = round(statistics.median(encode_seconds), 2)
print(json.dumps(summary), flush=True)
with open(output, 'w', encoding='utf-8') as stream:
    json.dump({'rows': rows, 'summary': summary}, stream)
os._exit(0)

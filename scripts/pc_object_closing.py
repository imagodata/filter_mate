"""Objects of a point cloud: grown by the closing of their gaps, or shrunk back; cells of 2 m or 1 m. Against blocks.

Pre-registered 2026-11-11, before any run:

- Why: on the bench of the same shape (scripts/pc_similar_shape.py) the clicked object overlapped its BD TOPO
  building at a median IoU of 0.13. Two causes are measured here: the objects are grown by one cell on each side
  (the gaps between the points are closed by a dilation, never shrunk back), and in a village the buildings share
  their walls, which no class of points can split. The truth is therefore the block: the BD TOPO buildings of the
  tile buffered by 0.5 m and merged, each block being the union of the buildings it holds.
- Variants: V0 cells of 2 m grown (today); V1 2 m, shrunk back by one cell (erode_cells=1: grown, holes filled,
  shrunk, point_cloud_objects.grow_object and point_cloud_footprint.footprint_geometry); V2 1 m grown; V3 1 m shrunk
  back. The clicked object is object_footprint(class 6) at the pole of inaccessibility of the largest building of the
  block; the similar objects are the parts of class_footprint(class 6) of the tile within the default ratios (0.5 to
  2) of its area, same shape on (the default), the clicked object itself left out.
- Sets: the blocks of 80 to 600 m² lying 64 m or more inside the tile, sorted by the smallest fid of their buildings;
  A the first 20, B the next 20.
- Measures, medians per set: IoU of the clicked object (holes filled) with its block; similar objects precision (found
  objects matching another block at IoU >= 0.5) and recall (other blocks of 0.5 to 2 times the reference block's
  area matched); time of a click; time and truncation of the class footprint.
- Rule: a variant replaces V0 when, on A and on B each, the median IoU of the clicked object rises by 0.05 or more
  and the median precision and recall of the similar objects fall by 0.05 at most; a 1 m variant must also read the
  class footprint untruncated in 30 s at most, with a median click of 3 s at most. Among the variants that pass, the
  one with the higher mean of the two median IoUs; a 2 m variant is kept over a 1 m one within 0.02.

Run with QGIS (offscreen): argv = plugins folder, point cloud, buildings, output json.
"""
import json
import os
import statistics
import sys
import time

plugins, cloud_path, buildings, output = sys.argv[1:5]
sys.path.insert(0, plugins)
if os.name != 'nt':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from qgis.core import (QgsApplication, QgsFeatureRequest, QgsGeometry, QgsPointCloudLayer,  # noqa: E402
                       QgsRectangle, QgsVectorLayer)

app = QgsApplication([], False)
app.initQgis()

from filter_mate.adapters.qgis.coverage_layers import point_cloud_objects as objects  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.geometry_tools import compactness  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.segmentation import overlap  # noqa: E402

RATIO = (0.5, 2.0)
BUILDING = 6
VARIANTS = {'V0': (2.0, 0), 'V1': (2.0, 1), 'V2': (1.0, 0), 'V3': (1.0, 1)}

layer = QgsPointCloudLayer(cloud_path, 'lidar', 'copc')
vector = QgsVectorLayer(f'{buildings}|layername=batiment_sl', 'batiment', 'ogr')
assert layer.isValid() and vector.isValid(), (layer.isValid(), vector.isValid())
assert layer.crs() == vector.crs(), (layer.crs().authid(), vector.crs().authid())
extent = layer.extent()
inner = QgsRectangle(extent.xMinimum() + 64, extent.yMinimum() + 64, extent.xMaximum() - 64, extent.yMaximum() - 64)
features = list(vector.getFeatures(QgsFeatureRequest().setFilterRect(extent)))
merged = QgsGeometry.unaryUnion([f.geometry().buffer(0.5, 4) for f in features])
blocks = []
for part in merged.asGeometryCollection():
    members = [f for f in features if f.geometry().intersects(part)]
    if not members:
        continue
    shape = QgsGeometry.unaryUnion([f.geometry() for f in members])
    largest = max(members, key=lambda f: f.geometry().area())
    blocks.append({'fid': min(f.id() for f in members), 'buildings': len(members), 'geometry': shape,
                   'area': shape.area(), 'click': largest.geometry().poleOfInaccessibility(0.25)[0].asPoint()})
blocks.sort(key=lambda block: block['fid'])
candidates = [b for b in blocks if 80 <= b['area'] <= 600 and inner.contains(b['geometry'].boundingBox())]
sets = {'A': candidates[:20], 'B': candidates[20:40]}
print(f"{len(features)} buildings, {len(blocks)} blocks, {len(candidates)} candidates, "
      f"A {len(sets['A'])}, B {len(sets['B'])}", flush=True)


def measure(found, reference):
    others = [b['geometry'] for b in blocks if b is not reference]
    truth = [b['geometry'] for b in blocks if b is not reference
             and RATIO[0] * reference['area'] <= b['area'] <= RATIO[1] * reference['area']]
    precise = sum(1 for part in found if any(overlap(part, other) >= 0.5 for other in others))
    recalled = sum(1 for block in truth if any(overlap(part, block) >= 0.5 for part in found))
    return (precise / len(found) if found else None, recalled / len(truth) if truth else None, len(found), len(truth))


def median(values):
    values = [value for value in values if value is not None]
    return round(statistics.median(values), 3) if values else None


results = {}
for name, (resolution, erode) in VARIANTS.items():
    begin = time.time()
    footprint = objects.class_footprint(layer, BUILDING, resolution=resolution, erode_cells=erode)
    footprint_time = time.time() - begin
    print(f'{name}: class footprint in {footprint_time:.1f} s, cells {footprint.cell_size}, '
          f'{footprint.points_read} points, truncated {footprint.truncated}', flush=True)
    rows = []
    for set_name, references in sets.items():
        for block in references:
            begin = time.time()
            clicked = objects.object_footprint(layer, block['click'].x(), block['click'].y(), BUILDING,
                                               resolution=resolution, erode_cells=erode)
            row = {'set': set_name, 'fid': block['fid'], 'buildings': block['buildings'],
                   'area': round(block['area'], 1), 'click_s': round(time.time() - begin, 2)}
            if clicked.geometry is None or clicked.geometry.isEmpty():
                row['iou'] = 0.0
                rows.append(row)
                continue
            shape = objects.filled_part(clicked.geometry)
            row['iou'] = round(overlap(shape, objects.filled_part(block['geometry'])), 3)
            row['object_area'] = round(shape.area(), 1)
            found, _total = objects.similar_parts(footprint.geometry, [shape.area()], RATIO, [compactness(shape)])
            found = [part for part in found if overlap(part, shape) < 0.5]
            row['precision'], row['recall'], row['found'], row['truth'] = measure(found, block)
            rows.append(row)
    summary = {}
    for set_name in sets:
        mine = [row for row in rows if row['set'] == set_name]
        summary[set_name] = {key: median([row.get(key) for row in mine])
                             for key in ('iou', 'precision', 'recall', 'click_s', 'found', 'object_area', 'area')}
    results[name] = {'resolution': resolution, 'erode_cells': erode, 'footprint_s': round(footprint_time, 1),
                     'truncated': footprint.truncated, 'cell_size': footprint.cell_size, 'summary': summary,
                     'rows': rows}
    print(name, json.dumps(summary), flush=True)


def passes(name):
    base, variant = results['V0'], results[name]
    for set_name in sets:
        mine, ref = variant['summary'][set_name], base['summary'][set_name]
        if (mine['iou'] or 0) < (ref['iou'] or 0) + 0.05:
            return False
        for key in ('precision', 'recall'):
            if (mine[key] or 0) < (ref[key] or 0) - 0.05:
                return False
    if variant['resolution'] < 2.0:
        if variant['truncated'] or variant['footprint_s'] > 30:
            return False
        if any((variant['summary'][s]['click_s'] or 0) > 3 for s in sets):
            return False
    return True


def score(name):
    return statistics.mean([results[name]['summary'][s]['iou'] or 0 for s in sets])


passing = [name for name in ('V1', 'V2', 'V3') if passes(name)]
chosen = 'V0'
if passing:
    chosen = max(passing, key=score)
    coarse = [name for name in passing if results[name]['resolution'] >= 2.0]
    if results[chosen]['resolution'] < 2.0 and coarse and score(chosen) - max(score(n) for n in coarse) <= 0.02:
        chosen = max(coarse, key=score)
print('passing', passing, 'chosen', chosen, flush=True)
with open(output, 'w', encoding='utf-8') as stream:
    json.dump({'results': results, 'passing': passing, 'chosen': chosen,
               'blocks': len(blocks), 'candidates': len(candidates)}, stream, indent=1)
print('done', flush=True)
os._exit(0)

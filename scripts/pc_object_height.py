"""Objects of a point cloud cut where the roof height jumps between two cells: stage 1, the clicked object.

Pre-registered 2026-11-11, before any run on set B. Sets, blocks and clicks of scripts/pc_object_closing.py.

- Explored on set A only (an exploration script, 2026-11-11): at the defaults (1 m, shrunk back), cutting the patch
  under the click where the highest points of two adjacent cells differ by more than T (a cell without a point taking
  the highest of its neighbours, three times) gave a median IoU with the block of 0.536 (no cut), 0.685 (T = 1 m),
  0.733 (1.25 m), 0.708 (1.5 m), 0.655 (2 m), 0.655 (2.5 m); with 1.25 m, 8 clicks of 20 better by more than 0.1 and
  2 worse. T = 1.25 m is chosen, the best median on A.
- Stage 1 rule, on set B: the median IoU of the clicked object with its block rises by 0.05 or more with the cut at
  1.25 m, and 3 clicks of 20 at most lose more than 0.1. Failing it, the cut is not adopted.
- Stage 2, only if stage 1 passes: the same cut on the footprint of the class, then scripts/pc_object_closing.py
  again, the cut against no cut: on A and on B each, the median precision and recall of the similar objects fall by
  0.05 at most.

Run with QGIS (offscreen): argv = plugins folder, point cloud, buildings, output json.

Result, 2026-11-11, Docker qgis/qgis:latest (QGIS 4.3): A, median IoU 0.536 -> 0.733, 8 better, 2 worse (as
explored); B, 0.786 -> 0.626, 3 better, 7 worse. Stage 1 FAILED: the cut is not adopted, stage 2 not run. On B the
blocks were mostly already found whole, and a cut at 1.25 m splits roofs of one building (steep pitches, dormers,
a lower annex of the same block); on A it split the dense core. The objects stay as they are.
"""
import json
import os
import statistics
import sys

plugins, cloud_path, buildings, output = sys.argv[1:5]
sys.path.insert(0, plugins)
if os.name != 'nt':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from qgis.core import (QgsApplication, QgsDoubleRange, QgsFeatureRequest, QgsGeometry, QgsPointCloudLayer,  # noqa: E402
                       QgsRectangle, QgsVectorLayer)

app = QgsApplication([], False)
app.initQgis()

import numpy as np  # noqa: E402

from filter_mate.adapters.qgis.coverage_layers import point_cloud_objects as objects  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.geometry_tools import mask_to_geometry  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.segmentation import overlap  # noqa: E402
from filter_mate.adapters.qgis.point_cloud_layer_adapter import class_code  # noqa: E402

BUILDING = 6
CUT = 1.25

layer = QgsPointCloudLayer(cloud_path, 'lidar', 'copc')
vector = QgsVectorLayer(f'{buildings}|layername=batiment_sl', 'batiment', 'ogr')
assert layer.isValid() and vector.isValid()
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
    blocks.append({'fid': min(f.id() for f in members), 'geometry': shape, 'area': shape.area(),
                   'click': largest.geometry().poleOfInaccessibility(0.25)[0].asPoint()})
blocks.sort(key=lambda block: block['fid'])
candidates = [b for b in blocks if 80 <= b['area'] <= 600 and inner.contains(b['geometry'].boundingBox())]
sets = {'A': candidates[:20], 'B': candidates[20:40]}
provider = layer.dataProvider()
crs = layer.crs().toWkt()


def cut_region(region, top_z, start, cut):
    """The cells of ``region`` reached from ``start`` without crossing a jump of more than ``cut``."""
    size = region.shape
    keep = np.zeros_like(region)
    keep[start] = True
    stack = [start]
    while stack:
        r, c = stack.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < size[0] and 0 <= nc < size[1]) or keep[nr, nc] or not region[nr, nc]:
                continue
            a, b = top_z[r, c], top_z[nr, nc]
            if not np.isnan(a) and not np.isnan(b) and abs(a - b) > cut:
                continue
            keep[nr, nc] = True
            stack.append((nr, nc))
    return keep


rows = []
for set_name, references in sets.items():
    for block in references:
        seen = {}

        def read(xmin, ymin, xmax, ymax):
            area = QgsRectangle(xmin, ymin, xmax, ymax)
            area.grow(0.5)
            points = provider.identify(objects.OBJECT_RESOLUTION, QgsGeometry.fromRect(area), QgsDoubleRange(),
                                       objects.OBJECT_POINTS_LIMIT)
            points = [p for p in points if class_code(p.get('Classification')) == BUILDING]
            seen['x'] = np.array([float(p['X']) for p in points])
            seen['y'] = np.array([float(p['Y']) for p in points])
            seen['z'] = np.array([float(p['Z']) for p in points])
            return seen['x'], seen['y']

        x, y = block['click'].x(), block['click'].y()
        grid = objects.grow_object(read, x, y, objects.OBJECT_RESOLUTION, objects.OBJECT_WINDOW_START,
                                   objects.OBJECT_WINDOW_MAX, erode_cells=objects.OBJECT_ERODE_CELLS)
        row = {'set': set_name, 'fid': block['fid'], 'area': round(block['area'], 1)}
        if grid is None:
            row['iou'] = row['iou_cut'] = 0.0
            rows.append(row)
            continue
        left, cell, _r1, top, _r2, _m = grid.geotransform
        top_z = np.full(grid.region.shape, np.nan)
        cols = np.floor((seen['x'] - left) / cell).astype(int)
        rws = np.floor((top - seen['y']) / cell).astype(int)
        inside = (cols >= 0) & (cols < top_z.shape[1]) & (rws >= 0) & (rws < top_z.shape[0])
        for r, c, z in zip(rws[inside], cols[inside], seen['z'][inside]):
            if np.isnan(top_z[r, c]) or z > top_z[r, c]:
                top_z[r, c] = z
        for _ in range(3):
            padded = np.pad(top_z, 1, constant_values=np.nan)
            near = np.nanmax(np.stack([padded[:-2, 1:-1], padded[2:, 1:-1], padded[1:-1, :-2], padded[1:-1, 2:]]),
                             axis=0)
            top_z = np.where(np.isnan(top_z) & grid.region, near, top_z)
        start = (int(np.floor((top - y) / cell)), int(np.floor((x - left) / cell)))
        if not grid.region[start]:
            found = np.argwhere(grid.region)
            start = tuple(found[np.argmin(((found - np.array(start)) ** 2).sum(axis=1))])
        reference = objects.filled_part(block['geometry'])
        for key, region in (('iou', grid.region), ('iou_cut', cut_region(grid.region, top_z, start, CUT))):
            shape = objects.filled_part(mask_to_geometry(region, grid.geotransform, crs, simplify_tolerance=0.5))
            row[key] = round(overlap(shape, reference), 3)
        rows.append(row)
        print(json.dumps(row), flush=True)

summary = {}
for set_name in sets:
    mine = [row for row in rows if row['set'] == set_name]
    summary[set_name] = {'iou': statistics.median(r['iou'] for r in mine),
                         'iou_cut': statistics.median(r['iou_cut'] for r in mine),
                         'worse': sum(1 for r in mine if r['iou_cut'] < r['iou'] - 0.1),
                         'better': sum(1 for r in mine if r['iou_cut'] > r['iou'] + 0.1)}
    print(set_name, json.dumps(summary[set_name]), flush=True)
b = summary['B']
passed = b['iou_cut'] >= b['iou'] + 0.05 and b['worse'] <= 3
print('stage 1', 'PASSED' if passed else 'FAILED', flush=True)
with open(output, 'w', encoding='utf-8') as stream:
    json.dump({'rows': rows, 'summary': summary, 'stage1': passed, 'cut': CUT}, stream, indent=1)
print('done', flush=True)
os._exit(0)

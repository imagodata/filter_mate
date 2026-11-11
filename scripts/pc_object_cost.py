"""Cost of the objects of a point cloud in cells of 1 m against 2 m, on the classes other than buildings.

Written 2026-11-11 after scripts/pc_object_closing.py chose cells of 1 m shrunk back (V3) on buildings, before any
run of this one. That rule asked, for cells of 1 m, a class footprint read untruncated in 30 s at most and a median
click of 3 s at most; it was measured on class 6 only, while the module notes 49 s for the vegetation of the tile at
1 m. Same criteria here, per class of the tile among 3, 4, 5 (vegetation) and 2 (ground):
the class footprint at 2 m and at 1 m (shrunk back), its time, points and truncation; ten clicks at the poles of
inaccessibility of the ten largest parts of the 2 m footprint lying 64 m inside the tile, their median time at 1 m.
A class passing both keeps 1 m; one failing either keeps cells of 2 m (shrunk back).

Run with QGIS (offscreen): argv = plugins folder, point cloud, output json.
"""
import json
import os
import statistics
import sys
import time

plugins, cloud_path, output = sys.argv[1:4]
sys.path.insert(0, plugins)
if os.name != 'nt':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from qgis.core import QgsApplication, QgsPointCloudLayer, QgsRectangle  # noqa: E402

app = QgsApplication([], False)
app.initQgis()

from filter_mate.adapters.qgis.coverage_layers import point_cloud_objects as objects  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.raster_adapter import geometry_parts  # noqa: E402

layer = QgsPointCloudLayer(cloud_path, 'lidar', 'copc')
assert layer.isValid()
extent = layer.extent()
inner = QgsRectangle(extent.xMinimum() + 64, extent.yMinimum() + 64, extent.xMaximum() - 64, extent.yMaximum() - 64)
results = {}
for code in (6, 5, 4, 3, 2):
    row = {}
    coarse = None
    for resolution in (2.0, 1.0):
        begin = time.time()
        footprint = objects.class_footprint(layer, code, resolution=resolution, erode_cells=1)
        row[f'footprint_{resolution:g}m'] = {'s': round(time.time() - begin, 1), 'points': footprint.points_read,
                                             'truncated': footprint.truncated, 'cell': footprint.cell_size}
        if resolution == 2.0:
            coarse = footprint
        print(code, resolution, row[f'footprint_{resolution:g}m'], flush=True)
    parts = sorted([part for part in geometry_parts(coarse.geometry) if inner.contains(part.boundingBox())],
                   key=lambda part: -part.area())[:10]
    clicks = []
    for part in parts:
        point = part.poleOfInaccessibility(0.5)[0].asPoint()
        begin = time.time()
        objects.object_footprint(layer, point.x(), point.y(), code, resolution=1.0, erode_cells=1)
        clicks.append(time.time() - begin)
    row['click_1m_median_s'] = round(statistics.median(clicks), 2) if clicks else None
    row['click_1m_max_s'] = round(max(clicks), 2) if clicks else None
    fine = row['footprint_1m']
    row['keeps_1m'] = bool(clicks) and not fine['truncated'] and fine['s'] <= 30 and row['click_1m_median_s'] <= 3
    results[code] = row
    print(code, json.dumps(row), flush=True)
with open(output, 'w', encoding='utf-8') as stream:
    json.dump(results, stream, indent=1)
print('done', flush=True)
os._exit(0)

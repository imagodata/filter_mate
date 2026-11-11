"""Cost of the objects of a point cloud in cells of 1 m against 2 m, on the classes other than buildings.

Written 2026-11-11 after scripts/pc_object_closing.py chose cells of 1 m shrunk back (V3) on buildings, before any
run of this one. That rule asked, for cells of 1 m, a class footprint read untruncated in 30 s at most and a median
click of 3 s at most; it was measured on class 6 only, while the module notes 49 s for the vegetation of the tile at
1 m. Same criteria here, per class of the tile among 3, 4, 5 (vegetation) and 2 (ground):
the class footprint at 2 m and at 1 m (shrunk back), its time, points and truncation; ten clicks at the poles of
inaccessibility of the ten largest parts of the 2 m footprint lying 64 m inside the tile, their median time at 1 m.
A class passing both keeps 1 m; one failing either keeps cells of 2 m (shrunk back).

Run with QGIS (offscreen): argv = plugins folder, point cloud, output json.

Result, 2026-11-11, Docker qgis/qgis:latest (QGIS 4.3), class footprint at 2 m then 1 m, points at 2 m, clicks at 1 m:

    class 6 buildings          2.2 s  25 781    4.1 s    click 0.99 s (2.35 s max)   keeps 1 m
    class 5 high vegetation    8.1 s  182 406   55.4 s   click 1.59 s (3.01 s max)   2 m
    class 4 medium vegetation  2.0 s  15 488    7.8 s    click 1.87 s (4.01 s max)   keeps 1 m
    class 3 low vegetation     2.2 s  13 047    9.6 s    click 0.50 s (3.80 s max)   keeps 1 m
    class 2 ground             29.2 s 226 586   93.0 s   no part inside the tile     2 m

Clicks pass for every class: they are read at 1 m. The footprint is a class of the tile, whose density changes from a
tile to the next: point_cloud_objects.class_footprint reads it at 2 m and again at 1 m for a class of 50 000 points at
most at 2 m (FINE_CLASS_POINTS, chosen after this run from its rates: 14 000 to 22 000 points a second at 1 m, so some
200 000 points in 10 to 15 s). A denser class stays at 2 m and its clicked objects are measured again in those cells.

Run again after the review (geometry_tools.shrink_back, see scripts/pc_object_closing.py): footprints at 1 m of 4.6 s
(class 6), 61.8 s (5), 5.9 s (4), 7.6 s (3), 97.2 s (2); median clicks of 1.13, 2.33, 1.99, 2.23 and 0.52 s (5.1 s at
most). Same classes keep 1 m.
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

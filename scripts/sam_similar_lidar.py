"""The LiDAR under the searches of the SAM similar objects bench: the class of each clicked object and its footprint.

Run with QGIS (offscreen) on the JSON of scripts/sam_similar_candidates.py; writes, per search (fid, set), the
dominant class of the LiDAR points inside the clicked object and the footprint of that class (and of class 6) over
the 150 m view of the search, in the cells of the point cloud objects (point_cloud_objects: 1 m, shrunk back), as
WKT. scripts/sam_similar_lidar_analysis.py then replays the search offline.

    argv = plugins folder, point cloud, candidates json, output json
"""
import collections
import json
import os
import sys
import time

plugins, cloud_path, candidates_path, output = sys.argv[1:5]
sys.path.insert(0, plugins)
if os.name != 'nt':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from qgis.core import QgsApplication, QgsDoubleRange, QgsGeometry, QgsPointCloudLayer  # noqa: E402

app = QgsApplication([], False)
app.initQgis()

from filter_mate.adapters.qgis.coverage_layers import point_cloud_objects as objects  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.point_cloud_footprint import (  # noqa: E402
    footprint_geometry, open_point_cloud)
from filter_mate.adapters.qgis.point_cloud_layer_adapter import class_code  # noqa: E402

VIEW_HALF = 75.0  # the 150 m view of the bench

layer = QgsPointCloudLayer(cloud_path, 'lidar', 'copc')
assert layer.isValid()
rows = json.load(open(candidates_path, encoding='utf-8'))
footprints = {}


def class_footprint_in(code, extent):
    copy = open_point_cloud(layer.source(), 'objects', layer.providerType())
    assert copy.setSubsetString(objects.class_subset(code))
    result = footprint_geometry(copy, objects.OBJECT_RESOLUTION, extent=extent,
                                dilate_cells=objects.OBJECT_DILATE_CELLS, erode_cells=objects.OBJECT_ERODE_CELLS,
                                points_limit=objects.CLASS_POINTS_LIMIT)
    return result


out = []
for row in rows:
    record = {'fid': row['fid'], 'set': row['set']}
    if not row.get('clicked'):
        out.append(record)
        continue
    clicked = QgsGeometry.fromWkt(row['clicked'])
    view = QgsGeometry.fromWkt(row['reference']).boundingBox()
    view.grow(VIEW_HALF)
    begin = time.time()
    points = layer.dataProvider().identify(objects.OBJECT_RESOLUTION, clicked, QgsDoubleRange(), 200000)
    counts = collections.Counter(class_code(point.get('Classification')) for point in points)
    dominant = counts.most_common(1)[0][0] if counts else None
    record['classes'] = {str(code): count for code, count in counts.most_common()}
    record['dominant'] = dominant
    for code in sorted({dominant, 6} - {None}):
        result = class_footprint_in(code, view)
        record[f'footprint_{code}'] = result.geometry.asWkt(2) if not result.geometry.isEmpty() else ''
        record[f'truncated_{code}'] = result.truncated
    record['seconds'] = round(time.time() - begin, 2)
    out.append(record)
    print(json.dumps({k: v for k, v in record.items() if not k.startswith('footprint')}), flush=True)
with open(output, 'w', encoding='utf-8') as stream:
    json.dump(out, stream)
print('done', flush=True)
os._exit(0)

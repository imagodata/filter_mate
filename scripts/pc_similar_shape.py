"""Similar objects of a point cloud: the area alone, or the area and the shape (compactness), against BD TOPO buildings.

Pre-registered 2026-11-11, before any run:

- References: the BD TOPO buildings of 80 to 400 m² lying 64 m or more inside the LiDAR HD tile of the test
  project, sorted by fid, the first 20. Each is clicked at its pole of inaccessibility with the object detector of
  CLASSES on class 6 (point_cloud_objects.object_footprint), then the similar objects are the parts of the footprint of
  class 6 over the tile (class_footprint, read once) within the default ratios (0.5 to 2), by area alone and by area
  and shape.
- Truth: the other buildings of the tile within 0.5 to 2 times the reference's area. An object matches a building at
  IoU >= 0.5. Precision: objects found that match a building; recall: truth buildings matched.
- Same shape stays on by default, as on a raster, unless the median precision does not rise and the median recall
  loses more than 0.05; then the option stays, off by default.

Run by python-qgis.bat: argv = plugins folder, point cloud, buildings, output json.

Result, 2026-11-11, QGIS 4.2.3 for Windows: medians, area alone precision 0.435, recall 0, 6.5 found; area and shape
precision 0.455, recall 0, 6 found. Same shape stays on. The bench says little: the class 6 footprint in 2 m cells
merges neighbouring buildings into blocks (47 objects for 126 buildings) and the clicked object overlaps its building
at a median IoU of 0.13, so almost no object matches one building.
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

from qgis.core import (QgsApplication, QgsFeatureRequest, QgsPointCloudLayer, QgsRectangle,  # noqa: E402
                       QgsVectorLayer)

app = QgsApplication([], True)
app.initQgis()

from filter_mate.adapters.qgis.coverage_layers import point_cloud_objects as objects  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.geometry_tools import compactness  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.segmentation import overlap  # noqa: E402

RATIO = (0.5, 2.0)
BUILDING = 6

layer = QgsPointCloudLayer(cloud_path, 'lidar', 'copc')
vector = QgsVectorLayer(f'{buildings}|layername=batiment_sl', 'batiment', 'ogr')
assert layer.isValid() and vector.isValid(), (layer.isValid(), vector.isValid())
assert layer.crs() == vector.crs(), (layer.crs().authid(), vector.crs().authid())
extent = layer.extent()
inner = QgsRectangle(extent.xMinimum() + 64, extent.yMinimum() + 64, extent.xMaximum() - 64, extent.yMaximum() - 64)
everything = [f for f in vector.getFeatures(QgsFeatureRequest().setFilterRect(extent))]
references = sorted([f for f in everything if 80 <= f.geometry().area() <= 400
                     and inner.contains(f.geometry().boundingBox())], key=lambda f: f.id())[:20]
print(f'{len(references)} references, {len(everything)} buildings on the tile', flush=True)
begin = time.time()
footprint = objects.class_footprint(layer, BUILDING)
print(f'class footprint in {time.time() - begin:.1f} s, cells {footprint.cell_size}, truncated {footprint.truncated}',
      flush=True)


def measure(found, truth, others):
    precise = sum(1 for part in found if any(overlap(part, other) >= 0.5 for other in others))
    recalled = sum(1 for building in truth if any(overlap(part, building) >= 0.5 for part in found))
    return {'found': len(found), 'precision': precise / len(found) if found else None,
            'recall': recalled / len(truth) if truth else None, 'truth': len(truth)}


rows = []
for feature in references:
    reference = feature.geometry()
    point = reference.poleOfInaccessibility(0.25)[0].asPoint()
    clicked = objects.object_footprint(layer, point.x(), point.y(), BUILDING)
    row = {'fid': feature.id(), 'area': round(reference.area(), 1)}
    if clicked.geometry is None or clicked.geometry.isEmpty():
        row['clicked'] = None
        rows.append(row)
        print(json.dumps(row), flush=True)
        continue
    shape = objects.filled_part(clicked.geometry)
    others = [f.geometry() for f in everything if f.id() != feature.id()]
    truth = [g for g in others if RATIO[0] * reference.area() <= g.area() <= RATIO[1] * reference.area()]
    row['clicked_iou'] = round(overlap(shape, reference), 3)
    area_alone, _total = objects.similar_parts(footprint.geometry, [shape.area()], RATIO)
    with_shape, total = objects.similar_parts(footprint.geometry, [shape.area()], RATIO, [compactness(shape)])
    # the clicked object itself is no similar object
    area_alone = [p for p in area_alone if overlap(p, shape) < 0.5]
    with_shape = [p for p in with_shape if overlap(p, shape) < 0.5]
    row.update(objects_of_class=total, area=measure(area_alone, truth, others),
               shape=measure(with_shape, truth, others))
    rows.append(row)
    print(json.dumps(row), flush=True)


def median(values):
    values = [value for value in values if value is not None]
    return round(statistics.median(values), 3) if values else None


summary = {}
for variant in ('area', 'shape'):
    measured = [row[variant] for row in rows if variant in row]
    summary[variant] = {'precision': median([m['precision'] for m in measured]),
                        'recall': median([m['recall'] for m in measured]),
                        'found': median([m['found'] for m in measured])}
print(json.dumps(summary), flush=True)
area, shape = summary['area'], summary['shape']
off = (shape['precision'] or 0) <= (area['precision'] or 0) and (shape['recall'] or 0) < (area['recall'] or 0) - 0.05
print('same shape OFF by default' if off else 'same shape ON by default', flush=True)
with open(output, 'w', encoding='utf-8') as stream:
    json.dump({'rows': rows, 'summary': summary, 'shape_on': not off}, stream, indent=1)
print('done', flush=True)
os._exit(0)

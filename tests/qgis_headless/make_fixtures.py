# -*- coding: utf-8 -*-
"""
Tiny synthetic data for the headless QGIS smoke test (no binary file in git).

Writes into ``<folder>`` (created when missing), with GDAL / OGR and numpy
only, which every QGIS install ships:

* ``dem.tif``: 100 x 100 Float32 DEM, 10 m pixels, EPSG:2154, NoData -9999.
  Elevation grows from west to east: column ``c`` holds ``100 + c``, so the
  range 150-199 is the east half (x >= ``EAST_X``).
* ``zones.gpkg`` (layer ``zones``): five squares named ``east_a``, ``east_b``
  (inside the east half), ``straddle`` (across x = ``EAST_X``), ``west_a``
  and ``west_b`` (outside).
* ``cloud.las``: LAS 1.2, point format 1, EPSG:2154 GeoKeys, 5000 points:
  ground (class 2) everywhere, high vegetation (class 5) in the south-west,
  buildings (class 6) inside ``east_a`` only.
* ``cloud_ept/ept.json``: the same points as an EPT dataset with binary
  tiles, read by the core ``ept`` provider of QGIS builds without PDAL (the
  official Docker images cannot open a LAS file).
* ``manifest.json``: paths and the expected results.

Usage:
    python3 make_fixtures.py <folder>
"""
import json
import os
import struct
import sys

import numpy as np
from osgeo import gdal, ogr, osr

EPSG = 2154
X0, Y0 = 700000.0, 6600000.0  # top-left corner of the DEM
PIXEL = 10.0
SIZE = 100  # pixels per side
NODATA = -9999.0
EAST_X = X0 + PIXEL * SIZE / 2  # first column of the 150-199 range
EAST_RANGE = (150.0, 199.0)

ZONES = {
    'east_a': (700700, 6599400, 700800, 6599500),
    'east_b': (700600, 6599100, 700650, 6599150),
    'straddle': (700450, 6599600, 700550, 6599700),
    'west_a': (700100, 6599400, 700200, 6599500),
    'west_b': (700050, 6599800, 700100, 6599900),
}
BUILDINGS = (700710, 6599410, 700790, 6599490)  # class 6 points, inside east_a
VEGETATION = (700050, 6599050, 700300, 6599300)  # class 5 points, far from every zone
COUNTS = {2: 3000, 5: 1000, 6: 1000}
SCALE = 0.01


def _srs():
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(EPSG)
    return srs


def write_dem(path):
    """Write the west -> east gradient DEM."""
    values = np.tile(100.0 + np.arange(SIZE, dtype='float32'), (SIZE, 1))
    dataset = gdal.GetDriverByName('GTiff').Create(path, SIZE, SIZE, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((X0, PIXEL, 0.0, Y0, 0.0, -PIXEL))
    dataset.SetProjection(_srs().ExportToWkt())
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(NODATA)
    band.WriteArray(values)
    dataset = None


def write_zones(path):
    """Write the five test squares to a GeoPackage."""
    driver = ogr.GetDriverByName('GPKG')
    if os.path.exists(path):
        driver.DeleteDataSource(path)
    source = driver.CreateDataSource(path)
    layer = source.CreateLayer('zones', _srs(), ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn('name', ogr.OFTString))
    for name, (xmin, ymin, xmax, ymax) in ZONES.items():
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField('name', name)
        feature.SetGeometry(ogr.CreateGeometryFromWkt(
            f"POLYGON(({xmin} {ymin},{xmax} {ymin},{xmax} {ymax},{xmin} {ymax},{xmin} {ymin}))"))
        layer.CreateFeature(feature)
    source = None


def make_points(seed=42):
    """Deterministic points: (x, y, z) already rounded to the LAS scale, classes."""
    rng = np.random.default_rng(seed)
    boxes = {2: (X0, Y0 - PIXEL * SIZE, X0 + PIXEL * SIZE, Y0), 5: VEGETATION, 6: BUILDINGS}
    xs, ys, classes = [], [], []
    for code, count in COUNTS.items():
        xmin, ymin, xmax, ymax = boxes[code]
        xs.append(rng.uniform(xmin + 0.5, xmax - 0.5, count))
        ys.append(rng.uniform(ymin + 0.5, ymax - 0.5, count))
        classes.append(np.full(count, code, dtype='uint8'))
    x, y, classes = np.concatenate(xs), np.concatenate(ys), np.concatenate(classes)
    x[np.abs(x - EAST_X) < 0.05] += 0.1  # never on the clip edge
    x, y = np.round(x / SCALE) * SCALE, np.round(y / SCALE) * SCALE
    ground = 100.0 + np.floor((x - X0) / PIXEL)
    z = ground + np.where(classes == 2, 0.0, np.where(classes == 5, 12.0, 8.0))
    return x, y, np.round(z / SCALE) * SCALE, classes


def _geokeys_vlr():
    """GeoKeyDirectoryTag VLR: projected CRS EPSG:2154, metres."""
    keys = [(1024, 0, 1, 1), (1025, 0, 1, 1), (3072, 0, 1, EPSG), (3076, 0, 1, 9001)]
    body = struct.pack('<4H', 1, 1, 0, len(keys)) + b''.join(struct.pack('<4H', *key) for key in keys)
    header = struct.pack('<H16sHH32s', 0, b'LASF_Projection', 34735, len(body), b'GeoKeyDirectoryTag')
    return header + body


def write_las(path, x, y, z, classes):
    """Write a LAS 1.2 file, point data format 1 (28 bytes per point)."""
    dtype = np.dtype([('X', '<i4'), ('Y', '<i4'), ('Z', '<i4'), ('intensity', '<u2'), ('flags', 'u1'),
                      ('classification', 'u1'), ('scan_angle', 'i1'), ('user_data', 'u1'),
                      ('point_source_id', '<u2'), ('gps_time', '<f8')])
    offsets = (X0, Y0 - PIXEL * SIZE, 0.0)
    points = np.zeros(len(x), dtype=dtype)
    points['X'] = np.round((x - offsets[0]) / SCALE)
    points['Y'] = np.round((y - offsets[1]) / SCALE)
    points['Z'] = np.round((z - offsets[2]) / SCALE)
    points['intensity'] = 100 + classes.astype('uint16') * 10
    points['flags'] = 1 | (1 << 3)  # return 1 of 1
    points['classification'] = classes
    points['gps_time'] = np.arange(len(x), dtype='float64')
    vlr = _geokeys_vlr()
    header = struct.pack(
        '<4sHHIHH8sBB32s32sHHHIIBHI5I3d3d6d',
        b'LASF', 0, 0, 0, 0, 0, b'\0' * 8, 1, 2, b'FilterMate fixtures', b'make_fixtures.py', 1, 2026,
        227, 227 + len(vlr), 1, 1, dtype.itemsize, len(x), len(x), 0, 0, 0, 0,
        SCALE, SCALE, SCALE, *offsets,
        x.max(), x.min(), y.max(), y.min(), z.max(), z.min())
    with open(path, 'wb') as stream:
        stream.write(header)
        stream.write(vlr)
        stream.write(points.tobytes())


def write_ept(folder, x, y, z, classes):
    """Write an EPT dataset: one root node, binary tile, JSON hierarchy."""
    os.makedirs(os.path.join(folder, 'ept-data'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'ept-hierarchy'), exist_ok=True)
    conforming = [x.min(), y.min(), z.min(), x.max(), y.max(), z.max()]
    half = max(conforming[3] - conforming[0], conforming[4] - conforming[1], conforming[5] - conforming[2]) / 2 + 1
    center = [(conforming[i] + conforming[i + 3]) / 2 for i in range(3)]
    offsets = [round(c) for c in center]
    dtype = np.dtype([('X', '<i4'), ('Y', '<i4'), ('Z', '<i4'), ('Intensity', '<u2'),
                      ('ReturnNumber', 'u1'), ('NumberOfReturns', 'u1'), ('Classification', 'u1')])
    points = np.zeros(len(x), dtype=dtype)
    for name, values, offset in (('X', x, offsets[0]), ('Y', y, offsets[1]), ('Z', z, offsets[2])):
        points[name] = np.round((values - offset) / SCALE)
    points['Intensity'] = 100 + classes.astype('uint16') * 10
    points['ReturnNumber'] = 1
    points['NumberOfReturns'] = 1
    points['Classification'] = classes
    schema = [{'name': axis, 'type': 'signed', 'size': 4, 'scale': SCALE, 'offset': offset}
              for axis, offset in zip('XYZ', offsets)]
    schema += [{'name': 'Intensity', 'type': 'unsigned', 'size': 2},
               {'name': 'ReturnNumber', 'type': 'unsigned', 'size': 1},
               {'name': 'NumberOfReturns', 'type': 'unsigned', 'size': 1},
               {'name': 'Classification', 'type': 'unsigned', 'size': 1}]
    ept = {
        'bounds': [c - half for c in center] + [c + half for c in center],
        'boundsConforming': conforming,
        'dataType': 'binary',
        'hierarchyType': 'json',
        'points': int(len(x)),
        'schema': schema,
        'span': 128,
        'srs': {'authority': 'EPSG', 'horizontal': str(EPSG), 'wkt': _srs().ExportToWkt()},
        'version': '1.0.0',
    }
    with open(os.path.join(folder, 'ept.json'), 'w', encoding='utf-8') as stream:
        json.dump(ept, stream, indent=1)
    with open(os.path.join(folder, 'ept-hierarchy', '0-0-0-0.json'), 'w', encoding='utf-8') as stream:
        json.dump({'0-0-0-0': int(len(x))}, stream)
    with open(os.path.join(folder, 'ept-data', '0-0-0-0.bin'), 'wb') as stream:
        stream.write(points.tobytes())
    return os.path.join(folder, 'ept.json')


def make_all(folder):
    """Write every fixture into ``folder`` and return the manifest (also written as manifest.json)."""
    folder = os.path.abspath(folder)
    os.makedirs(folder, exist_ok=True)
    x, y, z, classes = make_points()
    manifest = {
        'dem': os.path.join(folder, 'dem.tif'),
        'zones': os.path.join(folder, 'zones.gpkg'),
        'las': os.path.join(folder, 'cloud.las'),
        'ept': os.path.join(folder, 'cloud_ept', 'ept.json'),
        'crs': f'EPSG:{EPSG}',
        'dem_extent': [X0, Y0 - PIXEL * SIZE, X0 + PIXEL * SIZE, Y0],
        'pixel': PIXEL,
        'east_x': EAST_X,
        'east_range': list(EAST_RANGE),
        'zones_in_east_range': ['east_a', 'east_b', 'straddle'],
        'zones_with_buildings': ['east_a'],
        'zone_names': sorted(ZONES),
        'zone_boxes': ZONES,
        'points': int(len(x)),
        'points_by_class': {str(code): int((classes == code).sum()) for code in COUNTS},
        'points_east': int((x > EAST_X).sum()),
    }
    write_dem(manifest['dem'])
    write_zones(manifest['zones'])
    write_las(manifest['las'], x, y, z, classes)
    write_ept(os.path.dirname(manifest['ept']), x, y, z, classes)
    with open(os.path.join(folder, 'manifest.json'), 'w', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=1)
    return manifest


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(json.dumps(make_all(sys.argv[1]), indent=1))

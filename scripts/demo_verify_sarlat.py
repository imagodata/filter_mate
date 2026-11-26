#!/usr/bin/env python3
"""Independently verify Sarlat corridor and raster counts with QGIS/GDAL, without FilterMate."""
import argparse
import json
from pathlib import Path


def verify(data):
    import numpy as np
    from osgeo import gdal, ogr
    from qgis.core import QgsApplication, QgsGeometry, QgsVectorLayer
    app = QgsApplication.instance()
    if app is None:
        app = QgsApplication([], False)
        app.initQgis()
    gpkg = str(data / 'sarlat.gpkg')
    roads = QgsVectorLayer(gpkg + '|layername=troncon_de_route', 'roads', 'ogr')
    vectors = {name: QgsVectorLayer(gpkg + '|layername=' + name, name, 'ogr')
               for name in ('batiment', 'parcelle')}
    if not all(layer.isValid() for layer in [roads, *vectors.values()]):
        raise ValueError('invalid Sarlat vector layer')
    selected = [f.geometry() for f in roads.getFeatures() if f['nom_collaboratif_gauche'] == 'BD HENRI ARLET']
    corridor = QgsGeometry.unaryUnion(selected).buffer(50, 5)
    corridor_counts = {name: sum(f.geometry().intersects(corridor) for f in layer.getFeatures())
                       for name, layer in vectors.items()}
    raster = gdal.Open(str(data / 'mnt_1m.tif'))
    band = raster.GetRasterBand(1)
    values = band.ReadAsArray()
    valid = np.isfinite(values)
    if band.GetNoDataValue() is not None:
        valid &= values != band.GetNoDataValue()
    low = ((values <= 136) & valid).astype(np.uint8)
    mask = gdal.GetDriverByName('MEM').Create('', raster.RasterXSize, raster.RasterYSize, 1, gdal.GDT_Byte)
    mask.SetGeoTransform(raster.GetGeoTransform())
    mask.SetProjection(raster.GetProjection())
    mask.GetRasterBand(1).WriteArray(low)
    polygons = ogr.GetDriverByName('Memory').CreateDataSource('')
    layer = polygons.CreateLayer('low_ground')
    layer.CreateField(ogr.FieldDefn('kept', ogr.OFTInteger))
    gdal.Polygonize(mask.GetRasterBand(1), None, layer, 0, [])
    area = QgsGeometry.unaryUnion([QgsGeometry.fromWkt(f.GetGeometryRef().ExportToWkt())
                                  for f in layer if f.GetField('kept') == 1])
    low_counts = {}
    for name, vector in vectors.items():
        count = 0
        for feature in vector.getFeatures():
            geometry = feature.geometry()
            if geometry.area() > 0 and geometry.intersects(area):
                count += geometry.intersection(area).area() / geometry.area() >= 0.5
        low_counts[name] = count
    expected = {'corridor': {'batiment': 113, 'parcelle': 106},
                'raster': {'batiment': 187, 'parcelle': 182}}
    return {'method': 'independent QGIS geometry intersection and GDAL polygonization; no FilterMate calls',
            'boulevard_segments': len(selected), 'corridor_m': 50, 'raster_max_m_inclusive': 136,
            'raster_min_footprint_fraction': 0.5, 'corridor': corridor_counts, 'raster': low_counts,
            'expected': expected, 'ok': len(selected) == 9 and corridor_counts == expected['corridor']
            and low_counts == expected['raster'], 'lidar': 'not independently recomputed here; inspect the take'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    return int(not result['ok'])


if __name__ == '__main__':
    raise SystemExit(main())

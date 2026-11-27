"""Check Urumea geometry, GDAL terrain slope, zonal means, exports and portability.

Run with the production image, network disabled, after copying the entire
project folder to --moved. The original agent prose is not verification.
"""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--moved', type=Path, required=True)
    parser.add_argument('--acquire', type=Path, required=True)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--composer', type=Path, required=True)
    parser.add_argument('--exports', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--analysis-only', action='store_true')
    parser.add_argument('--finish', type=Path)
    args = parser.parse_args()
    from osgeo import gdal, ogr
    import numpy as np
    from qgis.core import (Qgis, QgsApplication, QgsProject, QgsVectorLayer, QgsGeometry, QgsRasterLayer, QgsFeature,
                           QgsLayoutItemPicture, QgsLayoutItemScaleBar)
    app = QgsApplication([b'urumea-verify'], False)
    app.initQgis()
    sys.path.insert(0, '/usr/share/qgis/python/plugins')
    from processing.core.Processing import Processing
    Processing.initialize()
    import processing
    project = QgsProject.instance()
    assert project.read(str(args.project))

    def one(name):
        layers = project.mapLayersByName(name)
        assert len(layers) == 1, (name, len(layers))
        return layers[0]

    def all_features(layer):
        # Read the complete physical table through an independent OGR handle.
        # A QGIS provider clone can share GDAL SQL state with the filtered layer.
        source = layer.source()
        dataset = ogr.Open(source.split('|',1)[0])
        assert dataset is not None, layer.name()
        name = next((part.split('=',1)[1] for part in source.split('|')[1:] if part.startswith('layername=')), None)
        table = dataset.GetLayerByName(name) if name else dataset.GetLayer(0)
        fields = layer.fields()
        result = []
        for row in table:
            feature = QgsFeature(fields)
            feature.setId(row.GetFID())
            feature.setAttributes([row.GetFID() if field.name()==table.GetFIDColumn() else row.GetField(field.name())
                                   for field in fields])
            geometry = QgsGeometry()
            geometry.fromWkb(bytes(row.GetGeometryRef().ExportToWkb()))
            feature.setGeometry(geometry)
            result.append(feature)
        return result

    def ids(features):
        values = [str(f['osm_type']) + ':' + str(f['osm_id']) for f in features]
        assert len(values) == len(set(values)), 'Duplicate OSM identifiers'
        return set(values)

    states = {}
    for stage in ('corridor', 't100', 'reseau'):
        states[stage] = json.loads((args.analysis / (stage + '-observed.json')).read_text())
    all_calls = []
    takes = [args.acquire, args.analysis]
    if not args.analysis_only:
        takes.append(args.composer)
        if args.finish:
            takes.append(args.finish)
    for take in takes:
        assert json.loads((take / 'meta.json').read_text())['status'] == 'complete'
        all_calls.extend(json.loads(row) for row in (take / 'tools.jsonl').read_text().splitlines())
    errors = [{'stage': call['request'], 'tool': call['tool'], 'content': call['content'][:300]}
              for call in all_calls if call['is_error']]
    assert not errors, errors

    buildings = one('Bâtiments pente')
    full_buildings = all_features(buildings)
    assert buildings.crs().authid() == 'EPSG:25830'
    total_ids = ids(full_buildings)
    selected_ids = ids(buildings.getFeatures())
    river = one('Urumea')
    river_geometries = [f.geometry() for f in river.getFeatures()]
    # The native:buffer call specifies the exact approximation used in this take.
    buffer_call = next(call for call in all_calls if call['tool'] == 'run_algorithm'
                       and call['arguments']['algorithm_id'] == 'native:buffer'
                       and call['arguments']['parameters'].get('DISTANCE') == 500)
    segments = buffer_call['arguments']['parameters'].get('SEGMENTS', 5)
    expected_corridor = QgsGeometry.unaryUnion([geometry.buffer(500, segments) for geometry in river_geometries])
    assert expected_corridor.boundingBox().intersects(QgsGeometry.unaryUnion([f.geometry() for f in full_buildings]).boundingBox())
    corridor_features = [f for f in full_buildings if f.geometry().intersects(expected_corridor)]
    corridor_ids = ids(corridor_features)
    ura = one('URA T100')
    assert ura.crs().authid() == 'EPSG:25830'
    zones = list(ura.getFeatures())
    assert zones and all(f['CODIGO'] == 'Q0100' and 'urumea' in str(f['RIO']).lower() for f in zones)
    zone_geometry = QgsGeometry.unaryUnion([f.geometry() for f in zones])
    expected_final = [f for f in corridor_features if f.geometry().intersects(zone_geometry)]
    final_ids = ids(expected_final)
    assert selected_ids == final_ids, {'actual': len(selected_ids), 'expected': len(final_ids),
                                     'missing': sorted(final_ids-selected_ids)[:12],
                                     'extra': sorted(selected_ids-final_ids)[:12]}

    def observed(stage, name):
        return next(item['count'] for item in states[stage]['layers'] if item['name'] == name)
    assert observed('corridor','Bâtiments pente') == len(corridor_ids)
    assert observed('t100','Bâtiments pente') == len(final_ids) == observed('reseau','Bâtiments pente')
    assert 0 < len(final_ids) <= len(corridor_ids) < len(total_ids)

    network_call = next(call for call in all_calls if call['request'] == 'reseau' and call['tool'] == 'cross_filter')
    assert network_call['arguments']['buffer'] == 300
    network_buffer = QgsGeometry.unaryUnion([f.geometry().buffer(300, 5) for f in expected_final])
    network = {}
    for name in ('Routes','Ponts lignes','Ponts polygones'):
        layer = one(name)
        assert layer.crs().authid() == 'EPSG:25830'
        expected = ids(f for f in all_features(layer) if f.geometry().intersects(network_buffer))
        actual = ids(layer.getFeatures())
        assert expected == actual, (name, len(expected), len(actual))
        assert observed('reseau',name) == len(actual)
        network[name] = len(actual)

    mnt, slope = one('MNT GeoEuskadi 5 m'), one('Pente (%)')
    assert abs(mnt.rasterUnitsPerPixelX()-5) < 1e-6
    expected_slope = gdal.DEMProcessing('', mnt.source(), 'slope', format='MEM', slopeFormat='percent', computeEdges=True)
    reference = expected_slope.ReadAsArray().astype('float64')
    actual = gdal.Open(slope.source()).ReadAsArray().astype('float64')
    assert actual.shape == reference.shape
    raster_delta = float(np.max(np.abs(actual-reference)))
    assert raster_delta < 1e-4, raster_delta
    source = QgsVectorLayer('MultiPolygon?crs=EPSG:25830','Independent full buildings','memory')
    source.dataProvider().addAttributes(one('Bâtiments').fields())
    source.updateFields()
    source.dataProvider().addFeatures(all_features(one('Bâtiments')))
    check = processing.run('native:zonalstatisticsfb', {
        'INPUT':source,'INPUT_RASTER':slope,'RASTER_BAND':1,'COLUMN_PREFIX':'check_',
        'STATISTICS':[2],'OUTPUT':'memory:'})['OUTPUT']
    means = {str(f['osm_id']): f['check_mean'] for f in check.getFeatures()}
    mean_delta, valid, missing = 0.0, 0, 0
    for f in buildings.getFeatures():
        value = f['pente_mean']
        if value is None or getattr(value,'isNull',lambda:False)():
            missing += 1
        else:
            valid += 1
            mean_delta = max(mean_delta,abs(float(value)-float(means[str(f['osm_id'])])))
    assert valid+missing == len(final_ids) and mean_delta < 1e-5

    if args.analysis_only:
        result = {'verified': False, 'analysis_verified': True, 'total_buildings':len(total_ids),
                  'corridor_500m_buildings':len(corridor_ids), 'ura_t100_buildings':len(final_ids),
                  'network_counts':network, 'building_ids_match':True, 'network_ids_match':True,
                  'slope_raster_max_abs_difference_percent':raster_delta,
                  'mean_slope_max_abs_difference_percent':mean_delta,
                  'valid_mean_slopes':valid, 'missing_mean_slopes':missing,
                  'scope':'Geometry and numerical checks only; composition/export/portability pending.'}
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False),flush=True)
        return

    packages = sorted(args.exports.rglob('urumea_resultats*.gpkg'))
    assert packages, 'No exported result GeoPackage'
    exported = {}
    dataset = ogr.Open(str(packages[-1]))
    expected_names = ('Bâtiments pente','Routes','Ponts lignes','Ponts polygones','Urumea','Couloir Urumea 500 m','URA T100')
    for name in expected_names:
        table = dataset.GetLayerByName(name)
        assert table is not None, (name,[dataset.GetLayer(i).GetName() for i in range(dataset.GetLayerCount())])
        exported[name] = table.GetFeatureCount()
        assert exported[name] == one(name).featureCount()
        if name in ('Bâtiments pente','Routes','Ponts lignes','Ponts polygones','Urumea'):
            exported_ids = {str(f.GetField('osm_type'))+':'+str(f.GetField('osm_id')) for f in table}
            assert exported_ids == ids(one(name).getFeatures())
    pdfs = sorted(args.exports.rglob('*.pdf'))
    assert pdfs and all(path.read_bytes().startswith(b'%PDF-') for path in pdfs)
    assert len(list(args.exports.rglob('*.tif'))) >= 2

    layout = project.layoutManager().layoutByName('Urumea — analyse')
    assert layout is not None
    pictures = [item for item in layout.items() if isinstance(item,QgsLayoutItemPicture)]
    chart_pictures = [item for item in pictures if item.customProperty('filtermate/chart')]
    d3_calls = [call for call in all_calls if call['tool']=='run_chart_code']
    assert len(d3_calls) == 2 and len(chart_pictures) == 2
    d3_ids = {json.loads(call['content'])['chart_id'] for call in d3_calls}
    placed_ids = {call['arguments']['chart_id'] for call in all_calls if call['tool']=='add_chart_to_layout'}
    assert placed_ids == d3_ids
    assert all(item.picturePath().startswith(('base64:',':/images/north_arrows/')) for item in pictures)
    scales = [item for item in layout.items() if isinstance(item,QgsLayoutItemScaleBar)]
    assert len(scales)==1 and scales[0].linkedMap() is not None
    assert 0 < scales[0].unitsPerSegment() < 100000 and scales[0].numberOfSegments() > 0
    scale_info = {'units_per_segment':scales[0].unitsPerSegment(),
                  'segments':scales[0].numberOfSegments(), 'label':scales[0].unitLabel()}
    assert any(item.picturePath().startswith(':/images/north_arrows/') for item in pictures)
    for call in d3_calls:
        reply = json.loads(call['content'])
        assert not reply.get('errors'), reply.get('errors')

    original_counts = {layer.name():layer.featureCount() for layer in project.mapLayers().values() if isinstance(layer,QgsVectorLayer)}
    # Clear the original project first, so the copied project cannot borrow its layers.
    project.clear()
    assert project.read(str(args.moved))
    portability = []
    for layer in project.mapLayers().values():
        assert layer.isValid(), layer.name()
        source_path = layer.source().split('|',1)[0]
        assert not source_path.startswith(('/vsimem','/vsicurl','https:','http:')), (layer.name(),source_path)
        assert Path(source_path).resolve().is_relative_to(args.moved.parent.resolve()), (layer.name(),source_path)
        if isinstance(layer,QgsVectorLayer):
            assert layer.featureCount() == original_counts[layer.name()], (layer.name(),layer.featureCount(),original_counts[layer.name()])
        else:
            assert isinstance(layer,QgsRasterLayer) and layer.dataProvider().block(1,layer.extent(),10,10).isValid()
        portability.append({'name':layer.name(),'valid':True})
    moved_layout = project.layoutManager().layoutByName('Urumea — analyse')
    assert moved_layout is not None
    moved_pictures = [item for item in moved_layout.items() if isinstance(item,QgsLayoutItemPicture)]
    assert len(moved_pictures)==len(pictures) and all(item.picturePath().startswith(('base64:',':/images/north_arrows/')) for item in moved_pictures)
    result = {'verified':True,'scope':'Observed tools, independent geometry and numerical recomputation; moved project reopened with network disabled.',
              'qgis_version':Qgis.QGIS_VERSION,'gdal_version':gdal.VersionInfo('--version'),
              'total_buildings':len(total_ids),'corridor_500m_buildings':len(corridor_ids),'ura_t100_buildings':len(final_ids),
              'network_counts':network,'exported_counts':exported,'building_ids_match':True,'network_ids_match':True,
              'buffer_segments':segments,'slope_raster_max_abs_difference_percent':raster_delta,
              'mean_slope_max_abs_difference_percent':mean_delta,'valid_mean_slopes':valid,'missing_mean_slopes':missing,
              'actual_d3_calls':2,'embedded_chart_svgs':2,'pdfs':[p.name for p in pdfs],
              'scale_bar':scale_info,'d3_chart_ids_placed':sorted(d3_ids),
              'native_qgis_picture_resources':[item.picturePath() for item in moved_pictures if item.picturePath().startswith(':/')],
              'offline_moved_project_layers':portability,'tool_errors':errors,'publication':'not_published'}
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()

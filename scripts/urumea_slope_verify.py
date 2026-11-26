"""Verify real slope/filter/replay/export behavior independently of agent prose."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/w'))
    parser.add_argument('--take', type=Path, required=True)
    parser.add_argument('--analysis-only', action='store_true')
    args = parser.parse_args()
    from osgeo import gdal
    import numpy as np
    from qgis.core import QgsApplication, QgsVectorLayer, QgsRasterLayer, QgsGeometry
    app = QgsApplication([], False)
    app.initQgis()
    sys.path.insert(0, '/usr/share/qgis/python/plugins')
    from processing.core.Processing import Processing
    Processing.initialize()
    import processing
    root, take = args.root, args.take
    meta = json.loads((take / 'meta.json').read_text())
    assert meta['status'] == 'complete'
    stages = ['moyenne', 'seuil', 'filtre', 'reseau'] + ([] if args.analysis_only else ['reset', 'rejeu'])
    states = {stage: json.loads((take / (stage + '-observed.json')).read_text()) for stage in stages}
    calls = [json.loads(line) for line in (take / 'tools.jsonl').read_text().splitlines()]
    slope_call = next(call for call in calls if call['tool'] == 'run_algorithm'
                      and call['arguments']['algorithm_id'] == 'gdal:slope' and not call['is_error'])
    parameters = slope_call['arguments']['parameters']
    assert parameters['AS_PERCENT'] is True and parameters['COMPUTE_EDGES'] is True
    assert parameters.get('SCALE', 1) == 1 and parameters.get('ZEVENBERGEN', False) is False
    network_call = next(call for call in calls if call['request'] == 'reseau'
                        and call['tool'] == 'cross_filter' and not call['is_error'])
    assert network_call['arguments']['buffer'] == 300
    before = states['reseau']['filters']
    assert set(before) == {'Bâtiments pente', 'Routes', 'Ponts lignes', 'Ponts polygones'}
    if not args.analysis_only:
        assert before == states['rejeu']['filters'] and states['reset']['filters'] == {}
        reset_counts = {layer['name']: layer.get('count') for layer in states['reset']['layers']}
        assert all(reset_counts[name] == value for name, value in
                   {'Bâtiments pente': 3073, 'Routes': 701, 'Ponts lignes': 158, 'Ponts polygones': 8}.items())
    replay = [call['tool'] for call in calls if call['request'] == 'rejeu' and not call['is_error']]
    if not args.analysis_only:
        assert 'apply_favorite' in replay
        assert not set(replay) & {'apply_filter', 'cross_filter', 'geometry_filter', 'run_algorithm', 'clear_filters'}
    gpkg = next((take / 'exports').rglob('*.gpkg'))
    exported = {}
    with closing(sqlite3.connect(gpkg.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        for (name,) in db.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'"):
            exported[name] = db.execute('SELECT count(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
    assert set(exported) == set(before) | {'Urumea', 'Couloir Urumea 500 m'}, exported
    assert all(exported[name] == value['count'] for name, value in before.items())
    dem_path = next(path for path in (take / 'exports').rglob('*.tif') if 'Copernicus' in path.name)
    slope_path = next(path for path in (take / 'exports').rglob('*.tif') if 'Pente' in path.name)
    independent_slope = gdal.DEMProcessing('', str(dem_path), 'slope', format='MEM', slopeFormat='percent', computeEdges=True)
    actual_slope = gdal.Open(str(slope_path))
    reference, actual = independent_slope.ReadAsArray(), actual_slope.ReadAsArray()
    assert reference.shape == actual.shape
    delta = float(np.max(np.abs(reference.astype('float64') - actual.astype('float64'))))
    assert delta < 1e-4, delta
    source = QgsVectorLayer(str(root / 'data/urumea-ready.gpkg') + '|layername=batiments', 'full buildings', 'ogr')
    river = QgsVectorLayer(str(root / 'data/urumea-ready.gpkg') + '|layername=urumea', 'river', 'ogr')
    raster = QgsRasterLayer(str(slope_path), 'slope', 'gdal')
    check = processing.run('native:zonalstatisticsfb', {'INPUT': source, 'INPUT_RASTER': raster, 'RASTER_BAND': 1,
                           'COLUMN_PREFIX': 'check_', 'STATISTICS': [2], 'OUTPUT': 'memory:'})['OUTPUT']
    assert check.featureCount() == 3073
    buffer_call = next(call for call in calls if call['tool'] == 'run_algorithm'
                       and call['arguments']['algorithm_id'] == 'native:buffer' and not call['is_error'])
    assert buffer_call['arguments']['parameters']['DISTANCE'] == 500
    segments = buffer_call['arguments']['parameters'].get('SEGMENTS', 5)
    corridor = QgsGeometry.unaryUnion([feature.geometry().buffer(500, segments) for feature in river.getFeatures()])
    independently_kept = {str(feature['osm_id']): float(feature['check_mean']) for feature in check.getFeatures()
                          if feature['check_mean'] < 10 and feature.geometry().intersects(corridor)}
    observed_buildings = QgsVectorLayer(str(gpkg) + '|layername=Bâtiments pente', 'export', 'ogr')
    ids = {str(feature['osm_id']): float(feature['pente_mean']) for feature in observed_buildings.getFeatures()}
    assert set(ids) == set(independently_kept)
    mean_delta = max(abs(value - independently_kept[key]) for key, value in ids.items())
    assert mean_delta < 1e-5
    assert sum(feature['check_mean'] < 10 for feature in check.getFeatures()) == 1463
    independent_sql = {}
    with closing(sqlite3.connect((root / 'data/urumea-ready.gpkg').resolve().as_uri() + '?mode=ro', uri=True)) as db:
        for name, table in {'Routes': 'routes', 'Ponts lignes': 'ponts_lignes', 'Ponts polygones': 'ponts_polygones'}.items():
            count = db.execute('SELECT count(*) FROM ' + table + ' WHERE ' + before[name]['subset']).fetchone()[0]
            assert count == before[name]['count']
            independent_sql[name] = count
    errors = [{'stage': call['request'], 'tool': call['tool']} for call in calls if call['is_error']]
    receipt = {'verified': True, 'expected_counts_from_real_filter_tools': {name: value['count'] for name, value in before.items()},
               'exported_counts': exported, 'replay_operations': replay, 'identical_filters_after_replay': None if args.analysis_only else True,
               'favorite_scope': 'not_in_this_take' if args.analysis_only else 'verified_replay',
               'independent_building_ids_match': True, 'independent_building_count': len(ids), 'independent_sql_counts': independent_sql,
               'slope_raster_max_abs_difference_percent': delta, 'mean_slope_max_abs_difference_percent': mean_delta,
               'buffer_m': 500, 'buffer_segments': segments, 'slope_threshold_percent': 10,
               'tool_errors': errors, 'scope': 'Real QGIS results, tool arguments and reopened exports; agent prose is not evidence.'}
    (take / 'verified-observations.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""
Two geometric filters combined on a GeoPackage, a SpatiaLite and a Shapefile target, counted in a real QGIS.

2026-11-12 (user decision): when a target already holds the subset of a previous geometric filter,
a new geometric filter combines with it under the combine operator of the other layers, OR and AND
(it replaced it), AND NOT is unchanged, no operator still replaces. For each target and each backend
path the plugin really takes (``FilterOrchestrator._determine_subset_strategy``, then the backend's
``build_expression`` and ``apply_filter``):

- GeoPackage through the SpatiaLite backend (inline predicate + R-tree prefilter);
- GeoPackage through the OGR backend (key list: the SpatiaLite backend hands a costly source over);
- GeoPackage, first filter by the SpatiaLite backend, second by the OGR backend (mixed subset);
- SpatiaLite database (``spatialite`` provider) through the SpatiaLite and the OGR backends;
- Shapefile through the OGR backend (OGR SQL key list).

A first filter (polygon P1, no operator), then a second one (P2, partly overlapping P1) with OR, AND,
AND NOT and no operator, then a three-step chain P1, OR P2, AND P3. Every expected count comes from
GDAL (``ogr.Geometry.Intersects`` on the file's points), not from QGIS nor the plugin. AND NOT keeps
its rule: a geometric subset is replaced by ``NOT (new)``, a key list gives ``(keys) AND NOT (new)``.

    docker run --rm -v "$PWD:/src:ro" qgis/qgis:stable python3 /src/tests/qgis_headless/check_geo_combine.py

Prints one ``PASS`` / ``FAIL`` line per scenario and ``N passed, M failed``; exits with 1 when one fails.
``FM_REPO`` copies another checkout of the plugin (to count the same scenarios before a change).
"""
import os
import shutil
import sys
import tempfile
import traceback

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from osgeo import gdal, ogr, osr  # noqa: E402
from qgis.core import Qgis, QgsApplication, QgsFeature, QgsFeatureRequest, QgsGeometry, QgsVectorLayer  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get('FM_REPO') or os.path.dirname(os.path.dirname(HERE))
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')

# 40 points on a line, 10 m apart; the polygons cover runs of them
POINTS = {i: (700000.0 + 10 * i, 6600000.0) for i in range(1, 41)}


def _box(x_min, x_max):
    return f'POLYGON(({x_min} 6599995, {x_max} 6599995, {x_max} 6600005, {x_min} 6600005, {x_min} 6599995))'


P1 = _box(700025, 700125)   # points 3..12
P2 = _box(700095, 700185)   # points 10..18: partly inside P1
P3 = _box(700145, 700225)   # points 15..22: partly inside P1 or P2

app = QgsApplication([], False)
app.initQgis()
results = []


def check(name, expected, got, detail=''):
    status = 'PASS' if expected == got else 'FAIL'
    results.append(status)
    print(f"{status:<5} {name}: expected {expected}, got {got}  {detail}".rstrip(), flush=True)


def features(layer):
    return sum(1 for _ in layer.getFeatures(QgsFeatureRequest()))


# --- data ------------------------------------------------------------------------

def write_file(path, driver_name, layer_name, options=()):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(2154)
    source = ogr.GetDriverByName(driver_name).CreateDataSource(path, options=list(options))
    layer = source.CreateLayer(layer_name, srs, ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
    for fid, (x, y) in POINTS.items():
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField('id', fid)
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint_2D(x, y)
        feature.SetGeometry(point)
        layer.CreateFeature(feature)
    source = None


def gdal_ids(path, polygon_wkt):
    """Ids of the file's points that intersect ``polygon_wkt``, read by GDAL (the independent count)."""
    polygon = ogr.CreateGeometryFromWkt(polygon_wkt)
    source = ogr.Open(path)
    layer = source.GetLayer(0)
    ids = {feature.GetField('id') for feature in layer if feature.GetGeometryRef().Intersects(polygon)}
    source = None
    return ids


def memory_source(wkt):
    source = QgsVectorLayer('Polygon?crs=EPSG:2154', 'source', 'memory')
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt(wkt))
    source.dataProvider().addFeatures([feature])
    return source


# --- one filter through the plugin --------------------------------------------------

class _Parent:
    """The task as FilterOrchestrator sees it: its operator for the targets."""

    def __init__(self, operator):
        self.operator = operator
        self.warning_messages = []

    def _get_combine_operator(self):
        return self.operator


def geometric_filter(layer, backend_name, polygon_wkt, operator):
    """FilterOrchestrator._determine_subset_strategy, then the backend: what a filter task does to a target."""
    from filter_mate.core.filter.filter_orchestrator import BackendFactory, FilterOrchestrator
    from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string
    orchestrator = FilterOrchestrator(
        task_parameters={}, subset_queue_callback=lambda target, subset: safe_set_subset_string(target, subset),
        parent_task=_Parent(operator), get_predicates_callback=lambda: {'ST_Intersects': 'ST_Intersects'})
    old_subset, combine_operator = orchestrator._determine_subset_strategy(layer)
    backend = BackendFactory.get_backend(backend_name, layer, orchestrator.task_parameters)
    if backend_name == 'ogr':
        source = memory_source(polygon_wkt)
        expression = backend.build_expression(layer_props={'layer_name': layer.name()},
                                              predicates={'ST_Intersects': True}, source_geom=source)
    else:
        expression = backend.build_expression(layer_props={'layer': layer, 'layer_name': layer.name()},
                                              predicates={'ST_Intersects': True}, source_geom=polygon_wkt,
                                              source_srid=2154)
        if expression == '__USE_OGR_FALLBACK__':
            raise RuntimeError(f"{layer.name()}: the SpatiaLite backend handed the layer over")
    if not backend.apply_filter(layer, expression, old_subset, combine_operator):
        raise RuntimeError(f"{layer.name()}: apply_filter failed: {getattr(backend, 'last_error', '')}")


# --- scenarios -------------------------------------------------------------------------

def scenarios(label, path, layer, first_backend, second_backend, key_list_after_first):
    one, two, three = (gdal_ids(path, wkt) for wkt in (P1, P2, P3))
    total = len(POINTS)
    and_not = len(one - two) if key_list_after_first else total - len(two)
    expected = {'OR': len(one | two), 'AND': len(one & two), 'AND NOT': and_not, None: len(two)}
    assert len({expected['OR'], expected['AND'], expected[None]}) == 3, expected
    for operator, wanted in expected.items():
        layer.setSubsetString('')
        geometric_filter(layer, first_backend, P1, None)
        check(f"{label}: first filter", len(one), features(layer), f"subset={layer.subsetString()[:70]!r}")
        geometric_filter(layer, second_backend, P2, operator)
        check(f"{label}: second filter, operator {operator}", wanted, features(layer),
              f"subset={layer.subsetString()[:110]!r}")
    layer.setSubsetString('')
    geometric_filter(layer, first_backend, P1, None)
    geometric_filter(layer, second_backend, P2, 'OR')
    geometric_filter(layer, second_backend, P3, 'AND')
    check(f"{label}: P1, OR P2, AND P3", len((one | two) & three), features(layer),
          f"subset={layer.subsetString()[:110]!r}")
    layer.setSubsetString('')


def main():
    work = tempfile.mkdtemp(prefix='fm_geo_combine_')
    plugins = os.path.join(work, 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    sys.path.append(os.path.join(QgsApplication.pkgDataPath(), 'python', 'plugins'))
    print(f"INFO  QGIS {Qgis.QGIS_VERSION}, GDAL {gdal.__version__}, plugin copied from {REPO}", flush=True)

    gpkg_path = os.path.join(work, 'points.gpkg')
    sqlite_path = os.path.join(work, 'points.sqlite')
    shp_path = os.path.join(work, 'points.shp')
    write_file(gpkg_path, 'GPKG', 'points')
    write_file(sqlite_path, 'SQLite', 'points', options=['SPATIALITE=YES'])
    write_file(shp_path, 'ESRI Shapefile', 'points')

    def gpkg(name):
        return QgsVectorLayer(f'{gpkg_path}|layername=points', name, 'ogr')

    def spatialite(name):
        return QgsVectorLayer(f"dbname='{sqlite_path}' table=\"points\" (GEOMETRY)", name, 'spatialite')

    cases = [
        ('GeoPackage, SpatiaLite backend', gpkg_path, gpkg('gpkg_sl'), 'spatialite', 'spatialite', False),
        ('GeoPackage, OGR backend', gpkg_path, gpkg('gpkg_ogr'), 'ogr', 'ogr', True),
        ('GeoPackage, SpatiaLite then OGR', gpkg_path, gpkg('gpkg_mixed'), 'spatialite', 'ogr', False),
        ('SpatiaLite, SpatiaLite backend', sqlite_path, spatialite('sqlite_sl'), 'spatialite', 'spatialite', False),
        ('SpatiaLite, OGR backend', sqlite_path, spatialite('sqlite_ogr'), 'ogr', 'ogr', True),
        ('Shapefile, OGR backend', shp_path, QgsVectorLayer(shp_path, 'shp_ogr', 'ogr'), 'ogr', 'ogr', True),
    ]
    for label, path, layer, first, second, key_list in cases:
        print(f"--- {label}: valid={layer.isValid()} provider={layer.providerType()} features={features(layer)}",
              flush=True)
        try:
            scenarios(label, path, layer, first, second, key_list)
        except Exception as exc:
            traceback.print_exc()
            check(f"{label} raised {type(exc).__name__}: {exc}", 'no error', 'error')

    failed = results.count('FAIL')
    print(f"\n{results.count('PASS')} passed, {failed} failed (QGIS {Qgis.QGIS_VERSION})", flush=True)
    shutil.rmtree(work, ignore_errors=True)
    sys.stdout.flush()
    os._exit(1 if failed else 0)  # skip the QGIS teardown, it may crash on exit


if __name__ == '__main__':
    main()

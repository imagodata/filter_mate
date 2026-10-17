# -*- coding: utf-8 -*-
"""
Subset strings, combinations and QGIS -> SQL conversions counted in a real QGIS.

2026-10-17: values containing "et", "ou", "non", quotes, parentheses, double
spaces or SQL keywords were rewritten by the sanitizer, the combiners and the
converters, and the combine operator of the target layers was ignored. This
script writes a GeoPackage and a Shapefile (and a PostGIS table when
``FM_PG_DSN`` is set) whose ``nom`` values are those traps, applies the
plugin's functions and counts the features QGIS really returns.

Prints one ``PASS`` / ``FAIL`` line per scenario (expected / got feature
count) and exits with 1 when one fails. Not a pytest module:

    python3 tests/qgis_headless/check_combine_literals.py
    FM_PG_DSN="host=fm-pg port=5432 dbname=postgres user=postgres password=fm" \\
        python3 tests/qgis_headless/check_combine_literals.py

``FM_REPO`` copies another checkout of the plugin (to count the same
scenarios before a fix).
"""
import os
import shutil
import sys
import tempfile
import traceback

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from osgeo import ogr, osr  # noqa: E402
from qgis.core import QgsApplication, QgsFeatureRequest, QgsProviderRegistry, QgsVectorLayer  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get('FM_REPO') or os.path.dirname(os.path.dirname(HERE))
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')

# id, nom: every value is a trap for a rewrite that ignores quotes.
NAMES = {
    1: 'Plages, dunes et sable',
    2: 'Pont ou Rivière',
    3: 'oui non peut-être',
    4: "l'Ariège",
    5: 'b)',
    6: 'Saint  Jean',
    7: 'Case-Pilote',
    8: 'WHERE x',
    9: 'Paris from above',
    10: 'Route',
    11: 'Chemin',
    12: 'Route du perimeter',
}
ROWS = [{'id': i, 'nom': nom, 'actif': i % 2 == 0, 'pop': i * 10, 'buffer_m': i * 1.5,
         'x': 700000.0 + 10 * i, 'y': 6600000.0} for i, nom in NAMES.items()]

app = QgsApplication([], False)
app.initQgis()
results = []


def count(rows_filter):
    return sum(1 for row in ROWS if rows_filter(row))


def features(layer):
    return sum(1 for _ in layer.getFeatures(QgsFeatureRequest()))


def check(name, expected, got, detail=''):
    status = 'PASS' if expected == got else 'FAIL'
    results.append(status)
    print(f"{status:<5} {name}: expected {expected}, got {got}  {detail}".rstrip(), flush=True)


# --- data ------------------------------------------------------------------------

def write_file(path, driver_name, layer_name):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(2154)
    driver = ogr.GetDriverByName(driver_name)
    source = driver.CreateDataSource(path)
    layer = source.CreateLayer(layer_name, srs, ogr.wkbPoint)
    for name, kind in (('id', ogr.OFTInteger), ('nom', ogr.OFTString), ('actif', ogr.OFTInteger),
                       ('pop', ogr.OFTInteger), ('buffer_m', ogr.OFTReal)):
        definition = ogr.FieldDefn(name, kind)
        if name == 'actif' and driver_name == 'GPKG':
            definition.SetSubType(ogr.OFSTBoolean)
        layer.CreateField(definition)
    for row in ROWS:
        feature = ogr.Feature(layer.GetLayerDefn())
        for name in ('id', 'nom', 'pop', 'buffer_m'):
            feature.SetField(name, row[name])
        feature.SetField('actif', int(row['actif']))
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint_2D(row['x'], row['y'])
        feature.SetGeometry(point)
        layer.CreateFeature(feature)
    source = None


def postgres_layer(dsn):
    """public.fm_lieux in PostGIS (pop stored as text, as real data often is)."""
    metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
    connection = metadata.createConnection(dsn, {})
    values = ', '.join(
        "({id}, '{nom}', {actif}, '{pop}', {buffer_m}, ST_SetSRID(ST_MakePoint({x}, {y}), 2154))".format(
            nom=row['nom'].replace("'", "''"), actif='TRUE' if row['actif'] else 'FALSE',
            **{k: v for k, v in row.items() if k not in ('nom', 'actif')})
        for row in ROWS)
    connection.executeSql('DROP TABLE IF EXISTS public.fm_lieux')
    connection.executeSql('CREATE TABLE public.fm_lieux (id integer PRIMARY KEY, nom varchar(80), actif boolean, '
                          'pop varchar(10), buffer_m double precision, geom geometry(Point, 2154))')
    connection.executeSql(f'INSERT INTO public.fm_lieux VALUES {values}')  # nosec B608 - test data
    uri = f"{dsn} key='id' srid=2154 type=Point table=\"public\".\"fm_lieux\" (geom)"
    return QgsVectorLayer(uri, 'fm_lieux', 'postgres')


# --- scenarios -------------------------------------------------------------------

def apply(layer, subset):
    from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string
    layer.setSubsetString('')
    accepted = safe_set_subset_string(layer, subset)
    return features(layer), f"accepted={accepted} subset={layer.subsetString()[:90]!r}"


def subset_scenarios(label, layer, has_boolean):
    """safe_set_subset_string (sanitizer) on values with French operators, quotes, parentheses."""
    cases = [
        ("\"nom\" = 'Plages, dunes et sable'", count(lambda r: r['id'] == 1)),
        ("\"nom\" IN ('Pont ou Rivière', 'oui non peut-être')", 2),
        ("\"nom\" IN ('a', 'b)')", 1),
        ("\"nom\" = 'Saint  Jean'", 1),
        ("\"nom\" = 'l''Ariège'", 1),
        ("\"nom\" = 'Route' ET \"id\" > 5", 1),
    ]
    if has_boolean:
        cases.append(("\"nom\" <> 'Route' AND ( \"actif\" )", count(lambda r: r['nom'] != 'Route' and r['actif'])))
    for subset, expected in cases:
        got, detail = apply(layer, subset)
        check(f"{label} subset {subset}", expected, got, detail)


def combine_scenarios(label, layer, provider_type):
    """combine_with_old_subset (+ duplicate IN optimizer) then setSubsetString."""
    from filter_mate.core.filter.expression_combiner import combine_with_old_subset
    from filter_mate.core.filter.expression_sanitizer import optimize_duplicate_in_clauses
    cases = [
        ('"id" = 12', '"id" = 1', 'OR', 2),
        ('"id" = 12', '"id" = 1', 'AND', 0),
        ('"id" = 1', '"id" = 1', 'AND NOT', 0),
        ("\"nom\" = 'WHERE x' OR \"id\" = 1", '"id" > 5', 'AND', 1),
        ("\"nom\" = 'Paris from above'", '"id" > 5', 'AND', 1),
        ('"id" IN (1, 2, 3)', '"id" IN (2, 3)', 'AND', 2),
        ("\"nom\" = 'Plages, dunes et sable'", '"id" > 10', 'OR', 3),
    ]
    for old, new, operator, expected in cases:
        combined = combine_with_old_subset(new, old, operator, provider_type, optimize_duplicate_in_clauses)
        got, detail = apply(layer, combined)
        check(f"{label} ({old}) {operator} ({new})", expected, got, detail)


def conversion_scenarios(label, layer, provider):
    """ExpressionService.to_sql (attribute expression of a SQL source layer) then setSubsetString."""
    from filter_mate.core.domain.filter_expression import ProviderType
    from filter_mate.core.services.expression_service import ExpressionService
    target = ProviderType.POSTGRESQL if provider == 'postgresql' else ProviderType.SPATIALITE
    cases = [
        ("\"nom\" ILIKE '%l''ariège%'", 1),
        ("\"nom\" = 'Case-Pilote'", 1),
        ("length(\"nom\") > 15", count(lambda r: len(r['nom']) > 15)),
        ("\"nom\" <> 'Route'", 11),
        ("\"pop\" > 100", count(lambda r: r['pop'] > 100)),
        ('"actif" = TRUE', count(lambda r: r['actif'])),
    ]
    for expression, expected in cases:
        sql = ExpressionService().to_sql(expression, target, 'geom')
        got, detail = apply(layer, sql)
        check(f"{label} to_sql {expression}", expected, got, detail)


def buffer_expression_scenarios(label, layer, provider):
    """Dynamic buffer expression converters, used in a condition on the target."""
    if provider == 'postgresql':
        from filter_mate.adapters.backends.postgresql.filter_executor import qgis_expression_to_postgis as convert
    else:
        from filter_mate.adapters.backends.spatialite.filter_executor import qgis_expression_to_spatialite as convert
    cases = [
        ('"buffer_m" * 2', lambda r: r['buffer_m'] * 2 > 20),
        ("if(\"nom\" = 'Route, chemin', 100, \"buffer_m\" * 4)", lambda r: r['buffer_m'] * 4 > 20),
        ("if(\"nom\" = 'Route du perimeter', 100, 0)", lambda r: r['nom'] == 'Route du perimeter'),
        # disc area ~ 3.12 r² (segmented buffer): > 20 from r = 2.6 m, i.e. id >= 2
        ('area(buffer($geometry, "buffer_m"))', lambda r: 3.12 * r['buffer_m'] ** 2 > 20),
    ]
    for expression, rows_filter in cases:
        sql = f'({convert(expression, "geom")}) > 20'
        got, detail = apply(layer, sql)
        check(f"{label} buffer expression {expression}", count(rows_filter), got, detail)


class _Parent:
    """The task as FilterOrchestrator sees it: its operator for the targets."""

    def __init__(self, operator):
        self.operator = operator
        self.warning_messages = []

    def _get_combine_operator(self):
        return self.operator


def target_scenarios(label, layer, backend_name, source=None):
    """FilterOrchestrator._determine_subset_strategy + the backend's apply_filter on a target."""
    from filter_mate.core.filter.filter_orchestrator import BackendFactory, FilterOrchestrator
    from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string
    old = "\"nom\" = 'Route'"
    new_ids = {11, 12}
    for operator in ('AND', 'OR', 'AND NOT', None):
        safe_set_subset_string(layer, old)
        orchestrator = FilterOrchestrator(
            task_parameters={}, subset_queue_callback=lambda lyr, expression: safe_set_subset_string(lyr, expression),
            parent_task=_Parent(operator), get_predicates_callback=lambda: {'ST_Intersects': 'ST_Intersects'})
        old_subset, combine_operator = orchestrator._determine_subset_strategy(layer)
        backend = BackendFactory.get_backend(backend_name, layer, orchestrator.task_parameters)
        if backend_name == 'ogr':
            expression = backend.build_expression(layer_props={'layer_name': layer.name()},
                                                  predicates={'ST_Intersects': True}, source_geom=source)
        else:
            expression = '"id" > 10'
        applied = backend.apply_filter(layer, expression, old_subset, combine_operator)
        old_ids = {10}
        expected = len({'AND': old_ids & new_ids, 'OR': old_ids | new_ids, 'AND NOT': old_ids - new_ids,
                        None: new_ids}[operator])
        check(f"{label} target {backend_name} operator {operator}", expected, features(layer),
              f"applied={applied} subset={layer.subsetString()[:90]!r}")
    layer.setSubsetString('')


def postgres_source_scenarios(layer):
    """The source flow: subset combined upstream, then the direct PostgreSQL filter action."""
    from filter_mate.adapters.backends.postgresql.filter_actions import execute_filter_action_postgresql_direct
    from filter_mate.core.filter.expression_combiner import combine_with_old_subset
    from filter_mate.core.tasks.builders.subset_string_builder import SubsetStringBuilder
    from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string
    old, new = "\"nom\" = 'Route'", '"id" > 10'
    for operator, expected in (('OR', 3), ('AND', 0), (None, 2)):
        layer.setSubsetString('')
        safe_set_subset_string(layer, old)
        combined = combine_with_old_subset(new, old, operator, 'postgresql')
        queue = [combined]  # apply_filter_and_update_subset queues the combined expression first
        execute_filter_action_postgresql_direct(
            layer=layer, sql_subset_string=f'SELECT "fm_lieux"."id", "fm_lieux"."geom" FROM "public"."fm_lieux" '
                                           f'WHERE {combined}',  # nosec B608 - test data
            primary_key_name='id', cur=None, conn=None, seq_order=1,
            queue_subset_fn=lambda lyr, expression: queue.append(expression),
            get_connection_fn=lambda: None, ensure_stats_fn=lambda *args: None,
            extract_where_fn=lambda sql: SubsetStringBuilder.extract_where_clause(sql)[1],
            insert_history_fn=lambda *args: None, source_schema='public', source_table='fm_lieux',
            source_geom='geom')
        for expression in queue:  # finished(): applied in order, the last one wins
            safe_set_subset_string(layer, expression)
        check(f"postgres source ({old}) {operator} ({new})", expected, features(layer),
              f"requests={len(queue)} subset={layer.subsetString()[:90]!r}")
    layer.setSubsetString('')


def main():
    work = tempfile.mkdtemp(prefix='fm_literals_')
    plugins = os.path.join(work, 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    sys.path.append(os.path.join(QgsApplication.pkgDataPath(), 'python', 'plugins'))
    from qgis.core import Qgis
    print(f"INFO  QGIS {Qgis.QGIS_VERSION}, plugin copied from {REPO}", flush=True)

    gpkg_path = os.path.join(work, 'lieux.gpkg')
    shp_path = os.path.join(work, 'lieux.shp')
    write_file(gpkg_path, 'GPKG', 'lieux')
    write_file(shp_path, 'ESRI Shapefile', 'lieux')
    gpkg = QgsVectorLayer(f'{gpkg_path}|layername=lieux', 'lieux_gpkg', 'ogr')
    shp = QgsVectorLayer(shp_path, 'lieux_shp', 'ogr')
    source = QgsVectorLayer('Polygon?crs=EPSG:2154', 'source', 'memory')
    from qgis.core import QgsFeature, QgsGeometry
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt('POLYGON((700105 6599995, 700125 6599995, 700125 6600005, '
                                            '700105 6600005, 700105 6599995))'))  # points 11 and 12
    source.dataProvider().addFeatures([feature])

    layers = [('gpkg', gpkg, 'spatialite', True), ('shp', shp, 'ogr', False)]
    dsn = os.environ.get('FM_PG_DSN')
    if dsn:
        pg = postgres_layer(dsn)
        layers.append(('postgres', pg, 'postgresql', True))
    for label, layer, _backend, _boolean in layers:
        print(f"INFO  {label}: valid={layer.isValid()} features={features(layer)}", flush=True)

    steps = []
    for label, layer, backend, has_boolean in layers:
        steps.append((subset_scenarios, (label, layer, has_boolean)))
        steps.append((combine_scenarios, (label, layer, 'postgresql' if backend == 'postgresql' else 'ogr')))
        if backend in ('spatialite', 'postgresql'):
            steps.append((conversion_scenarios, (label, layer, backend)))
            steps.append((buffer_expression_scenarios, (label, layer, backend)))
    steps.append((target_scenarios, ('gpkg', gpkg, 'spatialite')))
    steps.append((target_scenarios, ('shp', shp, 'ogr', source)))
    if dsn:
        steps.append((target_scenarios, ('postgres', pg, 'postgresql')))
        steps.append((postgres_source_scenarios, (pg,)))
    for step, args in steps:
        print(f"--- {step.__name__} {args[0] if isinstance(args[0], str) else ''}", flush=True)
        try:
            step(*args)
        except Exception as exc:
            traceback.print_exc()
            check(f"{step.__name__} raised {type(exc).__name__}: {exc}", 'no error', 'error')

    failed = results.count('FAIL')
    print(f"\n{results.count('PASS')} passed, {failed} failed (QGIS {Qgis.QGIS_VERSION})", flush=True)
    shutil.rmtree(work, ignore_errors=True)
    sys.stdout.flush()
    os._exit(1 if failed else 0)  # skip the QGIS teardown, it may crash on exit


if __name__ == '__main__':
    main()

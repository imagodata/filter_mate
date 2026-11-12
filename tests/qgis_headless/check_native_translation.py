# -*- coding: utf-8 -*-
"""
QGIS predicates written in the native SQL of the source, compared with QGIS itself.

For a GeoPackage, a Shapefile (and a PostGIS table when ``FM_PG_DSN`` is set),
each expression is evaluated by QGIS on every feature of the unfiltered layer
(the reference), then written by ``native_filter_translation`` and applied as
the layer's subset string: the features the source returns must be the same.
An expression the translator leaves to QGIS is a ``SKIP`` (its reason is
printed) unless it is listed as one that must be written.

Prints one ``PASS`` / ``FAIL`` / ``SKIP`` line per case and exits with 1 when
one fails. Not a pytest module (on Windows: ``python-qgis.bat`` of the QGIS
installation, with the path of this file):

    docker run --rm --network none -v "$PWD:/src:ro" qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_native_translation.py
    FM_PG_DSN="host=fm-pg port=5432 dbname=postgres user=postgres password=fm" \\
        python3 tests/qgis_headless/check_native_translation.py
"""
import os
import shutil
import sys
import tempfile
import traceback

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from osgeo import ogr, osr  # noqa: E402
from qgis.core import (  # noqa: E402
    QgsApplication, QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsFeatureRequest,
    QgsProviderRegistry, QgsVectorLayer,
)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get('FM_REPO') or os.path.dirname(os.path.dirname(HERE))
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')

# id, pop (integer), ratio (real), nom (text), code (text holding digits)
ROWS = [
    (1, 10, 0.5, 'Route', '10'),
    (2, 0, 1.5, 'route', '9'),
    (3, 7, None, 'ROUTE du Sud', '007'),
    (4, None, 2.0, None, None),
    (5, 3, 3.0, "l'Ariège", 'A1'),
    (6, 9, 4.5, 'r*ute', '100'),
    (7, 2, 0.1, 'Éte', ''),
    (8, -4, 0.3, 'route_66', '-4'),
    (9, 1000, 1e-05, '50%', '1e3'),
    (10, 5, 2.5, 'Été', ' 5'),
    (11, 6, 0.3, 'Route\nNord', '6'),
    (12, 1, 0.2, '\u017faint', 's'),        # long s
    (13, 4, 0.7, 'Kelvin \u212a', 'k'),     # Kelvin sign
    (14, 8, 6656395.210250434, 'Grand', '14'),  # SQLite 3.45 reads this literal one ulp off
]

# (expression, dialects that MUST write it entirely)
ALL, DB = ('postgresql', 'sqlite', 'ogr_sql'), ('postgresql', 'sqlite')
CASES = [
    ('"pop" > 5', ALL),
    ('"pop" >= 7 AND "ratio" < 2', ALL),
    ('"pop" = 10 OR "id" IN (2, 3)', ALL),
    ('"id" NOT IN (1, 2, 3)', ALL),
    ('NOT ("pop" > 5)', ALL),
    ('NOT ("pop" > 5 OR "ratio" < 2)', ALL),
    ('NOT ("pop" > 5 AND "ratio" < 2)', DB),        # OGR SQL: TRUE AND NULL is FALSE
    ('"pop" IS NULL', ALL),
    ('"nom" IS NOT NULL AND "pop" <> 0', ALL),
    ('"pop" BETWEEN 3 AND 9', ALL),
    ('"pop" NOT BETWEEN 3 AND 9', ALL),
    ('"ratio" BETWEEN 1 AND 2.5', ALL),
    ('"pop" BETWEEN "id" AND 9.5', DB),             # OGR SQL: bound read with the type of the first two
    ('2 NOT BETWEEN "pop" AND 1', DB),
    ('"pop" + "id" > 12', ALL),
    ('"pop" * 2 - 1 = 13', ALL),
    ('"ratio" * 3 = 4.5', ALL),
    ('"ratio" * 3 > 0.8', ALL),
    ('"ratio" * 3 = 0.3', ALL),                     # 0.30000000000000004: qgsDoubleNear
    ('"ratio" * 3 <> 0.3', ALL),
    ('"ratio" = 0.3', ALL),
    ('-"pop" < -8', ()),                                # QGIS: -NULL of an integer field is 0
    ('"pop" > -5', ALL),
    ('"ratio" = 0.00001', ALL),
    ('"ratio" = 6656395.210250434', ALL),
    ('"ratio" >= 6656395.210250434', ALL),
    ('"ratio" < 6656395.210250434', ALL),
    ('"pop" / 2 > 3', ALL),
    ('"pop" / 2 = 3.5', ALL),
    ('"pop" / -2.5 < -1', ALL),
    ('"ratio" / 3 > 0.4', ALL),
    ('"pop" / 0 > 1', DB),
    ('"id" / "pop" > 0', DB),
    ('"pop" / "ratio" > 10', DB),
    ('"nom" = \'Route\'', DB),
    ('"nom" <> \'Route\'', DB),
    ('\'Route\' = "nom"', DB),
    ('"nom" = \'l\'\'Ariège\'', DB),
    ('"nom" IN (\'route\', \'Été\')', DB),
    ('"nom" NOT IN (\'route\', \'Été\')', DB),
    ('"nom" LIKE \'Route%\'', DB),
    ('"nom" LIKE \'%Nord\'', DB),
    ('"nom" LIKE \'Route_Nord\'', DB),
    ('"nom" LIKE \'_oute\'', DB),
    ('"nom" LIKE \'route_66\'', DB),
    ('"nom" NOT LIKE \'Route%\'', DB),
    ('"nom" ILIKE \'route%\'', DB),
    ('"nom" NOT ILIKE \'route%\'', DB),
    ('"nom" ILIKE \'%E\'', DB),
    ('"nom" ILIKE \'saint\'', DB),                # long s
    ('"nom" ILIKE \'% k\'', DB),                  # Kelvin sign
    ('"nom" || \'!\' = \'Route!\'', DB),
    ('coalesce("pop", 100) > 50', DB),
    ('abs("pop" - 10) = 1', DB),
    ('abs("ratio" - 2) < 0.6', DB),
    ('if("pop" > 5, \'grand\', \'petit\') = \'petit\'', DB),
    ('CASE WHEN "pop" > 5 THEN 1 WHEN "pop" > 2 THEN 2 END = 2', DB),
    ('CASE WHEN "nom" LIKE \'R%\' THEN "pop" ELSE "id" END > 6', DB),
    ('upper("nom") = \'ROUTE\'', ('postgresql',)),
    ('lower("nom") = \'été\'', ('postgresql',)),
    ('floor("ratio") = 2', ('postgresql',)),
    ('ceil("ratio") = 2', ('postgresql',)),
    ('coalesce("nom", \'\') LIKE \'R%\'', DB),         # the sanitizer took COALESCE(...) GLOB for a display
    ('"nom" NOT LIKE \'A%\'', DB),
    ('coalesce("pop", 0) > 5 AND "ratio" < 3', DB),
    # left to QGIS today: printed with their reason, compared when written
    ('-"pop" > -1', ()),                                # QGIS: -NULL of an integer field is 0
    ('-"pop" IS NULL', ()),
    ('length("nom") = 5', ()),
    ('coalesce("pop") = 3', ()),
    ('"ratio" IN (0.5, 1.5)', ()),
    ('"code" > 9', ()),
    ('"code" = 10', ()),
    ('"nom" < \'m\'', ()),
    ('"nom" LIKE \'50\\%\'', ()),
    ('"nom" LIKE \'r*%\'', ()),
    ('"nom" ILIKE \'ét%\'', ()),
    ('"pop" % 2 = 0', ()),
    ('"pop" // 2 = 3', ()),
    ('"pop" ^ 2 > 50', ()),
    ('round("ratio") = 2', ()),
    ('regexp_match("nom", \'^R\') > 0', ()),
    ('$id > 3', ()),
    ('"pop" > 5 AND regexp_match("nom", \'^R\') > 0', ()),
]

app = QgsApplication([], False)
app.initQgis()
results = []


def report(status, name, detail=''):
    results.append(status)
    print(f"{status:<5} {name}  {detail}".rstrip(), flush=True)


def write_file(path, driver_name, layer_name):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(2154)
    source = ogr.GetDriverByName(driver_name).CreateDataSource(path)
    layer = source.CreateLayer(layer_name, srs, ogr.wkbPoint, options=['ENCODING=UTF-8'] if 'Shape' in driver_name else [])
    for name, kind in (('id', ogr.OFTInteger), ('pop', ogr.OFTInteger), ('ratio', ogr.OFTReal),
                       ('nom', ogr.OFTString), ('code', ogr.OFTString)):
        layer.CreateField(ogr.FieldDefn(name, kind))
    for index, row in enumerate(ROWS):
        feature = ogr.Feature(layer.GetLayerDefn())
        for name, value in zip(('id', 'pop', 'ratio', 'nom', 'code'), row):
            if value is not None:
                feature.SetField(name, value)
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint_2D(700000.0 + 10 * index, 6600000.0)
        feature.SetGeometry(point)
        layer.CreateFeature(feature)
    source = None


def write_nocase_gpkg(path):
    """A GeoPackage attribute table whose text column is COLLATE NOCASE (made by another tool than OGR)."""
    import sqlite3
    ogr.GetDriverByName('GPKG').CreateDataSource(path).FlushCache()  # an empty GeoPackage, closed
    connection = sqlite3.connect(path)
    connection.execute('CREATE TABLE nocase (fid INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, id INTEGER, '
                       'pop INTEGER, ratio REAL, nom TEXT COLLATE NOCASE, code TEXT COLLATE RTRIM)')
    connection.executemany('INSERT INTO nocase (id, pop, ratio, nom, code) VALUES (?, ?, ?, ?, ?)', ROWS)
    connection.execute("INSERT INTO gpkg_contents (table_name, data_type, identifier) "
                       "VALUES ('nocase', 'attributes', 'nocase')")
    connection.commit()
    connection.close()


def sql_literal(value):
    if value is None:
        return 'NULL'
    return "'" + value.replace("'", "''") + "'" if isinstance(value, str) else repr(value)


def postgres_layers(dsn):
    """Two tables: integer / double precision, then bigint / numeric (exact arithmetic)."""
    connection = QgsProviderRegistry.instance().providerMetadata('postgres').createConnection(dsn, {})
    layers = []
    for table, pop_type, ratio_type in (('fm_native_a', 'integer', 'double precision'),
                                        ('fm_native_b', 'bigint', 'numeric(12,6)')):
        values = ', '.join('({}, {})'.format(
            ', '.join(sql_literal(value) for value in row),
            f'ST_SetSRID(ST_MakePoint({700000 + 10 * index}, 6600000), 2154)') for index, row in enumerate(ROWS))
        connection.executeSql(f'DROP TABLE IF EXISTS public.{table}')
        connection.executeSql(f'CREATE TABLE public.{table} (id integer PRIMARY KEY, pop {pop_type}, '
                              f'ratio {ratio_type}, nom varchar(80), code text, geom geometry(Point, 2154))')
        connection.executeSql(f'INSERT INTO public.{table} VALUES {values}')  # nosec B608 - test data
        uri = f"{dsn} key='id' srid=2154 type=Point table=\"public\".\"{table}\" (geom)"
        layers.append((f'postgres {pop_type}/{ratio_type.split("(")[0]}', QgsVectorLayer(uri, table, 'postgres')))
    return layers


def keys(layer):
    return sorted(feature['id'] for feature in layer.getFeatures(QgsFeatureRequest()))


def reference(layer, text):
    """Keys of the features QGIS itself keeps, evaluated one by one without the provider."""
    expression = QgsExpression(text)
    context = QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
    expression.prepare(context)
    kept = []
    for feature in layer.getFeatures(QgsFeatureRequest()):
        context.setFeature(feature)
        value = expression.evaluate(context)
        if expression.hasEvalError():
            raise ValueError(expression.evalErrorString())
        if value is not None and value == value and bool(value) and str(value) != 'NULL':
            kept.append(feature['id'])
    return sorted(kept)


def compare(label, layer):
    from filter_mate.adapters.qgis.native_filter_translation import native_dialect_for_layer, translate_for_layer
    dialect = native_dialect_for_layer(layer)
    print(f"--- {label}: dialect {dialect}", flush=True)
    for text, required in CASES:
        layer.setSubsetString('')
        name = f"{label}: {text}"
        try:
            expected = reference(layer, text)
            result = translate_for_layer(layer, text)
        except Exception as exc:
            traceback.print_exc()
            report('FAIL', name, f"raised {type(exc).__name__}: {exc}")
            continue
        if result is None or result.status.value != 'FULL':
            reason = 'no dialect' if result is None else f"{result.status.value}: {result.reason}"
            report('FAIL' if dialect in required else 'SKIP', name, f"not written ({reason})")
            continue
        accepted = layer.setSubsetString(result.sql)
        got = keys(layer) if accepted else None
        layer.setSubsetString('')
        report('PASS' if got == expected else 'FAIL', name,
               f"sql={result.sql!r} expected={expected} got={got} accepted={accepted}")


def executor_path(label, layer, provider_type):
    """The plugin's own entry: AttributeFilterExecutor.process_qgis_expression then the subset.

    A case its dialect writes must give QGIS's answer. Any other goes through
    the former conversion: its answer is printed (``OLD``), right or wrong.
    """
    from filter_mate.adapters.qgis.native_filter_translation import APPLIED_DIALECTS, native_dialect_for_layer
    from filter_mate.core.tasks.executors.attribute_filter_executor import AttributeFilterExecutor
    dialect = native_dialect_for_layer(layer)
    for text, required in (('"pop" BETWEEN 3 AND 9', ALL), ('"pop" / 2 = 3.5', ALL),
                           ('"nom" LIKE \'Route%\'', DB), ('"nom" LIKE \'route%\'', DB),
                           ('"nom" = \'route\'', DB), ('"pop" > 5 AND "nom" = \'Route\'', DB)):
        layer.setSubsetString('')
        expected = reference(layer, text)
        executor = AttributeFilterExecutor(layer=layer, provider_type=provider_type, primary_key='id')
        processed, _ = executor.process_qgis_expression(text)
        accepted = bool(processed) and executor.apply_filter(processed)
        got = keys(layer) if accepted else None
        layer.setSubsetString('')
        written = dialect in required and dialect in APPLIED_DIALECTS
        status = ('PASS' if got == expected else 'FAIL') if written else 'OLD'
        report(status, f"{label} executor: {text}", f"sql={processed!r} expected={expected} got={got}")


# Expressions the translation leaves (in part) to QGIS: QGIS evaluates them, the
# subset lists keys (hybrid). Through the plugin's own entry, with its key.
HYBRID_CASES = [
    '"nom" = \'route\'',                                   # Shapefile: OGR SQL ignores case
    '"pop" > 5 AND regexp_match("nom", \'^R\') > 0',
    '"pop" > 5 AND regexp_match("nom", \'zzz\') > 0',      # nothing kept
    '"pop" > 5 AND length("nom") >= 0',                    # QGIS excludes nothing from the native part
    '"pop" >= 0 AND "nom" <> \'r*ute\'',                   # Shapefile: few keys excluded
    '"code" > 9',
    'length("nom") = 5',
    'regexp_match("nom", \'^R\') > 0 OR "pop" > 5',
    '"ratio" IN (0.5, 1.5)',
    'NOT ("pop" > 5 AND "ratio" < 2)',                     # Shapefile: a NOT over an AND
    '-"pop" > -1',                                         # QGIS: -NULL of an integer field is 0
    '-"pop" IS NULL',
    'coalesce(abs("pop"), 7) > 6',                         # the sanitizer truncates COALESCE(abs(CAST(...
    '"ratio" = 6656395.210250434 AND regexp_match("nom", \'^G\') > 0',
]
# (old subset, combine operator, expression): hybrid with AND only, the former path otherwise
COMBINED_CASES = [
    ('"pop" > 2', 'AND', 'regexp_match("nom", \'o\') > 0'),
    ('"pop" > 2', 'AND', '"nom" = \'route\' OR "nom" = \'Route\''),
    ('"pop" > 2', 'OR', 'regexp_match("nom", \'o\') > 0'),
    ('"pop" > 2', 'AND NOT', 'regexp_match("nom", \'o\') > 0'),
    ('"pop" > 2', None, 'regexp_match("nom", \'o\') > 0'),
]


def run_executor(layer, provider_type, text, old=None, operator=None):
    """process_qgis_expression, combination with the old subset and safe_set_subset_string, as the task runs them."""
    from filter_mate.core.tasks.executors.attribute_filter_executor import AttributeFilterExecutor
    layer.setSubsetString(old or '')
    executor = AttributeFilterExecutor(layer=layer, provider_type=provider_type, primary_key='fid',
                                       old_subset=old, combine_operator=operator)
    processed, _ = executor.process_qgis_expression(text)
    combined = executor.combine_with_old_subset(processed) if processed else None
    accepted = bool(combined) and executor.apply_filter(combined)
    got = keys(layer) if accepted else None
    layer.setSubsetString('')
    return processed in executor.native_origins, combined, got


def hybrid_path(label, layer, provider_type):
    """The plugin's entry on expressions left to QGIS: the hybrid subset keeps what QGIS keeps.

    Hybrid subsets are written for SQLite sources only: on a Shapefile these
    cases take the former conversion (OLD, printed, not asserted).
    """
    for text in HYBRID_CASES:
        layer.setSubsetString('')
        expected = reference(layer, text)
        written, subset, got = run_executor(layer, provider_type, text)
        status = ('PASS' if got == expected else 'FAIL') if written else 'OLD'
        report(status, f"{label} hybrid: {text}", f"subset={subset!r:.160} expected={expected} got={got}")
    for old, operator, text in COMBINED_CASES:
        layer.setSubsetString('')
        joined = {'AND': '({}) AND ({})', 'OR': '({}) OR ({})', 'AND NOT': '({}) AND NOT ({})'}.get(operator, '{1}')
        expected = reference(layer, joined.format(old, text))
        written, subset, got = run_executor(layer, provider_type, text, old, operator)
        status = ('PASS' if got == expected else 'FAIL') if written else 'OLD'
        if operator != 'AND' and written:
            status = 'FAIL'  # a list of keys read through the old subset, or negated: never written
        report(status, f"{label} combined {operator}: {old} / {text}",
               f"subset={subset!r:.160} expected={expected} got={got}")


def main():
    work = tempfile.mkdtemp(prefix='fm_native_')
    plugins = os.path.join(work, 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    sys.path.append(os.path.join(QgsApplication.pkgDataPath(), 'python', 'plugins'))
    from qgis.core import Qgis
    print(f"INFO  QGIS {Qgis.QGIS_VERSION}, plugin copied from {REPO}", flush=True)

    gpkg_path, shp_path = os.path.join(work, 'lieux.gpkg'), os.path.join(work, 'lieux.shp')
    write_file(gpkg_path, 'GPKG', 'lieux')
    write_file(shp_path, 'ESRI Shapefile', 'lieux')
    nocase_path = os.path.join(work, 'nocase.gpkg')
    write_nocase_gpkg(nocase_path)
    layers = [('gpkg', QgsVectorLayer(f'{gpkg_path}|layername=lieux', 'lieux_gpkg', 'ogr'), 'spatialite'),
              ('gpkg nocase', QgsVectorLayer(f'{nocase_path}|layername=nocase', 'nocase', 'ogr'), 'spatialite'),
              ('shp', QgsVectorLayer(shp_path, 'lieux_shp', 'ogr'), 'ogr')]
    dsn = os.environ.get('FM_PG_DSN')
    if dsn:
        layers += [(label, layer, 'postgresql') for label, layer in postgres_layers(dsn)]
    for label, layer, provider_type in layers:
        print(f"INFO  {label}: valid={layer.isValid()} features={len(keys(layer))}", flush=True)
        try:
            compare(label, layer)
            executor_path(label, layer, provider_type)
            hybrid_path(label, layer, provider_type)
        except Exception as exc:
            traceback.print_exc()
            report('FAIL', f"{label} raised {type(exc).__name__}: {exc}")

    failed = results.count('FAIL')
    print(f"\n{results.count('PASS')} passed, {failed} failed, {results.count('SKIP')} left to QGIS, "
          f"{results.count('OLD')} through the former conversion (QGIS {Qgis.QGIS_VERSION})", flush=True)
    shutil.rmtree(work, ignore_errors=True)
    sys.stdout.flush()
    os._exit(1 if failed else 0)  # skip the QGIS teardown, it may crash on exit


if __name__ == '__main__':
    main()

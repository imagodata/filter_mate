# -*- coding: utf-8 -*-
"""
The source selection read in the global, project and layer variables of the source layer, in a real QGIS.

2026-11-13: a request filtered by an expression has no context of its own, so ``"pop" > @seuil`` read the
variable as NULL and kept no feature. The source selection is now read in the context of the source layer
(``adapters.backends.source_refusal.with_layer_context``), read on the main thread when the filter task is made
(``SOURCE_CONTEXT_KEY``), and also when its features are read through a copy of the layer without its subset
(that copy, out of the project, has none of the layer variables). For a GeoPackage (``ogr`` provider) and a
SpatiaLite database:

- PATH 3A (``ExpressionBuilder._features_of_the_selection``): through the source layer and its subset, and on the
  whole layer through the copy (OR / replace), with a layer variable and a project variable, with the context read
  before and without it;
- SpatiaLite's source preparation (``_features_matching``) through the copy;
- the OGR source preparation (``selection_request`` on the layer itself);
- ``variable_values``, part of the cache keys of EXPLORING: it follows a change of the variable.

Every expected count comes from the data (pop = 1..40), not from QGIS nor the plugin.

    docker run --rm -v "$PWD:/src:ro" qgis/qgis:stable python3 /src/tests/qgis_headless/check_source_selection_context.py

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
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsExpressionContextUtils, QgsFeatureRequest, QgsProject, QgsVectorLayer)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get('FM_REPO') or os.path.dirname(os.path.dirname(HERE))
PACKAGE = 'filter_mate'
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')

POPS = range(1, 41)
SUBSET = '"pop" <= 10'  # the previous filter of the source layer
LAYER_SEUIL, PROJECT_SEUIL, LOW = 30, 35, 6  # @seuil (layer), @pseuil (project), @bas (layer)

app = QgsApplication([], False)
app.initQgis()
results = []


def check(name, expected, got, detail=''):
    status = 'PASS' if expected == got else 'FAIL'
    results.append(status)
    print(f"{status:<5} {name}: expected {expected}, got {got}  {detail}".rstrip(), flush=True)


def write_file(path, driver_name, options=()):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(2154)
    source = ogr.GetDriverByName(driver_name).CreateDataSource(path, options=list(options))
    layer = source.CreateLayer('points', srs, ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn('pop', ogr.OFTInteger))
    for pop in POPS:
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField('pop', pop)
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint_2D(700000.0 + 10 * pop, 6600000.0)
        feature.SetGeometry(point)
        layer.CreateFeature(feature)
    source = None


def pops(features):
    return sorted(feature['pop'] for feature in features)


def expected(expression, subset=False):
    """The pops ``expression`` keeps, from the data alone."""
    seuils = {'@seuil': LAYER_SEUIL, '@pseuil': PROJECT_SEUIL, '@bas': LOW}
    for name, value in seuils.items():
        if name in expression:
            kept = [pop for pop in POPS if pop > value]
            break
    return [pop for pop in kept if not subset or pop <= 10]


def scenarios(label, layer):
    from filter_mate.adapters.backends.source_refusal import (
        SOURCE_CONTEXT_KEY, layer_context, selection_request, variable_values)
    from filter_mate.adapters.backends.spatialite import filter_executor as spatialite_executor
    from filter_mate.core.filter.expression_builder import ExpressionBuilder
    from qgis.core import QgsExpression

    QgsProject.instance().addMapLayer(layer)
    QgsExpressionContextUtils.setLayerVariable(layer, 'seuil', str(LAYER_SEUIL))  # a text, as the dialog saves it
    QgsExpressionContextUtils.setLayerVariable(layer, 'bas', str(LOW))
    layer.setSubsetString(SUBSET)
    main_thread_context = layer_context(layer)

    # PATH 3A: the selection recorded by this filter, read through the source layer or on the whole layer
    for expression, whole in (('"pop" > @seuil', True), ('"pop" > @pseuil', True), ('"pop" > @bas', False)):
        for with_context in (True, False):
            parameters = {'source_selection_after_task': expression, 'task': {'expression': expression},
                          'source_selection_reads_whole_layer': whole}
            if with_context:
                parameters[SOURCE_CONTEXT_KEY] = main_thread_context
            builder = ExpressionBuilder(parameters, layer, [])
            try:
                got = pops(builder._features_of_the_selection())
            except Exception as exc:
                got = f"{type(exc).__name__}: {exc}"
            check(f"{label}, PATH 3A {expression}, {'whole layer' if whole else 'its subset'}, "
                  f"{'context read before' if with_context else 'context read in place'}",
                  expected(expression, subset=not whole), got)

    # SpatiaLite's source preparation, through the copy without subset
    copy = spatialite_executor._unfiltered_copy(layer)
    check(f"{label}, the copy without subset opens", True, copy is not None and copy.subsetString() == '')
    if copy is not None:
        for expression in ('"pop" > @seuil', '"pop" > @pseuil'):
            try:
                got = pops(spatialite_executor._features_matching(
                    copy, expression, layer, {SOURCE_CONTEXT_KEY: main_thread_context}))
            except Exception as exc:
                got = f"{type(exc).__name__}: {exc}"
            check(f"{label}, SpatiaLite preparation through the copy, {expression}", expected(expression), got)

    # The OGR source preparation reads the layer itself, in its subset
    request = selection_request(QgsExpression('"pop" > @bas'), layer, main_thread_context)
    check(f"{label}, OGR preparation, \"pop\" > @bas", expected('@bas', subset=True), pops(layer.getFeatures(request)))
    # A context read for another layer is not taken for this one's
    other = QgsVectorLayer('Point?crs=EPSG:2154', 'other', 'memory')
    QgsProject.instance().addMapLayer(other)
    QgsExpressionContextUtils.setLayerVariable(other, 'seuil', '1')
    request = selection_request(QgsExpression('"pop" > @seuil'), layer, layer_context(other))
    check(f"{label}, the context of another layer is read again", expected('@seuil', subset=True),
          pops(layer.getFeatures(request)))
    QgsProject.instance().removeMapLayer(other.id())

    # EXPLORING: the cache key follows a change of the variable
    before = variable_values('"pop" > @seuil', layer)
    QgsExpressionContextUtils.setLayerVariable(layer, 'seuil', '20')
    after = variable_values('"pop" > @seuil', layer)
    QgsExpressionContextUtils.setLayerVariable(layer, 'seuil', str(LAYER_SEUIL))
    check(f"{label}, variable_values follows @seuil", True, bool(before and after and before != after),
          f"{before} -> {after}")
    check(f"{label}, variable_values of an expression without variable", (), variable_values('"pop" > 3', layer))
    QgsProject.instance().removeMapLayer(layer.id())


def main():
    work = tempfile.mkdtemp(prefix='fm_selection_context_')
    plugins = os.path.join(work, 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    sys.path.append(os.path.join(QgsApplication.pkgDataPath(), 'python', 'plugins'))
    print(f"INFO  QGIS {Qgis.QGIS_VERSION}, GDAL {gdal.__version__}, plugin copied from {REPO}", flush=True)
    QgsExpressionContextUtils.setProjectVariable(QgsProject.instance(), 'pseuil', str(PROJECT_SEUIL))

    gpkg_path = os.path.join(work, 'points.gpkg')
    sqlite_path = os.path.join(work, 'points.sqlite')
    write_file(gpkg_path, 'GPKG')
    write_file(sqlite_path, 'SQLite', options=['SPATIALITE=YES'])
    cases = [
        ('GeoPackage', QgsVectorLayer(f'{gpkg_path}|layername=points', 'gpkg', 'ogr')),
        ('SpatiaLite', QgsVectorLayer(f"dbname='{sqlite_path}' table=\"points\" (GEOMETRY)", 'sqlite', 'spatialite')),
    ]
    for label, layer in cases:
        count = sum(1 for _ in layer.getFeatures(QgsFeatureRequest()))
        print(f"--- {label}: valid={layer.isValid()} provider={layer.providerType()} features={count}", flush=True)
        try:
            scenarios(label, layer)
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

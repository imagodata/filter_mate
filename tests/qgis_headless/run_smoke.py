# -*- coding: utf-8 -*-
"""
FilterMate smoke test in a real, headless QGIS (CI: official qgis/qgis Docker images).

Loads the plugin the way ``qgis_process`` does (package import, ``classFactory``
without ``iface``, ``initProcessing()``) from a copy of the repository named
``filter_mate`` (the top-level folders the release zip leaves out are left out
too), then runs cross filters on the synthetic data of ``make_fixtures.py``
through Processing and ``adapters.public_api.operations``.

Prints one ``PASS`` / ``FAIL`` / ``SKIP`` / ``XFAIL`` line per check and exits
with 1 when a check fails. ``XFAIL`` is a failure the line explains (a QGIS build
without PDAL, a QGIS issue) and does not fail the run. Not a pytest module:

    python3 tests/qgis_headless/make_fixtures.py /tmp/fm
    python3 tests/qgis_headless/run_smoke.py /tmp/fm

Without a folder, the fixtures are written to a temporary one.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from qgis.core import (  # noqa: E402
    Qgis,
    QgsApplication,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsVectorLayer,
)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PACKAGE = 'filter_mate'
# Top-level folders (and files) scripts/prepare_plugin_zip.sh keeps out of the release.
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
FM5_ALGORITHMS = {'cross_filter', 'cross_filter_from_raster', 'cross_filter_from_point_cloud',
                  'cross_filter_from_geometry', 'filter_point_cloud', 'clear_filters', 'apply_favorite',
                  'export_filtered_layers'}
POINT_CLOUD_MIN_VERSION = 32600  # core/domain/point_cloud_support.py

app = QgsApplication([], False)
app.initQgis()
sys.path.append(os.path.join(QgsApplication.pkgDataPath(), 'python', 'plugins'))  # processing

project = QgsProject.instance()
results = []
info = {}


def report(status, name, detail=''):
    results.append((status, name))
    print(f"{status:<5}  {name}  {detail}".rstrip(), flush=True)


def check(name, condition, detail='', expected_failure=''):
    """PASS / FAIL line; a known failure (``expected_failure`` = reason) is XFAIL."""
    if condition:
        report('PASS', name, detail)
    elif expected_failure:
        report('XFAIL', name, f"{detail} | known: {expected_failure}")
    else:
        report('FAIL', name, detail)
    return bool(condition)


def _on_log(message, tag, level):
    if 'Python' in tag:  # plugin import / start errors land here (qgis.utils.showException)
        print(f"   [QGIS log {tag}] {message}", flush=True)


QgsApplication.messageLog().messageReceived.connect(_on_log)


# --- helpers -------------------------------------------------------------------

def names(layer):
    """Sorted ``name`` values of the features the layer shows (iteration: no featureCount)."""
    return sorted(feature['name'] for feature in layer.getFeatures())


def is_nodata(layer, x, y):
    value, ok = layer.dataProvider().sample(QgsPointXY(x, y), 1)
    return not ok or value != value


def read_points(layer):
    """Every point the point cloud provider returns, its subset string applied."""
    from qgis.core import QgsDoubleRange, QgsRectangle
    area = QgsRectangle(layer.extent())
    area.grow(1.0)  # identify leaves out the points on the edge of the area
    return layer.dataProvider().identify(0.0, QgsGeometry.fromRect(area), QgsDoubleRange(), 1000000)


def subset_issue(since):
    """Known QGIS issue from version ``since`` (``QGIS_VERSION_INT // 100``) on, '' before.

    Seen in October 2026 with 3.44.15, 4.2.3 and the 4.3 nightly, never with 3.28 / 3.34:
    identify() of a point cloud ignores the layer's subset string, apparently when the
    background "Generating attributes statistics" task ran around setSubsetString().
    FilterMate's footprints (point_cloud_footprint.py) read the points with identify().
    """
    if Qgis.QGIS_VERSION_INT // 100 < since:
        return ''
    return 'QGIS point cloud identify() ignored the subset string (statistics task / block cache issue)'


def same_path(a, b):
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def enum_value(owner, enum_name, member):
    """Enum member, scoped (PyQt6 / recent QGIS) or not (older PyQt5 bindings)."""
    scoped = getattr(owner, enum_name, None)
    if scoped is not None and hasattr(scoped, member):
        return getattr(scoped, member)
    return getattr(owner, member)


def wait_for_index(layer, timeout=120.0):
    """Wait for the background indexing (EPT / COPC) of a LAS file opened by the ``pdal`` provider."""
    from qgis.core import QgsPointCloudDataProvider
    provider = layer.dataProvider()
    indexed = enum_value(QgsPointCloudDataProvider, 'PointCloudIndexGenerationState', 'Indexed')
    not_indexed = enum_value(QgsPointCloudDataProvider, 'PointCloudIndexGenerationState', 'NotIndexed')
    started = time.monotonic()
    asked = False
    while provider.indexingState() != indexed and time.monotonic() - started < timeout:
        if not asked and provider.indexingState() == not_indexed and time.monotonic() - started > 2:
            provider.generateIndex()  # nothing started it after 2 s: start it
            asked = True
        QgsApplication.processEvents()
        time.sleep(0.05)
    return provider.indexingState() == indexed


def processing_run(algorithm, parameters):
    """``processing.run``; the errors the algorithm reports go to ``info['errors']``."""
    import processing
    from qgis.core import QgsProcessingFeedback

    class Feedback(QgsProcessingFeedback):
        def reportError(self, error, fatalError=False):
            info['errors'].append(error)

    info['errors'] = []
    return processing.run(algorithm, parameters, feedback=Feedback())


# --- checks --------------------------------------------------------------------

def plugin_starts_without_iface():
    """Load the plugin like qgis_process: metadata scan, package import, classFactory(None), initProcessing()."""
    import qgis.utils
    from processing.core.Processing import Processing
    Processing.initialize()
    qgis.utils.plugin_paths.insert(0, info['plugins'])
    qgis.utils.updateAvailablePlugins()
    loaded = qgis.utils.loadPlugin(PACKAGE)
    started = loaded and qgis.utils.startProcessingPlugin(PACKAGE)
    check('plugin imports and starts without iface (qgis_process path)', started and PACKAGE in qgis.utils.plugins,
          f"metadata found={PACKAGE in qgis.utils.available_plugins} loadPlugin={loaded} startProcessingPlugin={started}")
    if not started:
        # Keep testing the engine: register the provider the plugin would have registered.
        from filter_mate.processing.provider import FilterMateProcessingProvider
        info['provider'] = FilterMateProcessingProvider()  # keep a Python reference (see fm5_scenarios.py)
        QgsApplication.processingRegistry().addProvider(info['provider'])
        print("INFO   the plugin did not start: the harness registered its Processing provider, "
              "the next checks test the engine only", flush=True)
    from filter_mate.adapters.qgis.coverage_layers import cache
    cache.set_cache_root(os.path.join(info['work'], 'cache'))


def provider_lists_algorithms():
    provider = QgsApplication.processingRegistry().providerById('filtermate')
    ids = sorted(algorithm.id().split(':', 1)[1] for algorithm in provider.algorithms()) if provider else []
    missing = sorted(FM5_ALGORITHMS - set(ids))
    check('processing provider "filtermate" lists the FilterMate 5 algorithms', provider is not None and not missing,
          f"{len(ids)} algorithms, missing={missing}")
    models = sum(name.endswith('.model3') for name in os.listdir(os.path.join(REPO, 'processing', 'models')))
    check('processing provider loads the shipped models', len(ids) >= len(FM5_ALGORITHMS) + models,
          f"{len(ids)} algorithms for {len(FM5_ALGORITHMS)} FM5 algorithms + {models} models: {ids}")


def load_layers():
    dem = QgsRasterLayer(info['m']['dem'], 'dem', 'gdal')
    zones = QgsVectorLayer(info['m']['zones'] + '|layername=zones', 'zones', 'ogr')
    project.addMapLayers([dem, zones])
    info.update(dem=dem, zones=zones)
    check('fixture DEM and polygons load', dem.isValid() and zones.isValid() and names(zones) == info['m']['zone_names'],
          f"dem={dem.isValid()} zones={names(zones) if zones.isValid() else 'invalid'}")


def raster_to_vector():
    dem, zones, m = info['dem'], info['zones'], info['m']
    low, high = m['east_range']
    result = processing_run('filtermate:cross_filter_from_raster', {
        'SOURCE': dem, 'BAND': 1, 'MODE': 0, 'MINIMUM': low, 'MAXIMUM': high,
        'TARGETS': [zones], 'PREDICATES': [0], 'OPERATOR': 0})
    check('raster source -> vector target (Processing, elevation range)',
          names(zones) == m['zones_in_east_range'] and result['OUTPUT'] == [zones.id()] and dem.providerType() == 'gdal',
          f"kept={names(zones)} subset={zones.subsetString()[:60]!r}")
    processing_run('filtermate:clear_filters', {'LAYERS': [zones]})
    check('clear_filters restores the vector target', zones.subsetString() == '' and names(zones) == m['zone_names'])


def vector_to_raster():
    from filter_mate.adapters.public_api import operations
    dem, zones, m = info['dem'], info['zones'], info['m']
    zones.selectByExpression("\"name\" = 'east_a'")
    result = operations.cross_filter(zones, [dem], predicates=('Intersect',))
    zones.removeSelection()
    xmin, ymin, xmax, ymax = m['zone_boxes']['east_a']
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    inside, _ = dem.dataProvider().sample(QgsPointXY(cx, cy), 1)
    expected = 100 + (cx - m['dem_extent'][0]) // m['pixel']  # make_fixtures: column c holds 100 + c
    check('vector source -> raster target (operations.py): clipped VRT, layer valid',
          result.ok and dem.source().endswith('.vrt') and dem.isValid() and dem.providerType() == 'gdal',
          f"error={result.error!r} failed={result.failed} source=...{dem.source()[-30:]}")
    check('clipped raster: pixel kept inside, NoData outside',
          not is_nodata(dem, cx, cy) and abs(inside - expected) < 1e-6
          and is_nodata(dem, m['dem_extent'][0] + 5, m['dem_extent'][1] + 5) and is_nodata(dem, xmax + 50, cy),
          f"inside={inside} expected={expected}")
    processing_run('filtermate:clear_filters', {'LAYERS': [dem]})
    check('clear_filters restores the raster target', same_path(dem.source(), m['dem']) and dem.providerType() == 'gdal'
          and dem.isValid(), f"source={dem.source()}")


def point_clouds():
    m = info['m']
    if Qgis.QGIS_VERSION_INT < POINT_CLOUD_MIN_VERSION:
        reason = f"QGIS {Qgis.QGIS_VERSION} < 3.26: no point cloud subset string (FilterMate gate)"
        for name in ('point cloud loads', 'point cloud filter by class', 'point cloud subset honored by the provider',
                     'point cloud source -> vector target', 'point cloud selection made right after loading',
                     'geometry -> point cloud target', 'clear_filters restores the point cloud'):
            report('SKIP', name, reason)
        return
    from qgis.core import QgsPointCloudLayer
    from filter_mate.adapters.qgis.coverage_layers import pdal_cli
    zones = info['zones']
    qgis_pdal = 'pdal' in QgsProviderRegistry.instance().providerList()
    info['qgis_pdal'] = qgis_pdal
    if qgis_pdal:
        cloud = QgsPointCloudLayer(m['las'], 'cloud', 'pdal')
        indexed = cloud.isValid() and wait_for_index(cloud)
        loaded_as = f"LAS 1.2 via the pdal provider, indexed={indexed}"
    else:
        cloud = QgsPointCloudLayer(m['ept'], 'cloud', 'ept')
        indexed = True
        loaded_as = "EPT (binary) via the ept provider: this QGIS has no pdal provider, LAS cannot be opened"
    project.addMapLayer(cloud)
    original = (cloud.source(), cloud.providerType())
    info['cloud_loaded_as'] = loaded_as
    check('point cloud loads', cloud.isValid() and indexed and cloud.pointCount() == m['points'],
          f"{loaded_as}; points={cloud.pointCount()}")

    processing_run('filtermate:filter_point_cloud', {'LAYERS': [cloud], 'CLASSES': '2'})
    check('point cloud filter by class (Processing filter_point_cloud): subset accepted',
          cloud.subsetString() == 'Classification = 2', f"subset={cloud.subsetString()!r}")
    points = read_points(cloud)
    classes = sorted({int(point.get('Classification', -1)) for point in points})
    check('point cloud subset honored by the provider (identify)',
          classes == [2] and len(points) == m['points_by_class']['2'],
          f"read={len(points)} classes={classes}", expected_failure=subset_issue(344))
    processing_run('filtermate:clear_filters', {'LAYERS': [cloud]})

    result = processing_run('filtermate:cross_filter_from_point_cloud', {
        'SOURCE': cloud, 'CLASSES': '6', 'TARGETS': [zones], 'PREDICATES': [0], 'OPERATOR': 0})
    check('point cloud source -> vector target (Processing, class 6 footprint)',
          names(zones) == m['zones_with_buildings'] and result['OUTPUT'] == [zones.id()],
          f"kept={names(zones)} source subset={cloud.subsetString()!r}", expected_failure=subset_issue(344))
    processing_run('filtermate:clear_filters', {'LAYERS': [cloud, zones]})
    dock_timing(cloud, zones)

    pdal_exe = pdal_cli.find_pdal()
    pdal_copc = bool(pdal_exe) and 'writers.copc' in subprocess.run(
        [pdal_exe, '--drivers'], capture_output=True, text=True, timeout=120).stdout
    known = '' if pdal_copc or qgis_pdal else (
        f"{'pdal without writers.copc (PDAL < 2.4)' if pdal_exe else 'no pdal executable'} and QGIS built "
        "without PDAL (QgsPointCloudLayerExporter cannot write LAS): no way to clip a point cloud here")
    xmin, ymin, xmax, ymax = m['dem_extent']
    result = processing_run('filtermate:cross_filter_from_geometry', {
        'EXTENT': f"{m['east_x']},{xmax},{ymin},{ymax} [{m['crs']}]", 'TARGETS': [cloud], 'PREDICATES': [0]})
    clipped = (cloud.source(), cloud.providerType()) != original
    info['clip_path'] = ('PDAL CLI (writers.copc)' if clipped and cloud.providerType() == 'copc' else
                         'QgsPointCloudLayerExporter (LAS)' if clipped else 'none (not clipped)')
    check('geometry -> point cloud target (Processing, east half)',
          clipped and cloud.isValid() and cloud.pointCount() == m['points_east'] and not result['LAYERS_FAILED'],
          f"path={info['clip_path']} points={cloud.pointCount()} expected={m['points_east']} "
          f"failed={result['LAYERS_FAILED']} errors={info['errors']}", expected_failure=known)
    processing_run('filtermate:clear_filters', {'LAYERS': [cloud]})
    check('clear_filters restores the point cloud', (cloud.source(), cloud.providerType()) == original
          and cloud.subsetString() == '' and cloud.pointCount() == m['points'], f"source={cloud.source()}")


def dock_timing(cloud, zones, attempts=5):
    """Point cloud source -> vector target as the dock runs it.

    The EXPLORING selection is set on a layer just added to the project (its
    statistics task runs), the event loop turns, then the cross filter reads
    the footprint of the selected points.
    """
    from qgis.core import QgsPointCloudLayer
    from filter_mate.adapters.public_api import operations
    m = info['m']
    wrong = []
    for attempt in range(attempts):
        layer = QgsPointCloudLayer(cloud.source(), f'cloud_dock_{attempt}', cloud.providerType())
        project.addMapLayer(layer)
        # The same selection each time, never made before in the session (class 6 points have Intensity 160).
        layer.setSubsetString('Classification = 6 AND Intensity >= 1')
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            QgsApplication.processEvents()
            time.sleep(0.01)
        result = operations.cross_filter(layer, [zones], predicates=('Intersect',))
        if names(zones) != m['zones_with_buildings']:
            wrong.append(f"{names(zones)} from {result.details.get('source', {}).get('points_read')} points")
        operations.clear_filters([zones, layer])
        project.removeMapLayer(layer.id())
    check('point cloud selection made right after loading -> vector target (dock timing)', not wrong,
          f"{attempts - len(wrong)}/{attempts} right; wrong: {wrong[:1]}", expected_failure=subset_issue(344))


def subset_literals():
    """check_combine_literals.py (subset strings with trap values, combinations, conversions) in its own QGIS.

    GeoPackage and Shapefile only here (no PostGIS in the CI job); each of its
    PASS / FAIL lines becomes a check of this run.
    """
    script = os.path.join(HERE, 'check_combine_literals.py')
    environment = {key: value for key, value in os.environ.items() if key != 'FM_PG_DSN'}
    run = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=600, env=environment)
    lines = [line for line in run.stdout.splitlines() if line.startswith(('PASS', 'FAIL'))]
    for line in lines:
        status, _, rest = line.partition(' ')
        name, _, detail = rest.strip().partition(': ')
        check(f"literals: {name}", status == 'PASS', detail)
    check('literals: scenario script ran to the end', run.returncode in (0, 1) and lines,
          f"exit={run.returncode} {run.stderr.strip()[-300:]}")


def environment():
    from filter_mate.adapters.qgis.coverage_layers import pdal_cli
    exe = pdal_cli.find_pdal()
    version = ''
    if exe:
        version = subprocess.run([exe, '--version'], capture_output=True, text=True).stdout.strip().splitlines()
        version = next((line for line in version if 'pdal' in line.lower()), '')
    print(f"INFO   python {sys.version.split()[0]}, QGIS {Qgis.QGIS_VERSION}, "
          f"pdal provider in QGIS: {info.get('qgis_pdal', 'pdal' in QgsProviderRegistry.instance().providerList())}",
          flush=True)
    print(f"INFO   pdal on PATH: {shutil.which('pdal') or 'no'}; plugin pdal_cli.find_pdal(): {exe or 'none'} {version}",
          flush=True)
    print(f"INFO   point cloud: {info.get('cloud_loaded_as', 'not tested')}; "
          f"target clip path: {info.get('clip_path', 'not tested')}", flush=True)


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else None
    info['work'] = tempfile.mkdtemp(prefix='fm_smoke_')
    sys.path.insert(0, HERE)
    import make_fixtures
    manifest_path = os.path.join(folder or '', 'manifest.json')
    if folder and os.path.exists(manifest_path):
        with open(manifest_path, encoding='utf-8') as stream:
            info['m'] = json.load(stream)
    else:
        info['m'] = make_fixtures.make_all(folder or os.path.join(info['work'], 'fixtures'))
    started = time.perf_counter()
    info['plugins'] = os.path.join(info['work'], 'plugins')
    shutil.copytree(REPO, os.path.join(info['plugins'], PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, info['plugins'])
    print(f"INFO   QGIS {Qgis.QGIS_VERSION}, python {sys.version.split()[0]}, plugin copied to {info['plugins']} "
          f"in {time.perf_counter() - started:.1f}s", flush=True)

    for step in (plugin_starts_without_iface, provider_lists_algorithms, load_layers, raster_to_vector,
                 vector_to_raster, point_clouds, subset_literals, environment):
        if (step is not plugin_starts_without_iface
                and QgsApplication.processingRegistry().providerById('filtermate') is None):
            report('SKIP', step.__name__, 'no FilterMate Processing provider')
            continue
        print(f"--- {step.__name__}", flush=True)
        step_started = time.perf_counter()
        try:
            step()
        except Exception as exc:
            traceback.print_exc()
            report('FAIL', f"{step.__name__} raised", f"{type(exc).__name__}: {exc}")
        print(f"       {time.perf_counter() - step_started:.1f}s", flush=True)

    counts = {status: sum(1 for s, _ in results if s == status) for status in ('PASS', 'FAIL', 'SKIP', 'XFAIL')}
    print(f"\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped, {counts['XFAIL']} known "
          f"failures in {time.perf_counter() - started:.1f}s (QGIS {Qgis.QGIS_VERSION})", flush=True)
    for status, name in results:
        if status == 'FAIL':
            print(f"FAILED: {name}")
    shutil.rmtree(info['work'], ignore_errors=True)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if counts['FAIL'] else 0)  # skip the QGIS teardown, it may crash on exit


if __name__ == '__main__':
    main()

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
    QgsCoordinateReferenceSystem,
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


def raster_alpha_band():
    """An RGBA orthophoto is RGB: its alpha band is told by the colour interpretation, not the name (2026-10-17)."""
    from osgeo import gdal
    from filter_mate.adapters.qgis.coverage_layers.raster_adapter import read_raster_summary
    from filter_mate.ui.widgets.coverage_panels.raster_exploring_panel import (
        default_band_layout, layouts_for, spectral_presets_for,
    )
    path = os.path.join(info['work'], 'ortho_rgba.tif')
    dataset = gdal.GetDriverByName('GTiff').Create(path, 8, 8, 4, gdal.GDT_Byte, ['PHOTOMETRIC=RGB', 'ALPHA=YES'])
    dataset.SetGeoTransform((600000, 0.25, 0, 6200002, 0, -0.25))
    for band, colour in enumerate((gdal.GCI_RedBand, gdal.GCI_GreenBand, gdal.GCI_BlueBand, gdal.GCI_AlphaBand), 1):
        dataset.GetRasterBand(band).SetColorInterpretation(colour)
        dataset.GetRasterBand(band).Fill(255 if band == 4 else 40 * band)
    dataset = None
    layer = QgsRasterLayer(path, 'ortho_rgba', 'gdal')
    summary = read_raster_summary(layer)
    band_names = [band.name for band in summary.bands]
    alpha = {band.number for band in summary.bands if band.is_alpha}
    check('RGBA orthophoto: the alpha band is flagged by its colour interpretation',
          layer.isValid() and alpha == {4}, f"bands={band_names} alpha={sorted(alpha)}")
    layout = default_band_layout(band_names, alpha)
    check('RGBA orthophoto: RGB layout, no infrared preset',
          layout == 'rgb' and 'rgbn' not in layouts_for(band_names, alpha)
          and not any(key.startswith('ndvi') for key in spectral_presets_for(layout)),
          f"layout={layout} (by name only: {default_band_layout(band_names)})")


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


def _fake_dock(session):
    """A QWidget standing in for the dock: the controllers are QObjects and need a real parent."""
    import types
    from qgis.PyQt.QtWidgets import QWidget
    dock = QWidget()
    dock.tr = lambda text: text
    dock._app_ref = types.SimpleNamespace(session_id=session)
    info.setdefault('docks', []).append(dock)  # keep a Python reference
    return dock


def user_data_safety():
    """The cleanup and export features never touch a user's own data (audit 2026-10).

    A GeoPackage with the user layers ``routes``, ``mvt_reseau`` and ``MVoies``
    gets one real FilterMate temp table, made by ``manage_spatialite_subset``.
    The global cleanup (confirmation bypassed) must drop that table only, and
    the file must stay a valid GeoPackage; an export onto the file is refused.
    """
    import hashlib
    import sqlite3
    from osgeo import ogr
    from filter_mate.adapters.backends.spatialite import filter_executor
    from filter_mate.core.export.layer_exporter import LayerExporter
    from filter_mate.infrastructure.logging.redaction import mask_sensitive_text
    from filter_mate.ui.controllers.backend_controller import BackendController

    session = 'ab12cd34'
    work = os.path.join(info['work'], 'safety')
    os.makedirs(work, exist_ok=True)
    gpkg = os.path.join(work, 'reseau.gpkg')
    datasource = ogr.GetDriverByName('GPKG').CreateDataSource(gpkg)
    for layer_name in ('routes', 'mvt_reseau', 'MVoies'):
        table = datasource.CreateLayer(layer_name, geom_type=ogr.wkbPoint)
        feature = ogr.Feature(table.GetLayerDefn())
        feature.SetGeometry(ogr.CreateGeometryFromWkt('POINT (1 2)'))
        table.CreateFeature(feature)
    datasource = None

    def sha():
        with open(gpkg, 'rb') as stream:
            return hashlib.sha256(stream.read()).hexdigest()

    def tables():
        connection = sqlite3.connect(gpkg)
        try:
            return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            connection.close()

    # --- a real temp table, created by the plugin's code ------------------------
    routes = QgsVectorLayer(f'{gpkg}|layername=routes', 'routes', 'ogr')
    project.addMapLayer(routes)
    queued = []
    ok = filter_executor.manage_spatialite_subset(
        layer=routes, sql_subset_string='SELECT fid, geom FROM routes', primary_key_name='fid',
        geom_key_name='geom', name='routes_1', session_id=session, project_uuid=None,
        queue_subset_func=lambda layer, subset: queued.append(subset),
        get_spatialite_datasource_func=lambda layer: (gpkg, 'routes', 4326, True))
    temp = f'fm_temp_{session}_routes_1'
    check('safety: manage_spatialite_subset creates the table its subset reads',
          ok and temp in tables() and queued == [f'"fid" IN (SELECT "fid" FROM {temp})'],
          f"ok={ok} tables={sorted(tables())} subset={queued}")

    # --- global cleanup ---------------------------------------------------------
    dock = _fake_dock(session)
    controller = BackendController(dock)
    controller.get_pg_session_context = lambda: (None, session, 'filter_mate_temp', None)
    candidates = controller.collect_global_cleanup_candidates()
    check('safety: the cleanup candidates are the FilterMate table only',
          candidates['spatialite'] == {gpkg: [temp]}, f"candidates={candidates['spatialite']}")

    asked = []
    controller._confirm_global_cleanup = lambda found: asked.append(found) or False
    before = sha()
    controller.run_global_cleanup_with_confirmation()
    check('safety: answering "No" to the confirmation drops nothing',
          bool(asked) and sha() == before and temp in tables())

    controller._confirm_global_cleanup = lambda found: True
    controller.run_global_cleanup_with_confirmation()
    left = tables()
    check('safety: global cleanup dropped the FilterMate table and the user layers stayed',
          temp not in left and {'routes', 'mvt_reseau', 'MVoies'} <= left, f"tables={sorted(left)}")
    connection = sqlite3.connect(gpkg)
    contents = sorted(row[0] for row in connection.execute('SELECT table_name FROM gpkg_contents'))
    integrity = connection.execute('PRAGMA integrity_check').fetchone()[0]
    connection.close()
    opened = ogr.Open(gpkg)
    counts = {opened.GetLayerByIndex(i).GetName(): opened.GetLayerByIndex(i).GetFeatureCount()
              for i in range(opened.GetLayerCount())}
    opened = None
    check('safety: the GeoPackage is still valid (gpkg_contents, integrity, ogr)',
          contents == ['MVoies', 'mvt_reseau', 'routes'] and integrity == 'ok'
          and counts == {'routes': 1, 'mvt_reseau': 1, 'MVoies': 1},
          f"gpkg_contents={contents} integrity={integrity} ogr={counts}")
    ogrinfo = shutil.which('ogrinfo')
    if ogrinfo:
        out = subprocess.run([ogrinfo, '-so', '-al', gpkg], capture_output=True, text=True)
        check('safety: ogrinfo reads the three layers', out.returncode == 0
              and all(f'Layer name: {n}' in out.stdout for n in ('routes', 'mvt_reseau', 'MVoies')),
              out.stderr.strip()[:120])

    # --- export onto a source file ------------------------------------------------
    exporter = LayerExporter(project)
    before = sha()
    single = exporter.export_single_layer('routes', gpkg, None, 'GPKG', None, False)
    package = exporter.export_to_gpkg(['routes'], gpkg, False)
    reprojected = exporter.export_to_gpkg(['routes'], gpkg, False, target_crs=QgsCoordinateReferenceSystem('EPSG:2154'))
    check('safety: export onto the GeoPackage a layer is read from is refused (single, package, reprojection)',
          not single.success and not package.success and not reprojected.success
          and sha() == before and 'routes' in single.error_message, f"{single.error_message!r}")
    other = os.path.join(work, 'copy.gpkg')
    copied = exporter.export_single_layer('routes', other, None, 'GPKG', None, False)
    check('safety: export to another file still works', copied.success and os.path.exists(other),
          f"{copied.error_message!r}")

    # --- passwords ------------------------------------------------------------------
    pg = QgsVectorLayer("dbname='gis' host=db.invalid port=5432 user='bob' password='s3cret' sslmode=disable "
                        "key='id' table=\"public\".\"roads\" (geom)", 'roads', 'postgres')
    masked = mask_sensitive_text(pg.source())
    check('safety: the source of a PostgreSQL layer is logged without its password',
          's3cret' not in masked and 'password=' in masked, masked[:90])
    project.removeMapLayer(routes.id())


def user_data_safety_postgresql():
    """PostGIS (``FM_PG_DSN``): the global cleanup drops FilterMate's objects only, without CASCADE."""
    dsn = os.environ.get('FM_PG_DSN')
    if not dsn:
        report('SKIP', 'safety: PostgreSQL cleanup', 'FM_PG_DSN not set')
        return
    import psycopg2
    from filter_mate.ui.controllers.backend_controller import BackendController

    session = 'ab12cd34'
    setup = psycopg2.connect(dsn)
    setup.autocommit = True
    cur = setup.cursor()
    for statement in (
            'DROP SCHEMA IF EXISTS filtermate_temp CASCADE', 'DROP SCHEMA IF EXISTS ref CASCADE',
            'DROP TABLE IF EXISTS public.filtermate_catalog, public.fm_buf_users, public."FM_TEMP_user"',
            'DROP MATERIALIZED VIEW IF EXISTS public.fm_mv_report',
            'CREATE SCHEMA filtermate_temp', 'CREATE SCHEMA ref',
            'CREATE TABLE ref.communes (id int primary key, name text)',
            "INSERT INTO ref.communes VALUES (1, 'a')",
            # FilterMate's own objects
            f'CREATE MATERIALIZED VIEW filtermate_temp.fm_temp_mv_{session}_abc AS SELECT id FROM ref.communes',
            f'CREATE MATERIALIZED VIEW filtermate_temp.fm_temp_mv_{session}_abc_dump AS '
            f'SELECT id FROM filtermate_temp.fm_temp_mv_{session}_abc',
            'CREATE TABLE ref.fm_temp_buf_communes_0123abcd AS SELECT id FROM ref.communes',
            'CREATE TABLE filtermate_temp.fm_temp_src_sel_0123abcd AS SELECT id FROM ref.communes',
            # the user's: the old patterns (filtermate\\_%, fm\\_buf\\_%, fm\\_mv\\_%) matched them
            'CREATE TABLE public.filtermate_catalog (id int)', 'CREATE TABLE public.fm_buf_users (id int)',
            'CREATE MATERIALIZED VIEW public.fm_mv_report AS SELECT id FROM ref.communes',
            'CREATE TABLE public."FM_TEMP_user" (id int)'):
        cur.execute(statement)
    dock = _fake_dock(session)
    controller = BackendController(dock)
    controller.get_pg_session_context = lambda: (None, session, 'filtermate_temp', psycopg2.connect(dsn))
    candidates = controller.collect_global_cleanup_candidates()['postgresql']
    expected = sorted([('matview', 'filtermate_temp', f'fm_temp_mv_{session}_abc'),
                       ('matview', 'filtermate_temp', f'fm_temp_mv_{session}_abc_dump'),
                       ('table', 'ref', 'fm_temp_buf_communes_0123abcd'),
                       ('table', 'filtermate_temp', 'fm_temp_src_sel_0123abcd')])
    check('safety: PostgreSQL candidates are FilterMate objects only', sorted(candidates) == expected,
          f"candidates={sorted(candidates)}")
    dropped = controller.cleanup_temp_tables_global()
    cur.execute("SELECT schemaname || '.' || tablename FROM pg_tables "
                "WHERE schemaname IN ('public', 'ref', 'filtermate_temp')")
    tables = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT schemaname || '.' || matviewname FROM pg_matviews "
                "WHERE schemaname IN ('public', 'ref', 'filtermate_temp')")
    views = {row[0] for row in cur.fetchall()}
    check('safety: PostgreSQL global cleanup dropped FilterMate objects (dependent view first), user objects stayed',
          dropped == 4 and tables >= {'ref.communes', 'public.filtermate_catalog', 'public.fm_buf_users',
                                      'public.FM_TEMP_user'}
          and views == {'public.fm_mv_report'} and not [t for t in tables if 'fm_temp' in t],
          f"dropped={dropped} tables={sorted(tables)} views={sorted(views)}")
    cur.execute("SELECT count(*) FROM pg_namespace WHERE nspname = 'filtermate_temp'")
    check('safety: the emptied FilterMate schema is dropped, the user schema is not',
          cur.fetchone()[0] == 0 and 'ref.communes' in tables)
    # schema cleanup refuses a schema that holds a user table
    cur.execute('CREATE SCHEMA filter_mate_temp')
    cur.execute('CREATE TABLE filter_mate_temp.mine (id int)')
    cur.execute(f'CREATE MATERIALIZED VIEW filter_mate_temp.fm_temp_mv_{session}_x AS SELECT 1 AS id')
    controller.get_pg_session_context = lambda: (None, session, 'filter_mate_temp', psycopg2.connect(dsn))
    refused = controller.cleanup_postgresql_schema_if_empty(force=True)
    cur.execute("SELECT count(*) FROM pg_tables WHERE schemaname = 'filter_mate_temp' AND tablename = 'mine'")
    check('safety: dropping the schema is refused while it holds a user table',
          refused is False and cur.fetchone()[0] == 1)
    controller.get_pg_session_context = lambda: (None, session, 'public', psycopg2.connect(dsn))
    check('safety: the public schema can never be dropped',
          controller.cleanup_postgresql_schema_if_empty(force=True) is False)
    # a schema with FilterMate objects only is emptied then dropped
    cur.execute('DROP TABLE filter_mate_temp.mine')
    controller.get_pg_session_context = lambda: (None, session, 'filter_mate_temp', psycopg2.connect(dsn))
    emptied = controller.cleanup_postgresql_schema_if_empty(force=True)
    cur.execute("SELECT count(*) FROM pg_namespace WHERE nspname = 'filter_mate_temp'")
    check('safety: a schema holding FilterMate objects only is emptied then dropped',
          emptied is True and cur.fetchone()[0] == 0)
    for statement in ('DROP SCHEMA IF EXISTS filter_mate_temp CASCADE', 'DROP SCHEMA IF EXISTS ref CASCADE',
                      'DROP TABLE IF EXISTS public.filtermate_catalog, public.fm_buf_users, public."FM_TEMP_user"',
                      'DROP MATERIALIZED VIEW IF EXISTS public.fm_mv_report'):
        cur.execute(statement)
    setup.close()


def user_data_safety_native_spatialite():
    """A native Spatialite database (the only kind where fm_temp_* is made in practice).

    Layers use the 'spatialite' provider: the cleanup must scan their database, drop the
    undeclared temp table of the all-sessions cleanup, spare the table a layer is filtered
    through, and (session cleanup) drop a declared table with its own R-tree index and
    metadata rows only.
    """
    import sqlite3
    from filter_mate.adapters.backends.spatialite import filter_executor
    from filter_mate.infrastructure.database.sql_utils import create_temp_spatialite_table
    from filter_mate.ui.controllers.backend_controller import BackendController

    session = 'cd34ab12'
    work = os.path.join(info['work'], 'native')
    os.makedirs(work, exist_ok=True)
    db = os.path.join(work, 'native.sqlite')
    conn = sqlite3.connect(db)
    conn.enable_load_extension(True)
    try:
        conn.load_extension('mod_spatialite')
    except sqlite3.Error:
        try:
            conn.load_extension('mod_spatialite.so')
        except sqlite3.Error:
            conn.close()
            report('SKIP', 'safety: native Spatialite', 'mod_spatialite is not available')
            return
    conn.execute('SELECT InitSpatialMetadata(1)')
    conn.execute('CREATE TABLE roads (pk INTEGER PRIMARY KEY)')
    conn.execute("SELECT AddGeometryColumn('roads', 'geom', 2154, 'LINESTRING', 'XY')")
    conn.execute("INSERT INTO roads (pk, geom) VALUES (1, GeomFromText('LINESTRING(0 0, 1 1)', 2154))")
    conn.execute("INSERT INTO roads (pk, geom) VALUES (2, GeomFromText('LINESTRING(5 5, 6 6)', 2154))")
    conn.execute('CREATE TABLE mv_20231231_bati (pk INTEGER)')
    conn.commit()
    conn.close()

    roads = QgsVectorLayer(f"dbname='{db}' table=\"roads\" (geom)", 'roads', 'spatialite')
    project.addMapLayer(roads)
    check('safety: the native Spatialite layer is valid', roads.isValid(), roads.source()[:80])

    queued = []
    ok = filter_executor.manage_spatialite_subset(
        layer=roads, sql_subset_string='SELECT pk, geom FROM roads WHERE pk = 1', primary_key_name='pk',
        geom_key_name='geom', name='roads_1', session_id=session, project_uuid=None,
        queue_subset_func=lambda layer, subset: queued.append(subset),
        get_spatialite_datasource_func=lambda layer: (db, 'roads', 2154, True))
    in_use = f'fm_temp_{session}_roads_1'
    check('safety: native: the temp table is made and its subset filters the layer',
          ok and queued == [f'"pk" IN (SELECT "pk" FROM {in_use})'] and roads.setSubsetString(queued[0])
          and [f['pk'] for f in roads.getFeatures()] == [1], f"ok={ok} subset={queued}")
    # a second table, declared in geometry_columns (R-tree + metadata) like a registered one, plus a sibling
    # whose name extends it: dropping one must leave the other's index alone
    for name in (f'fm_temp_{session}_declared', f'fm_temp_{session}_declared_more'):
        create_temp_spatialite_table(db, name, 'SELECT pk, geom FROM roads', 'geom', 2154, register_geometry=True)

    dock = _fake_dock(session)
    controller = BackendController(dock)
    controller.get_pg_session_context = lambda: (None, session, 'filter_mate_temp', None)
    check('safety: native: the database of a spatialite-provider layer is scanned',
          db in controller._spatialite_project_databases(), str(controller._spatialite_project_databases()))
    candidates = controller.collect_global_cleanup_candidates()['spatialite']
    check('safety: native: the table in use and the declared ones are not candidates, mv_20231231_bati neither',
          candidates == {}, f"candidates={candidates}")

    # session cleanup: declared tables go, the one a layer is filtered through stays
    count = controller._cleanup_spatialite_project_tables()
    conn = sqlite3.connect(db)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.enable_load_extension(True)
    conn.load_extension('mod_spatialite')
    declared = {row[0] for row in conn.execute('SELECT f_table_name FROM geometry_columns')}
    stats = {row[0] for row in conn.execute('SELECT f_table_name FROM geometry_columns_statistics')}
    integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
    conn.close()
    check('safety: native: the session cleanup drops the declared tables with index and metadata, keeps the table in use',
          count == 2 and in_use in tables and {'roads', 'mv_20231231_bati'} <= tables
          and not [t for t in tables if 'declared' in t] and declared == {'roads'}
          and not [s for s in stats if 'declared' in s] and integrity == 'ok'
          and [f['pk'] for f in roads.getFeatures()] == [1],
          f"count={count} tables={sorted(t for t in tables if 'fm_temp' in t or 'idx_' in t)} "
          f"declared={sorted(declared)} stats={sorted(stats)}")

    roads.setSubsetString('')
    candidates = controller.collect_global_cleanup_candidates()['spatialite']
    check('safety: native: once the filter is cleared the table is a candidate of the global cleanup',
          candidates == {db: [in_use]}, f"candidates={candidates}")
    dropped = controller.cleanup_temp_tables_global()
    conn = sqlite3.connect(db)
    left = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    check('safety: native: the global cleanup then drops it and nothing else',
          dropped == 1 and in_use not in left and {'roads', 'mv_20231231_bati'} <= left, f"dropped={dropped}")
    project.removeMapLayer(roads.id())


def user_data_safety_two_databases():
    """Two PostGIS databases in one project: each task connects to the database of its own layer.

    ACTIVE_POSTGRESQL used to be one shared connection (the first PostgreSQL layer's): every
    task filtered through it. Now DatasourceManager opens nothing, and a task opens its own
    connection from its source layer.
    """
    dsn = os.environ.get('FM_PG_DSN')
    if not dsn:
        report('SKIP', 'safety: two PostgreSQL databases', 'FM_PG_DSN not set')
        return
    from unittest.mock import MagicMock
    import psycopg2
    from qgis.PyQt.QtCore import QObject
    from filter_mate.core.services.datasource_manager import DatasourceManager
    from filter_mate.core.tasks.filter_task import FilterEngineTask

    params = dict(item.split('=', 1) for item in dsn.split())
    first_db, second_db = params['dbname'], 'fm_second_db'
    admin = psycopg2.connect(dsn)
    admin.autocommit = True
    admin.cursor().execute(f'DROP DATABASE IF EXISTS {second_db}')
    admin.cursor().execute(f'CREATE DATABASE {second_db}')
    rows = {first_db: 3, second_db: 5}
    for dbname, count in rows.items():
        connection = psycopg2.connect(dsn.replace(f"dbname={first_db}", f"dbname={dbname}"))
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute('CREATE EXTENSION IF NOT EXISTS postgis')
        cursor.execute('DROP TABLE IF EXISTS public.fm_two_roads')
        cursor.execute('CREATE TABLE public.fm_two_roads (id serial PRIMARY KEY, geom geometry(Point, 4326))')
        cursor.execute(f"INSERT INTO public.fm_two_roads (geom) SELECT ST_SetSRID(ST_MakePoint(g, g), 4326) "
                       f"FROM generate_series(1, {count}) g")
        connection.close()

    def layer_on(dbname):
        uri = (f"dbname='{dbname}' host={params['host']} port={params['port']} user='{params['user']}' "
               f"password='{params['password']}' sslmode=disable key='id' srid=4326 type=Point "
               f"table=\"public\".\"fm_two_roads\" (geom)")
        layer = QgsVectorLayer(uri, f'roads_{dbname}', 'postgres')
        project.addMapLayer(layer)
        return layer

    layers = {dbname: layer_on(dbname) for dbname in rows}
    check('safety: two databases: both PostGIS layers are valid', all(l.isValid() for l in layers.values()),
          str({k: l.isValid() for k, l in layers.items()}))

    # the datasource manager tracks both databases and opens no connection
    config = {"CURRENT_PROJECT": {"OPTIONS": {"ACTIVE_POSTGRESQL": "", "IS_ACTIVE_POSTGRESQL": False}}}
    manager = DatasourceManager(
        get_project_callback=lambda: project, get_iface_callback=MagicMock(),
        get_config_data_callback=lambda: config, set_config_data_callback=MagicMock(),
        get_db_file_path_callback=lambda: '', get_temp_schema_callback=lambda: 'filter_mate_temp',
        show_error_callback=MagicMock(), show_warning_callback=MagicMock())
    for layer in layers.values():
        manager.update_datasource_for_layer({'layer_provider_type': 'postgresql', 'layer_name': layer.name(),
                                             'layer_id': layer.id()})
    manager.update_datasource()
    tracked = manager.project_datasources['postgresql']
    options = config["CURRENT_PROJECT"]["OPTIONS"]
    check('safety: two databases: one entry per database, no connection, nothing secret, ACTIVE_POSTGRESQL empty',
          len(tracked) == 2 and set(tracked.values()) == {None} and 'password' not in repr(tracked)
          and options["ACTIVE_POSTGRESQL"] == ""
          and options["IS_ACTIVE_POSTGRESQL"] is True, f"tracked={list(tracked)} options={options}")

    # each task connects to the database of its own source layer
    seen = {}
    for dbname, layer in layers.items():
        task = QObject()  # attribute holder; the method only needs these attributes
        task.task_parameters = {"task": {"options": {"ACTIVE_POSTGRESQL": MagicMock(closed=False)}}}
        task.source_layer, task.active_connections, task.PROJECT = layer, [], project
        connection = FilterEngineTask._get_valid_postgresql_connection(task)
        cursor = connection.cursor()
        cursor.execute('SELECT current_database(), (SELECT count(*) FROM public.fm_two_roads)')
        seen[dbname] = cursor.fetchone()
        again = FilterEngineTask._get_valid_postgresql_connection(task)
        seen[dbname] += (again is connection,)
        for opened in task.active_connections:
            opened.close()
    check('safety: two databases: each task uses a connection to its own layer\'s database (not a shared one)',
          seen == {first_db: (first_db, 3, True), second_db: (second_db, 5, True)}, str(seen))

    for layer in layers.values():
        project.removeMapLayer(layer.id())
    admin.cursor().execute(f'DROP DATABASE IF EXISTS {second_db} WITH (FORCE)')
    connection = psycopg2.connect(dsn)
    connection.autocommit = True
    connection.cursor().execute('DROP TABLE IF EXISTS public.fm_two_roads')
    connection.close()
    admin.close()


def subset_literals():
    """check_combine_literals.py (subset strings with trap values, combinations, conversions) in its own QGIS.

    GeoPackage and Shapefile only here (no PostGIS in the CI job); each of its
    PASS / FAIL lines becomes a check of this run.
    """
    script = os.path.join(HERE, 'check_combine_literals.py')
    environment = {key: value for key, value in os.environ.items() if key != 'FM_PG_DSN'}
    try:
        run = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=600, env=environment)
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout.decode(errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        check('literals: scenario script ran to the end', False, f"timeout after 600 s: {output.strip()[-300:]}")
        return
    lines = [line for line in run.stdout.splitlines() if line.startswith(('PASS', 'FAIL'))]
    for line in lines:
        status, _, rest = line.partition(' ')
        name, _, detail = rest.strip().partition(': ')
        check(f"literals: {name}", status == 'PASS', detail)
    check('literals: scenario script ran to the end', run.returncode in (0, 1) and lines,
          f"exit={run.returncode} {run.stderr.strip()[-300:]}")


# --- remote sources, stable keys, key literals (2026-10-17) ----------------------

COMMUNES = (  # name, code (text), population (int): two communes share population 800
    ("L'Isle-Jourdain", '32160', 9000),
    ("L'Isle-Jourdain", '86112', 1200),
    ('Auch', '32013', 22000),
    ("L'Abergement-Clémenciat", '01001', 800),
    ('Ambérieu-en-Bugey', '01004', 800),
    ('Code sans zéro', '1001', 50),
    ('Saint\\Backslash', '99001', None),  # a backslash in a text key, a NULL population
)
BACKSLASH_NAME = 'Saint\\Backslash'
# Unreachable on purpose (connection refused at once): only the provider key is read.
OFFLINE_SERVICES = (
    ('WFS', "typename='communes' url='http://127.0.0.1:9/wfs' version='2.0.0'"),
    ('OAPIF', "typename='communes' url='http://127.0.0.1:9/ogcapi'"),
    ('arcgisfeatureserver', "url='http://127.0.0.1:9/arcgis/rest/services/x/FeatureServer/0'"),
)


def _old_heuristic_key(layer):
    """The key layer_management_task chose before 2026-10-17 (no declared key)."""
    fields = list(layer.fields())
    for field in fields:
        if field.name().lower() in ('id', 'fid', 'pk', 'gid', 'ogc_fid', 'objectid', 'oid', 'rowid'):
            return field.name()
    for field in fields:
        if 'uuid' in field.name().lower() or 'guid' in field.name().lower():
            return field.name()
    for field in fields:
        if field.isNumeric() and any(p in field.name().lower() for p in ('_id', 'id_', 'identifier')):
            return field.name()
    for field in fields:
        if field.isNumeric():
            return field.name()
    return fields[0].name() if fields else None


def _communes_layers():
    """The communes as memory, Shapefile, GeoJSON and GeoPackage layers (no declared key but the GPKG fid)."""
    from qgis.core import QgsFeature, QgsVectorFileWriter
    memory = QgsVectorLayer('Point?crs=EPSG:2154&field=nom:string(60)&field=code:string(5)&field=population:integer',
                            'communes_memory', 'memory')
    features = []
    for index, (name, code, population) in enumerate(COMMUNES):
        feature = QgsFeature(memory.fields())
        feature.setAttributes([name, code, population])
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500000 + 1000 * index, 6300000)))
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    layers = {'memory': memory}
    for driver, extension in (('ESRI Shapefile', 'shp'), ('GeoJSON', 'geojson'), ('GPKG', 'gpkg')):
        path = os.path.join(info['work'], f'communes.{extension}')
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = driver
        options.fileEncoding = 'UTF-8'
        result = QgsVectorFileWriter.writeAsVectorFormatV3(memory, path, project.transformContext(), options)
        if result[0] != QgsVectorFileWriter.WriterError.NoError:
            report('FAIL', f'write communes as {driver}', str(result))
            continue
        layers[extension] = QgsVectorLayer(path, f'communes_{extension}', 'ogr')
    return layers


def remote_sources():
    from filter_mate.adapters.backends.ogr.expression_builder import OGRExpressionBuilder
    from filter_mate.adapters.qgis.source_capability_probe import capability_for_layer
    from filter_mate.core.domain.source_capability import Locality, classify
    from qgis.core import QgsFeature
    from filter_mate.core.domain.stable_key import FEATURE_ID_KEY
    from filter_mate.core.filter.pk_formatter import format_key_literal, is_null_value
    from filter_mate.core.tasks.layer_management_task import LayersManagementEngineTask

    for key, uri in OFFLINE_SERVICES:
        layer = QgsVectorLayer(uri, f'offline_{key}', key)
        capability = capability_for_layer(layer)
        check(f'{key} layer: providerType() and source capability', layer.providerType() == key
              and capability.locality is Locality.REMOTE_SERVICE and not capability.counts_cheaply,
              f"providerType()={layer.providerType()!r} classify={capability.locality.value}/"
              f"{capability.server_filter.value} key_list_limit={capability.key_list_limit}")
    check('GDAL TMS raster is a rendered image', not classify(
        'gdal', '<GDAL_WMS><Service name="TMS"><ServerUrl>https://t/${z}/${x}/${y}.png</ServerUrl></Service></GDAL_WMS>',
        True).has_raw_values)

    task = type('KeyTask', (LayersManagementEngineTask,),
                {'__init__': lambda self: None, 'isCanceled': lambda self: False})()
    builder = OGRExpressionBuilder({})
    for kind, layer in _communes_layers().items():
        if not layer.isValid():
            report('FAIL', f'communes {kind} valid')
            continue
        old = _old_heuristic_key(layer) if not list(layer.primaryKeyAttributes()) else 'declared'
        key = task.search_primary_key_from_layer(layer)
        backend_key = builder._get_primary_key(layer)
        expected = 'fid' if kind == 'gpkg' else FEATURE_ID_KEY  # the GeoPackage declares its fid
        check(f'{kind}: key without a unique key field is the feature id, never "population"',
              key[0] == expected and backend_key == expected,
              f"before: {old}; now: registration {key}, OGR backend {backend_key!r}")

        def count(subset):
            layer.setSubsetString('')
            applied = layer.setSubsetString(subset)
            shown = len(list(layer.getFeatures())) if applied else -1
            layer.setSubsetString('')
            return shown

        clause = builder._build_fid_filter_with_values(layer, ["L'Isle-Jourdain"], 'nom')
        before = '"nom" IN (' + repr("L'Isle-Jourdain") + ')'  # repr() of core/filter/expression_builder
        check(f"{kind}: L'Isle-Jourdain key literal applied by setSubsetString", count(clause) == 2,
              f"{clause} -> {count(clause)} feature(s); before {before} -> {count(before)}")
        clause = builder._build_fid_filter_with_values(layer, [BACKSLASH_NAME], 'nom')
        before = '"nom" IN (' + "'" + BACKSLASH_NAME + "')"
        check(f"{kind}: a backslash in a key literal (QGIS expression escape on memory)", count(clause) == 1,
              f"{clause} -> {count(clause)}; before {before} -> {count(before)}")
        clause = builder._build_fid_filter_with_values(layer, ['01001'], 'code')
        before = '"code" IN (01001)'
        check(f"{kind}: text code '01001' stays a text literal", count(clause) == 1,
              f"{clause} -> {count(clause)}; before {before} -> {count(before)}")
        populations = [feature['population'] for feature in layer.getFeatures()]
        nulls = [value for value in populations if is_null_value(value)]
        check(f"{kind}: a NULL attribute is NULL, never 'NULL'", nulls and all(
            format_key_literal(value, True) == 'NULL' for value in nulls),
            f"{[repr(value) for value in nulls]} -> {[format_key_literal(value, True) for value in nulls]}")
        ids = [feature.id() for feature in layer.getFeatures() if feature['code'] in ('01001', '32013')]
        if layer.fields().indexOf(key[0]) < 0:
            clause = builder._build_fid_filter(layer, ids)
        else:
            clause = builder._build_fid_filter_with_values(layer, ids, key[0])
        before = '"population" IN (800, 22000)'
        check(f'{kind}: feature-id key list keeps exactly the selected features', count(clause) == 2,
              f"{clause} -> {count(clause)}; before {before} -> {count(before)}")

    from qgis.core import QgsExpression
    from filter_mate.core.filter.pk_formatter import qgis_string_literal
    samples = ["L'Isle", 'b\\c', 'd\\', 'tab\there', 'line\nbreak', "''"]
    check('QGIS expression literals are QgsExpression.quotedString', all(
        qgis_string_literal(text) == QgsExpression.quotedString(text) for text in samples),
        f"{[(qgis_string_literal(t), QgsExpression.quotedString(t)) for t in samples]}")

    # A unique "id" is the key, a duplicated one is not (proven by reading it, in the task)
    for label, values, expected in (('unique id', [1, 2, 3], 'id'), ('duplicated id', [1, 1, 3], FEATURE_ID_KEY),
                                    ('id with a NULL', [1, None, 3], FEATURE_ID_KEY)):
        layer = QgsVectorLayer('Point?crs=EPSG:2154&field=id:integer&field=population:integer', label, 'memory')
        features = []
        for value in values:
            feature = QgsFeature(layer.fields())
            feature.setAttributes([value, 10])
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
            features.append(feature)
        layer.dataProvider().addFeatures(features)
        key = task.search_primary_key_from_layer(layer)
        check(f'memory layer with a {label}: key {expected}', key[0] == expected, f"{key}")

    # Virtual layer without a uid column: fid / $id lists keep 0 feature, the key list is refused
    memory = _communes_layers()['memory']
    project.addMapLayer(memory)
    virtual = QgsVectorLayer(f'?query=SELECT * FROM "{memory.name()}"', 'communes_virtual', 'virtual')
    key = task.search_primary_key_from_layer(virtual)
    refusal = builder._key_list_refusal(virtual)
    check('virtual layer without uid: no key list (refused with a message)',
          virtual.isValid() and key[0] == FEATURE_ID_KEY and bool(refusal) and 'virtual layer' in refusal,
          f"valid={virtual.isValid()} key={key} refusal={refusal!r}")
    project.removeMapLayer(memory.id())


def compat_checks():
    """Version-dependent API the plugin relies on (audit October 2026): QMetaType, QColor, point cloud exporter."""
    from qgis.core import QgsField
    from qgis.PyQt.QtCore import QMetaType
    from qgis.PyQt.QtGui import QColor
    from filter_mate.adapters.qgis.coverage_layers.point_cloud_footprint import (
        exporter_unavailable_message, point_cloud_exporter_class)

    # Every QMetaType.Type member the plugin compares field types with (layer_adapter, layer_utils, ...).
    used = ('Int', 'UInt', 'LongLong', 'ULongLong', 'Double', 'QString', 'QChar', 'QDate', 'QTime', 'QDateTime',
            'Bool', 'QByteArray')
    missing = [name for name in used if not hasattr(QMetaType.Type, name)]
    check('QMetaType.Type has every member the plugin uses', not missing, f"missing={missing}")
    field = QgsField('population')  # the only QgsField the plugin builds (point_cloud_footprint): no type argument
    check('QgsField(name) builds without a type argument', field.name() == 'population', f"type={field.type()}")

    check('QColor.NameFormat.HexArgb / HexRgb exist (scoped spelling)',
          QColor('#80ff0000').name(QColor.NameFormat.HexArgb).lower() == '#80ff0000'
          and QColor('#ff0000').name(QColor.NameFormat.HexRgb).lower() == '#ff0000')

    exporter = point_cloud_exporter_class()
    has_exporter = hasattr(__import__('qgis.core', fromlist=['x']), 'QgsPointCloudLayerExporter')
    check('point cloud exporter class matches the QGIS build (3.28+)', (exporter is not None) == has_exporter,
          f"QGIS {Qgis.QGIS_VERSION}, exporter={exporter is not None}")
    if exporter is None:
        from filter_mate.adapters.qgis.coverage_layers.exporters import PointCloudExportJob

        class NoLayer:  # never touched: the missing exporter is reported first
            def name(self):
                return 'cloud'

        result = PointCloudExportJob(NoLayer(), os.path.join(info['work'], 'out.laz')).run()
        check('point cloud export without the exporter reports "QGIS 3.28" instead of raising',
              not result.success and 'QGIS 3.28' in result.message and result.message == exporter_unavailable_message(),
              result.message)


def ogr_target_centroids():
    """FilterMate 5: a target chosen 'by its centroids' is tested by its point on surface on the OGR backend too."""
    import json as _json
    from filter_mate.adapters.backends.ogr.expression_builder import OGRExpressionBuilder
    from qgis.core import QgsFeature, QgsGeometry

    target = QgsVectorLayer('Polygon?crs=EPSG:2154', 'centroid_targets', 'memory')
    features = []
    for wkt in ('POLYGON((8 0, 40 0, 40 2, 8 2, 8 0))',   # touches the source, its point on surface is outside
                'POLYGON((2 2, 4 2, 4 4, 2 4, 2 2))'):    # inside the source
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        features.append(feature)
    target.dataProvider().addFeatures(features)
    ids = [feature.id() for feature in target.getFeatures()]
    union = QgsGeometry.fromWkt('POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))')
    builder = OGRExpressionBuilder({})
    full = builder._select_against_union(target, union, target.crs(), ['intersects'])
    centroids = builder._select_against_union(target, union, target.crs(), ['intersects'], True)
    check('OGR target by its full geometry: both polygons intersect', sorted(full) == sorted(ids), str(full))
    check('OGR target by its centroids: only the polygon whose point on surface is inside', centroids == [ids[1]],
          str(centroids))
    params = _json.loads(builder.build_expression({'layer_name': 't'}, {'intersects': True}, None, use_centroids=True))
    check('OGR expression carries the per-target centroid choice', params.get('use_centroids') is True, str(params))


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
                 vector_to_raster, raster_alpha_band, point_clouds, remote_sources, subset_literals,
                 user_data_safety, user_data_safety_postgresql, user_data_safety_native_spatialite,
                 user_data_safety_two_databases, compat_checks, ogr_target_centroids,
                 environment):
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

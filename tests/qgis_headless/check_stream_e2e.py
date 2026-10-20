# -*- coding: utf-8 -*-
"""End to end run of the streaming sources, on real public services, in one QGIS project.

Opt-in: without FM_STREAM_PUBLIC=1 the script prints SKIP and exits 0. With it, a
service that cannot be reached prints ``SKIP <reason>`` (never FAIL). Lines are
``PASS ...`` / ``FAIL ...`` / ``SKIP ...``, then a total; exit code 1 when a FAIL.

    docker run --rm -v "$PWD:/src:ro" -e QT_QPA_PLATFORM=offscreen -e FM_STREAM_PUBLIC=1 \
      qgis/qgis:ltr bash -c 'bash /src/tests/qgis_headless/install_pdal.sh; \
      python3 /src/tests/qgis_headless/check_stream_e2e.py'

(install_pdal.sh is only needed for the remote COPC part; without PDAL that part is SKIP.)

One project around Toulouse: communes (WFS Geoplateforme), ortho (WMTS Geoplateforme),
a DEM (WCS: the Geoplateforme has no WCS endpoint any more, so the MapServer demo WCS of
lot D), the IGN plan (vector tiles) and two local GeoPackage layers (a zone, points).
Then undo / redo, a favorite replayed after clear_filters, and a .qgz round trip. The
remote COPC (Autzen) runs last, through a counting local relay, in a project of its own.

Environment: FM_E2E_ONLY=wfs,wmts,wcs,tiles,project,copc runs only those parts (the
project part needs the layers of the others), FM_E2E_API_TIMEOUT (seconds, default 45)
bounds a public API call that streams an unbounded amount of data, FM_STREAM_METRICS
writes the METRIC lines as JSON.

Local layers are GeoPackages rather than memory layers: a memory layer cannot survive
the .qgz round trip, which is part of the scenario.
"""
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

RESULTS = []
METRICS = []


def check(name, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    RESULTS.append(status)
    print('{} {} {}'.format(status, name, detail).rstrip(), flush=True)
    return bool(condition)


def skip(name, reason):
    RESULTS.append('SKIP')
    print('SKIP {}: {}'.format(name, reason), flush=True)


def metric(**values):
    METRICS.append(values)
    print('METRIC ' + json.dumps(values, default=str), flush=True)


def finish(code=None):
    print('TOTAL {} passed, {} failed, {} skipped'.format(
        RESULTS.count('PASS'), RESULTS.count('FAIL'), RESULTS.count('SKIP')), flush=True)
    if os.environ.get('FM_STREAM_METRICS'):
        Path(os.environ['FM_STREAM_METRICS']).write_text(json.dumps(METRICS, indent=2, default=str))
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code if code is not None else (1 if 'FAIL' in RESULTS else 0))


if os.environ.get('FM_STREAM_PUBLIC') != '1':
    skip('end to end streaming sources', 'set FM_STREAM_PUBLIC=1 (public services, opt-in)')
    finish(0)

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
WORK = Path(tempfile.mkdtemp(prefix='fm_stream_e2e_'))
os.environ['FILTERMATE_LOG_DIR'] = str(WORK / 'logs')

from osgeo import gdal, ogr, osr  # noqa: E402
from qgis.PyQt.QtCore import QSize, QTimer  # noqa: E402
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeature,
    QgsFeatureRequest, QgsFeedback, QgsGeometry, QgsMapRendererSequentialJob, QgsMapSettings,
    QgsNetworkAccessManager, QgsNetworkRequestParameters, QgsPointXY, QgsProject, QgsRasterLayer,
    QgsRectangle, QgsTask, QgsVectorLayer, QgsVectorTileLayer,
)

ROOT = Path(os.environ.get('FM_REPO', Path(__file__).resolve().parents[2]))
ONLY = set(filter(None, os.environ.get('FM_E2E_ONLY', '').split(',')))
API_TIMEOUT = float(os.environ.get('FM_E2E_API_TIMEOUT', '45'))

import faulthandler  # noqa: E402
# A hang (a stuck worker, a deadlocked nested loop) leaves its Python stacks in the log instead of nothing.
faulthandler.dump_traceback_later(int(os.environ.get('FM_E2E_HANG_SECONDS', '1500')), repeat=True)
app = QgsApplication([], False)
app.initQgis()
(WORK / 'plugins').mkdir()
(WORK / 'plugins' / 'filter_mate').symlink_to(ROOT, target_is_directory=True)
sys.path.insert(0, str(WORK / 'plugins'))

from filter_mate.adapters.public_api import operations as ops  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers import cache, favorites_bridge, snapshots  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers import vector_tile_filters as tile_filters  # noqa: E402
from filter_mate.core.domain.layer_kind import LayerKind  # noqa: E402

cache.set_cache_root(str(WORK / 'cache'))
# The dock reads the user's options: raster filtering is on in a session that filters rasters, which is what this
# scenario reproduces (favorites_bridge.capture and the dock-side layer kind both depend on it).
from filter_mate.config.config import ENV_VARS  # noqa: E402
ENV_VARS.setdefault('CONFIG_DATA', {}).setdefault('APP', {}).setdefault('OPTIONS', {}).setdefault('RASTER', {})['enabled'] = True
from filter_mate.adapters.qgis.point_cloud_capability import get_layer_kind  # noqa: E402
gdal.UseExceptions()
gdal.SetConfigOption('GDAL_PAM_ENABLED', 'NO')

REQUESTS = []
QgsNetworkAccessManager.instance().requestAboutToBeCreated[QgsNetworkRequestParameters].connect(
    lambda params: REQUESTS.append(params.request().url().toString()))

WFS_BASE = "url='https://data.geopf.fr/wfs/ows' srsname='EPSG:4326' version='2.0.0'"
ZONE = (1.40, 43.57, 1.47, 43.64)  # around Toulouse, WGS84
PROJECT = QgsProject.instance()
LAYERS = {}


# --- helpers ---------------------------------------------------------------------

def wanted(part):
    return not ONLY or part in ONLY


def wait_for(predicate, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return False


def in_worker(function, timeout=300):
    """Run ``function`` in a QgsTask (remote reads never run on the main thread)."""
    box = {}

    def work(task):
        return function()

    def done(exception, result=None):
        box.update(error=exception, result=result, done=True)

    task = QgsTask.fromFunction('e2e worker', work, on_finished=done)
    app.taskManager().addTask(task)
    if not wait_for(lambda: box.get('done'), timeout):
        task.cancel()
        raise TimeoutError('worker exceeded {} s'.format(timeout))
    if box['error'] is not None:
        raise box['error']
    return box['result']


def http_ok(url, timeout=20):
    try:
        with urlopen(Request(url, headers={'User-Agent': 'filtermate-e2e'}), timeout=timeout) as response:
            return response.read(4096)
    except Exception as exc:
        return exc


def make_gpkg(name, geometry_type, epsg, rows):
    """GeoPackage layer in the temp folder; ``rows`` = [(wkt, {'name': ...})]."""
    path = str(WORK / (name + '.gpkg'))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    dataset = ogr.GetDriverByName('GPKG').CreateDataSource(path)
    layer = dataset.CreateLayer(name, srs, geometry_type)
    layer.CreateField(ogr.FieldDefn('name', ogr.OFTString))
    for wkt, attributes in rows:
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
        for key, value in attributes.items():
            feature.SetField(key, value)
        layer.CreateFeature(feature)
    dataset = None
    result = QgsVectorLayer('{}|layername={}'.format(path, name), name, 'ogr')
    assert result.isValid(), path
    return result


def rect_wkt(x0, y0, x1, y1):
    return 'POLYGON(({0} {1},{2} {1},{2} {3},{0} {3},{0} {1}))'.format(x0, y0, x1, y1)


def names(layer):
    return sorted(feature['name'] for feature in layer.getFeatures())


def report_line(report):
    return 'error={} done={} failed={} skipped={}'.format(report.error, list(report.done.values()),
                                                         report.failed, report.skipped)


def wfs_layer(type_name='commune', title='communes_wfs', bbox_only=False):
    """``bbox_only``: restrictToRequestBBOX, the QGIS WFS option that sends the BBOX (default: whole table)."""
    return QgsVectorLayer("{} typename='ADMINEXPRESS-COG.LATEST:{}'{}".format(
        WFS_BASE, type_name, " restrictToRequestBBOX='1'" if bbox_only else ''), title, 'WFS')


def same_filter(a, b):
    """The server translation wraps the expression in parentheses: compare without them."""
    def bare(text):
        text = (text or '').strip()
        while text.startswith('(') and text.endswith(')') and text.count('(') == text.count(')'):
            text = text[1:-1].strip()
        return text
    return bare(a) == bare(b)


def set_server_filter(layer, expression, tries=3):
    """safe_set_subset_string with retries: a public WFS sometimes exceeds the 30 s server-filter deadline."""
    from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string
    for attempt in range(1, tries + 1):
        if safe_set_subset_string(layer, expression):
            return True
        print('INFO server filter attempt {} refused for {}'.format(attempt, layer.name()), flush=True)
    return False


def clear_all(layers):
    """clear_filters for the public API kinds, the tile service for vector tiles."""
    tiles = [layer for layer in layers if get_layer_kind(layer) is LayerKind.VECTOR_TILE]
    others = [layer for layer in layers if get_layer_kind(layer) not in (LayerKind.VECTOR_TILE, LayerKind.OTHER)]
    report = ops.clear_filters(others)
    for layer in tiles:
        unfilter_tiles(layer)
    for layer in others:
        if layer.providerType().lower() == 'wfs' and layer.subsetString():
            set_server_filter(layer, '')
    return report


def keys_in(subset):
    return set(re.findall(r"'([^']+)'", subset or ''))


def toulouse_polygon():
    """Commune of Toulouse straight from the service (GeoJSON), independent of the plugin."""
    url = ('https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature'
           '&TYPENAMES=ADMINEXPRESS-COG.LATEST:commune&outputFormat=application/json'
           "&cql_filter=" + quote("code_insee='31555'"))
    with urlopen(Request(url, headers={'User-Agent': 'filtermate-e2e'}), timeout=30) as response:
        data = json.load(response)
    return QgsGeometry.fromWkt(ogr.CreateGeometryFromJson(json.dumps(data['features'][0]['geometry'])).ExportToWkt())


# --- local layers ------------------------------------------------------------------

POINTS = {  # name: (lon, lat)
    'capitole': (1.4442, 43.6045), 'matabiau': (1.4540, 43.6112), 'jean_jaures': (1.4490, 43.6060),
    'blagnac': (1.3900, 43.6350), 'colomiers': (1.3340, 43.6110), 'labege': (1.5130, 43.5450),
    'balma': (1.4990, 43.6100), 'tournefeuille': (1.3410, 43.5860),
}


def build_local_layers():
    LAYERS['zone'] = make_gpkg('locale_zone', ogr.wkbPolygon, 4326, [(rect_wkt(*ZONE), {'name': 'zone_toulouse'})])
    LAYERS['points'] = make_gpkg('locale_points', ogr.wkbPoint, 4326, [
        ('POINT({} {})'.format(*xy), {'name': name}) for name, xy in POINTS.items()])
    for layer in (LAYERS['zone'], LAYERS['points']):
        PROJECT.addMapLayer(layer)
    check('local zone and points layers', LAYERS['zone'].featureCount() == 1
          and LAYERS['points'].featureCount() == len(POINTS))


# --- 1. WFS ------------------------------------------------------------------------

def wfs_checks():
    probe = http_ok('https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature'
                    '&TYPENAMES=ADMINEXPRESS-COG.LATEST:commune&COUNT=1&outputFormat=application/json')
    if isinstance(probe, Exception) or b'features' not in probe:
        skip('WFS Geoplateforme', 'service unreachable: {}'.format(probe))
        return
    from qgis.core import QgsCoordinateTransformContext
    from filter_mate.adapters.backends.ogr.expression_builder import OGRExpressionBuilder
    from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string

    target = wfs_layer()
    if not check('WFS communes layer valid', target.isValid(), target.error().message() if not target.isValid() else ''):
        return
    LAYERS['wfs'] = target
    PROJECT.addMapLayer(target)
    settings = {'_processing_settings': {'transform_context': QgsCoordinateTransformContext()}}

    def filter_keys(layer, source):
        """Lot B path: keys the dock would queue for ``layer`` against ``source``."""
        queued = []
        params = dict(settings, _subset_queue_callback=lambda lyr, subset: queued.append(subset))
        builder = OGRExpressionBuilder(task_params=params)
        expression = builder.build_expression(layer_props={}, predicates={'ST_Intersects': True}, source_geom=source)
        success = builder.apply_filter(layer, expression)
        return success, queued, builder

    # a) target, small zone: keys == reference computed on a bounded local copy
    def reference_keys():
        copy = wfs_layer(bbox_only=True)  # separate provider instance: independent bounded read
        zone = next(LAYERS['zone'].getFeatures()).geometry()
        keys = set()
        for feature in copy.getFeatures(QgsFeatureRequest().setFilterRect(zone.boundingBox())):
            if feature.geometry().intersects(zone):
                keys.add(feature['cleabs'])
        return keys

    started = time.perf_counter()
    expected = in_worker(reference_keys)
    ref_seconds = time.perf_counter() - started
    before = len(REQUESTS)
    started = time.perf_counter()
    success, queued, builder = in_worker(lambda: filter_keys(target, LAYERS['zone']))
    seconds = time.perf_counter() - started
    posed = keys_in(queued[0]) if queued else set()
    check('WFS target from local polygon: keys == bounded local reference',
          success and len(queued) == 1 and posed == expected and 0 < len(expected) <= 500,
          'posed={} reference={} requests={} seconds={:.1f} (reference {:.1f}s) warnings={}'.format(
              len(posed), len(expected), len(REQUESTS) - before, seconds, ref_seconds, builder.user_warnings))
    metric(part='wfs_target_keys', keys=len(posed), reference=len(expected), seconds=round(seconds, 2))
    # With retries (the public WFS sometimes exceeds the 30 s deadline); never read the unfiltered service.
    applied = bool(queued) and set_server_filter(target, queued[0])
    served = in_worker(lambda: sorted(f['cleabs'] for f in target.getFeatures())) if applied else []
    check('WFS target: keys applied to the layer, the service returns exactly them',
          applied and set(served) == expected, 'served={}'.format(len(served)))
    target.setSubsetString('')

    # b) more than 500 keys: clear refusal, previous filter kept
    previous = '"code_insee" = \'31555\''
    check('WFS previous filter installed', safe_set_subset_string(target, previous) and same_filter(target.subsetString(), previous),
          target.subsetString()[:120])
    held = target.subsetString()

    def department_layer():
        dep = wfs_layer('departement', 'departement')
        dep.setSubsetString("\"code_insee\" = '31'")
        rows = list(dep.getFeatures(QgsFeatureRequest().setLimit(2)))
        big = QgsVectorLayer('MultiPolygon?crs=EPSG:4326', 'Haute-Garonne', 'memory')
        big.dataProvider().addFeatures(rows)
        big.updateExtents()
        return big, len(rows)

    big, count = in_worker(department_layer)
    LAYERS['_big'] = big  # keep the scratch layer alive
    if count != 1:
        skip('WFS more than 500 keys', 'department geometry unavailable')
    else:
        started = time.perf_counter()
        success, queued, builder = in_worker(lambda: filter_keys(target, big))
        outcome = getattr(builder, 'remote_materialization_outcome', None)
        text = ' '.join(builder.user_warnings or []) + ' ' + str(getattr(builder, 'last_error', ''))
        check('WFS more than 500 keys: refused with a clear message, nothing queued',
              not success and not queued and '500' in text,
              'reason={} fetched={} keys={} warnings={} seconds={:.1f}'.format(
                  getattr(outcome, 'reason', None), getattr(outcome, 'fetched', None),
                  len(outcome.keys) if outcome else None, builder.user_warnings, time.perf_counter() - started))
        check('WFS more than 500 keys: previous filter kept', target.subsetString() == held, target.subsetString()[:120])
    target.setSubsetString('')

    # c) the public API on a WFS target: must give the same keys (lot B must be reachable from there)
    feedback = QgsFeedback()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(feedback.cancel)
    timer.start(int(API_TIMEOUT * 1000))
    before = len(REQUESTS)
    started = time.perf_counter()
    report = ops.cross_filter(LAYERS['zone'], [target], selected_only=False, feedback=feedback)
    seconds = time.perf_counter() - started
    timer.stop()
    unbounded = [u for u in REQUESTS[before:] if 'GetFeature' in u and 'BBOX' not in u.upper() and 'FILTER' not in u.upper()]
    check('API cross_filter local polygon -> WFS target applies the bounded keys',
          target.id() in report.done and keys_in(target.subsetString()) == expected,
          '{} subset={} seconds={:.1f} requests={} GetFeature-without-bbox={}'.format(
              report_line(report), target.subsetString()[:100], seconds, len(REQUESTS) - before, len(unbounded)))
    metric(part='wfs_api_target', seconds=round(seconds, 1), getfeature_without_bbox=len(unbounded))
    target.setSubsetString('')
    ops.clear_filters([target])

    # d) WFS source: attribute filter translated to an OGC filter, then used as source
    toulouse = in_worker(toulouse_polygon)
    expression = '"code_insee" = \'31555\''
    before = len(REQUESTS)
    ok = set_server_filter(target, expression)
    check('WFS attribute filter accepted (server translation)', ok and same_filter(target.subsetString(), expression),
          target.subsetString())
    served = in_worker(lambda: [f['code_insee'] for f in target.getFeatures()])
    sent = [u for u in REQUESTS[before:] if 'GetFeature' in u and '31555' in u]
    check('WFS attribute filter reaches the server as an OGC filter, one commune returned',
          served == ['31555'] and bool(sent), 'served={} requests_with_filter={}'.format(served, len(sent)))
    points = LAYERS['points']
    expected_points = sorted(name for name, (x, y) in POINTS.items()
                             if toulouse.intersects(QgsGeometry.fromPointXY(QgsPointXY(x, y))))
    started = time.perf_counter()
    report = ops.cross_filter(target, [points], selected_only=False)
    seconds = time.perf_counter() - started
    kept = names(points)
    check('WFS source -> local points: exactly the points inside the commune',
          points.id() in report.done and kept == expected_points and 0 < len(kept) < len(POINTS),
          '{} kept={} expected={} seconds={:.1f}'.format(report_line(report), kept, expected_points, seconds))
    ops.clear_filters([points, target])
    check('WFS and points back to no filter', target.subsetString() == '' and points.subsetString() == ''
          and names(points) == sorted(POINTS), 'wfs={!r} points={!r}'.format(target.subsetString(), points.subsetString()))


# --- 2. WMTS -----------------------------------------------------------------------

def wmts_checks():
    from filter_mate.adapters.qgis.coverage_layers import raster_adapter as adapter
    from filter_mate.adapters.qgis.coverage_layers.rendered_raster import RenderedRasterTask
    from filter_mate.adapters.qgis.coverage_layers.source_jobs import RasterSourceJob
    from filter_mate.core.domain.cross_filter import CrossFilterRequest, TargetSpec
    from filter_mate.core.services.cross_filter_service import CrossFilterService
    from filter_mate.ui.widgets.coverage_panels.raster_exploring_panel import RasterExploringPanel
    from qgis.core import QgsSingleBandColorDataRenderer
    import numpy as np

    endpoint = 'https://data.geopf.fr/wmts'
    extent = QgsRectangle(160000, 5400000, 160200, 5400200)  # EPSG:3857, Toulouse
    edge = 20037508.342789244
    span = 2 * edge / (2 ** 18)
    probe_url = endpoint + '?' + urlencode(dict(
        SERVICE='WMTS', VERSION='1.0.0', REQUEST='GetTile', LAYER='ORTHOIMAGERY.ORTHOPHOTOS', STYLE='normal',
        FORMAT='image/jpeg', TILEMATRIXSET='PM', TILEMATRIX=18, TILECOL=int(math.floor((160100 + edge) / span)),
        TILEROW=int(math.floor((edge - 5400100) / span))))
    tile = http_ok(probe_url)
    if isinstance(tile, Exception) or not tile.startswith(b'\xff\xd8'):
        skip('WMTS Geoplateforme', 'GetTile unavailable: {}'.format(tile if isinstance(tile, Exception) else tile[:80]))
        return
    capabilities = endpoint + '?SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0'
    uri = ('contextualWMSLegend=0&crs=EPSG:3857&dpiMode=7&format=image/jpeg&layers=ORTHOIMAGERY.ORTHOPHOTOS'
           '&styles=normal&tileMatrixSet=PM&url=' + quote(capabilities, safe=':/?'))
    source = QgsRasterLayer(uri, 'ortho_wmts', 'wms')
    if not check('WMTS ortho layer valid', source.isValid(), source.error().message() if not source.isValid() else ''):
        return
    LAYERS['wmts'] = source
    PROJECT.addMapLayer(source)
    original_source = source.source()
    crs = QgsCoordinateReferenceSystem('EPSG:3857')
    settings = QgsMapSettings()
    settings.setDestinationCrs(crs)
    settings.setExtent(extent)
    settings.setOutputSize(QSize(256, 256))
    captured = {}
    task = RenderedRasterTask(uri, 'wms', QgsSingleBandColorDataRenderer(None, 1), settings, crs,
                              lambda t, ok: captured.update(ok=ok, path=t.path) or True,
                              max_pixels=65536, max_size=256)
    started = time.perf_counter()
    app.taskManager().addTask(task)
    wait_for(lambda: bool(captured), 90)
    if not check('WMTS rendered snapshot', captured.get('ok'), task.error):
        return
    dataset = gdal.Open(task.path)
    colors = np.stack([dataset.GetRasterBand(i).ReadAsArray() for i in (1, 2, 3)], axis=-1)
    quant = colors.astype(np.uint32) // 16
    codes = quant[:, :, 0] * 256 + quant[:, :, 1] * 16 + quant[:, :, 2]
    values, counts = np.unique(codes, return_counts=True)
    hits = np.argwhere(codes == values[np.argmax(counts)])
    row, col = hits[len(hits) // 2]
    picked = {i: int(colors[row, col, i - 1]) for i in (1, 2, 3)}
    panel = RasterExploringPanel()
    panel.set_summary(adapter.read_raster_summary(source))
    panel.set_reference(adapter.raster_reference(source))
    panel.set_rendered_only(True)
    panel._tolerance_spin.setValue(10)
    panel.set_color_sample(picked)
    notice = panel._stream_notice.text()
    check('WMTS panel warns that colours are rendered (colour selection only)',
          'Rendered colors depend on style and scale' in notice and 'Only color selection' in notice, notice[:120])
    selection = panel.selection()
    panel.close()
    if not check('WMTS colour selection built', selection is not None and selection.mode.value == 'expression'
                 and all('@' + str(i) in selection.expression for i in (1, 2, 3)), 'picked={}'.format(picked)):
        return
    geometry_job = RasterSourceJob(source, selection, 65536, filter_source=False, analysis_source=(task.path, 'gdal'))
    box = {}
    request = CrossFilterRequest(source.id(), LayerKind.RASTER)
    worker = QgsTask.fromFunction('e2e color geometry', lambda t: geometry_job.compute(request, t.isCanceled, buffer=False),
                                  on_finished=lambda exc, result=None: box.update(error=exc, geometry=result))
    app.taskManager().addTask(worker)
    wait_for(lambda: 'geometry' in box, 90)
    geometry = box.get('geometry')
    if not check('WMTS colour region is a proper part of the capture',
                 box.get('error') is None and geometry is not None and not geometry.isEmpty()
                 and 0 < geometry.area() < 40000 * 0.95, 'area={}'.format(geometry.area() if geometry else None)):
        return
    inside = geometry.pointOnSurface().asPoint()
    to_4326 = QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem('EPSG:4326'), PROJECT.transformContext())
    inside_ll, outside_ll = to_4326.transform(inside), to_4326.transform(QgsPointXY(160300, 5400300))
    colour_targets = make_gpkg('locale_couleur', ogr.wkbPoint, 4326, [
        ('POINT({} {})'.format(inside_ll.x(), inside_ll.y()), {'name': 'inside_color'}),
        ('POINT({} {})'.format(outside_ll.x(), outside_ll.y()), {'name': 'outside_capture'})])
    PROJECT.addMapLayer(colour_targets)
    LAYERS['colour_targets'] = colour_targets
    service = CrossFilterService()
    final = {}
    cross = CrossFilterRequest(source.id(), LayerKind.RASTER, targets=(TargetSpec(colour_targets.id(), LayerKind.VECTOR),),
                               predicates=('Intersect',))
    job = RasterSourceJob(source, selection, 65536, filter_source=False, analysis_source=(task.path, 'gdal'))
    service.run(cross, job, on_done=lambda completed, ok: final.update(task=completed, ok=ok))
    wait_for(lambda: bool(final), 90)
    done = final.get('task')
    kept = names(colour_targets)
    check('WMTS colour selection -> local points keeps exactly the point in the colour region',
          bool(final.get('ok')) and done is not None and not done.error and kept == ['inside_color'],
          'kept={} error={} seconds={:.1f}'.format(kept, done.error if done else None, time.perf_counter() - started))
    check('WMTS source stays the original service', source.source() == original_source and source.providerType() == 'wms')
    check('WMTS colour filter is undoable and restores both points',
          service.can_undo(source.id()) and colour_targets.id() in service.undo(source.id())
          and names(colour_targets) == ['inside_color', 'outside_capture'])
    job.release()
    geometry_job.release()

    # as a target: refused, nothing changes
    report = ops.cross_filter(LAYERS['zone'], [source], selected_only=False)
    check('WMTS refused as a cross filter target', not report.done and bool(report.error or report.skipped)
          and source.source() == original_source and not snapshots.registry().is_derived(source.id()), report_line(report))


# --- 3. WCS ------------------------------------------------------------------------

def wcs_checks():
    import xml.etree.ElementTree as ET
    from qgis.core import QgsDataSourceUri

    geopf = http_ok('https://data.geopf.fr/wcs/ows?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCapabilities')
    endpoint = 'https://demo.mapserver.org/cgi-bin/wcs'
    used = 'MapServer demo (the Geoplateforme answers no WCS endpoint)'
    if not isinstance(geopf, Exception) and b'Capabilities' in geopf:
        endpoint, used = 'https://data.geopf.fr/wcs/ows', 'Geoplateforme'
    print('INFO WCS service: ' + used, flush=True)

    def meta(request, **extra):
        query = dict(SERVICE='WCS', VERSION='1.0.0', REQUEST=request, **extra)
        with urlopen(endpoint + '?' + urlencode(query), timeout=20) as response:
            return ET.fromstring(response.read(2 * 1024 * 1024))

    try:
        capabilities = meta('GetCapabilities')
        found = [n.text.strip() for n in capabilities.findall('.//{*}CoverageOfferingBrief/{*}name') if n.text]
        coverage = next((n for n in found if 'ndvi' in n.lower()), found[0])
        formats = [n.text.strip() for n in meta('DescribeCoverage', COVERAGE=coverage).findall('.//{*}supportedFormats/{*}formats')
                   if n.text]
    except Exception as exc:
        skip('WCS DEM', 'metadata unavailable: {}: {}'.format(type(exc).__name__, exc))
        return
    uri = QgsDataSourceUri()
    for key, value in [('url', endpoint), ('version', '1.0.0'), ('identifier', coverage)]:
        uri.setParam(key, value)
    fmt = next((f for f in formats if 'tiff' in f.lower()), None)
    if fmt:
        uri.setParam('format', fmt)
    layer = QgsRasterLayer(bytes(uri.encodedUri()).decode('utf-8'), 'mnt_wcs', 'wcs')
    if not layer.isValid():
        skip('WCS DEM', 'provider could not open {}: {}'.format(coverage, layer.error().message()))
        return
    LAYERS['wcs'] = layer
    PROJECT.addMapLayer(layer)
    original = layer.source()
    full = layer.extent()
    centre = full.center()
    dx, dy = full.width() * 0.01, full.height() * 0.01
    zone_rect = QgsRectangle(centre.x() - dx, centre.y() - dy, centre.x() + dx, centre.y() + dy)
    epsg = int(layer.crs().authid().split(':')[1]) if layer.crs().authid().startswith('EPSG:') else 4326
    zone = make_gpkg('locale_zone_mnt', ogr.wkbPolygon, epsg,
                     [(rect_wkt(zone_rect.xMinimum(), zone_rect.yMinimum(), zone_rect.xMaximum(), zone_rect.yMaximum()),
                       {'name': 'zone_mnt'})])
    PROJECT.addMapLayer(zone)
    LAYERS['zone_wcs'] = zone
    print('INFO WCS coverage={} crs={} native={}x{} zone={}'.format(
        coverage, layer.crs().authid(), layer.width(), layer.height(), zone_rect.toString(4)), flush=True)
    started = time.perf_counter()
    before = len(REQUESTS)
    report = ops.cross_filter(zone, [layer], selected_only=False, max_pixels=None)
    seconds = time.perf_counter() - started
    snapshot = snapshots.take_snapshot(layer, LayerKind.RASTER)
    derived_path = layer.source()
    ok = check('WCS target: cross filter done, layer now on a session GeoTIFF',
               layer.id() in report.done and layer.providerType() == 'gdal' and '.tif' in derived_path
               and str(WORK / 'cache') in derived_path, '{} source={}'.format(report_line(report), derived_path[-80:]))  # a clip VRT over the captured GeoTIFF
    check('WCS target: original WCS source preserved in the registry',
          snapshot.derived and snapshot.original_source == original and snapshot.original_provider == 'wcs',
          'derived={} original_provider={}'.format(snapshot.derived, snapshot.original_provider))
    if ok:
        dataset = gdal.Open(derived_path)
        gt = dataset.GetGeoTransform()
        got = QgsRectangle(gt[0], gt[3] + gt[5] * dataset.RasterYSize, gt[0] + gt[1] * dataset.RasterXSize, gt[3])
        pixel = max(abs(gt[1]), abs(gt[5]))
        within = (got.xMinimum() >= zone_rect.xMinimum() - 2 * pixel and got.xMaximum() <= zone_rect.xMaximum() + 2 * pixel
                  and got.yMinimum() >= zone_rect.yMinimum() - 2 * pixel and got.yMaximum() <= zone_rect.yMaximum() + 2 * pixel)
        valid = int((dataset.GetRasterBand(1).GetMaskBand().ReadAsArray() != 0).sum())
        captures = sorted(Path(WORK / 'cache').rglob('FilterMate_target_capture_*.tif'))
        tif_bytes = captures[-1].stat().st_size if captures else -1
        capture = gdal.Open(str(captures[-1])) if captures else None
        mask = dataset.GetRasterBand(1).GetMaskBand().ReadAsArray() != 0
        ys, xs = mask.nonzero()
        kept = QgsRectangle(gt[0] + xs.min() * gt[1], gt[3] + (ys.max() + 1) * gt[5],
                            gt[0] + (xs.max() + 1) * gt[1], gt[3] + ys.min() * gt[5]) if len(xs) else QgsRectangle()
        inside = (len(xs) > 0 and kept.xMinimum() >= zone_rect.xMinimum() - 2 * pixel and kept.xMaximum() <= zone_rect.xMaximum() + 2 * pixel
                  and kept.yMinimum() >= zone_rect.yMinimum() - 2 * pixel and kept.yMaximum() <= zone_rect.yMaximum() + 2 * pixel)
        check('WCS target: GeoTIFF capture in the session cache within the pixel budget, valid pixels only inside the zone',
              inside and tif_bytes > 0 and dataset.RasterXSize * dataset.RasterYSize <= 100_000_000,
              'clip={}x{} bands={} valid={} capture_tif={}x{} tif_bytes={} kept_extent={} seconds={:.1f}'.format(
                  dataset.RasterXSize, dataset.RasterYSize, dataset.RasterCount, int(mask.sum()),
                  capture.RasterXSize if capture else None, capture.RasterYSize if capture else None, tif_bytes,
                  kept.toString(2), seconds))
        zone_cells = (zone_rect.width() / pixel) * (zone_rect.height() / pixel)
        capture_cells = capture.RasterXSize * capture.RasterYSize if capture else 0
        from urllib.parse import parse_qs, urlsplit
        coverage_requests = []
        for url in REQUESTS[before:]:
            query = {k.lower(): v[0] for k, v in parse_qs(urlsplit(url).query).items()}
            if query.get('request', '').lower() == 'getcoverage' and 'bbox' in query:
                box = [float(v) for v in query['bbox'].split(',')[:4]]
                coverage_requests.append((box[2] - box[0], box[3] - box[1], query.get('width'), query.get('height')))
        # tiny whole-extent requests (10 x 10 pixels) are metadata probes; the data requests are the larger ones
        data = [r for r in coverage_requests if int(r[2] or 0) * int(r[3] or 0) > 400]
        widest = max((w for w, h, _, _ in data), default=0)
        check('WCS target: GetCoverage requests are bounded by the zone, not the whole coverage',
              bool(data) and widest <= 4 * zone_rect.width() + 10 * pixel,
              'requests={} data_requests={} widest_data_bbox={:.0f} zone_width={:.0f} coverage_width={:.0f} data_sample={}'.format(
                  len(coverage_requests), len(data), widest, zone_rect.width(), full.width(), data[:3]))
        valid_capture = int((capture.GetRasterBand(1).GetMaskBand().ReadAsArray() != 0).sum()) if capture else -1
        print('INFO WCS capture grid_cells={} valid_cells={} zone_cells={:.0f} tif_bytes={}'.format(
            capture_cells, valid_capture, zone_cells, tif_bytes), flush=True)
        metric(part='wcs_target', cells=capture_cells, bytes=tif_bytes,
               seconds=round(seconds, 2))
        dataset = None
    report = ops.clear_filters([layer])
    snapshot = snapshots.take_snapshot(layer, LayerKind.RASTER)
    check('WCS: clear_filters puts the original WCS source back',
          layer.id() in report.done and layer.providerType() == 'wcs' and layer.source() == original
          and not snapshot.derived, report_line(report))


# --- 4. vector tiles ---------------------------------------------------------------

def render(layer, extent, size=384):
    settings = QgsMapSettings()
    settings.setLayers([layer])
    settings.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
    settings.setExtent(extent)
    settings.setOutputSize(QSize(size, size))
    job = QgsMapRendererSequentialJob(settings)
    job.start()
    wait_for(lambda: not job.isActive(), 90)
    job.waitForFinished()
    return job.renderedImage()


def differing(a, b):
    return sum(1 for y in range(a.height()) for x in range(a.width()) if a.pixel(x, y) != b.pixel(x, y))


def tile_service():
    from filter_mate.core.services.cross_filter_service import CrossFilterService
    if 'tile_service' not in LAYERS:
        LAYERS['tile_service'] = CrossFilterService()
    return LAYERS['tile_service']


def filter_tiles_by_zone(layer):
    """Lot E path (CrossFilterService + FixedGeometrySourceJob), what the dock runs."""
    from filter_mate.adapters.qgis.coverage_layers.source_jobs import FixedGeometrySourceJob
    from filter_mate.core.domain.cross_filter import CrossFilterRequest, TargetSpec
    zone = QgsGeometry.fromWkt(rect_wkt(*ZONE))
    to_tiles = QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'), layer.crs(), PROJECT.transformContext())
    zone.transform(to_tiles)
    request = CrossFilterRequest(LAYERS['zone'].id(), LayerKind.OTHER, (TargetSpec(layer.id(), LayerKind.VECTOR_TILE),),
                                 predicates=('Intersect',), other_layers_combine_operator=None)
    return tile_service().run(request, FixedGeometrySourceJob(layer, zone.asWkt()), synchronous=True)


def unfilter_tiles(layer):
    return tile_service().unfilter(layer.id(), [layer.id()], {layer.id(): LayerKind.VECTOR_TILE}, project=PROJECT)


def tiles_checks():
    style_url = 'https://data.geopf.fr/annexes/ressources/vectorTiles/styles/PLAN.IGN/standard.json'
    tile_url = 'https://data.geopf.fr/tms/1.0.0/PLAN.IGN/14/{}/{}.pbf'.format(
        int((1.44 + 180) / 360 * 16384), int((1 - math.asinh(math.tan(math.radians(43.6))) / math.pi) / 2 * 16384))
    try:
        with urlopen(style_url, timeout=30) as response:
            style = json.load(response)
        with urlopen(tile_url, timeout=30) as response:
            raw = response.read()
    except Exception as exc:
        skip('IGN vector tiles', 'service unreachable: {}'.format(type(exc).__name__))
        return
    from qgis.core import QgsMapBoxGlStyleConverter
    converter = QgsMapBoxGlStyleConverter()
    converter.convert(style)
    renderer = converter.renderer()
    if not check('IGN tile and style available', bool(raw) and renderer is not None):
        return
    layer = QgsVectorTileLayer('type=xyz&url=https://data.geopf.fr/tms/1.0.0/PLAN.IGN/{z}/{x}/{y}.pbf&zmin=0&zmax=18',
                               'plan_ign_tuiles')
    layer.setRenderer(renderer.clone())
    if converter.labeling() is not None:
        layer.setLabeling(converter.labeling().clone())
    LAYERS['tiles'] = layer
    PROJECT.addMapLayer(layer)
    original = tile_filters.style_xml(layer)
    zone_3857 = QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'), QgsCoordinateReferenceSystem('EPSG:3857'),
                                       PROJECT.transformContext()).transformBoundingBox(QgsRectangle(*ZONE))
    wide = QgsRectangle(zone_3857)
    wide.scale(2.5)
    full = render(layer, wide)
    blank_task = tile_filters.apply_filter(layer, 'FALSE')
    blank = render(layer, wide)
    snapshots.restore_snapshot(layer, snapshots.base_snapshot(blank_task))
    check('tiles: probe filter removed, original style back', tile_filters.style_xml(layer) == original)

    # a) the public API: a vector tile layer is a documented target (lot E)
    report = ops.cross_filter(LAYERS['zone'], [layer], selected_only=False)
    api_ok = layer.id() in report.done
    check('API cross_filter local polygon -> vector tile target', api_ok, report_line(report))
    if api_ok:
        ops.clear_filters([layer])

    # b) the CrossFilterService path of the dock
    started = time.perf_counter()
    task = filter_tiles_by_zone(layer)
    seconds = time.perf_counter() - started
    outcomes = [(o.success, o.message) for o in task.outcomes]
    styles = layer.renderer().styles()
    with_filter = sum(1 for s in styles if 'intersects' in s.filterExpression())
    check('tiles target (service): display filter laid in the style rules',
          bool(task.outcomes) and task.outcomes[0].success and with_filter > 0,
          'outcomes={} rules_with_intersects={}/{} seconds={:.1f}'.format(outcomes, with_filter, len(styles), seconds))
    filtered = render(layer, wide)
    kept, everything = differing(filtered, blank), differing(full, blank)
    check('tiles target: filtered render keeps part of the plan (more than blank, less than unfiltered)',
          0 < kept < everything, 'pixels differing from blank: filtered={} unfiltered={}'.format(kept, everything))
    check('tiles target: style differs while filtered', tile_filters.style_xml(layer) != original)
    metric(part='tiles_target', rules=len(styles), rules_filtered=with_filter, pixels_filtered=kept, pixels_unfiltered=everything)
    restored = unfilter_tiles(layer)
    check('tiles: unfilter restores the exact original style', layer.id() in restored and tile_filters.style_xml(layer) == original)
    check('tiles: render after unfilter equals the original render', differing(render(layer, wide), full) == 0)
    if api_ok is False:
        # leave the scenario in a usable state for the project part
        pass


# --- 5. project: undo / redo, favorite, .qgz ----------------------------------------

def layer_state(layer, strict=True):
    kind = get_layer_kind(layer)  # dock-side kind (ops.layer_kind gives the same for these layers)
    if kind is LayerKind.VECTOR_TILE:
        return ('tile', hashlib.sha1(tile_filters.style_xml(layer).encode()).hexdigest())
    if kind is LayerKind.RASTER:
        snapshot = snapshots.take_snapshot(layer, kind)
        extent = layer.extent()
        return ('raster', layer.providerType(), snapshot.derived, snapshot.base_source,
                layer.source() if strict else '',
                tuple(round(v, 6) for v in (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())),
                layer.width() if snapshot.derived else None, layer.height() if snapshot.derived else None)
    if kind is LayerKind.VECTOR:
        return ('vector', layer.subsetString(), layer.source() if strict else '')
    return ('other',)


def project_state(strict=True):
    return {layer.name(): layer_state(layer, strict) for layer in PROJECT.mapLayers().values()}


def diff(a, b):
    return {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}


def project_checks():
    missing = [key for key in ('wfs', 'wmts', 'wcs', 'tiles') if key not in LAYERS]
    if missing:
        skip('project undo / redo / favorite / .qgz', 'layers missing (SKIP or failed earlier): {}'.format(missing))
        return
    from filter_mate.core.domain.favorites_manager import FilterFavorite
    from filter_mate.core.services.cross_filter_service import replay_project_filters
    from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string

    zone, points, wfs, tiles, wcs, zone_wcs = (LAYERS[k] for k in ('zone', 'points', 'wfs', 'tiles', 'wcs', 'zone_wcs'))
    everything = [layer for layer in PROJECT.mapLayers().values() if get_layer_kind(layer) is not LayerKind.OTHER]
    clear_all(everything)
    clean = project_state()
    clean_relaxed = project_state(strict=False)
    service = ops._api_service()

    # Undo / redo, one operation at a time (the tiles go through their own service, as in the dock)
    s0 = project_state()
    report_a = ops.cross_filter(zone, [points], selected_only=False)
    s1 = project_state()
    task_t = filter_tiles_by_zone(tiles)
    s2 = project_state()
    report_b = ops.cross_filter(zone_wcs, [wcs], selected_only=False)
    s3 = project_state()
    check('project: three operations applied (points, tiles, DEM)',
          points.id() in report_a.done and bool(task_t.outcomes) and task_t.outcomes[0].success and wcs.id() in report_b.done
          and len({str(x) for x in (s0, s1, s2, s3)}) == 4,
          '{} / {} / tiles={} changed: s1={} s2={} s3={}'.format(report_line(report_a), report_line(report_b),
                                                              [(o.success, o.message) for o in task_t.outcomes],
                                                              list(diff(s0, s1)), list(diff(s1, s2)), list(diff(s2, s3))))
    undone = service.undo(zone_wcs.id())
    now = project_state()
    check('project: undo of the DEM operation restores the exact previous state', wcs.id() in undone and now == s2, str(diff(now, s2)))
    undone = tile_service().undo(zone.id())
    now = project_state()
    check('project: undo of the tiles operation restores the exact previous state (style XML)',
          tiles.id() in undone and now == s1, str(diff(now, s1)))
    undone = service.undo(zone.id())
    now = project_state()
    check('project: undo of the points operation restores the exact initial state', points.id() in undone and now == s0,
          str(diff(now, s0)))
    redone = service.redo(zone.id())
    now = project_state()
    check('project: redo replays the points filter exactly', points.id() in redone and now == s1, str(diff(now, s1)))
    redone = tile_service().redo(zone.id())
    now = project_state()
    check('project: redo replays the tile style exactly', tiles.id() in redone and now == s2, str(diff(now, s2)))
    redone = service.redo(zone_wcs.id())
    now = project_state()
    check('project: redo replays the DEM exactly (same derived source)', wcs.id() in redone and now == s3, str(diff(now, s3)))

    # server attribute filter on the WFS layer, then the favorite
    expression = '"code_insee" = \'31555\''
    check('project: WFS attribute filter set', set_server_filter(wfs, expression) and same_filter(wfs.subsetString(), expression))
    full = project_state(strict=False)
    cover = favorites_bridge.capture(PROJECT)
    favorite = FilterFavorite(
        name='e2e toulouse', layer_name=wfs.name(), layer_id=wfs.id(), expression=wfs.subsetString(),
        remote_layers={points.name(): {'expression': points.subsetString(), 'layer_id': points.id(),
                                       'display_name': points.name()}},
        spatial_config={favorites_bridge.COVERAGE_KEY: cover})
    PROJECT.writeEntry('FilterMate', 'favorites_backup', json.dumps({'favorites': [favorite.to_dict()]}))
    check('project: favorite captured the coverage layers (DEM, tiles)',
          {e['kind'] for e in cover} >= {'raster', 'vector_tile'}, str(sorted(e['kind'] for e in cover)))
    clear_all(everything)
    now = project_state(strict=False)
    check('project: clear_filters gives back the clean state', diff(now, clean_relaxed) == {}, str(diff(now, clean_relaxed)))
    started = time.perf_counter()
    report = ops.apply_favorite('e2e toulouse')
    again = project_state(strict=False)
    tile_name, dem_name = tiles.name(), wcs.name()
    drift = diff(again, full)
    others = {k: v for k, v in drift.items() if k not in (tile_name, dem_name)}
    check('project: favorite replayed after clear_filters rebuilds the WFS filter and the points filter',
          not report.error and not report.failed and not others,
          '{} diff={} seconds={:.1f}'.format(report_line(report), others, time.perf_counter() - started))
    dem_back = dem_name not in drift
    check('project: the favorite rebuilds the derived DEM (the report claims it: {})'.format(wcs.id() in report.done),
          dem_back, 'report_done_dem={} drift={}'.format(wcs.id() in report.done, drift.get(dem_name)))
    tile_back = tile_name not in drift
    check('project: the same favorite restores the tile style through the public API', tile_back,
          'report={} tiles_diff={}'.format(report_line(report), tile_name in drift))
    # keep the scenario going with the dock-side / API paths that do work
    if not tile_back:
        favorites_bridge.apply([e for e in cover if e['kind'] == 'vector_tile'], service=tile_service(), project=PROJECT)
        check('project: tile favorite entry applied by favorites_bridge directly',
              tile_name not in diff(project_state(strict=False), full))
    if not dem_back:
        redo_dem = ops.cross_filter(zone_wcs, [wcs], selected_only=False)
        check('project: DEM filtered again through cross_filter to continue the scenario',
              wcs.id() in redo_dem.done and dem_name not in diff(project_state(strict=False), full), report_line(redo_dem))

    # .qgz round trip
    expected = project_state(strict=False)
    expected_points = names(points)
    path = str(WORK / 'e2e.qgz')
    PROJECT.setFileName(path)
    check('project: saved as .qgz', PROJECT.write() and os.path.getsize(path) > 0, path)
    ids = {layer.name(): layer.id() for layer in PROJECT.mapLayers().values()}
    snapshots.registry().restore_all(PROJECT)  # what unloading does: the file holds original sources
    PROJECT.clear()
    check('project: cleared', not PROJECT.mapLayers())
    check('project: reopened', PROJECT.read(path) and set(PROJECT.mapLayers()) == set(ids.values()))
    snapshots.registry().install(PROJECT)
    queued = replay_project_filters(service=ops._service(), synchronous=False)
    wait_for(lambda: not ops._service().replaying and not app.taskManager().activeTasks(), 180)
    check('project: stored clips queued for replay (DEM)', queued >= 1, 'queued={}'.format(queued))
    reloaded = project_state(strict=False)
    check('project: filters, derived sources and tile style are back as before', diff(reloaded, expected) == {},
          str(diff(reloaded, expected)))
    for name in ('locale_points',):
        layer = PROJECT.mapLayersByName(name)[0]
        check('project: reloaded points filter keeps the same features', names(layer) == expected_points, str(names(layer)))
    wcs_layer = PROJECT.mapLayersByName('mnt_wcs')[0]
    check('project: reloaded DEM is on a session GeoTIFF with the WCS original kept',
          wcs_layer.providerType() == 'gdal' and snapshots.take_snapshot(wcs_layer, LayerKind.RASTER).original_provider == 'wcs')
    clear_all([layer for layer in PROJECT.mapLayers().values() if get_layer_kind(layer) is not LayerKind.OTHER])
    check('project: clear_filters after reopening gives the clean state',
          diff(project_state(strict=False), clean_relaxed) == {}, str(diff(project_state(strict=False), clean_relaxed)))
    PROJECT.clear()
    LAYERS.clear()


# --- 6. remote COPC ------------------------------------------------------------------

class Relay(BaseHTTPRequestHandler):
    """Streams a public file with Range support and counts the body bytes sent."""
    upstream = ''
    sent = 0
    requests = 0
    lock = threading.Lock()

    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self.forward(False)

    def do_GET(self):
        self.forward(True)

    def forward(self, body):
        request = Request(type(self).upstream, method='GET' if body else 'HEAD')
        if self.headers.get('Range'):
            request.add_header('Range', self.headers['Range'])
        try:
            with urlopen(request, timeout=60) as response:
                self.send_response(response.status)
                for key in ('Content-Length', 'Content-Range', 'Accept-Ranges', 'Content-Type'):
                    if response.headers.get(key):
                        self.send_header(key, response.headers[key])
                self.end_headers()
                with type(self).lock:
                    type(self).requests += 1
                while body:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    with type(self).lock:
                        type(self).sent += len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            try:
                self.send_error(502)
            except Exception:
                pass


def copc_checks():
    from filter_mate.adapters.qgis.coverage_layers import pdal_cli
    from filter_mate.adapters.qgis.coverage_layers.point_cloud_footprint import open_point_cloud
    url = 'https://s3.amazonaws.com/hobu-lidar/autzen-classified.copc.laz'
    try:
        with urlopen(Request(url, headers={'Range': 'bytes=0-1023'}), timeout=30) as response:
            head = response.read(1024)
            total = int(response.headers.get('Content-Range', '/0').rsplit('/', 1)[1])
    except Exception as exc:
        skip('remote COPC (Autzen)', 'service unreachable: {}'.format(type(exc).__name__))
        return
    if not pdal_cli.supports_copc():
        skip('remote COPC (Autzen)', pdal_cli.copc_unavailable_reason())
        return
    Relay.upstream = url
    server = ThreadingHTTPServer(('127.0.0.1', 0), Relay)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    relay = 'http://127.0.0.1:{}/autzen-classified.copc.laz'.format(server.server_port)
    try:
        Relay.sent = 0
        cloud = open_point_cloud(relay, 'autzen_copc', 'copc')
        if not check('remote COPC opens through the relay', cloud is not None and cloud.isValid(),
                     'file_bytes={}'.format(total)):
            return
        PROJECT.addMapLayer(cloud)
        opened_bytes = Relay.sent
        crs = cloud.crs()
        # a drawn zone of 100 x 100 US survey feet inside the extent (EPSG:2992)
        zone = QgsGeometry.fromRect(QgsRectangle(636000, 849000, 636100, 849100))
        extent = cloud.extent()
        if not extent.contains(zone.boundingBox()):
            zone = QgsGeometry.fromRect(QgsRectangle(extent.center().x() - 50, extent.center().y() - 50,
                                                     extent.center().x() + 50, extent.center().y() + 50))
        full_points = cloud.pointCount()
        Relay.sent = 0
        started = time.perf_counter()
        report = ops.cross_filter_by_geometry(zone, crs, [cloud])
        seconds = time.perf_counter() - started
        snapshot = snapshots.take_snapshot(cloud, LayerKind.POINT_CLOUD)
        used = Relay.sent
        budget = min(total * 0.5, 40 * 1024 * 1024)
        check('remote COPC: zone cut applied, cloud now on a local derived COPC',
              cloud.id() in report.done and snapshot.derived and cloud.source() != relay
              and str(WORK / 'cache') in cloud.source(), '{} source={}'.format(report_line(report), cloud.source()[-70:]))
        check('remote COPC: bounded read ({} of {} bytes)'.format(used, total), 0 < used <= budget,
              'bytes_open={} bytes_cut={} file={} share={:.1%} seconds={:.1f}'.format(
                  opened_bytes, used, total, used / max(total, 1), seconds))
        points = cloud.pointCount()
        check('remote COPC: derived cloud holds points and is smaller than the original', points > 0
              and points < full_points, 'points={} full={}'.format(points, full_points))
        metric(part='copc_zone', bytes=used, file_bytes=total, seconds=round(seconds, 1), points=points)
        check('remote COPC: original source preserved for Unfilter', snapshot.original_source == relay)
        ops.clear_filters([cloud])
        check('remote COPC: clear_filters restores the remote source', cloud.source() == relay)
    finally:
        server.shutdown()
        server.server_close()
        PROJECT.clear()


def main():
    print('INFO QGIS ' + Qgis.QGIS_VERSION, flush=True)
    build_local_layers()
    for part, function in (('wfs', wfs_checks), ('wmts', wmts_checks), ('wcs', wcs_checks), ('tiles', tiles_checks),
                           ('project', project_checks), ('copc', copc_checks)):
        if not wanted(part):
            continue
        started = time.perf_counter()
        try:
            function()
        except Exception:
            traceback.print_exc()
            check('{} part finished without exception'.format(part), False, traceback.format_exc().splitlines()[-1])
        print('INFO part {} took {:.1f}s'.format(part, time.perf_counter() - started), flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    check('unhandled exception', False)
finally:
    try:
        snapshots.registry().restore_all(PROJECT)
        snapshots.registry().uninstall()
        app.taskManager().cancelAll()
    except Exception:
        pass
    finish()

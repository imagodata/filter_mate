# -*- coding: utf-8 -*-
"""Real QGIS streaming raster regression and reproducible HTTP byte measurements.

Run in qgis/qgis:ltr and qgis/qgis:stable (no external network required)::

    docker run --rm --network none -v "$PWD:/src:ro" \
      -e QT_QPA_PLATFORM=offscreen -e PYTHONDONTWRITEBYTECODE=1 \
      qgis/qgis:ltr python3 /src/tests/qgis_headless/check_stream_raster.py

FM_REPO selects a read-only baseline checkout. FM_STREAM_BASELINE=1 measures
old behavior without enforcing the new asynchronous contract. Add
FM_STREAM_ASSERT_ASYNC=1 to demonstrate the regression fails on main. METRIC lines are
JSON: HTTP response body bytes (not TCP/header bytes), requests and wall time.
Each phase uses a new URL to avoid GDAL's global curl cache; opening the layer
is measured separately from panel population. The server adds 10 ms per body
response to make synchronous network stalls observable without the Internet.
Public services are SKIP by default. FM_STREAM_PUBLIC=1 enables the actual
Geoplateforme ortho WMTS -> RGB panel -> RasterSourceJob -> vector filter.
Set FM_PUBLIC_COG to a public HTTPS COG for optional GDAL-accounted network
measurements; FM_PUBLIC_ONLY=1 runs just that experiment (omit --network none).
This exercises the real controller with a recording panel, not the full dock.
"""
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

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

from osgeo import gdal, osr  # noqa: E402
import numpy as np  # noqa: E402
from qgis.PyQt.QtCore import QSize, QTimer  # noqa: E402
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsMapRendererParallelJob, QgsMapSettings,
    QgsRasterLayer, QgsRectangle, QgsTask,
)

REPO = Path(os.environ.get('FM_REPO', Path(__file__).resolve().parents[2]))
BASELINE = os.environ.get('FM_STREAM_BASELINE') == '1'
MAIN_THREAD = threading.get_ident()
RESULTS = []


def check(name, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    RESULTS.append(status)
    print('{} {} {}'.format(status, name, detail), flush=True)


class RangeServer(ThreadingHTTPServer):
    """Serve one COG with strict range support and locked response accounting."""

    daemon_threads = True

    def __init__(self, data):
        self.data = data
        self.lock = threading.Lock()
        self.transfers = []
        super().__init__(('127.0.0.1', 0), RangeHandler)

    def snapshot(self):
        with self.lock:
            return len(self.transfers), sum(item[1] for item in self.transfers)


class RangeHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self.respond(False)

    def do_GET(self):
        self.respond(True)

    def respond(self, body):
        # Reject GDAL sidecar / directory probes instead of serving TIFF bytes.
        if not re.fullmatch(r'/[a-z0-9_-]+\.tif', self.path):
            self.send_error(404)
            return
        size = len(self.server.data)
        value = self.headers.get('Range', '')
        match = re.fullmatch(r'bytes=(\d+)-(\d*)', value)
        if value and not match:
            self.send_error(416)
            return
        start = int(match[1]) if match else 0
        end = min(int(match[2]) if match and match[2] else size - 1, size - 1)
        if start > end:
            self.send_error(416)
            return
        self.send_response(206 if match else 200)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Type', 'image/tiff')
        self.send_header('Content-Length', str(end - start + 1))
        if match:
            self.send_header('Content-Range', 'bytes {}-{}/{}'.format(start, end, size))
        self.end_headers()
        if body:
            time.sleep(0.01)
            payload = self.server.data[start:end + 1]
            # Snapshot cannot race the completion of a response body.
            with self.server.lock:
                try:
                    self.wfile.write(payload)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
                self.server.transfers.append((self.path, len(payload)))


def measure(server, phase, operation):
    before_requests, before_bytes = server.snapshot()
    start = time.perf_counter()
    result = operation()
    elapsed = time.perf_counter() - start
    requests, sent = server.snapshot()
    print('METRIC ' + json.dumps(dict(
        phase=phase, seconds=round(elapsed, 6), requests=requests - before_requests,
        bytes=sent - before_bytes, qgis=Qgis.QGIS_VERSION,
        baseline=BASELINE, repo=str(REPO))), flush=True)
    return result


def wait_for(app, predicate, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.002)
    return False


class RecordingPanel:
    """Panel boundary recording delivery while the real controller runs."""

    def __init__(self, derivative):
        self.derivative = derivative
        self.histograms = []
        self.spans = {}
        self.summary = None

    def set_summary(self, summary):
        self.summary = summary

    def set_reference(self, reference):
        self.reference = reference

    def set_rendered_only(self, value):
        self.rendered_only = value

    def set_stream_notice(self, notice):
        self.notice = notice

    def set_band_spans(self, spans):
        self.spans = spans

    def current_band(self):
        return 1

    def display_bands(self):
        return None

    def current_derivative(self):
        return self.derivative

    def set_histogram(self, band, counts, low, high, derivative):
        self.histograms.append((band, list(counts), low, high, derivative,
                                threading.get_ident()))

    def set_kept_ratio(self, value):
        self.ratio = value

    def preview_enabled(self):
        return False

    def selection(self):
        return None


def make_cog(folder):
    """Uncompressed gradient: predictable values / area and meaningful byte counts."""
    source = str(folder / 'source.tif')
    target = str(folder / 'gradient.tif')
    dataset = gdal.GetDriverByName('GTiff').Create(source, 2048, 2048, 1, gdal.GDT_UInt16)
    dataset.SetGeoTransform((0, 1, 0, 2048, 0, -1))
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(3857)
    dataset.SetProjection(crs.ExportToWkt())
    dataset.GetRasterBand(1).WriteArray(np.ascontiguousarray(np.broadcast_to(
        np.arange(2048, dtype=np.uint16) // 8, (2048, 2048))))
    dataset = None
    converted = gdal.Translate(target, source, format='COG', creationOptions=[
        'COMPRESS=NONE', 'BLOCKSIZE=256', 'RESAMPLING=NEAREST'])
    if converted is None:
        raise RuntimeError('GDAL COG creation failed')
    converted = None
    converted = gdal.Open(target)
    check('fixture is a real COG',
          converted.GetMetadataItem('LAYOUT', 'IMAGE_STRUCTURE') == 'COG')
    converted = None
    return Path(target).read_bytes()


class GdalNetworkMeter:
    """Count actual GDAL download bytes, including public HEAD/GET responses.

    See https://gdal.org/en/stable/api/cpl.html
    (VSINetworkStatsGetAsSerializedJSON). No estimated Content-Length totals.
    """

    def snapshot(self):
        stats = json.loads(gdal.NetworkStatsGetAsSerializedJSON())
        methods = stats.get('methods', {})
        return (sum(item.get('count', 0) for item in methods.values()),
                sum(item.get('downloaded_bytes', 0) for item in methods.values()))


def measure_public(app, adapter, controller_class, derivative, selection_class):
    """Opt-in public COG measurements; unavailable URL/network is a clear SKIP."""
    url = os.environ.get('FM_PUBLIC_COG', '')
    if not url:
        print('SKIP public COG: set FM_PUBLIC_COG to an HTTPS COG URL to opt in', flush=True)
        return
    if not hasattr(gdal, 'NetworkStatsGetAsSerializedJSON'):
        print('SKIP public COG: this GDAL has no network byte accounting API', flush=True)
        return
    meter = GdalNetworkMeter()
    gdal.NetworkStatsReset()
    uri = '/vsicurl/' + url
    try:
        dataset = measure(meter, 'public_validate_cog', lambda: gdal.Open(uri))
        verified = dataset is not None and dataset.GetMetadataItem('LAYOUT', 'IMAGE_STRUCTURE') == 'COG'
        if dataset is not None and not verified:
            # Older COGs predate the GDAL structural LAYOUT marker. Verify their
            # tile / overview offsets with GDAL's own validator instead.
            from osgeo_utils.samples.validate_cloud_optimized_geotiff import validate
            warnings, errors, details = validate(dataset, full_check=True)
            print('INFO public COG validator warnings={} errors={}'.format(warnings, errors), flush=True)
            verified = not errors
        if not verified:
            print('SKIP public COG: URL did not open as a verified COG', flush=True)
            return
        print('INFO public COG {} dimensions={}x{} bands={}'.format(
            url, dataset.RasterXSize, dataset.RasterYSize, dataset.RasterCount), flush=True)
        dataset = None
        gdal.VSICurlClearCache()
        source = measure(meter, 'public_layer_open', lambda: QgsRasterLayer(uri, 'public', 'gdal'))
        if not source.isValid():
            print('SKIP public COG: QGIS could not open the reachable URL', flush=True)
            return
    except RuntimeError as exc:
        print('SKIP public COG: network/URL unavailable: {}'.format(str(exc)[:240]), flush=True)
        return
    controller = controller_class(None)
    controller._active_layer = source
    panel = RecordingPanel(derivative)
    controller._raster_panel = panel
    measure(meter, 'public_panel_population', lambda: controller._populate_raster(source))
    measure(meter, 'public_histogram_wait', lambda: check(
        'public histogram delivered', wait_for(app, lambda: any(item[1] for item in panel.histograms))))
    filled = [item for item in panel.histograms if item[1]]
    if not filled:
        return
    _, _, low, high, _, _ = filled[-1]
    selection = selection_class(band=1, minimum=low + (high - low) * 0.25,
                                maximum=low + (high - low) * 0.75)
    preview = source if BASELINE else controller._local_raster_sample(source)
    if preview is None:
        check('public preview sample ready', False)
        return

    def render():
        adapter.apply_selection_preview(preview, selection)
        settings = QgsMapSettings()
        settings.setLayers([preview])
        settings.setDestinationCrs(preview.crs())
        settings.setExtent(preview.extent())
        settings.setOutputSize(QSize(256, 256))
        job = QgsMapRendererParallelJob(settings)
        job.start()
        job.waitForFinished()
        check('public preview rendered', not job.renderedImage().isNull() and not job.errors())

    measure(meter, 'public_preview_render', render)
    adapter.clear_selection_preview(preview)
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer
    from filter_mate.adapters.public_api import operations
    project = QgsProject.instance()
    target = QgsVectorLayer('Point?crs=' + source.crs().authid() + '&field=name:string',
                            'Public COG production API targets', 'memory')
    extent = source.extent()
    rows = []
    for row in range(16):
        for col in range(16):
            feature = QgsFeature(target.fields())
            feature.setAttribute('name', 'cell_{}_{}'.format(row, col))
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(
                extent.xMinimum() + (col + 0.5) * extent.width() / 16,
                extent.yMinimum() + (row + 0.5) * extent.height() / 16)))
            rows.append(feature)
    outside = QgsFeature(target.fields())
    outside.setAttribute('name', 'outside_capture')
    outside.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(
        extent.xMaximum() + extent.width(), extent.yMaximum() + extent.height())))
    rows.append(outside)
    target.dataProvider().addFeatures(rows)
    project.addMapLayer(source)
    project.addMapLayer(target)

    def filtering():
        report = operations.cross_filter(source, [target], raster_selection=selection,
                                         max_pixels=65536, filter_source=False)
        kept = [feature['name'] for feature in target.getFeatures()]
        check('public production cross_filter succeeded', not report.error and not report.failed
              and target.id() in report.done, 'error={} failed={}'.format(report.error, report.failed))
        check('public production cross_filter changed vector target', 0 < len(kept) < len(rows)
              and 'outside_capture' not in kept, 'kept={}/{}'.format(len(kept), len(rows)))
        print('INFO public production report ' + json.dumps(dict(
            done=report.done, failed=report.failed, details=report.details), default=str), flush=True)

    measure(meter, 'public_filter_production_api', filtering)
    project.removeMapLayer(target.id())
    project.removeMapLayer(source.id())
    if hasattr(controller, '_release_raster_sample'):
        controller._release_raster_sample()


def measure_geopf(app, adapter):
    """Exercise the real public ortho service, color panel and cross-filter jobs."""
    if os.environ.get('FM_STREAM_PUBLIC') != '1':
        print('SKIP public WMTS: set FM_STREAM_PUBLIC=1 to opt in', flush=True)
        return
    from urllib.error import HTTPError, URLError
    from urllib.parse import quote, urlencode
    from urllib.request import urlopen
    from qgis.core import (QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry,
                           QgsPointXY, QgsProject, QgsSingleBandColorDataRenderer, QgsVectorLayer)
    from filter_mate.adapters.qgis.coverage_layers.rendered_raster import RenderedRasterTask
    from filter_mate.adapters.qgis.coverage_layers.source_jobs import RasterSourceJob
    from filter_mate.core.domain.cross_filter import CrossFilterRequest, TargetSpec
    from filter_mate.core.domain.layer_kind import LayerKind
    from filter_mate.core.services.cross_filter_service import CrossFilterService
    from filter_mate.ui.widgets.coverage_panels.raster_exploring_panel import RasterExploringPanel

    endpoint = 'https://data.geopf.fr/wmts'
    extent = QgsRectangle(160000, 5400000, 160200, 5400200)
    edge = 20037508.342789244
    tile_span = 2 * edge / (2 ** 18)
    probe_url = endpoint + '?' + urlencode(dict(
        SERVICE='WMTS', VERSION='1.0.0', REQUEST='GetTile', LAYER='ORTHOIMAGERY.ORTHOPHOTOS',
        STYLE='normal', FORMAT='image/jpeg', TILEMATRIXSET='PM', TILEMATRIX=18,
        TILECOL=int(math.floor((160100 + edge) / tile_span)),
        TILEROW=int(math.floor((edge - 5400100) / tile_span))))
    start = time.perf_counter()
    try:
        with urlopen(probe_url, timeout=20) as response:
            payload = response.read(2 * 1024 * 1024)
            mime = response.headers.get('Content-Type', '')
            if not payload.startswith(b'\xff\xd8'):
                print('SKIP public WMTS: GetTile returned {} instead of JPEG: {}'.format(
                    mime, repr(payload[:160])), flush=True)
                return
            print('METRIC ' + json.dumps(dict(
                phase='geopf_tile_preflight', seconds=round(time.perf_counter() - start, 6),
                bytes=len(payload), http_status=response.status, url=probe_url,
                qgis=Qgis.QGIS_VERSION)), flush=True)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        print('SKIP public WMTS: GetTile service unavailable: {}'.format(exc), flush=True)
        return

    # Give QGIS the WMTS capabilities request explicitly. With only /wmts,
    # these QGIS builds send a WMS capabilities request and receive HTTP 400.
    capabilities = endpoint + '?SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0'
    uri = ('contextualWMSLegend=0&crs=EPSG:3857&dpiMode=7&format=image/jpeg'
           '&layers=ORTHOIMAGERY.ORTHOPHOTOS&styles=normal&tileMatrixSet=PM&url='
           + quote(capabilities, safe=':/?'))
    print('INFO public WMTS provider URI ' + uri, flush=True)
    source = QgsRasterLayer(uri, 'Geopf ortho', 'wms')
    check('public WMTS provider valid after successful tile probe', source.isValid(),
          source.error().message() if not source.isValid() else '')
    if not source.isValid():
        return  # A reachable service with a broken provider is FAIL, never SKIP.
    crs = QgsCoordinateReferenceSystem('EPSG:3857')
    settings = QgsMapSettings()
    settings.setDestinationCrs(crs)
    settings.setExtent(extent)
    settings.setOutputSize(QSize(256, 256))
    captured = {}
    heartbeat = []
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: heartbeat.append(True))
    timer.start()

    def capture_done(task, ok):
        captured.update(ok=ok, path=task.path)
        return True

    task = RenderedRasterTask(uri, 'wms', QgsSingleBandColorDataRenderer(None, 1),
                              settings, crs, capture_done, max_pixels=65536, max_size=256)
    start = time.perf_counter()
    app.taskManager().addTask(task)
    check('public WMTS rendered capture delivered', wait_for(app, lambda: bool(captured), timeout=60))
    timer.stop()
    check('public WMTS rendered capture succeeded', captured.get('ok'), task.error)
    print('METRIC ' + json.dumps(dict(phase='geopf_rendered_capture',
          seconds=round(time.perf_counter() - start, 6), heartbeat_ticks=len(heartbeat),
          qgis=Qgis.QGIS_VERSION, extent=[160000, 5400000, 160200, 5400200],
          pixel_limit=65536)), flush=True)
    if not captured.get('ok'):
        return
    check('public WMTS capture event loop responsive', bool(heartbeat))
    local = QgsRasterLayer(task.path, source.name(), 'gdal')
    dataset = gdal.Open(task.path)
    check('public WMTS bounded RGB capture', local.isValid() and dataset.RasterCount == 3
          and dataset.RasterXSize * dataset.RasterYSize <= 65536)
    colors = np.stack([dataset.GetRasterBand(i).ReadAsArray() for i in (1, 2, 3)], axis=-1)
    check('public WMTS imagery has varied RGB pixels', np.unique(colors.reshape(-1, 3), axis=0).shape[0] > 16)
    # Pick an actual pixel from the most common coarse color class; this is
    # reproducible across imagery updates and avoids an isolated noisy pixel.
    quantized = colors.astype(np.uint32) // 16
    codes = quantized[:, :, 0] * 256 + quantized[:, :, 1] * 16 + quantized[:, :, 2]
    values, counts = np.unique(codes, return_counts=True)
    row, col = np.argwhere(codes == values[np.argmax(counts)])[len(np.argwhere(
        codes == values[np.argmax(counts)])) // 2]
    picked = {i: int(colors[row, col, i - 1]) for i in (1, 2, 3)}
    panel = RasterExploringPanel()
    panel.set_summary(adapter.read_raster_summary(source))
    panel.set_reference(adapter.raster_reference(source))
    panel.set_rendered_only(True)
    panel._tolerance_spin.setValue(10)
    panel.set_color_sample(picked)
    selection = panel.selection()
    check('public WMTS real panel makes RGB color expression', selection is not None
          and selection.mode.value == 'expression'
          and all('@' + str(i) in selection.expression for i in (1, 2, 3)),
          'picked={} expression={}'.format(picked, selection.expression if selection else None))
    if selection is None:
        panel.close()
        return
    geometry_job = RasterSourceJob(source, selection, 65536, filter_source=False,
                                   analysis_source=(task.path, 'gdal'))
    geometry_result = {}
    request = CrossFilterRequest(source.id(), LayerKind.RASTER)

    def geometry_worker(worker):
        return geometry_job.compute(request, worker.isCanceled, buffer=False)

    def geometry_done(exception, result=None):
        geometry_result.update(error=exception, geometry=result)

    worker = QgsTask.fromFunction('Geopf color selection geometry', geometry_worker, on_finished=geometry_done)
    app.taskManager().addTask(worker)
    check('public WMTS RasterSourceJob delivered', wait_for(app, lambda: bool(geometry_result)))
    geometry = geometry_result.get('geometry')
    check('public WMTS color geometry is a proper part of capture',
          geometry_result.get('error') is None and geometry is not None
          and not geometry.isEmpty() and 0 < geometry.area() < 40000 * 0.95,
          'error={} area={}'.format(geometry_result.get('error'), geometry.area() if geometry else None))
    if geometry is None or geometry.isEmpty():
        geometry_job.release()
        panel.close()
        return
    inside = geometry.pointOnSurface().asPoint()
    target = QgsVectorLayer('Point?crs=EPSG:3857&field=name:string', 'WMTS color target', 'memory')
    features = []
    for name, point in [('inside_color', inside), ('outside_capture', QgsPointXY(160300, 5400300))]:
        feature = QgsFeature(target.fields())
        feature.setAttribute('name', name)
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        features.append(feature)
    target.dataProvider().addFeatures(features)
    project = QgsProject.instance()
    project.addMapLayer(source)
    project.addMapLayer(target)
    service = CrossFilterService()
    final = {}
    original_source = source.source()
    request = CrossFilterRequest(source.id(), LayerKind.RASTER,
                                 targets=(TargetSpec(target.id(), LayerKind.VECTOR),), predicates=('Intersect',))
    source_job = RasterSourceJob(source, selection, 65536, filter_source=False,
                                 analysis_source=(task.path, 'gdal'))
    start = time.perf_counter()
    service.run(request, source_job, on_done=lambda completed, ok: final.update(task=completed, ok=ok))
    check('public WMTS vector cross-filter delivered', wait_for(app, lambda: bool(final)))
    kept = [feature['name'] for feature in target.getFeatures()]
    completed = final.get('task')
    check('public WMTS vector cross-filter keeps exactly color-region point',
          final.get('ok') and completed is not None and not completed.error
          and len(completed.outcomes) == 1 and completed.outcomes[0].success
          and kept == ['inside_color'],
          'kept={} error={} subset={}'.format(kept, completed.error if completed else None, target.subsetString()))
    check('public WMTS source remains original service', source.source() == original_source
          and source.providerType() == 'wms')
    print('METRIC ' + json.dumps(dict(phase='geopf_color_vector_cross_filter',
          seconds=round(time.perf_counter() - start, 6), picked=picked, kept=kept,
          geometry_area=geometry.area(), qgis=Qgis.QGIS_VERSION)), flush=True)
    geometry_job.release()
    panel.close()
    project.removeMapLayer(target.id())
    project.removeMapLayer(source.id())


def main():
    global app
    app = QgsApplication([], False)
    app.initQgis()
    sys.path.append(os.path.join(QgsApplication.pkgDataPath(), 'python', 'plugins'))
    with tempfile.TemporaryDirectory(prefix='fm_stream_raster_') as directory:
        folder = Path(directory)
        os.environ['FILTERMATE_LOG_DIR'] = str(folder / 'logs')
        gdal.UseExceptions()
        gdal.SetConfigOption('GDAL_PAM_ENABLED', 'NO')
        gdal.SetConfigOption('CPL_VSIL_NETWORK_STATS_ENABLED', 'YES')
        plugins = folder / 'plugins'
        plugins.mkdir()
        # Read-only package alias: avoid copying unrelated local datasets.
        (plugins / 'filter_mate').symlink_to(REPO, target_is_directory=True)
        sys.path.insert(0, str(plugins))
        from filter_mate.adapters.qgis.coverage_layers import raster_adapter as adapter
        from filter_mate.core.domain.raster_filter_criteria import (
            RasterDerivative, RasterSelection, RasterSelectionMode)
        from filter_mate.ui.controllers.coverage_mode_controller import CoverageModeController

        from filter_mate.adapters.qgis.coverage_layers import cache
        cache.set_cache_root(str(folder / 'cache'))
        gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
        gdal.SetConfigOption('GDAL_HTTP_TIMEOUT', '10')
        if os.environ.get('FM_PUBLIC_ONLY') == '1':
            measure_public(app, adapter, CoverageModeController, RasterDerivative.VALUE, RasterSelection)
            measure_geopf(app, adapter)
            cache.purge_session()
            print('RESULT {} passed, {} failed'.format(RESULTS.count('PASS'), RESULTS.count('FAIL')), flush=True)
            return int('FAIL' in RESULTS)
        server = RangeServer(make_cog(folder))
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        print('INFO QGIS {} GDAL {} fixture_bytes={} latency_ms=10'.format(
            Qgis.QGIS_VERSION, gdal.VersionInfo(), len(server.data)), flush=True)
        gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
        gdal.SetConfigOption('GDAL_HTTP_TIMEOUT', '10')
        reads = []
        for name in ('band_statistics', 'band_histogram', 'read_band_array'):
            original = getattr(adapter, name)

            def record(*args, _original=original, _name=name, **kwargs):
                reads.append((_name, threading.get_ident()))
                return _original(*args, **kwargs)

            setattr(adapter, name, record)

        def layer(phase):
            uri = '/vsicurl/http://127.0.0.1:{}/{}.tif'.format(server.server_port, phase)
            opened = measure(server, phase + '_open', lambda: QgsRasterLayer(uri, phase, 'gdal'))
            check(phase + ' valid remote COG', opened.isValid())
            return opened

        controller = CoverageModeController(None)
        panel = RecordingPanel(RasterDerivative.VALUE)
        controller._raster_panel = panel
        source = layer('panel')
        controller._active_layer = source
        ticks = []
        timer = QTimer()
        timer.setInterval(5)
        timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
        timer.start()
        reads.clear()
        measure(server, 'panel_population', lambda: controller._populate_raster(source))
        statistics_task = getattr(controller, '_raster_stats_task', None)
        synchronous = [name for name, thread in reads if thread == MAIN_THREAD]
        check('panel summary populated', panel.summary is not None)
        if BASELINE:
            print('INFO baseline synchronous reads: {}'.format(synchronous), flush=True)
            if os.environ.get('FM_STREAM_ASSERT_ASYNC') == '1':
                check('no synchronous remote statistics or pixel reads', not synchronous, str(synchronous))
        else:
            check('no synchronous remote statistics or pixel reads', not synchronous, str(synchronous))
            check('population queued statistics task',
                  getattr(controller, '_raster_stats_task', None) is not None)
        measure(server, 'histogram_wait', lambda: check(
            'histogram delivered', wait_for(app, lambda: any(item[1] for item in panel.histograms))))
        filled = [item for item in panel.histograms if item[1]]
        if filled:
            histogram = filled[-1]
            check('histogram numeric range and bins', len(histogram[1]) == 64
                  and sum(histogram[1]) > 0 and abs(histogram[2]) <= 4
                  and abs(histogram[3] - 255) <= 4, str(histogram[:1] + histogram[2:4]))
            check('histogram delivered on main thread', histogram[-1] == MAIN_THREAD)
        if not BASELINE:
            check('Qt heartbeat during worker', len(ticks) >= 2, 'ticks={}'.format(len(ticks)))
            check('statistics ran off main thread', any(thread != MAIN_THREAD for _, thread in reads))
            if statistics_task is not None and hasattr(statistics_task, 'sample_source'):
                check('task returned existing local sample', os.path.isfile(statistics_task.sample_source))
            check('worker completed', getattr(controller, '_raster_stats_task', None) is None)
        timer.stop()

        if not BASELINE and hasattr(controller, '_cancel_raster_statistics'):
            # Supersede a real in-flight request before event delivery; a canceled
            # worker must not overwrite the panel once it becomes stale.
            stale = layer('stale')
            controller._active_layer = stale
            controller._populate_raster(stale)
            task = controller._raster_stats_task
            controller._cancel_raster_statistics()
            controller._active_layer = source
            before = len(panel.histograms)
            if task is not None:
                check('task cancellation flagged', task.isCanceled())
                controller._raster_statistics_ready(task, True)
                check('stale callback ignored', len(panel.histograms) == before)
            else:
                check('stale test queued a task', False)
            check('canceled worker drained', wait_for(app, lambda: not app.taskManager().activeTasks()))
            check('canceled worker did not deliver', len(panel.histograms) == before)

        if not BASELINE:
            from filter_mate.adapters.qgis.coverage_layers.raster_statistics_task import RasterStatisticsTask
            from filter_mate.adapters.qgis.coverage_layers.raster_surface_task import RasterSurfaceTask
            from filter_mate.adapters.qgis.coverage_layers.rendered_raster import RenderedRasterTask

            captured = {}

            def capture_done(task, ok):
                captured.update(task=task, ok=ok, thread=threading.get_ident())
                return True  # retain until the assertions have read the sample

            bounded = layer('bounded')
            task = RasterStatisticsTask(
                bounded.source(), 'gdal', 1, RasterDerivative.VALUE, 1, capture_done,
                extent=QgsRectangle(512, 512, 1024, 1024), max_pixels=16384)

            def capture():
                app.taskManager().addTask(task)
                check('bounded sample worker delivered', wait_for(app, lambda: bool(captured)))
                check('bounded sample worker succeeded', captured.get('ok'), task.error)

            measure(server, 'bounded_sample_worker', capture)
            if captured.get('ok'):
                local = QgsRasterLayer(task.sample_source, 'bounded sample', 'gdal')
                check('capture in session cache', cache.in_session(task.sample_source))
                check('capture extent and strict pixel budget', local.isValid()
                      and local.extent() == QgsRectangle(512, 512, 1024, 1024)
                      and local.width() * local.height() <= 16384)
                low, high, mean = adapter.band_range(local, 1)
                check('capture preserves raw values', low >= 64 and high <= 127
                      and 90 <= mean <= 100, str((low, high, mean)))
                check('bounded callback on main thread', captured['thread'] == MAIN_THREAD)
                cache.settle([task.sample_source])

            sample = controller._local_raster_sample(source)
            if sample is not None:
                cases = [
                    ('terrain', RasterSelection(band=1, minimum=0, maximum=90,
                                                derivative=RasterDerivative.SLOPE_DEGREES)),
                    ('expression', RasterSelection(
                        mode=RasterSelectionMode.EXPRESSION,
                        expression='"panel@1" >= 64 AND "panel@1" <= 127')),
                ]
                for label, selected in cases:
                    delivered = {}

                    def surface_done(task, ok):
                        delivered.update(ok=ok, surface=task.surface, thread=threading.get_ident())

                    surface_task = RasterSurfaceTask(sample.source(), 'panel', selected, surface_done)
                    reads.clear()
                    before_bytes = server.snapshot()[1]

                    def surface_run():
                        app.taskManager().addTask(surface_task)
                        check(label + ' surface delivered', wait_for(app, lambda: bool(delivered)))
                        surface = delivered.get('surface')
                        check(label + ' surface succeeded', delivered.get('ok') and surface is not None)
                        if surface is not None:
                            if label == 'terrain':
                                check('terrain values finite and bounded', np.isfinite(surface.values).any()
                                      and np.nanmin(surface.values) >= 0 and np.nanmax(surface.values) <= 90)
                            else:
                                check('expression selects expected quarter',
                                      surface.kept_ratio is not None and abs(surface.kept_ratio - 0.25) < 0.02,
                                      str(surface.kept_ratio))
                        check(label + ' surface callback on main thread', delivered.get('thread') == MAIN_THREAD)
                        check(label + ' surface reads off main thread', bool(reads)
                              and all(thread != MAIN_THREAD for _, thread in reads), str(reads))

                    measure(server, label + '_surface_worker', surface_run)
                    check(label + ' surface uses local sample only', server.snapshot()[1] == before_bytes)

                rendered = {}
                settings = QgsMapSettings()
                settings.setDestinationCrs(sample.crs())
                settings.setExtent(sample.extent())
                settings.setOutputSize(QSize(512, 512))

                def rendered_done(task, ok):
                    rendered.update(ok=ok, path=task.path, thread=threading.get_ident())
                    return True

                rgb_task = RenderedRasterTask(sample.source(), 'gdal', sample.renderer().clone(),
                                              settings, sample.crs(), rendered_done,
                                              max_pixels=16384, max_size=256)
                before_bytes = server.snapshot()[1]

                def render_capture():
                    app.taskManager().addTask(rgb_task)
                    check('rendered RGB worker delivered', wait_for(app, lambda: bool(rendered)))
                    check('rendered RGB worker succeeded', rendered.get('ok'), rgb_task.error)
                    if rendered.get('ok'):
                        rgb = QgsRasterLayer(rendered['path'], 'RGB snapshot', 'gdal')
                        check('rendered RGB bounded session file', rgb.isValid()
                              and gdal.Open(rgb.source()).RasterCount == 3
                              and rgb.width() * rgb.height() <= 16384
                              and cache.in_session(rgb.source()),
                              'valid={} qgis_bands={} dimensions={}x{}'.format(
                                  rgb.isValid(), rgb.bandCount(), rgb.width(), rgb.height()))
                        check('rendered RGB callback on main thread', rendered['thread'] == MAIN_THREAD)
                        cache.settle([rendered['path']])

                measure(server, 'rendered_rgb_worker', render_capture)
                check('rendered RGB uses local sample only', server.snapshot()[1] == before_bytes)

        selection = RasterSelection(band=1, minimum=64, maximum=127)
        preview = layer('preview') if BASELINE else None
        if not BASELINE and hasattr(controller, '_local_raster_sample'):
            sample = controller._local_raster_sample(source)
            check('worker materialized local sample', sample is not None and sample.isValid()
                  and '/vsicurl/' not in sample.source())
            if sample is not None:
                check('preview sample pixel budget', sample.width() * sample.height() <= 1000000)
                preview = sample
        if preview is None:
            raise RuntimeError('No local preview sample was delivered')

        def render_preview():
            check('preview transparency applied', adapter.apply_selection_preview(preview, selection))
            settings = QgsMapSettings()
            settings.setLayers([preview])
            settings.setDestinationCrs(preview.crs())
            settings.setExtent(preview.extent())
            settings.setOutputSize(QSize(256, 256))
            job = QgsMapRendererParallelJob(settings)
            job.start()
            job.waitForFinished()
            image = job.renderedImage()
            check('preview rendered', not image.isNull() and not job.errors(), str(job.errors()))

        preview_before = server.snapshot()
        measure(server, 'preview_render', render_preview)
        if not BASELINE:
            check('preview reads no remote bytes', server.snapshot()[1] == preview_before[1])
        adapter.clear_selection_preview(preview)
        filtering = layer('filter')
        outcome = {}
        filter_source = filtering.source()

        def filter_worker(task):
            private = QgsRasterLayer(filter_source, 'worker selection', 'gdal')
            # A known useful extent: half the width / height of the source.
            rect = QgsRectangle(0, 0, 1024, 1024)
            return adapter.selection_geometry(
                private.dataProvider(), selection, rect, 1024, 1024,
                private.crs().toWkt(), max_pixels=65536, sieve_pixels=0,
                is_canceled=task.isCanceled)

        def filtered(exception, result=None):
            outcome['exception'] = exception
            outcome['result'] = result

        def run_filter():
            task = QgsTask.fromFunction('Streaming selection smoke', filter_worker, on_finished=filtered)
            app.taskManager().addTask(task)
            check('filter worker completed', wait_for(app, lambda: 'exception' in outcome))
            result = outcome.get('result')
            check('bounded filter geometry', outcome.get('exception') is None and result is not None
                  and not result.geometry.isEmpty()
                  and abs(result.geometry.area() - 524288) < 10000,
                  'error={} area={}'.format(
                      outcome.get('exception'), result.geometry.area() if result else None))

        measure(server, 'filter_selection_worker', run_filter)
        requests, sent = server.snapshot()
        check('HTTP served real byte ranges', requests > 0 and sent > 0)
        measure_public(app, adapter, CoverageModeController, RasterDerivative.VALUE, RasterSelection)
        print('SKIP public WCS: external network/service integration is opt-in manual validation', flush=True)
        measure_geopf(app, adapter)
        if hasattr(controller, '_release_raster_sample'):
            controller._release_raster_sample()
        server.shutdown()
        server.server_close()
        serving.join(timeout=2)
        # Keep QGIS providers alive until their jobs finish; shutdown after locals
        # are released by main() avoids provider destruction after exitQgis().
        check('all workers drained', wait_for(app, lambda: not app.taskManager().activeTasks()))
        cache.purge_session()
    print('RESULT {} passed, {} failed'.format(RESULTS.count('PASS'), RESULTS.count('FAIL')), flush=True)
    return int('FAIL' in RESULTS)


if __name__ == '__main__':
    try:
        exit_status = main()
    except Exception:
        traceback.print_exc()
        exit_status = 1
    # Network providers retain Qt thread-local state. Release Python cycles
    # while providers are still registered, then shut QGIS down explicitly.
    if 'app' in globals():
        import gc
        from qgis.core import QgsProject
        app.taskManager().cancelAll()
        if not wait_for(app, lambda: not app.taskManager().activeTasks(), timeout=10):
            exit_status = 1
        QgsProject.instance().clear()
        app.processEvents()
        gc.collect()
        app.exitQgis()
    sys.exit(exit_status)

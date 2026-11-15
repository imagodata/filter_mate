# -*- coding: utf-8 -*-
"""Bounded worker-only value raster captures in the derived session cache."""
import math
import os
import threading

from ....core.domain.source_capability import classify, Locality
from . import cache


def _tr(text):
    """Translate user-visible capture refusals without requiring Qt at import."""
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        translated = QCoreApplication.translate('RasterMaterialization', text)
        return translated if isinstance(translated, str) else text
    except ImportError:
        return text


def is_wcs(provider, source):
    """Identify value services through the shared capability classification."""
    capability = classify(provider, source, is_raster=True)
    return capability.locality is Locality.REMOTE_SERVICE and capability.has_raw_values


def raster_reads_remotely(provider, source):
    """Whether opening values must be deferred, including PostGIS raster."""
    capability = classify(provider, source, is_raster=True)
    # PostgreSQL raster is not yet a separate entry in source_capability.
    return provider.strip().lower() == 'postgresraster' or not capability.counts_cheaply


def bounded_grid(extent, width, height, max_pixels, resolution=None):
    """Return positive dimensions with a strict cell budget and no upsampling."""
    span_x, span_y = extent.width(), extent.height()
    if not all(math.isfinite(v) and v > 0 for v in (span_x, span_y)):
        raise ValueError(_tr('raster capture requires a finite, non-empty extent'))
    limit = int(max_pixels)
    if limit < 1:
        raise ValueError(_tr('raster capture requires a positive pixel limit'))
    width, height = max(1, int(width)), max(1, int(height))
    if resolution is not None:
        resolution = float(resolution)
        if not math.isfinite(resolution) or resolution <= 0:
            raise ValueError(_tr('raster capture requires a positive resolution'))
        width = min(width, max(1, int(math.floor(span_x / resolution))))
        height = min(height, max(1, int(math.floor(span_y / resolution))))
    if width * height > limit:
        factor = math.sqrt(width * height / float(limit))
        width = max(1, int(width / factor))
        height = max(1, int(height / factor))
        # Thin extents can still exceed the budget after clamping to one cell.
        width = min(width, limit)
        height = min(height, max(1, limit // width))
    return width, height


def materialize_raster(layer, extent=None, max_pixels=None, resolution=None, is_canceled=None, destination=None):
    """Write raw pixels to a bounded GeoTIFF, only from a worker-owned layer.

    Args:
        layer: Private raster layer created in the worker, never a project layer.
        extent: Capture extent in layer CRS; None captures the source extent.
        max_pixels: Positive cell budget; None uses raster_source_max_pixels.
        resolution: Optional minimum cell size in layer CRS units.
        is_canceled: Cancellation predicate, polled at writer progress events.
        destination: Internal option for jobs sharing a cache key with a VRT.

    Returns:
        str: Protected session path. The caller must cache.settle([path]) after
            apply, or once a UI capture is no longer needed.

    Raises:
        RuntimeError: Main thread, cancellation or failed export. Failed exports
            are removed and settled; a partial raster is never returned.
    """
    if threading.current_thread() is threading.main_thread():
        raise RuntimeError(_tr('raster materialization must run in a worker thread'))
    from qgis.core import (QgsCoordinateTransformContext, QgsRasterBlockFeedback,
                           QgsRasterFileWriter, QgsRasterPipe, QgsRectangle)
    from .raster_adapter import source_max_pixels
    canceled = is_canceled or (lambda: False)
    if canceled():
        raise RuntimeError(_tr('raster capture canceled'))
    if not layer.isValid():
        raise RuntimeError(_tr('raster capture source could not be opened'))
    capability = classify(layer.providerType(), layer.source(), is_raster=True)
    if not capability.has_raw_values:
        raise RuntimeError(_tr('rendered rasters require a rendered color capture'))
    full = layer.extent()
    area = QgsRectangle(full if extent is None else extent)
    area = area.intersect(full)
    width = max(1, int(math.ceil(layer.width() * area.width() / full.width()))) if full.width() > 0 else 1
    height = max(1, int(math.ceil(layer.height() * area.height() / full.height()))) if full.height() > 0 else 1
    limit = (source_max_pixels(cache._config_value('raster_source_max_pixels', None))
             if max_pixels is None else int(max_pixels))
    width, height = bounded_grid(area, width, height, limit, resolution)
    path = destination or cache.new_path(layer.name(), '.tif')
    if not cache.in_session(path):
        raise ValueError(_tr('raster capture destination must be in the session cache'))
    try:
        pipe = QgsRasterPipe()
        if not pipe.set(layer.dataProvider().clone()):
            raise RuntimeError(_tr('raster capture provider could not be cloned'))
        feedback = QgsRasterBlockFeedback()

        def poll(*args):
            if canceled():
                feedback.cancel()

        feedback.progressChanged.connect(poll)
        writer = QgsRasterFileWriter(path)
        writer.setOutputFormat('GTiff')
        writer.setCreateOptions(['COMPRESS=LZW', 'TILED=YES'])
        poll()
        result = writer.writeRaster(pipe, width, height, area, layer.crs(), QgsCoordinateTransformContext(), feedback)
        if canceled() or feedback.isCanceled():
            raise RuntimeError(_tr('raster capture canceled'))
        if int(getattr(result, 'value', result)) != 0:
            raise RuntimeError(_tr('bounded raster capture failed'))
        return path
    except Exception:
        for suffix in ('', '.aux.xml', '.msk'):
            try:
                os.remove(path + suffix)
            except OSError:
                # The cache collector retries files held open by a provider.
                pass
        cache.settle([path])
        raise


# --- web maps (WMS, WMTS, XYZ tiles) -----------------------------------------
# 2026-11-15: a web map is a filter target. It draws an image and has no grid of its own: it is captured once, in
# the area the source keeps, on a grid chosen here, then cut as a local raster is (RasterTargetJob).

# Pixels of the capture of a web map: 4096 x 4096, about 250 tiles of 256 px, 64 MB before compression.
WEB_MAP_MAX_PIXELS = 16000000
WEB_MAP_MIN_PIXELS = 65536  # one tile
WEB_MAP_MAX_BUDGET = 268435456  # 16384 x 16384: above, a configured budget is brought back to it
WEB_MAP_TIMEOUT_SECONDS = 180.0


def web_map_max_pixels(value) -> int:
    """``CROSS_FILTER.web_map_target_max_pixels`` read from a config value; nothing or unreadable is the default."""
    if isinstance(value, dict):
        value = value.get('value')
    if isinstance(value, str):
        value = value.replace(' ', '').replace(' ', '').replace('_', '')
    try:
        number = int(float(value)) if not isinstance(value, bool) and value is not None else 0
    except (TypeError, ValueError, OverflowError):
        number = 0
    return WEB_MAP_MAX_PIXELS if number <= 0 else min(WEB_MAP_MAX_BUDGET, max(WEB_MAP_MIN_PIXELS, number))


def web_map_grid(full, box, max_pixels, native_resolutions=()):
    """The grid a web map is captured on: ``((x_min, y_min, x_max, y_max), columns, rows, resolution)``.

    The finest grid ``max_pixels`` affords over ``box`` (what the source keeps), inside ``full`` (the extent of the
    service), with one cell of margin (the cutline keeps the cells whose centre is inside). A tile service names
    its levels (``native_resolutions``, map units per pixel): the finest level within the budget is taken, never a
    finer grid than its finest level, and the area is snapped to the pixels of that level from the upper left
    corner of ``full``, so that tiles are copied and not resampled. Without levels (a WMS) the resolution is the
    one the budget gives. Where even the coarsest level is past the budget, the grid is coarser than it.

    Args:
        full, box: ``(x_min, y_min, x_max, y_max)`` in the CRS of the layer.
        max_pixels: Budget of cells of the capture.
        native_resolutions: Levels of a tile service; empty for a service that draws at any resolution.

    Raises:
        ValueError: ``box`` does not meet ``full``, or a bound that is not finite.
    """
    values = tuple(float(value) for value in tuple(full) + tuple(box))
    if not all(math.isfinite(value) for value in values):
        raise ValueError(_tr('raster capture requires a finite, non-empty extent'))
    full_x0, full_y0, full_x1, full_y1 = values[:4]
    x0, y0 = max(values[4], full_x0), max(values[5], full_y0)
    x1, y1 = min(values[6], full_x1), min(values[7], full_y1)
    if not (x1 > x0 and y1 > y0):
        raise ValueError(_tr('raster capture requires a finite, non-empty extent'))
    limit = int(max_pixels)
    if limit < 1:
        raise ValueError(_tr('raster capture requires a positive pixel limit'))

    def window(resolution):
        first_column = max(0, int(math.floor((x0 - full_x0) / resolution)) - 1)
        last_column = int(math.ceil((x1 - full_x0) / resolution)) + 1
        first_row = max(0, int(math.floor((full_y1 - y1) / resolution)) - 1)
        last_row = int(math.ceil((full_y1 - y0) / resolution)) + 1
        left, top = full_x0 + first_column * resolution, full_y1 - first_row * resolution
        right = min(full_x1, full_x0 + last_column * resolution)
        bottom = max(full_y0, full_y1 - last_row * resolution)
        columns = max(1, int(round((right - left) / resolution)))
        rows = max(1, int(round((top - bottom) / resolution)))
        return (left, bottom, right, top), columns, rows

    levels = sorted({float(level) for level in native_resolutions or ()
                     if isinstance(level, (int, float)) and math.isfinite(level) and level > 0})
    for level in levels:  # from the finest
        area, columns, rows = window(level)
        if columns * rows <= limit:
            return area, columns, rows, level
    resolution = math.sqrt((x1 - x0) * (y1 - y0) / float(limit))
    if levels:
        resolution = max(resolution, levels[-1])
    for _attempt in range(16):  # the margin and the snapping add cells: coarser until it fits
        area, columns, rows = window(resolution)
        if columns * rows <= limit:
            break
        resolution *= math.sqrt(columns * rows / float(limit)) * 1.001
    return area, columns, rows, resolution


_MARK = None  # one QObject of the main thread, kept for the life of the plugin (never deleted from a worker)
_MARK_LOCK = threading.Lock()


def _main_thread_mark():
    """The object whose queued call tells a worker the main thread handled what was posted before it."""
    global _MARK
    from qgis.PyQt.QtCore import QCoreApplication, QObject, pyqtSlot
    with _MARK_LOCK:
        if _MARK is None:
            application = QCoreApplication.instance()
            if application is None:
                return None

            class Mark(QObject):
                def __init__(self):
                    super().__init__()
                    self.waiting = []

                @pyqtSlot()
                def reach(self):
                    # Every event waiting was posted before this call: the queue is in order.
                    with _MARK_LOCK:
                        reached, self.waiting = self.waiting, []
                    for event in reached:
                        event.set()

            mark = Mark()
            mark.moveToThread(application.thread())
            _MARK = mark
        return _MARK


def _after_main_thread_events(seconds=1.5) -> bool:
    """Wait until the main thread handled the events already posted to it; False when it did not in time."""
    from qgis.PyQt.QtCore import QMetaObject, Qt
    mark = _main_thread_mark()
    if mark is None:
        return False
    reached = threading.Event()
    with _MARK_LOCK:
        mark.waiting.append(reached)
    QMetaObject.invokeMethod(mark, 'reach', Qt.ConnectionType.QueuedConnection)
    return reached.wait(seconds)


def _service_place(layer):
    """``(scheme, host)`` of the service a web map asks, to tell its replies from those of other layers."""
    from urllib.parse import unquote, urlsplit
    from qgis.core import QgsDataSourceUri
    try:
        url = unquote(QgsDataSourceUri(layer.source()).param('url') or '')
        parts = urlsplit(url)
        host = parts.netloc.lower()
        if '}' in host:  # a template in the host ({s}.tile...): what follows it
            host = host.rsplit('}', 1)[1].lstrip('.')
        return parts.scheme.lower(), host
    except Exception:  # an address that cannot be read: every reply is counted, as before
        return '', ''


def _has_visible_pixel(path) -> bool:
    """Whether the capture at ``path`` holds one pixel that is not fully transparent (its last band is alpha)."""
    from osgeo import gdal
    dataset = gdal.Open(path)
    if dataset is None:
        return False
    try:
        band = dataset.GetRasterBand(dataset.RasterCount)
        for row in range(0, dataset.RasterYSize, 1024):
            rows = min(1024, dataset.RasterYSize - row)
            if band.ReadAsArray(0, row, dataset.RasterXSize, rows).any():
                return True
        return False
    finally:
        dataset = None


def materialize_web_map(layer, area, columns, rows, is_canceled=None, timeout=WEB_MAP_TIMEOUT_SECONDS):
    """Write what a web map draws over ``area`` to a GeoTIFF (red, green, blue, alpha), from a worker only.

    2026-11-15. Read in real QGIS 3.22, 3.44 and 4.3: the writer of QGIS gets no error for a tile or a GetMap the
    service did not answer (the pixels stay transparent, the result code is 0), and a web map may be transparent
    of its own. The requests are counted instead: one never answered with an image is a hole. A GetMap is asked
    by this thread; tiles are asked by the tile manager of QGIS in a thread of its own (not reachable from
    Python), and every thread tells the network manager of the main thread what it finished: both are heard,
    the second once the main thread handled what was posted to it (a main thread that is busy hears nothing
    in time: holes are then not said, as in QGIS itself).

    Args:
        layer: Private layer or bare provider wrapper created in the worker, never a project layer.
        area: QgsRectangle of the capture, in the CRS of the layer.
        columns, rows: Size of the capture (``web_map_grid``).
        is_canceled: Cancellation predicate, polled ten times a second.
        timeout: Seconds after which the capture is given up.

    Returns:
        ``(path, unread)``: protected session path (the caller settles it), and the number of requests the
        service never answered with an image (0: no hole).

    Raises:
        RuntimeError: Main thread, cancellation, timeout, failed export, or a service that answered no request.
    """
    if threading.current_thread() is threading.main_thread():
        raise RuntimeError(_tr('raster materialization must run in a worker thread'))
    import time
    from qgis.core import (QgsCoordinateTransformContext, QgsNetworkAccessManager, QgsRasterBlockFeedback,
                           QgsRasterFileWriter, QgsRasterPipe)
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest
    canceled = is_canceled or (lambda: False)
    if canceled():
        raise RuntimeError(_tr('raster capture canceled'))
    if not layer.isValid():
        raise RuntimeError(_tr('raster capture source could not be opened'))
    if int(columns) < 1 or int(rows) < 1 or int(columns) * int(rows) > WEB_MAP_MAX_BUDGET:
        raise ValueError(_tr('raster capture requires a positive pixel limit'))
    path = cache.new_path(layer.name(), '.tif')
    feedback = QgsRasterBlockFeedback()
    stop = threading.Event()
    deadline = time.monotonic() + max(1.0, float(timeout))
    timed_out = []
    unread = {}

    def watch():
        while not stop.wait(0.1):
            late = time.monotonic() >= deadline
            if late or canceled():
                if late:
                    timed_out.append(True)
                feedback.cancel()
                return

    scheme, host = _service_place(layer)

    def finished(reply):
        # The signal of QGIS (a QgsNetworkReplyContent, a copy of the reply). The network manager of the main
        # thread hears the replies of every thread: those of the canvas and of other layers too. Only the replies
        # of the service of this web map are counted.
        try:
            url = reply.request().url()
            address = url.toString()
            place = (url.scheme().lower(), url.host().lower())
            error = reply.error()
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            kind = bytes(reply.rawHeader(b'Content-Type')).decode('ascii', 'replace').strip().lower()
        except (RuntimeError, AttributeError, TypeError):
            return
        if host and (place[0] != scheme or not (place[1] == host or place[1].endswith('.' + host))):
            return
        if error == QNetworkReply.NetworkError.OperationCanceledError:
            return  # a request QGIS dropped (the capture ended, or the canvas moved): nothing was missed
        status = int(status) if isinstance(status, int) else 0
        if error == QNetworkReply.NetworkError.ContentNotFoundError or status in (204, 404):
            # Many tile servers answer 404 where they have no tile (beyond their coverage or their last level):
            # an answer, transparent, not a hole.
            unread.pop(address, None)
        elif error != QNetworkReply.NetworkError.NoError or (
                status == 200 and any(word in kind for word in ('xml', 'json', 'html', 'text/plain'))):
            # HTTP 200 with a document in place of an image: a service exception report. (Tiles served as
            # application/octet-stream are images all the same.)
            unread[address] = True
        elif status in (0, 200):
            unread.pop(address, None)  # a tile asked again and answered

    from ..source_capability_probe import main_network_manager
    network = QgsNetworkAccessManager.instance()
    main_network = main_network_manager()
    if main_network is network:
        main_network = None
    network.finished.connect(finished, Qt.ConnectionType.DirectConnection)
    if main_network is not None:
        main_network.finished.connect(finished, Qt.ConnectionType.DirectConnection)
    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        pipe = QgsRasterPipe()
        if not pipe.set(layer.dataProvider().clone()):
            raise RuntimeError(_tr('raster capture provider could not be cloned'))
        writer = QgsRasterFileWriter(path)
        writer.setOutputFormat('GTiff')
        options = ['COMPRESS=LZW', 'TILED=YES']
        (getattr(writer, 'setCreationOptions', None) or writer.setCreateOptions)(options)
        result = writer.writeRaster(pipe, int(columns), int(rows), area, layer.crs(),
                                    QgsCoordinateTransformContext(), feedback)
        if int(getattr(result, 'value', result)) != 0:
            # A capture that ended is kept even when its deadline passed as it ended.
            if timed_out:
                raise RuntimeError(_tr('the web map did not answer in time'))
            if canceled() or feedback.isCanceled():
                raise RuntimeError(_tr('raster capture canceled'))
            raise RuntimeError(_tr('bounded raster capture failed'))
        if canceled():
            raise RuntimeError(_tr('raster capture canceled'))
        if main_network is not None:
            _after_main_thread_events()
        if unread and not _has_visible_pixel(path):
            # Requests failed and nothing was drawn: not a map that is transparent of its own.
            raise RuntimeError(_tr('the web map answered none of the requests of the capture'))
        return path, len(unread)
    except Exception:
        for suffix in ('', '.aux.xml', '.msk'):
            try:
                os.remove(path + suffix)
            except OSError:
                pass  # the cache collector retries files held open by a provider
        cache.settle([path])
        raise
    finally:
        stop.set()
        for manager in (network, main_network):
            try:
                if manager is not None:
                    manager.finished.disconnect(finished)
            except (TypeError, RuntimeError):
                pass

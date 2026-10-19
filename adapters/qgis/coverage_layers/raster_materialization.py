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

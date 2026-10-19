# -*- coding: utf-8 -*-
"""Sample remote raster statistics using a layer owned by the worker thread."""
import logging

from qgis.core import QgsRasterLayer, QgsTask
from qgis.PyQt.QtCore import QCoreApplication

from .raster_adapter import band_histogram, band_range, derivative_histogram
from . import cache
from .raster_materialization import materialize_raster

logger = logging.getLogger(__name__)


class RasterStatisticsTask(QgsTask):
    """Return plain Python results; never access the project layer in run()."""

    def __init__(self, source, provider, band, derivative, band_count, callback,
                 extent=None, max_pixels=1000000, resolution=None, sample_source=''):
        super().__init__(QCoreApplication.translate('RasterStatisticsTask', 'FilterMate: raster statistics'),
                         QgsTask.Flag.CanCancel)
        self.source = source
        self.provider = provider
        self.band = band
        self.derivative = derivative
        self.band_count = band_count
        self.callback = callback
        self.histogram = ([], 0.0, 0.0)
        self.spans = {}
        self.extent = extent
        self.max_pixels = max_pixels
        self.resolution = resolution
        self.sample_source = sample_source
        self.owns_sample = not bool(sample_source)
        self.error = ''

    def run(self):
        try:
            layer = QgsRasterLayer(self.sample_source or self.source, 'FilterMate statistics',
                                   'gdal' if self.sample_source else self.provider)
            if not layer.isValid() or self.isCanceled():
                return False
            if not self.sample_source:
                self.sample_source = materialize_raster(layer, self.extent, self.max_pixels,
                                                        self.resolution, self.isCanceled)
                layer = QgsRasterLayer(self.sample_source, 'FilterMate statistics', 'gdal')
                if not layer.isValid():
                    return False
            for band in range(1, min(self.band_count, 4) + 1):
                if self.isCanceled():
                    return False
                low, high, _ = band_range(layer, band)
                if low is not None and high is not None and high > low:
                    self.spans[band] = high - low
            if self.isCanceled():
                return False
            if self.derivative.is_terrain:
                self.histogram = derivative_histogram(layer, self.band, self.derivative, bins=64)
            else:
                self.histogram = band_histogram(layer, self.band, bins=64)
            return not self.isCanceled()
        except Exception:
            # Provider exceptions may include credentials in their URI.
            self.error = QCoreApplication.translate(
                'RasterStatisticsTask', 'Raster sample failed; retry with a smaller visible extent.')
            return False

    def finished(self, result):
        accepted = self.callback(self, result and not self.isCanceled())
        if self.owns_sample and not accepted and self.sample_source:
            cache.settle([self.sample_source])

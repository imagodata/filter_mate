# -*- coding: utf-8 -*-
"""Compute raster statistics using a layer owned by the worker thread."""
import logging

from qgis.core import QgsRasterLayer, QgsTask
from qgis.PyQt.QtCore import QCoreApplication

from .raster_adapter import band_histogram, band_range, derivative_histogram, expression_histogram, raster_expression_error
from . import cache
from .raster_materialization import materialize_raster

logger = logging.getLogger(__name__)


class RasterStatisticsTask(QgsTask):
    """Return plain Python results; never access the project layer in run()."""

    def __init__(self, source, provider, band, derivative, band_count, callback,
                 extent=None, max_pixels=1000000, resolution=None, sample_source='', expression='', layer_name='FilterMate statistics',
                 materialize=True):
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
        self.materialize = bool(materialize)
        self.owns_sample = self.materialize and not bool(sample_source)
        self.error = ''
        self.expression_error = ''
        self.expression, self.layer_name = expression, layer_name

    def run(self):
        try:
            if self.isCanceled():
                return False
            if self.expression:
                reference = ''.join(c if c.isalnum() or c == '_' else '_' for c in self.layer_name) or 'raster'
                self.expression_error = raster_expression_error(self.expression, reference, self.band_count)
                if self.expression_error:
                    return False
            layer = QgsRasterLayer(self.sample_source or self.source, self.layer_name,
                                   'gdal' if self.sample_source else self.provider)
            if not layer.isValid() or self.isCanceled():
                return False
            if self.materialize and not self.sample_source:
                self.sample_source = materialize_raster(layer, self.extent, self.max_pixels,
                                                        self.resolution, self.isCanceled)
                layer = QgsRasterLayer(self.sample_source, self.layer_name, 'gdal')
                if not layer.isValid():
                    return False
            for band in range(1, min(self.band_count, 4) + 1) if self.materialize else ():
                if self.isCanceled():
                    return False
                low, high, _ = band_range(layer, band)
                if low is not None and high is not None and high > low:
                    self.spans[band] = high - low
            if self.isCanceled():
                return False
            if self.expression:
                self.histogram = expression_histogram(layer, self.expression, bins=64, max_pixels=self.max_pixels)
            elif self.derivative.is_terrain:
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

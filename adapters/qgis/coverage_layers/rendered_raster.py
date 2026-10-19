"""Bounded, layer-only rendered RGB snapshots for colour selections.

Construct on the GUI thread with a detached ``layer.renderer().clone()``;
submit to QgsApplication.taskManager(). No provider is opened until run().
The callback runs on the GUI thread and must reject obsolete generations.
The resulting local RGB bands can feed identify_values and RasterSourceJob.
"""
import math
import os

from qgis.core import (
    QgsCoordinateTransform, QgsMapSettings, QgsMapRendererSequentialJob,
    QgsRasterLayer, QgsTask,
)
from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QSize, QTimer
from qgis.PyQt.QtGui import QColor, QImage

from . import cache


def bounded_size(width, height, max_pixels=1000000, max_size=2048):
    """Keep aspect ratio while enforcing both a pixel and an edge budget."""
    values = (width, height, max_pixels, max_size)
    if any(not math.isfinite(float(value)) or float(value) < 1 for value in values):
        raise ValueError('Invalid rendered snapshot dimensions or budget')
    factor = min(1.0, float(max_size) / width, float(max_size) / height,
                 math.sqrt(float(max_pixels) / (width * height)))
    bounded_width, bounded_height = max(1, int(width * factor)), max(1, int(height * factor))
    bounded_width = min(bounded_width, int(max_pixels))
    bounded_height = min(bounded_height, max(1, int(max_pixels) // bounded_width))
    return bounded_width, bounded_height


def write_rgb(image, path, extent, crs, canceled=lambda: False):
    """Write unpremultiplied RGB bytes plus a validity mask, never styled again."""
    import numpy as np
    from osgeo import gdal

    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = image.width(), image.height()
    pointer = image.constBits()
    length = image.bytesPerLine() * height
    pointer.setsize(length)
    pixels = np.frombuffer(pointer, dtype=np.uint8).reshape(height, image.bytesPerLine())
    pixels = pixels[:, :width * 4].reshape(height, width, 4)
    if not np.any(pixels[:, :, 3]):
        raise ValueError('Rendered snapshot has no visible pixels')
    dataset = gdal.GetDriverByName('GTiff').Create(
        path, width, height, 3, gdal.GDT_Byte,
        options=['COMPRESS=DEFLATE', 'PHOTOMETRIC=RGB'])
    if dataset is None:
        raise RuntimeError('Cannot create rendered snapshot')
    try:
        dataset.SetGeoTransform((extent.xMinimum(), extent.width() / width, 0,
                                 extent.yMaximum(), 0, -extent.height() / height))
        dataset.SetProjection(crs.toWkt())
        for index, interpretation in enumerate((gdal.GCI_RedBand, gdal.GCI_GreenBand, gdal.GCI_BlueBand)):
            if canceled():
                raise RuntimeError('Rendered snapshot canceled')
            band = dataset.GetRasterBand(index + 1)
            band.WriteArray(pixels[:, :, index])
            band.SetColorInterpretation(interpretation)
        # A separate mask preserves valid black pixels; zero is not RGB NoData.
        band = dataset.GetRasterBand(1)
        band.CreateMaskBand(gdal.GMF_PER_DATASET)
        band.GetMaskBand().WriteArray(np.where(pixels[:, :, 3] > 0, 255, 0).astype(np.uint8))
        dataset.FlushCache()
    finally:
        dataset = None


class RenderedRasterTask(QgsTask):
    """Render a detached provider in a worker and return a session-cache TIFF.

    Args:
        source: Original provider URI, retained only in memory.
        provider: QGIS provider key (including wms, arcgismapserver, gdal).
        renderer: Detached renderer clone, whose ownership passes to the worker.
        map_settings: Canvas settings, copied immediately without its layers.
        layer_crs: Destination CRS of the snapshot (the original layer CRS).
        callback: ``callback(task, success)`` on the GUI thread.
        max_pixels: Upper bound on total output pixels.
        max_size: Upper bound on each output edge.
    """

    def __init__(self, source, provider, renderer, map_settings, layer_crs,
                 callback, max_pixels=1000000, max_size=2048):
        super().__init__(QCoreApplication.translate('RenderedRasterTask', 'FilterMate: rendered colour snapshot'),
                         QgsTask.Flag.CanCancel)
        self.source, self.provider = source, provider
        self.renderer = renderer
        self.callback = callback
        self.path = ''
        self.error = ''
        self.settings = QgsMapSettings(map_settings)
        self.settings.setLayers([])
        self.settings.setLayerStyleOverrides({})
        transform = QgsCoordinateTransform(map_settings.destinationCrs(), layer_crs,
                                           map_settings.transformContext())
        extent = transform.transformBoundingBox(map_settings.visibleExtent())
        if extent.isEmpty() or not extent.isFinite():
            raise ValueError('Invalid rendered snapshot extent')
        self.settings.setDestinationCrs(layer_crs)
        self.settings.setRotation(0)
        self.settings.setDevicePixelRatio(1)
        size = map_settings.outputSize()
        width, height = bounded_size(size.width(), size.height(), max_pixels, max_size)
        # Fit the output aspect ratio to the transformed bounding box, rather
        # than letting QGIS expand the requested geographic coverage.
        if extent.width() / extent.height() > width / height:
            height = max(1, int(width * extent.height() / extent.width()))
        else:
            width = max(1, int(height * extent.width() / extent.height()))
        self.settings.setOutputSize(QSize(width, height))
        self.settings.setExtent(extent)
        # Keep scale-dependent rendering at the canvas scale despite the cap.
        self.settings.setOutputDpi(self.settings.outputDpi() * map_settings.scale() / self.settings.scale())
        self.settings.setBackgroundColor(QColor(0, 0, 0, 0))
        self.extent = self.settings.visibleExtent()

    def run(self):
        """Open, render and write only on worker threads."""
        layer = job = None
        try:
            if self.isCanceled():
                return False
            layer = QgsRasterLayer(self.source, 'FilterMate rendered colours', self.provider)
            if not layer.isValid() or self.isCanceled():
                raise RuntimeError('Rendered source could not be opened')
            if self.renderer is not None:
                layer.setRenderer(self.renderer)
                self.renderer = None
            self.settings.setLayers([layer])
            job = QgsMapRendererSequentialJob(self.settings)
            loop = QEventLoop()
            timer = QTimer()
            timer.setInterval(100)
            timer.timeout.connect(lambda: job.cancelWithoutBlocking() if self.isCanceled() else None)
            job.finished.connect(loop.quit)
            job.start()
            timer.start()
            if job.isActive():
                loop.exec()
            timer.stop()
            job.waitForFinished()  # Worker only, never the GUI thread.
            if self.isCanceled():
                return False
            if job.errors():
                raise RuntimeError('Rendered source reported a rendering error')
            image = job.renderedImage()
            if image.isNull():
                raise RuntimeError('Rendered source returned an empty image')
            self.path = cache.new_path('rendered_rgb', '.tif')
            write_rgb(image, self.path, self.extent, self.settings.destinationCrs(), self.isCanceled)
            return not self.isCanceled()
        except Exception:
            # Provider errors can contain credentials; expose only a safe reason.
            self.error = QCoreApplication.translate(
                'RenderedRasterTask', 'Rendered snapshot failed; retry with a smaller visible extent.')
            return False
        finally:
            self.settings.setLayers([])
            job = layer = None

    def finished(self, result):
        success = bool(result and not self.isCanceled())
        if not success:
            for suffix in ('', '.msk', '.aux.xml'):
                if self.path and os.path.isfile(self.path + suffix):
                    os.unlink(self.path + suffix)
        if not success:
            cache.settle([self.path])
        # Successful captures remain in flight until the controller leaves or
        # replaces the sample. It must settle obsolete successful results too.
        accepted = self.callback(self, success)
        if success and accepted is False:
            for suffix in ('', '.msk', '.aux.xml'):
                if os.path.isfile(self.path + suffix):
                    os.unlink(self.path + suffix)
            cache.settle([self.path])

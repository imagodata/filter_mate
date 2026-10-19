# -*- coding: utf-8 -*-
"""Build raster preview arrays away from the GUI thread."""
from qgis.core import QgsRasterLayer, QgsTask
from qgis.PyQt.QtCore import QCoreApplication


class RasterSurfaceTask(QgsTask):
    """Read a local bounded capture and return a terrain or expression surface."""

    def __init__(self, path, name, selection, callback):
        super().__init__(QCoreApplication.translate('RasterSurfaceTask', 'FilterMate: raster preview'),
                         QgsTask.Flag.CanCancel)
        self.path, self.name, self.selection = path, name, selection
        self.callback = callback
        self.surface = None

    def run(self):
        from .preview_overlay import DerivativeSurface, ExpressionSurface
        try:
            if self.isCanceled():
                return False
            layer = QgsRasterLayer(self.path, self.name, 'gdal')
            if not layer.isValid():
                return False
            if self.selection.mode.value == 'expression':
                self.surface = ExpressionSurface(layer, self.selection)
            else:
                self.surface = DerivativeSurface(layer, self.selection.band, self.selection.derivative)
            return not self.isCanceled()
        except Exception:
            return False

    def finished(self, result):
        self.callback(self, result and not self.isCanceled())

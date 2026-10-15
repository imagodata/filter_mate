# -*- coding: utf-8 -*-
"""
Height above a DTM for a point cloud, through PDAL ``filters.hag_dem``.

The point cloud is rewritten as a COPC file carrying a ``HeightAboveGround``
dimension and the layer is switched to it (derived source, restored on
unfilter / unload). Afterwards ``HeightAboveGround >= 2`` is an ordinary,
live subset expression.

Measured on LiDAR HD (Cerdagne): 2.2 M points in 14 s.
"""
import logging
import time

from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsTask

from ....core.domain.filter_state import LayerSnapshot
from ....core.domain.layer_kind import LayerKind
from . import cache, pdal_cli
from .snapshots import registry, take_snapshot

logger = logging.getLogger(__name__)


class HeightAboveGroundTask(QgsTask):
    """Add ``HeightAboveGround`` to a point cloud layer; emits ``done(ok, message)``."""

    done = pyqtSignal(bool, str)

    def __init__(self, layer, dem_layer) -> None:
        super().__init__(f"FilterMate: height above {dem_layer.name()}", QgsTask.CanCancel)
        self.layer_id = layer.id()
        self.layer_name = layer.name()
        self.before: LayerSnapshot = take_snapshot(layer, LayerKind.POINT_CLOUD)
        dem_snapshot = registry().get(dem_layer.id())
        self.dem_path = (dem_snapshot.original_source if dem_snapshot else dem_layer.source()).split('|')[0]
        self.crs = layer.crs().authid() or layer.crs().toWkt()
        self.output = ''
        self.message = ''
        self.after = None

    def run(self) -> bool:
        started = time.perf_counter()
        self.message = pdal_cli.copc_unavailable_reason()  # the panel gate may be stale: the pipeline ends with writers.copc
        if self.message:
            return False
        try:
            reader = pdal_cli.reader_for(self.before.base_source)
        except ValueError as exc:
            self.message = str(exc)
            return False
        self.output = cache.new_path(f"{self.layer_name}_hag", '.copc.laz')
        stages = [
            {"type": reader, "filename": self.before.base_source},  # a clip is redone by the filter that follows
            {"type": "filters.hag_dem", "raster": self.dem_path},
            {"type": "writers.copc", "filename": self.output, "forward": "all", "extra_dims": "all", "a_srs": self.crs},
        ]
        ok, self.message = pdal_cli.run_pipeline(stages, is_canceled=self.isCanceled)
        logger.info(f"⏱ [FM5] height above ground for '{self.layer_name}': ok={ok} {time.perf_counter() - started:.1f}s {self.message}")
        return ok

    def finished(self, result: bool) -> None:
        cache.settle([getattr(self, 'output', '')])
        if not result or self.isCanceled() or cache.is_closed():
            # Canceled or plugin unloaded: never swap the source of the layer.
            self.done.emit(False, self.message or 'canceled')
            return
        from qgis.core import QgsProject
        layer = QgsProject.instance().mapLayer(self.layer_id)
        if layer is None:
            self.done.emit(False, 'layer removed')
            return
        from .snapshots import swap_source
        if not swap_source(layer, self.output, 'copc'):
            self.done.emit(False, 'derived point cloud could not be opened')
            return
        if self.before.subset:
            layer.setSubsetString(self.before.subset)
        # The enriched cloud becomes the base of the layer (Unfilter keeps the
        # HeightAboveGround dimension); the pristine source is what unloading
        # and saving the project go back to.
        self.after = LayerSnapshot(self.layer_id, LayerKind.POINT_CLOUD.value, source=layer.source(), provider='copc',
                                   subset=layer.subsetString(), derived=True,
                                   original_source=self.output, original_provider='copc',
                                   enriched_source=self.before.pristine_source,
                                   enriched_provider=self.before.pristine_provider)
        registry().record(self.after, layer)
        layer.triggerRepaint()
        self.done.emit(True, '')

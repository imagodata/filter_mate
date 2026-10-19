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
from qgis.core import QgsGeometry, QgsRectangle, QgsTask

from ....core.domain.filter_state import LayerSnapshot
from ....core.domain.layer_kind import LayerKind
from . import cache, pdal_cli
from .snapshots import registry, take_snapshot

logger = logging.getLogger(__name__)


def _horizontal(crs):
    """Horizontal part of a compound CRS (QGIS >= 3.38); None when it cannot be told apart."""
    getter = getattr(crs, 'horizontalCrs', None)
    if getter is not None:
        horizontal = getter()
        return horizontal if horizontal.isValid() else crs
    wkt = crs.toWkt().lstrip().upper()
    return None if wkt.startswith(('COMPD_CS', 'COMPOUNDCRS')) else crs


def _same_crs(a, b) -> bool:
    """QGIS equality, or the same definition under other names (GDAL); True when GDAL cannot tell."""
    if a == b:
        return True
    try:
        from osgeo import osr
        first, second = osr.SpatialReference(), osr.SpatialReference()
        if first.ImportFromWkt(a.toWkt()) != 0 or second.ImportFromWkt(b.toWkt()) != 0:
            return True
        for srs in (first, second):
            if hasattr(srs, 'DemoteTo2D'):  # GDAL >= 3.6: 3D (EPSG:4979) and 2D (EPSG:4326) share X / Y
                srs.DemoteTo2D(None)
        if first.IsSame(second):
            return True
        if first.IsGeographic() and second.IsGeographic():  # older GDAL: the same datum is enough
            return first.GetAttrValue('DATUM') == second.GetAttrValue('DATUM')
        return False
    except Exception:  # GDAL exceptions turned on by another plugin
        return True


def crs_mismatch(cloud_crs, dem_crs) -> str:
    """Why the DTM cannot be sampled at the point X / Y ('' when it can, or cannot be told).

    ``filters.hag_dem`` reads the raster at the coordinates of the points
    without reprojecting: the horizontal CRS must be the same. A vertical
    part (LiDAR HD: Lambert-93 + NGF-IGN69) does not matter.
    """
    if not cloud_crs.isValid() or not dem_crs.isValid():
        return ''
    cloud, dem = _horizontal(cloud_crs), _horizontal(dem_crs)
    if cloud is None or dem is None or _same_crs(cloud, dem):
        return ''
    return (f"the DTM is in {dem.authid() or dem.description()} and the point cloud in "
            f"{cloud.authid() or cloud.description()}: reproject the DTM to the point cloud CRS first")


class HeightAboveGroundTask(QgsTask):
    """Add ``HeightAboveGround`` to a point cloud layer; emits ``done(ok, message)``."""

    done = pyqtSignal(bool, str)

    def __init__(self, layer, dem_layer, zone=None) -> None:
        super().__init__(f"FilterMate: height above {dem_layer.name()}", QgsTask.Flag.CanCancel)
        self.layer_id = layer.id()
        self.layer_name = layer.name()
        self.before: LayerSnapshot = take_snapshot(layer, LayerKind.POINT_CLOUD)
        dem_snapshot = registry().get(dem_layer.id())
        self.dem_path = (dem_snapshot.original_source if dem_snapshot else dem_layer.source()).split('|')[0]
        self.crs = pdal_cli.srs_for(layer.crs())
        self.crs_error = crs_mismatch(layer.crs(), dem_layer.crs())
        # Capture metadata only. The worker reads points inside the DTM and
        # the current kept area, never the whole remote octree.
        self.extent = QgsRectangle(layer.extent()).intersect(dem_layer.extent())
        self.polygon = self.before.geometry_wkt
        if pdal_cli.is_remote_source(self.before.base_source) and not self.polygon and (zone is None or zone.isEmpty()):
            from .target_appliers import translate
            self.crs_error = self.crs_error or translate('HeightAboveGround',
                                                       'Draw a useful selection zone before computing height above ground remotely')
        if zone is not None and not zone.isEmpty():
            geometry = QgsGeometry(zone)
            if self.polygon:
                geometry = geometry.intersection(QgsGeometry.fromWkt(self.polygon))
            self.polygon = geometry.asWkt()
            self.extent = self.extent.intersect(geometry.boundingBox())
        if self.polygon:
            self.extent = self.extent.intersect(QgsGeometry.fromWkt(self.polygon).boundingBox())
        self._bounded = bool(zone is not None or self.before.geometry_wkt or self.extent != layer.extent())
        self.output = ''
        self.message = ''
        self.after = None

    def run(self) -> bool:
        from .target_appliers import translate
        started = time.perf_counter()
        # The panel gate may be stale: the pipeline ends with writers.copc.
        self.message = self.crs_error or pdal_cli.copc_unavailable_reason()
        if self.message:
            return False
        try:
            if self.extent.isEmpty():
                self.message = translate('HeightAboveGround', 'The DTM and point cloud have no common useful extent')
                return False
            bounds = (self.extent.xMinimum(), self.extent.yMinimum(), self.extent.xMaximum(), self.extent.yMaximum())
            if self.polygon:
                from .gdal_warp import polygonal_wkt
                self.polygon = polygonal_wkt(self.polygon)
                if not self.polygon:
                    self.message = translate('HeightAboveGround', 'The useful selection has no polygon area')
                    return False
            stages = pdal_cli.read_stages(self.before.base_source, bounds, self.polygon or None)
        except ValueError as exc:
            self.message = str(exc)
            return False
        self.output = cache.new_path(f"{self.layer_name}_hag", '.copc.laz')
        stages += [
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
                                   enriched_provider=self.before.pristine_provider,
                                   geometry_wkt=(self.polygon or QgsGeometry.fromRect(self.extent).asWkt()) if self._bounded else '',
                                   bounded_enrichment=self._bounded)
        registry().record(self.after, layer)
        layer.triggerRepaint()
        from .target_appliers import translate
        self.done.emit(True, translate('HeightAboveGround',
                                      'Height above ground covers the useful area only; Unfilter restores the original cloud') if self._bounded else '')

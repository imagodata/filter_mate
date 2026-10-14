# -*- coding: utf-8 -*-
"""
Source side of a cross filter: turn the EXPLORING selection of the current
layer into a source geometry, and filter the source layer itself.

* :class:`VectorSourceJob` - geometries of the selected features.
* :class:`RasterSourceJob` - polygons of the selected pixels; the raster
  itself is then switched to a virtual raster keeping those pixels only.
* :class:`PointCloudSourceJob` - footprint of the points kept by the
  selection, which is applied as the layer's subset string beforehand.

Same threading rules as the target jobs: ``prepare`` (constructor) on the
main thread, ``compute`` in the task, ``apply`` on the main thread.
"""
import logging
import time
from typing import Iterable, List, Optional

from qgis.core import QgsCoordinateReferenceSystem, QgsDataProvider, QgsGeometry, QgsRectangle

from ....core.domain.filter_state import LayerSnapshot
from ....core.domain.layer_kind import LayerKind
from ....core.domain.raster_filter_criteria import RasterSelection, RasterSelectionMode
from .geometry_tools import buffer_geometry, union_geometries
from .snapshots import registry, take_snapshot

logger = logging.getLogger(__name__)


class SourceJob:
    kind = LayerKind.OTHER

    def __init__(self, layer) -> None:
        self.layer_id = layer.id()
        self.layer_name = layer.name()
        self.crs = QgsCoordinateReferenceSystem(layer.crs())
        self.before: LayerSnapshot = take_snapshot(layer, self.kind)
        self.geometry = QgsGeometry()
        self.message = ''
        self.elapsed = 0.0
        self.details: dict = {}

    def compute(self, request, is_canceled) -> QgsGeometry:
        """Return the buffered source geometry (layer CRS)."""
        started = time.perf_counter()
        raw = self._raw_geometry(is_canceled)
        self.geometry = buffer_geometry(raw, request.buffer_value, request.buffer_segments, request.buffer_type)
        self.elapsed = time.perf_counter() - started
        return self.geometry

    def _raw_geometry(self, is_canceled) -> QgsGeometry:
        raise NotImplementedError

    def apply(self, layer) -> Optional[LayerSnapshot]:
        """Filter the source layer itself (main thread); None when unchanged."""
        return None


class VectorSourceJob(SourceJob):
    """Selected features of a vector source (geometries read on the main thread)."""

    kind = LayerKind.VECTOR

    def __init__(self, layer, features: Iterable) -> None:
        super().__init__(layer)
        self._geometries: List[QgsGeometry] = []
        for feature in features or []:
            try:
                geometry = feature.geometry()
            except AttributeError:
                geometry = feature if isinstance(feature, QgsGeometry) else None
            if geometry is not None and not geometry.isEmpty():
                self._geometries.append(QgsGeometry(geometry))
        self.details['features'] = len(self._geometries)

    def _raw_geometry(self, is_canceled) -> QgsGeometry:
        return union_geometries(self._geometries)


class RasterSourceJob(SourceJob):
    """Pixels kept by a :class:`RasterSelection` of a raster source."""

    kind = LayerKind.RASTER

    def __init__(self, layer, selection: RasterSelection, max_pixels: int = 4000000, filter_source: bool = True) -> None:
        super().__init__(layer)
        from .raster_adapter import selection_virtual_layer
        self.selection = selection
        self._max_pixels = max_pixels
        self._filter_source = filter_source
        self._extent = QgsRectangle(layer.extent())
        self._width, self._height = layer.width(), layer.height()
        self._crs_wkt = layer.crs().toWkt()
        self._virtual = None
        if selection.mode is RasterSelectionMode.EXPRESSION:
            self._virtual = selection_virtual_layer(layer, selection)
            provider = self._virtual.dataProvider() if self._virtual is not None else None
        else:
            # Read the original pixels, not a previously masked derived source.
            base = self._base_layer(layer)
            provider = base.dataProvider() if base is not None else layer.dataProvider()
        self._provider = provider.clone() if provider is not None else None
        self._derived_uri = ''
        self._nodata = None

    def _base_layer(self, layer):
        if not self.before.derived:
            return layer
        from qgis.core import QgsRasterLayer
        base = QgsRasterLayer(self.before.base_source, f"{self.layer_name}_base", self.before.base_provider)
        self._base_keepalive = base
        return base if base.isValid() else layer

    def _raw_geometry(self, is_canceled) -> QgsGeometry:
        from .raster_adapter import selection_geometry
        if self._provider is None:
            self.message = 'raster provider unavailable'
            return QgsGeometry()
        result = selection_geometry(self._provider, self.selection, self._extent, self._width, self._height,
                                    self._crs_wkt, max_pixels=self._max_pixels)
        self.details.update(kept_pixels=result.kept_pixels, total_pixels=result.total_pixels, cell_size=result.cell_size)
        return result.geometry

    def apply(self, layer) -> Optional[LayerSnapshot]:
        if not self._filter_source or self.selection.mode is RasterSelectionMode.EXPRESSION and self._virtual is None:
            return None
        from .raster_adapter import selection_virtual_uri, set_user_nodata
        nodata = -9999.0
        try:
            provider = layer.dataProvider()
            if provider.sourceHasNoDataValue(self.selection.band):
                nodata = float(provider.sourceNoDataValue(self.selection.band))
        except Exception:
            pass
        uri, nodata = selection_virtual_uri(self.before.base_source, self.before.base_provider, layer, self.selection, nodata)
        layer.setDataSource(uri, layer.name(), 'virtualraster', QgsDataProvider.ProviderOptions(), False)
        if not layer.isValid():
            self.message = 'virtual raster of the selection could not be opened'
            return None
        set_user_nodata(layer, nodata)
        after = LayerSnapshot(self.layer_id, self.kind.value, source=layer.source(), provider='virtualraster',
                              derived=True, original_source=self.before.base_source,
                              original_provider=self.before.base_provider)
        registry().record(after)
        layer.triggerRepaint()
        return after


class PointCloudSourceJob(SourceJob):
    """Points kept by the selection (already applied as the layer subset)."""

    kind = LayerKind.POINT_CLOUD

    def __init__(self, layer, resolution: float = 2.0, before: Optional[LayerSnapshot] = None) -> None:
        super().__init__(layer)
        if before is not None:
            # Snapshot taken before the controller applied the selection subset.
            self.before = before
        self._layer = layer
        self._resolution = resolution

    def _raw_geometry(self, is_canceled) -> QgsGeometry:
        from .point_cloud_footprint import footprint_geometry
        result = footprint_geometry(self._layer, self._resolution)
        self.details.update(points_read=result.points_read, cell_size=result.cell_size)
        return result.geometry

    def apply(self, layer) -> Optional[LayerSnapshot]:
        after = take_snapshot(layer, self.kind)
        return None if after.same_state(self.before) else after

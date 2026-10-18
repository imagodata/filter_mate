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

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransformContext, QgsGeometry, QgsRectangle

from ....core.domain.filter_state import LayerSnapshot
from ....core.domain.layer_kind import LayerKind
from ....core.domain.raster_filter_criteria import RasterSelection, RasterSelectionMode
from .geometry_tools import WHOLE_SOURCE_METHODS, buffer_geometry, make_valid, transform_geometry, union_geometries
from .snapshots import registry, swap_source, take_snapshot

logger = logging.getLogger(__name__)


class SourceJob:
    kind = LayerKind.OTHER

    def __init__(self, layer) -> None:
        self.layer_id = layer.id()
        self.layer_name = layer.name()
        self.crs = QgsCoordinateReferenceSystem(layer.crs())
        self.before: LayerSnapshot = take_snapshot(layer, self.kind)
        self.geometry = QgsGeometry()
        self.raw_geometry = QgsGeometry()
        self.message = ''
        self.elapsed = 0.0
        self.details: dict = {}

    def compute(self, request, is_canceled) -> QgsGeometry:
        """Return the buffered source geometry (layer CRS)."""
        started = time.perf_counter()
        raw = self._raw_geometry(is_canceled)
        self.raw_geometry = raw
        self._computed = True
        self.geometry = self._buffer(raw, request)
        self.elapsed = time.perf_counter() - started
        return self.geometry

    def _buffer(self, raw: QgsGeometry, request, around: Optional[QgsGeometry] = None) -> QgsGeometry:
        """Buffer in metres like the vector engine, even for a geographic source CRS.

        ``around``: geometry whose centroid picks the UTM zone (default ``raw``).
        """
        if not request.buffer_value or raw.isEmpty() or not self.crs.isGeographic():
            return buffer_geometry(raw, request.buffer_value, request.buffer_segments, request.buffer_type)
        center = (around if around is not None and not around.isEmpty() else raw).centroid().asPoint()
        zone = min(60, max(1, int((center.x() + 180.0) / 6.0) + 1))
        metric = QgsCoordinateReferenceSystem(f"EPSG:{(32600 if center.y() >= 0 else 32700) + zone}")
        context = QgsCoordinateTransformContext()
        projected = transform_geometry(raw, self.crs, metric, context)
        buffered = buffer_geometry(projected, request.buffer_value, request.buffer_segments, request.buffer_type)
        return transform_geometry(buffered, metric, self.crs, context)

    def _raw_geometry(self, is_canceled) -> QgsGeometry:
        raise NotImplementedError

    _QGIS_HANDLES = ('_layer', '_provider', '_virtual', '_base_keepalive')

    def release(self) -> None:
        """Drop the QGIS objects owned by the job (see TargetJob.release)."""
        for name in self._QGIS_HANDLES:
            if hasattr(self, name):
                setattr(self, name, None)

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

    def parts(self, request) -> Optional[List[QgsGeometry]]:
        """The buffered selected features, for the vector targets (after :meth:`compute`); None when the union does.

        Intersect and Disjoint are tested against the union; the other
        predicates hold when ONE selected feature satisfies them
        (native:selectbylocation), not their union: a parcel containing one
        of three selected buildings is kept. A buffer can erase every
        feature: an empty list then matches nothing.
        """
        if len(self._geometries) < 2 or all(m in WHOLE_SOURCE_METHODS for m in request.methods):
            return None
        parts = (make_valid(self._buffer(g, request, around=self.raw_geometry)) for g in self._geometries)
        return [part for part in parts if not part.isEmpty()]

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
        self._band_count = layer.bandCount()
        if selection.mode is RasterSelectionMode.EXPRESSION:
            self._virtual = selection_virtual_layer(layer, selection, self.before.base_source, self.before.base_provider)
            provider = self._virtual.dataProvider() if self._virtual is not None else None
        else:
            # Read the original pixels, not a previously masked derived source.
            base = self._base_layer(layer)
            provider = base.dataProvider() if base is not None else layer.dataProvider()
        self._provider = provider.clone() if provider is not None else None
        self._object_providers = {}  # expression -> cloned provider of its virtual raster (object detection)
        if selection.seeds:
            from .raster_adapter import object_virtual_layers
            self._object_virtuals = object_virtual_layers(layer, selection, self.before.base_source, self.before.base_provider)
            self._object_providers = {expression: virtual.dataProvider().clone()
                                      for expression, virtual in self._object_virtuals.items() if virtual is not None}
            if any(c.mode is not RasterSelectionMode.EXPRESSION for c in selection.objects):
                base = self._base_layer(layer)
                self._object_base = (base.dataProvider() if base is not None else layer.dataProvider()).clone()
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
        if is_canceled():
            self.message = 'canceled'
            return QgsGeometry()
        result = selection_geometry(self._provider, self.selection, self._extent, self._width, self._height,
                                    self._crs_wkt, max_pixels=self._max_pixels, provider_for=self._object_provider)
        if is_canceled():  # the polygonization cannot be interrupted: its result is dropped
            self.message = 'canceled'
            return QgsGeometry()
        self.details.update(kept_pixels=result.kept_pixels, total_pixels=result.total_pixels, cell_size=result.cell_size)
        return result.geometry

    def _object_provider(self, criterion):
        """Provider an object of the selection is read from: its own virtual raster for an expression."""
        if criterion.mode is RasterSelectionMode.EXPRESSION:
            return self._object_providers.get(criterion.expression)
        return getattr(self, '_object_base', None) or self._provider

    def apply(self, layer) -> Optional[LayerSnapshot]:
        if not self._filter_source or (self.selection.mode is RasterSelectionMode.EXPRESSION and self._virtual is None):
            return None
        if (self._band_count > 1 or self.selection.mode is RasterSelectionMode.EXPRESSION
                or self.selection.derivative.is_terrain or self.selection.seeds):
            # Multiband (RGB...), expression, terrain derivative or detected objects (the
            # raster calculator has neither a slope nor a connected patch): keep every
            # band, mask outside the selected area with a clipped VRT (a virtual raster has one band).
            return self._apply_clip(layer)
        from .raster_adapter import selection_virtual_uri, set_user_nodata
        nodata = -9999.0
        base = self._base_layer(layer)
        try:
            provider = base.dataProvider()
            if provider.sourceHasNoDataValue(self.selection.band):
                nodata = float(provider.sourceNoDataValue(self.selection.band))
        except Exception as exc:
            logger.debug(f"[FM5] source NoData value unreadable: {exc}")
        uri, nodata = selection_virtual_uri(self.before.base_source, self.before.base_provider, base, self.selection, nodata)
        if not swap_source(layer, uri, 'virtualraster'):
            self.message = 'virtual raster of the selection could not be opened'
            return None
        if nodata is not None:
            set_user_nodata(layer, nodata)
        return self._record(layer, 'virtualraster', nodata=nodata)

    def _apply_clip(self, layer) -> Optional[LayerSnapshot]:
        from .target_appliers import RasterTargetJob
        from ....core.domain.cross_filter import CrossFilterRequest, TargetSpec
        if not getattr(self, '_computed', False) and self._provider is not None:
            # No target: the task never ran compute(), the selection is read here (main thread).
            self.raw_geometry = self._raw_geometry(lambda: False)
        if self.raw_geometry.isEmpty():
            self.message = self.message or 'no pixel is selected: the source is left as it is'
            return None
        if self.before.base_provider != 'gdal':
            self.message = (f"the source cannot be masked: its provider ({self.before.base_provider}) is not a GDAL file; "
                            "its pixels are still used as the selection")
            return None
        from . import cache
        job = RasterTargetJob(layer, None)
        request = CrossFilterRequest(self.layer_id, LayerKind.RASTER, targets=(TargetSpec(self.layer_id, LayerKind.RASTER),))
        try:
            job.compute(self.raw_geometry, self.crs, QgsCoordinateTransformContext(), request, lambda: False)
            return job.apply(layer) if job.outcome.success else None
        finally:
            # Not a target of the task: its VRT is released for the cache cleaner here.
            cache.settle(job.outputs)

    def _record(self, layer, provider: str, nodata=None) -> LayerSnapshot:
        import json
        after = LayerSnapshot(self.layer_id, self.kind.value, source=layer.source(), provider=provider,
                              derived=True, original_source=self.before.base_source,
                              original_provider=self.before.base_provider, nodata=nodata,
                              selection=json.dumps(self.selection.to_dict()),
                              enriched_source=self.before.enriched_source,
                              enriched_provider=self.before.enriched_provider)
        registry().record(after, layer)
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
        from .point_cloud_footprint import layer_resolution
        self._resolution = layer_resolution(resolution, self.crs)
        self._layer = None
        self._error = ''
        if layer.providerType() == 'vpc':
            self._error = "a virtual point cloud (VPC) cannot be a source: its points are read tile by tile"
            return
        # The task reads its own copy of the layer (same source, same subset):
        # the live layer may change (preview, removal) while the task runs, and
        # it is never read from the task thread.
        from .point_cloud_footprint import index_ready, open_point_cloud
        copy = open_point_cloud(layer.source(), f"{layer.name()}_footprint", layer.providerType())
        subset = layer.subsetString()
        # Spelled in parentheses: QGIS caches the decoded blocks under the
        # subset text, and the statistics task of the project layer may have
        # cached unfiltered blocks under its spelling (see open_point_cloud).
        # The line break keeps a final "--" comment out of the parenthesis.
        self._subset = f"({subset}\n)" if subset else ''
        if not copy.isValid() or not index_ready(copy):
            self._error = "the point cloud could not be read (not indexed yet?)"
        elif subset and not copy.setSubsetString(self._subset):
            self._error = f"the selection was rejected by the point cloud: {subset[:120]}"
        else:
            self._layer = copy

    def _raw_geometry(self, is_canceled) -> QgsGeometry:
        from .point_cloud_footprint import footprint_geometry, selection_check
        if self._error:
            self.message = self._error
            return QgsGeometry()
        try:
            result = footprint_geometry(self._layer, self._resolution, is_canceled=is_canceled,
                                        check=selection_check(self._subset))
        except RuntimeError as exc:
            self.message = str(exc)
            return QgsGeometry()
        if is_canceled():
            self.message = 'canceled'
            return QgsGeometry()
        self.details.update(points_read=result.points_read, cell_size=result.cell_size)
        if result.truncated:
            self.details['truncated'] = True
            logger.warning(f"[FM5] footprint of '{self.layer_name}' read the maximum of {result.points_read} points: "
                           f"it may miss areas, use a coarser resolution")
        if result.coarse:
            # Wider than the resolution asked for: the footprint covers more than the points.
            self.details['coarse'] = True
        return result.geometry

    def apply(self, layer) -> Optional[LayerSnapshot]:
        after = take_snapshot(layer, self.kind)
        return None if after.same_state(self.before) else after


class FixedGeometrySourceJob(SourceJob):
    """A stored clip geometry (project reopened): no selection to read, nothing to filter on the source."""

    kind = LayerKind.OTHER

    def __init__(self, layer, geometry_wkt: str) -> None:
        super().__init__(layer)
        self._wkt = geometry_wkt

    def _raw_geometry(self, is_canceled) -> QgsGeometry:
        return QgsGeometry.fromWkt(self._wkt)


def apply_stored_selection(layer, snapshot: LayerSnapshot) -> Optional[LayerSnapshot]:
    """Rebuild the virtual raster of a stored raster source selection (main thread)."""
    import json
    from .raster_adapter import selection_virtual_uri
    try:
        selection = RasterSelection.from_dict(json.loads(snapshot.selection))
    except (TypeError, ValueError, KeyError):
        return None
    if selection.seeds:
        return None  # a detected object is a clip of the source, not a formula (never stored as one)
    uri, _ = selection_virtual_uri(snapshot.base_source, snapshot.base_provider, layer, selection)
    if not swap_source(layer, uri, 'virtualraster'):
        return None
    after = LayerSnapshot(layer.id(), LayerKind.RASTER.value, source=layer.source(), provider='virtualraster',
                          derived=True, original_source=snapshot.base_source, original_provider=snapshot.base_provider,
                          selection=snapshot.selection)
    registry().record(after, layer)
    layer.triggerRepaint()
    return after

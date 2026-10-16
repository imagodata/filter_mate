# -*- coding: utf-8 -*-
"""
Apply a source geometry to target layers of every kind.

Each job follows the QgsTask threading rules:

* ``prepare`` runs on the main thread (reads the layer, captures a snapshot,
  builds thread-safe feature sources);
* ``compute`` runs in the task thread (iterates features, writes the derived
  VRT or point cloud);
* ``apply`` runs on the main thread again (``setSubsetString`` /
  ``setDataSource``) and returns the ``after`` snapshot for the history.

Target semantics (see ``core.domain.cross_filter``):

* vector: features for which ``target.<predicate>(source)`` holds, optional
  minimum coverage for polygons, combined with the previous subset;
* raster: pixels inside (or outside, for Disjoint) the source geometry stay,
  the others become NoData, through a clipped VRT;
* point cloud: points inside (or outside) the source geometry stay, through a
  derived COPC file written by PDAL (exact) or an X/Y expression (bbox mode).
"""
import logging
import math
import os
import time
from typing import Callable, List, Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
    QgsVectorLayerFeatureSource,
    Qgis,
)

from ....core.domain.cross_filter import (
    CoverageSide,
    CrossFilterOutcome,
    build_in_expression,
    combine_subset,
    coverage_ratio_ok,
)
from ....core.domain.filter_state import LayerSnapshot
from ....core.domain.layer_kind import LayerKind
from . import cache
from .gdal_warp import gdal_warp, polygonal_wkt
from .geometry_tools import (
    WHOLE_SOURCE_METHODS,
    SourceParts,
    make_valid,
    prepared_engine,
    target_matches,
    transform_geometry,
)
from .snapshots import registry, take_snapshot

logger = logging.getLogger(__name__)

CanceledFn = Callable[[], bool]
MAX_BBOX_TERMS = 50
NO_AREA = "the source geometry has no area (lines or points only): add a buffer"


def _checked(result: QgsGeometry, operation: str) -> QgsGeometry:
    """Valid result of a GEOS operation; a null result is an error, never "nothing kept".

    An empty result (the areas do not meet) is a valid empty geometry, kept
    as it is; GEOS failing (invalid input) gives a null one, which must not
    mask everything.
    """
    if result is None or result.isNull():
        error = result.lastError() if result is not None and hasattr(result, 'lastError') else ''
        raise RuntimeError(f"{operation} of the source geometry failed{': ' + error if error else ''}")
    return result if result.isEmpty() else make_valid(result)


def _nothing_kept(extent: QgsRectangle) -> QgsGeometry:
    """Area kept when nothing is: a tiny polygon outside ``extent``.

    Stored like any kept area, so that the state survives a project reload
    and combines like an empty area (no pixel, no point lies there).
    """
    return QgsGeometry.fromRect(QgsRectangle(extent.xMinimum() - 2, extent.yMinimum() - 2,
                                             extent.xMinimum() - 1, extent.yMinimum() - 1))


def _has_area(geometry: QgsGeometry) -> bool:
    """True when ``geometry`` has a polygon part (pixels and points are kept inside areas only)."""
    return polygonal_wkt(geometry.asWkt()) is not None


def _kept_area(geometry: QgsGeometry) -> Optional[str]:
    """WKT of the polygon parts of a kept area; None when nothing is kept.

    Two kept areas that touch meet in a line: no pixel, no point is kept
    there, and only polygons are stored (overlays of collections with lines
    fail on older GEOS).
    """
    if geometry is None or geometry.isEmpty():
        return None
    return polygonal_wkt(geometry.asWkt())


def _combine_geometry(previous_wkt: str, previous_side: str, new: QgsGeometry, side: CoverageSide,
                      operator: Optional[str]) -> QgsGeometry:
    """Combine the kept area of an already derived target with a new kept area.

    Both geometries are areas KEPT (outside already subtracted), so they
    combine whatever their side.
    """
    if not previous_wkt or not operator:
        return new
    previous = QgsGeometry.fromWkt(previous_wkt)
    if previous.isEmpty():
        return new
    op = operator.upper()
    if new is None or new.isEmpty():
        # Nothing new kept (outside of a source covering the whole layer):
        # AND keeps nothing, OR and AND NOT keep the previous area.
        return previous if op in ('OR', 'AND NOT') else new
    if op == 'AND':
        return _checked(previous.intersection(new), 'intersection')
    if op == 'OR':
        return _checked(previous.combine(new), 'union')
    if op == 'AND NOT':
        return _checked(previous.difference(new), 'difference')
    return new


def _simplified_for_cutline(geometry: QgsGeometry, tolerance: float, max_vertices: int = 20000) -> QgsGeometry:
    """Simplify a heavy cutline (vectorized selection) to keep the VRT fast to render."""
    try:
        if tolerance > 0 and geometry.constGet().nCoordinates() > max_vertices:
            simplified = geometry.simplify(tolerance)
            if simplified is not None and not simplified.isEmpty():
                return make_valid(simplified)
    except Exception as exc:
        logger.debug(f"[FM5] geometry not simplified: {exc}")
    return geometry


def _base_raster_layer(snapshot: LayerSnapshot, fallback):
    """The original raster of a derived target (its NoData, type and extent are the truth)."""
    if not snapshot.derived:
        return fallback
    from qgis.core import QgsRasterLayer
    base = QgsRasterLayer(snapshot.base_source, 'fm5_base', snapshot.base_provider)
    return base if base.isValid() else fallback


class TargetJob:
    """Common state of a target job."""

    kind = LayerKind.OTHER

    def __init__(self, layer, operator: Optional[str]) -> None:
        self.layer_id = layer.id()
        self.layer_name = layer.name()
        self.crs = QgsCoordinateReferenceSystem(layer.crs())
        self.operator = operator
        self.before: LayerSnapshot = take_snapshot(layer, self.kind)
        self.outcome = CrossFilterOutcome(self.layer_id, self.kind, False)
        self.outputs: List[str] = []  # cache files written, settled once applied
        self._started = 0.0

    def _new_path(self, suffix: str) -> str:
        """A cache file for this job, protected from the cache cleaner until the task is applied."""
        path = cache.new_path(self.layer_name, suffix)
        self.outputs.append(path)
        return path

    # Attributes holding QGIS objects owned by Python (layer copies, feature
    # sources, exporters): released once the task is over, never left for the
    # interpreter shutdown (QGIS 3.44 crashed on exit when they outlived it).
    _QGIS_HANDLES = ('_source', '_unfiltered', '_base_layer', '_exporter', '_base_keepalive')
    # QgsFeedback canceled with the task (set by CrossFilterTask), for the
    # QGIS calls that cannot poll ``is_canceled``.
    feedback = None

    def release(self) -> None:
        for name in self._QGIS_HANDLES:
            if hasattr(self, name):
                setattr(self, name, None)

    def compute(self, source_geometry: QgsGeometry, source_crs: QgsCoordinateReferenceSystem,
                context: QgsCoordinateTransformContext, request, is_canceled: CanceledFn) -> None:
        raise NotImplementedError

    def apply(self, layer) -> Optional[LayerSnapshot]:
        raise NotImplementedError

    def _target_geometry(self, source_geometry, source_crs, context) -> QgsGeometry:
        # A reprojection can make a valid polygon invalid (GEOS operations then fail).
        return make_valid(transform_geometry(source_geometry, source_crs, self.crs, context))


# --- vector -----------------------------------------------------------------

def _is_polygon_layer(layer) -> bool:
    geometry_type = layer.geometryType()
    scoped = getattr(Qgis, 'GeometryType', None)
    if scoped is not None and hasattr(scoped, 'Polygon'):
        return geometry_type == scoped.Polygon
    try:
        return int(geometry_type) == 2
    except (TypeError, ValueError):
        return False


class VectorTargetJob(TargetJob):
    """Keep the features of a vector target that satisfy the predicates."""

    kind = LayerKind.VECTOR
    # The selected features of a vector source, buffered (set by CrossFilterTask).
    source_parts: Optional[List[QgsGeometry]] = None

    def __init__(self, layer: QgsVectorLayer, operator: Optional[str]) -> None:
        super().__init__(layer, operator)
        self._error = ''
        if self.before.subset and (operator or '').upper() not in ('AND', 'AND NOT'):
            # Replace (no operator) and OR: the result does not depend on the
            # features the previous subset hides, they are tested too.
            self._source = self._unfiltered_source(layer)
        else:
            self._source = QgsVectorLayerFeatureSource(layer)
        self._is_polygon = _is_polygon_layer(layer)
        self._pk, self._raw_pk = self._primary_key(layer)
        self._expression = ''

    def _unfiltered_source(self, layer: QgsVectorLayer):
        """Feature source of every feature of ``layer``, its subset left out (main thread)."""
        if layer.providerType() == 'memory':
            # A memory layer opened again is a new, empty one: the source is
            # taken while its provider shows every feature, signals blocked so
            # that nothing sees the subset go and come back.
            provider = layer.dataProvider()
            subset = provider.subsetString()
            provider.blockSignals(True)
            try:
                provider.setSubsetString('')
                return QgsVectorLayerFeatureSource(layer)
            finally:
                provider.setSubsetString(subset)
                provider.blockSignals(False)
        options = QgsVectorLayer.LayerOptions(QgsProject.instance().transformContext())
        options.loadDefaultStyle = False
        options.skipCrsValidation = True  # never a "which CRS?" prompt for a private copy
        unfiltered = QgsVectorLayer(layer.source(), f"{layer.name()}_all", layer.providerType(), options)
        if not unfiltered.isValid():
            self._error = "the layer could not be read without its current filter"
            return None
        unfiltered.setSubsetString('')
        self._unfiltered = unfiltered
        return QgsVectorLayerFeatureSource(unfiltered)

    @staticmethod
    def _primary_key(layer: QgsVectorLayer):
        try:
            from ....core.filter.source_filter_builder import get_primary_key_field
            pk = get_primary_key_field(layer)
        except Exception:
            pk = None
        if pk:
            return pk, False
        if layer.providerType() == 'ogr':
            return 'FID', True
        return '$id', True

    def compute(self, source_geometry, source_crs, context, request, is_canceled) -> None:
        self._started = time.perf_counter()
        if self._error:
            self.outcome.message = self._error
            return
        geometry = self._target_geometry(source_geometry, source_crs, context)
        methods = request.methods
        # Intersects / disjoint are tested against the union of the source,
        # the other predicates against each selected feature (vector source).
        whole_methods = [m for m in methods if m in WHOLE_SOURCE_METHODS]
        part_methods = [m for m in methods if m not in WHOLE_SOURCE_METHODS]
        parts = None
        if self.source_parts is not None and part_methods:
            parts = SourceParts([self._target_geometry(part, source_crs, context) for part in self.source_parts])
            methods = whole_methods
        needs_all = 'disjoint' in methods
        feature_request = QgsFeatureRequest()
        if not needs_all and not geometry.isEmpty():
            feature_request.setFilterRect(geometry.boundingBox())
        if self._raw_pk:
            feature_request.setNoAttributes()
        else:
            feature_request.setSubsetOfAttributes([self._pk], self._source_fields())
        kept: List = []
        engine = prepared_engine(geometry) if methods and not geometry.isEmpty() else None
        coverage = float(request.coverage_min or 0.0) if self._is_polygon else 0.0
        for feature in self._source.getFeatures(feature_request):
            if is_canceled():
                self.outcome.message = 'canceled'
                return
            target_geometry = feature.geometry()
            if target_geometry is None or target_geometry.isEmpty():
                continue
            if engine is None:
                matched = methods == ['disjoint']
            else:
                matched = target_matches(engine, target_geometry, methods)
            if not matched and parts is not None:
                matched = parts.matches(target_geometry, part_methods)
            if matched and coverage > 0 and 'disjoint' not in request.methods:
                matched = coverage_ratio_ok(target_geometry.area(), target_geometry.intersection(geometry).area(), coverage)
            if matched:
                kept.append(feature.id() if self._raw_pk else feature.attribute(self._pk))
        self._expression = build_in_expression(self._pk, kept, raw_field=self._raw_pk)
        # Release the provider connection held by the feature source before the
        # subset is applied (an open GeoPackage reader made the count fail).
        # The unfiltered copy, a QObject of the main thread, goes in apply().
        self._source = None
        self.outcome.kept_count = len(kept)
        self.outcome.success = True
        self.outcome.elapsed = time.perf_counter() - self._started

    def _source_fields(self):
        try:
            return self._source.fields()
        except AttributeError:
            return QgsProject.instance().mapLayer(self.layer_id).fields()

    def apply(self, layer) -> Optional[LayerSnapshot]:
        self._unfiltered = None  # before the subset is applied, on the main thread
        if not self.outcome.success:
            return None
        subset = combine_subset(self.before.subset, self._expression, self.operator)
        try:
            from ....infrastructure.database.sql_utils import safe_set_subset_string
            ok = safe_set_subset_string(layer, subset)
        except ImportError:
            ok = layer.setSubsetString(subset)
        if not ok:
            self.outcome.success = False
            self.outcome.message = f"subset rejected by the provider: {subset[:200]}"
            return None
        layer.triggerRepaint()
        return take_snapshot(layer, self.kind)


# --- raster -----------------------------------------------------------------

class RasterTargetJob(TargetJob):
    """Set the pixels of a raster target outside (or inside) the source geometry to NoData."""

    kind = LayerKind.RASTER

    def __init__(self, layer, operator: Optional[str]) -> None:
        super().__init__(layer, operator)
        self._base_source = self.before.base_source
        self._base_provider = self.before.base_provider
        base = _base_raster_layer(self.before, layer)
        self._extent = QgsRectangle(base.extent())
        provider = base.dataProvider()
        self._nodata = []
        self._float = True
        self._pixel = 0.0
        try:
            from .raster_adapter import _data_type_name
            types = [_data_type_name(provider.dataType(band)) for band in range(1, base.bandCount() + 1)]
            self._float = all('Float' in name for name in types)
            for band in range(1, base.bandCount() + 1):
                self._nodata.append(float(provider.sourceNoDataValue(band)) if provider.sourceHasNoDataValue(band) else None)
            if base.width():
                self._pixel = self._extent.width() / base.width()
        except Exception as exc:
            logger.debug(f"[FM5] raster target metadata incomplete: {exc}")
        self._derived_path = ''
        self._geometry_wkt = ''
        self._side = CoverageSide.INSIDE

    def compute(self, source_geometry, source_crs, context, request, is_canceled) -> None:
        self._started = time.perf_counter()
        if self._base_provider != 'gdal':
            self.outcome.message = f"raster provider '{self._base_provider}' cannot be clipped (GDAL files only)"
            return
        side = request.side
        if side is CoverageSide.ALL:
            self.outcome.message = 'inside OR outside keeps every pixel: nothing to do'
            return
        if (self.operator or '').upper() in ('AND', 'OR', 'AND NOT') and self.before.derived \
                and self.before.selection and not self.before.geometry_wkt:
            # Filtered as a source (virtual raster of its own pixel selection):
            # there is no kept area to combine with, and the clip of the
            # original raster would silently drop that selection.
            self.outcome.message = ("the layer is filtered by its own pixel selection, which cannot be combined: "
                                    "replace its filter or unfilter it first")
            return
        geometry = self._target_geometry(source_geometry, source_crs, context)
        if side is CoverageSide.INSIDE and not geometry.isEmpty() and not _has_area(geometry):
            self.outcome.message = NO_AREA
            return
        if side is CoverageSide.OUTSIDE:
            geometry = _checked(QgsGeometry.fromRect(self._extent).difference(geometry), 'difference')
        geometry = _combine_geometry(self.before.geometry_wkt if self.before.derived else '', self.before.side,
                                     geometry, side, self.operator)
        self._side = side
        kept = _kept_area(geometry)
        # Nothing kept: clip with a degenerate polygon far outside the extent.
        geometry = QgsGeometry.fromWkt(kept) if kept is not None else _nothing_kept(self._extent)
        self._geometry_wkt = geometry.asWkt()
        cutline = _simplified_for_cutline(geometry, self._pixel * 0.5)
        path = self._new_path('.vrt')
        options = dict(format='VRT', cutlineWKT=cutline.asWkt(), cropToCutline=False)
        if self.crs.isValid():
            # An empty cutlineSRS is an invalid SRS for GDAL >= 3.9: without a
            # CRS the cutline is in the raster's own coordinates.
            options['cutlineSRS'] = self.crs.toWkt()
        if self._nodata and all(value is not None for value in self._nodata):
            options['dstNodata'] = ' '.join(repr(value) for value in self._nodata)
        elif self._float:
            options['dstNodata'] = -9999.0
        else:
            # Integer raster without NoData: an alpha band, never a clipped value.
            options['dstAlpha'] = True
        dataset = gdal_warp(path, self._base_source, **options)
        dataset = None  # noqa: F841 - flush the VRT
        if is_canceled():
            self.outcome.message = 'canceled'
            return
        self._derived_path = path
        self.outcome.success = True
        self.outcome.elapsed = time.perf_counter() - self._started
        self.outcome.details['vrt'] = path

    def apply(self, layer) -> Optional[LayerSnapshot]:
        if not self.outcome.success:
            return None
        from .snapshots import _sync_alpha_band, swap_source
        if not swap_source(layer, self._derived_path, 'gdal'):
            self.outcome.success = False
            self.outcome.message = 'derived VRT could not be opened'
            return None
        _sync_alpha_band(layer)
        after = LayerSnapshot(self.layer_id, self.kind.value, source=layer.source(), provider='gdal', derived=True,
                              original_source=self._base_source, original_provider=self._base_provider,
                              geometry_wkt=self._geometry_wkt, side=self._side.value,
                              enriched_source=self.before.enriched_source, enriched_provider=self.before.enriched_provider)
        registry().record(after, layer)
        layer.triggerRepaint()
        return after


# --- point cloud ------------------------------------------------------------

def _bound(value: float, decimals: int, upper: bool) -> str:
    """``value`` written with ``decimals`` decimals, rounded outwards (a box never loses an edge point)."""
    scale = 10 ** decimals
    rounded = (math.ceil(value * scale) if upper else math.floor(value * scale)) / scale
    return f"{rounded:.{decimals}f}"


def _bbox_expression(geometry: QgsGeometry, outside: bool, geographic: bool = False) -> str:
    parts = [part for part in geometry.asGeometryCollection()] if geometry.isMultipart() else [geometry]
    boxes = [p.boundingBox() for p in parts if p is not None and not p.isEmpty()]
    if len(boxes) > MAX_BBOX_TERMS:
        boxes = [geometry.boundingBox()]
    decimals = 9 if geographic else 3  # 0.001 degree is about 111 m
    terms = [f"(X >= {_bound(b.xMinimum(), decimals, False)} AND X <= {_bound(b.xMaximum(), decimals, True)} "
             f"AND Y >= {_bound(b.yMinimum(), decimals, False)} AND Y <= {_bound(b.yMaximum(), decimals, True)})"
             for b in boxes]
    expression = " OR ".join(terms) if terms else "X < X"
    return f"NOT ({expression})" if outside else expression


class PointCloudTargetJob(TargetJob):
    """Keep the points of a point cloud target inside (or outside) the source geometry."""

    kind = LayerKind.POINT_CLOUD

    def __init__(self, layer, operator: Optional[str], clip_mode: str = 'exact') -> None:
        super().__init__(layer, operator)
        self._base_source = self.before.base_source
        self._base_provider = self.before.base_provider
        self._own_subset = self.before.subset
        self._mode = clip_mode if clip_mode in ('exact', 'bbox') else 'exact'
        self._derived_path = ''
        self._derived_provider = ''
        self._expression = ''
        self._geometry_wkt = ''
        self._side = CoverageSide.INSIDE
        self._extent = QgsRectangle(layer.extent())
        self._unsupported = ''
        if self.before.derived:
            # Outside / empty areas are computed on the ORIGINAL extent: the
            # clip is applied to the original source, not to the derived one.
            from .point_cloud_footprint import open_point_cloud
            base = open_point_cloud(self._base_source, f"{self.layer_name}_base", self._base_provider)
            if base.isValid():
                self._extent = QgsRectangle(base.extent())
        self._extent.grow(1.0)  # header rounding: keep the points on the edge
        self._exporter = None
        if self._mode == 'exact':
            if self._base_provider == 'vpc':
                # Neither PDAL (readers.las / copc / ept) nor the QGIS exporter
                # (no index: it would crash) reads a virtual point cloud.
                self._unsupported = "a virtual point cloud (VPC) cannot be clipped exactly (bbox clip mode only)"
                return
            from . import pdal_cli
            self._use_pdal = pdal_cli.supports_copc() and self._pdal_readable(self._base_source)
            if not self._use_pdal:
                self._prepare_exporter()

    @staticmethod
    def _pdal_readable(path: str) -> bool:
        from . import pdal_cli
        try:
            pdal_cli.reader_for(path)
            return os.path.isfile(path) or path.lower().endswith('ept.json')
        except ValueError:
            return False

    def _prepare_exporter(self) -> None:
        """QgsPointCloudLayerExporter must be prepared on the main thread."""
        from qgis.core import QgsPointCloudLayerExporter
        from .point_cloud_footprint import index_ready, open_point_cloud
        base = open_point_cloud(self._base_source, f"{self.layer_name}_base", self._base_provider)
        if not base.isValid():
            return
        if not index_ready(base):
            # The exporter reads the index without checking it (crash on a null one).
            self._unsupported = "the point cloud has no index yet (LAS file being indexed): try again later"
            return
        self._base_layer = base  # keep alive while the task runs
        exporter = QgsPointCloudLayerExporter(base)
        exporter.setFormat(QgsPointCloudLayerExporter.ExportFormat.Las)
        exporter.setFileName(self._new_path('.laz'))
        exporter.setAllAttributes()
        self._exporter = exporter

    def compute(self, source_geometry, source_crs, context, request, is_canceled) -> None:
        self._started = time.perf_counter()
        side = request.side
        if side is CoverageSide.ALL:
            self.outcome.message = 'inside OR outside keeps every point: nothing to do'
            return
        geometry = self._target_geometry(source_geometry, source_crs, context)
        self._side = side
        if side is CoverageSide.INSIDE and not geometry.isEmpty() and not _has_area(geometry):
            # Same as the raster target: lines or points keep no point at all.
            self.outcome.message = NO_AREA
            return
        if self._mode == 'bbox':
            if geometry.isEmpty():
                self._expression = 'X = X' if side is CoverageSide.OUTSIDE else 'X < X'
            else:
                self._expression = _bbox_expression(geometry, side is CoverageSide.OUTSIDE, self.crs.isGeographic())
            self.outcome.success = True
            self.outcome.elapsed = time.perf_counter() - self._started
            return
        if self._unsupported:
            self.outcome.message = self._unsupported
            return
        # Like the raster target, the stored geometry is the area KEPT (outside
        # = extent minus the source geometry) and the clip always keeps the inside.
        if side is CoverageSide.OUTSIDE:
            geometry = _checked(QgsGeometry.fromRect(self._extent).difference(geometry), 'difference')
        geometry = _combine_geometry(self.before.geometry_wkt if self.before.derived else '', self.before.side,
                                     geometry, side, self.operator)
        # filters.crop takes polygons only: make_valid / an intersection can add lines and points.
        polygon = _kept_area(geometry)
        geometry = QgsGeometry.fromWkt(polygon) if polygon is not None else None
        if geometry is None or not geometry.boundingBox().intersects(self._extent):
            # Nothing kept. Stored, not left empty: an empty state would be
            # dropped from the project and read as "no previous filter" by the next AND.
            polygon, geometry = None, _nothing_kept(self._extent)
        self._geometry_wkt = geometry.asWkt()
        if self._use_pdal:
            self._compute_pdal(polygon, is_canceled)
        else:
            self._compute_exporter(geometry, is_canceled)
        self.outcome.elapsed = time.perf_counter() - self._started

    def _compute_pdal(self, polygon: Optional[str], is_canceled) -> None:
        """Clip with ``polygon`` (WKT), nothing kept when None."""
        from . import pdal_cli
        path = self._new_path('.copc.laz')
        reader = {"type": pdal_cli.reader_for(self._base_source), "filename": self._base_source}
        stages = [reader]
        if polygon is None:
            stages.append({"type": "filters.head", "count": 0})
        else:
            if reader["type"] == 'readers.copc':
                reader["polygon"] = polygon
            stages.append({"type": "filters.crop", "polygon": polygon})
        stages.append({"type": "writers.copc", "filename": path, "forward": "all", "extra_dims": "all",
                       "a_srs": pdal_cli.srs_for(self.crs)})
        ok, message = pdal_cli.run_pipeline(stages, is_canceled=is_canceled)
        if not ok:
            self.outcome.message = f"pdal: {message}"
            return
        self._derived_path, self._derived_provider = path, 'copc'
        self.outcome.success = True
        self.outcome.details['derived'] = path

    def _compute_exporter(self, geometry: QgsGeometry, is_canceled) -> None:
        if self._exporter is None:
            self.outcome.message = self._unsupported or 'point cloud cannot be clipped (no pdal and no exporter)'
            return
        # Nothing kept is a tiny polygon outside the extent here (None would export everything).
        self._exporter.setFilterGeometry(geometry.constGet().clone())
        if self.feedback is not None:
            self._exporter.setFeedback(self.feedback)
        self._exporter.doExport()
        if is_canceled():
            self.outcome.message = 'canceled'
            return
        error = self._exporter.lastError()
        if error:
            self.outcome.message = f"export: {error}"
            return
        self._derived_path, self._derived_provider = self._exporter.fileName(), 'pdal'
        self.outcome.success = True
        self.outcome.details['derived'] = self._derived_path

    def apply(self, layer) -> Optional[LayerSnapshot]:
        if not self.outcome.success:
            return None
        if self._mode == 'bbox':
            subset = combine_subset(self.before.subset, self._expression, self.operator)
            if not layer.setSubsetString(subset):
                self.outcome.success = False
                self.outcome.message = f"point cloud subset rejected: {subset[:200]}"
                return None
            layer.triggerRepaint()
            return take_snapshot(layer, self.kind)
        from .snapshots import swap_source
        if not swap_source(layer, self._derived_path, self._derived_provider):
            self.outcome.success = False
            self.outcome.message = 'derived point cloud could not be opened'
            return None
        if self._own_subset:
            if self._derived_provider == 'pdal':
                try:
                    layer.dataProvider().generateIndex()
                except Exception as exc:
                    logger.debug(f"[FM5] PDAL index not generated: {exc}")
            if not layer.setSubsetString(self._own_subset):
                self.outcome.message = f"the layer's own filter could not be kept: {self._own_subset[:120]}"
                logger.warning(f"[FM5] '{layer.name()}': {self.outcome.message}")
        after = LayerSnapshot(self.layer_id, self.kind.value, source=layer.source(), provider=self._derived_provider,
                              subset=layer.subsetString(), derived=True, original_source=self._base_source,
                              original_provider=self._base_provider, geometry_wkt=self._geometry_wkt,
                              side=self._side.value, enriched_source=self.before.enriched_source,
                              enriched_provider=self.before.enriched_provider)
        registry().record(after, layer)
        layer.triggerRepaint()
        return after


def make_job(layer, kind: LayerKind, operator: Optional[str], point_cloud_clip: str = 'exact') -> Optional[TargetJob]:
    """Build the job for a target layer (main thread)."""
    if kind is LayerKind.VECTOR:
        return VectorTargetJob(layer, operator)
    if kind is LayerKind.RASTER:
        return RasterTargetJob(layer, operator)
    if kind is LayerKind.POINT_CLOUD:
        return PointCloudTargetJob(layer, operator, point_cloud_clip)
    return None

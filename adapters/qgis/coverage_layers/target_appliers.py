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
import os
import time
from typing import Callable, List, Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext,
    QgsDataProvider,
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
from .geometry_tools import make_valid, prepared_engine, target_matches, transform_geometry
from .snapshots import registry, take_snapshot

logger = logging.getLogger(__name__)

CanceledFn = Callable[[], bool]
MAX_BBOX_TERMS = 50


def _combine_geometry(previous_wkt: str, previous_side: str, new: QgsGeometry, side: CoverageSide,
                      operator: Optional[str]) -> QgsGeometry:
    """Combine the clip geometry of an already derived target with a new one."""
    if not previous_wkt or not operator or previous_side != side.value:
        return new
    previous = QgsGeometry.fromWkt(previous_wkt)
    if previous.isEmpty():
        return new
    op = operator.upper()
    if op == 'AND':
        return make_valid(previous.intersection(new))
    if op == 'OR':
        return make_valid(previous.combine(new))
    if op == 'AND NOT':
        return make_valid(previous.difference(new))
    return new


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
        self._started = 0.0

    def compute(self, source_geometry: QgsGeometry, source_crs: QgsCoordinateReferenceSystem,
                context: QgsCoordinateTransformContext, request, is_canceled: CanceledFn) -> None:
        raise NotImplementedError

    def apply(self, layer) -> Optional[LayerSnapshot]:
        raise NotImplementedError

    def _target_geometry(self, source_geometry, source_crs, context) -> QgsGeometry:
        return transform_geometry(source_geometry, source_crs, self.crs, context)


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

    def __init__(self, layer: QgsVectorLayer, operator: Optional[str]) -> None:
        super().__init__(layer, operator)
        self._source = QgsVectorLayerFeatureSource(layer)
        self._is_polygon = _is_polygon_layer(layer)
        self._pk, self._raw_pk = self._primary_key(layer)
        self._expression = ''

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
        geometry = self._target_geometry(source_geometry, source_crs, context)
        methods = request.methods
        needs_all = 'disjoint' in methods
        feature_request = QgsFeatureRequest()
        if not needs_all and not geometry.isEmpty():
            feature_request.setFilterRect(geometry.boundingBox())
        if self._raw_pk:
            feature_request.setNoAttributes()
        else:
            feature_request.setSubsetOfAttributes([self._pk], self._source_fields())
        kept: List = []
        engine = prepared_engine(geometry) if not geometry.isEmpty() else None
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
            if matched and coverage > 0 and 'disjoint' not in methods:
                matched = coverage_ratio_ok(target_geometry.area(), target_geometry.intersection(geometry).area(), coverage)
            if matched:
                kept.append(feature.id() if self._raw_pk else feature.attribute(self._pk))
        self._expression = build_in_expression(self._pk, kept, raw_field=self._raw_pk)
        # Release the provider connection held by the feature source before the
        # subset is applied (an open GeoPackage reader made the count fail).
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
        self._extent = QgsRectangle(layer.extent())
        provider = layer.dataProvider()
        self._nodata = None
        try:
            if provider.sourceHasNoDataValue(1):
                self._nodata = float(provider.sourceNoDataValue(1))
        except Exception:
            self._nodata = None
        try:
            from .raster_adapter import _data_type_name
            self._float = 'Float' in _data_type_name(provider.dataType(1))
        except Exception:
            self._float = True
        self._derived_path = ''
        self._geometry_wkt = ''
        self._side = CoverageSide.INSIDE

    def compute(self, source_geometry, source_crs, context, request, is_canceled) -> None:
        from osgeo import gdal
        self._started = time.perf_counter()
        if self._base_provider != 'gdal':
            self.outcome.message = f"raster provider '{self._base_provider}' cannot be clipped (GDAL files only)"
            return
        side = request.side
        if side is CoverageSide.ALL:
            self.outcome.message = 'inside OR outside keeps every pixel: nothing to do'
            return
        geometry = self._target_geometry(source_geometry, source_crs, context)
        if side is CoverageSide.OUTSIDE:
            geometry = make_valid(QgsGeometry.fromRect(self._extent).difference(geometry))
        geometry = _combine_geometry(self.before.geometry_wkt if self.before.derived else '', self.before.side,
                                     geometry, side, self.operator)
        self._side = side
        if geometry.isEmpty():
            # Nothing kept: clip with a degenerate polygon far outside the extent.
            ext = self._extent
            geometry = QgsGeometry.fromRect(QgsRectangle(ext.xMinimum() - 2, ext.yMinimum() - 2, ext.xMinimum() - 1, ext.yMinimum() - 1))
        self._geometry_wkt = geometry.asWkt()
        path = cache.new_path(self.layer_name, '.vrt')
        options = dict(format='VRT', cutlineWKT=self._geometry_wkt, cutlineSRS=self.crs.toWkt(), cropToCutline=False)
        if self._nodata is not None:
            options['dstNodata'] = self._nodata
        elif self._float:
            options['dstNodata'] = -9999.0
        else:
            options['dstAlpha'] = True
        gdal.UseExceptions()
        dataset = gdal.Warp(path, self._base_source, **options)
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
        from .snapshots import _sync_alpha_band
        layer.setDataSource(self._derived_path, layer.name(), 'gdal', QgsDataProvider.ProviderOptions(), False)
        if not layer.isValid():
            self.outcome.success = False
            self.outcome.message = 'derived VRT could not be opened'
            return None
        _sync_alpha_band(layer)
        after = LayerSnapshot(self.layer_id, self.kind.value, source=layer.source(), provider='gdal', derived=True,
                              original_source=self._base_source, original_provider=self._base_provider,
                              geometry_wkt=self._geometry_wkt, side=self._side.value)
        registry().record(after)
        layer.triggerRepaint()
        return after


# --- point cloud ------------------------------------------------------------

def _bbox_expression(geometry: QgsGeometry, outside: bool) -> str:
    parts = [part for part in geometry.asGeometryCollection()] if geometry.isMultipart() else [geometry]
    boxes = [p.boundingBox() for p in parts if p is not None and not p.isEmpty()]
    if len(boxes) > MAX_BBOX_TERMS:
        boxes = [geometry.boundingBox()]
    terms = [f"(X >= {b.xMinimum():.3f} AND X <= {b.xMaximum():.3f} AND Y >= {b.yMinimum():.3f} AND Y <= {b.yMaximum():.3f})"
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
        self._exporter = None
        if self._mode == 'exact':
            from . import pdal_cli
            self._use_pdal = pdal_cli.is_available() and self._pdal_readable(self._base_source)
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
        from qgis.core import QgsPointCloudLayer, QgsPointCloudLayerExporter
        base = QgsPointCloudLayer(self._base_source, f"{self.layer_name}_base", self._base_provider)
        if not base.isValid():
            return
        self._base_layer = base  # keep alive while the task runs
        exporter = QgsPointCloudLayerExporter(base)
        exporter.setFormat(QgsPointCloudLayerExporter.ExportFormat.Las)
        exporter.setFileName(cache.new_path(self.layer_name, '.laz'))
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
        if self._mode == 'bbox':
            self._expression = _bbox_expression(geometry, side is CoverageSide.OUTSIDE) if not geometry.isEmpty() else ('X = X' if side is CoverageSide.OUTSIDE else 'X < X')
            self.outcome.success = True
            self.outcome.elapsed = time.perf_counter() - self._started
            return
        geometry = _combine_geometry(self.before.geometry_wkt if self.before.derived else '', self.before.side,
                                     geometry, side, self.operator)
        self._geometry_wkt = geometry.asWkt() if not geometry.isEmpty() else ''
        if self._use_pdal:
            self._compute_pdal(geometry, side, is_canceled)
        else:
            self._compute_exporter(geometry, side, is_canceled)
        self.outcome.elapsed = time.perf_counter() - self._started

    def _compute_pdal(self, geometry: QgsGeometry, side: CoverageSide, is_canceled) -> None:
        from . import pdal_cli
        path = cache.new_path(self.layer_name, '.copc.laz')
        reader = {"type": pdal_cli.reader_for(self._base_source), "filename": self._base_source}
        stages = [reader]
        if geometry.isEmpty():
            if side is CoverageSide.INSIDE:
                stages.append({"type": "filters.head", "count": 0})
        else:
            if side is CoverageSide.INSIDE and reader["type"] == 'readers.copc':
                reader["polygon"] = geometry.asWkt()
            stages.append({"type": "filters.crop", "polygon": geometry.asWkt(), "outside": side is CoverageSide.OUTSIDE})
        stages.append({"type": "writers.copc", "filename": path, "forward": "all", "extra_dims": "all",
                       "a_srs": self.crs.authid() or self.crs.toWkt()})
        ok, message = pdal_cli.run_pipeline(stages, is_canceled=is_canceled)
        if not ok:
            self.outcome.message = f"pdal: {message}"
            return
        self._derived_path, self._derived_provider = path, 'copc'
        self.outcome.success = True
        self.outcome.details['derived'] = path

    def _compute_exporter(self, geometry: QgsGeometry, side: CoverageSide, is_canceled) -> None:
        if self._exporter is None:
            self.outcome.message = 'point cloud cannot be clipped (no pdal and no exporter)'
            return
        if side is CoverageSide.OUTSIDE:
            geometry = make_valid(QgsGeometry.fromRect(QgsProject.instance().mapLayer(self.layer_id).extent()).difference(geometry)) \
                if QgsProject.instance().mapLayer(self.layer_id) is not None else geometry
        self._exporter.setFilterGeometry(geometry.constGet().clone() if not geometry.isEmpty() else None)
        self._exporter.doExport()
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
        layer.setDataSource(self._derived_path, layer.name(), self._derived_provider, QgsDataProvider.ProviderOptions(), False)
        if not layer.isValid():
            self.outcome.success = False
            self.outcome.message = 'derived point cloud could not be opened'
            return None
        if self._own_subset:
            if self._derived_provider == 'pdal':
                try:
                    layer.dataProvider().generateIndex()
                except Exception:
                    pass
            layer.setSubsetString(self._own_subset)
        after = LayerSnapshot(self.layer_id, self.kind.value, source=layer.source(), provider=self._derived_provider,
                              subset=layer.subsetString(), derived=True, original_source=self._base_source,
                              original_provider=self._base_provider, geometry_wkt=self._geometry_wkt,
                              side=self._side.value)
        registry().record(after)
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

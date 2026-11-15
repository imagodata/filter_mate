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
from ....core.filter.pk_formatter import is_null_value
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


def _capture_window(full: QgsRectangle, width: int, height: int, kept: Optional[QgsGeometry]):
    """``(area, (columns, rows))``: the cells of a ``width`` x ``height`` grid over ``full`` to capture for ``kept``.

    The bounding box of the parts of ``kept`` that meet ``full``, snapped
    outwards to the native grid, one cell of margin (the cutline keeps the
    cells whose centre is inside), inside ``full``. Nothing kept (None, or outside ``full``): one corner
    cell, the clip masks it. The area stops a millionth of a cell short of
    its last row and column, so that the capture's ``ceil`` gives exactly the
    native cell count: no resampling within the pixel budget.
    """
    cell_x, cell_y = full.width() / width, full.height() / height
    # Part by part: a stored "nothing kept" polygon lies outside the extent, and
    # OR-combined with a zone it would stretch one box from a corner to the zone.
    parts = [] if kept is None or kept.isEmpty() else (
        kept.asGeometryCollection() if kept.isMultipart() else [kept])
    boxes = [box for box in (part.boundingBox() for part in parts) if box.intersects(full)]
    if not boxes:
        first_col, last_col, first_row, last_row = 0, 1, 0, 1
    else:
        x_min, x_max = min(box.xMinimum() for box in boxes), max(box.xMaximum() for box in boxes)
        y_min, y_max = min(box.yMinimum() for box in boxes), max(box.yMaximum() for box in boxes)
        first_col = max(0, int(math.floor((x_min - full.xMinimum()) / cell_x)) - 1)
        last_col = min(width, int(math.ceil((x_max - full.xMinimum()) / cell_x)) + 1)
        first_row = max(0, int(math.floor((full.yMaximum() - y_max) / cell_y)) - 1)
        last_row = min(height, int(math.ceil((full.yMaximum() - y_min) / cell_y)) + 1)
    short = 1e-6
    area = QgsRectangle(full.xMinimum() + first_col * cell_x, full.yMaximum() - (last_row - short) * cell_y,
                        full.xMinimum() + (last_col - short) * cell_x, full.yMaximum() - first_row * cell_y)
    return area, (last_col - first_col, last_row - first_row)


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


def _polygons(geometry: QgsGeometry) -> QgsGeometry:
    """The polygon parts of ``geometry`` (an empty geometry when it has none)."""
    wkt = _kept_area(geometry)
    return QgsGeometry.fromWkt(wkt) if wkt is not None else QgsGeometry()


def _combine_geometry(previous_wkt: str, previous_side: str, new: QgsGeometry, side: CoverageSide,
                      operator: Optional[str], extent: Optional[QgsRectangle] = None) -> QgsGeometry:
    """Combine the kept area of an already derived target with a new kept area.

    Both geometries are areas KEPT (outside already subtracted), so they
    combine whatever their side. 2026-11-12: a target without a previous area
    under AND NOT keeps ``extent`` (its whole area) minus the new area, as a
    vector layer without a filter keeps ``NOT (new)``; it kept the new area.
    """
    if not operator:
        return new
    op = operator.upper()
    if not previous_wkt:
        if op != 'AND NOT' or extent is None:
            return new
        previous_wkt = QgsGeometry.fromRect(extent).asWkt()
    # Polygons only: overlays of collections holding lines fail in older GEOS (QGIS 3.22 - 3.28).
    previous = _polygons(QgsGeometry.fromWkt(previous_wkt))
    if previous.isEmpty():
        return new
    new = _polygons(new)
    if new.isEmpty():
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


def _keeps_previous(previous_subset: str, operator: Optional[str]) -> bool:
    """True when nothing new combined with ``operator`` leaves the layer as it was.

    OR with a previous subset, and AND NOT always (2026-11-12: without a
    previous subset it removes the new selection from the whole layer).
    """
    op = (operator or '').strip().upper()
    return op == 'AND NOT' or (op == 'OR' and bool((previous_subset or '').strip()))


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
    _QGIS_HANDLES = ('_source', '_unfiltered', '_base_layer', '_exporter', '_base_keepalive', '_remote_target')
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


def translate(context: str, text: str) -> str:
    """``QCoreApplication.translate``; the source text without Qt (or a mocked one)."""
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        translated = QCoreApplication.translate(context, text)
    except Exception:  # nosec B110 - untranslated without Qt
        return text
    return translated if isinstance(translated, str) else text


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


class _Unlisted:
    """The matching features of a web service could not be listed; ``reason`` is the one of the bounded read.

    ``key_limit``: more of them than a service is sent as a list. ``unverified_filter``: nothing was read, this
    QGIS cannot check what a service answers.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason


def BY_EXTENT(reason: str = '') -> str:
    """What is said of a web service cut by the extent of the source: the words of the dock (filter_executor)."""
    from ...backends.ogr.filter_executor import _remote_message
    return _remote_message({'unverified_filter': 'by_extent_unverified', 'refused': 'by_extent_refused'}.get(
        reason, 'by_extent'))


class VectorTargetJob(TargetJob):
    """Keep the features of a vector target that satisfy the predicates."""

    kind = LayerKind.VECTOR
    # The selected features of a vector source, buffered (set by CrossFilterTask).
    source_parts: Optional[List[QgsGeometry]] = None

    def __init__(self, layer: QgsVectorLayer, operator: Optional[str]) -> None:
        super().__init__(layer, operator)
        self._error = ''
        # 2026-10-17: the key-list bounds of the source (core.domain.source_capability)
        from ..source_capability_probe import capability_for_layer
        self._capability = capability_for_layer(layer)
        # 2026-10-20: a web service is read like the dock reads it (remote_materializer):
        # the server gets the useful BBOX, the exact predicate runs on bounded copies.
        # A filter rectangle alone downloaded the whole service (35 000 communes).
        self._remote_target = None
        self._partial = ''
        whole_layer = bool(self.before.subset) and (operator or '').upper() not in ('AND', 'AND NOT')
        if self._capability is not None and self._capability.is_remote_service:
            self._remote_target = self._remote_snapshot(layer, whole_layer)
            self._source = None
        elif whole_layer:
            # Replace (no operator) and OR: the result does not depend on the
            # features the previous subset hides, they are tested too.
            self._source = self._unfiltered_source(layer)
        else:
            self._source = QgsVectorLayerFeatureSource(layer)
        self._is_polygon = _is_polygon_layer(layer)
        line_type = getattr(getattr(Qgis, 'GeometryType', None), 'Line', 1)
        self._centroid_eligible = self._is_polygon or layer.geometryType() == line_type
        self._use_centroids = False
        self._pk, self._raw_pk = self._primary_key(layer)
        # The cut by extent set in place of the list of keys when the service refuses it (apply).
        self._extent_fallback = ''
        # A layer that only asks the rectangle of the map writes a longer address for the same keys.
        from ....core.domain.source_capability import asks_by_rectangle
        self._by_rectangle = asks_by_rectangle(layer.source())
        self._no_key = ''
        if self._pk is None:
            no_key = translate(
                "VectorTargetJob",
                "{0}: no unique key field, its features cannot be listed in its filter "
                "(a web service, or a virtual layer without a unique id column)."
            ).format(layer.name())
            if self._remote_target is not None and getattr(self._capability, 'takes_extent_subset', False):
                # 2026-11-15: such a service is cut by the extent of the source (compute), which lists no key.
                self._no_key = no_key
            else:
                self._error = no_key
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
    def _remote_snapshot(layer: QgsVectorLayer, whole_layer: bool):
        """Frozen web service target for a bounded worker read (main thread, nothing fetched).

        ``whole_layer``: its current subset is left out (replace, OR), as for a local target.
        """
        from ..remote_materializer import _snapshot, unfiltered_snapshot
        from ...backends.ogr import filter_executor  # noqa: F401 - imported here, on the main thread, not by the worker
        return unfiltered_snapshot(layer) if whole_layer else _snapshot(layer)

    def _compute_remote(self, geometry, methods, parts, part_methods, coverage):
        """Keys of a web service target, read inside the useful BBOX only.

        The dock's bounded read (``filter_executor.apply_remote_spatial_filter``):
        same budgets, same 500-key limit, same refusals and partial results.
        Returns the keys to list, or None when the target is refused
        (``outcome.message`` says why); a disjoint keeps the complement of the keys.
        """
        from ....config.config import ENV_VARS
        from ...backends.ogr.filter_executor import _remote_message
        from ..remote_materializer import materialization_limits, materialize
        complement = 'disjoint' in methods
        if complement and (methods != ['disjoint'] or (parts is not None and part_methods)):
            self.outcome.message = _remote_message('mixed_disjoint')
            return None
        if geometry.isEmpty():
            return ()
        tests = ['intersects'] if complement else methods
        engine = prepared_engine(geometry) if tests else None

        def matches(feature):
            target_geometry = feature.geometry()
            if target_geometry is None or target_geometry.isEmpty():
                return False
            if not target_geometry.isGeosValid():
                # As the dock: refused (read_error), never silently left out of a complement.
                raise ValueError('Invalid target geometry')
            target_geometry = self._predicate_geometry(target_geometry)
            matched = engine is not None and target_matches(engine, target_geometry, tests)
            if not matched and parts is not None and not complement:
                matched = parts.matches(target_geometry, part_methods)
            if matched and coverage > 0 and not complement:
                matched = coverage_ratio_ok(target_geometry.area(), target_geometry.intersection(geometry).area(),
                                            coverage)
            return matched

        # The user's REMOTE_MATERIALIZATION budgets, as in the dock (they were the defaults).
        outcome = materialize(self._remote_target, geometry.boundingBox(), '', matches,
                              materialization_limits(ENV_VARS), self.feedback)
        self._remote_target = None  # the snapshot holds a feature source of the main thread's layer
        if not outcome.complete:
            from ..remote_materializer import supports_reply_validation
            if outcome.reason == 'key_limit' or (
                    outcome.reason == 'unverified_filter' and not supports_reply_validation()):
                # (A read that found nothing on a QGIS that checks its replies stays refused, as before.)
                return _Unlisted(outcome.reason)  # compute() cuts by the extent of the source, or refuses with it
            if outcome.reason not in ('feature_limit', 'timeout'):
                self.outcome.message = _remote_message(outcome.reason)
                return None
            if complement:
                self.outcome.message = _remote_message('disjoint_partial')
                return None
            if (self.operator or '').upper() == 'AND NOT':
                # (old) AND NOT (keys), or NOT (keys) without a previous filter
                # (2026-11-12): the matching features never read would stay.
                self.outcome.message = translate(
                    'VectorTargetJob', '{0} AND NOT would keep the features not read; the previous filter is kept.'
                ).format(_remote_message(outcome.reason))
                return None
            if not outcome.keys:
                self.outcome.message = _remote_message('partial_empty')
                return None
            self._partial = _remote_message(outcome.reason)
        return outcome.keys

    @staticmethod
    def _primary_key(layer: QgsVectorLayer):
        """``(key, raw)``: the stable key of core.domain.stable_key, or the feature id (raw ``FID`` / ``$id``).

        2026-10-17: verdicts already proven only (this runs on the main thread:
        no read of the layer). ``(None, False)`` where feature ids cannot be
        listed (a web service or a virtual layer without key): refused. The FID
        of a Shapefile / CSV is its row number, renumbered when the file is edited.
        """
        from ..source_capability_probe import stable_key_for_layer
        choice = stable_key_for_layer(layer, scan=False)
        if choice.is_field:
            return choice.name, False
        if choice.name is None:
            return None, False
        if layer.providerType() == 'ogr':
            return 'FID', True
        return '$id', True

    def compute(self, source_geometry, source_crs, context, request, is_canceled) -> None:
        self._started = time.perf_counter()
        if self._error:
            self.outcome.message = self._error
            return
        self._use_centroids = self._centroid_eligible and any(
            target.layer_id == self.layer_id and target.use_centroids for target in request.targets)
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
        coverage = float(request.coverage_min or 0.0) if self._is_polygon else 0.0
        complement = False
        remote = self._remote_target is not None
        if remote:
            if self._no_key:
                # Nothing to list, so nothing to read: the server is asked what meets the extent of the source.
                self._remote_target = None
                if not self._cut_by_extent(geometry, request.methods):
                    self.outcome.message = self._no_key
                return
            kept = self._compute_remote(geometry, methods, parts, part_methods, coverage)
            if isinstance(kept, _Unlisted):
                if not self._cut_by_extent(geometry, request.methods, kept.reason):
                    from ...backends.ogr.filter_executor import _remote_message
                    self.outcome.message = _remote_message(kept.reason)
                return
            if kept is None:
                return
            # Disjoint: the keys are those of the features that intersect (all inside the BBOX).
            complement = 'disjoint' in methods
        else:
            kept = self._compute_local(geometry, methods, parts, part_methods, coverage, request, is_canceled)
            if kept is None:
                return
        capability = self._capability
        limit = capability.key_list_limit if capability is not None and capability.is_remote_service else None
        if remote and kept and not complement:
            # 2026-11-15: QGIS writes the keys in the address of each request, and a server stops reading an address
            # at a length of its own (8 KB for most): a longer list gave an empty layer, or was refused. Not sent.
            from ....core.domain.source_capability import key_list_fits
            from ..remote_materializer import request_bytes_limit
            from ....config.config import ENV_VARS
            if not key_list_fits(self._pk, kept, request_bytes_limit(ENV_VARS),
                                 self._by_rectangle) and self._cut_by_extent(
                    geometry, request.methods):
                self._source = None
                return
        if limit and len(kept) > limit:
            self._source = None
            if self._cut_by_extent(geometry, request.methods):
                return
            self.outcome.message = translate(
                "VectorTargetJob",
                "{0} features to list, more than the {1} sent to a web service: narrow the source "
                "or use an attribute filter."
            ).format(f"{len(kept):,}", f"{limit:,}")
            return
        qgis_expression = capability is not None and capability.subset_is_qgis_expression
        chunk = capability.in_list_max if capability is not None else None
        if chunk and len(kept) > chunk:
            lists = [build_in_expression(self._pk, kept[i:i + chunk], raw_field=self._raw_pk,
                                         qgis_expression=qgis_expression) for i in range(0, len(kept), chunk)]
            self._expression = "(" + " OR ".join(lists) + ")"
        else:
            self._expression = build_in_expression(self._pk, kept, raw_field=self._raw_pk,
                                                   qgis_expression=qgis_expression)
        # Release the provider connection held by the feature source before the
        # subset is applied (an open GeoPackage reader made the count fail).
        # The unfiltered copy, a QObject of the main thread, goes in apply().
        self._source = None
        if complement:
            # Every feature but the listed ones (the dock writes the same filter).
            self._expression = f"NOT ({self._expression})" if kept else '1 = 1'
        else:
            self.outcome.kept_count = len(kept)
            if remote and kept:
                # 2026-11-15: a service may refuse this list (its address is too long for it, far under 500 keys
                # on a real WFS): apply() then sets the cut by extent kept here.
                self._extent_fallback = self._extent_expression(geometry, request.methods) or ''
            # OR / AND NOT nothing leave the previous subset as it was.
            self.outcome.emptied = not kept and not _keeps_previous(self.before.subset, self.operator)
        if self._partial:
            # Kept features are exact, others may be missing: applied with a warning, as in the dock.
            self.outcome.message = self._partial
            self.outcome.details['partial'] = True
        self.outcome.success = True
        self.outcome.elapsed = time.perf_counter() - self._started

    def _cut_by_extent(self, geometry, methods, reason: str = '') -> bool:
        """Cut the target by the extent of the source, on the server, where its features cannot be listed.

        2026-11-15: a web service was refused past 500 matching features, or without a stable key. A WFS is asked
        what meets the rectangle of the source instead (``source_capability.extent_subset``): no key is listed, so
        the result has no bound. It is a cut by extent, and says so: a feature inside the rectangle and outside the
        source itself stays, whatever the predicate. So is a WFS on a QGIS that cannot check what a service answers
        (``reason`` ``unverified_filter``: before 3.26, or before 3.36 under Python 3.12), where nothing is read.

        Returns:
            False where the cut cannot be made, the job left as it was: a service that takes no such filter, AND NOT
            or Disjoint (both keep what lies outside the rectangle, a negation the validated WFS dialect does not
            write: what a server answers for a feature without geometry is not proven), an empty source.
        """
        expression = self._extent_expression(geometry, methods)
        if expression is None:
            return False
        self._source = None
        self._expression = expression
        self.outcome.details['by_extent'] = True
        self.outcome.message = BY_EXTENT(reason)
        self.outcome.success = True
        self.outcome.elapsed = time.perf_counter() - self._started
        return True

    def _extent_expression(self, geometry, methods) -> Optional[str]:
        """The filter by the extent of ``geometry`` this target takes; None where a cut by extent cannot be made."""
        from ....core.domain.source_capability import extent_subset
        if self._capability is None or (self.operator or '').upper() == 'AND NOT' or geometry.isEmpty():
            return None
        if 'disjoint' in methods:
            return None
        box = geometry.boundingBox()
        return extent_subset(self._capability, box.xMinimum(), box.yMinimum(), box.xMaximum(), box.yMaximum())

    def _predicate_geometry(self, geometry):
        """The geometry used by the predicate; the original feature is retained in the target layer."""
        if not self._use_centroids:
            return geometry
        point = geometry.pointOnSurface()
        if point is None or point.isEmpty():
            raise ValueError('Cannot compute the target point on surface')
        return point

    def _compute_local(self, geometry, methods, parts, part_methods, coverage, request, is_canceled):
        """Keys of the features of a local (or database) target; None when canceled."""
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
        for feature in self._source.getFeatures(feature_request):
            if is_canceled():
                self.outcome.message = 'canceled'
                return None
            target_geometry = feature.geometry()
            if target_geometry is None or target_geometry.isEmpty():
                continue
            target_geometry = self._predicate_geometry(target_geometry)
            if engine is None:
                matched = methods == ['disjoint']
            else:
                matched = target_matches(engine, target_geometry, methods)
            if not matched and parts is not None:
                matched = parts.matches(target_geometry, part_methods)
            if matched and coverage > 0 and 'disjoint' not in request.methods:
                matched = coverage_ratio_ok(target_geometry.area(), target_geometry.intersection(geometry).area(), coverage)
            if matched:
                value = feature.id() if self._raw_pk else feature.attribute(self._pk)
                if not is_null_value(value):  # a NULL key (None / null QVariant) matches nothing
                    kept.append(value)
        return kept

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
            from ....infrastructure.database.sql_utils import safe_set_subset_string as set_subset
        except ImportError:
            def set_subset(target, text):
                return target.setSubsetString(text)
        ok = set_subset(layer, subset)
        if not ok and self._extent_fallback:
            # The service refused the list of keys: cut by the extent of the source instead, and said.
            by_extent = combine_subset(self.before.subset, self._extent_fallback, self.operator)
            ok = set_subset(layer, by_extent)
            if ok:
                subset, self._partial = by_extent, ''
                self.outcome.details.pop('partial', None)
                self.outcome.details['by_extent'] = True
                self.outcome.message = BY_EXTENT('refused')
                self.outcome.kept_count = None  # what the rectangle holds was not counted
                self.outcome.emptied = False
        if not ok:
            self.outcome.success = False
            self.outcome.message = f"subset rejected by the provider: {subset[:200]}"
            return None
        if self._capability is not None and self._capability.is_remote_service:
            # Partial provenance, as the dock records it (the dock refuses such a layer as a source).
            from ..remote_materializer import mark_partial_result
            mark_partial_result(layer, bool(self._partial), subset)
        layer.triggerRepaint()
        return take_snapshot(layer, self.kind)


# --- raster -----------------------------------------------------------------

def _transparent_cell(extent: QgsRectangle, crs_wkt: str) -> str:
    """One transparent cell at the upper left corner of ``extent``: the capture of a web map that keeps nothing."""
    from osgeo import gdal
    path = cache.new_path('web_map_empty', '.tif')
    size = max(extent.width(), extent.height()) / 4096.0 or 1.0
    dataset = gdal.GetDriverByName('GTiff').Create(path, 1, 1, 4, gdal.GDT_Byte)
    if dataset is None:
        cache.settle([path])
        raise RuntimeError(translate('RasterTargetJob', 'local raster target could not be opened'))
    dataset.SetGeoTransform((extent.xMinimum(), size, 0, extent.yMaximum(), 0, -size))
    if crs_wkt:
        dataset.SetProjection(crs_wkt)
    for index, interpretation in enumerate((gdal.GCI_RedBand, gdal.GCI_GreenBand, gdal.GCI_BlueBand,
                                            gdal.GCI_AlphaBand)):
        band = dataset.GetRasterBand(index + 1)
        band.SetColorInterpretation(interpretation)
        band.Fill(0)
    dataset.FlushCache()
    dataset = None  # noqa: F841 - close the file
    return path


def _web_map_note(capture: dict, crs) -> str:
    """What is said of a web map cut by a source: it is a still image, at this resolution, maybe with holes."""
    try:
        from qgis.core import QgsUnitTypes
        unit = QgsUnitTypes.toAbbreviatedString(crs.mapUnits())
    except Exception:  # an invalid CRS, or a QGIS without this helper
        unit = ''
    resolution = '{:.3g}'.format(capture.get('resolution') or 0.0)
    note = translate(
        'RasterTargetJob',
        'Web map captured as a still image of {0} x {1} pixels ({2} {3} per pixel), then cut by the source: '
        'zooming in shows no more detail. Unfilter gives the live service back.'
    ).format(capture.get('columns'), capture.get('rows'), resolution, unit or translate('RasterTargetJob', 'map units'))
    if capture.get('unread'):
        note += ' ' + translate(
            'RasterTargetJob', '{0} request(s) of the service were not answered: the image may have holes.'
        ).format(capture['unread'])
    return note


class _ProviderLayer:
    """A raster provider with the few layer calls ``materialize_raster`` makes (worker only)."""

    def __init__(self, provider, provider_key: str, source: str, name: str) -> None:
        self._provider, self._key, self._source, self._name = provider, provider_key, source, name

    @classmethod
    def open(cls, provider_key: str, source: str, name: str) -> '_ProviderLayer':
        """``source`` as a bare provider, not a QgsRasterLayer.

        A layer computes the statistics of its default renderer when it
        opens: one more read of the whole coverage (WCS: a GetCoverage of
        586 x 427 cells over 1 240 km).
        """
        from qgis.core import QgsDataProvider, QgsProviderRegistry
        provider = QgsProviderRegistry.instance().createProvider(
            provider_key, source, QgsDataProvider.ProviderOptions())
        return cls(provider, provider_key, source, name)

    def isValid(self) -> bool:
        return self._provider is not None and self._provider.isValid()

    def dataProvider(self):
        return self._provider

    def providerType(self) -> str:
        return self._key

    def source(self) -> str:
        return self._source

    def name(self) -> str:
        return self._name

    def extent(self):
        return self._provider.extent()

    def width(self) -> int:
        return self._provider.xSize()

    def height(self) -> int:
        return self._provider.ySize()

    def crs(self):
        return self._provider.crs()


class RasterTargetJob(TargetJob):
    """Set the pixels of a raster target outside (or inside) the source geometry to NoData."""

    kind = LayerKind.RASTER

    def __init__(self, layer, operator: Optional[str]) -> None:
        super().__init__(layer, operator)
        self._base_source = self.before.base_source
        self._base_provider = self.before.base_provider
        from ....core.domain.source_capability import classify
        from .raster_materialization import is_wcs, raster_reads_remotely
        capability = classify(self._base_provider, self._base_source, is_raster=True)
        self._rendered = not capability.has_raw_values
        # 2026-11-15: a web map (WMS, WMTS, XYZ tiles) draws an image and was refused as a target. It is captured
        # in the area the source keeps, within a budget of pixels, then cut as a local raster is (_capture_web_map).
        from ..point_cloud_capability import CAPTURED_TARGET_PROVIDERS
        self._web_map = self._rendered and (self._base_provider or '').lower() in CAPTURED_TARGET_PROVIDERS
        if self._web_map:
            # The tiles of QGIS are asked by a thread of its own, which tells the network manager of the main
            # thread what it finished: the capture listens to it (materialize_web_map).
            from ..source_capability_probe import capture_network_manager
            capture_network_manager()
        self._remote = self._web_map or raster_reads_remotely(self._base_provider, self._base_source)
        self._is_wcs = is_wcs(self._base_provider, self._base_source)
        self._analysis_source = None
        self._input_source = self._base_source
        self._extent = QgsRectangle(layer.extent())
        self._nodata, self._float, self._pixel = [], True, 0.0
        if not self._remote:
            self._read_metadata(_base_raster_layer(self.before, layer))
        self._derived_path = ''
        self._geometry_wkt = ''
        self._side = CoverageSide.INSIDE

    def _read_metadata(self, base):
        """Read remote metadata only after opening the worker's private layer."""
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

    def _open_remote(self):
        """The original remote raster, opened in the worker: its full extent (``self._extent``) and grid."""
        import threading
        if threading.current_thread() is threading.main_thread():
            raise RuntimeError(translate('RasterTargetJob', 'remote raster target must run in a worker thread'))
        from .raster_materialization import _tr
        base = _ProviderLayer.open(self._base_provider, self._base_source, 'FilterMate target capture')
        if not base.isValid() or base.width() < 1 or base.height() < 1:
            raise RuntimeError(_tr('raster capture source could not be opened'))
        # Not the layer's extent: a derived layer shows its previous capture only.
        self._extent = QgsRectangle(base.extent())
        return base

    def _open_web_map(self):
        """The web map as a bare provider, opened in the worker: its extent (``self._extent``); it has no grid."""
        import threading
        if threading.current_thread() is threading.main_thread():
            raise RuntimeError(translate('RasterTargetJob', 'remote raster target must run in a worker thread'))
        from .raster_materialization import _tr
        base = _ProviderLayer.open(self._base_provider, self._base_source, 'FilterMate target capture')
        extent = QgsRectangle(base.extent()) if base.isValid() else QgsRectangle()
        if not base.isValid() or extent.isEmpty() or not extent.isFinite():
            raise RuntimeError(_tr('raster capture source could not be opened'))
        self._extent = extent
        return base

    def _capture_web_map(self, base, kept: Optional[QgsGeometry], is_canceled) -> str:
        """The image the web map draws over the area ``kept``, as a local GeoTIFF (red, green, blue, alpha).

        The grid is the finest the budget of pixels affords over the bounding box of ``kept``
        (``CROSS_FILTER.web_map_target_max_pixels``, ``raster_materialization.web_map_grid``): a level of the
        service when it has levels (tiles), copied and not resampled. Nothing kept: one transparent cell written
        here, the service is asked nothing.
        """
        from .raster_materialization import materialize_web_map, web_map_grid, web_map_max_pixels
        parts = [] if kept is None or kept.isEmpty() else (
            kept.asGeometryCollection() if kept.isMultipart() else [kept])
        boxes = [box for box in (part.boundingBox() for part in parts) if box.intersects(self._extent)]
        grid = None
        if boxes:
            full = (self._extent.xMinimum(), self._extent.yMinimum(), self._extent.xMaximum(), self._extent.yMaximum())
            box = (min(b.xMinimum() for b in boxes), min(b.yMinimum() for b in boxes),
                   max(b.xMaximum() for b in boxes), max(b.yMaximum() for b in boxes))
            try:
                levels = [float(level) for level in base.dataProvider().nativeResolutions()]
            except Exception:  # a provider without levels
                levels = []
            try:
                grid = web_map_grid(full, box, web_map_max_pixels(cache._config_value('web_map_target_max_pixels', None)),
                                    levels)
            except ValueError:
                grid = None  # the area kept only touches the extent of the service
        if grid is None:
            return _transparent_cell(self._extent, base.crs().toWkt())
        (x_min, y_min, x_max, y_max), columns, rows, resolution = grid
        path, unread = materialize_web_map(base, QgsRectangle(x_min, y_min, x_max, y_max), columns, rows, is_canceled)
        self.outcome.details['web_map'] = {'resolution': resolution, 'columns': columns, 'rows': rows, 'unread': unread}
        return path

    def _prepare_input(self, is_canceled, base=None, kept: Optional[QgsGeometry] = None):
        """Local pixels to clip: the analysis capture, or a capture of ``base`` around ``kept``.

        2026-10-20: a remote target is captured over the area the clip keeps
        only (native grid, one cell of margin, the pixel budget still applies),
        no longer over its whole extent (the WCS was read over 1 240 km for a
        zone of 25 km).
        """
        from qgis.core import QgsRasterLayer
        from .raster_materialization import materialize_raster
        if base is None:
            source, provider = self._analysis_source
            base = QgsRasterLayer(source, 'FilterMate target capture', provider)
            native_size = base.width(), base.height()
        elif self._web_map:
            source = self._capture_web_map(base, kept, is_canceled)
            self.outputs.append(source)
            base = QgsRasterLayer(source, 'FilterMate local target', 'gdal')
            native_size = base.width(), base.height()  # a web map has no grid to be resampled from
        else:
            area, native_size = _capture_window(self._extent, base.width(), base.height(), kept)
            source = materialize_raster(base, extent=area, is_canceled=is_canceled)
            self.outputs.append(source)
            base = QgsRasterLayer(source, 'FilterMate local target', 'gdal')
        if not base.isValid():
            raise RuntimeError(translate('RasterTargetJob', 'local raster target could not be opened'))
        self._input_source = source
        self._read_metadata(base)
        self.outcome.details['capture_grid'] = '{}x{}'.format(base.width(), base.height())
        self.outcome.details['capture_resampled'] = (base.width(), base.height()) != native_size
        self.outcome.details['capture_cell_size'] = self._pixel

    def compute(self, source_geometry, source_crs, context, request, is_canceled) -> None:
        self._started = time.perf_counter()
        if self._rendered and (not self._web_map or self._analysis_source is not None):
            # Not captured (ArcGIS MapServer, GDAL WMS), or a web map filtered as a source by its own colours:
            # the capture of its selection is the one of the screen, not one made for a cut.
            self.outcome.message = translate('RasterTargetJob', 'Rendered color layers cannot be filter targets.')
            return
        if not self._web_map and self._base_provider not in ('gdal', 'postgresraster') and not self._is_wcs:
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
        if is_canceled():
            self.outcome.message = 'canceled'
            return
        if self._analysis_source is not None:
            self._prepare_input(is_canceled)
        geometry = self._target_geometry(source_geometry, source_crs, context)
        if side is CoverageSide.INSIDE and not geometry.isEmpty() and not _has_area(geometry):
            self.outcome.message = NO_AREA
            return
        remote = None
        if self._analysis_source is None and self._remote:
            # Its full extent; captured below, once the kept area is known.
            remote = self._open_web_map() if self._web_map else self._open_remote()
        if side is CoverageSide.OUTSIDE:
            geometry = _checked(QgsGeometry.fromRect(self._extent).difference(geometry), 'difference')
        geometry = _combine_geometry(self.before.geometry_wkt if self.before.derived else '', self.before.side,
                                     geometry, side, self.operator, self._extent)
        self._side = side
        kept = _kept_area(geometry)
        self.outcome.emptied = kept is None or not geometry.boundingBox().intersects(self._extent)
        # Nothing kept: clip with a degenerate polygon far outside the extent.
        geometry = QgsGeometry.fromWkt(kept) if kept is not None else _nothing_kept(self._extent)
        self._geometry_wkt = geometry.asWkt()
        if remote is not None:
            self._prepare_input(is_canceled, remote, geometry if kept is not None else None)
        cutline = _simplified_for_cutline(geometry, self._pixel * 0.5)
        if self._input_source != self._base_source:
            # The VRT and its captured pixels share a cache key: history keeps both.
            path = self._input_source + '.clip.vrt'
            self.outputs.append(path)
        else:
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
        options['callback'] = lambda *args: 0 if is_canceled() else 1
        dataset = gdal_warp(path, self._input_source, **options)
        dataset = None  # noqa: F841 - flush the VRT
        if is_canceled():
            self.outcome.message = 'canceled'
            return
        self._derived_path = path
        capture = self.outcome.details.get('web_map')
        if capture:
            self.outcome.details['captured'] = True
            self.outcome.message = _web_map_note(capture, self.crs)
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
        if self.before.bounded_enrichment and (operator or '').upper() not in ('AND', 'AND NOT'):
            self._unsupported = translate('PointCloudTarget',
                                          'A bounded height-above-ground cloud only supports AND or AND NOT; Unfilter first')
        self._pending_extent_source = None
        if self.before.derived:
            # Outside / empty areas are computed on the ORIGINAL extent: the
            # clip is applied to the original source, not to the derived one.
            from .point_cloud_footprint import open_point_cloud
            from .pdal_cli import is_remote_source
            if is_remote_source(self._base_source):
                self._pending_extent_source = self._base_source
            else:
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
                if pdal_cli.is_remote_source(self._base_source):
                    self._unsupported = translate('PointCloudTarget', 'PDAL 2.4 or newer is required to clip a remote point cloud')
                else:
                    self._prepare_exporter()

    @staticmethod
    def _pdal_readable(path: str) -> bool:
        from . import pdal_cli
        try:
            pdal_cli.reader_for(path)
            return os.path.isfile(path) or pdal_cli.is_remote_source(path) or path.lower().endswith('ept.json')
        except ValueError:
            return False

    def _prepare_exporter(self) -> None:
        """QgsPointCloudLayerExporter must be prepared on the main thread."""
        from .point_cloud_footprint import (
            exporter_unavailable_message, index_ready, open_point_cloud, point_cloud_exporter_class, qgis_reads_las,
        )
        exporter_class = point_cloud_exporter_class()
        if exporter_class is None:
            self._unsupported = exporter_unavailable_message()
            return
        if not qgis_reads_las():
            self._unsupported = ("QGIS is built without PDAL: it can neither write nor open the clipped LAS file; "
                                 "install the pdal tool (2.4 or later) or use the bbox clip mode")
            return
        base = open_point_cloud(self._base_source, f"{self.layer_name}_base", self._base_provider)
        if not base.isValid():
            return
        if not index_ready(base):
            # The exporter reads the index without checking it (crash on a null one).
            self._unsupported = "the point cloud has no index yet (LAS file being indexed): try again later"
            return
        self._base_layer = base  # keep alive while the task runs
        exporter = exporter_class(base)
        exporter.setFormat(exporter_class.ExportFormat.Las)
        exporter.setFileName(self._new_path('.laz'))
        exporter.setAllAttributes()
        self._exporter = exporter

    def compute(self, source_geometry, source_crs, context, request, is_canceled) -> None:
        self._started = time.perf_counter()
        side = request.side
        if side is CoverageSide.ALL:
            self.outcome.message = 'inside OR outside keeps every point: nothing to do'
            return
        if self.before.bounded_enrichment and (self.operator or '').upper() not in ('AND', 'AND NOT'):
            self.outcome.message = self._unsupported
            return
        from .pdal_cli import is_remote_source
        if side is CoverageSide.OUTSIDE and is_remote_source(self._base_source):
            self.outcome.message = translate('PointCloudTarget',
                                            'Disjoint would read the whole remote cloud; choose an inside selection')
            return
        if self._pending_extent_source is not None:
            from .point_cloud_footprint import open_point_cloud
            base = open_point_cloud(self._pending_extent_source, f'{self.layer_name}_base', self._base_provider)
            if not base.isValid():
                self.outcome.message = translate('PointCloudTarget', 'The original remote point cloud could not be opened')
                return
            self._extent = QgsRectangle(base.extent())
            self._extent.grow(1.0)
            self._pending_extent_source = None
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
            self.outcome.emptied = (side is CoverageSide.INSIDE and not _keeps_previous(self._own_subset, self.operator)
                                    and (geometry.isEmpty() or not geometry.boundingBox().intersects(self._extent)))
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
                                     geometry, side, self.operator, self._extent)
        # filters.crop takes polygons only: make_valid / an intersection can add lines and points.
        polygon = _kept_area(geometry)
        geometry = QgsGeometry.fromWkt(polygon) if polygon is not None else None
        if geometry is None or not geometry.boundingBox().intersects(self._extent):
            # Nothing kept. Stored, not left empty: an empty state would be
            # dropped from the project and read as "no previous filter" by the next AND.
            polygon, geometry = None, _nothing_kept(self._extent)
            self.outcome.emptied = True
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
        area = QgsGeometry.fromWkt(polygon or self._geometry_wkt).boundingBox()
        bounds = (area.xMinimum(), area.yMinimum(), area.xMaximum(), area.yMaximum())
        try:
            stages = pdal_cli.read_stages(self._base_source, bounds, polygon)
        except ValueError as exc:
            self.outcome.message = str(exc)
            return
        if polygon is None:
            stages.append({"type": "filters.head", "count": 0})
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
        if not self.outcome.emptied and derived_point_count(layer) == 0:
            # 2026-10-18: an area over the cloud extent that holds no point (a gap, a
            # strip between flight lines) left an empty cloud reported as filtered.
            self.outcome.emptied = True
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
                              enriched_provider=self.before.enriched_provider,
                              bounded_enrichment=self.before.bounded_enrichment)
        registry().record(after, layer)
        layer.triggerRepaint()
        return after


def derived_point_count(layer) -> int:
    """Points of the file a point cloud layer now reads (its header, no point is read); -1 when unknown."""
    try:
        provider = layer.dataProvider()
        count = provider.pointCount() if provider is not None else -1
        return int(count) if count is not None else -1
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return -1


def make_job(layer, kind: LayerKind, operator: Optional[str], point_cloud_clip: str = 'exact') -> Optional[TargetJob]:
    """Build the job for a target layer (main thread)."""
    if kind is LayerKind.VECTOR_TILE:
        from .vector_tile_target import VectorTileTargetJob
        return VectorTileTargetJob(layer, operator)
    if kind is LayerKind.VECTOR:
        return VectorTargetJob(layer, operator)
    if kind is LayerKind.RASTER:
        return RasterTargetJob(layer, operator)
    if kind is LayerKind.POINT_CLOUD:
        return PointCloudTargetJob(layer, operator, point_cloud_clip)
    return None

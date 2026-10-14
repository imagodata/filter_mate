# -*- coding: utf-8 -*-
"""
FilterMate operations usable without the dock (FilterMate 5).

One implementation behind the three automation surfaces:

* the public Python API (:class:`FilterMatePublicAPI`, other plugins, console scripts);
* the Processing algorithms (``filtermate:*``, models, batch, ``qgis_process``);
* the REST API (``filtermate_api``).

Every operation runs synchronously on the main thread, changes the project
layers in place like the dock does, and records its changes in the cross
filter history so the dock's Undo / Redo / Unfilter buttons can revert them.
Layers are QGIS layer objects; :func:`resolve_layer` finds them by id or name.

Operations:

* :func:`cross_filter` - source of any kind (vector features, raster pixels,
  point cloud points) -> targets of any kind;
* :func:`cross_filter_by_geometry` - a geometry (extent, drawn shape) -> targets;
* :func:`filter_point_clouds` - same criteria on several point clouds (tiles);
* :func:`clear_filters` - back to the original source, no subset;
* :func:`export_layers` - filtered layers to files (vector, GeoTIFF / COG, LAZ / COPC);
* :func:`apply_favorite` / :func:`list_favorites` - saved favorites, dock or not.
"""
import json
import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ...core.domain.api_requests import (
    OperationReport,
    POINT_CLOUD_EXPORT_FORMATS,
    RASTER_EXPORT_FORMATS,
    VECTOR_EXPORT_FORMATS,
)
from ...core.domain.layer_kind import LayerKind

logger = logging.getLogger(__name__)

NOT_IN_PROJECT = "not in the project: a filter on a temporary layer would be lost"
NOT_FILTERABLE = "not a vector, raster or point cloud layer FilterMate can filter"


# --- layers --------------------------------------------------------------------

def _project(project=None):
    if project is not None:
        return project
    from qgis.core import QgsProject
    return QgsProject.instance()


def layer_kind(layer) -> LayerKind:
    """Kind from the layer class only (no dock option involved)."""
    from ..qgis.point_cloud_capability import layer_kind_by_class
    return layer_kind_by_class(layer)


def resolve_layer(reference: Any, project=None):
    """Project layer from a layer object, an id or a name (first match); None when absent."""
    if reference is None:
        return None
    project = _project(project)
    if not isinstance(reference, str):
        try:
            return project.mapLayer(reference.id())
        except (AttributeError, RuntimeError):
            return None
    layer = project.mapLayer(reference)
    if layer is not None:
        return layer
    matches = project.mapLayersByName(reference)
    return matches[0] if matches else None


def _name(layer, fallback: str = "?") -> str:
    try:
        return layer.name()
    except (AttributeError, RuntimeError):
        return fallback


def _project_targets(layers: Iterable, project, exclude_id: Optional[str], report: OperationReport):
    """(TargetSpec list, layers) of the filterable project layers; the others go to ``report.skipped``."""
    from ...core.domain.cross_filter import TargetSpec
    specs, kept = [], []
    seen = set()
    for reference in layers or []:
        layer = resolve_layer(reference, project)
        label = reference if isinstance(reference, str) else _name(reference)
        if layer is None:
            report.skipped[label] = NOT_IN_PROJECT if not isinstance(reference, str) else "layer not found"
            continue
        if layer.id() == exclude_id:
            report.skipped[layer.name()] = "the source layer itself"
            continue
        if layer.id() in seen:
            continue
        kind = layer_kind(layer)
        if kind is LayerKind.OTHER:
            report.skipped[layer.name()] = NOT_FILTERABLE
            continue
        seen.add(layer.id())
        specs.append(TargetSpec(layer.id(), kind))
        kept.append(layer)
    return specs, kept


def _service(service=None):
    """The dock's service: its history is the one the dock's Undo / Redo read."""
    from ...core.services.cross_filter_service import get_cross_filter_service
    return service or get_cross_filter_service()


_API_SERVICE = None


def _api_service():
    """Service with its own history, for the operations the dock cannot undo.

    The dock undoes a vector source through its own vector history (linked
    runs): an operation pushed under a vector layer id there would be popped
    by the next dock Undo of that layer, in the wrong order. Vector sources,
    geometries, layers outside the project and unfilter operations are kept
    apart; raster / point cloud sources of the project share the dock's
    history (the dock undoes them the same way).
    """
    global _API_SERVICE
    if _API_SERVICE is None:
        from ...core.services.cross_filter_service import CrossFilterService
        _API_SERVICE = CrossFilterService()
    return _API_SERVICE


def _busy() -> str:
    """Error message while a cross filter of the dock still runs in the background, "" otherwise."""
    try:
        from ...core.services.cross_filter_service import _finished, get_cross_filter_service
        running = [task for task in get_cross_filter_service()._running if not _finished(task)]
    except Exception:
        return ""
    return "a FilterMate filter is still running in the background: try again when it ends" if running else ""


def _install_registry(project) -> None:
    """Hook that writes original sources in the project file (a dock never opened has not installed it)."""
    from ..qgis.coverage_layers.snapshots import registry
    registry().install(project)


def _collect(task, project, report: OperationReport) -> OperationReport:
    """Copy the outcomes of a finished cross filter task into ``report``."""
    if task.error:
        report.error = task.error
        return report
    changed_ids = {after.layer_id for _, after in task.changes}
    # The source is not a target: it stays out of ``done`` (Processing OUTPUT, export chains).
    report.details["source_filtered"] = (task.source_job.layer_id in changed_ids
                                         and task.source_job.kind is not LayerKind.OTHER)
    per_layer = {}
    for outcome in task.outcomes:
        layer = project.mapLayer(outcome.layer_id)
        name = _name(layer, outcome.layer_id) if layer is not None else outcome.layer_id
        if outcome.success:
            report.done[outcome.layer_id] = name
            per_layer[name] = {"kept": outcome.kept_count, "seconds": round(outcome.elapsed, 2)}
        else:
            report.failed[name] = outcome.message or "failed"
    report.details["layers"] = per_layer
    report.details["source"] = dict(task.source_job.details)
    return report


# --- cross filter --------------------------------------------------------------

def cross_filter(source, targets: Sequence, predicates: Sequence[str] = ("Intersect",), buffer: float = 0.0,
                 coverage_min: float = 0.0, operator: Optional[str] = None, selected_only: bool = True,
                 raster_selection=None, point_cloud_criteria=None, source_operator: Optional[str] = None,
                 filter_source: bool = False, footprint_resolution: Optional[float] = None,
                 max_pixels: Optional[int] = None, project=None, service=None) -> OperationReport:
    """Filter ``targets`` (any kind) by the selection made on ``source`` (any kind).

    Args:
        source: Source layer (object, id or name). A layer object outside the
            project (a model output) is accepted: it is read, never filtered.
        targets: Layers to filter; layers outside the project are skipped.
        predicates: FILTERING predicate labels (see :data:`api_requests.PREDICATES`).
        buffer: Buffer of the source geometry (source CRS units, metres for a geographic CRS).
        coverage_min: Minimum share (%) of a polygon target inside the source geometry.
        operator: Combination with each target's previous filter, None to replace it.
        selected_only: Vector source: use the selected features (all when none is selected).
        raster_selection: Raster source: :class:`RasterSelection` of the pixels kept (required).
        point_cloud_criteria: Point cloud source: :class:`PointCloudFilterCriteria` or an
            expression string applied to the source first; None = its current points.
        source_operator: Combination of ``point_cloud_criteria`` with the source's subset.
        filter_source: Raster source: also mask the source raster outside the selection.
        footprint_resolution: Point cloud source: cell size of the footprint (default: config, 2 m).
        max_pixels: Raster source: maximum pixels read (default: config, 4 000 000).

    Returns:
        The report; ``done`` lists the target layers filtered (the source only
        when there is no target), ``details["source_filtered"]`` tells whether
        the source changed.
    """
    from ...core.domain.cross_filter import CrossFilterRequest
    project = _project(project)
    report = OperationReport(error=_busy())
    if report.error:
        return report
    targets = list(targets or [])
    layer = resolve_layer(source, project) if isinstance(source, str) else source
    if layer is None:
        report.error = f"source layer not found: {source}"
        return report
    kind = layer_kind(layer)
    if kind is LayerKind.OTHER:
        report.error = f"'{_name(layer)}' is {NOT_FILTERABLE}"
        return report
    specs, _ = _project_targets(targets, project, layer.id(), report)
    if targets and not specs:
        report.error = "no filterable target layer"
        return report
    in_project = project.mapLayer(layer.id()) is not None
    service = service or (_service() if kind.is_coverage and in_project else _api_service())
    _install_registry(project)
    try:
        source_job = _source_job(layer, kind, report, selected_only=selected_only, raster_selection=raster_selection,
                                 point_cloud_criteria=point_cloud_criteria, source_operator=source_operator,
                                 filter_source=filter_source and in_project,
                                 footprint_resolution=footprint_resolution, max_pixels=max_pixels)
    except ValueError as exc:
        report.error = str(exc)
        return report
    if source_job is None:
        return report
    try:
        if not specs:
            _source_only(layer, kind, source_job, report, service, in_project)
        else:
            request = CrossFilterRequest(source_layer_id=layer.id(), source_kind=kind, targets=tuple(specs),
                                         predicates=tuple(predicates) or ("Intersect",),
                                         buffer_value=float(buffer or 0.0), coverage_min=float(coverage_min or 0.0),
                                         other_layers_combine_operator=operator)
            _collect(service.run(request, source_job, synchronous=True), project, report)
    except Exception as exc:  # never leave the source criteria applied after a failure
        logger.warning(f"[FM5] cross filter from '{_name(layer)}' failed: {exc}", exc_info=True)
        report.error = str(exc) or type(exc).__name__
    if report.error and kind is LayerKind.POINT_CLOUD:
        _restore_point_cloud_source(layer, source_job.before)
    return report


def _restore_point_cloud_source(layer, before) -> None:
    """Nothing was related: drop the criteria applied to the point cloud source."""
    try:
        if layer.subsetString() != before.subset:
            layer.setSubsetString(before.subset)
    except RuntimeError:
        pass


def _option(key: str, default):
    try:
        from ...core.services.cross_filter_service import _config_option
        return _config_option(key, default)
    except Exception:
        return default


def _source_job(layer, kind: LayerKind, report: OperationReport, selected_only: bool, raster_selection,
                point_cloud_criteria, source_operator, filter_source: bool, footprint_resolution, max_pixels):
    """Source job for ``layer``; None (with ``report.error`` set) when there is nothing to relate."""
    from ..qgis.coverage_layers import source_jobs
    if kind is LayerKind.VECTOR:
        features = list(layer.getSelectedFeatures() if selected_only and layer.selectedFeatureCount()
                        else layer.getFeatures())
        if not features:
            report.error = f"'{layer.name()}' has no feature to use"
            return None
        return source_jobs.VectorSourceJob(layer, features)
    if kind is LayerKind.RASTER:
        if raster_selection is None:
            raise ValueError("a raster source needs a pixel selection (range, classes or expression)")
        if raster_selection.band > layer.bandCount():
            raise ValueError(f"'{layer.name()}' has {layer.bandCount()} band(s), band {raster_selection.band} requested")
        pixels = int(max_pixels or _option('raster_selection_max_pixels', 4000000))
        return source_jobs.RasterSourceJob(layer, raster_selection, pixels, filter_source=filter_source)
    # Point cloud: the criteria become the source subset, its footprint is the source geometry.
    from ...core.domain.cross_filter import combine_subset
    from ..qgis.coverage_layers.snapshots import take_snapshot
    before = take_snapshot(layer, LayerKind.POINT_CLOUD)
    expression = point_cloud_criteria if isinstance(point_cloud_criteria, str) else (
        point_cloud_criteria.to_subset_string() if point_cloud_criteria is not None else "")
    expression = (expression or "").strip()
    if expression:
        if source_operator == "AND NOT" and not before.subset:
            raise ValueError("AND NOT needs an existing filter on the point cloud source")
        subset = combine_subset(before.subset, expression, source_operator)
        if not layer.setSubsetString(subset):
            layer.setSubsetString(before.subset)
            raise ValueError(f"the point cloud expression was rejected: {subset}")
    try:
        resolution = float(footprint_resolution or _option('point_cloud_footprint_resolution', 2.0))
        job = source_jobs.PointCloudSourceJob(layer, resolution, before=before)
    except Exception:
        _restore_point_cloud_source(layer, before)
        raise
    job.details["subset"] = layer.subsetString()
    return job


def _source_only(layer, kind: LayerKind, source_job, report: OperationReport, service, in_project: bool) -> OperationReport:
    """No target: filter the source itself (raster mask, point cloud subset), undoable."""
    from ...core.domain.filter_state import CrossOperation
    after = source_job.apply(layer) if in_project else None
    source_job.release()
    if after is None:
        if not report.skipped:
            report.error = "no target layer, and the source layer itself was not changed"
        else:
            report.error = "no filterable target layer"
        return report
    service.history.push(CrossOperation(layer.id(), ((source_job.before, after),), f"{kind.value} selection"))
    report.done[layer.id()] = layer.name()
    report.details["source_filtered"] = True
    return report


def cross_filter_by_geometry(geometry, crs, targets: Sequence, predicates: Sequence[str] = ("Intersect",),
                             buffer: float = 0.0, coverage_min: float = 0.0, operator: Optional[str] = None,
                             project=None, service=None) -> OperationReport:
    """Filter ``targets`` by a geometry (an extent, a drawn polygon) given in ``crs``.

    The operation has its own history (not the dock's): undo it with
    :func:`clear_filters` or the dock's Unfilter.
    """
    from qgis.core import QgsCoordinateTransform, QgsGeometry
    from ...core.domain.cross_filter import CrossFilterRequest
    from ..qgis.coverage_layers.source_jobs import FixedGeometrySourceJob
    project = _project(project)
    report = OperationReport(error=_busy())
    if report.error:
        return report
    if geometry is None or geometry.isNull() or geometry.isEmpty():
        report.error = "the geometry is empty"
        return report
    specs, layers = _project_targets(targets, project, None, report)
    if not specs:
        report.error = "no filterable target layer"
        return report
    anchor = layers[0]
    local = QgsGeometry(geometry)
    if crs is not None and crs.isValid() and crs != anchor.crs():
        local.transform(QgsCoordinateTransform(crs, anchor.crs(), project.transformContext()))
    request = CrossFilterRequest(source_layer_id=anchor.id(), source_kind=LayerKind.OTHER, targets=tuple(specs),
                                 predicates=tuple(predicates) or ("Intersect",), buffer_value=float(buffer or 0.0),
                                 coverage_min=float(coverage_min or 0.0), other_layers_combine_operator=operator)
    task = (service or _api_service()).run(request, FixedGeometrySourceJob(anchor, local.asWkt()), synchronous=True)
    return _collect(task, project, report)


# --- point clouds ----------------------------------------------------------------

def filter_point_clouds(layers: Sequence, criteria, operator: Optional[str] = None, project=None,
                        service=None) -> OperationReport:
    """Apply the same criteria (or expression) to several point clouds, as one undoable step."""
    from ...core.domain.cross_filter import combine_subset
    from ...core.domain.filter_state import CrossOperation
    from ..qgis.coverage_layers.snapshots import take_snapshot
    project = _project(project)
    report = OperationReport(error=_busy())
    if report.error:
        return report
    expression = criteria if isinstance(criteria, str) else (criteria.to_subset_string() if criteria is not None else "")
    expression = (expression or "").strip()
    if not expression:
        report.error = "no point cloud criteria: give classes, a range, a return number or an expression"
        return report
    changes = []
    for reference in layers or []:
        layer = resolve_layer(reference, project)
        label = reference if isinstance(reference, str) else _name(reference)
        if layer is None:
            report.skipped[label] = NOT_IN_PROJECT
            continue
        if layer_kind(layer) is not LayerKind.POINT_CLOUD:
            report.skipped[layer.name()] = "not a point cloud layer"
            continue
        before = take_snapshot(layer, LayerKind.POINT_CLOUD)
        if operator == "AND NOT" and not before.subset:
            # combine_subset would keep only the excluded points of an unfiltered cloud.
            report.failed[layer.name()] = "AND NOT needs an existing filter on the layer"
            continue
        subset = combine_subset(before.subset, expression, operator)
        if not layer.setSubsetString(subset):
            layer.setSubsetString(before.subset)
            report.failed[layer.name()] = f"expression rejected: {subset}"
            continue
        after = take_snapshot(layer, LayerKind.POINT_CLOUD)
        if not after.same_state(before):
            changes.append((before, after))
        report.done[layer.id()] = layer.name()
        layer.triggerRepaint()
    if changes:
        _service(service).history.push(CrossOperation(changes[0][0].layer_id, tuple(changes), 'point cloud filter'))
    if not report.done and not report.failed:
        report.error = "no point cloud layer to filter"
    report.details["expression"] = expression
    return report


# --- unfilter --------------------------------------------------------------------

def clear_filters(layers: Sequence, project=None, service=None) -> OperationReport:
    """Put layers of any kind back on their original source with no subset.

    Recorded in the automation history, not the dock's (the dock's own
    Unfilter records nothing either).
    """
    project = _project(project)
    report = OperationReport(error=_busy())
    if report.error:
        return report
    ids, kinds, names = [], {}, {}
    for reference in layers or []:
        layer = resolve_layer(reference, project)
        label = reference if isinstance(reference, str) else _name(reference)
        if layer is None:
            report.skipped[label] = NOT_IN_PROJECT
            continue
        kind = layer_kind(layer)
        if kind is LayerKind.OTHER:
            report.skipped[layer.name()] = NOT_FILTERABLE
            continue
        if layer.id() not in kinds:
            ids.append(layer.id())
        kinds[layer.id()] = kind
        names[layer.id()] = layer.name()
    if not ids:
        report.error = "no layer to clear"
        return report
    restored = (service or _api_service()).unfilter(ids[0], ids, kinds, project=project)
    for layer_id in restored:
        report.done[layer_id] = names.get(layer_id, layer_id)
    for layer_id in ids:
        if layer_id not in restored:
            report.skipped[names[layer_id]] = "not filtered"
    return report


# --- export ----------------------------------------------------------------------

def _unique_path(path: str, used: set) -> str:
    root, ext = path, ""
    for compound in (".copc.laz",):
        if path.lower().endswith(compound):
            root, ext = path[:-len(compound)], path[-len(compound):]
            break
    else:
        root, ext = os.path.splitext(path)
    candidate, index = path, 2
    while candidate.lower() in used:
        candidate = f"{root}_{index}{ext}"
        index += 1
    used.add(candidate.lower())
    return candidate


def export_layers(layers: Sequence, folder: str, vector_format: str = "GPKG", raster_format: str = "COG",
                  point_cloud_format: str = "LAZ", crs=None, feedback=None, project=None) -> OperationReport:
    """Write each layer as it is filtered now into ``folder``.

    Vector layers keep the features of their subset, rasters the pixels kept
    (NoData elsewhere), point clouds the points kept. One file per layer,
    named after the layer; ``report.outputs`` maps layer names to the files.

    Args:
        layers: Layers of any kind (objects, ids or names); layer objects outside the project are accepted.
        folder: Destination folder (created when missing).
        vector_format: Key of :data:`VECTOR_EXPORT_FORMATS`.
        raster_format: ``COG`` or ``GTiff``.
        point_cloud_format: ``LAZ``, ``COPC``, ``LAS``, ``GPKG`` or ``CSV``.
        crs: Optional output CRS (``QgsCoordinateReferenceSystem``).
        feedback: Optional ``QgsFeedback`` (progress, cancellation).
    """
    from ..qgis.coverage_layers.exporters import POINT_CLOUD_FORMATS, export_point_cloud, export_raster, output_path
    project = _project(project)
    report = OperationReport()
    if vector_format not in VECTOR_EXPORT_FORMATS:
        report.error = f"unknown vector format {vector_format!r}"
        return report
    if raster_format not in RASTER_EXPORT_FORMATS:
        report.error = f"unknown raster format {raster_format!r}"
        return report
    if point_cloud_format not in POINT_CLOUD_EXPORT_FORMATS:
        report.error = f"unknown point cloud format {point_cloud_format!r}"
        return report
    if not folder:
        report.error = "no output folder"
        return report
    os.makedirs(folder, exist_ok=True)
    resolved = []
    for reference in layers or []:
        layer = resolve_layer(reference, project) if isinstance(reference, str) else reference
        if layer is None:
            report.skipped[str(reference)] = "layer not found"
            continue
        resolved.append(layer)
    used: set = set()
    total = max(1, len(resolved))
    for index, layer in enumerate(resolved):
        if feedback is not None and feedback.isCanceled():
            report.error = "canceled"
            break
        kind = layer_kind(layer)
        name = layer.name()
        try:
            if kind is LayerKind.VECTOR:
                driver, extension = VECTOR_EXPORT_FORMATS[vector_format]
                ok, path, message = _export_vector(layer, _unique_path(output_path(folder, name, extension), used),
                                                   driver, crs, project)
            elif kind is LayerKind.RASTER:
                block, release = _raster_feedback(feedback, index, total)
                try:
                    result = export_raster(layer, _unique_path(output_path(folder, name, '.tif'), used),
                                           raster_format, crs, feedback=block)
                finally:
                    release()
                ok, path, message = result.success, result.path, result.message
            elif kind is LayerKind.POINT_CLOUD:
                path = _unique_path(output_path(folder, name, POINT_CLOUD_FORMATS[point_cloud_format]), used)
                result = export_point_cloud(layer, path, point_cloud_format, crs)
                ok, path, message = result.success, result.path, result.message
            else:
                report.skipped[name] = NOT_FILTERABLE
                continue
        except Exception as exc:  # one layer must not stop the others
            logger.warning(f"[FM5] export of '{name}' failed: {exc}", exc_info=True)
            ok, path, message = False, '', str(exc)
        if ok:
            report.done[layer.id()] = name
            report.outputs[name] = path
            if message:
                report.details.setdefault("notes", {})[name] = message
        else:
            report.failed[name] = message or "export failed"
        if feedback is not None:
            feedback.setProgress(100.0 * (index + 1) / total)
    return report


def _raster_feedback(feedback, index: int, total: int):
    """``(QgsRasterBlockFeedback, release)`` relaying progress and cancellation to ``feedback``.

    ``QgsRasterFileWriter`` refuses any other feedback type (a Processing
    feedback raises TypeError): a block feedback forwards the write progress
    as this layer's share of the export, and a cancel request stops the write.
    """
    from qgis.core import QgsRasterBlockFeedback
    if feedback is None or isinstance(feedback, QgsRasterBlockFeedback):
        return feedback, lambda: None
    block = QgsRasterBlockFeedback()

    def _progress(value):
        feedback.setProgress(100.0 * (index + value / 100.0) / max(1, total))

    block.progressChanged.connect(_progress)
    if feedback.isCanceled():
        block.cancel()
    feedback.canceled.connect(block.cancel)

    def _release():
        for signal, slot in ((feedback.canceled, block.cancel), (block.progressChanged, _progress)):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass

    return block, _release


def _export_vector(layer, path: str, driver: str, crs, project) -> Tuple[bool, str, str]:
    """``QgsVectorFileWriter`` honours the subset string: only the filtered features are written."""
    from qgis.core import QgsCoordinateTransform, QgsVectorFileWriter
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = driver
    options.fileEncoding = "UTF-8"
    options.layerName = layer.name()
    if crs is not None and crs.isValid() and crs != layer.crs():
        options.ct = QgsCoordinateTransform(layer.crs(), crs, project.transformContext())
    result = QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, project.transformContext(), options)
    error, message = result[0], result[1] if len(result) > 1 else ""
    written = result[2] if len(result) > 2 and result[2] else path
    if error != QgsVectorFileWriter.WriterError.NoError:
        return False, path, message or f"vector writer error {error}"
    return True, written, ""


# --- favorites -------------------------------------------------------------------

def find_favorites_service(plugin=None):
    """The FavoritesService of the running plugin, or None (headless, plugin not loaded)."""
    candidates = [plugin, getattr(plugin, 'app', None)]
    try:
        from qgis.utils import plugins
        loaded = plugins.get('filter_mate')
        candidates += [loaded, getattr(loaded, 'app', None)]
    except Exception:
        pass
    for candidate in candidates:
        service = getattr(candidate, 'favorites_manager', None) if candidate is not None else None
        if service is not None and hasattr(service, 'get_favorite'):
            return service
    return None


def _project_backup_favorites(project) -> List[Any]:
    """Favorites saved in the project file (``FilterMate/favorites_backup``): headless fallback."""
    from ...core.domain.favorites_manager import FilterFavorite
    try:
        data, ok = project.readEntry("FilterMate", "favorites_backup", "")
        entries = json.loads(data).get('favorites', []) if ok and data else []
    except (ValueError, TypeError, AttributeError):
        return []
    favorites = []
    for entry in entries:
        try:
            favorites.append(FilterFavorite.from_dict(dict(entry)))
        except Exception as exc:
            logger.debug(f"[FM5] favorite backup entry skipped: {exc}")
    return favorites


def list_favorites(service=None, project=None) -> List[Any]:
    """Favorites of the running plugin, or those saved in the project file."""
    service = service or find_favorites_service()
    if service is not None:
        try:
            return list(service.get_all_favorites() or [])
        except Exception as exc:
            logger.warning(f"[FM5] favorites unavailable: {exc}")
    return _project_backup_favorites(_project(project))


def find_favorite(name_or_id: str, service=None, project=None):
    """Favorite by id, then by name (case-insensitive); None when absent."""
    service = service or find_favorites_service()
    if service is not None:
        for getter in ('get_favorite', 'get_favorite_by_name'):
            try:
                favorite = getattr(service, getter)(name_or_id)
            except Exception:
                favorite = None
            if favorite is not None:
                return favorite
    wanted = (name_or_id or "").strip().lower()
    for favorite in list_favorites(service, project):
        if favorite.id == name_or_id or (favorite.name or "").strip().lower() == wanted:
            return favorite
    return None


def _favorite_layer(project, signature: Optional[str], layer_id: Optional[str], name: Optional[str], by_signature):
    if signature and signature in by_signature:
        return by_signature[signature]
    if layer_id:
        layer = project.mapLayer(layer_id)
        if layer is not None:
            return layer
    if name:
        matches = project.mapLayersByName(name)
        if matches:
            return matches[0]
    return None


def apply_favorite(name_or_id: str, service=None, project=None) -> OperationReport:
    """Apply a favorite: its subset strings, then its raster / point cloud clips.

    Same behaviour as the dock's favorites menu (subsets pushed directly,
    layers resolved by signature, then id, then name). Works headless from
    the favorites saved in the project file when the plugin is not loaded.
    """
    from ...core.domain.layer_signature import LayerSignature
    from ...infrastructure.database.sql_utils import safe_set_subset_string
    from ..qgis.coverage_layers import favorites_bridge
    project = _project(project)
    report = OperationReport(error=_busy())
    if report.error:
        return report
    service = service or find_favorites_service()
    favorite = find_favorite(name_or_id, service, project)
    if favorite is None:
        report.error = f"favorite not found: {name_or_id}"
        return report
    by_signature = {}
    for layer in project.mapLayers().values():
        try:
            by_signature[LayerSignature.compute(layer)] = layer
        except Exception:
            pass
    spatial = favorite.spatial_config if isinstance(favorite.spatial_config, dict) else {}
    coverage = spatial.get(favorites_bridge.COVERAGE_KEY) or []
    entries = []
    if favorite.expression or favorite.remote_layers or not coverage:
        entries.append((favorite.layer_name or "source", favorite.expression or "",
                        _favorite_layer(project, spatial.get('source_layer_signature'), favorite.layer_id,
                                        favorite.layer_name, by_signature)))
    for key, payload in (favorite.remote_layers or {}).items():
        payload = payload if isinstance(payload, dict) else {}
        signature = payload.get('layer_signature') or (key if isinstance(key, str) and '::' in key else None)
        name = payload.get('display_name') or (key if isinstance(key, str) and '::' not in key else None)
        entries.append((name or str(key), payload.get('expression', '') or '',
                        _favorite_layer(project, signature, payload.get('layer_id'), name, by_signature)))
    for label, expression, layer in entries:
        if layer is None:
            report.skipped[label] = "layer not found in this project"
            continue
        try:
            if safe_set_subset_string(layer, expression):
                report.done[layer.id()] = layer.name()
            else:
                report.failed[layer.name()] = "subset rejected by the provider"
        except Exception as exc:
            report.failed[layer.name()] = str(exc)
    if coverage:
        _install_registry(project)
        applied: List[str] = []
        try:
            handled = favorites_bridge.apply(coverage, project=project, synchronous=True, kind_of=layer_kind,
                                             applied=applied)
        except Exception as exc:  # a stored source that no longer opens
            logger.warning(f"[FM5] favorite clips not applied: {exc}", exc_info=True)
            report.failed[favorite.name or name_or_id] = f"raster / point cloud clips not applied: {exc}"
            handled = 0
        for layer_id in applied:
            layer = project.mapLayer(layer_id)
            if layer is not None:
                report.done[layer_id] = layer.name()
        if handled < len(coverage):
            report.details["coverage_layers_missing"] = len(coverage) - handled
        report.details["coverage_layers"] = handled
    if report.done and service is not None:
        try:
            service.mark_favorite_used(favorite.id)
        except Exception as exc:
            logger.debug(f"[FM5] favorite use count not updated: {exc}")
    if not report.done and not report.error:
        report.error = f"favorite '{favorite.name}' matched no layer of this project"
    report.details["favorite"] = {"id": favorite.id, "name": favorite.name}
    return report


# --- status ----------------------------------------------------------------------

def filter_state(project=None) -> List[Dict[str, Any]]:
    """Every filtered layer of the project: name, kind, subset, derived source."""
    from ..qgis.coverage_layers.snapshots import take_snapshot
    project = _project(project)
    rows = []
    for layer in project.mapLayers().values():
        kind = layer_kind(layer)
        if kind is LayerKind.OTHER:
            continue
        try:
            snapshot = take_snapshot(layer, kind)
        except Exception:
            continue
        if not snapshot.subset and not snapshot.derived:
            continue
        rows.append({"id": layer.id(), "name": layer.name(), "kind": kind.value, "subset": snapshot.subset,
                     "derived": bool(snapshot.derived), "source": layer.source() if snapshot.derived else ""})
    return rows

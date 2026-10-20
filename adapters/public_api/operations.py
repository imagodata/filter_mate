# -*- coding: utf-8 -*-
"""
FilterMate operations usable without the dock (FilterMate 5).

One implementation behind the three automation surfaces:

* the public Python API (:class:`FilterMatePublicAPI`, other plugins, console scripts);
* the Processing algorithms (``filtermate:*``, models, batch, ``qgis_process``);
* the REST API (``filtermate_api``).

Every operation runs synchronously on the main thread, one at a time
(:func:`busy_reason`), changes the project layers in place like the dock
does, and records its changes in the cross filter history so the dock's
Undo / Redo / Unfilter buttons can revert them. A ``feedback``
(``QgsFeedback``, Processing's) receives the progress and can cancel. The
derived files nothing refers to any more are removed after each filter.
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
import functools
import json
import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ...core.domain.api_requests import (
    OperationReport,
    POINT_CLOUD_EXPORT_FORMATS,
    RASTER_EXPORT_FORMATS,
    VECTOR_EXPORT_FORMATS,
    relation_numbers,
)
from ...core.domain.layer_kind import LayerKind

logger = logging.getLogger(__name__)

NOT_IN_PROJECT = "not in the project: a filter on a temporary layer would be lost"
NOT_FILTERABLE = "not a vector, raster or point cloud layer FilterMate can filter"
TILES_TARGET_ONLY = "vector tiles are filter targets only, never a source"


def _tr(text: str) -> str:
    """Translate automation diagnostics, with a plain-text fallback outside Qt."""
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        translated = QCoreApplication.translate('FilterMateOperations', text)
        return translated if isinstance(translated, str) else text
    except ImportError:
        return text


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
            report.skipped[_report_label(report, layer.name(), layer.id())] = "the source layer itself"
            continue
        if layer.id() in seen:
            continue
        kind = layer_kind(layer)
        from ..qgis.point_cloud_capability import is_non_analysis_raster
        if is_non_analysis_raster(layer):
            report.skipped[_report_label(report, layer.name(), layer.id())] = _tr(
                "rendered or unsupported raster: cannot be a filter target")
            continue
        if kind is LayerKind.OTHER:
            report.skipped[_report_label(report, layer.name(), layer.id())] = NOT_FILTERABLE
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


# Name of the operation running now: one at a time (see busy_reason).
_RUNNING: List[str] = []

BACKGROUND_BUSY = "a FilterMate filter is still running in the background: try again when it ends"


# Dock tasks an operation must not overlap, by class (their descriptions are
# translated or shared with harmless tasks, e.g. "FilterMate: Evaluating ..."):
# - FilterEngineTask: the vector engine applies its subsets when it ends,
#   over the operation's;
# - CrossFilterTask: a cross filter of the dock, same story for any kind;
# - CoverageExportTask: an export of the dock reads the layers as filtered;
# - HeightAboveGroundTask: when it ends it swaps the point cloud to its
#   enriched copy and puts back the subset of its start, over the operation's.
_CONFLICTING_TASKS = frozenset({"FilterEngineTask", "CrossFilterTask", "CoverageExportTask", "HeightAboveGroundTask"})


def _background_tasks_running(allow_finishing: bool = False) -> bool:
    """A dock or automation task still changes or reads the filters.

    Args:
        allow_finishing: a dock task in its ``finished()`` does not count. Only
            for the start of a server filter (server_subset_job): the dock
            applies that task's own server subsets there. Everything else,
            busy_reason() included, waits until ``finished()`` returns, so an
            API call cannot start in the middle of it (2026-10-20).
    """
    try:
        from ...core.services.cross_filter_service import _finished, get_cross_filter_service
        services = [get_cross_filter_service()]
        if _API_SERVICE is not None and _API_SERVICE is not services[0]:
            services.append(_API_SERVICE)
        if any(not _finished(task) for service in services for task in service._running):
            return True
        from qgis.core import QgsApplication
        # Not activeTasks(): it drops a task in its finished() as soon as another
        # task is queued (a server filter queues one), tasks() lists it until
        # finished() returns (QGIS 3.22 - 4.2, 2026-10-20).
        tasks = list(QgsApplication.taskManager().tasks())
    except Exception:
        return False

    def finishing(task):
        # QGIS still lists a task while its finished() runs on the main
        # thread, where the dock applies that task's own (server) subsets.
        try:
            from qgis.core import QgsTask
            return task.status() in (QgsTask.TaskStatus.Complete, QgsTask.TaskStatus.Terminated)
        except Exception:
            return False

    return any(type(task).__name__ in _CONFLICTING_TASKS and not (allow_finishing and finishing(task))
               for task in tasks)


def busy_reason() -> str:
    """Why an operation cannot start now, "" when it can.

    One at a time: refused while another operation runs (a REST call can
    re-enter through processEvents while an export writes), and while a
    FilterMate task of the dock runs in the background.
    """
    if _RUNNING:
        return f"FilterMate is already running {_RUNNING[0]}: try again when it ends"
    from ...core.filter.server_filter_state import server_filter_pending
    if server_filter_pending():
        return BACKGROUND_BUSY
    return BACKGROUND_BUSY if _background_tasks_running() else ""


def _tidy_cache(project=None) -> None:
    """Remove the derived files nothing refers to any more, keep the cache under its limit.

    The dock tidies after its own runs only: a session driven by Processing,
    the Python API or REST (``qgis_process`` included) never did.
    """
    try:
        from ...core.services.cross_filter_service import tidy_cache
        tidy_cache(project)
    except Exception as exc:
        logger.debug(f"[FM5] cache not tidied: {exc}")


def _exclusive(tidy: bool = True):
    """Run the operation alone (refused with ``details["busy"]`` while FilterMate is busy).

    ``tidy``: the operation filters layers, the cache is tidied once it is over.
    """
    def decorate(operation):
        @functools.wraps(operation)
        def run(*args, **kwargs) -> OperationReport:
            reason = busy_reason()
            if reason:
                report = OperationReport(error=reason)
                report.details["busy"] = True
                return report
            _RUNNING.append(operation.__name__)
            try:
                return operation(*args, **kwargs)
            finally:
                _RUNNING.clear()
                if tidy:
                    _tidy_cache(kwargs.get("project"))
        return run
    return decorate


def _run_task(service, request, source_job, feedback=None, apply_results=None):
    """Compute in one Qt worker thread while Qt keeps serving events, then apply on main.

    Automation waits for the result, but remote raster materialization must
    never run on the caller's main thread. The worker is a QThread, like the
    QgsTask threads of the dock: the WCS and WFS providers start Qt timers in
    the thread that reads, which a plain Python thread has no event dispatcher
    for (QGIS 3.44 then crashed in the WCS download). Only apply_results
    touches project layers. Progress is queued explicitly so feedback runs on main.
    """
    from queue import Empty, SimpleQueue
    from qgis.PyQt.QtCore import QEventLoop, QThread, QTimer, Qt

    task = service.build_task(request, source_job)

    def apply(result):
        if apply_results is None:
            task.apply_results(result)
        else:
            apply_results(task, result)

    outcome = {}

    class Worker(QThread):
        def run(self):
            try:
                outcome['result'] = task.run()
            except BaseException as exc:  # re-raised on main, once applied
                outcome['error'] = exc
            finally:
                outcome['done'] = True

    def release_lease():
        # cancel_all() and on_done may replace the list while Qt processes events.
        # Remove only this lease, preserving any other tasks registered meanwhile.
        service._running = [running for running in service._running if running is not task]

    loop = QEventLoop()
    timer = QTimer()
    progress = SimpleQueue()
    links = []
    if feedback is not None:
        # A direct connection only enqueues a number, never calls GUI code.
        connection = getattr(Qt, 'ConnectionType', Qt).DirectConnection
        task.progressChanged.connect(progress.put, connection)
        feedback.canceled.connect(task.cancel)
        links = [(task.progressChanged, progress.put), (feedback.canceled, task.cancel)]
        if feedback.isCanceled():
            task.cancel()

    # This task is not submitted to QgsTaskManager, so its QGIS status stays
    # Queued. Keep a service lease for unload cancellation while it reads; it
    # is released before apply, which may install a server filter that refuses
    # to start while a FilterMate task still reads layers (see
    # _background_tasks_running for the dock's tasks).
    service._running.append(task)
    worker = Worker()

    def poll():
        if outcome.get('done'):
            loop.quit()  # first: a failing feedback below must not keep the nested loop running
        if feedback is not None:
            while True:
                try:
                    value = progress.get_nowait()
                except Empty:
                    break
                feedback.setProgress(value)
            if feedback.isCanceled():
                task.cancel()

    timer.timeout.connect(poll)
    try:
        try:
            worker.start()
            if not worker.isRunning() and not worker.isFinished():
                raise RuntimeError("the FilterMate worker thread could not start")
            timer.start(10)
            # Re-enter if an unrelated event quits the nested loop early.
            while not outcome.get('done'):
                loop.exec()
            poll()
        except BaseException:
            task.cancel()
            # Do not release worker-owned providers/files while run uses them.
            worker.wait()
            release_lease()
            apply(False)
            raise
        finally:
            timer.stop()
        worker.wait()
        release_lease()
        if links:
            # Applying cannot be stopped half way: a Cancel now must not report applied targets as canceled.
            _disconnect(links.pop())
        if 'error' in outcome:
            task.cancel()
            apply(False)
            raise outcome['error']
        apply(outcome.get('result') and not task.isCanceled())
    finally:
        release_lease()
        _disconnect(*links)
    return task


def _task_failure(task, layer_id: str) -> str:
    """Why ``task`` left ``layer_id`` unfiltered, "" when it filtered it."""
    if task.error:
        return task.error
    if task.isCanceled():
        return "canceled"
    for outcome in task.outcomes:
        if outcome.layer_id == layer_id:
            return "" if outcome.success else (outcome.message or "failed")
    return "layer not found"


def _disconnect(*connections) -> None:
    for signal, slot in connections:
        try:
            signal.disconnect(slot)
        except (TypeError, RuntimeError):
            pass


def _canceled(feedback) -> bool:
    return feedback is not None and feedback.isCanceled()


def _unexpected(report: OperationReport, exc: Exception, label: Optional[str] = None) -> str:
    """Message of an unexpected exception, flagged in ``report.details``.

    Kept for the local caller (Processing log, Python console); a remote
    REST client gets a generic message instead (``internal_error`` /
    ``internal_failures``): paths of the cache, SQL, module names.
    """
    message = str(exc) or type(exc).__name__
    if label is None:
        report.details["internal_error"] = True
    else:
        report.details.setdefault("internal_failures", []).append(label)
    return message


def _install_registry(project) -> None:
    """Hook that writes original sources in the project file (a dock never opened has not installed it)."""
    from ..qgis.coverage_layers.snapshots import registry
    registry().install(project)


def _collect(task, project, report: OperationReport) -> OperationReport:
    """Copy the outcomes of a finished cross filter task into ``report``."""
    if task.error:
        report.error = task.error
        return report
    if task.isCanceled():
        # Targets computed before the cancel were not applied (apply_results(False)).
        report.error = "canceled"
        return report
    changed_ids = {after.layer_id for _, after in task.changes}
    # The source is not a target: it stays out of ``done`` (Processing OUTPUT, export chains).
    report.details["source_filtered"] = (task.source_job.layer_id in changed_ids
                                         and task.source_job.kind is not LayerKind.OTHER)
    per_layer = {}
    for outcome in task.outcomes:
        layer = project.mapLayer(outcome.layer_id)
        name = _name(layer, outcome.layer_id) if layer is not None else outcome.layer_id
        label = _report_label(report, name, outcome.layer_id)
        if outcome.success:
            report.done[outcome.layer_id] = label
            per_layer[label] = {"kept": outcome.kept_count, "seconds": round(outcome.elapsed, 2)}
            if outcome.details.get('capture_resampled'):
                per_layer[label]['resampled'] = True
                per_layer[label]['capture_grid'] = outcome.details.get('capture_grid')
            if outcome.details.get('partial'):
                # A web service read up to its budget: the features kept are exact, some may be missing.
                per_layer[label]['partial'] = outcome.message
        else:
            report.failed[label] = outcome.message or "failed"
    report.details["layers"] = per_layer
    report.details["source"] = dict(task.source_job.details)
    return report


# --- cross filter --------------------------------------------------------------

@_exclusive()
def cross_filter(source, targets: Sequence, predicates: Sequence[str] = ("Intersect",), buffer: float = 0.0,
                 coverage_min: float = 0.0, operator: Optional[str] = None, selected_only: bool = True,
                 raster_selection=None, point_cloud_criteria=None, source_operator: Optional[str] = None,
                 filter_source: bool = False, footprint_resolution: Optional[float] = None,
                 max_pixels: Optional[int] = None, project=None, service=None, feedback=None) -> OperationReport:
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
            A web service source (WFS, OGC API, ArcGIS) must be selected or filtered:
            it is never read whole; its rows are read within the remote budgets in the
            worker, and an incomplete copy is refused.
        raster_selection: Raster source: :class:`RasterSelection` of the pixels kept (required).
        point_cloud_criteria: Point cloud source: :class:`PointCloudFilterCriteria` or an
            expression string applied to the source first; None = its current points.
        source_operator: Combination of ``point_cloud_criteria`` with the source's subset.
        filter_source: Raster source: also mask the source raster outside the selection.
        footprint_resolution: Point cloud source: cell size of the footprint (default: config, 2 m).
        max_pixels: Raster source: pixels read at the native resolution, a coarser grid beyond
            (default: config, 100 000 000).
        feedback: Optional ``QgsFeedback``: progress over the targets, cancellation.

    Returns:
        The report; ``done`` lists the target layers filtered (the source only
        when there is no target), ``details["source_filtered"]`` tells whether
        the source changed.
    """
    from ...core.domain.cross_filter import CrossFilterRequest
    project = _project(project)
    report = OperationReport()
    targets = list(targets or [])
    layer = resolve_layer(source, project) if isinstance(source, str) else source
    if layer is None:
        report.error = f"source layer not found: {source}"
        return report
    kind = layer_kind(layer)
    if kind is LayerKind.OTHER:
        report.error = f"'{_name(layer)}' is {NOT_FILTERABLE}"
        return report
    if kind is LayerKind.VECTOR_TILE:
        report.error = f"'{_name(layer)}': {TILES_TARGET_ONLY}"
        return report
    specs, _ = _project_targets(targets, project, layer.id(), report)
    if targets and not specs:
        report.error = "no filterable target layer"
        return report
    try:
        buffer, coverage_min = relation_numbers(buffer, coverage_min)
    except ValueError as exc:
        report.error = str(exc)
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
            _source_only(layer, kind, source_job, report, service, in_project, feedback, project=project)
        else:
            request = CrossFilterRequest(source_layer_id=layer.id(), source_kind=kind, targets=tuple(specs),
                                         predicates=tuple(predicates) or ("Intersect",),
                                         buffer_value=buffer, coverage_min=coverage_min,
                                         other_layers_combine_operator=operator)
            _collect(_run_task(service, request, source_job, feedback), project, report)
    except Exception as exc:  # never leave the source criteria applied after a failure
        logger.warning(f"[FM5] cross filter from '{_name(layer)}' failed: {exc}", exc_info=True)
        report.error = _unexpected(report, exc)
    if _canceled(feedback) and not report.error and not report.done:  # applied targets stay reported
        report.error = "canceled"
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
        from ..qgis.source_capability_probe import capability_for_layer
        capability = capability_for_layer(layer)
        if capability is not None and capability.is_remote_service:
            # 2026-10-20: never the whole service on the main thread: selected or
            # filtered, read bounded in the task, as the dock does (ValueError otherwise).
            return source_jobs.RemoteVectorSourceJob(layer, selected_only)
        features = list(layer.getSelectedFeatures() if selected_only and layer.selectedFeatureCount()
                        else layer.getFeatures())
        if not features:
            report.error = f"'{layer.name()}' has no feature to use"
            return None
        return source_jobs.VectorSourceJob(layer, features)
    if kind is LayerKind.RASTER:
        from ..qgis.source_capability_probe import capability_for_layer
        capability = capability_for_layer(layer)
        if capability is not None and not capability.has_raw_values:
            # Automation has no local rendered capture to supply to the job.
            raise ValueError(_tr("rendered raster sources require a local colour capture; numeric pixel selections are unavailable"))
        if raster_selection is None:
            raise ValueError("a raster source needs a pixel selection (range, classes or expression)")
        if raster_selection.band > layer.bandCount():
            raise ValueError(f"'{layer.name()}' has {layer.bandCount()} band(s), band {raster_selection.band} requested")
        # Read and bounded by the job (raster_adapter.source_max_pixels).
        pixels = max_pixels or _option('raster_source_max_pixels', None)
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


def _source_only(layer, kind: LayerKind, source_job, report: OperationReport, service, in_project: bool,
                 feedback=None, project=None) -> OperationReport:
    """No target: filter the source itself (raster mask, point cloud subset), undoable."""
    from ...core.domain.filter_state import CrossOperation
    if _canceled(feedback):
        source_job.release()
        report.error = "canceled"
        return report
    if in_project and kind is LayerKind.RASTER and getattr(source_job, 'clips_source', False):
        from ...core.domain.cross_filter import CrossFilterRequest
        request = CrossFilterRequest(source_layer_id=layer.id(), source_kind=kind, targets=())
        project = _project(project)

        def apply_source(task, result):
            # CrossFilterTask's default application resolves the project singleton.
            # Source-only operations must honor the explicitly supplied project.
            from ..qgis.coverage_layers import cache
            try:
                if result and cache.is_closed():
                    task.error = _tr("FilterMate was unloaded")
                    result = False
                current = project.mapLayer(layer.id())
                after = source_job.apply(current) if result and current is not None else None
                if after is not None:
                    task.changes.append((source_job.before, after))
                    service.history.push(CrossOperation(
                        layer.id(), ((source_job.before, after),), f"{kind.value} selection"))
            finally:
                try:
                    cache.settle(getattr(source_job, 'outputs', ()))
                finally:
                    source_job.release()

        task = _run_task(service, request, source_job, feedback, apply_results=apply_source)
        _collect(task, project, report)
        if report.error:
            return report
        if report.details.get("source_filtered"):
            report.done[layer.id()] = _report_label(report, layer.name(), layer.id())
        else:
            report.error = source_job.message or _tr("the source layer itself was not changed")
        return report
    after = source_job.apply(layer) if in_project else None
    source_job.release()
    if after is None:
        if not report.skipped:
            report.error = "no target layer, and the source layer itself was not changed"
        else:
            report.error = "no filterable target layer"
        return report
    service.history.push(CrossOperation(layer.id(), ((source_job.before, after),), f"{kind.value} selection"))
    report.done[layer.id()] = _report_label(report, layer.name(), layer.id())
    report.details["source_filtered"] = True
    return report


@_exclusive()
def cross_filter_by_geometry(geometry, crs, targets: Sequence, predicates: Sequence[str] = ("Intersect",),
                             buffer: float = 0.0, coverage_min: float = 0.0, operator: Optional[str] = None,
                             project=None, service=None, feedback=None) -> OperationReport:
    """Filter ``targets`` by a geometry (an extent, a drawn polygon) given in ``crs``.

    The operation has its own history (not the dock's): undo it with
    :func:`clear_filters` or the dock's Unfilter. ``feedback``: progress, cancellation.
    """
    from qgis.core import QgsCoordinateTransform, QgsGeometry
    from ...core.domain.cross_filter import CrossFilterRequest
    from ..qgis.coverage_layers.source_jobs import FixedGeometrySourceJob
    project = _project(project)
    report = OperationReport()
    if geometry is None or geometry.isNull() or geometry.isEmpty():
        report.error = "the geometry is empty"
        return report
    specs, layers = _project_targets(targets, project, None, report)
    if not specs:
        report.error = "no filterable target layer"
        return report
    anchor = layers[0]
    try:
        buffer, coverage_min = relation_numbers(buffer, coverage_min)
        local = QgsGeometry(geometry)
        if crs is not None and crs.isValid() and crs != anchor.crs():
            # QgsCsException when the geometry lies outside the target CRS's area.
            local.transform(QgsCoordinateTransform(crs, anchor.crs(), project.transformContext()))
        request = CrossFilterRequest(source_layer_id=anchor.id(), source_kind=LayerKind.OTHER, targets=tuple(specs),
                                     predicates=tuple(predicates) or ("Intersect",), buffer_value=buffer,
                                     coverage_min=coverage_min, other_layers_combine_operator=operator)
        task = _run_task(service or _api_service(), request, FixedGeometrySourceJob(anchor, local.asWkt()), feedback)
    except ValueError as exc:  # buffer / coverage
        report.error = str(exc)
        return report
    except Exception as exc:  # QgsCsException out of the CRS area, failing job
        logger.warning(f"[FM5] geometry filter failed: {exc}", exc_info=True)
        report.error = _unexpected(report, exc)
        return report
    _collect(task, project, report)
    if _canceled(feedback) and not report.error and not report.done:  # applied targets stay reported
        report.error = "canceled"
    return report


# --- point clouds ----------------------------------------------------------------

@_exclusive()
def filter_point_clouds(layers: Sequence, criteria, operator: Optional[str] = None, project=None,
                        service=None, feedback=None) -> OperationReport:
    """Apply the same criteria (or expression) to several point clouds, as one undoable step.

    A cancel request (``feedback``) stops before the next layer: the layers
    already filtered stay so, in the undoable step.
    """
    from ...core.domain.cross_filter import combine_subset
    from ...core.domain.filter_state import CrossOperation
    from ..qgis.coverage_layers.snapshots import take_snapshot
    project = _project(project)
    report = OperationReport()
    expression = criteria if isinstance(criteria, str) else (criteria.to_subset_string() if criteria is not None else "")
    expression = (expression or "").strip()
    if not expression:
        report.error = "no point cloud criteria: give classes, a range, a return number or an expression"
        return report
    changes = []
    references = list(layers or [])
    for index, reference in enumerate(references):
        if _canceled(feedback):
            report.error = "canceled"
            break
        if feedback is not None:
            feedback.setProgress(100.0 * index / len(references))
        layer = resolve_layer(reference, project)
        label = reference if isinstance(reference, str) else _name(reference)
        if layer is None:
            report.skipped[label] = NOT_IN_PROJECT
            continue
        name = _report_label(report, layer.name(), layer.id())
        if layer_kind(layer) is not LayerKind.POINT_CLOUD:
            report.skipped[name] = "not a point cloud layer"
            continue
        before = take_snapshot(layer, LayerKind.POINT_CLOUD)
        if operator == "AND NOT" and not before.subset:
            # combine_subset would keep only the excluded points of an unfiltered cloud.
            report.failed[name] = "AND NOT needs an existing filter on the layer"
            continue
        subset = combine_subset(before.subset, expression, operator)
        if not layer.setSubsetString(subset):
            layer.setSubsetString(before.subset)
            report.failed[name] = f"expression rejected: {subset}"
            continue
        after = take_snapshot(layer, LayerKind.POINT_CLOUD)
        if not after.same_state(before):
            changes.append((before, after))
        report.done[layer.id()] = name
        layer.triggerRepaint()
    if changes:
        _service(service).history.push(CrossOperation(changes[0][0].layer_id, tuple(changes), 'point cloud filter'))
    if not report.done and not report.failed and not report.error:
        report.error = "no point cloud layer to filter"
    report.details["expression"] = expression
    return report


# --- unfilter --------------------------------------------------------------------

@_exclusive()
def clear_filters(layers: Sequence, project=None, service=None) -> OperationReport:
    """Put layers of any kind back on their original source with no subset.

    Recorded in the automation history, not the dock's (the dock's own
    Unfilter records nothing either).
    """
    project = _project(project)
    report = OperationReport()
    ids, kinds, names = [], {}, {}
    for reference in layers or []:
        layer = resolve_layer(reference, project)
        label = reference if isinstance(reference, str) else _name(reference)
        if layer is None:
            report.skipped[label] = NOT_IN_PROJECT
            continue
        kind = layer_kind(layer)
        if kind is LayerKind.OTHER:
            report.skipped[_report_label(report, layer.name(), layer.id())] = NOT_FILTERABLE
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
        report.done[layer_id] = _report_label(report, names.get(layer_id, layer_id), layer_id)
    for layer_id in ids:
        if layer_id not in restored:
            report.skipped[_report_label(report, names[layer_id], layer_id)] = "not filtered"
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


@_exclusive(tidy=False)
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
    from qgis.core import QgsFeedback, QgsRasterBlockFeedback
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
    from ...core.export.target_guard import ProjectSources
    sources = ProjectSources(project)  # the files the project layers read from, once for the whole export
    total = max(1, len(resolved))
    for index, layer in enumerate(resolved):
        if feedback is not None and feedback.isCanceled():
            report.error = "canceled"
            break
        kind = layer_kind(layer)
        name = layer.name()
        label = _report_label(report, name, layer.id())
        try:
            if kind is LayerKind.VECTOR:
                driver, extension = VECTOR_EXPORT_FORMATS[vector_format]
                path = _output_file(_unique_path(output_path(folder, name, extension), used), sources)
                block, release = _child_feedback(feedback, index, total, QgsFeedback)
                try:
                    ok, path, message = _export_vector(layer, path, driver, crs, project, feedback=block)
                finally:
                    release()
            elif kind is LayerKind.RASTER:
                path = _output_file(_unique_path(output_path(folder, name, '.tif'), used), sources)
                block, release = _child_feedback(feedback, index, total, QgsRasterBlockFeedback)
                try:
                    result = export_raster(layer, path, raster_format, crs, feedback=block)
                finally:
                    release()
                ok, path, message = result.success, result.path, result.message
            elif kind is LayerKind.POINT_CLOUD:
                path = _output_file(_unique_path(output_path(folder, name, POINT_CLOUD_FORMATS[point_cloud_format]),
                                                 used), sources)
                result = export_point_cloud(layer, path, point_cloud_format, crs)
                ok, path, message = result.success, result.path, result.message
            else:
                report.skipped[label] = ("vector tiles are filtered for display only, not exported"
                                         if kind is LayerKind.VECTOR_TILE else NOT_FILTERABLE)
                continue
        except ValueError as exc:  # output file refused
            ok, path, message = False, '', str(exc)
        except Exception as exc:  # one layer must not stop the others
            logger.warning(f"[FM5] export of '{name}' failed: {exc}", exc_info=True)
            ok, path, message = False, '', _unexpected(report, exc, label)
        if ok:
            report.done[layer.id()] = label
            report.outputs[label] = path
            if message:
                report.details.setdefault("notes", {})[label] = message
        else:
            report.failed[label] = message or "export failed"
        if feedback is not None:
            feedback.setProgress(100.0 * (index + 1) / total)
    return report


def _output_file(path: str, sources=None) -> str:
    """``path``, unless writing it would be unsafe (ValueError).

    Refused: a symbolic link (the writer would follow it anywhere) and, when
    ``sources`` (the project's :class:`ProjectSources`, worked out once per export) is
    given, the file another layer of the project is read from (the writer overwrites its
    target: every layer stored in it would be lost).
    """
    if os.path.islink(path):
        raise ValueError(f"not written: {path} is a symbolic link")
    if sources is not None:
        name = sources.layer_using(path)
        if name is not None:
            raise ValueError(f"not written: {path} is the data source of the layer '{name}'")
    return path


def _report_label(report: OperationReport, name: str, layer_id: str) -> str:
    """``name``, or ``name (layer id)`` when a layer of that name is already in the report."""
    used = set(report.done.values()) | set(report.failed) | set(report.skipped)
    return name if name not in used else f"{name} ({layer_id})"


def _child_feedback(feedback, index: int, total: int, child_class):
    """``(child feedback, release)`` relaying progress and cancellation to ``feedback``.

    A writer reports 0-100 % for one layer: the child forwards it as this
    layer's share of the export, and a cancel request stops the write.
    ``QgsRasterFileWriter`` refuses any feedback but a ``QgsRasterBlockFeedback``
    (a Processing feedback raises TypeError): ``child_class`` picks the child.
    """
    if feedback is None:
        return None, lambda: None
    block = child_class()

    def _progress(value):
        feedback.setProgress(100.0 * (index + value / 100.0) / max(1, total))

    block.progressChanged.connect(_progress)
    if feedback.isCanceled():
        block.cancel()
    feedback.canceled.connect(block.cancel)
    return block, lambda: _disconnect((feedback.canceled, block.cancel), (block.progressChanged, _progress))


def _export_vector(layer, path: str, driver: str, crs, project, feedback=None) -> Tuple[bool, str, str]:
    """``QgsVectorFileWriter`` honours the subset string: only the filtered features are written."""
    from qgis.core import QgsCoordinateTransform, QgsVectorFileWriter
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = driver
    options.fileEncoding = "UTF-8"
    options.layerName = layer.name()
    if feedback is not None:
        options.feedback = feedback
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
        from ...core.domain.plugin_package import PLUGIN_PACKAGE
        loaded = plugins.get(PLUGIN_PACKAGE)
        candidates += [loaded, getattr(loaded, 'app', None)]
    except Exception as exc:
        logger.debug(f"[FM5] loaded plugin instance not found: {exc}")
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


@_exclusive()
def apply_favorite(name_or_id: str, service=None, project=None, feedback=None) -> OperationReport:
    """Apply a favorite: its subset strings, then its raster / point cloud clips.

    Same behaviour as the dock's favorites menu (subsets pushed directly,
    layers resolved by signature, then id, then name). Works headless from
    the favorites saved in the project file when the plugin is not loaded.
    ``feedback``: canceled before the clips, progress after the subsets.
    """
    from ...core.domain.layer_signature import LayerSignature
    from ...infrastructure.database.sql_utils import safe_set_subset_string
    from ..qgis.coverage_layers import favorites_bridge
    project = _project(project)
    report = OperationReport()
    service = service or find_favorites_service()
    favorite = find_favorite(name_or_id, service, project)
    if favorite is None:
        report.error = f"favorite not found: {name_or_id}"
        return report
    by_signature = {}
    for layer in project.mapLayers().values():
        try:
            by_signature[LayerSignature.compute(layer)] = layer
        except Exception as exc:
            logger.debug(f"[FM5] layer signature not computed: {exc}")
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
        name = _report_label(report, layer.name(), layer.id())
        try:
            if safe_set_subset_string(layer, expression):
                report.done[layer.id()] = name
            else:
                report.failed[name] = "subset rejected by the provider"
        except Exception as exc:
            logger.warning(f"[FM5] favorite subset on '{name}' failed: {exc}", exc_info=True)
            report.failed[name] = _unexpected(report, exc, name)
    if coverage and _canceled(feedback):
        report.error = "canceled"
        coverage = []
    elif feedback is not None and coverage:
        feedback.setProgress(50.0)
    if coverage:
        _install_registry(project)
        applied: List[str] = []
        clip_failures: Dict[str, str] = {}

        def clip(clip_service, request, source_job) -> str:
            # A worker like cross_filter's: a remote raster (WCS) refuses the main thread.
            return _task_failure(_run_task(clip_service, request, source_job, feedback), request.targets[0].layer_id)

        try:
            handled = favorites_bridge.apply(coverage, project=project, kind_of=layer_kind, applied=applied,
                                             run=clip, failed=clip_failures, canceled=lambda: _canceled(feedback))
        except Exception as exc:  # a stored source that no longer opens
            logger.warning(f"[FM5] favorite clips not applied: {exc}", exc_info=True)
            label = favorite.name or name_or_id
            report.failed[label] = f"raster / point cloud clips not applied: {_unexpected(report, exc, label)}"
            handled = 0
        for layer_id in applied:
            layer = project.mapLayer(layer_id)
            if layer is not None and layer_id not in report.done:
                report.done[layer_id] = _report_label(report, layer.name(), layer_id)
        for layer_id, reason in clip_failures.items():
            layer = project.mapLayer(layer_id)
            report.failed[_report_label(report, _name(layer, layer_id) if layer is not None else layer_id,
                                        layer_id)] = reason
        if handled + len(clip_failures) < len(coverage):
            report.details["coverage_layers_missing"] = len(coverage) - handled - len(clip_failures)
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
        except Exception as exc:
            logger.debug(f"[FM5] layer snapshot not taken: {exc}")
            continue
        if not snapshot.subset and not snapshot.derived:
            continue
        if kind is LayerKind.VECTOR_TILE:
            # A display filter laid in the style rules: no derived source.
            rows.append({"id": layer.id(), "name": layer.name(), "kind": kind.value,
                         "subset": snapshot.tile_filter, "derived": False, "source": ""})
            continue
        rows.append({"id": layer.id(), "name": layer.name(), "kind": kind.value, "subset": snapshot.subset,
                     "derived": bool(snapshot.derived), "source": layer.source() if snapshot.derived else ""})
    return rows

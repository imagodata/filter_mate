# -*- coding: utf-8 -*-
"""
CrossFilterService - FILTERING between layers of any kind.

The source is the current layer and its EXPLORING selection; the targets are
the checked "layers to filter". The vector -> vector case stays on the
historical engine (``FilterEngineTask``); this service handles every other
pair, plus the raster and point cloud targets of a vector source.

It owns the history of cross operations (per source layer), so the dock's
Undo / Redo / Unfilter buttons can restore derived sources as well as
subset strings.
"""
import logging
import time
import weakref
from typing import Callable, Iterable, List, Optional

from ..domain.cross_filter import CrossFilterOutcome, CrossFilterRequest
from ..domain.filter_state import CrossOperation, CrossOperationHistory
from ..domain.layer_kind import LayerKind

logger = logging.getLogger(__name__)

# Every live service (the dock's and the automation one): their histories
# keep derived files alive (see tidy_cache).
_SERVICES: "weakref.WeakSet" = weakref.WeakSet()


def _config_option(key: str, default):
    try:
        from ...config.config import ENV_VARS, _get_option_value
        section = ENV_VARS.get('CONFIG_DATA', {}).get('APP', {}).get('OPTIONS', {}).get('CROSS_FILTER', {})
        return _get_option_value(section.get(key), default)
    except Exception:
        return default


class _UnpreparedTarget:
    """A target whose job could not be built: the task reports it failed, like the others."""

    def __init__(self, layer, kind: LayerKind, reason: str) -> None:
        self.layer_id = layer.id()
        self.layer_name = layer.name()
        self.kind = kind
        self.outcome = CrossFilterOutcome(self.layer_id, kind, False, reason)

    def compute(self, *args) -> None:
        """Nothing to compute: the outcome already holds the reason."""


class CrossFilterService:
    """Run cross filters and keep their undo / redo history."""

    def __init__(self, history: Optional[CrossOperationHistory] = None) -> None:
        self.history = history or CrossOperationHistory()
        self.last_skipped: List[str] = []
        self._running = []
        self.replaying: set = set()
        _SERVICES.add(self)

    # --- run ----------------------------------------------------------------

    def build_task(self, request: CrossFilterRequest, source_job, project=None, on_done: Optional[Callable] = None):
        """Create the jobs for every target and the QgsTask (main thread)."""
        from qgis.core import QgsProject
        from ...adapters.qgis.coverage_layers.cross_filter_task import CrossFilterTask
        from ...adapters.qgis.coverage_layers.target_appliers import make_job
        from ...adapters.qgis.coverage_layers.snapshots import registry

        project = project or QgsProject.instance()
        registry().install(project)
        clip_mode = str(_config_option('point_cloud_clip', 'exact') or 'exact')
        jobs = []
        for target in request.targets:
            if target.layer_id == request.source_layer_id and request.source_kind is not LayerKind.OTHER:
                continue  # a real source is filtered by its own job; a stored geometry targets its layer
            layer = project.mapLayer(target.layer_id)
            if layer is None:
                continue
            try:
                job = make_job(layer, target.kind, request.other_layers_combine_operator, clip_mode)
            except Exception as exc:
                logger.warning(f"[FM5] target '{layer.name()}' skipped: {exc}", exc_info=True)
                job = _UnpreparedTarget(layer, target.kind, str(exc))
            if job is not None:
                jobs.append(job)

        def _done(task, result):
            self._record(task, request)
            self._running = [t for t in self._running if t is not task and not _finished(t)]
            if on_done is not None:
                on_done(task, result)

        return CrossFilterTask(f"FilterMate: {source_job.layer_name}", request, source_job, jobs, _done)

    def run(self, request: CrossFilterRequest, source_job, on_done: Optional[Callable] = None,
            synchronous: bool = False):
        """Start a cross filter. ``synchronous`` runs it inline (scripts, tests)."""
        task = self.build_task(request, source_job, on_done=on_done)
        if synchronous:
            result = task.run()
            task.apply_results(result)
            return task
        from qgis.core import QgsApplication
        self._running = [t for t in self._running if not _finished(t)] + [task]
        QgsApplication.taskManager().addTask(task)
        return task

    def cancel_all(self) -> None:
        """Cancel the cross filter tasks still running (plugin unload).

        A task whose ``run`` is over may still wait for ``finished`` on the
        main thread: its callback is dropped too (and the closed cache stops
        it from applying anything).
        """
        for task in self._running:
            try:
                task.on_done = None
                if not _finished(task):
                    task.cancel()
            except RuntimeError:
                pass
        self._running = []

    def _record(self, task, request: CrossFilterRequest) -> None:
        if task.changes:
            self.history.push(CrossOperation(request.source_layer_id, tuple(task.changes),
                                             description=f"cross filter from {task.source_job.layer_name}"))

    # --- undo / redo / unfilter --------------------------------------------

    def _restore(self, pairs: Iterable, use_before: bool, project=None) -> List[str]:
        """Restore one side of an operation, only on layers still in the other side's state.

        A layer changed since the operation (another source filtered it again,
        the user edited its subset) is left alone and listed in
        :attr:`last_skipped`: undoing must never overwrite newer work.
        """
        from qgis.core import QgsProject
        from ...adapters.qgis.coverage_layers.snapshots import restore_snapshot, take_snapshot
        project = project or QgsProject.instance()
        restored = []
        self.last_skipped = []
        for before, after in pairs:
            snapshot, expected = (before, after) if use_before else (after, before)
            layer = project.mapLayer(snapshot.layer_id)
            if layer is None:
                continue
            try:
                current = take_snapshot(layer, LayerKind(snapshot.kind))
                if not current.same_state(expected) and not current.same_state(snapshot):
                    self.last_skipped.append(layer.name())
                    logger.info(f"[FM5] '{layer.name()}' changed since this operation: left as is")
                    continue
                if restore_snapshot(layer, snapshot):
                    restored.append(snapshot.layer_id)
            except Exception as exc:
                logger.warning(f"[FM5] '{layer.name()}' not restored: {exc}", exc_info=True)
        return restored

    def can_undo(self, source_layer_id: str) -> bool:
        return self.history.can_undo(source_layer_id)

    def can_redo(self, source_layer_id: str) -> bool:
        return self.history.can_redo(source_layer_id)

    def undo(self, source_layer_id: str, project=None) -> List[str]:
        """Restore the layers of the last operation of ``source_layer_id``."""
        operation = self.history.undo(source_layer_id)
        if operation is None:
            return []
        return self._restore(reversed(operation.changes), use_before=True, project=project)

    def redo(self, source_layer_id: str, project=None) -> List[str]:
        operation = self.history.redo(source_layer_id)
        if operation is None:
            return []
        return self._restore(operation.changes, use_before=False, project=project)

    def unfilter(self, source_layer_id: str, layer_ids: Iterable[str], kinds: dict, project=None,
                 record: bool = True) -> List[str]:
        """Put layers back on their original source with no subset (undoable).

        Args:
            source_layer_id: History key.
            layer_ids: Layers to clear (source and targets).
            kinds: ``{layer_id: LayerKind}``.
        """
        from qgis.core import QgsProject
        from ...adapters.qgis.coverage_layers.snapshots import base_snapshot, restore_snapshot, take_snapshot
        project = project or QgsProject.instance()
        changes = []
        for layer_id in layer_ids:
            layer = project.mapLayer(layer_id)
            kind = kinds.get(layer_id, LayerKind.OTHER)
            if layer is None or kind is LayerKind.OTHER:
                continue
            before = take_snapshot(layer, kind)
            original = base_snapshot(before)
            if original.same_state(before):
                continue
            try:
                restore_snapshot(layer, original)
                changes.append((before, take_snapshot(layer, kind)))
            except Exception as exc:
                logger.warning(f"[FM5] '{layer.name()}' not cleared: {exc}", exc_info=True)
        if changes and record:
            self.history.push(CrossOperation(source_layer_id, tuple(changes), description='unfilter'))
        return [before.layer_id for before, _ in changes]


def replay_project_filters(service: Optional['CrossFilterService'] = None, synchronous: bool = False) -> int:
    """Rebuild the raster / point cloud clips stored in the opened project.

    Each layer is clipped again by its stored geometry (same side), from its
    original source, in a background task. Returns the number of layers queued.
    """
    from ...adapters.qgis.coverage_layers.snapshots import pending_replays, registry
    from ...adapters.qgis.coverage_layers.source_jobs import FixedGeometrySourceJob
    from ..domain.cross_filter import CrossFilterRequest, TargetSpec
    service = service or get_cross_filter_service()
    registry().install()
    queued = 0
    for layer, snapshot in pending_replays():
        if layer.id() in service.replaying:
            continue  # already queued (setup and readProject can both trigger)
        try:
            kind = LayerKind(snapshot.kind)
        except ValueError:
            continue
        if not kind.is_coverage:
            continue
        if snapshot.selection and not snapshot.geometry_wkt:
            # A raster source filtered by its own selection: rebuilt at once (no task needed).
            from ...adapters.qgis.coverage_layers.source_jobs import apply_stored_selection
            if apply_stored_selection(layer, snapshot) is not None:
                queued += 1
                logger.info(f"[FM5] replayed the stored raster selection of '{layer.name()}'")
            continue
        # The stored geometry is the area kept (outside already subtracted):
        # clip the original source again, keeping its inside.
        request = CrossFilterRequest(source_layer_id=layer.id(), source_kind=LayerKind.OTHER,
                                     targets=(TargetSpec(layer.id(), kind),), predicates=('Intersect',))
        geometry = snapshot.geometry_wkt
        job = FixedGeometrySourceJob(layer, geometry)
        service.replaying.add(layer.id())

        def _done(task, result, layer_id=layer.id()):
            service.replaying.discard(layer_id)

        service.run(request, job, on_done=_done, synchronous=synchronous)
        queued += 1
        logger.info(f"[FM5] replaying the stored {kind.value} filter of '{layer.name()}'")
    return queued


def all_services() -> List[CrossFilterService]:
    """Every live :class:`CrossFilterService`."""
    return list(_SERVICES)


def clear_histories() -> None:
    """Forget every cross filter history (the project they refer to was closed)."""
    for service in all_services():
        service.history.clear()


def forget_layer_everywhere(layer_id: str) -> None:
    """Drop the operations touching a removed layer from every history."""
    for service in all_services():
        service.history.forget_layer(layer_id)


def _snapshot_sources(snapshot) -> tuple:
    return tuple(s for s in (snapshot.source, snapshot.original_source, snapshot.enriched_source) if s)


def _operation_sources(operation) -> list:
    return [s for before, after in operation.changes for s in _snapshot_sources(before) + _snapshot_sources(after)]


def current_sources(project=None) -> set:
    """Sources the layers use now: derived registry and project layers."""
    from qgis.core import QgsProject
    from ...adapters.qgis.coverage_layers.snapshots import registry
    project = project or QgsProject.instance()
    sources = set()
    reg = registry()
    for layer_id in reg.layer_ids():
        snapshot = reg.get(layer_id)
        if snapshot is not None:
            sources.update(_snapshot_sources(snapshot))
    for layer in project.mapLayers().values():
        try:
            sources.add(layer.source())
        except RuntimeError:
            pass
    return sources


def history_sources() -> set:
    """Sources kept by every undo / redo step of every service."""
    return {s for service in all_services() for op in service.history.operations() for s in _operation_sources(op)}


def referenced_sources(project=None) -> set:
    """Sources still in use: project layers, derived registry and every undo / redo snapshot."""
    return current_sources(project) | history_sources()


def filtermate_tasks_active() -> bool:
    """True while a FilterMate task runs (the cache is tidied once they are over)."""
    try:
        from qgis.core import QgsApplication
        tasks = QgsApplication.taskManager().activeTasks()
    except Exception:
        return False
    return any(str(task.description()).startswith('FilterMate') for task in tasks)


def stop_filtermate_tasks(wait_seconds: float = 2.0) -> int:
    """Cancel the FilterMate tasks still running, then give them a moment to end (plugin unload).

    Exports, height-above-ground runs and cross filters read and write the
    cache, removed next: a killed pdal process or a GDAL dataset must close
    its files first (Windows cannot delete a file still open). A task still
    running after ``wait_seconds`` is left to the closed cache, which stops
    its callback from applying anything.

    Returns:
        Number of tasks canceled.
    """
    try:
        from qgis.core import QgsApplication
        tasks = [task for task in QgsApplication.taskManager().activeTasks()
                 if str(task.description()).startswith('FilterMate: ')]
    except Exception:
        return 0
    for task in tasks:
        try:
            task.cancel()
        except RuntimeError:
            pass
    deadline = time.monotonic() + wait_seconds
    for task in tasks:
        left = int((deadline - time.monotonic()) * 1000)
        if left <= 0:
            break  # never waitForFinished(0): that waits for ever
        try:
            task.waitForFinished(left)
        except RuntimeError:
            pass
    return len(tasks)


def tidy_cache(project=None) -> Optional[dict]:
    """Remove the derived files nothing refers to, then keep the cache under its limit.

    While the cache is over ``CROSS_FILTER.cache_max_gb``, the oldest undo /
    redo step of a history that keeps a derived file alive (a file no layer
    shows) is forgotten, until the limit is met or no step holds such a file.
    Current filters and files of running tasks are never touched.

    Returns:
        None when a FilterMate task runs (try again later), else
        ``{'size': bytes, 'limit': bytes, 'removed': entries, 'dropped': [(service, DroppedStep)]}``.
    """
    from ...adapters.qgis.coverage_layers import cache
    if filtermate_tasks_active():
        return None
    current = current_sources(project)
    removed = cache.collect_garbage(current | history_sources())
    limit = cache.max_bytes()
    sizes = cache.entry_sizes()
    size = sum(sizes.values())
    dropped = []
    while limit and size > limit:
        held = {cache.file_key(name) for name in cache.unused_entries(current, names=sizes)}
        if not held:
            break  # the current filters alone are over the limit

        def holds(operation, held=held) -> bool:
            return any(key in source for source in _operation_sources(operation) for key in held)

        candidates = [(op.op_id, service) for service in all_services()
                      for op in (service.history.oldest(holds),) if op is not None]
        if not candidates:
            break
        service = min(candidates, key=lambda c: c[0])[1]
        dropped.append((service, service.history.drop_oldest(holds)))
        for name in cache.unused_entries(current | history_sources(), names=sizes):
            size -= sizes.pop(name)
    if dropped:
        removed += cache.collect_garbage(current | history_sources())
        size = sum(cache.entry_sizes().values())
        logger.info(f"[FM5] cache over its limit: {len(dropped)} oldest undo step(s) forgotten")
    return {'size': size, 'limit': limit, 'removed': removed, 'dropped': dropped}


def _finished(task) -> bool:
    try:
        from qgis.core import QgsTask
        return task.status() in (QgsTask.TaskStatus.Complete, QgsTask.TaskStatus.Terminated)
    except Exception:
        return True


_service: Optional[CrossFilterService] = None


def get_cross_filter_service() -> CrossFilterService:
    """Process-wide service instance."""
    global _service
    if _service is None:
        _service = CrossFilterService()
    return _service


def reset_cross_filter_service() -> None:
    global _service
    _service = None

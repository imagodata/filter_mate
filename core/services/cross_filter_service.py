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
from typing import Callable, Iterable, List, Optional

from ..domain.cross_filter import CrossFilterRequest, TargetSpec
from ..domain.filter_state import CrossOperation, CrossOperationHistory, LayerSnapshot
from ..domain.layer_kind import LayerKind

logger = logging.getLogger(__name__)


def _config_option(key: str, default):
    try:
        from ...config.config import ENV_VARS, _get_option_value
        section = ENV_VARS.get('CONFIG_DATA', {}).get('APP', {}).get('OPTIONS', {}).get('CROSS_FILTER', {})
        return _get_option_value(section.get(key), default)
    except Exception:
        return default


class CrossFilterService:
    """Run cross filters and keep their undo / redo history."""

    def __init__(self, history: Optional[CrossOperationHistory] = None) -> None:
        self.history = history or CrossOperationHistory()
        self._running = None

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
            if target.layer_id == request.source_layer_id:
                continue
            layer = project.mapLayer(target.layer_id)
            if layer is None:
                continue
            try:
                job = make_job(layer, target.kind, request.other_layers_combine_operator, clip_mode)
            except Exception as exc:
                logger.warning(f"[FM5] target '{layer.name()}' skipped: {exc}", exc_info=True)
                job = None
            if job is not None:
                jobs.append(job)

        def _done(task, result):
            self._record(task, request)
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
        self._running = task
        QgsApplication.taskManager().addTask(task)
        return task

    def _record(self, task, request: CrossFilterRequest) -> None:
        if task.changes:
            self.history.push(CrossOperation(request.source_layer_id, tuple(task.changes),
                                             description=f"cross filter from {task.source_job.layer_name}"))

    # --- undo / redo / unfilter --------------------------------------------

    def _restore(self, pairs: Iterable, use_before: bool, project=None) -> List[str]:
        from qgis.core import QgsProject
        from ...adapters.qgis.coverage_layers.snapshots import restore_snapshot
        project = project or QgsProject.instance()
        restored = []
        for before, after in pairs:
            snapshot = before if use_before else after
            layer = project.mapLayer(snapshot.layer_id)
            if layer is None:
                continue
            try:
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

    def unfilter(self, source_layer_id: str, layer_ids: Iterable[str], kinds: dict, project=None) -> List[str]:
        """Put layers back on their original source with no subset (undoable).

        Args:
            source_layer_id: History key.
            layer_ids: Layers to clear (source and targets).
            kinds: ``{layer_id: LayerKind}``.
        """
        from qgis.core import QgsProject
        from ...adapters.qgis.coverage_layers.snapshots import restore_snapshot, take_snapshot
        project = project or QgsProject.instance()
        changes = []
        for layer_id in layer_ids:
            layer = project.mapLayer(layer_id)
            kind = kinds.get(layer_id, LayerKind.OTHER)
            if layer is None or kind is LayerKind.OTHER:
                continue
            before = take_snapshot(layer, kind)
            original = LayerSnapshot(layer_id, kind.value, source=before.base_source, provider=before.base_provider, subset='')
            if original.same_state(before):
                continue
            try:
                restore_snapshot(layer, original)
                changes.append((before, take_snapshot(layer, kind)))
            except Exception as exc:
                logger.warning(f"[FM5] '{layer.name()}' not cleared: {exc}", exc_info=True)
        if changes:
            self.history.push(CrossOperation(source_layer_id, tuple(changes), description='unfilter'))
        return [before.layer_id for before, _ in changes]


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

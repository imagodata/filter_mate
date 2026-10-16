# -*- coding: utf-8 -*-
"""
QgsTask running a cross filter: source geometry, then every target.

``run`` (task thread) computes the source geometry and each target's result;
``finished`` (main thread) applies them and reports the before / after
snapshots to the ``on_done`` callback, which records the history.
"""
import logging
import time
from typing import Callable, List, Optional, Tuple

from qgis.core import QgsFeedback, QgsProject, QgsTask

from ....core.domain.filter_state import LayerSnapshot

logger = logging.getLogger(__name__)


class CrossFilterTask(QgsTask):
    """Apply one source selection to target layers of any kind."""

    def __init__(self, description: str, request, source_job, target_jobs: list,
                 on_done: Optional[Callable] = None) -> None:
        super().__init__(description, QgsTask.Flag.CanCancel)
        self.request = request
        self.source_job = source_job
        self.target_jobs = list(target_jobs)
        self.on_done = on_done
        self.transform_context = QgsProject.instance().transformContext()
        self.error: str = ''
        self.changes: List[Tuple[LayerSnapshot, LayerSnapshot]] = []
        self.outcomes = []
        self.elapsed = 0.0
        # Canceled with the task, for the QGIS calls that only take a feedback.
        self.feedback = QgsFeedback()

    def cancel(self) -> None:
        self.feedback.cancel()
        super().cancel()

    def run(self) -> bool:
        started = time.perf_counter()
        try:
            geometry = self.source_job.compute(self.request, self.isCanceled)
            logger.info(f"⏱ [FM5] source geometry ({self.source_job.kind.value}) in {self.source_job.elapsed:.2f}s "
                        f"{self.source_job.details}")
            if self.source_job.message:
                # The selection could not be read: never empty the targets for that.
                self.error = self.source_job.message
                return False
            if geometry.isEmpty() and self.target_jobs:
                self.error = 'the selection is empty: nothing to relate to the target layers'
                return False
            # The selected features of a vector source, apart, for the vector targets only.
            parts = None
            if callable(getattr(self.source_job, 'parts', None)) and any(hasattr(j, 'source_parts') for j in self.target_jobs):
                parts = self.source_job.parts(self.request)
            total = max(1, len(self.target_jobs))
            for index, job in enumerate(self.target_jobs):
                if self.isCanceled():
                    return False
                job.feedback = self.feedback
                if parts is not None and hasattr(job, 'source_parts'):
                    job.source_parts = parts
                try:
                    job.compute(geometry, self.source_job.crs, self.transform_context, self.request, self.isCanceled)
                except Exception as exc:  # one target must not stop the others
                    logger.warning(f"[FM5] target '{job.layer_name}' failed: {exc}", exc_info=True)
                    job.outcome.message = str(exc)
                self.setProgress(100.0 * (index + 1) / total)
            return not self.isCanceled()
        except Exception as exc:
            logger.error(f"[FM5] cross filter failed: {exc}", exc_info=True)
            self.error = str(exc)
            return False
        finally:
            self.elapsed = time.perf_counter() - started

    def finished(self, result: bool) -> None:
        self.apply_results(result)

    def apply_results(self, result: bool) -> None:
        """Apply the computed results on the main thread (also used by synchronous runs)."""
        from . import cache
        project = QgsProject.instance()
        if result and cache.is_closed():
            # The plugin unloaded while the task ran: its files are gone.
            result = False
            self.error = 'FilterMate was unloaded'
        if result:
            source_layer = project.mapLayer(self.source_job.layer_id)
            if source_layer is not None:
                try:
                    after = self.source_job.apply(source_layer)
                    if after is not None:
                        self.changes.append((self.source_job.before, after))
                except Exception as exc:
                    logger.warning(f"[FM5] source layer not filtered: {exc}", exc_info=True)
            for job in self.target_jobs:
                layer = project.mapLayer(job.layer_id)
                if layer is None:
                    job.outcome.success = False
                    job.outcome.message = 'layer removed'
                elif job.outcome.success:
                    try:
                        after = job.apply(layer)
                        if after is not None and not after.same_state(job.before):
                            self.changes.append((job.before, after))
                    except Exception as exc:
                        logger.warning(f"[FM5] target '{job.layer_name}' not applied: {exc}", exc_info=True)
                        job.outcome.success = False
                        job.outcome.message = str(exc)
                logger.info(f"⏱ [FM5] target {job.kind.value} '{job.layer_name}': success={job.outcome.success} "
                            f"kept={job.outcome.kept_count} {job.outcome.elapsed:.2f}s {job.outcome.message}")
        self.outcomes = [job.outcome for job in self.target_jobs]
        cache.settle(path for job in self.target_jobs for path in getattr(job, 'outputs', ()))
        for job in [self.source_job] + list(self.target_jobs):
            release = getattr(job, 'release', None)
            if release is not None:
                release()
        if self.on_done is not None:
            try:
                self.on_done(self, result)
            except Exception as exc:
                logger.error(f"[FM5] cross filter callback failed: {exc}", exc_info=True)

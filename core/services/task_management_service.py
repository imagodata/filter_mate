# -*- coding: utf-8 -*-
"""
Task Management Service for FilterMate v4.0

Manages asynchronous task lifecycle:
- Safe task cancellation
- Queue processing for add_layers operations
- Layer-specific task cancellation
- Task termination handling

This service extracts task management logic from the FilterMateApp god class.

Author: FilterMate Team
Date: January 2026
"""
from typing import List, Optional, Any, Callable
from dataclasses import dataclass
import logging

try:
    from qgis.core import QgsApplication, QgsTask
    try:
        import sip
    except ImportError:
        from PyQt6 import sip
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False
    sip = None
    QgsTask = Any

logger = logging.getLogger('FilterMate.TaskManagementService')

# Root package of the plugin ('filter_mate' once installed): every FilterMate task
# class is defined under it, whatever the (translated) description of the task.
_PLUGIN_PACKAGE = __name__.split('.')[0]

# Left running by safe_cancel_all_tasks: a FilterEngineTask lifts its protections (panel
# in "filtering" state, signals of the current-layer combo box blocked) on taskCompleted
# only, and its cancel() drops PostgreSQL views on the main thread. The former loop
# (task(i), which takes an id) practically never reached it either.
_TASKS_LEFT_RUNNING = ('FilterEngineTask',)


def is_filtermate_task(task: Any) -> bool:
    """True for a task started by FilterMate: a task class of the plugin, or a
    description starting with "FilterMate" (raster / point cloud tasks)."""
    module = type(task).__module__ or ''
    if module == _PLUGIN_PACKAGE or module.startswith(_PLUGIN_PACKAGE + '.'):
        return True
    try:
        return str(task.description()).startswith('FilterMate')
    except (RuntimeError, AttributeError):
        return False


@dataclass
class TaskManagementConfig:
    """Configuration for task management operations."""
    max_queue_size: int = 50
    retry_delay_ms: int = 500
    processing_flag_timeout_ms: int = 5000


class TaskManagementService:
    """
    Service for managing asynchronous tasks in FilterMate.

    Responsibilities:
    - Cancel all tasks safely
    - Cancel layer-specific tasks
    - Process add_layers queue
    - Handle task termination recovery

    This service maintains task state and provides safe operations
    for concurrent task management.
    """

    def __init__(self, config: Optional[TaskManagementConfig] = None):
        """
        Initialize the task management service.

        Args:
            config: Optional configuration for task operations
        """
        self.config = config or TaskManagementConfig()
        self._add_layers_queue: List[List[Any]] = []
        self._processing_queue = False
        self._pending_add_layers_tasks = 0

    def safe_cancel_all_tasks(self) -> None:
        """
        Safely cancel all FilterMate tasks in the task manager.

        Cancels tasks individually instead of using cancelAll() to avoid
        Windows access violations during project transitions. Tasks of QGIS
        (Processing in the background) and of other plugins are left alone:
        a project change or the plugin unload is no reason to stop them.
        """
        try:
            task_manager = QgsApplication.taskManager()
            if not task_manager:
                return

            # tasks(), not task(i) for i < count(): task() takes a task id, not an index
            for task in reversed(list(task_manager.tasks())):
                try:
                    if (task and is_filtermate_task(task) and type(task).__name__ not in _TASKS_LEFT_RUNNING
                            and task.canCancel()):
                        task.cancel()
                except RuntimeError as e:  # task deleted meanwhile: the others are still canceled
                    logger.debug(f"Task not canceled: {e}")

        except Exception as e:
            logger.warning(f"Could not cancel tasks: {e}")

    def cancel_layer_tasks(
        self,
        layer_id: str,
        dockwidget: Any
    ) -> None:
        """
        Cancel all running tasks for a specific layer.

        CRASH FIX: Must be called before modifying layer variables to prevent
        race conditions where background tasks iterate features while main
        thread modifies layer state.

        Args:
            layer_id: The ID of the layer whose tasks should be cancelled
            dockwidget: Dockwidget instance containing widgets with tasks
        """
        try:
            if not dockwidget:
                return

            exploring_widget = dockwidget.widgets.get("EXPLORING", {})
            for widget_key in ["SINGLE_SELECTION_FEATURES", "MULTIPLE_SELECTION_FEATURES"]:
                widget_data = exploring_widget.get(widget_key, {})
                widget = widget_data.get("WIDGET")
                if widget and hasattr(widget, 'tasks'):
                    for task_type in widget.tasks:
                        if layer_id in widget.tasks[task_type]:
                            task = widget.tasks[task_type][layer_id]
                            if isinstance(task, QgsTask) and not sip.isdeleted(task):
                                if task.status() in [QgsTask.TaskStatus.Running, QgsTask.TaskStatus.Queued]:
                                    logger.debug(f"Cancelling {task_type} task for layer {layer_id}")
                                    task.cancel()
        except Exception as e:
            logger.debug(f"cancel_layer_tasks: Error cancelling tasks: {e}")

    def enqueue_add_layers(self, layers: List[Any]) -> bool:
        """
        Add layers to the processing queue.

        Args:
            layers: List of layers to add

        Returns:
            True if enqueued successfully, False if queue full
        """
        if len(self._add_layers_queue) >= self.config.max_queue_size:
            logger.warning(f"Add layers queue is full ({self.config.max_queue_size}), dropping request")
            return False

        self._add_layers_queue.append(layers)
        logger.info(f"Enqueued add_layers operation (queue size: {len(self._add_layers_queue)})")
        return True

    def process_add_layers_queue(
        self,
        manage_task_callback: Callable[[str, List[Any]], None],
        queue: Optional[List[Any]] = None
    ) -> None:
        """
        Process queued add_layers operations.

        Processes the first queued operation from the queue.
        Called after a previous add_layers task completes.

        Args:
            manage_task_callback: Callback to trigger manage_task('add_layers', layers)
            queue: The queue to process (2026-10-17: FilterMateApp passes the
                one manage_task fills; this service's own queue otherwise)
        """
        pending = self._add_layers_queue if queue is None else queue

        # Prevent concurrent queue processing
        if self._processing_queue:
            logger.debug("Queue already being processed, skipping")
            return

        if not pending:
            logger.debug("Queue is empty, nothing to process")
            return

        self._processing_queue = True

        try:
            # Get first queued operation
            queued_layers = pending.pop(0)
            logger.info(f"Processing queued add_layers operation with {len(queued_layers) if queued_layers else 0} layers (queue size: {len(pending)})")

            # Process via callback (which will increment _pending_add_layers_tasks)
            manage_task_callback('add_layers', queued_layers)

        except Exception as e:
            logger.error(f"Error processing add_layers queue: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        finally:
            self._processing_queue = False

    def increment_pending_tasks(self) -> None:
        """Increment counter for pending add_layers tasks."""
        self._pending_add_layers_tasks += 1
        logger.debug(f"Pending add_layers tasks: {self._pending_add_layers_tasks}")

    def decrement_pending_tasks(self) -> int:
        """
        Decrement counter for pending add_layers tasks.

        Returns:
            Remaining pending tasks count
        """
        if self._pending_add_layers_tasks > 0:
            self._pending_add_layers_tasks -= 1
        logger.debug(f"Pending add_layers tasks: {self._pending_add_layers_tasks}")
        return self._pending_add_layers_tasks

    def get_pending_tasks_count(self) -> int:
        """Get number of pending add_layers tasks."""
        return self._pending_add_layers_tasks

    def get_queue_size(self) -> int:
        """Get current size of add_layers queue."""
        return len(self._add_layers_queue)

    def clear_queue(self) -> None:
        """Clear all queued add_layers operations."""
        size = len(self._add_layers_queue)
        self._add_layers_queue.clear()
        self._processing_queue = False
        if size > 0:
            logger.info(f"Cleared {size} queued add_layers operations")

    def reset_counters(self) -> None:
        """Reset all task counters."""
        self._pending_add_layers_tasks = 0
        logger.debug("Reset task counters")

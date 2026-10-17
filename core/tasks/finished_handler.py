"""
Task Completion (finished) Handler

Handles all post-task completion logic for FilterEngineTask, including:
- Warning message display
- Pending subset string application (main thread safety)
- PostgreSQL materialized view cleanup
- Memory layer cleanup
- Success/failure/exception message display via QGIS message bar
- OGR backend temporary layer cleanup
- TaskBridge metrics logging
- Safe intersect temporary layer cleanup
- Source layer selection restoration

Extracted from FilterEngineTask.finished() as part of the C1 God Object
decomposition (Phase 3, US-C1.3.3).

Location: core/tasks/finished_handler.py (Hexagonal Architecture - Application Layer)

Thread Safety:
    All methods in this handler run in the MAIN THREAD (called from
    QgsTask.finished()). They CAN safely access Qt widgets and iface.
"""

import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
)
from qgis.PyQt.QtCore import QCoreApplication

from ...infrastructure.logging import setup_logger
from ...config.config import ENV_VARS

# E6: Task completion handler functions (reused, not duplicated)
from .task_completion_handler import (
    display_warning_messages as tch_display_warnings,
    apply_pending_subset_requests,
    schedule_canvas_refresh,
    cleanup_memory_layer,
)

# Setup logger
logger = setup_logger(
    'FilterMate.Tasks.Finished',
    os.path.join(ENV_VARS.get("PATH_ABSOLUTE_PROJECT", "."), 'logs', 'filtermate_tasks.log'),
    level=logging.INFO
)


def _deleted(layer: Any) -> bool:
    """True once the layer's C++ object is gone."""
    if layer is None:
        return True
    try:
        layer.id()
        return False
    except RuntimeError:
        return True


class FinishedHandler:
    """Handles task completion logic for FilterEngineTask.

    This class encapsulates all post-task operations previously embedded
    in FilterEngineTask.finished() and its auxiliary methods. It receives
    dependencies explicitly via method parameters rather than accessing
    task state directly.

    All methods run in the MAIN THREAD and can safely access Qt widgets,
    iface, and QgsProject.

    Example:
        >>> handler = FinishedHandler()
        >>> handler.handle_finished(
        ...     result=True,
        ...     task_action='filter',
        ...     message_categories={'filter': 'FilterLayers'},
        ...     ...
        ... )
    """

    def __init__(self):
        """Initialize FinishedHandler."""

    def handle_finished(
        self,
        result: Optional[bool],
        task_action: str,
        message_category: str,
        is_canceled_fn: Callable[[], bool],
        warning_messages: List[str],
        pending_subset_requests: List[Tuple[Any, str]],
        safe_set_subset_fn: Callable[[Any, str], bool],
        is_complex_filter_fn: Callable,
        single_canvas_refresh_fn: Callable,
        cleanup_mv_fn: Callable[[], None],
        ogr_source_geom: Optional[Any],
        exception: Optional[Exception],
        task_message: Optional[str],
        source_layer: Optional[Any],
        task_parameters: Dict[str, Any],
        failed_layer_names: List[str],
        layers_count: Optional[int],
        task_description: str,
        restore_selection_fn: Callable[[], None],
        task_bridge: Optional[Any],
        cleanup_safe_intersect_fn: Callable[[], None],
        cleanup_canceled_mv_fn: Optional[Callable[[], None]] = None,
    ) -> Tuple[List[str], List, Optional[Any]]:
        """Handle task completion with cleanup and user notifications.

        Called by QGIS task manager when task completes. Performs:
        1. Display warning messages collected during task execution
        2. Apply pending subset string requests on main Qt thread
        3. Cleanup PostgreSQL materialized views (for reset/unfilter only)
        4. Cleanup memory layers
        5. Show success/error message in QGIS message bar
        6. Cleanup OGR temp layers and safe_intersect layers
        7. Log TaskBridge metrics

        Args:
            result: True if task succeeded, False if failed, None if canceled.
            task_action: The action type ('filter', 'unfilter', 'reset', 'export').
            message_category: The message bar category string.
            is_canceled_fn: Function returning True if task was canceled.
            warning_messages: List of warning messages from task execution.
            pending_subset_requests: List of (layer, expression) tuples.
            safe_set_subset_fn: Function to safely set subset string on a layer.
            is_complex_filter_fn: Function to check if a filter is complex.
            single_canvas_refresh_fn: Function for single canvas refresh.
            cleanup_mv_fn: Function to cleanup PostgreSQL materialized views.
            ogr_source_geom: OGR source geometry layer to cleanup.
            exception: Exception from task execution, if any.
            task_message: Task result/error message string.
            source_layer: The source layer (may be None).
            task_parameters: Task parameters dict.
            failed_layer_names: List of layer names that failed filtering.
            layers_count: Number of layers processed.
            task_description: Task description string.
            restore_selection_fn: Function to restore source layer selection.
            task_bridge: TaskBridge instance for metrics, if any.
            cleanup_safe_intersect_fn: Function to cleanup safe_intersect layers.
            cleanup_canceled_mv_fn: For a canceled task: drops the materialized views it
                created that nothing uses (instead of cleanup_mv_fn).

        Returns:
            Tuple of (cleared_warnings, cleared_pending_requests, cleared_ogr_source_geom)
            so the caller can update its own state.
        """
        from qgis.utils import iface

        # E6: Delegate warning display to task_completion_handler
        if warning_messages:
            tch_display_warnings(warning_messages)

        # 2026-10-17: a canceled task applies nothing, even when its run()
        # completed: canceled by a newer task (a second click on Filter),
        # whose subsets are the ones to keep, or by QGIS (a layer removed).
        # They were applied whenever the task had queued some.
        if is_canceled_fn():
            if pending_subset_requests:
                logger.info(f"Task was canceled - its {len(pending_subset_requests)} pending subset "
                            "request(s) are dropped")
            pending_subset_requests = []

        # 2026-10-17: a target removed from the project during the task is left out (the
        # task depends on its source layer only); the other targets get their subsets.
        removed_targets = self._removed_target_names(task_parameters)
        if pending_subset_requests:
            pending_subset_requests = [(layer, expression) for layer, expression in pending_subset_requests
                                       if not _deleted(layer)]
        if removed_targets and not is_canceled_fn():
            self._display_removed_targets(removed_targets, iface)

        # Apply pending subset strings on main thread
        apply_failures: List[str] = []
        if pending_subset_requests:
            applied_count = apply_pending_subset_requests(
                pending_subset_requests,
                safe_set_subset_fn,
                failures=apply_failures,
            )
            logger.info(f"Applied {applied_count} pending subset requests")

            # E6: Delegated canvas refresh to task_completion_handler
            schedule_canvas_refresh(
                is_complex_filter_fn,
                single_canvas_refresh_fn
            )

        # Only cleanup MVs on reset/unfilter actions, NOT on filter
        # When filtering, materialized views are referenced by the layer's subsetString.
        # Cleaning them up would invalidate the filter expression causing empty results.
        # 2026-10-17: nor on export, which creates no MV and leaves the
        # filters in place (it dropped the MVs the filtered layers used).
        # 2026-10-17: not after a canceled reset / unfilter either: its subsets were not
        # applied, the layers still read those views.
        if is_canceled_fn():
            if cleanup_canceled_mv_fn is not None:
                cleanup_canceled_mv_fn()
        elif task_action in ('reset', 'unfilter'):
            cleanup_mv_fn()

        # E6: Delegate memory layer cleanup to task_completion_handler
        if ogr_source_geom is not None:
            cleanup_memory_layer(ogr_source_geom)

        # Handle result messages
        self._handle_result_messages(
            result=result,
            exception=exception,
            task_action=task_action,
            message_category=message_category,
            is_canceled_fn=is_canceled_fn,
            task_message=task_message,
            source_layer=source_layer,
            failed_layer_names=failed_layer_names,
            layers_count=layers_count,
            restore_selection_fn=restore_selection_fn,
            iface=iface,
        )

        # 2026-10-17: a filter the provider refused is not a success
        if apply_failures:
            self._display_apply_failures(apply_failures, iface)

        self._release_task_caches(task_parameters)

        # MIG-023: Log TaskBridge metrics for migration validation
        self._log_task_bridge_metrics(task_bridge)

        # FIX 2026-01-17: Clean up orphaned safe_intersect layers from project
        cleanup_safe_intersect_fn()

        # Return cleared state values for the caller to apply
        return ([], [], None)

    def _handle_result_messages(
        self,
        result: Optional[bool],
        exception: Optional[Exception],
        task_action: str,
        message_category: str,
        is_canceled_fn: Callable[[], bool],
        task_message: Optional[str],
        source_layer: Optional[Any],
        failed_layer_names: List[str],
        layers_count: Optional[int],
        restore_selection_fn: Callable[[], None],
        iface: Any,
    ) -> None:
        """Handle success/failure/exception result messages.

        Displays appropriate messages in the QGIS message bar based on
        task result status.

        Args:
            result: True if task succeeded, False if failed, None if canceled.
            exception: Exception from task execution, if any.
            task_action: The action type.
            message_category: The message bar category string.
            is_canceled_fn: Function returning True if task was canceled.
            task_message: Task result/error message string.
            source_layer: The source layer.
            failed_layer_names: Layer names that failed filtering.
            layers_count: Number of layers processed.
            restore_selection_fn: Function to restore source layer selection.
            iface: QGIS iface instance.
        """
        if is_canceled_fn():
            # 2026-10-17: no message for a canceled task, whatever its run()
            # returned: a newer task reports, and an interrupted query
            # (PostgreSQL "canceling statement") is no error to show.
            logger.info(f"Task was canceled - no message displayed (result={result}, exception={exception})")
            return
        if exception is None:
            self._handle_no_exception_result(
                result=result,
                task_action=task_action,
                message_category=message_category,
                is_canceled_fn=is_canceled_fn,
                task_message=task_message,
                source_layer=source_layer,
                failed_layer_names=failed_layer_names,
                layers_count=layers_count,
                restore_selection_fn=restore_selection_fn,
                iface=iface,
            )
        else:
            self._handle_exception_result(
                result=result,
                exception=exception,
                message_category=message_category,
                iface=iface,
            )

    def _handle_no_exception_result(
        self,
        result: Optional[bool],
        task_action: str,
        message_category: str,
        is_canceled_fn: Callable[[], bool],
        task_message: Optional[str],
        source_layer: Optional[Any],
        failed_layer_names: List[str],
        layers_count: Optional[int],
        restore_selection_fn: Callable[[], None],
        iface: Any,
    ) -> None:
        """Handle task result when no exception occurred.

        Args:
            result: True if succeeded, False if failed, None if canceled.
            task_action: The action type.
            message_category: The message bar category string.
            is_canceled_fn: Function returning True if task was canceled.
            task_message: Task result/error message string.
            source_layer: The source layer.
            failed_layer_names: Layer names that failed filtering.
            layers_count: Number of layers processed.
            restore_selection_fn: Function to restore source layer selection.
            iface: QGIS iface instance.
        """
        task_was_canceled = is_canceled_fn()

        if result is None:
            # Task was likely canceled by user - log only, no message bar notification
            logger.info('Task completed with no result (likely canceled by user)')

        elif result is False:
            # Task failed without exception - only display error if NOT canceled
            if task_was_canceled:
                logger.info('Task was canceled - no error message displayed')
            else:
                self._display_failure_message(
                    task_action=task_action,
                    message_category=message_category,
                    task_message=task_message,
                    source_layer=source_layer,
                    failed_layer_names=failed_layer_names,
                    layers_count=layers_count,
                    iface=iface,
                )
        else:
            # Task succeeded
            self._display_success_message(
                task_action=task_action,
                message_category=message_category,
                task_message=task_message,
                restore_selection_fn=restore_selection_fn,
                iface=iface,
            )

    def _display_failure_message(
        self,
        task_action: str,
        message_category: str,
        task_message: Optional[str],
        source_layer: Optional[Any],
        failed_layer_names: List[str],
        layers_count: Optional[int],
        iface: Any,
    ) -> None:
        """Display failure message in QGIS message bar.

        Args:
            task_action: The action type.
            message_category: The message bar category string.
            task_message: Task result/error message string.
            source_layer: The source layer.
            failed_layer_names: Layer names that failed filtering.
            layers_count: Number of layers processed.
            iface: QGIS iface instance.
        """
        # Enhanced error message with failed layer names
        error_msg = task_message if task_message else QCoreApplication.translate(
            "FinishedHandler", "Task failed"
        )

        # Include failed layer names if available
        if failed_layer_names and error_msg == QCoreApplication.translate("FinishedHandler", "Task failed"):
            error_msg = QCoreApplication.translate(
                "FinishedHandler", "Filter failed for: {0}"
            ).format(', '.join(failed_layer_names[:3]))
            if len(failed_layer_names) > 3:
                error_msg += QCoreApplication.translate(
                    "FinishedHandler", " (+{0} more)"
                ).format(len(failed_layer_names) - 3)

        source_name = source_layer.name() if source_layer else 'None'
        logger.error(f"Task finished with failure: {error_msg}")
        logger.error(f"   Task action: {task_action}")
        logger.error(f"   Source layer: {source_name}")
        logger.error(f"   Layers count: {layers_count if layers_count is not None else 'N/A'}")

        # Log to QGIS message log for visibility
        QgsMessageLog.logMessage(
            f"Task failed: {error_msg}",
            "FilterMate", Qgis.MessageLevel.Critical
        )

        # Log additional diagnostic info to Python console
        if error_msg == 'Task failed':
            logger.error("   TIP: Check the Python console for detailed error messages")
            logger.error("   Common causes: no features selected, invalid layer, database connection issue")

        iface.messageBar().pushMessage(
            message_category,
            error_msg,
            Qgis.MessageLevel.Critical)

    def _display_success_message(
        self,
        task_action: str,
        message_category: str,
        task_message: Optional[str],
        restore_selection_fn: Callable[[], None],
        iface: Any,
    ) -> None:
        """Display success message in QGIS message bar.

        Args:
            task_action: The action type.
            message_category: The message bar category string.
            task_message: Task result/error message string.
            restore_selection_fn: Function to restore source layer selection.
            iface: QGIS iface instance.
        """
        result_action: Optional[str] = None

        if message_category == 'FilterLayers':
            if task_action == 'filter':
                result_action = QCoreApplication.translate(
                    "FinishedHandler", "Layer(s) filtered"
                )
            elif task_action == 'unfilter':
                result_action = QCoreApplication.translate(
                    "FinishedHandler", "Layer(s) filtered to precedent state"
                )
            elif task_action == 'reset':
                result_action = QCoreApplication.translate(
                    "FinishedHandler", "Layer(s) unfiltered"
                )

            iface.messageBar().pushMessage(
                message_category,
                QCoreApplication.translate(
                    "FinishedHandler", "Filter task : {0}"
                ).format(result_action),
                Qgis.MessageLevel.Success)

            # Restore source layer selection after filter/unfilter
            try:
                restore_selection_fn()
            except (RuntimeError, AttributeError) as sel_err:
                logger.debug(f"Could not restore source layer selection: {sel_err}")

            # Ensure canvas is refreshed after successful filter operation
            try:
                iface.mapCanvas().refresh()
            except (RuntimeError, AttributeError) as e:
                logger.debug(f"Ignored in post-filter canvas refresh: {e}")

        elif message_category == 'ExportLayers':
            if task_action == 'export':
                iface.messageBar().pushMessage(
                    message_category,
                    QCoreApplication.translate(
                        "FinishedHandler", "Export task : {0}"
                    ).format(task_message),
                    Qgis.MessageLevel.Success)

    def _handle_exception_result(
        self,
        result: Optional[bool],
        exception: Exception,
        message_category: str,
        iface: Any,
    ) -> None:
        """Handle task result when an exception occurred.

        Args:
            result: True if partial success, False if complete failure.
            exception: The exception that occurred.
            message_category: The message bar category string.
            iface: QGIS iface instance.

        Raises:
            Exception: Re-raises the exception if result is False (complete failure).
        """
        error_msg = QCoreApplication.translate(
            "FinishedHandler", "Exception: {0}"
        ).format(exception)
        logger.error(f"Task finished with exception: {error_msg}")

        # Display error to user
        iface.messageBar().pushMessage(
            message_category,
            error_msg,
            Qgis.MessageLevel.Critical)

        # Only raise exception if task completely failed (result is False)
        # If result is True, some layers may have been processed successfully
        if result is False:
            raise exception
        else:
            # Partial success - log but don't raise
            logger.warning(
                "Task completed with partial success. "
                f"Some operations succeeded but an exception occurred: {exception}"
            )

    @staticmethod
    def _display_apply_failures(failures: List[str], iface: Any) -> None:
        """Message bar warning for the filters the providers refused (2026-10-17)."""
        shown = "; ".join(failures[:3]) + (f" (+{len(failures) - 3})" if len(failures) > 3 else "")
        message = QCoreApplication.translate(
            "FinishedHandler", "Filter not applied, previous filter kept: {0}"
        ).format(shown)
        logger.warning(message)
        try:
            iface.messageBar().pushWarning("FilterMate", message)
        except (RuntimeError, AttributeError):
            pass

    @staticmethod
    def _release_task_caches(task_parameters: Dict[str, Any]) -> None:
        """Drop the backends' per-task caches (source union, buffered source, bbox).

        2026-10-17: they hang on the task object, which task_parameters (the
        source layer's PROJECT_LAYERS entry) keeps until the next task.
        """
        if not isinstance(task_parameters, dict):
            return
        for stale in ('_ogr_source_union_cache', '_ogr_buffered_source_cache', '_spatialite_source_bbox_cache'):
            task_parameters.pop(stale, None)
        task = task_parameters.get('_parent_task')
        store = getattr(task, '__dict__', None)
        if isinstance(store, dict):
            store.pop('_filtermate_task_caches', None)

    @staticmethod
    def _removed_target_names(task_parameters: Dict[str, Any]) -> List[str]:
        """Names of the task's target layers no longer in the project."""
        names = []
        project = QgsProject.instance()
        for props in ((task_parameters or {}).get('task') or {}).get('layers') or []:
            if not isinstance(props, dict) or not props.get('layer_id'):
                continue
            try:
                if project.mapLayer(props['layer_id']) is None:
                    names.append(props.get('layer_name') or props['layer_id'])
            except RuntimeError:
                continue
        return names

    @staticmethod
    def _display_removed_targets(names: List[str], iface: Any) -> None:
        """One warning for the target layers removed while the task ran."""
        text = QCoreApplication.translate(
            "FinishedHandler", "Layer(s) removed during the filter, left out: {0}").format(', '.join(names))
        logger.warning(text)
        try:
            iface.messageBar().pushWarning("FilterMate", text)
        except Exception as e:  # catch-all safety net: no message bar (shutdown)
            logger.debug(f"Removed targets not shown: {e}")

    def _log_task_bridge_metrics(self, task_bridge: Optional[Any]) -> None:
        """Log TaskBridge metrics for migration validation (MIG-023).

        Args:
            task_bridge: TaskBridge instance, if any.
        """
        if task_bridge is not None:
            try:
                metrics_report = task_bridge.get_metrics_report()
                logger.info(metrics_report)
            except (RuntimeError, AttributeError) as metrics_err:
                logger.debug(f"TaskBridge metrics logging failed: {metrics_err}")

    def cleanup_safe_intersect_layers(self) -> None:
        """Clean up orphaned safe_intersect temporary layers from the project.

        These layers are created during OGR/Spatialite filtering as GEOS-safe
        wrappers and should be removed after task completion to prevent project
        pollution.

        FIX 2026-01-17: Extracted from FilterEngineTask.
        """
        try:
            project = QgsProject.instance()
            layers_to_remove = []

            # Patterns for temp layers created by FilterMate
            temp_patterns = [
                r'_safe_intersect_\d+',
                r'_safe_source$',
                r'_safe_target$',
                r'_geos_safe$',
                r'^source_from_task$',
                r'^source_selection$',
                r'^source_filtered$',
                r'^source_field_based$',
                r'^source_expr_filtered$',
            ]

            for layer_id, layer in project.mapLayers().items():
                layer_name = layer.name()
                for pattern in temp_patterns:
                    if re.search(pattern, layer_name):
                        layers_to_remove.append(layer_id)
                        logger.debug(f"Marking for removal: {layer_name}")
                        break

            if layers_to_remove:
                project.removeMapLayers(layers_to_remove)
                logger.debug(f"Cleaned up {len(layers_to_remove)} temporary safe_intersect layers")
        except (RuntimeError, AttributeError) as e:
            logger.debug(f"safe_intersect cleanup failed (non-critical): {e}")

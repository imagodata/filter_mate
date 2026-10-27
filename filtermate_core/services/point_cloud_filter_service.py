# -*- coding: utf-8 -*-
"""
Point Cloud Filter Service.

Applies ``PointCloudFilterCriteria`` to a point cloud layer through injected
callables (subset writer and reader) and records every change in the history
service, so the existing undo/redo path restores the previous subset string.
Pure Python: no QGIS import, every dependency is injected.
"""
import logging
from typing import Any, Callable, TYPE_CHECKING

try:
    from ..domain.point_cloud_filter_criteria import PointCloudFilterResult
except ImportError:
    PointCloudFilterResult = None

if TYPE_CHECKING:
    from ..domain.point_cloud_filter_criteria import PointCloudFilterCriteria

logger = logging.getLogger('FilterMate.Core.Services.PointCloudFilterService')

POINT_CLOUD_BACKEND = "pointcloud"
INITIAL_STATE_DESCRIPTION = "Initial state (before first filter)"


class PointCloudFilterService:
    """Apply, clear and read the subset string of a point cloud layer."""

    def __init__(
        self,
        apply_subset: Callable[[Any, str], bool],
        read_subset: Callable[[Any], str],
        history_service: Any = None
    ) -> None:
        """
        Initialize the service.

        Args:
            apply_subset: Callable ``(layer, subset_string) -> bool`` writing the subset.
            read_subset: Callable ``(layer) -> str`` reading the current subset.
            history_service: Optional ``HistoryService`` receiving one entry per change.
        """
        self._apply_subset = apply_subset
        self._read_subset = read_subset
        self._history_service = history_service

    @property
    def history_service(self) -> Any:
        """History service receiving the filter entries (may be None)."""
        return self._history_service

    @history_service.setter
    def history_service(self, value: Any) -> None:
        self._history_service = value

    def apply(self, layer: Any, criteria: 'PointCloudFilterCriteria', combine_with_existing: bool = False) -> 'PointCloudFilterResult':
        """
        Apply the criteria to the layer.

        Args:
            layer: Point cloud layer.
            criteria: Criteria converted with ``to_subset_string()``.
            combine_with_existing: AND the new subset with the current one.

        Returns:
            PointCloudFilterResult describing the applied subset.
        """
        subset = criteria.to_subset_string()
        previous = self.current_subset(layer)
        if combine_with_existing and previous and subset:
            subset = f"({previous}) AND ({subset})"
        applied, message = self._write_subset(layer, subset)
        if applied:
            self._push_history(layer, subset, previous, "filter")
        return self._result(applied, subset, previous, message)

    def clear(self, layer: Any) -> 'PointCloudFilterResult':
        """
        Remove the subset of the layer.

        Args:
            layer: Point cloud layer.

        Returns:
            PointCloudFilterResult with an empty subset string.
        """
        previous = self.current_subset(layer)
        applied, message = self._write_subset(layer, "")
        if applied:
            self._push_history(layer, "", previous, "unfilter")
        return self._result(applied, "", previous, message)

    def current_subset(self, layer: Any) -> str:
        """
        Read the current subset of the layer.

        Args:
            layer: Point cloud layer.

        Returns:
            The subset string, or "" when unavailable.
        """
        try:
            return self._read_subset(layer) or ""
        except Exception as e:
            logger.debug(f"[PC] subset unreadable: {e}")
            return ""

    def _write_subset(self, layer: Any, subset: str):
        """Write the subset; returns ``(applied, message)``."""
        try:
            applied = bool(self._apply_subset(layer, subset))
        except Exception as e:
            logger.warning(f"[PC] subset application failed: {e}")
            return False, str(e)
        if not applied:
            logger.warning(f"[PC] subset rejected by the provider: {subset!r}")
            return False, "The point cloud provider rejected the subset string"
        return True, ""

    def _push_history(self, layer: Any, subset: str, previous: str, operation: str) -> None:
        """Record the change so the undo/redo handler can restore ``previous``."""
        if self._history_service is None:
            return
        try:
            layer_id = layer.id()
            history = self._history_service.get_or_create_history(layer_id)
            if previous and not self._history_service.get_history_for_layer(layer_id):
                history.push_state(
                    expression=previous,
                    feature_count=-1,
                    description=INITIAL_STATE_DESCRIPTION,
                    metadata={"backend": POINT_CLOUD_BACKEND, "operation": "initial", "layer_count": 1}
                )
            description = f"Point cloud filter: {subset[:60]}" if subset else "Point cloud filter cleared"
            history.push_state(
                expression=subset,
                feature_count=-1,
                description=description,
                metadata={"backend": POINT_CLOUD_BACKEND, "operation": operation, "layer_count": 1}
            )
        except Exception as e:
            logger.warning(f"[PC] history not updated: {e}")

    @staticmethod
    def _result(success: bool, subset: str, previous: str, message: str) -> 'PointCloudFilterResult':
        if PointCloudFilterResult is None:
            raise RuntimeError("core.domain.point_cloud_filter_criteria is not importable")
        return PointCloudFilterResult(success=success, subset_string=subset, previous_subset=previous, message=message)

# -*- coding: utf-8 -*-
"""
Spatialite Filter Executor.

v4.0.1: Wrapper implementing FilterExecutorPort for Spatialite backend.
Delegates to existing SpatialiteBackend to avoid breaking changes.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple, Callable

from ....core.ports.filter_executor_port import (
    FilterExecutorPort,
    FilterExecutionResult,
)
from .backend import SpatialiteBackend
from .filter_executor import (
    prepare_spatialite_source_geom,
    apply_spatialite_subset,
    cleanup_session_temp_tables,
)

logger = logging.getLogger('FilterMate')


class SpatialiteFilterExecutor(FilterExecutorPort):
    """
    FilterExecutorPort implementation for Spatialite/GeoPackage.

    Wraps existing SpatialiteBackend functionality to provide
    a clean interface for core/ without breaking existing code.
    """

    def __init__(self):
        """Initialize the Spatialite executor."""
        self._backend: Optional[SpatialiteBackend] = None

    def _get_backend(self) -> SpatialiteBackend:
        """Lazy initialization of backend."""
        if self._backend is None:
            from .backend import create_spatialite_backend
            self._backend = create_spatialite_backend()
        return self._backend

    def execute_filter(
        self,
        source_layer_info: Dict[str, Any],
        target_layers_info: List[Dict[str, Any]],
        expression: Optional[str] = None,
        predicates: Optional[Dict[str, str]] = None,
        buffer_value: float = 0.0,
        buffer_type: int = 0,
        use_centroids: bool = False,
        combine_operator: str = "AND",
        is_canceled_callback: Optional[Callable[[], bool]] = None,
    ) -> FilterExecutionResult:
        """
        Execute a filter operation using Spatialite.

        Delegates to existing SpatialiteBackend.execute() method.
        """
        import time
        start_time = time.time()

        try:
            backend = self._get_backend()

            # Check for cancellation
            if is_canceled_callback and is_canceled_callback():
                return FilterExecutionResult.cancelled()

            # Build filter parameters compatible with existing backend
            filter_params = {
                'expression': expression,
                'predicates': predicates or {},
                'buffer_value': buffer_value,
                'buffer_type': buffer_type,
                'use_centroids': use_centroids,
                'combine_operator': combine_operator,
            }

            # Execute via existing backend
            result = backend.execute(
                source_layer_info=source_layer_info,
                target_layer_infos=target_layers_info,
                **filter_params
            )

            execution_time = (time.time() - start_time) * 1000

            if result.success:
                return FilterExecutionResult.success(
                    feature_ids=result.feature_ids or [],
                    expression=result.expression,
                    backend='spatialite',
                    execution_time=execution_time
                )
            else:
                return FilterExecutionResult.failed(
                    error=result.error_message or "Unknown error",
                    backend='spatialite'
                )

        except Exception as e:
            logger.error(f"[Spatialite] Spatialite filter execution failed: {e}")
            return FilterExecutionResult.failed(str(e), backend='spatialite')

    def prepare_source_geometry(
        self,
        layer_info: Dict[str, Any],
        feature_ids: Optional[List[int]] = None,
        buffer_value: float = 0.0,
        use_centroids: bool = False,
    ) -> Tuple[Any, Optional[str]]:
        """Prepare source geometry using existing function."""
        try:
            layer = layer_info.get('layer')
            if not layer:
                return None, "No layer provided"

            result = prepare_spatialite_source_geom(
                layer=layer,
                feature_ids=feature_ids,
                buffer_value=buffer_value,
                use_centroids=use_centroids
            )

            return result, None

        except Exception as e:
            logger.error(f"[Spatialite] Spatialite geometry preparation failed: {e}")
            return None, str(e)

    def apply_subset_string(
        self,
        layer: Any,
        expression: str
    ) -> bool:
        """Apply subset string to layer."""
        try:
            return apply_spatialite_subset(layer, expression)
        except Exception as e:
            logger.error(f"[Spatialite] Failed to apply Spatialite subset: {e}")
            return False

    def cleanup_resources(self, session_id: Optional[str] = None, db_paths: Optional[List[str]] = None,
                          exclude_referenced_by: Optional[List[str]] = None) -> int:
        """Clean up the temporary tables of a session.

        The registry calls this at the end of every task, without arguments: nothing is
        dropped then, because the filter the task has just made reads its temp table until
        the main thread applies the queued subset. Tables go only when the caller names the
        session and the databases, and never those a layer is still filtered through.

        Args:
            session_id: Session whose tables are dropped.
            db_paths: Databases to clean.
            exclude_referenced_by: Subset strings of layers in use.

        Returns:
            int: Number of tables dropped.
        """
        if not session_id or not db_paths:
            return 0
        dropped = 0
        try:
            for db_path in db_paths:
                dropped += cleanup_session_temp_tables(
                    db_path, session_id, exclude_referenced_by=exclude_referenced_by)
            logger.debug(f"[Spatialite] Spatialite temp tables cleaned up ({dropped})")
        except Exception as e:
            logger.warning(f"[Spatialite] Spatialite cleanup failed: {e}")
        return dropped

    @property
    def backend_name(self) -> str:
        return "spatialite"

    @property
    def supports_spatial_index(self) -> bool:
        return True  # R-tree support

    @property
    def supports_materialized_views(self) -> bool:
        return False  # Uses temp tables instead

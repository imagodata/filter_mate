# -*- coding: utf-8 -*-
"""
FilterMate QGIS Tasks module.

Phase 4 Task Refactoring - ARCH-046/047

Provides focused, single-responsibility task classes
for async operations in QGIS.

Task Categories:
- BaseTask: Abstract base for all tasks
- FilterTask: Layer filtering operations
- SpatialTask: Spatial filter operations
- LayerTask: Layer management operations
- MultiStepTask: Multi-step progressive filtering
- ProgressHandler: Centralized progress reporting

Note: Export operations live in core/tasks/export_handler.py and are
driven by FilterEngineTask(task_action='export'). The standalone
ExportTask/BatchExportTask wrappers were removed (unused, missing
hardening from ad54833b/f769f134).

Migration from modules/appTasks.py:
    OLD: from adapters.qgis.tasks import FilterEngineTask
    NEW: from adapters.qgis.tasks import FilterTask
"""

from .base_task import (  # noqa: F401
    BaseFilterMateTask,
    TaskResult,
    TaskStatus,
)

from .filter_task import (  # noqa: F401
    FilterTask,
    ClearFilterTask,
)

from .spatial_task import (  # noqa: F401
    SpatialFilterTask,
    BufferFilterTask,
)

from .layer_task import (  # noqa: F401
    GatherLayerInfoTask,
    ValidateExpressionsTask,
    CreateSpatialIndexTask,
)

from .multi_step_task import (  # noqa: F401
    MultiStepFilterTask,
)

from .progress_handler import (  # noqa: F401
    ProgressHandler,
    ProgressAggregator,
    ProgressEvent,
    ProgressPhase,
)

__all__ = [
    # Base
    'BaseFilterMateTask',
    'TaskResult',
    'TaskStatus',
    # Filter
    'FilterTask',
    'ClearFilterTask',
    # Spatial
    'SpatialFilterTask',
    'BufferFilterTask',
    # Layer
    'GatherLayerInfoTask',
    'ValidateExpressionsTask',
    'CreateSpatialIndexTask',
    # Multi-step (MIG-023)
    'MultiStepFilterTask',
    # Progress (MIG-023)
    'ProgressHandler',
    'ProgressAggregator',
    'ProgressEvent',
    'ProgressPhase',
]

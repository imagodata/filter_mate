"""
Config Provider Module

EPIC-1 Phase E7.5: Extracted from modules/tasks/filter_task.py

Provides configuration extraction utilities for:
- Optimization thresholds
- Geometry simplification settings
- Other runtime configuration

Author: FilterMate Team
Created: January 2026 (EPIC-1 Phase E7.5)
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('FilterMate.Core.Optimization.ConfigProvider')


# Default optimization thresholds
DEFAULT_OPTIMIZATION_THRESHOLDS = {
    'large_dataset_warning': 50000,
    'async_expression_threshold': 10000,
    'update_extents_threshold': 50000,
    'centroid_optimization_threshold': 5000,
    'exists_subquery_threshold': 100000,
    'parallel_processing_threshold': 100000,
    'progress_update_batch_size': 100,
    'source_mv_fid_threshold': 500
}

# Default simplification configuration
DEFAULT_SIMPLIFICATION_CONFIG = {
    'enabled': True,
    'max_wkt_length': 100000,
    'preserve_topology': True,
    'min_tolerance_meters': 1.0,
    'max_tolerance_meters': 100.0,
    'show_warnings': True
}


def get_app_options(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """``APP.OPTIONS`` of the FilterMate configuration carried by ``params``.

    2026-10-17: the readers looked for ``params['config']``, a key nothing
    sets. The configuration travels as:

    - ``params['task']['config_data']``: filter and export tasks (set by
      FilterMateApp.get_task_parameters), layer management tasks;
    - ``params['config_data']``: TaskParameters.to_legacy_format;
    - ``params['CONFIG_DATA']``: ``ENV_VARS`` itself.

    Returns an empty dict when none is there (the callers use defaults).
    """
    if not isinstance(params, dict):
        return {}
    task_section = params.get('task')
    candidates = (
        task_section.get('config_data') if isinstance(task_section, dict) else None,
        params.get('config_data'),
        params.get('CONFIG_DATA'),
    )
    for config in candidates:
        if isinstance(config, dict) and isinstance(config.get('APP'), dict):
            options = config['APP'].get('OPTIONS')
            return options if isinstance(options, dict) else {}
    return {}


def _option_value(entry: Any, default: Any) -> Any:
    """Value of a configuration entry: ``{"value": x, ...}`` or a plain ``x``."""
    if isinstance(entry, dict):
        return entry.get('value', default)
    return default if entry is None else entry


def get_app_option_value(params: Optional[Dict[str, Any]], section: str, key: str, default: Any) -> Any:
    """``APP.OPTIONS.<section>.<key>`` value from ``params``, ``default`` when absent."""
    section_config = get_app_options(params).get(section)
    if not isinstance(section_config, dict):
        return default
    return _option_value(section_config.get(key), default)


def get_optimization_thresholds(task_parameters: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    """
    Get optimization thresholds configuration from task parameters or defaults.

    Thresholds control:
    - large_dataset_warning: Feature count for performance warnings
    - async_expression_threshold: Feature count for async expressions
    - update_extents_threshold: Feature count for auto extent update
    - centroid_optimization_threshold: Feature count for centroid optimization
    - exists_subquery_threshold: WKT length for EXISTS mode
    - parallel_processing_threshold: Feature count for parallel processing
    - progress_update_batch_size: Features per progress update
    - source_mv_fid_threshold: Max FIDs for inline IN clause (above creates MV)

    Args:
        task_parameters: Task parameters or ENV_VARS (see get_app_options)

    Returns:
        dict: Optimization thresholds
    """
    opt_config = get_app_options(task_parameters).get('OPTIMIZATION_THRESHOLDS')
    if not isinstance(opt_config, dict) or not opt_config:
        return DEFAULT_OPTIMIZATION_THRESHOLDS.copy()

    return {
        key: _option_value(opt_config.get(key), default)
        for key, default in DEFAULT_OPTIMIZATION_THRESHOLDS.items()
    }


def get_simplification_config(task_parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get geometry simplification configuration from task parameters or defaults.

    Configuration controls:
    - enabled: Whether simplification is enabled
    - max_wkt_length: Maximum WKT string length
    - preserve_topology: Whether to preserve topology during simplification
    - min_tolerance_meters: Minimum tolerance in meters
    - max_tolerance_meters: Maximum tolerance in meters
    - show_warnings: Whether to show simplification warnings

    Args:
        task_parameters: Task parameters or ENV_VARS (see get_app_options)

    Returns:
        dict: Simplification configuration
    """
    simp_config = get_app_options(task_parameters).get('GEOMETRY_SIMPLIFICATION')
    if not isinstance(simp_config, dict) or not simp_config:
        return DEFAULT_SIMPLIFICATION_CONFIG.copy()

    # 'show_warnings' is stored as 'show_simplification_warnings'
    config_keys = {'show_warnings': 'show_simplification_warnings'}
    return {
        key: _option_value(simp_config.get(config_keys.get(key, key)), default)
        for key, default in DEFAULT_SIMPLIFICATION_CONFIG.items()
    }

"""
Logging Utilities Module

EPIC-1 Phase E7.5: Extracted from modules/tasks/filter_task.py

Provides logging utilities for:
- Filtering operation summaries
- Backend information logging
- Performance diagnostics

Author: FilterMate Team
Created: January 2026 (EPIC-1 Phase E7.5)
"""

import logging
from typing import List, Optional

logger = logging.getLogger('FilterMate.Core.Optimization.LoggingUtils')


def log_filtering_summary(
    layers_count: int,
    successful_filters: int,
    failed_filters: int,
    failed_layer_names: Optional[List[str]] = None,
    log_to_qgis: bool = True
) -> None:
    """
    Log summary of filtering results.

    Provides a detailed summary of the geometric filtering operation,
    including success/failure counts and recommendations for failed layers.

    Args:
        layers_count: Total number of layers in the filter operation
        successful_filters: Number of layers that filtered successfully
        failed_filters: Number of layers that failed to filter
        failed_layer_names: Optional list of names of layers that failed
        log_to_qgis: Whether to also log to QGIS message panel
    """
    if failed_layer_names is None:
        failed_layer_names = []

    logger.info("")
    logger.info("=" * 70)
    logger.info("GEOMETRIC FILTERING SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Total layers: {layers_count}")
    logger.info(f"  Success: {successful_filters}")
    logger.info(f"  Failures: {failed_filters}")

    # Log to QGIS message panel if requested
    if log_to_qgis:
        try:
            from qgis.core import QgsMessageLog, Qgis as QgisLevel

            if failed_filters > 0:
                QgsMessageLog.logMessage(
                    f"📊 Filter summary: {successful_filters} OK, {failed_filters} failed ({', '.join(failed_layer_names[:3])})",
                    "FilterMate", QgisLevel.Warning
                )
            else:
                QgsMessageLog.logMessage(
                    f"📊 Filter summary: {successful_filters} layers filtered successfully",
                    "FilterMate", QgisLevel.Info
                )
        except ImportError:
            pass  # Not in QGIS environment

    if failed_filters > 0:
        logger.info("")
        if failed_layer_names:
            logger.info("  FAILED LAYERS:")
            for name in failed_layer_names[:10]:  # Show first 10
                logger.info(f"     • {name}")
            if len(failed_layer_names) > 10:
                logger.info(f"     ... and {len(failed_layer_names) - 10} more")
        logger.info("")
        logger.info("  TIP: If layers fail with the Spatialite backend:")
        logger.info("     -> Check that layers are GeoPackage/SQLite")
        logger.info("     -> Shapefiles do not support Spatialite functions")
        logger.info("     -> Try the OGR backend (QGIS processing) for these layers")
    logger.info("=" * 70)


def log_backend_info(
    task_action: str,
    provider_type: str,
    postgresql_available: bool,
    feature_count: int,
    large_dataset_threshold: int,
    provider_postgres: str = 'postgresql',
    provider_spatialite: str = 'spatialite',
    provider_ogr: str = 'ogr'
) -> None:
    """
    Log backend information and performance warnings for filtering tasks.

    Only logs if task_action is 'filter'.

    Args:
        task_action: Current task action ('filter', 'unfilter', 'reset', etc.)
        provider_type: Provider type being used
        postgresql_available: Whether PostgreSQL/psycopg2 is available
        feature_count: Number of features in source layer
        large_dataset_threshold: Threshold for large dataset warnings
        provider_postgres: Provider type constant for PostgreSQL
        provider_spatialite: Provider type constant for Spatialite
        provider_ogr: Provider type constant for OGR
    """
    if task_action != 'filter':
        return

    # Determine active backend
    backend_name = "Memory/QGIS"
    if postgresql_available and provider_type == provider_postgres:
        backend_name = "PostgreSQL/PostGIS"
    elif provider_type == provider_spatialite:
        backend_name = "Spatialite"
    elif provider_type == provider_ogr:
        backend_name = "OGR"

    logger.debug(f"Using {backend_name} backend for filtering")

    # Performance warning for large datasets without PostgreSQL
    if large_dataset_threshold > 0 and feature_count > large_dataset_threshold and not (
        postgresql_available and provider_type == provider_postgres
    ):
        logger.warning(
            f"Large dataset detected ({feature_count:,} features > {large_dataset_threshold:,} threshold) without PostgreSQL backend. "
            "Performance may be reduced. Consider using PostgreSQL/PostGIS for optimal performance."
        )

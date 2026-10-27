"""
Performance Advisor Module

EPIC-1 Phase E7.5: Extracted from modules/tasks/filter_task.py

Provides contextual performance warnings and recommendations based on:
- Current backend (PostgreSQL, Spatialite, OGR)
- Query duration
- Dataset size

Author: FilterMate Team
Created: January 2026 (EPIC-1 Phase E7.5)
"""

import logging
from typing import Optional

logger = logging.getLogger('FilterMate.Core.Optimization.PerformanceAdvisor')


def get_contextual_performance_warning(
    elapsed_time: float,
    provider_type: str,
    postgresql_available: bool = True,
    severity: str = 'warning'
) -> Optional[str]:
    """
    Generate contextual performance warning based on current backend.

    Provides relevant advice based on current backend instead of always suggesting PostgreSQL.

    Args:
        elapsed_time: Query duration in seconds
        provider_type: Provider type ('postgresql', 'spatialite', 'ogr')
        postgresql_available: Whether PostgreSQL/psycopg2 is available
        severity: 'warning' or 'critical'

    Returns:
        Contextual warning message string, or None if no warning needed
    """
    is_postgresql = postgresql_available and provider_type == 'postgresql'
    is_spatialite = provider_type == 'spatialite'
    is_ogr = provider_type == 'ogr'

    # Base message with timing
    base_msg = f"Filter query took {elapsed_time:.1f}s"

    if is_postgresql:
        # Already using PostgreSQL - suggest complexity reduction
        if severity == 'critical':
            return (
                f"{base_msg} (backend: PostgreSQL). "
                "To improve performance, you can: "
                "reduce the buffer radius, limit the number of layers, "
                "or create spatial indexes on the affected tables."
            )
        else:
            return (
                f"{base_msg} (backend: PostgreSQL). "
                "Normal time for a complex query. "
                "Check your spatial indexes if performance remains slow."
            )
    elif is_spatialite:
        # Using Spatialite - suggest PostgreSQL for large datasets
        if severity == 'critical':
            return (
                f"{base_msg} (backend: Spatialite). "
                "For better performance, consider: "
                "PostgreSQL/PostGIS for large datasets, "
                "or reduce filter complexity."
            )
        else:
            return (
                f"{base_msg} (backend: Spatialite). "
                "Acceptable performance. PostgreSQL/PostGIS would be faster "
                "for frequent queries on this dataset."
            )
    elif is_ogr:
        # Using OGR fallback - suggest optimized backend
        if severity == 'critical':
            return (
                f"{base_msg} (backend: OGR/memory). "
                "For better performance, use PostgreSQL/PostGIS "
                "or Spatialite. The current backend is not optimized for large data."
            )
        else:
            return (
                f"{base_msg} (backend: OGR/memory). "
                "Consider PostgreSQL or GeoPackage (Spatialite) for better performance."
            )
    else:
        # Unknown/default backend
        if severity == 'critical':
            return (
                f"{base_msg}. "
                "For better performance, use PostgreSQL/PostGIS "
                "or reduce filter complexity."
            )
        else:
            return (
                f"{base_msg}. "
                "High processing time. Check data size and filter complexity."
            )

# -*- coding: utf-8 -*-
"""
Spatialite Expression Builder: the QGIS side of the SpatiaLite / GeoPackage spatial filters.

2026-10-28 (S0 step 4): the SQL generation and the GeoPackage R-tree lookups
moved to ``filtermate_core.sql.spatialite.expression_builder.SpatialiteSqlBuilder``;
its constants and helpers are re-exported here for the plugin.
``SpatialiteExpressionBuilder`` keeps its name and its callers (factory,
LegacyAdapter) and adds what needs QGIS:

- ``supports_layer`` / ``apply_filter``: the subset string on a QgsVectorLayer;
- the host hooks of the core builder: the source bounding box with
  QgsGeometry and QgsCoordinateTransform, and the JSON1 probe of GDAL's SQLite.
"""

from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from qgis.core import QgsVectorLayer

try:
    from ....filtermate_core.sql.spatialite.expression_builder import (  # noqa: F401
        RTREE_CHECK_TTL_SECONDS,
        RTREE_COUNT_CACHE_MAX,
        RTREE_PREFILTER_PREDICATES,
        SPATIALITE_INLINE_BUDGET_SECONDS,
        SPATIALITE_INLINE_COST_US_PER_ROW_KB,
        SPATIALITE_INLINE_SQL_BUFFER_FACTOR,
        SPATIALITE_WKT_INLINE_MAX_LENGTH,
        SPATIALITE_WKT_STATIC_INLINE_LIMIT,
        SpatialiteSqlBuilder,
        USE_OGR_FALLBACK,
        clear_rtree_cache,
        gpkg_has_rtree,
        gpkg_layer_location,
        gpkg_rtree_count,
        logger,
        task_scoped_cache,
    )
except ImportError:  # imported from the repository root (tests)
    from filtermate_core.sql.spatialite.expression_builder import (  # noqa: F401
        RTREE_CHECK_TTL_SECONDS,
        RTREE_COUNT_CACHE_MAX,
        RTREE_PREFILTER_PREDICATES,
        SPATIALITE_INLINE_BUDGET_SECONDS,
        SPATIALITE_INLINE_COST_US_PER_ROW_KB,
        SPATIALITE_INLINE_SQL_BUFFER_FACTOR,
        SPATIALITE_WKT_INLINE_MAX_LENGTH,
        SPATIALITE_WKT_STATIC_INLINE_LIMIT,
        SpatialiteSqlBuilder,
        USE_OGR_FALLBACK,
        clear_rtree_cache,
        gpkg_has_rtree,
        gpkg_layer_location,
        gpkg_rtree_count,
        logger,
        task_scoped_cache,
    )

# Import safe_set_subset_string from infrastructure
try:
    from ....infrastructure.database.sql_utils import safe_set_subset_string
except ImportError:
    def safe_set_subset_string(layer, expression):
        """Fallback implementation."""
        if layer is None:
            return False
        try:
            return layer.setSubsetString(expression)
        except Exception:
            return False


def json1_available() -> bool:
    """Whether GDAL's SQLite has ``json_each`` (see infrastructure.database.sqlite_capabilities)."""
    try:
        from ....infrastructure.database.sqlite_capabilities import gdal_sqlite_json1_available
    except ImportError:
        try:
            from infrastructure.database.sqlite_capabilities import gdal_sqlite_json1_available
        except ImportError:
            return False
    return gdal_sqlite_json1_available()


class SpatialiteExpressionBuilder(SpatialiteSqlBuilder):
    """SpatiaLite / GeoPackage spatial filters on QGIS layers (see the module docstring)."""

    def supports_layer(self, layer: 'QgsVectorLayer') -> bool:
        """
        Check if this backend supports the given layer.

        Args:
            layer: QGIS vector layer to check

        Returns:
            True if layer is Spatialite or GeoPackage
        """
        if layer is None:
            return False

        provider = layer.providerType()
        if provider == 'spatialite':
            return True

        # Check for GeoPackage via OGR
        if provider == 'ogr':
            source = layer.source().lower()
            if '.gpkg' in source or 'gpkg|' in source:
                return True

        return False

    def apply_filter(
        self,
        layer: 'QgsVectorLayer',
        expression: str,
        old_subset: Optional[str] = None,
        combine_operator: Optional[str] = None
    ) -> bool:
        """
        Apply filter to Spatialite layer.

        Args:
            layer: Layer to filter
            expression: SQL expression
            old_subset: Existing filter
            combine_operator: Combine operator (AND/OR)

        Returns:
            True if filter applied successfully
        """
        try:
            if not expression:
                self.last_error = "Empty expression, skipping filter"
                self.log_warning(self.last_error)
                return False

            # Check for OGR fallback sentinel
            if expression == USE_OGR_FALLBACK:
                self.last_error = "OGR fallback requested"
                self.log_info(self.last_error)
                return False

            # Combine with existing filter if needed
            if old_subset and combine_operator:
                if self._is_geometric_filter(old_subset):
                    self.log_info("Replacing geometric filter in old_subset")
                    final_expression = expression
                else:
                    final_expression = f"({old_subset}) {combine_operator} ({expression})"
            else:
                final_expression = expression

            # 2026-04-29 fix: prefer the task's subset queue when available so
            # `setSubsetString` runs on the Qt main thread. The cascade is
            # invoked from `QgsTask.run()` (worker thread) and the docstring
            # of ``FilterEngineTask.queue_subset_request`` is explicit:
            # "Subset strings cannot be applied directly from background
            # threads due to Qt thread safety constraints." Calling
            # `safe_set_subset_string` straight from the worker silently
            # no-ops on spatialite (the cascade reported "8/8 filtered
            # successfully" while every distant layer kept its full feature
            # count). When no queue is wired (tests, public-API direct use),
            # fall back to the synchronous path.
            queue_callback = self.task_params.get('_subset_queue_callback') if self.task_params else None
            if queue_callback is not None:
                queue_callback(layer, final_expression)
                self.log_info("✓ Filter queued for main-thread application")
                return True

            success = safe_set_subset_string(layer, final_expression)

            if success:
                self.log_info("✓ Filter applied successfully")
            else:
                self.last_error = f"setSubsetString failed for {layer.name()} (spatialite)"
                self.log_error(f"✗ Failed to apply filter: {self.last_error}")

            return success

        except Exception as e:
            self.last_error = f"Spatialite apply_filter exception: {e}"
            self.log_error(self.last_error)
            return False

    # =========================================================================
    # Host hooks of SpatialiteSqlBuilder
    # =========================================================================

    def _wkt_bounds_in_target_crs(
        self, source_wkt: str, source_srid: int, target_srid: int
    ) -> Optional[Tuple[float, float, float, float]]:
        """QgsGeometry's bounding box, reprojected with QgsCoordinateTransform when the SRIDs differ."""
        from qgis.core import (
            QgsGeometry, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
        )
        geometry = QgsGeometry.fromWkt(source_wkt)
        if geometry is None or geometry.isEmpty():
            return None
        bbox = geometry.boundingBox()
        if source_srid != target_srid:
            source_crs = QgsCoordinateReferenceSystem(f"EPSG:{source_srid}")
            target_crs = QgsCoordinateReferenceSystem(f"EPSG:{target_srid}")
            if not source_crs.isValid() or not target_crs.isValid():
                return None
            bbox = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance()).transformBoundingBox(bbox)
        if bbox.isNull():
            return None
        return (bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum())

    def _json1_available(self) -> bool:
        """The JSON1 probe of GDAL's SQLite (the OGR backend's key lists)."""
        return json1_available()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'SpatialiteExpressionBuilder',
    'USE_OGR_FALLBACK',
]

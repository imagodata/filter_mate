# -*- coding: utf-8 -*-
"""
PostgreSQL Expression Builder: the QGIS side of the PostGIS spatial filters.

2026-10-27 (S0 step 3): the SQL generation moved to
``filtermate_core.sql.postgresql.expression_builder.PostgreSQLSqlBuilder``.
``PostgreSQLExpressionBuilder`` keeps its name and its callers (factory,
LegacyAdapter, FilterEngineTask) and adds what needs QGIS:

- ``supports_layer`` / ``apply_filter``: the subset string on a QgsVectorLayer;
- the host hooks of the core builder: the layer's database connection,
  the QGIS message log, and the QGIS CRS database for authids and lon/lat SRIDs
  (the core's EPSG-only answers remain the fallback, as before).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from qgis.core import QgsVectorLayer

try:
    from ....filtermate_core.sql.postgresql.expression_builder import (  # noqa: F401
        CHAIN_OPTIMIZER_AVAILABLE,
        PostgreSQLSqlBuilder,
        _GEOGRAPHIC_SRIDS,
        logger,
    )
except ImportError:  # imported from the repository root (tests)
    from filtermate_core.sql.postgresql.expression_builder import (  # noqa: F401
        CHAIN_OPTIMIZER_AVAILABLE,
        PostgreSQLSqlBuilder,
        _GEOGRAPHIC_SRIDS,
        logger,
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


class PostgreSQLExpressionBuilder(PostgreSQLSqlBuilder):
    """PostGIS spatial filters on QGIS PostgreSQL layers (see the module docstring)."""

    def supports_layer(self, layer: 'QgsVectorLayer') -> bool:
        """
        Check if this backend supports the given layer.

        Args:
            layer: QGIS vector layer to check

        Returns:
            True if layer is PostgreSQL
        """
        if layer is None:
            return False
        return layer.providerType() == 'postgres'

    def apply_filter(
        self,
        layer: 'QgsVectorLayer',
        expression: str,
        old_subset: Optional[str] = None,
        combine_operator: Optional[str] = None
    ) -> bool:
        """
        Apply filter to PostgreSQL layer.

        Args:
            layer: PostgreSQL layer to filter
            expression: PostGIS SQL expression
            old_subset: Existing subset string
            combine_operator: Operator to combine (AND/OR)

        Returns:
            True if filter applied successfully
        """
        # DIAGNOSTIC 2026-01-19: Trace apply_filter execution

        try:
            if not expression:
                self.last_error = "Empty expression, skipping filter"
                self.log_warning(self.last_error)
                return False

            # Normalize column case and apply type casting
            expression = self._normalize_column_case(expression, layer)
            expression = self._apply_numeric_type_casting(expression, layer)

            if old_subset:
                old_subset = self._normalize_column_case(old_subset, layer)
                old_subset = self._apply_numeric_type_casting(old_subset, layer)

            # Handle existing subset
            if old_subset and combine_operator:
                # Check if old subset contains geometric filter (should be replaced)
                if self._is_geometric_filter(old_subset):
                    self.log_info("🔄 Replacing geometric filter in old_subset")
                    final_expression = expression
                else:
                    # Combine with attribute filter
                    final_expression = f"({old_subset}) {combine_operator} ({expression})"
                    self.log_info(f"✅ Combined with existing filter using {combine_operator}")
            else:
                final_expression = expression

            # DIAGNOSTIC: Print final expression before applying

            # Apply filter
            # FIX v4.2.13: Enhanced logging for debugging failures
            self.log_info(f"📝 Applying PostgreSQL filter to {layer.name()}:")
            self.log_info(f"   Expression length: {len(final_expression)} chars")
            self.log_debug(f"   Expression preview: {final_expression[:300]}...")

            # 2026-04-29 fix: prefer the task's subset queue when available so
            # `setSubsetString` runs on the Qt main thread. Same root cause as
            # the spatialite cascade silent no-op — calling setSubsetString
            # straight from `QgsTask.run()` (worker) is not thread-safe per
            # `FilterEngineTask.queue_subset_request` docstring. PG appeared
            # to "work" historically only because EXISTS subsets are short
            # enough that the worker-thread call sometimes succeeds; routing
            # through the queue eliminates the race for both backends.
            queue_callback = self.task_params.get('_subset_queue_callback') if self.task_params else None
            if queue_callback is not None:
                queue_callback(layer, final_expression)
                self.log_info(f"✓ Filter queued for main-thread application: {layer.name()}")
                return True

            success = safe_set_subset_string(layer, final_expression)

            if success:
                self.log_info(f"✓ Filter applied successfully to {layer.name()}")
                self.log_info(f"   → Feature count after filter: {layer.featureCount()}")
            else:
                self.last_error = f"setSubsetString failed for {layer.name()} (postgresql, expr_len={len(final_expression)})"
                self.log_error(f"✗ FAILED to apply filter to {layer.name()}!")
                self.log_error("   → This triggers OGR fallback")
                # Log the FULL expression for debugging (not truncated)
                self.log_error(f"   Expression that FAILED:\n{final_expression}")

            return success

        except Exception as e:
            self.last_error = f"PostgreSQL apply_filter exception: {e}"
            self.log_error(self.last_error)
            return False

    # =========================================================================
    # Host hooks of PostgreSQLSqlBuilder
    # =========================================================================

    def _connection_for_layer(self, layer):
        """The psycopg2 connection of the layer's data source (None without one)."""
        from ....infrastructure.utils import get_datasource_connexion_from_layer
        connexion, _ = get_datasource_connexion_from_layer(layer)
        return connexion

    def _notify_user_warning(self, message: str) -> None:
        """The QGIS message log, FilterMate tab."""
        from qgis.core import QgsMessageLog, Qgis
        QgsMessageLog.logMessage(message, "FilterMate", Qgis.MessageLevel.Warning)

    @classmethod
    def _authid_to_srid(cls, authid) -> Optional[int]:
        """The QGIS CRS database first (any authority), then the core's ``EPSG:<n>``."""
        if authid and isinstance(authid, str):
            try:
                from qgis.core import QgsCoordinateReferenceSystem
                srid = cls._positive_srid(QgsCoordinateReferenceSystem(authid).postgisSrid())
                if srid:
                    return srid
            except Exception:  # nosec B110 - no QGIS CRS database: parse the EPSG code
                pass
        return super()._authid_to_srid(authid)

    @staticmethod
    def _srid_is_geographic(srid: Optional[int]) -> bool:
        """The QGIS CRS database first, then the core's known lon/lat SRIDs."""
        if not srid:
            return False
        try:
            from qgis.core import QgsCoordinateReferenceSystem
            crs = QgsCoordinateReferenceSystem(f"EPSG:{int(srid)}")
            if crs.isValid() is True:
                return crs.isGeographic() is True
        except Exception:  # nosec B110 - no QGIS CRS database: known lon/lat SRIDs
            pass
        return PostgreSQLSqlBuilder._srid_is_geographic(srid)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'PostgreSQLExpressionBuilder',
]

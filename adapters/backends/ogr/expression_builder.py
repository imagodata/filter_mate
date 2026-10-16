# -*- coding: utf-8 -*-
"""
OGR Expression Builder.

v4.1.0: Migrated from before_migration/modules/backends/ogr_backend.py

This module contains the filter logic for OGR-based layers (Shapefiles, etc.).
Unlike PostgreSQL/Spatialite, OGR uses QGIS processing algorithms for filtering.

It implements the GeometricFilterPort interface for backward compatibility.

Features:
- QGIS processing selectbylocation algorithm
- Memory layer optimization for PostgreSQL
- Spatial index auto-creation
- Thread-safe reference management
- Cancellable feedback for interruption

Author: FilterMate Team
Date: January 2026
"""

import json
import logging
import threading
from typing import Dict, Optional, Any

from qgis.core import QgsVectorLayer

logger = logging.getLogger('FilterMate.Backend.OGR.ExpressionBuilder')

# 2026-10-17: above this many keys, a GeoPackage / SQLite key-list subset is
# written as ONE JSON string literal, ``"fid" IN (SELECT value FROM
# json_each('[...]'))``. QGIS 4.2.3 stayed frozen for more than 25 min in
# setSubsetString() with ``"fid" IN (98,687 literals)`` on troncon_de_route
# (more than 10 min headless), while SQLite itself counted them in 0.1 s:
# the long literal list goes through GDAL's SQL parsing. The JSON form took
# 0.29 s to apply, 0.14 s to count, 0.8 s for the extent and 0.74 s to read
# the 98,687 rows out of 1.15 million (BD TOPO 31 roads, headless QGIS 4.2.3).
KEY_LIST_JSON_THRESHOLD = 1000
# 2026-10-17: other OGR formats (Shapefile...) evaluate the subset with OGR
# SQL, which rescans the IN list for every row: on the 383,112 BD TOPO roads
# as a Shapefile, a read took 3.4 s with 1,000 keys and 8.7 s with 4,000,
# and QGIS refused 8,000 (setSubsetString False, layer left unfiltered).
# Above PLAIN_KEY_LIST_WARNING a WARNING names the cost; above
# PLAIN_KEY_LIST_MAX the filter is refused with an explicit error.
PLAIN_KEY_LIST_WARNING = 1000
PLAIN_KEY_LIST_MAX = 5000

# Import the port interface
try:
    from ....core.ports.geometric_filter_port import GeometricFilterPort
except ImportError:
    from core.ports.geometric_filter_port import GeometricFilterPort

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

# Thread safety for OGR operations
_ogr_operations_lock = threading.Lock()
_last_operation_thread = None

# Import QgsProcessingFeedback for proper inheritance
try:
    from qgis.core import QgsProcessingFeedback
    _HAS_PROCESSING_FEEDBACK = True
except ImportError:
    _HAS_PROCESSING_FEEDBACK = False
    QgsProcessingFeedback = object  # Fallback for type hints


class CancellableFeedback(QgsProcessingFeedback if _HAS_PROCESSING_FEEDBACK else object):
    """
    Feedback class for cancellable QGIS processing operations.

    Inherits from QgsProcessingFeedback to be compatible with QGIS processing.
    Allows interrupting long-running processing algorithms.
    """

    def __init__(self, is_cancelled_callback=None):
        """
        Initialize feedback.

        Args:
            is_cancelled_callback: Callable returning True if cancelled
        """
        if _HAS_PROCESSING_FEEDBACK:
            super().__init__()
        self._cancelled = False
        self._is_cancelled_callback = is_cancelled_callback

    def isCanceled(self) -> bool:
        """Check if operation is cancelled."""
        if self._cancelled:
            return True
        if self._is_cancelled_callback:
            return self._is_cancelled_callback()
        return False

    def cancel(self):
        """Cancel the operation."""
        self._cancelled = True
        if _HAS_PROCESSING_FEEDBACK:
            try:
                super().cancel()
            except Exception:  # nosec B110 - best-effort forward to base feedback, safe to ignore if unavailable
                pass

    def setProgress(self, progress: float):
        """Set progress (0-100)."""
        if _HAS_PROCESSING_FEEDBACK:
            try:
                super().setProgress(progress)
            except Exception:  # nosec B110 - best-effort forward to base feedback, safe to ignore if unavailable
                pass


class OGRExpressionBuilder(GeometricFilterPort):
    """
    OGR expression builder.

    Uses QGIS processing algorithms for spatial filtering since OGR
    providers don't support complex SQL expressions.

    Implements the legacy GeometricFilterPort interface.

    Features:
    - QGIS selectbylocation algorithm
    - FID-based filtering
    - Memory layer optimization
    - Cancellable operations

    Example:
        builder = OGRExpressionBuilder(task_params)
        expr = builder.build_expression(
            layer_props={'layer_name': 'buildings'},
            predicates={'intersects': True},
            source_geom=source_layer
        )
        builder.apply_filter(layer, expr)
    """

    # QGIS predicate codes for selectbylocation
    PREDICATE_CODES = {
        'intersects': 0,
        'contains': 1,
        'disjoint': 2,
        'equals': 3,
        'touches': 4,
        'overlaps': 5,
        'within': 6,
        'crosses': 7,
        # 2026-10-16: were missing, so Covers / CoveredBy fell back to code 0
        # (Intersects). select-by-location has no covers predicate: the
        # closest are Contains / Within, as FilterEngineTask maps them.
        'covers': 1,
        'coveredby': 6,
    }

    def __init__(self, task_params: Dict[str, Any]):
        """
        Initialize OGR expression builder.

        Args:
            task_params: Task configuration parameters
        """
        super().__init__(task_params)
        self._logger = logger
        self.source_geom = None
        self._temp_layers_keep_alive = []
        self._source_layer_keep_alive = []
        self._feedback = None
        self.last_error = None

    def get_backend_name(self) -> str:
        """Get backend name."""
        return "OGR"

    def supports_layer(self, layer: 'QgsVectorLayer') -> bool:
        """
        Check if this backend supports the given layer.

        OGR is the fallback backend - supports everything not handled
        by PostgreSQL or Spatialite.

        Args:
            layer: QGIS vector layer to check

        Returns:
            True for OGR-based layers (Shapefile, GeoJSON, etc.)
        """
        if layer is None:
            return False

        provider = layer.providerType()

        # Don't handle PostgreSQL or Spatialite
        if provider in ('postgres', 'spatialite'):
            return False

        # Handle OGR and memory providers
        return provider in ('ogr', 'memory')

    def build_expression(
        self,
        layer_props: Dict[str, Any],
        predicates: Dict[str, bool],
        source_geom: Optional[Any] = None,
        buffer_value: Optional[float] = None,
        buffer_expression: Optional[str] = None,
        source_filter: Optional[str] = None,
        use_centroids: bool = False,
        **kwargs
    ) -> str:
        """
        Build expression for OGR backend.

        OGR uses QGIS processing, so this returns JSON parameters
        rather than SQL. The actual filtering happens in apply_filter().

        Args:
            layer_props: Layer properties
            predicates: Spatial predicates to apply
            source_geom: Source layer reference
            buffer_value: Buffer distance
            buffer_expression: Dynamic buffer expression
            source_filter: Not used
            use_centroids: Already applied in source preparation
            **kwargs: Additional parameters

        Returns:
            JSON string with processing parameters
        """
        self.log_debug(f"Preparing OGR processing for {layer_props.get('layer_name', 'unknown')}")

        # Log buffer parameters
        self.log_info("📐 OGR buffer parameters:")
        self.log_info(f"  - buffer_value: {buffer_value}")
        self.log_info(f"  - buffer_expression: {buffer_expression}")

        if buffer_value is not None and buffer_value < 0:
            self.log_info(f"  ⚠️ NEGATIVE BUFFER (erosion) requested: {buffer_value}m")

        # Store source geometry for apply_filter
        self.source_geom = source_geom

        # Keep source layer alive
        if source_geom is not None:
            try:
                from qgis.core import QgsVectorLayer
                if isinstance(source_geom, QgsVectorLayer):
                    self._source_layer_keep_alive.append(source_geom)
            except ImportError:
                pass

        # Return JSON parameters
        params = {
            'predicates': list(predicates.keys()),
            'buffer_value': buffer_value,
            'buffer_expression': buffer_expression
        }
        return json.dumps(params)

    def apply_filter(
        self,
        layer: 'QgsVectorLayer',
        expression: str,
        old_subset: Optional[str] = None,
        combine_operator: Optional[str] = None
    ) -> bool:
        """
        Apply filter using QGIS processing selectbylocation algorithm.

        Thread Safety:
        - Uses lock for concurrent access detection
        - Uses data provider directly to avoid layer signals

        Args:
            layer: Layer to filter
            expression: JSON parameters from build_expression
            old_subset: Existing subset (handled via selection)
            combine_operator: Combine operator

        Returns:
            True if filter applied successfully
        """
        global _last_operation_thread

        # Thread safety check
        current_thread = threading.current_thread().ident
        with _ogr_operations_lock:
            if _last_operation_thread is not None and _last_operation_thread != current_thread:
                self.log_warning(
                    "⚠️ OGR apply_filter called from different thread! "
                    f"Previous: {_last_operation_thread}, Current: {current_thread}"
                )
            _last_operation_thread = current_thread

        try:
            from qgis import processing
            from qgis.core import QgsVectorLayer

            # Parse parameters
            params = json.loads(expression) if expression else {}
            predicates = params.get('predicates', ['intersects'])
            buffer_value = params.get('buffer_value')
            buffer_expression = params.get('buffer_expression')

            # Get source layer
            source_layer = self.source_geom

            if source_layer is None:
                self.last_error = "No source layer available for OGR filter"
                self.log_error(self.last_error)
                return False

            if not isinstance(source_layer, QgsVectorLayer):
                self.last_error = f"Source is not a QgsVectorLayer: {type(source_layer)}"
                self.log_error(self.last_error)
                return False

            self.log_info(f"📍 Applying OGR filter to {layer.name()}")
            self.log_info(f"  - Source: {source_layer.name()} ({source_layer.featureCount()} features)")

            # FIX v4.2.11: Apply buffer to source layer if needed (static or dynamic)
            if buffer_expression and buffer_expression.strip():
                self.log_info(f"  - Applying dynamic buffer expression: {buffer_expression[:50]}...")
                source_layer = self._apply_buffer_expression_to_layer(source_layer, buffer_expression)
                if source_layer is None:
                    self.last_error = f"Failed to apply dynamic buffer expression: {buffer_expression[:80]}"
                    self.log_error(self.last_error)
                    return False
                self.log_info(f"  - Buffered source: {source_layer.featureCount()} features")
            elif buffer_value is not None and buffer_value != 0:
                self.log_info(f"  - Applying static buffer: {buffer_value}m")
                source_layer = self._apply_buffer_to_layer(source_layer, buffer_value)
                if source_layer is None:
                    self.last_error = f"Failed to apply static buffer ({buffer_value}m)"
                    self.log_error(self.last_error)
                    return False
                self.log_info(f"  - Buffered source: {source_layer.featureCount()} features")

            # 2026-10-17: test the union of the source, like the SpatiaLite
            # and GeoPackage SQL (one dissolved WKT). select-by-location
            # tests each source feature on its own: "Cross" from the 691
            # Toulouse rivers kept 702 roads instead of ~747 (a road meeting
            # two rivers at a junction crosses the network, not either river)
            # and ran 691 target requests, each paying the target's subset
            # again (98 s for troncon_de_route).
            source_union = self._source_union(source_layer)

            # Map predicates to QGIS codes
            predicate_codes = []
            for pred in predicates:
                pred_lower = pred.lower().replace('st_', '')
                code = self.PREDICATE_CODES.get(pred_lower, 0)
                predicate_codes.append(code)

            # Create feedback for cancellation
            self._feedback = CancellableFeedback()

            if source_union is not None:
                selected_ids = self._select_against_union(layer, source_union, source_layer.crs(), predicate_codes)
                if selected_ids is None:
                    return False
            else:
                # Run selectbylocation
                try:
                    processing.run(
                        'native:selectbylocation',
                        {
                            'INPUT': layer,
                            'INTERSECT': source_layer,
                            'PREDICATE': predicate_codes,
                            'METHOD': 0  # New selection
                        },
                        feedback=self._feedback
                    )
                except Exception as e:
                    self.last_error = f"native:selectbylocation processing failed: {e}"
                    self.log_error(self.last_error)
                    return False

                # Get selected feature IDs
                selected_ids = list(layer.selectedFeatureIds())
            self.log_info(f"  - Selected: {len(selected_ids)} features")

            if len(selected_ids) > PLAIN_KEY_LIST_WARNING and not self._is_sqlite_storage(layer):
                if len(selected_ids) > PLAIN_KEY_LIST_MAX:
                    self.last_error = (
                        f"{layer.name()}: {len(selected_ids):,} features selected, more than {PLAIN_KEY_LIST_MAX:,} "
                        "keys in a subset string for this format (OGR SQL rescans the list for every row, GDAL "
                        "refuses ~8,000). Layer left unfiltered: convert it to GeoPackage to filter it."
                    )
                    self.log_error(self.last_error)
                    return False
                self.log_warning(
                    f"  ⚠️ {len(selected_ids):,} keys in the subset of {layer.name()}: every read of this format "
                    "rescans the list (about 3 s per 1,000 keys on 380,000 rows); GeoPackage avoids it"
                )

            if not selected_ids:
                self.log_warning("No features selected - applying empty filter")
                # 2026-04-29 fix: route through subset queue when wired to
                # ensure setSubsetString runs on the Qt main thread (cf
                # `FilterEngineTask.queue_subset_request` docstring).
                queue_callback = self.task_params.get('_subset_queue_callback') if self.task_params else None
                if queue_callback is not None:
                    queue_callback(layer, "1 = 0")
                else:
                    safe_set_subset_string(layer, "1 = 0")
                return True

            # FIX v4.5.3: For OGR layers with a real PK attribute field, use actual
            # field values instead of QGIS internal FIDs. selectedFeatureIds() returns
            # QGIS-internal IDs which don't match attribute values and the pseudo
            # 'fid' column is unreliable in setSubsetString for many OGR drivers
            # (ESRI Shapefile, PostgreSQL via OGR, etc.).
            pk_field = self._get_primary_key(layer)
            use_pk_values = False

            # Use actual PK values when we have a real attribute field (not pseudo 'fid')
            if pk_field and pk_field.lower() != 'fid':
                use_pk_values = True
                self.log_info(f"  - Real PK field '{pk_field}' detected: fetching actual attribute values")
            else:
                # Even for 'fid', check if it's a real field in the layer
                if pk_field and layer.fields().indexOf(pk_field) >= 0:
                    use_pk_values = True
                    self.log_info(f"  - PK field '{pk_field}' exists as attribute: fetching actual values")

            if use_pk_values and self._pk_is_feature_id(layer, pk_field):
                # PERF 2026-10-17: on a GeoPackage the QGIS feature ids ARE the
                # FID column values (checked on BD TOPO 31: 98,687 / 98,687);
                # fetching them again by id took 4 s (9 s on 1.15 M rows).
                pk_values = list(selected_ids)
            elif use_pk_values:
                # PERF 2026-09-13: one request for all selected rows instead
                # of one getFeature() (one provider query) per selected id.
                pk_values = self._fetch_pk_values(layer, selected_ids, pk_field)
            if use_pk_values:
                if pk_values:
                    self.log_info(f"  - Retrieved {len(pk_values)} actual PK values")
                    fid_filter = self._build_fid_filter_with_values(layer, pk_values, pk_field)
                else:
                    self.log_warning("  - Could not retrieve PK values, falling back to FID-based filter")
                    fid_filter = self._build_fid_filter(layer, selected_ids)
            else:
                # No real PK field: use QGIS internal FIDs with pseudo 'fid' column
                fid_filter = self._build_fid_filter(layer, selected_ids)

            # Clear selection (filter applied via subset)
            layer.removeSelection()

            # Combine with existing filter if needed
            if old_subset and combine_operator:
                if self._is_geometric_filter(old_subset):
                    final_filter = fid_filter
                else:
                    final_filter = f"({old_subset}) {combine_operator} ({fid_filter})"
            else:
                final_filter = fid_filter

            # Apply filter
            self.log_info(f"  - Applying filter: {final_filter[:200]}..." if len(final_filter) > 200 else f"  - Applying filter: {final_filter}")
            # 2026-04-29 fix: route through subset queue when wired so
            # `setSubsetString` runs on the Qt main thread. Same root cause
            # as the spatialite/postgresql cascade no-op (cf
            # `FilterEngineTask.queue_subset_request` docstring).
            queue_callback = self.task_params.get('_subset_queue_callback') if self.task_params else None
            if queue_callback is not None:
                queue_callback(layer, final_filter)
                self.log_info(f"✓ OGR filter queued for main-thread application: {len(selected_ids)} features")
                return True

            success = safe_set_subset_string(layer, final_filter)

            if success:
                self.log_info(f"✓ OGR filter applied: {len(selected_ids)} features")
            else:
                pk_name = self._get_primary_key(layer)
                storage = ""
                try:
                    storage = layer.dataProvider().storageType()
                except Exception:  # nosec B110 - storageType() best-effort, diagnostic field only, defaults to ""
                    pass
                self.last_error = (
                    f"setSubsetString failed for {layer.name()} "
                    f"(pk={pk_name}, fids={len(selected_ids)}, storage={storage})"
                )
                self.log_error(f"✗ Failed to apply FID filter to {layer.name()}")
                self.log_error(f"  - Filter expression: {final_filter[:500]}...")
                self.log_error(f"  - Primary key field: {pk_name}")
                self.log_error(f"  - Number of FIDs: {len(selected_ids)}")
                try:
                    provider = layer.dataProvider()
                    self.log_error(f"  - Provider capabilities: {provider.capabilities()}")
                    self.log_error(f"  - Storage type: {storage}")
                except Exception as diag_e:
                    self.log_error(f"  - Could not get diagnostics: {diag_e}")

            return success

        except Exception as e:
            self.last_error = f"OGR apply_filter exception: {e}"
            self.log_error(self.last_error)
            return False

    def cancel(self):
        """Cancel ongoing operation."""
        if self._feedback:
            self._feedback.cancel()

    def cleanup(self):
        """Clean up temporary layers."""
        self._temp_layers_keep_alive.clear()
        self._source_layer_keep_alive.clear()
        self.source_geom = None

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _build_fid_filter(self, layer, fids: list) -> str:
        """
        Build FID-based filter expression for OGR layers (v4.0.7).

        Improved to handle various primary key types:
        - Numeric IDs: fid IN (1, 2, 3)
        - UUIDs: uuid IN ('abc-123', 'def-456')
        - GeoPackage: "fid" IN (1, 2, 3)
        - Shapefiles: fid IN (1, 2, 3)

        Args:
            layer: QGIS vector layer
            fids: List of feature IDs

        Returns:
            Filter expression string
        """
        if not fids:
            return "1 = 0"

        # Get storage type and primary key
        storage_type = ""
        try:
            storage_type = layer.dataProvider().storageType().lower()
        except Exception:  # nosec B110 - storageType() best-effort, defaults to "" if provider call fails
            pass

        pk_field = self._get_primary_key(layer)
        pk_field_lower = pk_field.lower()

        # Check if PK field is numeric or text (for quoting values)
        is_numeric_pk = True
        try:
            fields = layer.fields()
            pk_idx = fields.indexOf(pk_field)
            if pk_idx >= 0:
                from qgis.PyQt.QtCore import QMetaType
                field_type = fields.at(pk_idx).type()
                is_numeric_pk = field_type in (QMetaType.Type.Int, QMetaType.Type.LongLong, QMetaType.Type.UInt, QMetaType.Type.ULongLong, QMetaType.Type.Double)
        except Exception:  # nosec B110 - field type detection best-effort, defaults to numeric assumption
            pass

        # Build value list based on PK type
        if is_numeric_pk:
            fid_list = ", ".join(str(fid) for fid in fids)
        else:
            # Quote string values (UUID, etc.)
            fid_list = ", ".join(f"'{fid}'" for fid in fids)

        # Shapefile special case: QGIS 3.x requires lowercase 'fid' for setSubsetString
        if 'shapefile' in storage_type or 'esri' in storage_type:
            self.log_info("  - Shapefile detected: using lowercase 'fid' for QGIS subset")
            return f'fid IN ({fid_list})'

        # GeoPackage and SQLite-based formats: use quoted field name
        if 'geopackage' in storage_type or 'gpkg' in storage_type or 'sqlite' in storage_type:
            self.log_info(f"  - GeoPackage/SQLite detected: using quoted '{pk_field}'")
            if len(fids) > KEY_LIST_JSON_THRESHOLD:
                return self._json_key_clause(f'"{pk_field}"', fids, is_numeric_pk)
            return f'"{pk_field}" IN ({fid_list})'

        # For other OGR formats with detected primary key
        if pk_field and pk_field_lower not in ['fid']:
            self.log_info(f"  - Using detected primary key: {pk_field}")
            return f'"{pk_field}" IN ({fid_list})'

        # Default: try lowercase fid (more compatible with QGIS setSubsetString)
        self.log_info(f"  - Unknown format ({storage_type}): using lowercase 'fid' syntax")
        return f'fid IN ({fid_list})'

    def _build_fid_filter_with_values(self, layer, pk_values: list, pk_field: str) -> str:
        """
        Build filter expression using actual PK values (v4.0.8).

        This method is used for PostgreSQL layers accessed via OGR, where we
        need to use actual PK column values instead of QGIS internal FIDs.

        Args:
            layer: QGIS vector layer
            pk_values: List of actual primary key values from the PK column
            pk_field: Name of the primary key field

        Returns:
            Filter expression string like "id" IN (1, 2, 3)
        """
        if not pk_values:
            return "1 = 0"

        # FIX v4.0.9: IMPROVED numeric detection for PostgreSQL via OGR
        # QGIS OGR provider may return incorrect field types for PostgreSQL.
        # Use multiple detection strategies with VALUE-BASED priority.
        is_numeric_pk = None

        # Strategy 1: Check ACTUAL VALUES first (most reliable)
        # If all values are Python int/float, they're numeric
        try:
            all_numeric_values = all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in pk_values[:10]  # Check first 10 values
            )
            if all_numeric_values:
                is_numeric_pk = True
                self.log_info("  - PK type detected from VALUES: numeric (all values are int/float)")
        except Exception as val_e:
            self.log_debug(f"  - Value-based detection failed: {val_e}")

        # Strategy 2: Check if string values look like integers
        if is_numeric_pk is None:
            try:
                sample_values = pk_values[:10]
                all_look_numeric = all(
                    isinstance(v, (int, float)) or
                    (isinstance(v, str) and v.lstrip('-').isdigit())
                    for v in sample_values
                )
                if all_look_numeric:
                    is_numeric_pk = True
                    self.log_info("  - PK type detected from string VALUES: numeric (all values look like integers)")
            except Exception:  # nosec B110 - value-based detection best-effort, falls through to next strategy
                pass

        # Strategy 3: Check field type from layer fields (may be unreliable for OGR)
        if is_numeric_pk is None:
            try:
                fields = layer.fields()
                pk_idx = fields.indexOf(pk_field)
                if pk_idx >= 0:
                    from qgis.PyQt.QtCore import QMetaType
                    field_type = fields.at(pk_idx).type()
                    numeric_types = (QMetaType.Type.Int, QMetaType.Type.LongLong, QMetaType.Type.UInt, QMetaType.Type.ULongLong, QMetaType.Type.Double)
                    is_numeric_pk = field_type in numeric_types
                    self.log_info(f"  - PK type detected from field schema: {'numeric' if is_numeric_pk else 'text'} (QMetaType type={field_type})")
            except Exception as field_e:
                self.log_debug(f"  - Field type detection failed: {field_e}")

        # Default: assume numeric for common PK field names
        if is_numeric_pk is None:
            pk_lower = pk_field.lower()
            common_numeric_names = ('id', 'fid', 'gid', 'pk', 'ogc_fid', 'objectid', 'oid', 'rowid')
            is_numeric_pk = pk_lower in common_numeric_names
            self.log_info(f"  - PK type FALLBACK: {'numeric' if is_numeric_pk else 'text'} (based on field name '{pk_field}')")

        # Build value list based on PK type
        if is_numeric_pk:
            # Numeric: no quotes - convert all values to int if possible
            formatted_values = []
            for v in pk_values:
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    formatted_values.append(str(int(v)))
                elif isinstance(v, str) and v.lstrip('-').isdigit():
                    formatted_values.append(v)  # Already a numeric string
                else:
                    formatted_values.append(str(v))  # Best effort
            value_list = ", ".join(formatted_values)
            self.log_info(f"  - Building NUMERIC IN clause for '{pk_field}': {len(pk_values)} values")
            self.log_debug(f"    Sample: {value_list[:100]}...")
        else:
            # String/UUID: single quotes
            value_list = ", ".join(f"'{v}'" for v in pk_values)
            self.log_info(f"  - Building STRING IN clause for '{pk_field}': {len(pk_values)} values")
            self.log_debug(f"    Sample: {value_list[:100]}...")

        if len(pk_values) > KEY_LIST_JSON_THRESHOLD and self._is_sqlite_storage(layer):
            return self._json_key_clause(f'"{pk_field}"', formatted_values if is_numeric_pk else pk_values, is_numeric_pk)

        # Always use quoted field name for PostgreSQL
        return f'"{pk_field}" IN ({value_list})'

    @staticmethod
    def _pk_is_feature_id(layer, pk_field: str) -> bool:
        """True when ``pk_field`` is the FID column of a GeoPackage (QGIS feature id == its value)."""
        try:
            storage_type = layer.dataProvider().storageType().lower()
            if 'gpkg' not in storage_type and 'geopackage' not in storage_type:
                return False
            pk_indexes = list(layer.dataProvider().pkAttributeIndexes())
            return len(pk_indexes) == 1 and layer.fields().at(pk_indexes[0]).name() == pk_field
        except Exception:
            return False

    @staticmethod
    def _is_sqlite_storage(layer) -> bool:
        """GeoPackage or SQLite layer (subset strings are SQLite SQL)."""
        try:
            storage_type = layer.dataProvider().storageType().lower()
        except Exception:
            return False
        return 'geopackage' in storage_type or 'gpkg' in storage_type or 'sqlite' in storage_type

    def _json_key_clause(self, field_sql: str, values: list, numeric: bool) -> str:
        """``field IN (SELECT value FROM json_each('[...]'))`` (see KEY_LIST_JSON_THRESHOLD)."""
        if numeric:
            payload = "[" + ",".join(str(int(float(v))) for v in values) + "]"
        else:
            payload = json.dumps([str(v) for v in values], ensure_ascii=False, separators=(",", ":"))
        self.log_info(f"  - {len(values):,} keys: one JSON literal ({len(payload):,} chars) instead of an IN list")
        return f"{field_sql} IN (SELECT value FROM json_each('{payload.replace(chr(39), chr(39) * 2)}'))"

    @staticmethod
    def _fetch_pk_values(layer, selected_ids, pk_field) -> list:
        """Primary-key values of ``selected_ids`` fetched in a single request."""
        from qgis.core import QgsFeatureRequest
        pk_values = []
        request = QgsFeatureRequest().setFilterFids(list(selected_ids))
        request.setFlags(QgsFeatureRequest.Flag.NoGeometry)
        try:
            request.setSubsetOfAttributes([pk_field], layer.fields())
        except (AttributeError, TypeError):
            pass
        for feature in layer.getFeatures(request):
            pk_value = feature[pk_field]
            if pk_value is not None:
                pk_values.append(pk_value)
        return pk_values

    def _buffered_source_cache(self) -> dict:
        """Per-task cache of buffered source layers, shared by every target layer.

        PERF 2026-09-13: apply_filter() runs once per target layer and buffered
        the source layer each time - 36 buffers of the same 4 711 road segments
        for a 36-layer cascade. task_params is the dict shared by all the
        backends of one task, so the buffered layer is computed once.
        """
        params = self.task_params if isinstance(self.task_params, dict) else None
        if params is None:
            return {}
        return params.setdefault('_ogr_buffered_source_cache', {})

    def _source_union(self, layer: 'QgsVectorLayer'):
        """Union of the source geometries, or None to test the source features one by one.

        2026-10-17: the filter tests the union of the source on every
        backend (SpatiaLite / GeoPackage inline one dissolved WKT). Computed
        once per task and source layer (task_params cache, like the buffered
        source). None for a single-feature source (same answer, the
        select-by-location path stays) and, with a WARNING, when the union
        fails or mixes geometry types.
        """
        try:
            if layer.featureCount() <= 1:
                return None
        except RuntimeError:
            return None
        from qgis.core import QgsFeatureRequest, QgsGeometry, QgsWkbTypes

        params = self.task_params if isinstance(self.task_params, dict) else {}
        cache = params.setdefault('_ogr_source_union_cache', {})
        if layer.id() in cache:
            return cache[layer.id()]
        geometries = [
            feature.geometry()
            for feature in layer.getFeatures(QgsFeatureRequest().setNoAttributes())
            if feature.hasGeometry() and not feature.geometry().isEmpty()
        ]
        union = QgsGeometry.unaryUnion(geometries) if geometries else None
        if union is None or union.isEmpty():
            union = QgsGeometry.unaryUnion([geometry.makeValid() for geometry in geometries]) if geometries else None
        if (
            union is None or union.isEmpty()
            or QgsWkbTypes.geometryType(union.wkbType()) != QgsWkbTypes.geometryType(layer.wkbType())
        ):
            self.log_warning(
                f"  ⚠️ Union of the source {layer.name()} unavailable: each source feature is tested on its own "
                "(Crosses / Touches / Within may differ from the SQL backends)"
            )
            union = None
        else:
            self.log_info(f"  - Source dissolved: {len(geometries)} features → 1 (union semantics)")
        cache[layer.id()] = union
        return union

    def _select_against_union(self, layer, union, union_crs, predicate_codes) -> Optional[list]:
        """Ids of the ``layer`` features related to ``union`` by any of ``predicate_codes``.

        2026-10-17: same codes and directions as native:selectbylocation
        (INPUT = target, INTERSECT = source): Contains = the target contains
        the source, Within = the target is within the source. One request
        (bounding box of the source, the whole layer for Disjoint) through
        the layer and its subset, a prepared source, and a prepared
        Intersects before the costlier predicates. Measured on 100,000 road
        segments and a 260 KB river network (shapely / GEOS 3.14): 3 s to
        read the candidates through a framed subset, 0.07 s for Intersects,
        0.4 s for Crosses on the hits; select-by-location with the union
        took 4.6 s, one request per river 35 s through the same subset.
        Returns None (last_error set) when cancelled.
        """
        from qgis.core import QgsFeatureRequest, QgsGeometry, QgsProject

        engine = QgsGeometry.createGeometryEngine(union.constGet())
        engine.prepareGeometry()
        codes = set(predicate_codes)
        request = QgsFeatureRequest().setNoAttributes()
        request.setDestinationCrs(union_crs, QgsProject.instance().transformContext())
        if 2 not in codes:  # every predicate but Disjoint needs a shared point
            request.setFilterRect(union.boundingBox())
        tests = {
            1: engine.within,     # target contains source
            3: engine.isEqual,
            4: engine.touches,
            5: engine.overlaps,
            6: engine.contains,   # target within source
            7: engine.crosses,
        }
        selected = []
        for index, feature in enumerate(layer.getFeatures(request)):
            if index % 1000 == 0 and self._feedback is not None and self._feedback.isCanceled():
                self.last_error = "OGR selection cancelled"
                return None
            if not feature.hasGeometry():
                continue
            geometry = feature.geometry().constGet()
            if not engine.intersects(geometry):
                if 2 in codes:
                    selected.append(feature.id())
                continue
            if 0 in codes or any(code in tests and tests[code](geometry) for code in codes):
                selected.append(feature.id())
        return selected

    def _apply_buffer_to_layer(
        self,
        layer: 'QgsVectorLayer',
        buffer_value: float
    ) -> Optional['QgsVectorLayer']:
        """
        Apply static buffer to source layer using QGIS processing.

        FIX v4.2.11: Add support for static buffer via processing.

        Args:
            layer: Source layer to buffer
            buffer_value: Buffer distance in layer units

        Returns:
            Buffered memory layer, or None on failure
        """
        try:
            from qgis import processing

            # 2026-09-13: honour the task's buffer segments / end cap style
            # (they were hard-coded to 8 segments, round) and reuse the
            # buffered layer across the target layers of the task.
            params = self.task_params if isinstance(self.task_params, dict) else {}
            segments = int(params.get('buffer_segments', 5) or 5)
            cap_styles = {'round': 0, 'flat': 1, 'square': 2}
            end_cap = cap_styles.get(str(params.get('buffer_endcap_style', 'round')).lower(), 0)
            cache = self._buffered_source_cache()
            cache_key = (layer.id(), float(buffer_value), segments, end_cap)
            cached = cache.get(cache_key)
            if cached is not None:
                try:
                    if cached.isValid():
                        self.log_info("  - Buffered source reused from the task cache")
                        return cached
                except RuntimeError:
                    pass  # C++ object gone: rebuild below
            result = processing.run(
                'native:buffer',
                {
                    'INPUT': layer,
                    'DISTANCE': buffer_value,
                    'SEGMENTS': segments,
                    'END_CAP_STYLE': end_cap,
                    'JOIN_STYLE': 0,  # Round
                    'MITER_LIMIT': 2,
                    'DISSOLVE': False,
                    'OUTPUT': 'memory:'
                },
                feedback=self._feedback if hasattr(self, '_feedback') else None
            )

            buffered_layer = result.get('OUTPUT')
            if buffered_layer and isinstance(buffered_layer, QgsVectorLayer):
                self._source_layer_keep_alive.append(buffered_layer)
                cache[cache_key] = buffered_layer
                return buffered_layer

            self.log_error("Buffer processing returned no valid layer")
            return None

        except Exception as e:
            self.log_error(f"Failed to apply static buffer: {e}")
            return None

    def _apply_buffer_expression_to_layer(
        self,
        layer: 'QgsVectorLayer',
        buffer_expression: str
    ) -> Optional['QgsVectorLayer']:
        """
        Apply dynamic buffer expression to source layer.

        FIX v4.2.12: Support QGIS expressions for dynamic buffer values.
        Strategy:
        1. Try native:bufferbym if expression is a simple field reference
        2. Fallback to computing average buffer and using static buffer
        3. Last resort: extract numeric default from expression

        Args:
            layer: Source layer to buffer
            buffer_expression: QGIS expression returning buffer distance

        Returns:
            Buffered memory layer, or None on failure
        """
        try:
            from qgis import processing
            import re

            self.log_debug(f"Dynamic buffer expression: {buffer_expression}")

            # Strategy 1: Check if it's a simple field reference - use bufferbym
            field_match = re.match(r'^"?(\w+)"?$', buffer_expression.strip())
            if field_match:
                field_name = field_match.group(1)
                if field_name in [f.name() for f in layer.fields()]:
                    self.log_info(f"  Using native:bufferbym with field '{field_name}'")
                    try:
                        result = processing.run(
                            'native:bufferbym',
                            {
                                'INPUT': layer,
                                'FIELD': field_name,
                                'SEGMENTS': 8,
                                'END_CAP_STYLE': 0,
                                'JOIN_STYLE': 0,
                                'MITER_LIMIT': 2,
                                'OUTPUT': 'memory:'
                            },
                            feedback=self._feedback if hasattr(self, '_feedback') else None
                        )
                        buffered_layer = result.get('OUTPUT')
                        if buffered_layer and isinstance(buffered_layer, QgsVectorLayer):
                            self._source_layer_keep_alive.append(buffered_layer)
                            self.log_info("  ✅ Dynamic buffer (field) applied successfully")
                            return buffered_layer
                    except Exception as e:
                        self.log_warning(f"  bufferbym failed: {e}, trying alternatives")

            # Strategy 2: Compute average buffer value from expression and use static buffer
            self.log_info("  Computing average buffer from expression...")
            avg_buffer = self._compute_average_buffer(layer, buffer_expression)

            if avg_buffer is not None and avg_buffer > 0:
                self.log_info(f"  Using computed average buffer: {avg_buffer:.2f}m")
                return self._apply_buffer_to_layer(layer, avg_buffer)

            # Strategy 3: Fallback to extracting numeric default
            return self._fallback_buffer_from_expression(layer, buffer_expression)

        except Exception as e:
            self.log_error(f"Failed to apply dynamic buffer: {e}")
            return self._fallback_buffer_from_expression(layer, buffer_expression)

    def _compute_average_buffer(
        self,
        layer: 'QgsVectorLayer',
        buffer_expression: str
    ) -> Optional[float]:
        """
        Compute average buffer value by evaluating expression on sample features.

        Args:
            layer: Source layer
            buffer_expression: QGIS expression returning buffer distance

        Returns:
            Average buffer value, or None if cannot compute
        """
        try:
            from qgis.core import (
                QgsExpression, QgsExpressionContext,
                QgsExpressionContextUtils, QgsFeatureRequest
            )

            expr = QgsExpression(buffer_expression)
            if expr.hasParserError():
                self.log_warning(f"  Expression parse error: {expr.parserErrorString()}")
                return None

            # Sample up to 100 features for average
            context = QgsExpressionContext()
            context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))

            buffer_values = []
            request = QgsFeatureRequest().setLimit(100)

            for feature in layer.getFeatures(request):
                context.setFeature(feature)
                result = expr.evaluate(context)
                if result is not None:
                    try:
                        val = float(result)
                        if val > 0:  # Only positive buffers
                            buffer_values.append(val)
                    except (TypeError, ValueError):
                        pass

            if buffer_values:
                avg = sum(buffer_values) / len(buffer_values)
                self.log_debug(f"  Computed average buffer from {len(buffer_values)} features: {avg:.2f}")
                return avg

            return None

        except Exception as e:
            self.log_warning(f"  Could not compute average buffer: {e}")
            return None

    def _fallback_buffer_from_expression(
        self,
        layer: 'QgsVectorLayer',
        buffer_expression: str
    ) -> Optional['QgsVectorLayer']:
        """
        Fallback: extract numeric default from expression and apply static buffer.

        Handles expressions like 'if("field" > 100, 50, 10)' by extracting
        the else value (10) as a safe default.

        Args:
            layer: Source layer
            buffer_expression: Original expression that failed

        Returns:
            Statically buffered layer, or original layer
        """
        import re

        self.log_warning(f"Using fallback for expression: {buffer_expression}")

        # Try to extract a default numeric value
        # Pattern: if(..., ..., DEFAULT) - get the last number
        numbers = re.findall(r'[-+]?\d*\.?\d+', buffer_expression)

        if numbers:
            try:
                # Use the last number as default (else clause)
                default_buffer = float(numbers[-1])
                self.log_info(f"  Fallback buffer value: {default_buffer}")
                return self._apply_buffer_to_layer(layer, default_buffer)
            except ValueError:
                pass

        self.log_warning("Could not extract default buffer, using original layer")
        return layer

    def _get_primary_key(self, layer) -> str:
        """
        Get primary key field name with improved detection (v4.0.7).

        Priority order:
        1. Provider-declared primary key
        2. Exact PK names: id, fid, pk, gid, ogc_fid, objectid, oid, rowid
        3. UUID fields (uuid, guid in name)
        4. Numeric fields with ID patterns (_id, id_, identifier, etc.)
        5. First numeric integer field
        6. Default to "fid"

        Args:
            layer: QGIS vector layer

        Returns:
            Primary key field name
        """
        # Common primary key field names (exact match, case-insensitive)
        PK_EXACT_NAMES = ['id', 'fid', 'pk', 'gid', 'ogc_fid', 'objectid', 'oid', 'rowid']
        # UUID field patterns (contains, case-insensitive)
        UUID_PATTERNS = ['uuid', 'guid']
        # ID field patterns (contains, case-insensitive)
        ID_PATTERNS = ['_id', 'id_', 'identifier', 'feature_id', 'object_id']

        try:
            from qgis.PyQt.QtCore import QMetaType

            fields = layer.fields()
            if not fields:
                return "fid"

            # 1. Try provider-declared primary key
            try:
                pk_indexes = layer.dataProvider().pkAttributeIndexes()
                if pk_indexes:
                    pk_name = fields.at(pk_indexes[0]).name()
                    self.log_debug(f"Using provider PK: {pk_name}")
                    return pk_name
            except Exception:  # nosec B110 - provider PK lookup best-effort, falls through to heuristics below
                pass

            # 2. Look for exact match PK names
            for field in fields:
                if field.name().lower() in PK_EXACT_NAMES:
                    self.log_debug(f"Found exact PK name: {field.name()}")
                    return field.name()

            # 3. Look for UUID fields
            for field in fields:
                field_name_lower = field.name().lower()
                for pattern in UUID_PATTERNS:
                    if pattern in field_name_lower:
                        self.log_debug(f"Found UUID field: {field.name()}")
                        return field.name()

            # 4. Look for numeric fields with ID patterns
            numeric_types = (QMetaType.Type.Int, QMetaType.Type.LongLong, QMetaType.Type.UInt, QMetaType.Type.ULongLong)
            for field in fields:
                field_name_lower = field.name().lower()
                if field.type() in numeric_types:
                    for pattern in ID_PATTERNS:
                        if pattern in field_name_lower:
                            self.log_debug(f"Found numeric ID field: {field.name()}")
                            return field.name()

            # 5. First numeric integer field
            for field in fields:
                if field.type() in numeric_types:
                    self.log_debug(f"Using first numeric field: {field.name()}")
                    return field.name()

        except Exception as e:
            self.log_warning(f"Error detecting primary key: {e}")

        # 6. Default to fid
        return "fid"

    def _is_geometric_filter(self, subset: str) -> bool:
        """Check if subset contains geometric filter patterns."""
        subset_lower = subset.lower()

        # OGR filters are typically FID-based
        geometric_patterns = [
            'intersects',
            'contains',
            'within',
            'st_'
        ]

        return any(p in subset_lower for p in geometric_patterns)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'OGRExpressionBuilder',
    'CancellableFeedback',
]

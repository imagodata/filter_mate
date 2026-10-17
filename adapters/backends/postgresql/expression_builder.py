# -*- coding: utf-8 -*-
"""
PostgreSQL Expression Builder.

v4.1.0: Migrated from before_migration/modules/backends/postgresql_backend.py

This module contains the SQL expression building logic for PostGIS spatial filters.
It implements the GeometricFilterPort interface for PostgreSQL backends.

Architecture:
- PostgreSQLExpressionBuilder: Implements GeometricFilterPort for expression building
- PostgreSQLBackend: Uses the new BackendPort interface (execute())

The ExpressionBuilder is used by LegacyAdapter to maintain backward compatibility
with FilterEngineTask while the codebase transitions to the new architecture.

Author: FilterMate Team
Date: January 2026
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Any

if TYPE_CHECKING:
    from qgis.core import QgsVectorLayer

logger = logging.getLogger('FilterMate.Backend.PostgreSQL.ExpressionBuilder')

# Lon/lat SRIDs recognised when the QGIS CRS database is not available
# (WGS 84, ETRS89, NAD83, RGF93 geographic, ED50, NTF).
_GEOGRAPHIC_SRIDS = frozenset({4326, 4258, 4269, 4171, 4230, 4275})

# Import the port interface
try:
    from ....core.ports.geometric_filter_port import GeometricFilterPort
except ImportError:
    # Fallback for direct import
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

# v4.2.10: Import filter chain optimizer for MV-based optimization
try:
    from .filter_chain_optimizer import (
        FilterChainOptimizer,
        FilterChainContext,
        OptimizationStrategy
    )
    CHAIN_OPTIMIZER_AVAILABLE = True
except ImportError:
    CHAIN_OPTIMIZER_AVAILABLE = False
    logger.debug("Filter chain optimizer not available")


class PostgreSQLExpressionBuilder(GeometricFilterPort):
    """
    PostgreSQL/PostGIS expression builder.

    Generates PostGIS SQL expressions for spatial filtering.
    Implements the legacy GeometricFilterPort interface for backward compatibility.

    Features:
    - Simple WKT mode for small datasets
    - EXISTS subquery mode for large datasets
    - Buffer support with endcap styles
    - Centroid optimization for complex geometries
    - Geographic CRS handling (EPSG:4326 -> 3857 reprojection)
    - Column case normalization
    - Numeric type casting for varchar fields

    Example:
        builder = PostgreSQLExpressionBuilder(task_params)
        expr = builder.build_expression(
            layer_props={'layer_schema': 'public', 'layer_table_name': 'buildings'},
            predicates={'intersects': True},
            source_wkt='POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))',
            source_srid=4326,
            buffer_value=100
        )
    """

    # Strategy thresholds
    SIMPLE_WKT_THRESHOLD = 100  # Use simple WKT for <= 100 source features
    MAX_WKT_LENGTH = 100000     # Max WKT length before switching to EXISTS
    WKT_SIMPLIFY_THRESHOLD = 500000  # Warn about very large geometries

    # Predicate optimization order (most selective first)
    PREDICATE_ORDER = {
        'within': 1,       # Most selective - target fully inside source
        'contains': 2,     # Target fully contains source
        'disjoint': 3,     # Inverse of intersects
        'equals': 4,       # Exact match
        'touches': 5,      # Border contact only
        'crosses': 6,      # Lines crossing
        'overlaps': 7,     # Partial overlap
        'intersects': 8,   # Least selective - any overlap
    }

    # PostGIS predicate mapping
    PREDICATE_FUNCTIONS = {
        'intersects': 'ST_Intersects',
        'contains': 'ST_Contains',
        'within': 'ST_Within',
        'touches': 'ST_Touches',
        'overlaps': 'ST_Overlaps',
        'crosses': 'ST_Crosses',
        'disjoint': 'ST_Disjoint',
        'equals': 'ST_Equals',
        'covers': 'ST_Covers',
        'coveredby': 'ST_CoveredBy',
    }

    def __init__(self, task_params: Dict[str, Any]):
        """
        Initialize PostgreSQL expression builder.

        Args:
            task_params: Task configuration parameters
        """
        super().__init__(task_params)
        self._logger = logger
        self.last_error = None

    def get_backend_name(self) -> str:
        """Get backend name."""
        return "PostgreSQL"

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

    def build_expression(
        self,
        layer_props: Dict[str, Any],
        predicates: Dict[str, bool],
        source_geom: Optional[str] = None,
        buffer_value: Optional[float] = None,
        buffer_expression: Optional[str] = None,
        source_filter: Optional[str] = None,
        use_centroids: bool = False,
        **kwargs
    ) -> str:
        """
        Build PostGIS filter expression.

        Strategy based on source feature count:
        - Tiny (< SIMPLE_WKT_THRESHOLD): Use direct WKT geometry literal
        - Larger: Use EXISTS subquery with source filter

        FIX v4.2.12 (2026-01-21): Detects complex query scenarios (buffer expression + filter chaining)
        and warns user about potential performance impact. Sets 2-minute timeout for protection.

        Args:
            layer_props: Layer properties (schema, table, geometry field, etc.)
            predicates: Spatial predicates to apply (intersects, contains, etc.)
            source_geom: Source geometry expression
            buffer_value: Buffer distance in layer units
            buffer_expression: Dynamic buffer expression
            source_filter: Source layer filter (for EXISTS)
            use_centroids: Use centroid optimization
            **kwargs: source_wkt, source_srid, source_feature_count

        Returns:
            PostGIS SQL expression string
        """
        self.log_debug(f"Building PostgreSQL expression for {layer_props.get('layer_name', 'unknown')}")

        # FIX v4.2.12: Detect complex query scenarios EARLY
        self._detect_and_warn_complex_query(
            buffer_expression=buffer_expression,
            source_filter=source_filter,
            layer_name=layer_props.get('layer_name', 'unknown')
        )

        # Extract kwargs
        source_wkt = kwargs.get('source_wkt')
        source_srid = kwargs.get('source_srid')
        source_feature_count = kwargs.get('source_feature_count')

        # Extract layer properties
        layer = layer_props.get("layer")

        # FIX 2026-01-19: Extract schema/table/geom from layer's URI (most reliable source)
        schema = None
        table = None
        geom_field = None

        if layer:
            try:
                from qgis.core import QgsDataSourceUri
                uri = QgsDataSourceUri(layer.dataProvider().dataSourceUri())
                schema = uri.schema() or "public"
                table = uri.table()
                geom_field = uri.geometryColumn() or "geom"
                self.log_debug(f"Extracted from URI: schema={schema}, table={table}, geom={geom_field}")
            except Exception as e:
                self.log_warning(f"Failed to extract from URI: {e}")

        # Fallback to layer_props if URI extraction failed
        if not schema:
            schema = layer_props.get("layer_schema") or "public"
        if not table:
            table = layer_props.get("layer_table_name") or layer_props.get("layer_name")
        if not geom_field:
            geom_field = self._detect_geometry_column(layer_props)

        # DIAGNOSTIC: Print extracted values

        # FIX 2026-01-19: Build geometry expression with TABLE.GEOM (not schema)
        # For PostgreSQL setSubsetString, the schema is implicit in the layer context
        # Format: "table"."geom" - NOT "schema"."table"."geom"
        geom_expr = f'"{table}"."{geom_field}"'
        raw_geom_expr = geom_expr
        # 2026-10-17: the source is brought to this SRID (None: unknown, kept as is)
        target_srid = self._layer_srid(layer)

        # Apply centroid optimization if enabled
        if use_centroids:
            geom_expr = self._apply_centroid_transform(geom_expr, layer_props)

        # FIX v4.2.7: DO NOT apply buffer_expression to distant layer geometry!
        # The buffer_expression is for the SOURCE layer and is already applied in the MV.
        # When source_geom points to a buffer_expr MV (mv_xxx_buffer_expr_dump), the buffer
        # is already baked into that MV's geometries. Applying it again to the distant layer
        # would double-buffer and also fail because the CASE WHEN fields belong to the source.
        #
        # REMOVED: The buffer_expression should NOT be applied here for distant layers.
        # if buffer_expression:
        #     geom_expr = self._apply_dynamic_buffer(geom_expr, buffer_expression)

        # DIAGNOSTIC 2026-01-19: Log the fully qualified geom_expr

        # Determine strategy
        wkt_length = len(source_wkt) if source_wkt else 0
        use_simple_wkt = (
            source_wkt is not None and
            source_srid is not None and
            source_feature_count is not None and
            source_feature_count <= self.SIMPLE_WKT_THRESHOLD and
            wkt_length <= self.MAX_WKT_LENGTH
        )

        if use_simple_wkt:
            self.log_info(f"📝 Using SIMPLE WKT mode ({source_feature_count} features, {wkt_length} chars)")
        else:
            self.log_info("📝 Using EXISTS subquery mode")

        # FIX v4.2.7: Get original source table name for proper aliasing
        original_source_table = kwargs.get('source_table_name')

        # v4.2.10: Check for filter chain MV optimization
        filter_chain_mv_name = kwargs.get('filter_chain_mv_name')
        if filter_chain_mv_name:
            self.log_info(f"🚀 FILTER CHAIN MV OPTIMIZATION: Using {filter_chain_mv_name}")
            # The MV already contains pre-filtered source features satisfying all spatial constraints
            # Generate a simple EXISTS against the MV instead of multiple chained EXISTS
            return self._build_optimized_mv_expression(
                geom_expr=geom_expr,
                predicates=predicates,
                mv_name=filter_chain_mv_name,
                buffer_value=buffer_value
            )

        # 2026-10-16: EXISTS needs a source table ("schema"."table"."geom").
        # A source that is only a WKT (non-PostgreSQL source layer) used to
        # reach _build_exists_expression(), fail to parse and end as a silent
        # "1 = 0". Inline it when it is small enough whatever the feature
        # count; otherwise return None so the caller hands the layer to the
        # OGR backend (exact).
        if not use_simple_wkt and not self._is_source_table_reference(source_geom):
            if source_wkt is not None and source_srid is not None and wkt_length <= self.MAX_WKT_LENGTH:
                use_simple_wkt = True
                self.log_info(f"📝 No source table for EXISTS: using SIMPLE WKT mode ({wkt_length} chars)")
            else:
                self.log_error(
                    f"No source table for EXISTS and source WKT unusable ({wkt_length:,} chars, "
                    f"limit {self.MAX_WKT_LENGTH:,}) - no PostgreSQL expression, OGR fallback"
                )
                return None

        # Build predicate expressions
        predicate_expressions = []

        # Sort predicates for optimal performance
        sorted_predicates = self._sort_predicates(predicates)

        # FIX v4.2.9: Separate EXISTS clauses from simple filters
        # EXISTS clauses should be ANDed at the TOP LEVEL, not inside the new EXISTS
        exists_clauses_to_combine = []
        simple_source_filter = source_filter

        # FIX v4.3.1 (2026-01-22): Initialize is_filter_chaining as local variable BEFORE any usage
        # This flag will be set to True if EXISTS clauses are extracted from source_filter
        # CRITICAL: Must be initialized here because it's used in:
        #   - Line 362: Passed to _build_exists_expression
        #   - Line 1161: Buffer creation logic
        #   - Line 1213: Fallback inline buffer logic
        # If not initialized, Python lookups will fail or use wrong scope
        is_filter_chaining = False  # Will be set to True if EXISTS extracted

        if source_filter and 'EXISTS' in source_filter.upper():
            # Extract EXISTS clauses to combine at the top level
            try:
                from ....core.filter.expression_combiner import extract_exists_clauses, adapt_exists_for_nested_context
            except ImportError:
                from core.filter.expression_combiner import extract_exists_clauses, adapt_exists_for_nested_context
            extracted = extract_exists_clauses(source_filter)
            if extracted:
                # FIX v4.2.12 (2026-01-21): Adapt EXISTS clauses for distant layer context
                #
                # Problem: EXISTS clauses extracted from source layer (e.g., demand_points) contain
                # references to that source table (e.g., "demand_points"."geom"). When these
                # EXISTS are applied to a distant layer (e.g., ducts), the table reference is invalid
                # because "demand_points" is not in the FROM clause of the distant layer query.
                #
                # Solution: Replace source table references with the distant (target) table name.
                # Example: ST_PointOnSurface("demand_points"."geom") → ST_PointOnSurface("ducts"."geom")
                #
                # The `table` variable contains the distant layer's table name (e.g., "ducts")
                # The `original_source_table` contains the source layer's table name (e.g., "demand_points")

                adapted_exists = []
                search_from = 0
                for clause_info in extracted:
                    clause_sql = clause_info['sql']
                    # 2026-10-17: a disjoint filter is NOT EXISTS (...); the
                    # extraction returns the EXISTS (...) part only, which
                    # chained as is would keep the opposite targets.
                    clause_start = source_filter.find(clause_sql, search_from)
                    negated = clause_start > 0 and re.search(
                        r'\bNOT\s*(?:\(\s*)*$', source_filter[:clause_start], re.IGNORECASE
                    ) is not None
                    if clause_start >= 0:
                        search_from = clause_start + len(clause_sql)

                    # Adapt the EXISTS clause for the distant layer context
                    if original_source_table and table:
                        adapted_sql = adapt_exists_for_nested_context(
                            exists_sql=clause_sql,
                            original_table=original_source_table,
                            new_alias=f'"{table}"',  # Replace with target table reference
                            original_schema=None  # Schema is handled by pattern matching
                        )
                        if adapted_sql != clause_sql:
                            self.log_info(f"🔄 Adapted EXISTS for distant layer: '{original_source_table}' → '{table}'")
                    else:
                        # No adaptation needed or possible
                        adapted_sql = clause_sql
                    adapted_exists.append(f"NOT {adapted_sql}" if negated else adapted_sql)

                exists_clauses_to_combine = adapted_exists
                self.log_info(f"🔗 Filter chaining: Found {len(exists_clauses_to_combine)} EXISTS clause(s) to chain at top level")
                # FIX v4.3.1 (2026-01-22): Set is_filter_chaining = True when EXISTS are extracted
                # This flag is used throughout build_expression() to:
                #   - Pass to _build_exists_expression (line 371)
                #   - Control buffer table creation behavior (line 1161)
                #   - Block inline buffer fallback in filter chaining (line 1213)
                is_filter_chaining = True
                # Don't pass EXISTS to _build_exists_expression (they go at top level)
                simple_source_filter = None

        for predicate_name, predicate_func in sorted_predicates:
            if use_simple_wkt:
                expr = self._build_simple_wkt_expression(
                    geom_expr=geom_expr,
                    predicate_func=predicate_func,
                    source_wkt=source_wkt,
                    source_srid=source_srid,
                    buffer_value=buffer_value,
                    raw_geom_expr=raw_geom_expr,
                    target_srid=target_srid
                )
            else:
                # CRITICAL: Use unqualified geom_expr for EXISTS subquery
                # setSubsetString applies to the main table, so no table prefix needed
                # Format: EXISTS (SELECT 1 FROM source AS __source WHERE ST_Intersects("geom", __source."geom"))
                # FIX v4.3.1: Pass is_filter_chaining flag (True if EXISTS were extracted)
                expr = self._build_exists_expression(
                    geom_expr=geom_expr,  # Unqualified - no table prefix!
                    predicate_func=predicate_func,
                    source_geom=source_geom,
                    source_filter=simple_source_filter,  # FIX: Only simple filters, not EXISTS
                    buffer_value=buffer_value,
                    layer_props=layer_props,
                    original_source_table=original_source_table,
                    buffer_expression=buffer_expression,  # FIX v4.2.11: Pass dynamic buffer expression
                    is_filter_chaining=is_filter_chaining,  # FIX v4.3.1: Use local variable instead of recalculating
                    raw_geom_expr=raw_geom_expr,
                    target_srid=target_srid
                )

            if expr:
                predicate_expressions.append(expr)

        # Combine predicates with OR (any predicate match)
        if not predicate_expressions:
            if not sorted_predicates:
                self.log_warning("No predicates specified")
                return "1 = 0"  # No results
            # 2026-10-16: predicates were asked for but none could be built:
            # an error, not an empty result (the caller falls back to OGR).
            self.log_error("No predicate expression could be built - no PostgreSQL expression")
            return None

        if len(predicate_expressions) == 1:
            final_expr = predicate_expressions[0]
        else:
            final_expr = f"({' OR '.join(predicate_expressions)})"

        # FIX v4.2.9: Combine extracted EXISTS clauses at top level
        # Result: EXISTS(new_source) AND EXISTS(zone_pop) AND EXISTS(other...)
        if exists_clauses_to_combine:
            all_exists = [final_expr] + exists_clauses_to_combine
            final_expr = ' AND '.join(all_exists)
            self.log_info(f"🔗 Filter chaining: Combined {len(all_exists)} EXISTS clauses at top level")
            self.log_debug(f"   Final chained expression preview: {final_expr[:300]}...")

        # DIAGNOSTIC: Log the final expression
        self.log_info(f"✅ PostgreSQL expression built: {final_expr[:200]}...")

        # FIX v4.2.12: Set query timeout if complex query detected
        if hasattr(self, '_is_complex_query') and self._is_complex_query:
            self._set_query_timeout(layer_props.get('layer'))

        return final_expr

    def build_expression_optimized(
        self,
        layer_props: Dict[str, Any],
        predicates: Dict[str, bool],
        spatial_filters: List[Dict[str, Any]],
        source_geom: Optional[str] = None,
        buffer_value: Optional[float] = None,
        buffer_expression: Optional[str] = None,  # v4.3.5: Dynamic buffer support
        connection=None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Build optimized expression using materialized views for filter chaining.

        v4.2.10: Uses MV-based optimization when multiple spatial filters are present.

        Instead of multiple EXISTS clauses:
            EXISTS (SELECT 1 FROM demand_points WHERE ST_Intersects(...))
            AND EXISTS (SELECT 1 FROM zone_pop WHERE ST_Intersects(...))

        Creates a single MV with pre-filtered source features and uses:
            EXISTS (SELECT 1 FROM filter_mate_temp.fm_chain_xxx AS __source
                    WHERE ST_Intersects("distant"."geom", __source."geom"))

        Args:
            layer_props: Layer properties (schema, table, geometry field)
            predicates: Spatial predicates to apply
            spatial_filters: List of spatial filter definitions:
                [
                    {'table': 'zone_pop', 'schema': 'ref', 'predicate': 'ST_Intersects'},
                    {'table': 'demand_points', 'schema': 'ref', 'predicate': 'ST_Intersects', 'buffer': 5.0}
                ]
            source_geom: Source geometry expression
            buffer_value: Buffer distance for source
            buffer_expression: Dynamic buffer expression (v4.3.5)
            connection: PostgreSQL connection (required for MV creation)
            session_id: Session ID for MV naming
            **kwargs: Additional parameters

        Returns:
            Optimized PostGIS SQL expression
        """
        if not CHAIN_OPTIMIZER_AVAILABLE:
            self.log_warning("Filter chain optimizer not available, using standard expression")
            return self.build_expression(
                layer_props=layer_props,
                predicates=predicates,
                source_geom=source_geom,
                buffer_value=buffer_value,
                buffer_expression=buffer_expression,  # v4.3.5
                **kwargs
            )

        if not connection:
            self.log_warning("No connection provided for MV optimization, using standard expression")
            return self.build_expression(
                layer_props=layer_props,
                predicates=predicates,
                source_geom=source_geom,
                buffer_value=buffer_value,
                buffer_expression=buffer_expression,  # v4.3.5
                **kwargs
            )

        if len(spatial_filters) < 2:
            self.log_debug("Less than 2 spatial filters, MV optimization not beneficial")
            return self.build_expression(
                layer_props=layer_props,
                predicates=predicates,
                source_geom=source_geom,
                buffer_value=buffer_value,
                buffer_expression=buffer_expression,  # v4.3.5
                **kwargs
            )

        # Extract distant layer info
        layer = layer_props.get("layer")
        distant_table = layer_props.get("layer_table_name") or layer_props.get("layer_name")
        distant_schema = layer_props.get("layer_schema") or "public"
        distant_geom = self._detect_geometry_column(layer_props)

        if layer:
            try:
                from qgis.core import QgsDataSourceUri
                uri = QgsDataSourceUri(layer.dataProvider().dataSourceUri())
                distant_schema = uri.schema() or distant_schema
                distant_table = uri.table() or distant_table
                distant_geom = uri.geometryColumn() or distant_geom
            except (AttributeError, RuntimeError, KeyError):
                pass  # Use default values if URI parsing fails

        # Extract source layer info from source_geom
        source_info = self._parse_source_table_reference(source_geom) if source_geom else {}
        source_schema = source_info.get('schema', 'public')
        source_table = source_info.get('table', '')
        source_geom_column = source_info.get('geom_field', 'geom')

        if not source_table:
            self.log_warning("Could not determine source table from source_geom, using standard expression")
            return self.build_expression(
                layer_props=layer_props,
                predicates=predicates,
                source_geom=source_geom,
                buffer_value=buffer_value,
                **kwargs
            )

        # Build filter chain context
        context = FilterChainContext(
            source_schema=source_schema,
            source_table=source_table,
            source_geom_column=source_geom_column,
            spatial_filters=spatial_filters,
            buffer_value=buffer_value,
            buffer_expression=buffer_expression,  # v4.3.5
            session_id=session_id
        )

        # Get predicate function
        predicate_func = "ST_Intersects"  # Default
        for pred_name, enabled in predicates.items():
            if enabled and pred_name in self.PREDICATE_FUNCTIONS:
                predicate_func = self.PREDICATE_FUNCTIONS[pred_name]
                break

        # Create optimizer and get optimized expression
        optimizer = FilterChainOptimizer(connection, session_id)

        try:
            result = optimizer.optimize_for_distant_layer(
                context=context,
                distant_table=distant_table,
                distant_schema=distant_schema,
                distant_geom_column=distant_geom,
                predicate=predicate_func
            )

            if result.strategy != OptimizationStrategy.NONE:
                self.log_info(f"🚀 MV optimization applied: {result.strategy.value}")
                self.log_info(f"   MV name: {result.mv_name}")
                self.log_info(f"   Estimated improvement: {result.estimated_improvement:.0%}")
                self.log_debug(f"   Expression: {result.expression[:200]}...")

                # Store cleanup SQL for later
                if hasattr(self, '_mv_cleanup_sql'):
                    self._mv_cleanup_sql.append(result.cleanup_sql)
                else:
                    self._mv_cleanup_sql = [result.cleanup_sql]

                return result.expression
            else:
                self.log_debug("MV optimization not applied, using standard expression")

        except Exception as e:
            self.log_error(f"MV optimization failed: {e}")

        # Fallback to standard expression
        return self.build_expression(
            layer_props=layer_props,
            predicates=predicates,
            source_geom=source_geom,
            buffer_value=buffer_value,
            **kwargs
        )

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
    # Private Helper Methods
    # =========================================================================

    def _detect_geometry_column(self, layer_props: Dict) -> str:
        """Detect geometry column from layer properties."""
        geom_field = layer_props.get("layer_geometry_field", "geom")
        layer = layer_props.get("layer")

        if layer:
            try:
                from qgis.core import QgsDataSourceUri
                provider = layer.dataProvider()
                uri_string = provider.dataSourceUri()
                uri_obj = QgsDataSourceUri(uri_string)
                geom_col = uri_obj.geometryColumn()
                if geom_col:
                    geom_field = geom_col
                    self.log_debug(f"Detected geometry column: '{geom_field}'")
            except Exception as e:
                self.log_warning(f"Error detecting geometry column: {e}")

        return geom_field

    # NOTE v4.0.1: _apply_centroid_transform inherited from GeometricFilterPort

    def _apply_dynamic_buffer(self, geom_expr: str, buffer_expression: str) -> str:
        """Apply dynamic buffer expression."""
        endcap_style = self._get_buffer_endcap_style()
        if endcap_style == 'round':
            return f"ST_Buffer({geom_expr}, {buffer_expression})"
        else:
            return f"ST_Buffer({geom_expr}, {buffer_expression}, 'endcap={endcap_style}')"

    def _sort_predicates(self, predicates: Dict) -> List[Tuple[str, str]]:
        """Sort predicates by selectivity for optimal performance."""
        sorted_items = []

        for key, value in predicates.items():
            # Extract predicate name from value
            if isinstance(value, str):
                predicate_func = value
            else:
                predicate_func = self.PREDICATE_FUNCTIONS.get(key.lower(), 'ST_Intersects')

            predicate_lower = predicate_func.lower().replace('st_', '')
            order = self.PREDICATE_ORDER.get(predicate_lower, 99)
            sorted_items.append((key, predicate_func, order))

        sorted_items.sort(key=lambda x: x[2])
        return [(item[0], item[1]) for item in sorted_items]

    def _detect_and_warn_complex_query(
        self,
        buffer_expression: Optional[str],
        source_filter: Optional[str],
        layer_name: str
    ) -> None:
        """
        Detect complex query scenarios and warn user about performance impact.

        FIX v4.2.12 (2026-01-21): Prevents freeze by warning users when combining:
        - Dynamic buffer expressions (if("field" > X, Y, Z))
        - Filter chaining (multiple EXISTS subqueries)

        Complex queries can cause PostgreSQL to hang due to:
        - Per-feature buffer calculations (CASE WHEN evaluated for each feature)
        - Nested EXISTS subqueries (cartesian product)
        - Missing spatial indexes

        Sets self._is_complex_query flag for timeout enforcement.
        """
        self._is_complex_query = False

        # Check for complex scenario: buffer expression + filter chaining
        has_buffer_expr = buffer_expression is not None and buffer_expression.strip() != ''
        has_chained_filter = source_filter and 'EXISTS' in source_filter.upper()

        if has_buffer_expr and has_chained_filter:
            self._is_complex_query = True
            self.log_warning("🚨 COMPLEX QUERY DETECTED")
            self.log_warning(f"   Layer: {layer_name}")
            self.log_warning(f"   → Dynamic buffer expression: {buffer_expression[:50]}...")
            self.log_warning("   → Filter chaining (multiple EXISTS)")
            self.log_warning("   ⚠️  This may cause slow performance or timeout")

            # Warn user via QGIS message bar
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(
                    f"⚠️ FilterMate: Complex query on '{layer_name}'\n"
                    f"Combining dynamic buffer ({buffer_expression[:30]}...) with filter chaining.\n"
                    "Query may take 10-60 seconds. A 2-minute timeout is set for protection.\n"
                    "Consider using static buffer values for better performance.",
                    "FilterMate",
                    Qgis.MessageLevel.Warning
                )
            except Exception as e:
                self.log_debug(f"Could not display warning in QGIS UI: {e}")

    def _set_query_timeout(self, layer) -> None:
        """
        Set PostgreSQL statement timeout for complex queries.

        FIX v4.2.12 (2026-01-21): Protection against infinite queries.
        Sets timeout to 120 seconds (2 minutes) for complex buffer+chaining scenarios.

        Args:
            layer: QGIS layer with PostgreSQL provider
        """
        if not layer:
            return

        try:
            # Get PostgreSQL connection from layer
            from ....infrastructure.utils import get_datasource_connexion_from_layer
            connexion, _ = get_datasource_connexion_from_layer(layer)

            if not connexion:
                self.log_warning("No PostgreSQL connection available for timeout")
                return

            # Set statement timeout (120 seconds = 2 minutes)
            timeout_ms = 120000  # 120 seconds in milliseconds

            with connexion.cursor() as cursor:
                cursor.execute(f"SET statement_timeout = {timeout_ms}")

            self.log_info(f"✅ Query timeout set: {timeout_ms / 1000:.0f} seconds")
            self.log_info("   → Protection against infinite queries enabled")

        except Exception as e:
            self.log_warning(f"Could not set query timeout: {e}")
            # Non-critical - continue anyway

    @staticmethod
    def _quote_ident(name) -> str:
        """``name`` as a quoted PostgreSQL identifier (embedded double quotes doubled)."""
        return '"' + str(name).replace('"', '""') + '"'

    # =========================================================================
    # SRIDs (2026-10-17): the source is brought to the SRID of the target.
    # A GeoJSON source in EPSG:4326 against a BD TOPO table in EPSG:2154 gave
    # "Operation on mixed SRID geometries", and a 100 m buffer around a source
    # in degrees was 100 degrees.
    # =========================================================================

    @staticmethod
    def _positive_srid(value) -> Optional[int]:
        """``value`` when it is a usable SRID (a positive int), else None."""
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return None
        return value

    @classmethod
    def _authid_to_srid(cls, authid) -> Optional[int]:
        """PostGIS SRID of a CRS authid (``EPSG:2154`` → 2154), None when unknown."""
        if not authid or not isinstance(authid, str):
            return None
        try:
            from qgis.core import QgsCoordinateReferenceSystem
            srid = cls._positive_srid(QgsCoordinateReferenceSystem(authid).postgisSrid())
            if srid:
                return srid
        except Exception:  # nosec B110 - no QGIS CRS database: parse the EPSG code below
            pass
        match = re.fullmatch(r'\s*EPSG:(\d+)\s*', authid, re.IGNORECASE)
        return cls._positive_srid(int(match.group(1))) if match else None

    @classmethod
    def _layer_srid(cls, layer) -> Optional[int]:
        """SRID of the geometry column of a PostgreSQL layer, None when unknown.

        The provider CRS is the column SRID; the layer CRS can be overridden
        in QGIS.
        """
        if layer is None:
            return None
        for crs_of in (lambda: layer.dataProvider().crs(), layer.crs):
            try:
                srid = cls._positive_srid(crs_of().postgisSrid())
            except Exception:  # nosec B112 - try the next CRS source
                continue
            if srid:
                return srid
        return None

    def _source_table_srid(self) -> Optional[int]:
        """SRID of the source table (the source layer's own CRS, before any metric reprojection)."""
        infos = (self.task_params or {}).get('infos') or {}
        return self._authid_to_srid(infos.get('layer_crs_authid'))

    @staticmethod
    def _srid_is_geographic(srid: Optional[int]) -> bool:
        """Whether ``srid`` is a lon/lat CRS (degrees)."""
        if not srid:
            return False
        try:
            from qgis.core import QgsCoordinateReferenceSystem
            crs = QgsCoordinateReferenceSystem(f"EPSG:{int(srid)}")
            if crs.isValid() is True:
                return crs.isGeographic() is True
        except Exception:  # nosec B110 - no QGIS CRS database: known lon/lat SRIDs below
            pass
        return int(srid) in _GEOGRAPHIC_SRIDS

    @staticmethod
    def _transform_sql(expr: str, source_srid: Optional[int], target_srid: Optional[int]) -> str:
        """``ST_Transform(expr, target)`` when both SRIDs are known and differ."""
        if source_srid and target_srid and source_srid != target_srid:
            return f"ST_Transform({expr}, {target_srid})"
        return expr

    def _source_in_target_srid(
        self,
        source_expr: str,
        source_srid: Optional[int],
        target_srid: Optional[int],
        buffer_value: Optional[float],
    ) -> Tuple[str, Optional[float]]:
        """The source geometry in the target SRID, and the buffer still to apply there.

        The buffer distance is in metres:
        - same SRID, metric: nothing changes (the buffer is applied by the
          predicate, ST_DWithin for intersects);
        - metric target: the source is transformed, the buffer applies in
          the target metres (the GiST index of the target stays usable);
        - geographic target: the buffer is applied before the transform, on
          the geography for a geographic source, in the source metres else.

        Returns ``(expression, remaining_buffer)``; ``remaining_buffer`` is
        None when there is no buffer left to apply.
        """
        has_buffer = buffer_value is not None and buffer_value != 0
        source_geographic = self._srid_is_geographic(source_srid)
        reproject = bool(source_srid and target_srid and source_srid != target_srid)
        if not reproject and not (has_buffer and source_geographic):
            return source_expr, (buffer_value if has_buffer else None)
        target_geographic = self._srid_is_geographic(target_srid or source_srid)
        if has_buffer and target_geographic:
            if source_geographic:
                buffered = self._build_geography_buffer(source_expr, buffer_value)
            else:
                buffered = self._build_st_buffer_with_style(source_expr, buffer_value)
            return self._transform_sql(buffered, source_srid, target_srid), None
        return (
            self._transform_sql(source_expr, source_srid, target_srid),
            buffer_value if has_buffer else None,
        )

    def _buffer_table_name(
        self,
        source_schema: str,
        source_table: str,
        buffer_expression: str,
        source_filter: Optional[str],
    ) -> str:
        """Name of the pre-computed buffer table of a dynamic buffer.

        2026-10-17: it was ``fm_temp_buf_<table>_<md5(expression)[:8]>`` and an
        existing table was reused, so a second filter on another selection
        (or by another user, or after an edit of the source) got the buffers
        of the first one. The name is now
        ``fm_temp_buf_<session>_<md5(task, schema, table, expression, filter)>``:

        - the selection (source filter), schema, table and expression decide
          what the table holds;
        - the task token makes the reuse of v4.2.19 (the distant layers of
          one task share the table) stop at the end of the task, while the
          tables of earlier tasks stay in place for the layers that still
          reference them;
        - the session prefix lets the session cleanup find the table in
          whatever schema it was created (the source schema).

        At most 12 + 12 + 1 + 20 = 45 characters: the 63-character identifier
        limit is never reached, also with the ``idx_..._geom`` index name.
        """
        from ....infrastructure.constants import TABLE_PREFIX_BUFFER
        params = self.task_params if self.task_params is not None else {}
        # The token lives in the "task" section: the app rebuilds it for each
        # task, while the top-level dict is the layer's PROJECT_LAYERS entry,
        # which outlives the task.
        holder = params.get('task') if isinstance(params.get('task'), dict) else params
        task_token = holder.get('_fm_buffer_table_task_token')
        if not task_token:
            task_token = uuid.uuid4().hex
            holder['_fm_buffer_table_task_token'] = task_token
        session = self._session_token()
        digest = hashlib.md5(
            "\x1f".join([
                task_token, str(source_schema), str(source_table),
                buffer_expression or "", source_filter or "",
            ]).encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()[:20]
        return f"{TABLE_PREFIX_BUFFER}{session}_{digest}"

    def _session_token(self) -> str:
        """The session id reduced to ``[0-9a-z]{1,12}`` (``nosession`` without one)."""
        params = self.task_params or {}
        task_section = params.get('task') if isinstance(params.get('task'), dict) else {}
        session_id = params.get('session_id') or task_section.get('session_id') or ''
        from .cleanup import session_token
        return session_token(session_id)

    def _build_exists_with_buffer_table(
        self,
        geom_expr: str,
        predicate_func: str,
        source_schema: str,
        source_table: str,
        source_geom_field: str,
        buffer_expression: Optional[str],
        source_filter: Optional[str],
        layer_props: Dict,
        buffer_table_name: Optional[str] = None,  # FIX v4.2.20: Pre-calculated table name
        target_srid: Optional[int] = None
    ) -> str:
        """
        Build EXISTS expression using pre-calculated buffer temporary table.

        FIX v4.2.13 (2026-01-21): Performance optimization for complex queries.
        Instead of calculating ST_Buffer(CASE WHEN...) for EVERY feature in EVERY distant layer,
        we pre-calculate buffers ONCE and store in a temporary table with spatial index.

        Performance improvement:
        - Before: O(N×M) - N source features × M distant features × buffer calculation
        - After: O(N + M) - N buffer calculations + M indexed lookups

        Example: 1000 source × 50000 distant × 6 layers = 300M buffer calculations
                 vs 1000 calculations + 300k indexed lookups

        Args:
            geom_expr: Target geometry expression
            predicate_func: PostGIS predicate (ST_Intersects, etc.)
            source_schema: Source schema name
            source_table: Source table name
            source_geom_field: Source geometry field name
            buffer_expression: Dynamic buffer expression (QGIS syntax)
            source_filter: Source filter with EXISTS clauses
            layer_props: Layer properties for connection

        Returns:
            EXISTS expression using temp buffer table
        """
        import time
        from .filter_executor import qgis_expression_to_postgis
        from ....infrastructure.utils import get_datasource_connexion_from_layer

        start_time = time.time()

        layer = layer_props.get('layer')
        if not layer:
            self.log_warning("No layer available for buffer table creation")
            return None

        # Get PostgreSQL connection
        connexion, _ = get_datasource_connexion_from_layer(layer)
        if not connexion:
            self.log_warning("No PostgreSQL connection for buffer table")
            return None

        # FIX v4.2.20 (2026-01-21): Use pre-calculated table name if provided (filter chaining)
        # When filter chaining, the table name was calculated BEFORE buffer_expression was cleared
        # This allows intermediate layers to reference the ORIGINAL buffer table
        if buffer_table_name:
            temp_table_name = buffer_table_name
            self.log_debug(f"Using provided buffer table name: {temp_table_name}")
        elif buffer_expression:
            # 2026-10-17: named after the selection, the session and the task
            # (see _buffer_table_name), no longer after the expression alone.
            temp_table_name = self._buffer_table_name(source_schema, source_table, buffer_expression, source_filter)
        else:
            self.log_error("No buffer_table_name or buffer_expression provided")
            return None

        # FIX v4.2.18 (2026-01-21): Use same schema as source table for QGIS visibility
        # Problem with v4.2.16: filtermate_temp schema not visible to QGIS's connection
        # QGIS rejects queries referencing unknown schemas BEFORE sending to PostgreSQL
        # Solution: Create buffer table in SAME schema as source table
        # This ensures QGIS's connection can see the table (schema is already known)
        temp_schema = source_schema  # Use source schema (e.g., "ref") instead of filtermate_temp

        # Convert QGIS buffer expression to PostGIS SQL
        buffer_expr_sql = qgis_expression_to_postgis(buffer_expression)

        # FIX v4.2.21 (2026-01-21): DO NOT prefix field references in CREATE TABLE context
        # In "SELECT ... FROM table", field references should be unqualified
        # Previous regex was incorrectly adding table prefix, causing "table.field does not exist"
        # The fields are already implicitly scoped to the source table in the FROM clause
        # buffer_expr_sql is used as-is (e.g., "homecount" stays as "homecount")

        # FIX v4.2.18: Schema already exists (it's the source table's schema)
        # No need to create schema - we're using the same schema as the source table
        self.log_debug(f"Using existing schema {temp_schema} (source table schema)")

        q_temp_table = f"{self._quote_ident(temp_schema)}.{self._quote_ident(temp_table_name)}"
        # 2026-10-17: the buffers are in the source SRID
        buffered_in_target = self._transform_sql("__buffer.buffered_geom", self._source_table_srid(), target_srid)
        q_source_table = f"{self._quote_ident(source_schema)}.{self._quote_ident(source_table)}"

        # FIX v4.2.19: Check if table already exists (for filter chaining)
        # 2026-10-17: the name carries the task token (_buffer_table_name), so
        # an existing table was built by this very task for this selection.
        try:
            with connexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = %s
                        AND table_name = %s
                    )
                    """,
                    (temp_schema, temp_table_name),
                )
                table_exists = cursor.fetchone()[0]
                if table_exists:
                    self.log_info(f"♻️ Reusing existing buffer table: {temp_schema}.{temp_table_name}")
                    # FIX v4.2.20: Build EXISTS expression using existing table
                    exists_expr = self._predicate_against_sources(
                        predicate_func, geom_expr, buffered_in_target,
                        f"{q_temp_table} AS __buffer", [], None, None,
                    )
                    self.log_debug(f"Reuse buffer table expression: {exists_expr}")
                    return exists_expr
        except Exception as e:
            self.log_warning(f"Could not check table existence: {e}")

        # FIX v4.2.20: If buffer_expression is None (filter chaining), table should already exist
        if not buffer_expression:
            self.log_error(f"Buffer table {temp_schema}.{temp_table_name} does not exist but buffer_expression is None!")
            self.log_error("This should not happen - table should have been created for original source layer")
            return None

        # FIX v4.3.11 (2026-01-25): Get actual primary key from PostgreSQL (not hardcoded "id")
        # Problem: Using "id" as source_id fails when table has different PK name (e.g., "cleabs", "fid", etc.)
        # Solution: Query PostgreSQL's information_schema to get the actual primary key column name
        primary_key_column = None
        try:
            with connexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = %s::regclass
                    AND i.indisprimary
                    LIMIT 1
                    """,
                    (q_source_table,),
                )
                result = cursor.fetchone()
                if result:
                    primary_key_column = result[0]
                    self.log_debug(f"Found primary key: {primary_key_column}")
        except Exception as pk_err:
            self.log_warning(f"Could not determine primary key: {pk_err}")

        # Fallback: try common primary key names if query failed
        if not primary_key_column:
            self.log_warning("Could not detect PK from PostgreSQL, trying common fallbacks")
            try:
                with connexion.cursor() as cursor:
                    # Check for common PK column names (using parameterized query)
                    for candidate in ['id', 'fid', 'ogc_fid', 'cleabs', 'gid', 'objectid']:
                        cursor.execute("""
                            SELECT column_name FROM information_schema.columns
                            WHERE table_schema = %s
                            AND table_name = %s
                            AND column_name = %s
                        """, (source_schema, source_table, candidate))
                        if cursor.fetchone():
                            primary_key_column = candidate
                            self.log_debug(f"Using fallback PK column: {primary_key_column}")
                            break
            except Exception as fallback_err:
                self.log_warning(f"PK fallback detection failed: {fallback_err}")

        # If still no PK, skip source_id column entirely (buffer table still works for filtering)
        pk_select = f'{self._quote_ident(primary_key_column)} as source_id,' if primary_key_column else ''
        if not primary_key_column:
            self.log_warning("No primary key found - creating buffer table without source_id column")

        # Build CREATE TABLE statement (NOT TEMP - must be visible to QGIS connection)
        # FIX v4.2.18: Table name must be unique to avoid conflicts
        # Note: Table will be cleaned up by FilterMate's cleanup mechanism (same as MVs)
        # FIX v4.3.1 (2026-01-22): Remove table prefix from fields in CREATE TABLE AS SELECT
        # In single-table SELECT, field references should be unqualified (implicit scope)
        # buffer_expr_sql already contains unqualified field names (e.g., "homecount", not "table"."homecount")
        # DDL: identifiers come from QGIS layer metadata (trusted), can't be parameterized
        # 2026-10-17: a lon/lat source is buffered in metres on the geography
        # (the distances of the expression are metres, not degrees)
        source_geom_sql = self._quote_ident(source_geom_field)
        if self._srid_is_geographic(self._source_table_srid()):
            buffered_sql = f"ST_Buffer(({source_geom_sql})::geography, {buffer_expr_sql}, 'quad_segs=5')::geometry"
        else:
            buffered_sql = f"ST_Buffer({source_geom_sql}, {buffer_expr_sql}, 'quad_segs=5')"
        sql_create = f"""
            CREATE TABLE IF NOT EXISTS {q_temp_table} AS
            SELECT
                {pk_select}
                {buffered_sql} as buffered_geom
            FROM {q_source_table}
            {f"WHERE {source_filter}" if source_filter else ""}
        """  # nosec B608

        # Create spatial index
        sql_index = f'CREATE INDEX IF NOT EXISTS "idx_{temp_table_name}_geom" ON {q_temp_table} USING GIST (buffered_geom)'  # nosec B608

        # Analyze for query planner
        sql_analyze = f'ANALYZE {q_temp_table}'

        try:
            with connexion.cursor() as cursor:
                self.log_info(f"📦 Creating buffer table: {temp_schema}.{temp_table_name}")
                self.log_debug(f"SQL: {sql_create[:500]}...")  # nosec B608
                cursor.execute(sql_create)
                self.log_debug("✓ Buffer table created")

                cursor.execute(sql_index)
                self.log_debug("✓ Spatial index created")

                cursor.execute(sql_analyze)
                self.log_debug("✓ Statistics updated")

                # Get row count for logging
                cursor.execute(f'SELECT COUNT(*) FROM {q_temp_table}')  # nosec B608
                row_count = cursor.fetchone()[0]

            # FIX v4.3.6 (2026-01-22): COMMIT the transaction!
            # Without commit, the CREATE TABLE is rolled back when the connection
            # is reused for subsequent operations. This caused "relation does not exist"
            # errors when filter chaining with dynamic buffer expressions.
            connexion.commit()
            self.log_debug("✓ Transaction committed")

            elapsed = time.time() - start_time
            self.log_info(f"✅ Buffer table created: {row_count} features in {elapsed:.2f}s")  # nosec B608
            self.log_info("   → Buffers pre-calculated, will be reused across all distant layers")

            # Build EXISTS using buffer table (with schema prefix for QGIS visibility)
            exists_expr = self._predicate_against_sources(
                predicate_func, geom_expr, buffered_in_target,
                f"{q_temp_table} AS __buffer", [], None, None,
            )

            return exists_expr

        except Exception as e:
            # FIX v4.3.6 (2026-01-22): Enhanced error logging and explicit rollback
            self.log_error(f"Failed to create buffer table: {e}")  # nosec B608
            self.log_error(f"   SQL that failed: {sql_create[:300]}...")  # nosec B608
            self.log_error(f"   buffer_expression: {buffer_expression}")
            self.log_error(f"   source_filter: {source_filter[:200] if source_filter else 'None'}...")

            # Rollback to clean up any partial transaction
            try:
                connexion.rollback()
                self.log_debug("Transaction rolled back")
            except Exception as rollback_err:
                self.log_warning(f"Rollback failed: {rollback_err}")

            self.log_warning("Falling back to inline buffer expression")
            # Return None to trigger fallback in caller
            return None

    def _build_optimized_mv_expression(
        self,
        geom_expr: str,
        predicates: Dict,
        mv_name: str,
        buffer_value: Optional[float] = None
    ) -> str:
        """
        Build optimized expression using filter chain materialized view.

        v4.2.10: Instead of multiple chained EXISTS clauses like:
            EXISTS(source + zone_pop) AND EXISTS(source + demand_points)

        We generate a single EXISTS against the pre-computed MV:
            EXISTS (SELECT 1 FROM filter_mate_temp.fm_temp_chain_xxx AS __chain
                    WHERE ST_Intersects("distant"."geom", __chain."geom"))

        Performance: O(N×M) → O(1) EXISTS per distant layer

        Args:
            geom_expr: Target geometry expression (e.g., '"table"."geom"')
            predicates: Spatial predicates to apply (intersects, contains, etc.)
            mv_name: Fully qualified MV name (e.g., "filter_mate_temp"."fm_temp_chain_xxx")
            buffer_value: Optional buffer distance (already baked into MV typically)

        Returns:
            Optimized EXISTS expression against MV
        """
        self.log_info("🚀 Building OPTIMIZED MV expression")
        self.log_info(f"   MV: {mv_name}")
        self.log_info(f"   Target geom: {geom_expr}")

        # Get primary predicate (usually intersects)
        sorted_predicates = self._sort_predicates(predicates)
        if sorted_predicates:
            predicate_func = sorted_predicates[0][1]
        else:
            predicate_func = "ST_Intersects"

        # Build EXISTS against the MV
        # The MV contains pre-filtered source features that satisfy all spatial constraints
        # Each distant layer only needs ONE EXISTS query against this MV

        # Build the optimized EXISTS
        # Format: EXISTS (SELECT 1 FROM mv AS __chain WHERE ST_Intersects(target, __chain.geom))
        # 2026-10-17: same union semantics as the other paths (disjoint →
        # NOT EXISTS, non-distributive predicates against the union); the
        # buffer, if any (usually already baked into the MV), applies there.
        exists_expr = self._predicate_against_sources(
            predicate_func, geom_expr, '__chain."geom"', f"{mv_name} AS __chain", [],
            buffer_value, None,
        )

        self.log_info(f"✅ Optimized MV expression: {exists_expr[:150]}...")
        return exists_expr

    def _build_simple_wkt_expression(
        self,
        geom_expr: str,
        predicate_func: str,
        source_wkt: str,
        source_srid: int,
        buffer_value: Optional[float] = None,
        raw_geom_expr: Optional[str] = None,
        target_srid: Optional[int] = None
    ) -> str:
        """
        Build simple PostGIS expression using direct WKT.

        Args:
            geom_expr: Target geometry expression
            predicate_func: PostGIS predicate (ST_Intersects, etc.)
            source_wkt: Source geometry WKT
            source_srid: Source SRID
            buffer_value: Optional buffer distance
            raw_geom_expr: Raw target column (centroid bbox test)
            target_srid: SRID of the target geometry column (None: unknown)

        Returns:
            PostGIS SQL expression
        """
        # Build source geometry with ST_MakeValid
        source_geom_sql = f"ST_MakeValid(ST_GeomFromText('{source_wkt}', {source_srid}))"

        # 2026-10-17: in the SRID of the target, the buffer in metres
        # (see _source_in_target_srid).
        source_geom_sql, remaining_buffer = self._source_in_target_srid(
            source_geom_sql, self._positive_srid(source_srid), target_srid, buffer_value
        )
        if remaining_buffer is not None:
            # 2026-09-13: ST_DWithin for intersects + positive round buffer
            return self._buffered_predicate(
                predicate_func, geom_expr, source_geom_sql, remaining_buffer, raw_geom_expr
            )

        return self._index_aware_predicate(predicate_func, geom_expr, source_geom_sql, raw_geom_expr)

    @staticmethod
    def _source_selection_mv_ref(source_filter: Optional[str]) -> Optional[tuple]:
        """``(schema, name)`` of the source-selection MV referenced by ``source_filter``, or None.

        Matches the filter built by the core ExpressionBuilder:
        ``"table"."pk" IN (SELECT pk FROM "filter_mate_temp"."fm_temp_mv_...")``.
        """
        if not source_filter:
            return None
        match = re.fullmatch(
            r'\s*"?[^"]*"?\.?"?[^"]*"?\s+IN\s*\(\s*SELECT\s+pk\s+FROM\s+"([^"]+)"\."([^"]+)"\s*\)\s*',
            source_filter,
            re.IGNORECASE,
        )
        if not match:
            return None
        return match.group(1), match.group(2)

    @staticmethod
    def _source_envelope_prefilter(
        target_geom: str,
        geom_expr: str,
        predicate_func: str,
        source_schema: str,
        source_table: str,
        source_expr: str,
        aliased_source_filter: Optional[str],
        buffer_value: Optional[float],
    ) -> Optional[str]:
        """``target && <envelope of the selected source rows>``, or None.

        PERF 2026-09-13: with ``EXISTS (SELECT 1 FROM source AS __source WHERE
        ST_DWithin(target, __source.geom, d) AND __source.fid IN (...))``
        PostgreSQL scanned every row of the target and ran the subquery per
        row: 322 s on zone_de_vegetation, 35 s on batiment for 300 road
        segments. The envelope of the selected source rows (grown by the
        buffer) is computed once by an uncorrelated scalar subquery, and the
        ``&&`` test against it drives the GiST index of the target before the
        EXISTS runs - the PostgreSQL counterpart of the GeoPackage R-tree
        prefilter. It never changes the result for the predicates that imply
        a bbox overlap; skipped for ST_Disjoint, for a reprojected target
        geometry, and when the whole source table is the selection.
        """
        if not aliased_source_filter or not aliased_source_filter.strip():
            return None
        if predicate_func.upper() == 'ST_DISJOINT' or 'ST_TRANSFORM(' in geom_expr.upper():
            return None
        margin = float(buffer_value) if buffer_value else 0.0
        if margin < 0:
            margin = 0.0
        # 2026-10-17: source_expr is the row geometry in the target SRID
        # (ST_Transform(...) when the SRIDs differ), buffer_value the buffer
        # left to apply in that SRID.
        source_col = source_expr
        envelope = (
            f'SELECT ST_SetSRID(ST_Expand(ST_Extent({source_col})::geometry, {margin}), '
            f'MAX(ST_SRID({source_col}))) '
            f'FROM "{source_schema}"."{source_table}" AS __source '  # nosec B608
            f'WHERE ({aliased_source_filter})'
        )
        # 2026-10-17: a target containing / covering / equal to the union
        # (not eroded) holds its bbox: "~" lets PostgreSQL skip the union,
        # computed once per query, when no target can hold it.
        holds_union = predicate_func.upper() in ('ST_CONTAINS', 'ST_COVERS', 'ST_EQUALS') and not (
            buffer_value is not None and float(buffer_value) < 0
        )
        return f'{target_geom} {"~" if holds_union else "&&"} ({envelope})'

    def _buffered_predicate(
        self,
        predicate_func: str,
        geom_expr: str,
        source_expr: str,
        buffer_value: float,
        raw_geom_expr: Optional[str] = None
    ) -> str:
        """Predicate between the target geometry and a buffered source geometry.

        2026-09-13: ``ST_Intersects(target, ST_Buffer(source, d))`` makes
        PostgreSQL compute a buffer per (source, target) pair whenever it
        drives the join from the target side - a 20 m buffer around 1 661 road
        segments never finished on the first of 17 target layers. For the
        intersects predicate and a positive round buffer the exact equivalent
        is ``ST_DWithin(target, source, d)``: no buffer geometry at all, and
        its support function lets the GiST index of either side serve the
        join. Other predicates, negative buffers and flat/square caps keep the
        explicit ``ST_Buffer()``.
        """
        use_dwithin = (
            predicate_func.upper() == 'ST_INTERSECTS'
            and buffer_value is not None and float(buffer_value) > 0
            and str(self._get_buffer_endcap_style()).lower() == 'round'
        )
        if not use_dwithin:
            buffered = self._build_st_buffer_with_style(source_expr, buffer_value)
            return self._index_aware_predicate(predicate_func, geom_expr, buffered, raw_geom_expr)
        predicate = f"ST_DWithin({geom_expr}, {source_expr}, {buffer_value})"
        if not raw_geom_expr or raw_geom_expr == geom_expr or 'ST_TRANSFORM(' in geom_expr.upper():
            return predicate
        # Centroid optimisation: the predicate runs on ST_PointOnSurface(geom),
        # which no index covers; the bbox test on the raw column brings the
        # GiST index back (the point lies inside the feature's own bbox).
        return f"({raw_geom_expr} && ST_Expand({source_expr}, {buffer_value}) AND {predicate})"

    @staticmethod
    def _index_aware_predicate(
        predicate_func: str,
        geom_expr: str,
        source_expr: str,
        raw_geom_expr: Optional[str] = None
    ) -> str:
        """``predicate(geom, source)``, preceded by a bbox test when needed.

        PERF 2026-09-12: with the centroid optimisation the predicate is
        evaluated on ``ST_PointOnSurface("table"."geom")``, an expression
        PostgreSQL cannot look up in the GiST index of ``geom``: every row of
        the target was scanned (16 s on the 1.2 M-row batiment table for five
        communes). ``"table"."geom" && source`` in front of the predicate
        brings the index back; it never changes the result because a feature's
        point-on-surface (or centroid) lies inside the feature's own bounding
        box. Skipped for ST_Disjoint, for a reprojected target geometry (bbox
        in another CRS) and when the predicate already uses the raw column.
        """
        predicate = f"{predicate_func}({geom_expr}, {source_expr})"
        if not raw_geom_expr or raw_geom_expr == geom_expr:
            return predicate
        if predicate_func.upper() == 'ST_DISJOINT' or 'ST_TRANSFORM(' in geom_expr.upper():
            return predicate
        return f"({raw_geom_expr} && {source_expr} AND {predicate})"

    # Predicates whose truth against the union only depends on the source
    # rows near the target (see _predicate_against_sources).
    _LOCAL_UNION_PREDICATES = frozenset({'ST_WITHIN', 'ST_COVEREDBY', 'ST_TOUCHES'})
    # Upper bound of the degrees per metre ratio below 85° of latitude (one
    # degree of longitude is ~9.7 km there): a reach in metres as degrees.
    _METRES_PER_DEGREE_MIN = 9000.0

    def _predicate_against_sources(
        self,
        predicate_func: str,
        geom_expr: str,
        source_expr: str,
        from_sql: str,
        filter_clauses: List[str],
        buffer_value: Optional[float],
        raw_geom_expr: Optional[str],
        geography_buffer: bool = False,
    ) -> str:
        """``predicate(target, union of the selected source rows)`` as SQL.

        2026-10-17: Spatialite and OGR test a target against ONE geometry,
        the union of the selected source features. ``EXISTS (SELECT 1 FROM
        <source> WHERE ST_<pred>(target, row) AND <selection>)`` tested it
        against each feature: ST_Disjoint kept every target disjoint from a
        single feature (nearly the whole layer), ST_Within rejected a target
        spanning two adjacent source polygons, ST_Contains kept a target
        holding one of the selected features only.

        - intersects: true for the union iff true for one row - EXISTS kept;
        - disjoint: disjoint from the union iff it intersects no row -
          ``NOT EXISTS (... ST_Intersects ...)`` (ST_DWithin with a buffer),
          a target without geometry is not kept (as ST_Disjoint(NULL, x));
        - within, coveredby, touches, and intersects / disjoint with a
          negative buffer (erosion does not distribute over the union) only
          depend on the rows near the target: ``EXISTS (SELECT 1 FROM
          <source> WHERE row && <target grown by the buffer> AND <selection>
          HAVING <pred>(target, ST_Union(rows)))``, a small union per target
          the source GiST index finds;
        - contains, covers, equals, overlaps, crosses depend on every
          selected row (a far one breaks "contains"): against ``(SELECT
          ST_Union(rows) ...)``, an uncorrelated subquery PostgreSQL computes
          once per query, aliased ``__fm_union`` (a ``__source`` outside
          EXISTS reads as a corrupted FilterMate subset).

        The unions take ST_MakeValid rows: GEOS raises a TopologyException
        on an invalid polygon, which would reject the whole subset.

        Args:
            predicate_func: PostGIS predicate (ST_Intersects, ...)
            geom_expr: Target geometry expression
            source_expr: Source geometry of one row (e.g. ``__source."geom"``)
            from_sql: ``<relation> AS <alias>`` the rows come from
            filter_clauses: Selection clauses ANDed in the subquery
            buffer_value: Static buffer still to apply, None for none
            raw_geom_expr: Raw target column (centroid bbox test)
            geography_buffer: Apply the buffer on the geography (lon/lat target)
        """
        predicate_upper = predicate_func.upper()
        has_buffer = buffer_value is not None and buffer_value != 0
        eroding = has_buffer and float(buffer_value) < 0
        selection = " AND ".join(filter_clauses)
        not_null = f"{raw_geom_expr or geom_expr} IS NOT NULL"

        if predicate_upper in ('ST_INTERSECTS', 'ST_DISJOINT') and not eroding:
            test_func = 'ST_Intersects' if predicate_upper == 'ST_DISJOINT' else predicate_func
            if has_buffer:
                row_test = self._buffered_predicate(test_func, geom_expr, source_expr, buffer_value, raw_geom_expr)
            else:
                row_test = self._index_aware_predicate(test_func, geom_expr, source_expr, raw_geom_expr)
            where = f"{row_test} AND {selection}" if selection else row_test
            exists_expr = f'EXISTS (SELECT 1 FROM {from_sql} WHERE {where})'  # nosec B608 - identifiers quoted, SQL fragments FilterMate built
            if predicate_upper == 'ST_DISJOINT':
                return f"({not_null} AND NOT {exists_expr})"
            return exists_expr

        union_of_rows = f"ST_Union(ST_MakeValid({source_expr}))"
        if predicate_upper in self._LOCAL_UNION_PREDICATES or predicate_upper in ('ST_INTERSECTS', 'ST_DISJOINT'):
            margin = abs(float(buffer_value)) if has_buffer else 0.0
            if geography_buffer:
                margin = margin / self._METRES_PER_DEGREE_MIN
            reach = f"ST_Expand({geom_expr}, {margin})" if margin else geom_expr
            where = " AND ".join([f"{source_expr} && {reach}"] + list(filter_clauses))
            operand = self._buffer_sql(union_of_rows, buffer_value, geography_buffer) if has_buffer else union_of_rows
            test_func = 'ST_Intersects' if predicate_upper in ('ST_INTERSECTS', 'ST_DISJOINT') else predicate_func
            exists_expr = (
                f'EXISTS (SELECT 1 FROM {from_sql} WHERE {where} '  # nosec B608 - identifiers quoted, SQL fragments FilterMate built
                f'HAVING {test_func}({geom_expr}, {operand}))'
            )
            if predicate_upper == 'ST_DISJOINT':
                return f"({not_null} AND NOT {exists_expr})"
            return exists_expr

        def global_alias(sql: str) -> str:
            return re.sub(r'\b__source\b', '__fm_union', sql)

        where = f' WHERE {global_alias(selection)}' if selection else ''
        union_expr = f'(SELECT {global_alias(union_of_rows)} FROM {global_alias(from_sql)}{where})'  # nosec B608 - identifiers quoted, SQL fragments FilterMate built
        operand = self._buffer_sql(union_expr, buffer_value, geography_buffer) if has_buffer else union_expr
        # The union is only computed for a target whose bbox can hold the
        # result: inside CASE, PostgreSQL evaluates the subquery on first use
        # (a bare predicate turns it into an index condition, computed
        # upfront: 8.9 s instead of 44 ms for 30 000 sources none of the
        # targets contains). Contains / covers / equals need the target bbox
        # to hold the union bbox ("~", the buffer only grows it), the others
        # a bbox overlap with it, grown by a positive buffer.
        row = global_alias(source_expr)
        holds_union = predicate_upper in ('ST_CONTAINS', 'ST_COVERS', 'ST_EQUALS') and not eroding
        margin = float(buffer_value) if has_buffer and not eroding and not holds_union and not geography_buffer else 0.0
        envelope = (
            f'(SELECT ST_SetSRID(ST_Expand(ST_Extent({row})::geometry, {margin}), MAX(ST_SRID({row}))) '
            f'FROM {global_alias(from_sql)}{where})'  # nosec B608 - identifiers quoted, SQL fragments FilterMate built
        )
        bbox_test = f"{raw_geom_expr or geom_expr} {'~' if holds_union else '&&'} {envelope}"
        return f"CASE WHEN {bbox_test} THEN {predicate_func}({geom_expr}, {operand}) ELSE FALSE END"

    def _buffer_sql(self, geom_expr: str, buffer_value: float, geography: bool = False) -> str:
        """``ST_Buffer(geom, d, style)``, on the geography for a lon/lat geometry.

        No empty-geometry guard: an eroded-away union is an empty geometry no
        predicate matches (disjoint is NOT intersects).
        """
        endcap_style = self._get_buffer_endcap_style()
        quad_segs = self.task_params.get('buffer_segments', 5)
        style_params = f"quad_segs={quad_segs}"
        if endcap_style != 'round':
            style_params += f" endcap={endcap_style}"
        if geography:
            return f"ST_Buffer(({geom_expr})::geography, {buffer_value}, '{style_params}')::geometry"
        return f"ST_Buffer({geom_expr}, {buffer_value}, '{style_params}')"

    def _build_exists_expression(
        self,
        geom_expr: str,
        predicate_func: str,
        source_geom: str,
        source_filter: Optional[str],
        buffer_value: Optional[float],
        layer_props: Dict,
        original_source_table: Optional[str] = None,
        buffer_expression: Optional[str] = None,
        is_filter_chaining: bool = False,  # FIX v4.3.1: Explicit flag
        raw_geom_expr: Optional[str] = None,
        target_srid: Optional[int] = None
    ) -> str:
        """
        Build EXISTS subquery expression.

        Format: EXISTS (SELECT 1 FROM "schema"."source_table" AS __source
                        WHERE ST_Predicate("target_geom", __source."source_geom"))

        Args:
            geom_expr: Target geometry expression (UNQUALIFIED - e.g., "geom")
            predicate_func: PostGIS predicate (ST_Intersects, etc.)
            source_geom: Source geometry reference ("schema"."table"."geom")
            source_filter: Optional source filter (e.g., id IN (...) or "field" = 'value')
            buffer_value: Optional buffer distance (static)
            layer_props: Layer properties
            original_source_table: Original source table name for aliasing (v4.2.7)
            buffer_expression: Optional dynamic buffer expression (QGIS syntax)

        Returns:
            EXISTS subquery expression
        """
        if not source_geom:
            self.log_warning("No source_geom for EXISTS expression")
            return None

        # Parse source table reference
        source_ref = self._parse_source_table_reference(source_geom)

        if not source_ref:
            self.log_warning("Could not parse source table reference")
            return None

        source_schema = source_ref.get('schema', 'public')
        source_table = source_ref['table']
        source_geom_field = source_ref['geom_field']

        # 2026-09-13: when the selection lives in the source-selection MV
        # ("pk" and "geom" columns, GiST index), read the MV itself instead
        # of joining the whole source table through "fid" IN (SELECT pk ...):
        # the EXISTS then touches 1 734 rows instead of 500 000.
        mv_selection = self._source_selection_mv_ref(source_filter)
        if mv_selection and not (buffer_expression and buffer_expression.strip()):
            mv_schema, mv_table = mv_selection
            self.log_info(f"🗄️ EXISTS reads the source selection MV directly: \"{mv_schema}\".\"{mv_table}\"")
            source_schema, source_table, source_geom_field = mv_schema, mv_table, "geom"
            source_filter = None
            original_source_table = None
            whole_source_is_selection = True
        else:
            whole_source_is_selection = False

        # Build source geometry in subquery
        source_geom_in_subquery = f'__source."{source_geom_field}"'
        static_buffer = None  # 2026-09-13: set when a static buffer applies (see below)

        # FIX v4.2.20 (2026-01-21): Calculate buffer table name BEFORE filter chaining check
        # In filter chaining, we need to reference the ORIGINAL buffer table even after clearing buffer_expression
        # So compute the table name first, then decide whether to create it or reuse it
        buffer_table_name = None
        if buffer_expression and buffer_expression.strip():
            # CRITICAL FIX v4.2.20: For buffer table name, use CURRENT source_table (where buffer is defined)
            # NOT original_source_table (which is the first layer in the filter chain)
            # Example: zone_pop → demand_points (WITH buffer) → ducts → sheaths
            #   - At demand_points: source_table="demand_points", buffer_expression set
            #     → Create table: fm_buf_demand_points_xxx
            #   - At ducts: source_table="demand_points" (from source_geom), buffer_expression still set
            #     → Reuse table: fm_buf_demand_points_xxx (same name!)
            #   - At sheaths: source_table="demand_points", buffer_expression still set
            #     → Reuse table: fm_buf_demand_points_xxx (same name!)
            # 2026-10-17: the name also covers the selection, the session and
            # the task (_buffer_table_name): the reuse above stays within one task.
            buffer_table_name = self._buffer_table_name(source_schema, source_table, buffer_expression, source_filter)
            self.log_debug(f"Calculated buffer table name: {buffer_table_name} (from {source_table})")

        # FIX v4.2.17 (2026-01-21): Don't apply buffer_expression in filter chaining context
        # When source_filter contains EXISTS (filter chaining: zone_pop → demand_points → ducts → sheaths),
        # the buffer_expression references fields from the ORIGINAL source (demand_points.homecount)
        # but is being applied to INTERMEDIATE sources (ducts, sheaths) that don't have those fields!
        #
        # Example error: "ducts → sheaths" tries to use CASE WHEN ducts.homecount > 100
        # but "homecount" only exists in demand_points, not ducts!
        #
        # Solution: In filter chaining, the buffer was ALREADY applied when creating the temp table
        # for the original source (demand_points). Intermediate layers should use plain geometry.
        # FIX v4.3.1: Use explicit is_filter_chaining flag instead of detecting from source_filter
        # (source_filter may be None if EXISTS were already extracted)

        self.log_debug(f"🔍 Filter chaining detection: is_filter_chaining={is_filter_chaining}, buffer_expression={'SET' if buffer_expression else 'None'}")
        self.log_debug(f"   source_filter: {source_filter[:200] if source_filter else 'None'}...")

        # FIX v4.3.3 (2026-01-22): CRITICAL - Do NOT clear buffer_expression BEFORE creating table!
        #
        # Problem: Previous code (v4.3.2) cleared buffer_expression when is_filter_chaining=True,
        # BEFORE checking if the buffer table exists. This caused the table to never be created
        # on the FIRST distant layer, because buffer_expression was None.
        #
        # Example scenario: zone_pop → demand_points (buffer) → ducts → sheaths
        #   - ducts is FIRST distant layer after demand_points
        #   - source_filter already contains EXISTS from zone_pop
        #   - is_filter_chaining=True (EXISTS detected)
        #   - OLD CODE: Cleared buffer_expression → Table never created!
        #   - sheaths tries to reuse table → ERROR: table doesn't exist!
        #
        # Solution: Keep buffer_expression SET for the FIRST layer (to create table),
        # only clear it for SUBSEQUENT layers (to reuse table).
        # The table creation logic in _build_exists_with_buffer_table checks if table exists:
        #   - If exists: Return reuse expression (buffer_expression can be None)
        #   - If not exists: Create table (buffer_expression MUST be set)
        #
        # We DON'T clear buffer_expression here anymore - let _build_exists_with_buffer_table
        # handle table creation/reuse logic internally.

        # REMOVED in v4.3.3: Don't clear buffer_expression before creating table
        # if is_filter_chaining and buffer_expression:
        #     buffer_expression = None  # WRONG! Table not created yet!

        # FIX v4.2.14 (2026-01-21): ALWAYS use temp table for dynamic buffer expressions
        # Dynamic buffers (CASE WHEN) recalculate for EVERY feature pair - causes freeze on mapCanvas.refresh()
        # Problem: With 7 distant layers × 974 source features × 50k distant features each = 340M calculations!
        # Solution: Pre-calculate buffers ONCE in temp table, reuse across all EXISTS queries
        # Priority: temp_table (ALWAYS for dynamic) > buffer_value (static)
        # FIX v4.2.20: Also use temp table if buffer_table_name is set (filter chaining)
        if buffer_table_name:
            # CRITICAL: Use temp table for ALL dynamic buffer expressions
            # The freeze happens during mapCanvas.refresh() when QGIS renders all 7 layers simultaneously
            # Each layer's setSubsetString contains inline ST_Buffer(CASE WHEN...) that recalculates
            # for every feature during rendering - causes multi-minute freeze even with timeout protection
            if buffer_expression:
                self.log_info("🚀 Creating pre-calculated buffer table (prevents freeze on canvas refresh)")
            else:
                self.log_info("🔗 Reusing existing buffer table from filter chain")
            temp_table_expr = self._build_exists_with_buffer_table(
                geom_expr=geom_expr,
                predicate_func=predicate_func,
                source_schema=source_schema,
                source_table=source_table,
                source_geom_field=source_geom_field,
                buffer_expression=buffer_expression,
                source_filter=source_filter,
                layer_props=layer_props,
                buffer_table_name=buffer_table_name,  # FIX v4.2.20: Pass pre-calculated name
                target_srid=target_srid,
            )

            # If temp table creation succeeded, return it
            if temp_table_expr:
                return temp_table_expr

            # FIX v4.3.1 (2026-01-22): Handle filter chaining failure
            # If temp table creation failed in filter chaining (buffer_expression was cleared),
            # we cannot fallback to inline because we don't have the original buffer_expression
            # This should not happen if the first layer created the table successfully
            if not buffer_expression:
                self.log_error("❌ Buffer table creation failed AND buffer_expression is None (filter chaining)")
                self.log_error("   This means the original buffer table was never created or failed")
                self.log_error("   Cannot build filter - returning None to skip this filter")
                return None

            # Fallback to inline if temp table failed (logged in _build_exists_with_buffer_table)
            self.log_warning("⚠️  Temp table creation failed - falling back to inline buffer (may cause freeze)")
            self.log_warning(f"   🔍 DEBUG: is_filter_chaining={is_filter_chaining}, buffer_expression={'SET' if buffer_expression else 'None'}")

            # FIX v4.3.1 (2026-01-22): CRITICAL - Do NOT use inline buffer in filter chaining
            # In filter chaining, buffer_expression contains fields from the ORIGINAL source table
            # (e.g., demand_points.homecount) but would be applied to INTERMEDIATE tables (ducts, sheaths)
            # This causes "column __source.homecount does not exist" errors
            # If we're in filter chaining context, the buffer should ONLY come from the pre-calculated table
            if is_filter_chaining:
                self.log_error("❌ CRITICAL: Cannot use inline buffer in filter chaining context")
                self.log_error("   Buffer expression contains fields from original source, not intermediate table")
                self.log_error("   Example: if('homecount' >= 10, 50, 1) only valid on demand_points, not ducts")
                self.log_error("   Returning None to prevent 'column does not exist' SQL error")
                return None

            # Non-complex: Use inline buffer (existing code)
            from .filter_executor import qgis_expression_to_postgis
            buffer_expr_sql = qgis_expression_to_postgis(buffer_expression)

            # Prefix field references with __source. for subquery context
            # Pattern: "field" -> __source."field"
            # Note: 're' module is already imported at module level (line 22)
            # Only prefix unqualified field references (not already prefixed with table/alias)
            buffer_expr_sql = re.sub(
                r'(?<![.\w])"([^"]+)"(?!\s*\.)',
                r'__source."\1"',
                buffer_expr_sql
            )

            self.log_info(f"🔧 Using dynamic buffer expression: {buffer_expr_sql[:100]}...")
            source_geom_in_subquery = self._build_st_buffer_with_dynamic_expr(
                source_geom_in_subquery, buffer_expr_sql
            )
        # Apply static buffer
        elif buffer_value is not None and buffer_value != 0:
            # 2026-09-13: the buffer is folded into the predicate below
            # (ST_DWithin for intersects + positive round buffer, see
            # _buffered_predicate) instead of ST_Buffer() on the source.
            static_buffer = buffer_value

        # 2026-10-17: source rows in the SRID of the target, the buffer in
        # metres (see _source_in_target_srid). static_buffer becomes the
        # buffer left to apply in the target SRID.
        source_srid = self._source_table_srid()
        # An erosion goes through the union of the rows (see
        # _predicate_against_sources): on a lon/lat target it is applied to
        # that union on the geography, never row by row before the transform.
        erosion_on_geography = (
            static_buffer is not None and float(static_buffer) < 0
            and self._srid_is_geographic(target_srid or source_srid)
        )
        if erosion_on_geography:
            source_geom_in_subquery = self._transform_sql(source_geom_in_subquery, source_srid, target_srid)
        else:
            source_geom_in_subquery, static_buffer = self._source_in_target_srid(
                source_geom_in_subquery, source_srid, target_srid, static_buffer
            )

        # Source selection clauses (the spatial test is built by
        # _predicate_against_sources below)
        filter_clauses = []
        prefilter_filter = None  # 2026-09-13: aliased simple source filter for the envelope prefilter
        if whole_source_is_selection:
            prefilter_filter = "TRUE"  # the MV holds exactly the selection

        if source_filter:
            # CRITICAL FIX v4.2.8 (2026-01-21): Handle combined EXISTS filters properly
            #
            # Problem: When source_filter contains combined EXISTS subqueries (zone_pop + buffer),
            # we need to apply BOTH the spatial intersection AND the source filters.
            #
            # Before: Only added source_filter with aliasing (wrong for EXISTS patterns)
            # After: Detect if source_filter contains EXISTS - if yes, apply AS-IS (no aliasing needed)
            #        because EXISTS subqueries are ALREADY self-contained with their own aliases.
            #
            # Example source_filter from zone_pop + buffer optimization:
            #   (EXISTS (SELECT 1 FROM zone_pop AS __source WHERE ...)) AND
            #   (EXISTS (SELECT 1 FROM buffer AS __source WHERE ...))
            #
            # This filter should be applied DIRECTLY to verify the source geometry satisfies both constraints!

            # Check if source_filter contains EXISTS subqueries (combined filters from optimization)
            contains_exists = 'EXISTS' in source_filter.upper()

            if contains_exists:
                # FIX v4.2.8: EXISTS subqueries are self-contained - apply as-is
                # These are the combined zone_pop + buffer filters from Path 3A optimization
                # They MUST be applied to ensure source geometry passes all filter constraints
                self.log_info("🎯 source_filter contains EXISTS subqueries (combined filters)")
                self.log_info("   → Applying combined filter directly (no aliasing needed)")
                self.log_debug(f"   Combined filter preview: {source_filter[:200]}...")

                # CRITICAL: Add the combined EXISTS filters to WHERE clause
                # This ensures the source geometry satisfies zone_pop AND buffer constraints
                filter_clauses.append(f"({source_filter})")

            else:
                # Original aliasing logic for simple filters (FID IN, field = value, etc.)
                # CRITICAL FIX v4.2.7 (2026-01-22): Proper aliasing of source_filter
                #
                # Problem: When using buffer_expression (MV), source_table is the MV name
                # (mv_xxx_table_buffer_expr_dump) but source_filter contains the ORIGINAL
                # table name ("ducts"."id" IN ...) or a simple filter ("nom" = 'value').
                #
                # Solution: Use original_source_table (passed from task_parameters) for aliasing.
                # This ensures we replace the correct table name with __source.
                #
                # Patterns handled:
                # 1. "table"."pk" IN (...) → __source."pk" IN (...)
                # 2. "field" = 'value' → __source."field" = 'value' (when table name known)

                aliased_source_filter = source_filter

                # Priority 1: Use original_source_table if provided
                if original_source_table:
                    self.log_debug(f"Using original_source_table for aliasing: {original_source_table}")
                    aliased_source_filter = source_filter.replace(
                        f'"{original_source_table}".',
                        '__source.'
                    )
                else:
                    # Priority 2: Extract table name from source_filter pattern: "table"."column" IN (...)
                    filter_table_match = re.search(r'^"([^"]+)"\."([^"]+)"\s*IN', source_filter)
                    if filter_table_match:
                        filter_table_name = filter_table_match.group(1)
                        self.log_debug(f"Extracted table name from source_filter: {filter_table_name}")
                        aliased_source_filter = source_filter.replace(
                            f'"{filter_table_name}".',
                            '__source.'
                        )
                    else:
                        # Priority 3: Fallback to source_table from parsed source_geom
                        # This works when source_geom points to original table (no MV)
                        self.log_debug(f"Fallback: using source_table from source_geom: {source_table}")
                        aliased_source_filter = source_filter.replace(
                            f'"{source_table}".',
                            '__source.'
                        )

                self.log_debug(f"Aliased source_filter: {aliased_source_filter[:100]}...")
                prefilter_filter = aliased_source_filter
                filter_clauses.append(f"({aliased_source_filter})")

        exists_expr = self._predicate_against_sources(
            predicate_func,
            geom_expr,
            source_geom_in_subquery,
            f'"{source_schema}"."{source_table}" AS __source',
            filter_clauses,
            static_buffer,
            raw_geom_expr,
            geography_buffer=erosion_on_geography,
        )
        envelope_prefilter = self._source_envelope_prefilter(
            target_geom=raw_geom_expr or geom_expr,
            geom_expr=geom_expr,
            predicate_func=predicate_func,
            source_schema=source_schema,
            source_table=source_table,
            source_expr=source_geom_in_subquery,
            aliased_source_filter=prefilter_filter,
            buffer_value=static_buffer,
        )
        if envelope_prefilter:
            if 'EXISTS' not in exists_expr.upper():
                # union computed once (no EXISTS): no "__source" outside EXISTS
                # either, a corrupted FilterMate subset for the cleaners
                envelope_prefilter = re.sub(r'\b__source\b', '__fm_union', envelope_prefilter)
            exists_expr = f"({envelope_prefilter} AND {exists_expr})"
            self.log_info("📦 Source envelope prefilter added (GiST index on the target)")

        # FIX v4.2.13: Enhanced diagnostics for EXISTS expression
        self.log_info("📝 EXISTS expression built:")
        self.log_info(f"   Source: \"{source_schema}\".\"{source_table}\"")
        self.log_info(f"   Predicate: {predicate_func}")
        self.log_info(f"   Has buffer: {bool(buffer_expression or buffer_value)}")
        if buffer_expression:
            self.log_info(f"   Buffer expression: {buffer_expression[:80]}...")
        elif buffer_value:
            self.log_info(f"   Buffer value: {buffer_value}m")
        self.log_debug(f"   Full EXISTS: {exists_expr[:500]}...")

        return exists_expr

    @staticmethod
    def _is_source_table_reference(source_geom) -> bool:
        """Whether ``source_geom`` names a table column (``"table"."geom"``), as EXISTS needs."""
        return isinstance(source_geom, str) and re.search(r'"[^"]+"\."[^"]+"', source_geom) is not None

    def _parse_source_table_reference(self, source_geom: str) -> Optional[Dict]:
        """Parse source table reference from geometry expression.

        Handles formats:
        - "schema"."table"."column"
        - ST_Buffer("schema"."table"."column", value)
        - ST_Centroid("schema"."table"."column")
        - CASE WHEN ... "schema"."table"."column" ...
        """
        self.log_debug(f"Parsing source_geom: '{source_geom[:100]}...' " if len(source_geom) > 100 else f"Parsing source_geom: '{source_geom}'")

        # Pattern 1: "schema"."table"."column" (3 parts with dots)
        pattern = r'"([^"]+)"\."([^"]+)"\."([^"]+)"'
        match = re.search(pattern, source_geom)

        if match:
            result = {
                'schema': match.group(1),
                'table': match.group(2),
                'geom_field': match.group(3)
            }
            self.log_debug(f"Matched 3-part pattern: {result}")
            return result

        # Pattern 2: "table"."column" (2 parts, assume public schema)
        pattern2 = r'"([^"]+)"\."([^"]+)"'
        match2 = re.search(pattern2, source_geom)

        if match2:
            result = {
                'schema': 'public',
                'table': match2.group(1),
                'geom_field': match2.group(2)
            }
            self.log_debug(f"Matched 2-part pattern: {result}")
            return result

        self.log_warning(f"Could not parse source_geom: {source_geom[:200]}")
        return None

    def _build_st_buffer_with_style(self, geom_expr: str, buffer_value: float) -> str:
        """Build ST_Buffer expression with endcap style."""
        endcap_style = self._get_buffer_endcap_style()
        quad_segs = self.task_params.get('buffer_segments', 5)

        style_params = f"quad_segs={quad_segs}"
        if endcap_style != 'round':
            style_params += f" endcap={endcap_style}"

        buffer_expr = f"ST_Buffer({geom_expr}, {buffer_value}, '{style_params}')"

        # Wrap negative buffers in ST_MakeValid with empty check
        if buffer_value < 0:
            validated = f"ST_MakeValid({buffer_expr})"
            return f"CASE WHEN ST_IsEmpty({validated}) THEN NULL ELSE {validated} END"

        return buffer_expr

    def _build_st_buffer_with_dynamic_expr(self, geom_expr: str, buffer_expr_sql: str) -> str:
        """
        Build ST_Buffer expression with dynamic buffer expression (SQL).

        FIX v4.2.11 (2026-01-21): Support QGIS expressions converted to SQL.
        Example: if("homecount" > 100, 50, 1) -> CASE WHEN "homecount" > 100 THEN 50 ELSE 1 END

        Args:
            geom_expr: Geometry expression (e.g., __source."geom")
            buffer_expr_sql: SQL expression for buffer distance (already converted from QGIS)

        Returns:
            ST_Buffer expression with dynamic buffer
        """
        endcap_style = self._get_buffer_endcap_style()
        quad_segs = self.task_params.get('buffer_segments', 5)

        style_params = f"quad_segs={quad_segs}"
        if endcap_style != 'round':
            style_params += f" endcap={endcap_style}"

        # For dynamic expressions, we can't know if it's negative at build time
        # PostgreSQL will handle empty geometries gracefully with ST_IsEmpty check
        return f"ST_Buffer({geom_expr}, {buffer_expr_sql}, '{style_params}')"

    def _build_geography_buffer(self, geom_expr: str, buffer_value: float) -> str:
        """Buffer in metres of a lon/lat geometry, computed on the geography.

        2026-10-17: replaces the buffer via EPSG:3857, whose metres are
        1/cos(latitude) too short (a 100 m buffer was 72 m at 44° N).
        PostGIS buffers a geography in a suited planar projection and
        returns it in the SRID of the input.
        """
        endcap_style = self._get_buffer_endcap_style()
        quad_segs = self.task_params.get('buffer_segments', 5)
        style_params = f"quad_segs={quad_segs}"
        if endcap_style != 'round':
            style_params += f" endcap={endcap_style}"

        buffer_expr = f"ST_Buffer(({geom_expr})::geography, {buffer_value}, '{style_params}')::geometry"

        if buffer_value < 0:
            validated = f"ST_MakeValid({buffer_expr})"
            return f"CASE WHEN ST_IsEmpty({validated}) THEN NULL ELSE {validated} END"

        return buffer_expr

    def _normalize_column_case(self, expression: str, layer) -> str:
        """Normalize column names to match actual database case."""
        if not expression or not layer:
            return expression

        # Get actual column names from layer
        actual_columns = {}
        for field in layer.fields():
            actual_columns[field.name().lower()] = field.name()

        result = expression

        # Find quoted identifiers
        quoted_pattern = re.compile(r'"([^"]+)"')

        def normalize_match(match):
            col_name = match.group(1)
            col_lower = col_name.lower()
            if col_lower in actual_columns:
                return f'"{actual_columns[col_lower]}"'
            return match.group(0)

        result = quoted_pattern.sub(normalize_match, result)

        return result

    def _apply_numeric_type_casting(self, expression: str, layer) -> str:
        """Apply ::numeric casting for varchar field comparisons."""
        if not expression or not layer:
            return expression

        # Get varchar fields
        varchar_fields = set()
        for field in layer.fields():
            type_name = field.typeName().lower()
            if type_name in ('varchar', 'text', 'character varying', 'char'):
                varchar_fields.add(field.name().lower())

        if not varchar_fields:
            return expression

        # Pattern: "field" operator number
        pattern = re.compile(
            r'"([^"]+)"(\s*)(<|>|<=|>=)(\s*)(\d+(?:\.\d+)?)',
            re.IGNORECASE
        )

        def add_cast(match):
            field = match.group(1)
            if field.lower() in varchar_fields:
                return f'"{field}"::numeric{match.group(2)}{match.group(3)}{match.group(4)}{match.group(5)}'
            return match.group(0)

        if '::numeric' not in expression:
            expression = pattern.sub(add_cast, expression)

        return expression

    def _is_geometric_filter(self, subset: str) -> bool:
        """Check if subset contains geometric filter patterns."""
        subset_upper = subset.upper()

        geometric_patterns = [
            '__source',
            '__fm_union',  # 2026-10-17: union of the source rows (_predicate_against_sources)
            'EXISTS (',
            'EXISTS(',
            'ST_INTERSECTS',
            'ST_CONTAINS',
            'ST_WITHIN',
            'ST_TOUCHES',
            'ST_OVERLAPS',
            'ST_CROSSES',
            'ST_DISJOINT',
            'ST_BUFFER'
        ]

        return any(p in subset_upper or p.lower() in subset.lower() for p in geometric_patterns)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'PostgreSQLExpressionBuilder',
]

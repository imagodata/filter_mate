# -*- coding: utf-8 -*-
"""
SQL Utilities for FilterMate

Provides SQL sanitization and safety functions.

Migrated from modules/appUtils.py to infrastructure/database/sql_utils.py
"""

import logging
import sys
import time as _perf
from contextlib import contextmanager

try:
    from qgis.PyQt.QtCore import QCoreApplication
except ImportError:
    QCoreApplication = None

from ..logging.redaction import mask_sensitive_text

logger = logging.getLogger('FilterMate.Infrastructure.Database.SQLUtils')


def _on_main_thread() -> bool:
    """True on the Qt main thread (a widget is never touched from a task's worker)."""
    try:
        from qgis.PyQt.QtCore import QThread
        app = QCoreApplication.instance() if QCoreApplication is not None else None
        return app is not None and QThread.currentThread() == app.thread()
    except Exception:  # catch-all safety net: unknown means no
        return False


@contextmanager
def feature_picker_guard(layer):
    """
    FIX 2026-02-11: Temporarily detach QgsFeaturePickerWidget to prevent crash during subset change.

    QgsFeaturePickerWidget's internal model iterates features on a background thread.
    If setSubsetString() is called while iteration is in progress, it causes an access
    violation in sqlite3_bind_int64. Detaching the widget (setLayer(None)) stops the
    background thread before the subset string changes.

    Args:
        layer: QgsVectorLayer whose subset string is about to change
    """
    picker = None
    try:
        # 2026-10-17: the plugin's dock module, by its package. ``from filter_mate_dockwidget
        # import`` (absolute) never found it (ImportError swallowed): the guard never ran.
        # Read from sys.modules: no import of the dock where it was never loaded (Processing).
        from ...core.domain.plugin_package import PLUGIN_PACKAGE
        dock_module = sys.modules.get(f"{PLUGIN_PACKAGE}.filter_mate_dockwidget")
        active_dock = getattr(dock_module, '_active_dockwidget', None)
        if active_dock is not None and _on_main_thread():
            widget = getattr(active_dock, 'mFeaturePickerWidget_exploring_single_selection', None)
            if widget is not None and hasattr(widget, 'layer') and widget.layer() == layer:
                widget.setLayer(None)
                picker = widget
                logger.debug("FIX-2026-02-11: FeaturePickerWidget detached before subset change")
    except (ImportError, RuntimeError, Exception) as e:
        logger.debug(f"FIX-2026-02-11: feature_picker_guard detach skipped: {e}")

    try:
        yield
    finally:
        if picker is not None:
            try:
                if layer and hasattr(layer, 'isValid') and layer.isValid():
                    picker.setLayer(layer)
                    logger.debug("FIX-2026-02-11: FeaturePickerWidget reattached after subset change")
            except (RuntimeError, Exception) as e:
                logger.debug(f"FIX-2026-02-11: feature_picker_guard reattach failed: {e}")


try:
    from ...filtermate_core.sql.identifiers import sanitize_sql_identifier  # noqa: F401  (moved to the host-free core)
except ImportError:  # imported from the repository root (tests)
    from filtermate_core.sql.identifiers import sanitize_sql_identifier  # noqa: F401


def _layer_count_label(layer) -> str:
    """Return a count label for diagnostics: features (vector) or points (point cloud).

    Args:
        layer: QgsVectorLayer or QgsPointCloudLayer.

    Returns:
        str: ``"<n> features"``, ``"<n> points"`` or ``"n/a"`` when no count is available.
    """
    try:
        if hasattr(layer, 'featureCount'):
            return f"{layer.featureCount()} features"
        if hasattr(layer, 'pointCount'):
            return f"{layer.pointCount()} points"
    except Exception as e:
        logger.debug(f"[SQL]   Count unavailable: {e}")
    return "n/a"


def _text_field_names(layer) -> set:
    """Lower-case names of the layer's text columns (the sanitizer drops ``( "text column" )`` operands).

    2026-10-17: a text column is never a boolean condition; a boolean one
    (``AND ( "actif" )``) is, and must be kept. Empty when unknown.
    """
    names = set()
    try:
        for field in layer.fields():
            field_type = field.type()
            # QVariant.String (Qt5) / QMetaType.Type.QString (Qt6)
            if field_type == 10 or getattr(field_type, 'name', None) == 'QString':
                names.add(field.name().lower())
    except Exception:  # nosec B110 - no field information: nothing is dropped
        return set()
    return names


def safe_set_subset_string(layer, subset_expression: str) -> bool:
    """
    Safely set subset string (filter) on a QGIS layer.

    Handles edge cases:
    - Layer is None or invalid
    - setSubsetString method not available (rare)
    - Exception during filter application

    FIX v4.8.1 (2026-01-25): Automatically apply PostgreSQL type casting
    for PostgreSQL layers to prevent "operator does not exist" errors
    when comparing varchar fields to numeric literals.

    Args:
        layer: QgsVectorLayer (or QgsPointCloudLayer) to filter
        subset_expression: SQL WHERE clause (without WHERE keyword)

    Returns:
        bool: True if filter applied successfully, False otherwise

    Examples:
        >>> safe_set_subset_string(layer, "population > 10000")
        True
        >>> safe_set_subset_string(None, "any expression")
        False
    """
    if not layer:
        logger.warning("safe_set_subset_string: layer is None")
        return False

    # Server predicates must be checked before the legacy sanitizer can
    # remove an unsupported fragment or a display expression.
    try:
        from ...core.domain.source_capability import classify_layer
    except ImportError:
        from core.domain.source_capability import classify_layer
    capability = classify_layer(layer)
    if capability.requires_server_translation:
        from ...adapters.qgis.server_filter_translation import (
            ServerFilterError, apply_server_subset, remember_server_filter_error,
        )
        remember_server_filter_error(layer, '')
        try:
            with feature_picker_guard(layer):
                return apply_server_subset(layer, subset_expression)
        except ServerFilterError as exc:
            remember_server_filter_error(layer, str(exc))
            logger.warning('%s', exc)
            from qgis.core import Qgis, QgsMessageLog
            QgsMessageLog.logMessage(str(exc), 'FilterMate', Qgis.MessageLevel.Warning)
            return False

    # PERF 2026-09-12: phase timings, logged when the whole call takes 250 ms
    # or more. A 16 s setSubsetString was measured on a PostgreSQL target and
    # nothing between "Applying subset" and the result said which phase it was.
    _t_start = _perf.perf_counter()
    _types_ms = _cast_ms = _set_ms = 0.0
    try:
        if hasattr(layer, 'setSubsetString'):
            # FIX v4.2.13: Enhanced diagnostics for setSubsetString failures
            logger.debug(f"[SQL] Applying subset to layer '{layer.name()}':")
            logger.debug(f"[SQL]   Provider: {layer.providerType()}")
            logger.debug(f"[SQL]   Expression length: {len(subset_expression) if subset_expression else 0} chars")

            # H2 FIX (2026-04-23): defense-in-depth sanitization at the universal
            # setSubsetString chokepoint. Upstream callers (favorites apply,
            # filter task) already sanitize on capture, but a tampered config
            # or stale favorite can re-enter the subset layer through other
            # paths (undo/redo, public API, legacy task paths). The sanitizer
            # is idempotent on already-clean expressions and strips standalone
            # display expressions (COALESCE/CONCAT/CASE-as-boolean) that would
            # otherwise reach PostgreSQL as "WHERE COALESCE(...)" → type error.
            if subset_expression:
                sanitize_subset_string = None
                try:
                    # Plugin context: loaded as filter_mate.infrastructure.database.sql_utils
                    from ...core.filter import sanitize_subset_string as _sanitize
                    sanitize_subset_string = _sanitize
                except ImportError:
                    try:
                        # Test context: plugin root on sys.path
                        from core.filter import sanitize_subset_string as _sanitize
                        sanitize_subset_string = _sanitize
                    except ImportError:
                        logger.debug("[SQL]   sanitize_subset_string unavailable; skipping")

                if sanitize_subset_string is not None:
                    sanitized = sanitize_subset_string(subset_expression, text_fields=_text_field_names(layer))
                    if sanitized != subset_expression:
                        logger.info(
                            f"[SQL]   Sanitized subset string for layer '{layer.name()}': "
                            f"'{subset_expression[:80]}...' → '{sanitized[:80]}...'"
                        )
                    subset_expression = sanitized

            # FIX v4.8.2: Detect type mismatches BEFORE applying to PostgreSQL
            # Prevents "operator does not exist: character varying < integer" errors
            _t_phase = _perf.perf_counter()
            if subset_expression and layer.providerType() == 'postgres':
                try:
                    from ..database.field_type_detector import get_field_types_from_layer
                    from ...core.services.expression_service import ExpressionService

                    field_types = get_field_types_from_layer(layer)
                    service = ExpressionService()
                    warnings = service.detect_type_mismatches(subset_expression, field_types)

                    if warnings:
                        logger.warning("⚠️ Type mismatch detected in PostgreSQL expression:")
                        for warning in warnings:
                            logger.warning(f"  - {warning}")

                        # Show warning to user via QGIS message bar
                        try:
                            from qgis.utils import iface
                            if iface:
                                title = QCoreApplication.translate(
                                    "SqlUtils",
                                    "FilterMate - PostgreSQL Type Warning"
                                )
                                message = QCoreApplication.translate(
                                    "SqlUtils",
                                    "Type mismatch in filter: {warning_detail}..."
                                ).format(warning_detail=warnings[0][:100])
                                iface.messageBar().pushWarning(title, message)
                        except (ImportError, AttributeError):
                            pass  # No UI available (testing environment)

                        logger.info("💡 FilterMate will auto-apply type casting to fix this.")
                except Exception as type_check_err:
                    logger.debug(f"Type mismatch detection failed (non-critical): {type_check_err}")

            # FIX v4.8.1: Apply PostgreSQL type casting for PostgreSQL layers
            # This ensures numeric comparisons have ::numeric casting
            _types_ms = (_perf.perf_counter() - _t_phase) * 1000.0
            _t_phase = _perf.perf_counter()
            if subset_expression and layer.providerType() == 'postgres':
                try:
                    # Import from adapters (infrastructure/database -> adapters/backends)
                    from ...adapters.backends.postgresql.filter_executor import apply_postgresql_type_casting
                    subset_expression = apply_postgresql_type_casting(subset_expression, layer)
                    logger.debug("[SQL]   PostgreSQL type casting applied")
                except ImportError:
                    # Fallback: inline type casting if import fails
                    import re
                    pattern = r'"([^"]+)"(?!::)(\s*)(<|>|<=|>=|=)(\s*)(\d+(?:\.\d+)?)'

                    def add_cast(m):
                        return f'"{m.group(1)}"::numeric{m.group(2)}{m.group(3)}{m.group(4)}{m.group(5)}'
                    subset_expression = re.sub(pattern, add_cast, subset_expression)
                    logger.debug("[SQL]   PostgreSQL type casting applied (fallback)")

            _cast_ms = (_perf.perf_counter() - _t_phase) * 1000.0
            if subset_expression:
                # Log first 500 chars of expression for debugging
                preview = subset_expression[:500]
                if len(subset_expression) > 500:
                    preview += f"... ({len(subset_expression) - 500} more chars)"
                logger.debug(f"[SQL]   Expression: {preview}")

            # FIX 2026-02-11: Detach FeaturePickerWidget before subset change to prevent crash
            _t_phase = _perf.perf_counter()
            with feature_picker_guard(layer):
                result = layer.setSubsetString(subset_expression)

            # FIX v4.9.0: Retry for PostgreSQL layers after connection reset.
            # When a prior complex PostGIS EXISTS query fails, the QGIS PostgreSQL provider
            # may leave its internal connection in an aborted-transaction state, causing
            # all subsequent setSubsetString() calls to fail even with valid expressions.
            # reloadData() forces a fresh connection so the retry has a clean state.
            if not result and layer.providerType() == 'postgres':
                logger.info(
                    f"[SQL] 🔄 setSubsetString failed for PostgreSQL layer '{layer.name()}' "
                    "- retrying once after reloadData()..."
                )
                try:
                    layer.dataProvider().reloadData()
                    with feature_picker_guard(layer):
                        result = layer.setSubsetString(subset_expression)
                    if result:
                        logger.info("[SQL]   ✓ Retry succeeded after reloadData()")
                    else:
                        logger.warning("[SQL]   ✗ Retry also failed after reloadData()")
                except Exception as _retry_err:
                    logger.warning(f"[SQL]   ⚠️ Retry attempt raised exception: {_retry_err}")
            _set_ms = (_perf.perf_counter() - _t_phase) * 1000.0
            _total_ms = (_perf.perf_counter() - _t_start) * 1000.0
            if _total_ms >= 250:
                logger.info(
                    f"⏱ set_subset: {_total_ms:.0f} ms ({layer.name()}: types {_types_ms:.0f} ms, "
                    f"cast {_cast_ms:.0f} ms, setSubsetString {_set_ms:.0f} ms)"
                )

            if not result:
                logger.warning(f"setSubsetString returned False for layer {layer.name()}")
                # Additional diagnostics for failure
                logger.warning("[SQL] ❌ FAILED - Diagnostics:")
                # The source of a PostgreSQL layer without authcfg carries its password
                logger.warning(f"[SQL]   Layer source: {mask_sensitive_text(layer.source())[:200]}...")
                logger.warning(f"[SQL]   Count before: {_layer_count_label(layer)}")
                logger.warning(f"[SQL]   Current subset: {layer.subsetString()[:200] if layer.subsetString() else 'None'}...")

                # FIX v4.9.0: Improved provider error capture for PostgreSQL layers
                try:
                    provider = layer.dataProvider()
                    if provider:
                        # Try QgsDataProvider.error() (returns QgsError)
                        if hasattr(provider, 'error') and provider.error():
                            pg_msg = provider.error().message()
                            if pg_msg:
                                logger.warning(f"[SQL]   Provider error: {pg_msg}")
                        # Try errors() which returns a list of error messages (QGIS 3.x)
                        if hasattr(provider, 'errors'):
                            for err_item in (provider.errors() or []):
                                logger.warning(f"[SQL]   Provider errors(): {err_item}")
                        # For PostgreSQL, try executing a simple query to check connection state
                        if layer.providerType() == 'postgres':
                            try:
                                from ...infrastructure.utils import get_datasource_connexion_from_layer
                                conn, _ = get_datasource_connexion_from_layer(layer)
                                if conn:
                                    # Check if connection is in a broken/aborted transaction state
                                    try:
                                        try:
                                            with conn.cursor() as cur:
                                                cur.execute("SELECT 1")
                                            conn.rollback()  # Keep the connection clean after the probe
                                            logger.info("[SQL]   PostgreSQL connection (psycopg2 probe): OK")
                                        except Exception as probe_inner:
                                            try:
                                                conn.rollback()
                                            except Exception:  # nosec B110 - best-effort rollback after connection probe failure
                                                pass
                                            logger.warning(f"[SQL]   PostgreSQL connection BROKEN: {mask_sensitive_text(str(probe_inner))}")
                                            logger.warning("[SQL]   → Root cause: prior query may have aborted the transaction")
                                    finally:
                                        # The probe opened its own connection: do not leak it
                                        try:
                                            conn.close()
                                        except Exception:  # nosec B110 - best-effort close of the probe connection
                                            pass
                            except Exception as pg_probe_e:
                                logger.debug(f"[SQL]   psycopg2 probe unavailable: {pg_probe_e}")
                except Exception as diag_e:
                    logger.debug(f"[SQL]   Could not get provider error: {diag_e}")

                # Log the full expression to a separate line for easy copy/paste
                logger.warning(f"[SQL] Full expression that FAILED:\n{subset_expression}")
            else:
                logger.debug(f"[SQL] ✓ Success - {_layer_count_label(layer)} after filter")

            return result
        else:
            logger.error(f"Layer {layer.name()} does not have setSubsetString method")
            return False
    except Exception as e:
        logger.error(f"Error setting subset string on layer {layer.name()}: {e}")
        logger.error(f"[SQL] Exception details - Expression:\n{subset_expression}")
        return False


def create_temp_spatialite_table(
    db_path: str,
    table_name: str,
    sql_query: str,
    geom_field: str = 'geometry',
    srid: int = 4326,
    register_geometry: bool = False
) -> bool:
    """
    Create temporary table in Spatialite database.

    Alternative to PostgreSQL materialized views for Spatialite backend.
    Creates a temp table populated from a SELECT query. The layer's subset
    only reads its primary key, so by default the geometry column is neither
    registered in ``geometry_columns`` nor spatially indexed: the table stays
    an anonymous scratch table that cannot be mistaken for a user layer (and
    adds no trigger, R-tree or metadata row to the user's database).

    Args:
        db_path: Path to Spatialite database file
        table_name: Name for temporary table
        sql_query: SELECT query to populate table
        geom_field: Name of geometry column (default: 'geometry')
        srid: SRID for geometry column (default: 4326)
        register_geometry: Register the geometry column and create its R-tree
            index (native Spatialite databases only)

    Returns:
        bool: True if table created successfully

    Example:
        >>> create_temp_spatialite_table(
        ...     "/path/to/db.sqlite",
        ...     "temp_filtered",
        ...     "SELECT * FROM cities WHERE population > 100000",
        ...     "geom",
        ...     3857
        ... )
        True
    """
    import sqlite3

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.enable_load_extension(True)

        # Load Spatialite extension
        try:
            conn.load_extension('mod_spatialite')
        except sqlite3.OperationalError:
            try:
                conn.load_extension('mod_spatialite.dll')  # Windows fallback
            except Exception as e:
                logger.error(f"Failed to load Spatialite extension: {e}")
                return False

        cursor = conn.cursor()

        # Quoted: the name is data (session id + layer id), never a bare identifier
        quoted_table = '"' + sanitize_sql_identifier(table_name).replace('"', '""') + '"'

        # Drop existing table if exists
        cursor.execute(f"DROP TABLE IF EXISTS {quoted_table}")  # nosec B608

        # Create table from query
        create_sql = f"CREATE TABLE {quoted_table} AS {sql_query}"  # nosec B608
        cursor.execute(create_sql)

        # Register the geometry and index it (opt-in, see the docstring)
        if register_geometry:
            try:
                # Register geometry column
                cursor.execute(f"""
                    SELECT RecoverGeometryColumn(
                        '{sanitize_sql_identifier(table_name)}',
                        '{sanitize_sql_identifier(geom_field)}',
                        {srid},
                        'GEOMETRY',
                        'XY'
                    )
                """)

                # Create R-tree spatial index
                cursor.execute(f"""
                    SELECT CreateSpatialIndex(
                        '{sanitize_sql_identifier(table_name)}',
                        '{sanitize_sql_identifier(geom_field)}'
                    )
                """)
            except Exception as e:
                logger.warning(f"Could not create spatial index: {e}")
                # Continue anyway - table is still usable without index

        conn.commit()

        logger.info(f"Created temporary Spatialite table: {table_name}")
        return True

    except Exception as e:
        logger.error(f"Error creating Spatialite temp table {table_name}: {e}")
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # nosec B110 - best-effort close
                pass


def format_pk_values_for_sql(
    values: list,
    pk_field: str = None,
    layer=None,
    is_numeric: bool = None
) -> str:
    """
    Format primary key values for SQL IN clause.

    CENTRALIZED v4.3.8: Single implementation for all backends.
    2026-10-17: the literals are written by core.filter.pk_formatter (one
    formatter for every path); this wrapper only adds the PostgreSQL
    ``::uuid`` cast of a uuid-typed key.

    Handles different data types:
    - UUID: Quoted strings with ::uuid cast ('uuid-value'::uuid)
    - Text: Quoted strings ('text-value'), quotes doubled
    - Numeric: Unquoted (123, 456)

    Detection priority (2026-10-17: the schema before the values, so a text
    key made of digits such as '01001' stays quoted):
    1. Explicit is_numeric parameter
    2. Field schema from the layer (a text field holding real numbers is numeric)
    3. Every value: numbers or integers written as text without a leading zero

    Args:
        values: List of feature ID values
        pk_field: Primary key field name (optional)
        layer: QgsVectorLayer for schema inspection (optional)
        is_numeric: Force numeric detection (optional)

    Returns:
        str: Comma-separated formatted values for SQL IN clause

    Examples:
        >>> format_pk_values_for_sql([1, 2, 3], 'id')
        '1, 2, 3'
        >>> format_pk_values_for_sql(['a', 'b'], 'code')
        "'a', 'b'"
        >>> format_pk_values_for_sql(['550e8400-e29b-41d4-a716-446655440000'], 'uuid_pk')
        "'550e8400-e29b-41d4-a716-446655440000'::uuid"
    """
    if not values:
        return ""

    try:
        from ...core.filter.pk_formatter import format_key_literal, is_pk_numeric, key_field, key_values_look_numeric
    except ImportError:
        from core.filter.pk_formatter import format_key_literal, is_pk_numeric, key_field, key_values_look_numeric

    if is_numeric is None:
        field = key_field(layer, pk_field)
        if field is not None:
            try:
                if 'uuid' in str(field.typeName()).lower():
                    return ", ".join(format_key_literal(fid, False) + "::uuid" for fid in values)
            except Exception as e:  # nosec B110 - type name unavailable, the numeric test below decides
                logger.debug(f"Could not get field schema: {e}")
            is_numeric = is_pk_numeric(layer, pk_field, sample_values=values)
        else:
            is_numeric = key_values_look_numeric(values)
        logger.debug(f"PK '{pk_field}' formatted as {'numeric' if is_numeric else 'text'}")

    return ", ".join(format_key_literal(fid, is_numeric) for fid in values)


__all__ = [
    'sanitize_sql_identifier',
    'safe_set_subset_string',
    'create_temp_spatialite_table',
    'format_pk_values_for_sql',
]

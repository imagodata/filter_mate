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
import re
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
# Memory (and delimited text) layers evaluate the subset with QgsExpression,
# which also scans the list for every feature: on 100,000 rows a read took
# 10.8 s with 1,000 keys, 45 s with 5,000, 156 s with 20,000 (QGIS 4.2.3).
# Above PLAIN_KEY_LIST_WARNING a WARNING names the cost; above
# PLAIN_KEY_LIST_MAX the filter is refused with an explicit error.
# PostgreSQL is not bounded: its planner hashes a long IN list once per
# statement and the key is indexed.
PLAIN_KEY_LIST_WARNING = 1000
PLAIN_KEY_LIST_MAX = 5000

# 2026-10-17: caches that used to live in ``task_params`` (= the source
# layer's PROJECT_LAYERS entry, so they outlived the task). Dropped on sight.
STALE_TASK_PARAM_CACHES = (
    '_ogr_source_union_cache', '_ogr_buffered_source_cache', '_spatialite_source_bbox_cache',
)

# DE-9IM patterns of A covers B / A is covered by B (A, B: relate(A, B)).
COVERS_PATTERNS = ("T*****FF*", "*T****FF*", "***T**FF*", "****T*FF*")
COVERED_BY_PATTERNS = ("T*F**F***", "*TF**F***", "**FT*F***", "**F*TF***")


# 2026-10-17: a spatial function CALL (name followed by "("), not a substring.
_GEOMETRIC_FILTER_RE = re.compile(
    r"\b(?:ST_\w+|Intersects|Contains|Within|Touches|Overlaps|Crosses|Disjoint|Equals|Covers|CoveredBy"
    r"|MbrIntersects|GeomFromText|GeomFromGPB|Buffer)\s*\(",
    re.IGNORECASE,
)


def _de9im_matches(matrix: str, pattern: str) -> bool:
    """DE-9IM ``matrix`` (e.g. "0F1FF0102") against ``pattern`` (T, F, *, 0, 1, 2)."""
    if not matrix or len(matrix) != 9:
        return False
    for cell, wanted in zip(matrix.upper(), pattern.upper()):
        if wanted == '*':
            continue
        if wanted == 'T':
            if cell not in '012':
                return False
        elif cell != wanted:
            return False
    return True


def _de9im_any(matrix: str, patterns) -> bool:
    return any(_de9im_matches(matrix, pattern) for pattern in patterns)


def task_scoped_cache(task, name: str, owner) -> dict:
    """Cache ``name`` held by the filter task, or by ``owner`` without a task (2026-10-17)."""
    store = getattr(task, '__dict__', None) if task is not None else None
    if store is None:
        store = owner.__dict__
    return store.setdefault('_filtermate_task_caches', {}).setdefault(name, {})


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


# Import the port interface
try:
    from ....core.ports.geometric_filter_port import GeometricFilterPort
except ImportError:
    from core.ports.geometric_filter_port import GeometricFilterPort

# 2026-10-17: the one formatter of key literals (quotes doubled, type-driven).
try:
    from ....core.filter.pk_formatter import QGIS_EXPRESSION, SQL, format_key_literal, is_null_value, is_pk_numeric
except ImportError:
    from core.filter.pk_formatter import QGIS_EXPRESSION, SQL, format_key_literal, is_null_value, is_pk_numeric

# 2026-10-17: the stable key shared with the layer registration (never "the first integer field").
try:
    from ....core.domain.stable_key import FEATURE_ID, FEATURE_ID_KEY, NONE, KeyChoice, choose_key, is_feature_id_key
except ImportError:
    from core.domain.stable_key import FEATURE_ID, FEATURE_ID_KEY, NONE, KeyChoice, choose_key, is_feature_id_key

# Providers whose subset is a QGIS expression AND address features by ``$id`` (no fid column).
FEATURE_ID_EXPRESSION_PROVIDERS = ('memory', 'delimitedtext')


def stable_key(layer):
    """adapters.qgis.source_capability_probe.stable_key_for_layer: the key, proven unique on a local layer.

    Outside the plugin package (unit tests) the names alone decide, and a
    local layer without a declared key is keyed by its feature id.
    """
    try:
        from ...qgis.source_capability_probe import stable_key_for_layer
    except ImportError:
        capability = source_capability(layer)
        fields = layer.fields()
        names = [field.name() for field in fields]
        try:
            declared = [fields.at(index).name() for index in layer.dataProvider().pkAttributeIndexes()]
        except Exception:  # nosec B110 - provider PK lookup best-effort, the names decide
            declared = []
        choice = choose_key(names, declared, local=not capability.is_remote)
        if choice.origin == FEATURE_ID and not capability.lists_feature_ids:
            return KeyChoice(None, NONE)
        if choice.origin == NONE and capability.lists_feature_ids:
            return KeyChoice(FEATURE_ID_KEY, FEATURE_ID)
        return choice
    return stable_key_for_layer(layer)


def source_capability(layer):
    """core.domain.source_capability of ``layer`` (web service, remote file, database...)."""
    try:
        from ...qgis.source_capability_probe import capability_for_layer
    except ImportError:  # loaded outside the plugin package (unit tests)
        from core.domain.source_capability import classify_layer as capability_for_layer
    capability = capability_for_layer(layer)
    if capability is None:
        from core.domain.source_capability import classify
        capability = classify('', '')
    return capability


def translate(context: str, text: str) -> str:
    """``QCoreApplication.translate``; the source text without Qt (or a mocked one)."""
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        translated = QCoreApplication.translate(context, text)
    except Exception:  # nosec B110 - untranslated message without Qt (unit tests)
        return text
    return translated if isinstance(translated, str) else text


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


def _worker_processing_kwargs(feedback=None, settings=None) -> dict:
    """``processing.run`` keyword arguments for the filter task's worker thread (2026-10-17).

    An explicit QgsProcessingContext: without one, processing.run() builds its own from
    the project and ``iface.mapCanvas()``, read from the worker thread: QGIS crashed
    (segfault in createExpressionContext) while the main thread removed a layer. It
    carries the Processing settings captured on the main thread when the task was
    created (invalid geometry check, project transform context, ellipsoid).
    """
    kwargs = {'feedback': feedback}
    try:
        from ....infrastructure.utils.processing_context import worker_processing_context
        context = worker_processing_context(settings)
    except ImportError:  # test doubles of the plugin packages
        try:
            from qgis.core import QgsProcessingContext
            context = QgsProcessingContext()
        except ImportError:  # test doubles of qgis.core
            context = None
    if context is not None:
        kwargs['context'] = context
    return kwargs


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
        # (Intersects). select-by-location has no covers predicate: on its
        # per-feature fallback only, Contains / Within APPROXIMATE them (a
        # boundary contact counts for Covers, not for Contains). The union
        # path (_select_against_union) tests them exactly.
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
        # 2026-10-17: messages for the QGIS message bar (collected by the
        # orchestrator into the task's warning_messages).
        self.user_warnings = []

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
            use_centroids: Test the target by its centroids (point on surface), like
                ``ST_PointOnSurface`` on the SQL backends (FilterMate 5: chosen per target)
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
            'buffer_expression': buffer_expression,
            'use_centroids': bool(use_centroids),
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
        Apply filter: select the target features in QGIS, write them as a key list.

        2026-10-17: the same semantics as the SQL backends.

        - The source is the union of its features, buffered after the union
          (as the SpatiaLite executor does), mixed geometry types reduced to
          the highest dimension (polygons, else lines, else points).
        - The target is read WITHOUT its current subset: the new key list is
          then combined with ``old_subset`` by the rules every backend uses
          (``_combine_with_old_subset``). Reading through the old subset used
          to turn ``(old) OR (keys)`` into ``old``, and to intersect a new
          spatial filter with the previous one instead of replacing it.
        - Disjoint alone is written ``NOT (<keys of the intersecting
          features>)``: the key list stays the size of the source window, not
          of the whole table.

        Thread Safety:
        - Uses lock for concurrent access detection

        Args:
            layer: Layer to filter
            expression: JSON parameters from build_expression
            old_subset: Existing subset to combine with (see the orchestrator's
                _determine_subset_strategy)
            combine_operator: Combine operator, None to replace

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
            from qgis.core import QgsVectorLayer

            # Parse parameters
            params = json.loads(expression) if expression else {}
            predicates = params.get('predicates', ['intersects'])
            buffer_value = params.get('buffer_value')
            buffer_expression = params.get('buffer_expression')
            use_centroids = bool(params.get('use_centroids'))
            names = [str(pred).lower().replace('st_', '') for pred in predicates] or ['intersects']

            # Get source layer
            source_layer = self.source_geom

            if source_capability(layer).requires_server_translation:
                from ...qgis.server_filter_translation import dialect_for_layer
                if dialect_for_layer(layer) == 'unsupported':
                    self.last_error = translate(
                        'OGRExpressionBuilder',
                        '{0}: this provider cannot guarantee a complete server filter. '
                        'Use a bounded local copy before filtering.'
                    ).format(layer.name())
                    self.user_warnings.append(self.last_error)
                    return False

            if source_layer is None:
                self.last_error = "No source layer available for OGR filter"
                self.log_error(self.last_error)
                return False

            if not isinstance(source_layer, QgsVectorLayer):
                self.last_error = f"Source is not a QgsVectorLayer: {type(source_layer)}"
                self.log_error(self.last_error)
                return False

            refusal = self._key_list_refusal(layer)
            if refusal:
                self.last_error = refusal
                self.user_warnings.append(refusal)
                return False

            # Remote reads belong to the bounded worker path (lot B).
            self._feedback = CancellableFeedback()
            if source_capability(source_layer).is_remote_service or source_capability(layer).is_remote_service:
                self._feedback._is_cancelled_callback = (
                    getattr(self.task_params.get('_parent_task'), 'isCanceled', None) if self.task_params else None)
            if source_capability(source_layer).is_remote_service:
                from .filter_executor import copy_remote_source
                try:
                    source_layer = copy_remote_source(source_layer, self.task_params, self._feedback)
                except ValueError as exc:
                    self.last_error = str(exc)
                    self.user_warnings.append(self.last_error)
                    return False
            if source_capability(layer).is_remote_service:
                from .filter_executor import apply_remote_spatial_filter
                return apply_remote_spatial_filter(
                    self, layer, source_layer, names, buffer_value, buffer_expression,
                    use_centroids, old_subset, combine_operator)

            self.log_info(f"📍 Applying OGR filter to {layer.name()}")
            self.log_info(f"  - Source: {source_layer.name()} ({source_layer.featureCount()} features)")

            target = self._unfiltered_target(layer, old_subset, combine_operator)
            source_union = self._source_geometry(source_layer, buffer_value, buffer_expression)
            complement = False
            if source_union is not None:
                if names == ['disjoint']:
                    complement = True
                    selected_ids = self._select_against_union(target, source_union, source_layer.crs(), ['intersects'],
                                                              use_centroids)
                else:
                    selected_ids = self._select_against_union(target, source_union, source_layer.crs(), names,
                                                              use_centroids)
                if selected_ids is None:
                    return False
            else:
                # Per-feature fallback (no union available): buffer each feature
                if use_centroids and source_layer.featureCount() > 0:
                    note = (f"{layer.name()}: tested by its full geometry, not its centroids "
                            "(the source could not be merged into one geometry)")
                    self.log_warning(f"  - {note}")
                    self.user_warnings.append(note)
                if buffer_expression and buffer_expression.strip():
                    source_layer = self._apply_buffer_expression_to_layer(source_layer, buffer_expression)
                    if source_layer is None:
                        self.last_error = f"Failed to apply dynamic buffer expression: {buffer_expression[:80]}"
                        self.log_error(self.last_error)
                        return False
                elif buffer_value is not None and buffer_value != 0:
                    source_layer = self._apply_buffer_to_layer(source_layer, buffer_value)
                    if source_layer is None:
                        self.last_error = f"Failed to apply static buffer ({buffer_value}m)"
                        self.log_error(self.last_error)
                        return False
                # 2026-10-17 (review): each target feature tested against the source features,
                # read by the worker like the union path reads the target. native:selectbylocation
                # selected in the project's layer from the worker thread (selection signals there,
                # the user's selection wiped); a second layer on the same source cost a provider
                # and could not exist for a memory / virtual target. Covers / CoveredBy are exact.
                selected_ids = self._select_feature_by_feature(target, source_layer, names)
                if selected_ids is None:
                    return False
            self.log_info(f"  - {'Intersecting' if complement else 'Selected'}: {len(selected_ids)} features")

            refusal = self._key_list_refusal(layer, len(selected_ids))
            if refusal:
                self.last_error = refusal
                self.log_error(refusal)
                self.user_warnings.append(refusal)
                return False

            if len(selected_ids) > PLAIN_KEY_LIST_WARNING and self._rescans_key_lists(layer):
                if len(selected_ids) > PLAIN_KEY_LIST_MAX:
                    kept = "keeps its previous filter" if layer.subsetString() else "is left unfiltered"
                    self.last_error = (
                        f"{layer.name()}: {len(selected_ids):,} features to list, more than {PLAIN_KEY_LIST_MAX:,} "
                        "keys for this file format (OGR SQL rescans the list for every row, GDAL refuses ~8,000). "
                        f"The layer {kept}: convert it to GeoPackage to filter it."
                    )
                    self.log_error(self.last_error)
                    self.user_warnings.append(self.last_error)
                    return False
                self.log_warning(
                    f"  ⚠️ {len(selected_ids):,} keys in the subset of {layer.name()}: every read of this format "
                    "rescans the list (about 3 s per 1,000 keys on 380,000 rows); GeoPackage avoids it"
                )

            if len(selected_ids) > KEY_LIST_JSON_THRESHOLD and self._is_sqlite_storage(layer) and not json1_available():
                kept = "keeps its previous filter" if layer.subsetString() else "is left unfiltered"
                self.last_error = (
                    f"{layer.name()}: {len(selected_ids):,} keys and no JSON1 in this SQLite build: a plain key "
                    f"list that long freezes QGIS. The layer {kept}."
                )
                self.log_error(self.last_error)
                self.user_warnings.append(self.last_error)
                return False

            key_filter = self._key_filter(layer, target, selected_ids)
            if key_filter is None:
                self.log_error(self.last_error)
                self.user_warnings.append(self.last_error)
                return False
            if complement:
                key_filter = "1 = 1" if not selected_ids else f"NOT ({key_filter})"
            final_filter = self._combine_with_old_subset(old_subset, combine_operator, key_filter)

            if source_capability(layer).requires_server_translation:
                from ...qgis.server_filter_translation import prepare_server_subset
                prepare_server_subset(layer, final_filter)

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

            return success

        except Exception as e:
            self.last_error = f"OGR apply_filter exception: {e}"
            self.log_error(self.last_error)
            self.user_warnings.append(self.last_error)
            return False

    def _key_filter(self, layer, target, selected_ids: list) -> Optional[str]:
        """Key-list subset of ``selected_ids`` (ids read from ``target``) for ``layer``.

        FIX v4.5.3: for OGR layers with a real PK attribute field, use actual
        field values instead of QGIS internal FIDs (the pseudo 'fid' column
        is unreliable in setSubsetString for many OGR drivers).
        None (``last_error`` set) when a web service gives no key value.
        """
        if not selected_ids:
            return "1 = 0"
        pk_field = self._get_primary_key(layer)
        use_pk_values = bool(pk_field) and not self._is_feature_id_key(layer, pk_field)
        if not use_pk_values:
            # No real PK field: use QGIS internal FIDs with pseudo 'fid' column
            return self._build_fid_filter(layer, selected_ids)
        if self._pk_is_feature_id(layer, pk_field):
            # PERF 2026-10-17: on a GeoPackage the QGIS feature ids ARE the
            # FID column values (checked on BD TOPO 31: 98,687 / 98,687);
            # fetching them again by id took 4 s (9 s on 1.15 M rows).
            pk_values = list(selected_ids)
        else:
            # PERF 2026-09-13: one request for all selected rows. The ids come
            # from ``target`` (the unfiltered reading of the layer), so are the
            # values: a PostgreSQL feature id is only valid in its own layer.
            pk_values = self._fetch_pk_values(target, selected_ids, pk_field)
        if not pk_values:
            if source_capability(layer).is_remote_service:
                # 2026-10-17: QGIS feature ids mean nothing to a web service
                self.last_error = translate(
                    "OGRExpressionBuilder",
                    "{0}: the key values of the selected features could not be read from the web service."
                ).format(layer.name())
                return None
            self.log_warning("  - Could not retrieve PK values, falling back to FID-based filter")
            return self._build_fid_filter(layer, selected_ids)
        self.log_info(f"  - Retrieved {len(pk_values)} actual PK values")
        return self._build_fid_filter_with_values(layer, pk_values, pk_field)

    def _combine_with_old_subset(self, old_subset: Optional[str], combine_operator: Optional[str], new_filter: str) -> str:
        """Same rule as SpatialiteExpressionBuilder.apply_filter (2026-10-17).

        The orchestrator passes an operator only with an attribute filter;
        a previous spatial filter (geometric or key list) is replaced.
        """
        if old_subset and combine_operator and not self._is_geometric_filter(old_subset):
            return f"({old_subset}) {combine_operator} ({new_filter})"
        return new_filter

    def _unfiltered_target(self, layer, old_subset=None, combine_operator=None):
        """The target layer read WITHOUT its current subset (2026-10-17).

        A second layer on the same data source, subset removed (same feature
        ids for OGR and SpatiaLite, PK values fetched from it for
        PostgreSQL). When the source cannot be reopened (memory layer,
        unknown URI), the layer itself is read and a WARNING says the result
        is limited to its current subset.
        """
        current = layer.subsetString()
        if not current:
            return layer
        if (
            old_subset and combine_operator == 'AND' and current == old_subset
            and not self._is_geometric_filter(old_subset)
        ):
            return layer  # (old) AND (keys): reading through old gives the same keys, faster
        try:
            from qgis.core import QgsProviderRegistry, QgsVectorLayer
            provider = layer.providerType()
            if provider != 'memory':
                registry = QgsProviderRegistry.instance()
                parts = dict(registry.decodeUri(provider, layer.source()))
                if parts:
                    # 'filter': the subset of a WFS / OGC API Features URI
                    for key in ('subset', 'sql', 'filter'):
                        parts.pop(key, None)
                    clone = QgsVectorLayer(registry.encodeUri(provider, parts), f"{layer.name()} (unfiltered)",
                                           provider)
                else:
                    # 2026-10-17: QGIS 3.44 decodes nothing for a WFS URI ({}): the
                    # same source, its subset cleared (the provider rewrites its URI).
                    clone = QgsVectorLayer(layer.source(), f"{layer.name()} (unfiltered)", provider)
                    if clone.isValid() and clone.subsetString():
                        clone.setSubsetString('')
                if clone.isValid() and not clone.subsetString():
                    self._temp_layers_keep_alive.append(clone)
                    return clone
        except Exception as exc:  # nosec B110 - falls back to the layer itself below
            self.log_debug(f"  - Unfiltered reading of {layer.name()} unavailable: {exc}")
        self.log_warning(
            f"  ⚠️ {layer.name()} ({layer.providerType()}) cannot be read without its current filter: "
            "the new filter is computed inside it"
        )
        return layer

    @staticmethod
    def _rescans_key_lists(layer) -> bool:
        """Layers whose subset rescans a key list for every row (2026-10-17).

        OGR files evaluated by OGR SQL (Shapefile, GeoJSON, ...) and the
        QgsExpression-based providers (memory, delimited text): bounded by
        PLAIN_KEY_LIST_MAX. GeoPackage / SQLite use the JSON literal;
        PostgreSQL and SpatiaLite layers are not bounded. Web services have
        their own, lower bound (SourceCapability.key_list_limit, see
        _key_list_refusal).
        """
        try:
            provider = layer.providerType()
        except Exception:
            return False
        if provider in ('memory', 'delimitedtext'):
            return True
        return provider == 'ogr' and not OGRExpressionBuilder._is_sqlite_storage(layer)

    def _key_list_refusal(self, layer, key_count: Optional[int] = None) -> Optional[str]:
        """Why ``layer`` cannot get a key-list subset (None when it can), 2026-10-17.

        - a web service whose key is the QGIS feature id (no declared key, no
          field named like a unique key): its feature ids mean nothing to the
          server, a list of them would be a wrong result;
        - more than ``key_list_limit`` keys for a web service: the list goes
          into every request (OGC Filter, CQL2 text, ``where=``).
        """
        try:
            capability = source_capability(layer)
        except Exception:  # nosec B110 - no classification: no refusal
            return None
        if capability.lists_feature_ids and not capability.is_remote_service:
            return None
        if layer.subsetString():
            kept = translate("OGRExpressionBuilder", "keeps its previous filter")
        else:
            kept = translate("OGRExpressionBuilder", "is left unfiltered")
        if key_count is None:
            if not self._is_feature_id_key(layer, self._get_primary_key(layer)):
                return None
            if capability.is_remote_service:
                return translate(
                    "OGRExpressionBuilder",
                    "{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, "
                    "objectid...), so the selected features cannot be listed for the server. The layer {1}. "
                    "An attribute filter, or a local copy of the layer, works."
                ).format(layer.name(), kept)
            return translate(
                "OGRExpressionBuilder",
                "{0}: this layer has no unique key field and its feature ids cannot be listed in its filter "
                "(a virtual layer needs a unique id column, its uid). The layer {1}."
            ).format(layer.name(), kept)
        if not capability.is_remote_service:
            return None
        limit = capability.key_list_limit
        if limit and key_count > limit:
            return translate(
                "OGRExpressionBuilder",
                "{0}: {1} features to list, more than the {2} sent to a web service. The layer {3}. "
                "Narrow the selection, use an attribute filter, or work on a local copy of the layer."
            ).format(layer.name(), f"{key_count:,}", f"{limit:,}", kept)
        return None

    @staticmethod
    def _is_feature_id_key(layer, pk_field: str) -> bool:
        """The key is the QGIS feature id: ``$id``, or a legacy ``fid`` that is no field of the layer."""
        if not pk_field:
            return False
        if pk_field == FEATURE_ID_KEY:
            return True
        try:
            return is_feature_id_key(pk_field, [pk_field] if layer.fields().indexOf(pk_field) >= 0 else [])
        except Exception:
            return False

    @staticmethod
    def _dialect(layer) -> str:
        """Literal dialect of the layer's subset: a QGIS expression (memory, WFS...) escapes backslashes."""
        try:
            return QGIS_EXPRESSION if source_capability(layer).subset_is_qgis_expression else SQL
        except Exception:
            return SQL

    def _in_list(self, layer, field_sql: str, literals: list) -> str:
        """``field IN (...)``, split into ORed lists where the source caps one list (Oracle: 1000)."""
        try:
            chunk = source_capability(layer).in_list_max
        except Exception:
            chunk = None
        if not chunk or len(literals) <= chunk:
            return f'{field_sql} IN ({", ".join(literals)})'
        parts = [f'{field_sql} IN ({", ".join(literals[i:i + chunk])})' for i in range(0, len(literals), chunk)]
        self.log_info(f"  - {len(literals):,} keys split into {len(parts)} lists of at most {chunk}")
        return "(" + " OR ".join(parts) + ")"

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
        feature_id_key = self._is_feature_id_key(layer, pk_field)

        # Numeric or text PK (quoting): the field type, else the values (core.filter.pk_formatter)
        is_numeric_pk = True if feature_id_key else is_pk_numeric(layer, pk_field, sample_values=list(fids))
        dialect = self._dialect(layer)
        literals = [format_key_literal(fid, is_numeric_pk, dialect) for fid in fids]
        fid_list = ", ".join(literals)

        # 2026-10-17: memory / delimited text subsets are QGIS expressions: the
        # feature id is $id there ('fid' is no field of theirs). Elsewhere the
        # pseudo key '$id' is OGR's FID column, written fid. The FID of a
        # Shapefile / CSV is its row number: renumbered when the file is edited.
        try:
            provider = layer.providerType()
        except Exception:
            provider = ''
        if feature_id_key:
            if provider in FEATURE_ID_EXPRESSION_PROVIDERS:
                return f'$id IN ({fid_list})'
            pk_field = 'fid'
        pk_field_lower = pk_field.lower()

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
            return self._in_list(layer, f'"{pk_field}"', literals)

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

        # FIX v4.0.9 / 2026-10-17: numeric or text key from the field type first
        # (a text code made of digits, '01001', stays quoted), then from ALL the
        # values (a PostgreSQL integer read as text through OGR is numeric).
        # The literals are written by core.filter.pk_formatter (quotes doubled).
        is_numeric_pk = is_pk_numeric(layer, pk_field, sample_values=pk_values)
        dialect = self._dialect(layer)
        literals = [format_key_literal(v, is_numeric_pk, dialect) for v in pk_values]
        value_list = ", ".join(literals)
        self.log_info(
            f"  - Building {'NUMERIC' if is_numeric_pk else 'STRING'} IN clause for '{pk_field}': {len(pk_values)} values"
        )
        self.log_debug(f"    Sample: {value_list[:100]}...")

        if len(pk_values) > KEY_LIST_JSON_THRESHOLD and self._is_sqlite_storage(layer):
            return self._json_key_clause(f'"{pk_field}"', pk_values, is_numeric_pk)

        # Always use quoted field name for PostgreSQL (Oracle: lists of at most 1000)
        return self._in_list(layer, f'"{pk_field}"', literals)

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
        """``field IN (SELECT value FROM json_each('[...]'))`` (see KEY_LIST_JSON_THRESHOLD).

        2026-10-17: integers are written as they are (int64 beyond 2^53
        included), integral floats as integers, other numbers and text keys
        as JSON strings; None keys are dropped (they match nothing).
        """
        kept = [v for v in values if not is_null_value(v)]
        if numeric:
            items = []
            for value in kept:
                if isinstance(value, bool):
                    items.append(json.dumps(str(value)))
                elif isinstance(value, int):
                    items.append(str(value))
                elif isinstance(value, float) and value.is_integer():
                    items.append(str(int(value)))
                elif isinstance(value, str) and value.lstrip('-').isdigit():
                    items.append(str(int(value)))
                else:
                    items.append(json.dumps(value if isinstance(value, (int, float)) else str(value), ensure_ascii=False))
            payload = "[" + ",".join(items) + "]"
        else:
            payload = json.dumps([str(v) for v in kept], ensure_ascii=False, separators=(",", ":"))
        self.log_info(f"  - {len(kept):,} keys: one JSON literal ({len(payload):,} chars) instead of an IN list")
        literal = payload.replace("'", "''")  # json.dumps output as one SQL string literal
        return f"{field_sql} IN (SELECT value FROM json_each('{literal}'))"  # nosec B608 - JSON of the keys, quotes doubled

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
            if not is_null_value(pk_value):
                pk_values.append(pk_value)
        return pk_values

    def _buffered_source_cache(self) -> dict:
        """Buffered source layers of the task, shared by every target layer.

        PERF 2026-09-13: apply_filter() runs once per target layer and buffered
        the source layer each time. 2026-10-17: held by the task (it used to
        live in task_params and outlive it, see _task_cache).
        """
        return self._task_cache('ogr_buffered_source')

    def _task_cache(self, name: str) -> dict:
        """A cache that lives as long as the filter task (2026-10-17).

        ``task_params`` is the source layer's entry of PROJECT_LAYERS: a cache
        kept there outlived the task (a buffered source or a source union
        became stale after an edit). The caches now hang on the task object
        (``_parent_task``, set by the orchestrator, released by the finished
        handler); without a task (tests, API) they live with this builder.
        """
        params = self.task_params if isinstance(self.task_params, dict) else {}
        for stale in STALE_TASK_PARAM_CACHES:
            params.pop(stale, None)
        return task_scoped_cache(params.get('_parent_task'), name, self)

    def _source_geometry(self, layer: 'QgsVectorLayer', buffer_value=None, buffer_expression=None):
        """Union of the source as the SQL backends see it, or None to test feature by feature.

        2026-10-17, aligned on filter_executor.process_spatialite_geometries():
        union first, mixed geometry types reduced to the highest dimension
        (polygons, else lines, else points), then the static buffer on the
        union (an erosion of the union is not the union of the erosions).
        A dynamic buffer expression buffers each feature (its own distance)
        before the union. Computed once per task, source and buffer.
        """
        from qgis.core import QgsFeatureRequest, QgsGeometry

        params = self.task_params if isinstance(self.task_params, dict) else {}
        segments = int(params.get('buffer_segments', 5) or 5)
        cap = str(params.get('buffer_endcap_style', 'round')).lower()
        dynamic = bool(buffer_expression and str(buffer_expression).strip())
        distance = 0.0 if dynamic else float(buffer_value or 0.0)
        cache = self._task_cache('ogr_source_geometry')
        try:
            key = (layer.id(), distance, str(buffer_expression or '').strip(), segments, cap)
        except RuntimeError:
            return None
        if key in cache:
            return cache[key]
        source = layer
        if dynamic:
            source = self._apply_buffer_expression_to_layer(layer, buffer_expression)
            if source is None:
                cache[key] = None
                return None
        try:
            geometries = [
                feature.geometry()
                for feature in source.getFeatures(QgsFeatureRequest().setNoAttributes())
                if feature.hasGeometry() and not feature.geometry().isEmpty()
            ]
        except (RuntimeError, TypeError):
            geometries = []
        union = None
        if len(geometries) == 1:
            union = QgsGeometry(geometries[0])
        elif geometries:
            union = QgsGeometry.unaryUnion(geometries)
            if union is None or union.isEmpty():
                union = QgsGeometry.unaryUnion([geometry.makeValid() for geometry in geometries])
        if union is not None and not union.isEmpty():
            union = self._highest_dimension(union)
        if union is None or union.isEmpty():
            if geometries:
                self.log_warning(
                    f"  ⚠️ Union of the source {layer.name()} unavailable: each source feature is tested on its own "
                    "(Crosses / Touches / Within may differ from the SQL backends)"
                )
            cache[key] = None
            return None
        if distance:
            union = self._buffer_geometry(union, distance, segments, cap)
        self.log_info(f"  - Source dissolved: {len(geometries)} features → 1 (union semantics)")
        cache[key] = union
        return union

    @staticmethod
    def _highest_dimension(geometry):
        """Polygons of a mixed collection, else its lines, else its points (as the SQL executor)."""
        from qgis.core import QgsGeometry, QgsWkbTypes

        if 'GeometryCollection' not in QgsWkbTypes.displayString(geometry.wkbType()):
            return geometry
        collection = geometry.constGet()
        parts = {}
        for index in range(collection.numGeometries()):
            part = collection.geometryN(index)
            parts.setdefault(QgsWkbTypes.geometryType(part.wkbType()), []).append(QgsGeometry(part.clone()))
        for dimension in (
            QgsWkbTypes.GeometryType.PolygonGeometry,
            QgsWkbTypes.GeometryType.LineGeometry,
            QgsWkbTypes.GeometryType.PointGeometry,
        ):
            if parts.get(dimension):
                return QgsGeometry.collectGeometry(parts[dimension])
        return None

    @staticmethod
    def _buffer_geometry(geometry, distance: float, segments: int, cap: str):
        """The static buffer of filter_executor._apply_static_buffer (round joins, miter 2)."""
        from qgis.core import Qgis, QgsGeometry

        caps = {'round': Qgis.EndCapStyle.Round, 'flat': Qgis.EndCapStyle.Flat, 'square': Qgis.EndCapStyle.Square}
        buffered = geometry.buffer(float(distance), max(int(segments), 1), caps.get(cap, Qgis.EndCapStyle.Round),
                                   Qgis.JoinStyle.Round, 2.0)
        if buffered is None:
            return QgsGeometry()
        if distance < 0 and not buffered.isEmpty():
            buffered = buffered.makeValid()
        return buffered

    def _select_against_union(self, layer, union, union_crs, predicates, use_centroids: bool = False) -> Optional[list]:
        """Ids of the ``layer`` features related to ``union`` by any of ``predicates``.

        With ``use_centroids`` each target is tested by its point on surface (inside the
        feature, like ``ST_PointOnSurface`` on the SQL backends).

        2026-10-17: same directions as native:selectbylocation (INPUT =
        target, INTERSECT = source): Contains = the target contains the
        source, Within = the target is within the source. Covers / CoveredBy
        are exact here (DE-9IM of the source against the target). One request
        (bounding box of the source, the whole layer for Disjoint), a
        prepared source, and a prepared Intersects before the costlier
        predicates. Measured on 100,000 road segments and a 260 KB river
        network: Crosses 0.94 s, Intersects 0.43 s in QGIS 4.2.3.
        Returns None (last_error set) when cancelled.
        """
        from qgis.core import QgsFeatureRequest, QgsGeometry

        names = {str(name).lower().replace('st_', '') for name in predicates}
        if union.isEmpty():
            # An erosion that ate the whole source: nothing intersects it.
            if 'disjoint' not in names:
                return []
        engine = QgsGeometry.createGeometryEngine(union.constGet())
        engine.prepareGeometry()
        request = QgsFeatureRequest().setNoAttributes()
        request.setDestinationCrs(union_crs, self._transform_context())
        if 'disjoint' not in names:  # every predicate but Disjoint needs a shared point
            request.setFilterRect(union.boundingBox())
        tests = {
            'contains': engine.within,     # target contains source
            'equals': engine.isEqual,
            'touches': engine.touches,
            'overlaps': engine.overlaps,
            'within': engine.contains,     # target within source
            'crosses': engine.crosses,
            # source DE-9IM against the target: target covers source <=> source covered by target
            'covers': lambda g: _de9im_any(engine.relate(g), COVERED_BY_PATTERNS),
            'coveredby': lambda g: _de9im_any(engine.relate(g), COVERS_PATTERNS),
        }
        selected = []
        for index, feature in enumerate(layer.getFeatures(request)):
            if index % 1000 == 0 and self._feedback is not None and self._feedback.isCanceled():
                self.last_error = "OGR selection cancelled"
                return None
            if not feature.hasGeometry():
                continue
            target_geometry = feature.geometry()
            if use_centroids:
                target_geometry = target_geometry.pointOnSurface()
                if target_geometry.isNull():
                    continue
            geometry = target_geometry.constGet()
            if not engine.intersects(geometry):
                if 'disjoint' in names:
                    selected.append(feature.id())
                continue
            if 'intersects' in names or any(name in tests and tests[name](geometry) for name in names):
                selected.append(feature.id())
        return selected

    def _processing_settings(self):
        """The Processing settings the task captured on the main thread (None: the last captured)."""
        params = self.task_params if isinstance(self.task_params, dict) else {}
        return params.get('_processing_settings')

    def _transform_context(self):
        """The project's transform context, captured on the main thread when the task was created.

        2026-10-17: read from the worker (``QgsProject.instance().transformContext()``) only
        when nothing was captured (a builder used outside a FilterMate task).
        """
        settings = self._processing_settings() or {}
        context = settings.get('transform_context')
        if context is None:
            try:
                from ....infrastructure.utils.processing_context import captured_transform_context
                context = captured_transform_context()
            except ImportError:  # test doubles of the plugin packages
                context = None
        if context is None:
            try:
                from qgis.core import QgsProject
                context = QgsProject.instance().transformContext()
            except ImportError:  # test doubles of qgis.core
                return None
        return context

    def _select_feature_by_feature(self, target, source_layer, predicates) -> Optional[list]:
        """Ids of the ``target`` features related to ANY source feature by any of ``predicates``.

        The fallback when the source cannot be merged into one geometry: the source
        features are indexed (in the target's CRS) and each target feature is tested
        against those whose bounding box it meets, with the directions of the union
        path (Contains = the target contains the source...). Disjoint: the targets
        meeting no source feature. No selection, no second layer, no Processing.
        Returns None (last_error set) when cancelled.
        """
        from qgis.core import QgsFeatureRequest, QgsGeometry, QgsSpatialIndex

        names = {str(name).lower().replace('st_', '') for name in predicates}
        request = QgsFeatureRequest().setNoAttributes()
        transform_context = self._transform_context()
        if transform_context is not None:
            request.setDestinationCrs(target.crs(), transform_context)
        index = QgsSpatialIndex()
        engines = {}
        for position, feature in enumerate(source_layer.getFeatures(request)):
            if position % 1000 == 0 and self._feedback is not None and self._feedback.isCanceled():
                self.last_error = "OGR selection cancelled"
                return None
            if not feature.hasGeometry() or feature.geometry().isEmpty():
                continue
            engine = QgsGeometry.createGeometryEngine(feature.geometry().constGet())
            engine.prepareGeometry()
            engines[feature.id()] = engine
            index.addFeature(feature)

        def related(engine, geometry):
            tests = {
                'contains': engine.within,     # target contains source
                'equals': engine.isEqual,
                'touches': engine.touches,
                'overlaps': engine.overlaps,
                'within': engine.contains,     # target within source
                'crosses': engine.crosses,
                'covers': lambda g: _de9im_any(engine.relate(g), COVERED_BY_PATTERNS),
                'coveredby': lambda g: _de9im_any(engine.relate(g), COVERS_PATTERNS),
            }
            return 'intersects' in names or any(name in tests and tests[name](geometry) for name in names)

        selected = []
        for position, feature in enumerate(target.getFeatures(QgsFeatureRequest().setNoAttributes())):
            if position % 1000 == 0 and self._feedback is not None and self._feedback.isCanceled():
                self.last_error = "OGR selection cancelled"
                return None
            if not feature.hasGeometry():
                continue
            target_geometry = feature.geometry()
            geometry = target_geometry.constGet()
            meeting = [engines[fid] for fid in index.intersects(target_geometry.boundingBox())
                       if fid in engines and engines[fid].intersects(geometry)]
            if not meeting:
                if 'disjoint' in names:
                    selected.append(feature.id())
                continue
            if any(related(engine, geometry) for engine in meeting):
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
                **_worker_processing_kwargs(self._feedback if hasattr(self, '_feedback') else None,
                                            self._processing_settings())
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
        """Buffer each source feature by the distance its expression gives.

        2026-10-17: the distance is evaluated on every feature, never
        averaged. The previous strategies (an average over 100 features used
        as a static buffer, or the last number of the expression) gave
        267.5 m to every road of the Muret scene where the expression says
        300 or 250 m: 2,546 buildings instead of 2,753. Same segments and end
        cap as a static buffer (task parameters ``buffer_segments`` /
        ``buffer_endcap_style``). A feature whose distance is NULL or not a
        number is left out, as ``ST_Buffer(geom, NULL)`` is NULL in SQL (a
        WARNING counts them); a negative distance erodes it.

        Args:
            layer: Source layer (attributes needed by the expression)
            buffer_expression: QGIS expression returning the buffer distance

        Returns:
            Memory layer of the buffered features (MultiPolygon), or None
            (last_error set) when the expression does not parse.
        """
        from qgis.core import (
            QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsFeature, QgsFeatureRequest,
        )

        params = self.task_params if isinstance(self.task_params, dict) else {}
        segments = int(params.get('buffer_segments', 5) or 5)
        cap = str(params.get('buffer_endcap_style', 'round')).lower()
        cache = self._buffered_source_cache()
        try:
            cache_key = (layer.id(), 'expression', str(buffer_expression).strip(), segments, cap)
        except RuntimeError:
            return None
        cached = cache.get(cache_key)
        if cached is not None:
            try:
                if cached.isValid():
                    return cached
            except RuntimeError:
                pass  # C++ object gone: rebuild below

        expression = QgsExpression(buffer_expression)
        if expression.hasParserError():
            self.last_error = f"Buffer expression does not parse: {expression.parserErrorString()}"
            self.log_error(self.last_error)
            return None
        context = QgsExpressionContext()
        context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
        expression.prepare(context)

        buffered = []
        distances = set()
        skipped = 0
        for feature in layer.getFeatures(QgsFeatureRequest()):
            if not feature.hasGeometry() or feature.geometry().isEmpty():
                continue
            context.setFeature(feature)
            value = expression.evaluate(context)
            try:
                distance = float(value) if value is not None else None
            except (TypeError, ValueError):
                distance = None
            if distance is None or distance != distance:  # NULL, text or NaN
                skipped += 1
                continue
            distances.add(distance)
            geometry = self._buffer_geometry(feature.geometry(), distance, segments, cap)
            if geometry is None or geometry.isEmpty():
                continue
            geometry.convertToMultiType()
            out = QgsFeature()
            out.setGeometry(geometry)
            buffered.append(out)
        if skipped:
            self.log_warning(
                f"  ⚠️ Buffer expression gave no distance for {skipped} source feature(s): left out "
                "(as ST_Buffer(geom, NULL) in SQL)"
            )
        shown = ", ".join(f"{d:g}" for d in sorted(distances)[:6]) + (" ..." if len(distances) > 6 else "")
        self.log_info(
            f"  - Buffer per feature: {len(buffered)} feature(s), distances {shown or 'none'} "
            f"({segments} segments, {cap} end caps)"
        )
        result = self._memory_layer_of(buffered, layer.crs(), "filtermate_buffered_source")
        if result is not None:
            cache[cache_key] = result
        return result

    def _memory_layer_of(self, features: list, crs, name: str):
        """A MultiPolygon memory layer holding ``features`` (kept alive with this builder)."""
        from qgis.core import QgsVectorLayer

        memory = QgsVectorLayer("MultiPolygon", name, "memory")
        memory.setCrs(crs)
        if features:
            memory.dataProvider().addFeatures(features)
        memory.updateExtents()
        self._source_layer_keep_alive.append(memory)
        return memory

    def _get_primary_key(self, layer) -> str:
        """
        Get primary key field name (core.domain.stable_key, 2026-10-17).

        Priority order:
        1. Provider-declared primary key
        2. A field named like a key: on a local layer only when its values are
           proven unique and never NULL (id, *_id, uuid*, objectid, fid...); on
           a web service the known unique names (gml_id, cleabs, id...)
        3. "$id": the QGIS feature id (OGR SQL fid, QGIS expression $id;
           refused on a web service / virtual layer by _key_list_refusal)

        The first integer field is no key: ``"population" IN (...)`` kept every
        feature sharing a population with a selected one.

        Args:
            layer: QGIS vector layer

        Returns:
            Primary key field name
        """
        try:
            choice = stable_key(layer)
            if choice.is_field:
                self.log_debug(f"Primary key of {layer.name()}: {choice.name} ({choice.origin})")
                return choice.name
        except Exception as e:
            self.log_warning(f"Error detecting primary key: {e}")
        return FEATURE_ID_KEY

    def _is_geometric_filter(self, subset: str) -> bool:
        """Whether ``subset`` holds a spatial predicate (2026-10-17: function calls, not substrings).

        ``"st_code" = 3`` or ``"name" LIKE '%contains%'`` used to count as
        geometric (``st_`` / ``contains`` substrings) and were replaced.
        """
        return bool(_GEOMETRIC_FILTER_RE.search(subset or ''))


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'OGRExpressionBuilder',
    'CancellableFeedback',
]

"""
EPIC-1 Phase E6: Task completion handler for FilterTask.

Extracted from filter_task.py finished() method to reduce complexity.
This module handles post-task operations like subset application and canvas refresh.
"""

import logging
from typing import List, Tuple, Optional, Any, Callable

from qgis.core import QgsMessageLog, Qgis, QgsProject
from qgis.utils import iface
from qgis.PyQt.QtCore import QCoreApplication, QTimer

from ...core.ports.qgis_port import get_qgis_factory
from ...infrastructure.signal_utils import SignalBlocker

try:
    from ...infrastructure.perf_timer import perf_mark_start, perf_mark_end
except ImportError:  # stubbed package in the handler test suite
    def perf_mark_start(name):  # noqa: D103 - no-op fallback
        return None

    def perf_mark_end(name, details=None):  # noqa: D103 - no-op fallback
        return None
from ...infrastructure.constants import (
    QGIS_PROVIDER_POSTGRES, QGIS_PROVIDER_SPATIALITE,
    QGIS_PROVIDER_MEMORY,
)

logger = logging.getLogger(__name__)

# Import centralized validation (v4.0.4 - eliminate duplication)
try:
    from ...infrastructure.utils import is_layer_valid as is_valid_layer
except ImportError:
    # Fallback for testing or import issues
    def is_valid_layer(layer: Any) -> bool:
        """Check if layer is valid and accessible (fallback)."""
        if layer is None:
            return False
        try:
            return hasattr(layer, 'isValid') and layer.isValid() and hasattr(layer, 'id')
        except RuntimeError:
            return False


def display_warning_messages(warning_messages: List[str]) -> None:
    """
    Display warning messages stored during worker thread execution.

    These warnings could not be displayed from worker thread due to
    Qt thread safety requirements.

    Args:
        warning_messages: List of warning message strings to display
    """
    if not warning_messages:
        return

    for warning_msg in warning_messages:
        try:
            iface.messageBar().pushWarning("FilterMate", warning_msg)
        except (RuntimeError, AttributeError) as e:
            logger.warning(f"Could not display warning: {e}")


def should_skip_subset_application(
    is_canceled: bool,
    has_pending_requests: bool,
    pending_requests: List,
    result: Optional[bool]
) -> bool:
    """
    Determine if pending subset requests should be skipped.

    Args:
        is_canceled: Whether task.isCanceled() is True
        has_pending_requests: Whether there are pending requests
        pending_requests: The actual pending requests list
        result: The task result (True/False/None)

    Returns:
        bool: True if subset application should be skipped
    """
    # v3.0.8: Only skip if TRULY canceled (not just marked as canceled)
    # Check if we have pending requests AND if the task actually returned False (failed)
    # If the task succeeded (result=True), we should still apply the subsets even if
    # isCanceled() returns True (which can happen due to race conditions in QGIS)
    truly_canceled = (
        is_canceled and
        not (has_pending_requests and pending_requests and result is not False)
    )

    return truly_canceled and has_pending_requests and not pending_requests


def _layer_database_path(layer: Any) -> Optional[str]:
    """Return the on-disk SQLite/GeoPackage file backing this layer (or None).

    Mirrors :meth:`ParallelFilterExecutor._get_layer_database_path` so the
    same single-writer locking heuristics can be applied here. Recognised
    extensions: .gpkg, .sqlite, .db, .spatialite. Returned path is
    lowercased for case-insensitive equality on Windows/WSL.
    """
    try:
        if not hasattr(layer, 'source'):
            return None
        source = layer.source()
        if not source:
            return None

        file_path: Optional[str] = None
        if '|' in source:
            file_path = source.split('|')[0]
        elif "dbname='" in source:
            import re
            match = re.search(r"dbname='([^']+)'", source)
            if match:
                file_path = match.group(1)
        elif 'dbname="' in source:
            import re
            match = re.search(r'dbname="([^"]+)"', source)
            if match:
                file_path = match.group(1)
        else:
            file_path = source

        if file_path:
            lower = file_path.lower()
            if lower.endswith(('.gpkg', '.sqlite', '.db', '.spatialite')):
                return lower
        return None
    except (RuntimeError, AttributeError):
        return None


_SQLITE_LOCK_ERROR_MARKERS = ('unable to open database file', 'database is locked', 'sqlite3_step')


def _is_sqlite_lock_error(layer: Any) -> bool:
    """True when the provider's last error is the SQLite file-lock signature."""
    try:
        error = layer.error()
        message = error.message() if error is not None and hasattr(error, 'message') else str(error or '')
    except (RuntimeError, AttributeError):
        return False
    lowered = (message or '').lower()
    return any(marker in lowered for marker in _SQLITE_LOCK_ERROR_MARKERS)


def _freeze_canvas(request_count: int):
    """Freeze the map canvas while several subsets are applied (PERF 2026-09-12).

    A frozen canvas issues no redraw between two setSubsetString/reload calls,
    which is what used to trigger ``sqlite3_step(): unable to open database
    file`` on layers sharing one SQLite file, and it turns N repaints into one.
    Returns the canvas to unfreeze, or None.
    """
    if request_count < 2 or iface is None:
        return None
    try:
        canvas = iface.mapCanvas()
        if canvas is None:
            return None
        # A render job still running for the previous subsets (e.g. the whole
        # dataset after an unfilter) holds the layers' data sources; the first
        # setSubsetString/reload of the loop waited 44 s for it on a 1.2 M-row
        # GeoPackage layer. That render is obsolete: cancel it first.
        canvas.stopRendering()
        if bool(canvas.isFrozen()):
            # Frozen by whoever launched the task (FilterMateApp freezes the
            # canvas for the whole task): that owner thaws and refreshes once
            # at the end, this loop must not do it halfway through.
            return None
        canvas.freeze(True)
        return canvas
    except (RuntimeError, AttributeError) as e:
        logger.debug(f"Could not freeze canvas: {e}")
        return None


def _unfreeze_canvas(canvas) -> None:
    if canvas is None:
        return
    try:
        canvas.freeze(False)
        canvas.refresh()
    except (RuntimeError, AttributeError) as e:
        logger.debug(f"Could not unfreeze canvas: {e}")


def _extent_fallback():
    """The module holding the cuts by extent left for refused filters; None where it cannot be loaded."""
    try:
        from ...adapters.qgis import extent_fallback
        return extent_fallback
    except Exception:  # a filter is set whatever happens to this lookup
        return None


def _say_cut_by_extent(layer: Any, subset: str) -> None:
    """Tell that a web service refused its exact filter and was cut by the extent of the source instead."""
    try:
        from ...adapters.backends.ogr.filter_executor import _remote_message
        from ...adapters.qgis.remote_materializer import mark_partial_result
        mark_partial_result(layer, False, subset)  # the server answers every feature of the extent
        from ...adapters.qgis.remote_materializer import mark_extent_result
        from ...core.domain.source_capability import extent_subset_in
        mark_extent_result(layer, extent_subset_in(subset))
        message = f"{layer.name()}: {_remote_message('by_extent_refused')}"
        logger.warning(f"  ↪ {message}")
        iface.messageBar().pushWarning("FilterMate", message)
    except (ImportError, RuntimeError, AttributeError) as exc:
        logger.warning(f"Cut by extent not reported: {exc}")


class _NoWatch:
    """Stand-in when the watch cannot be loaded: the reason is whatever the layer says."""

    def __init__(self, layer: Any):
        self._layer = layer

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def reason(self) -> str:
        try:
            error = self._layer.error()
            message = error.message() if error is not None else ''
        except (RuntimeError, AttributeError):
            message = ''
        try:
            from ...adapters.qgis.server_filter_translation import last_server_filter_error
            message = last_server_filter_error(self._layer) or message
        except Exception as exc:  # catch-all safety net: the reason must not break the apply loop
            logger.debug(f"Web service error not read: {exc}")
        return message if isinstance(message, str) and message.strip() else 'Unknown error'


def _note_refused(refusals: Optional[List[Tuple[str, str, str]]], layer: Any, reason: str) -> None:
    """Add (id, name, reason) of a layer whose filter was refused (a deleted layer: no id)."""
    if refusals is None:
        return
    try:
        layer_id, name = (layer.id(), layer.name()) if layer is not None else ('', 'Unknown')
    except (RuntimeError, AttributeError):
        layer_id, name = '', 'Unknown'
    refusals.append((layer_id, name, reason))


def _invalid_layer_reason() -> str:
    """The reason of a filter not set on an invalid layer (a message already translated, reused)."""
    return QCoreApplication.translate(
        "FilterApplicationService", "Layer is invalid or its source cannot be found. Operation cancelled.")


def _note_invalid_layer(failures: Optional[List[str]], refusals: Optional[List[Tuple[str, str, str]]],
                        layer: Any) -> None:
    """A layer invalid when its subset was to be set: a refusal, logged."""
    reason = _invalid_layer_reason()
    try:
        name = layer.name() if layer is not None else 'Unknown'
    except (RuntimeError, AttributeError):
        name = 'Unknown'
    logger.warning(f"  ✗ Filter not set, layer invalid: {name}")
    if failures is not None:
        failures.append(f"{name}: {reason}")
    _note_refused(refusals, layer, reason)


def _subset_failure_watch(layer: Any):
    """A SubsetFailureWatch for the layer (see adapters/qgis/subset_failure_reason.py)."""
    try:
        from ...adapters.qgis.subset_failure_reason import SubsetFailureWatch
        return SubsetFailureWatch(layer)
    except Exception as exc:  # catch-all safety net: the filter is applied whatever happens to the watch
        logger.debug(f"Subset failure watch unavailable: {exc}")
        return _NoWatch(layer)


def apply_pending_subset_requests(
    pending_requests: List[Tuple[Any, str]],  # List[Tuple[QgsVectorLayer, str]]
    safe_set_subset_fn: Callable[[Any, str], bool],  # Callable[[QgsVectorLayer, str], bool]
    failures: Optional[List[str]] = None,
    refusals: Optional[List[Tuple[str, str, str]]] = None,
    deferred: Optional[List[str]] = None,
    on_deferred_done: Optional[Callable[[List[Tuple[str, str, str]]], None]] = None,
) -> int:
    """
    Apply pending subset string requests on main thread.

    This is called from the main Qt thread (unlike run() which is on a worker thread).
    Fully extracted from FilterTask.finished() in Phase E6.

    Args:
        pending_requests: List of (layer, expression) tuples
        safe_set_subset_fn: Function to safely set subset string
        failures: When given, receives one "<layer>: <error>" line per filter
            the provider refused (2026-10-17: shown in the message bar
            instead of a silent success)
        refusals: When given, receives (layer id, layer name, reason) per refused
            filter (2026-11-16: its filter history is put back, the warning groups
            the layers by reason)
        deferred: When given, receives the id of each layer whose subset (over 1 MB)
            is set later, out of this call (2026-11-18)
        on_deferred_done: Called once those subsets are set, with the (layer id, layer
            name, reason) of those refused (2026-11-18)

    Returns:
        int: Number of successfully applied filters
    """
    if not pending_requests:
        return 0

    # DEDUP FIX 2026-04-21: defensive dedup on (layer_id, expression) at apply time.
    # Upstream queueing already dedups, but a second guard avoids noisy double-apply
    # when multiple code paths feed the same request.
    seen_keys = set()
    deduped_requests: List[Tuple[Any, str]] = []
    for layer, expression in pending_requests:
        try:
            key = (layer.id() if layer is not None else None, expression)
        except (RuntimeError, AttributeError):
            key = (None, expression)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_requests.append((layer, expression))

    if len(deduped_requests) != len(pending_requests):
        logger.debug(
            f"Deduped subset requests: {len(pending_requests)} -> {len(deduped_requests)}"
        )
    pending_requests = deduped_requests

    QgsMessageLog.logMessage(
        f"📥 Applying {len(pending_requests)} pending subset requests on main thread",
        "FilterMate", Qgis.MessageLevel.Info
    )
    logger.info(f"finished(): Applying {len(pending_requests)} pending subset requests on main thread")
    perf_mark_start("apply_subsets")

    # Log all pending requests details — promoted to QGIS log panel 2026-04-29
    # so the user can see exactly what subset is being applied per cascade
    # target. Without this it was impossible to distinguish "no subset queued"
    # from "empty subset queued" from "valid subset queued but rejected by
    # provider"; the previous DEBUG-level message only landed in the Python
    # console which most users don't have open.
    for idx, (lyr, expr) in enumerate(pending_requests):
        lyr_name = lyr.name() if lyr and is_valid_layer(lyr) else "INVALID"
        expr_preview = (expr[:120] + '...') if expr and len(expr) > 120 else (expr or 'EMPTY')
        logger.debug(f"  [{idx + 1}] {lyr_name}: {expr_preview}")
        QgsMessageLog.logMessage(
            f"  [{idx + 1}/{len(pending_requests)}] {lyr_name}: {expr_preview}",
            "FilterMate", Qgis.MessageLevel.Info
        )

    # Performance thresholds
    MAX_FEATURES_FOR_UPDATE_EXTENTS = 50000
    # 2026-09-13: raised from 100 KB to 1 MB. A buffered Spatialite source
    # now yields ~150 KB subset strings, and the deferred path applied all 36
    # layers outside the frozen canvas with a repaint and a full count each
    # (4.6 s of post-filter UI work).
    MAX_EXPRESSION_FOR_DIRECT_APPLY = 1_000_000  # 1 MB

    # 2026-04-29: count layers per shared SQLite file so we can throttle
    # consecutive setSubsetString+reload+featureCount calls. Without the
    # throttle, an 8-layers-from-the-same-server.sqlite cascade triggers
    # ``OGR error: sqlite3_step(): unable to open database file`` during
    # the redraw that follows each apply, and featureCount() returns the
    # stale pre-filter count — the cascade looks like a no-op even though
    # the subset string is correctly set.
    db_layer_counts: dict = {}
    for layer, _ in pending_requests:
        if layer is None:
            continue
        db_path = _layer_database_path(layer)
        if db_path:
            db_layer_counts[db_path] = db_layer_counts.get(db_path, 0) + 1

    # Collect large expressions for deferred application
    large_expressions = []
    applied_count = 0
    last_db_path: Optional[str] = None

    canvas = _freeze_canvas(len(pending_requests))

    import time as _perf_time

    for layer, expression in pending_requests:
        layer_started = _perf_time.perf_counter()
        phase_details = ''
        # 2026-11-18: the subset is on the layer (set now or already there): what fails after it
        # (reload, repaint) is no refusal (its history was put back, "previous filter kept" said).
        in_place = False
        try:

            if not layer or not is_valid_layer(layer):
                QgsMessageLog.logMessage(
                    f"finished() ✗ Layer invalid: {layer.name() if layer else 'None'}",
                    "FilterMate", Qgis.MessageLevel.Warning
                )
                # 2026-11-18: noted as refused (its filter is not set, its history goes back): skipped
                # in silence, a task whose layers were all invalid said "Layer(s) filtered".
                _note_invalid_layer(failures, refusals, layer)
                continue

            # PERF 2026-09-12: the fixed 0.2-0.5 s pause between layers of the
            # same SQLite file (2026-04-29) is gone. Its purpose was to let the
            # redraw triggered by the previous apply release the file before the
            # next setSubsetString+reload; the canvas is now frozen for the whole
            # loop (no redraw at all), and a lock error is retried once below.
            current_db_path = _layer_database_path(layer)
            shares_file = bool(current_db_path and current_db_path == last_db_path)

            current_subset = layer.subsetString() or ''
            expression_str = expression or ''

            # Check if expression is too large for direct application
            if expression_str and len(expression_str) > MAX_EXPRESSION_FOR_DIRECT_APPLY:
                logger.warning(f"  ⚠️ Large expression ({len(expression_str)} chars) for {layer.name()} - deferring")
                large_expressions.append((layer, expression_str))
                continue

            # Check if filter already applied
            if current_subset.strip() == expression_str.strip():
                in_place = True
                # Filter already applied. PERF 2026-09-12: same rules as a new
                # filter below - no reload() on PostgreSQL/OGR (a reload reopens
                # a GeoPackage and forces a full recount), reload kept on
                # Spatialite for non-empty subsets (FIX 2026-01-24), and the
                # count only where the provider already holds it.
                if layer.providerType() == QGIS_PROVIDER_SPATIALITE and expression_str.strip() != '':
                    with SignalBlocker(layer):
                        layer.reload()

                # Update extents for smaller layers
                if layer.providerType() == QGIS_PROVIDER_POSTGRES:
                    feature_count = -1
                else:
                    from ...adapters.qgis.source_capability_probe import feature_count_or_none
                    feature_count = feature_count_or_none(layer)
                if feature_count is not None and feature_count >= 0 and feature_count < MAX_FEATURES_FOR_UPDATE_EXTENTS:
                    try:
                        layer.updateExtents()
                    except (RuntimeError, AttributeError):
                        pass

                layer.triggerRepaint()

                # FIX v2.9.24: Clear selection for Spatialite layers after reload
                if layer.providerType() == QGIS_PROVIDER_SPATIALITE:
                    try:
                        layer.removeSelection()
                        logger.debug("Cleared selection after Spatialite filter (already applied)")
                    except (RuntimeError, AttributeError) as sel_err:
                        logger.debug(f"Could not clear selection: {sel_err}")

                count_str = f"{feature_count} features" if feature_count is not None and feature_count >= 0 else "(count pending)"
                logger.debug(f"  ✓ Filter already applied to {layer.name()}, triggered reload+repaint")
                QgsMessageLog.logMessage(
                    f"finished() ✓ Repaint: {layer.name()} → {count_str} (filter already applied)",
                    "FilterMate", Qgis.MessageLevel.Info
                )
                applied_count += 1
            else:
                set_started = _perf_time.perf_counter()
                # 2026-11-16: keeps what the provider says during the attempts, for the
                # reason of a refusal (layer.error() is empty when the server is gone).
                watch = _subset_failure_watch(layer)
                with watch:
                    # Apply new filter
                    success = safe_set_subset_fn(layer, expression_str)
                    if not success and shares_file and _is_sqlite_lock_error(layer):
                        # The previous layer's provider still holds the file: give it
                        # a moment and retry once (replaces the blind pause of old).
                        import time as _time
                        _time.sleep(0.3)
                        success = safe_set_subset_fn(layer, expression_str)
                    in_place = bool(success)

                    extent_fallback = _extent_fallback()
                    if success and extent_fallback is not None:
                        extent_fallback.forget(layer.id())
                    elif extent_fallback is not None:
                        # 2026-11-15: a web service refused the keys of an exact filter (their address is too long
                        # for it, far under 500 keys on a real WFS). The cut by the extent of the source left for
                        # that case is set instead, and said: the layer is filtered, not left whole with an error.
                        by_extent = extent_fallback.take(layer.id(), expression_str)
                        if by_extent and safe_set_subset_fn(layer, by_extent):
                            success = in_place = True
                            expression_str = by_extent
                            _say_cut_by_extent(layer, by_extent)

                set_ms = (_perf_time.perf_counter() - set_started) * 1000.0
                phase_details = f", set {set_ms:.0f} ms"
                if success:
                    # PERF 2026-09-12: no reload() after a successful setSubsetString. The
                    # provider already emits dataChanged; on OGR/GeoPackage the reload
                    # reopened the dataset and dropped the count QGIS had just computed, so
                    # featureCount() ran the filter a second time (164 s of the 371 s
                    # Toulouse cascade were the second scan of `batiment`). Spatialite keeps
                    # its reload for non-empty subsets (FIX 2026-01-24, unmeasured).
                    if layer.providerType() == QGIS_PROVIDER_SPATIALITE and expression_str.strip() != '':
                        with SignalBlocker(layer):
                            layer.reload()
                    # The count is free on OGR (computed inside setSubsetString) and a real
                    # COUNT query with the spatial predicate on PostgreSQL: only ask for it
                    # when the provider already holds it.
                    count_started = _perf_time.perf_counter()
                    if layer.providerType() == QGIS_PROVIDER_POSTGRES:
                        feature_count = -1
                    else:
                        from ...adapters.qgis.source_capability_probe import feature_count_or_none
                        feature_count = feature_count_or_none(layer)
                    count_ms = (_perf_time.perf_counter() - count_started) * 1000.0
                    phase_details = f", set {set_ms:.0f} ms, count {count_ms:.0f} ms"
                    # Update extents for smaller layers
                    if feature_count is not None and feature_count >= 0 and feature_count < MAX_FEATURES_FOR_UPDATE_EXTENTS:
                        try:
                            layer.updateExtents()
                        except (RuntimeError, AttributeError):
                            pass
                    layer.triggerRepaint()

                    # FIX v2.9.24: Clear selection for Spatialite layers
                    if layer.providerType() == QGIS_PROVIDER_SPATIALITE:
                        try:
                            layer.removeSelection()
                            logger.debug("Cleared selection after Spatialite filter (new filter)")
                        except (RuntimeError, AttributeError) as sel_err:
                            logger.debug(f"Could not clear selection: {sel_err}")

                    logger.debug(f"  ✓ Applied filter to {layer.name()}: {len(expression_str)} chars")

                    # Handle feature count and logging (PERF 2026-09-12: reuse the
                    # count computed above instead of asking the provider again)
                    if feature_count is None:
                        feature_count = -1
                    if feature_count >= 0:
                        QgsMessageLog.logMessage(
                            f"✓ Filter APPLIED: {layer.name()} → {feature_count} features",
                            "FilterMate", Qgis.MessageLevel.Info
                        )
                        # Diagnostic for layers with 0 features
                        if feature_count == 0:
                            logger.warning(f"  ⚠️ Layer {layer.name()} has 0 features after filtering!")
                            logger.warning(f"    → Expression length: {len(expression_str)} chars")
                            QgsMessageLog.logMessage(
                                f"⚠️ {layer.name()} → 0 features (filter may be too restrictive)",
                                "FilterMate", Qgis.MessageLevel.Warning
                            )
                    else:
                        QgsMessageLog.logMessage(
                            f"✓ Filter APPLIED: {layer.name()} → (count pending)",
                            "FilterMate", Qgis.MessageLevel.Info
                        )

                    applied_count += 1
                else:
                    # Enhanced diagnostic for failed filters
                    error_msg = watch.reason()
                    logger.warning(f"  ✗ Failed to apply filter to {layer.name()}")
                    logger.warning(f"    → Error: {error_msg}")
                    logger.warning(f"    → Expression ({len(expression_str)} chars): {expression_str[:200]}...")
                    logger.warning(f"    → Provider: {layer.providerType()}")
                    QgsMessageLog.logMessage(
                        f"finished() ✗ FAILED: {layer.name()} - {error_msg}",
                        "FilterMate", Qgis.MessageLevel.Critical
                    )
                    if failures is not None:
                        failures.append(f"{layer.name()}: {error_msg}")
                    _note_refused(refusals, layer, error_msg)

        except Exception as e:  # catch-all safety net: subset application must not crash finished()
            import traceback
            if in_place:
                # Counted where the branch ends, which the exception skipped
                logger.warning(f"  ⚠️ Subset set, but the refresh after it failed: {e}")
                logger.debug(f"    → Traceback: {traceback.format_exc()}")
                applied_count += 1
            else:
                logger.error(f"  ✗ Error applying subset string: {e}")
                logger.error(f"    → Traceback: {traceback.format_exc()}")
                QgsMessageLog.logMessage(
                    f"finished() ✗ Exception: {layer.name() if layer else 'Unknown'} - {str(e)}",
                    "FilterMate", Qgis.MessageLevel.Critical
                )
                if failures is not None:
                    failures.append(f"{layer.name() if layer else 'Unknown'}: {e}")
                _note_refused(refusals, layer, str(e))

        # Track last-touched DB path so the next iteration knows whether the
        # lock-error retry applies (same shared SQLite file).
        if layer is not None:
            db_path_after = _layer_database_path(layer)
            if db_path_after:
                last_db_path = db_path_after
            layer_ms = (_perf_time.perf_counter() - layer_started) * 1000.0
            if layer_ms >= 250:
                try:
                    logger.info(f"⏱ apply_subset_layer: {layer_ms:.0f} ms ({layer.name()}{phase_details})")
                except (RuntimeError, AttributeError):
                    logger.info(f"⏱ apply_subset_layer: {layer_ms:.0f} ms")

    _unfreeze_canvas(canvas)

    # Handle large expressions with deferred application
    if large_expressions:
        logger.info(f"  📦 Applying {len(large_expressions)} large expressions with deferred processing")
        if deferred is not None:
            for lyr, _expr in large_expressions:
                try:
                    deferred.append(lyr.id())
                except (RuntimeError, AttributeError):
                    deferred.append('')
        _schedule_deferred_filter_application(large_expressions, safe_set_subset_fn, on_done=on_deferred_done)

    perf_mark_end("apply_subsets", f"{applied_count} layer(s) on the main thread")
    return applied_count


def _schedule_deferred_filter_application(
    large_expressions: List[Tuple[Any, str]],  # List[Tuple[QgsVectorLayer, str]]
    safe_set_subset_fn: Callable[[Any, str], bool],  # Callable[[QgsVectorLayer, str], bool]
    on_done: Optional[Callable[[List[Tuple[str, str, str]]], None]] = None,
) -> None:
    """
    Schedule deferred application of large filter expressions.

    This allows the UI to remain responsive during large filter application.

    Args:
        large_expressions: List of (layer, expression) tuples with large expressions
        safe_set_subset_fn: Function to safely set subset string
        on_done: Called at the end with the (layer id, layer name, reason) of the
            refused filters (2026-11-18: their history is put back, the views they
            read kept, as for the filters set in the loop)
    """
    def apply_deferred_filters():
        """Apply large filter expressions with UI breathing room."""
        refused: List[Tuple[str, str, str]] = []
        for lyr, expr in large_expressions:
            in_place = False
            try:
                if lyr and is_valid_layer(lyr):
                    watch = _subset_failure_watch(lyr)
                    with watch:
                        success = safe_set_subset_fn(lyr, expr)
                    in_place = bool(success)
                    reason = '' if success else watch.reason()
                else:
                    # 2026-11-18: invalid by now: refused, as in the loop (it was skipped in silence)
                    success, reason = False, _invalid_layer_reason()
                if success:
                    lyr.triggerRepaint()
                    QgsMessageLog.logMessage(
                        f"finished() ✓ Deferred: {lyr.name()} → (count pending)",
                        "FilterMate", Qgis.MessageLevel.Info
                    )
                else:
                    logger.error(f"Failed to apply deferred filter to {lyr.name()}")
                    _note_refused(refused, lyr, reason)
                    # 2026-10-17: deferred after the task messages: say it here
                    try:
                        iface.messageBar().pushWarning(
                            "FilterMate",
                            QCoreApplication.translate(
                                "TaskCompletionHandler", "The filter of {0} could not be applied; it keeps its previous filter."
                            ).format(lyr.name())
                        )
                    except (RuntimeError, AttributeError):
                        pass
            except (RuntimeError, AttributeError, ValueError) as e:
                logger.error(f"Error applying deferred filter: {e}")
                if not in_place:
                    _note_refused(refused, lyr, str(e))

        # Final canvas refresh
        try:
            iface.mapCanvas().refresh()
        except (RuntimeError, AttributeError):
            pass

        if on_done is not None:
            try:
                on_done(refused)
            except Exception as e:  # catch-all safety net: a timer slot must not raise
                logger.warning(f"End of the deferred filters not handled: {e}")

    # Defer to allow UI to breathe
    QTimer.singleShot(100, apply_deferred_filters)


def schedule_canvas_refresh(
    is_complex_filter_fn: Callable[[str, str], bool],
    single_refresh_fn: Callable[[], None]
) -> None:
    """
    Schedule canvas refresh with adaptive timing.

    Uses longer delay for complex filters to allow provider to process.

    Args:
        is_complex_filter_fn: Function to check if filter is complex
        single_refresh_fn: Function to perform single canvas refresh
    """
    try:
        # Stop any ongoing rendering first
        canvas = iface.mapCanvas()
        canvas.stopRendering()
        canvas.refresh()
        logger.debug("Immediate canvas refresh triggered after filter application (with stopRendering)")
    except (RuntimeError, AttributeError) as refresh_err:
        logger.debug(f"Could not trigger immediate canvas refresh: {refresh_err}")

    try:
        # Check if any filter is complex
        has_complex_filter = False
        # FIX 2026-01-15: Use QgsProject.instance() directly instead of factory.get_project()
        # The QGISFactory doesn't have a get_project() method
        project = QgsProject.instance()
        for layer_id, layer in project.mapLayers().items():
            if layer.type() == 0:  # Vector layer
                subset = layer.subsetString() or ''
                if subset and is_complex_filter_fn(subset, layer.providerType()):
                    has_complex_filter = True
                    break

        # Use longer delay for complex filters (configurable via APP.OPTIONS.UI_RESPONSIVENESS)
        try:
            from ...config.config import ENV_VARS
            _ui_resp = ENV_VARS.get('CONFIG_DATA', {}).get('APP', {}).get('OPTIONS', {}).get('UI_RESPONSIVENESS', {})
            _complex = _ui_resp.get('canvas_refresh_delay_complex_ms', {})
            _simple = _ui_resp.get('canvas_refresh_delay_simple_ms', {})
            delay_complex = _complex.get('value', 1500) if isinstance(_complex, dict) else 1500
            delay_simple = _simple.get('value', 500) if isinstance(_simple, dict) else 500
        except (ImportError, AttributeError, TypeError):
            delay_complex, delay_simple = 1500, 500
        refresh_delay = delay_complex if has_complex_filter else delay_simple

        # Schedule single comprehensive refresh
        QTimer.singleShot(refresh_delay, single_refresh_fn)
        logger.debug(f"Scheduled single canvas refresh in {refresh_delay}ms (complex={has_complex_filter})")

    except (RuntimeError, AttributeError) as canvas_err:
        logger.warning(f"Failed to schedule canvas refresh: {canvas_err}")
        # Fallback: immediate refresh
        try:
            iface.mapCanvas().refresh()
        except (RuntimeError, AttributeError):
            pass


def cleanup_memory_layer(ogr_source_geom: Optional[Any]) -> None:  # Optional[QgsVectorLayer]
    """
    Cleanup memory layer added to project to prevent garbage collection issues.

    Args:
        ogr_source_geom: The OGR source geometry layer to cleanup
    """
    if ogr_source_geom is None:
        return

    try:
        if ogr_source_geom.isValid() and ogr_source_geom.providerType() == QGIS_PROVIDER_MEMORY:
            # Check if layer is in project
            factory = get_qgis_factory()
            project = factory.get_project()
            if project.map_layer(ogr_source_geom.id()):
                logger.debug("finished(): Removing OGR source memory layer from project")
                project.remove_map_layer(ogr_source_geom.id())
    except (RuntimeError, AttributeError) as e:
        logger.debug(f"Could not cleanup memory layer: {e}")

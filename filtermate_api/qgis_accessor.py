"""
QGIS-backed FilterMateAccessor — issue #45.

Bridges the standalone REST API to the running FilterMate QGIS plugin
by delegating each accessor method to:

* :class:`FilterMatePublicAPI` for ``apply_filter`` / ``get_active_filters``
  (the contract documented at #13).
* :class:`HistoryService` (the same instance shared with the legacy plugin
  via ``adapters.app_bridge.get_history_service`` after #41 M4) for the
  undo/redo stack.
* :class:`FavoritesService` (mounted on the plugin instance) for
  favorite listing and apply.
* ``QgsProject.instance().mapLayers()`` for the layer enumeration.

The class is import-light: no Qt/QGIS imports at module top-level so it
can be loaded under the headless test harness. QGIS only enters the
picture when methods run, and any QGIS access is wrapped in a defensive
try/except so a misconfigured plugin doesn't bring the API down.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .accessor import (
    Favorite,
    FilterStatus,
    HistoryStep,
    LayerSummary,
)
from .main_thread import run_on_main_thread


def _safe(callable_, default):
    """Call ``callable_()`` and return ``default`` on any exception.

    Used to wrap QGIS accessors that might fail when the project is in
    an unusual state — the REST API should never 500 because a layer
    has no CRS or a fields() call exploded.
    """
    try:
        return callable_()
    except Exception:
        return default


class QGISFilterMateAccessor:
    """Production accessor backed by a running FilterMate plugin instance.

    Construct from inside the plugin once everything is wired::

        accessor = QGISFilterMateAccessor(
            public_api=plugin.get_public_api(),
            plugin=plugin,
        )
        app = create_app(config=APIConfig.load(), accessor=accessor)
        # ... start uvicorn in a QThread, see #45 acceptance criteria.

    The ``plugin`` argument exposes the plugin singleton so the bridge
    can reach :attr:`history_manager` and :attr:`favorites_manager` —
    these aren't on the public API surface today (#13 EPIC scoped them
    out), but the bridge is plugin-internal so reaching in is fine.
    """

    def __init__(self, public_api, plugin):
        self._public_api = public_api
        self._plugin = plugin
        # Track last-apply metadata locally so /filters/status can report
        # ``last_applied_at`` / ``last_applied_source``. The PublicAPI
        # doesn't expose this — it emits a Qt signal we can't easily tap
        # from outside Qt's event loop.
        self._last_applied_at: Optional[str] = None
        self._last_applied_layer: Optional[str] = None
        self._last_applied_source: Optional[str] = None
        self._last_error: Optional[str] = None

    # ------------------------------------------------------------------
    # Layer enumeration
    # ------------------------------------------------------------------

    def list_layers(self) -> List[LayerSummary]:
        """Return all valid vector layers in the current QgsProject."""
        try:
            from qgis.core import QgsProject, QgsVectorLayer
        except ImportError:
            # Bridge running outside QGIS — fail soft with empty list.
            return []

        project = QgsProject.instance()
        active_filters = self.get_active_filters()

        out: List[LayerSummary] = []
        for layer in project.mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue
            if not _safe(layer.isValid, False):
                continue

            name = _safe(layer.name, "")
            subset = _safe(layer.subsetString, "") or ""
            geom_type_int = _safe(layer.geometryType, -1)
            crs_obj = _safe(layer.crs, None)
            crs_authid = _safe(crs_obj.authid, "") if crs_obj else ""

            out.append(
                LayerSummary(
                    layer_id=_safe(layer.id, ""),
                    name=name,
                    provider_type=_safe(layer.providerType, ""),
                    feature_count=_safe(layer.featureCount, -1),
                    geometry_type=_GEOMETRY_TYPE_NAMES.get(geom_type_int, "Unknown"),
                    crs_authid=crs_authid,
                    has_active_filter=bool(subset and subset.strip()),
                    active_filter_expression=active_filters.get(name, subset),
                )
            )
        return out

    # ------------------------------------------------------------------
    # Filter mutations — delegated to the PublicAPI
    # ------------------------------------------------------------------

    def apply_filter(self, layer_name: str, expression: str, source: str) -> bool:
        # P0-B (audit 2026-04-29): ``PublicAPI.apply_filter`` ultimately
        # calls ``QgsVectorLayer.setSubsetString`` which is not
        # thread-safe outside the Qt main thread. ``uvicorn`` runs us
        # on a worker, so we marshal the call through the main-thread
        # dispatcher; under the headless test harness this is a no-op
        # inline call.
        ok = run_on_main_thread(
            self._public_api.apply_filter,
            layer_name=layer_name,
            filter_expr=expression,
            source_plugin=source,
        )
        if ok:
            self._last_applied_at = datetime.now(timezone.utc).isoformat()
            self._last_applied_layer = layer_name
            self._last_applied_source = source
            self._last_error = None
        else:
            self._last_error = f"apply_filter({layer_name!r}) returned False"
        return ok

    def get_active_filters(self) -> Dict[str, str]:
        return _safe(self._public_api.get_active_filters, {}) or {}

    def get_filter_status(self) -> FilterStatus:
        active = self.get_active_filters()
        return FilterStatus(
            status="error" if self._last_error else ("completed" if active else "idle"),
            active_filters=active,
            active_filters_count=len(active),
            last_applied_at=self._last_applied_at,
            last_applied_layer=self._last_applied_layer,
            last_applied_source=self._last_applied_source,
            last_error=self._last_error,
        )

    # ------------------------------------------------------------------
    # Undo / redo — delegated to the shared HistoryService
    # ------------------------------------------------------------------

    def undo_filter(self) -> Optional[HistoryStep]:
        return self._step_via_history(self._history_undo, direction="undo")

    def redo_filter(self) -> Optional[HistoryStep]:
        return self._step_via_history(self._history_redo, direction="redo")

    # ------------------------------------------------------------------
    # Favorites — delegated to FavoritesService
    # ------------------------------------------------------------------

    def list_favorites(self) -> List[Favorite]:
        favorites_service = getattr(self._plugin, "favorites_manager", None)
        if favorites_service is None:
            return []
        try:
            entries = favorites_service.get_all_favorites() or []
        except Exception:
            return []
        return [self._favorite_from(entry) for entry in entries]

    def apply_favorite(self, favorite_id: str) -> Optional[HistoryStep]:
        favorites_service = getattr(self._plugin, "favorites_manager", None)
        if favorites_service is None:
            return None
        try:
            entry = favorites_service.get_favorite(favorite_id)
        except Exception:
            return None
        if entry is None:
            return None
        layer_name = getattr(entry, "layer_name", "") or ""
        expression = getattr(entry, "expression", "") or ""
        if not layer_name or not expression:
            return None
        ok = self.apply_filter(
            layer_name=layer_name,
            expression=expression,
            source=f"favorite:{favorite_id}",
        )
        if not ok:
            return None
        return HistoryStep(layer_name=layer_name, expression=expression)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _history_service(self):
        return getattr(self._plugin, "history_manager", None)

    def _history_undo(self):
        svc = self._history_service()
        return svc.undo() if svc is not None and hasattr(svc, "undo") else None

    def _history_redo(self):
        svc = self._history_service()
        return svc.redo() if svc is not None and hasattr(svc, "redo") else None

    def _step_via_history(self, action, direction: str) -> Optional[HistoryStep]:
        """Run ``action`` (HistoryService.undo/redo) and re-apply the resulting
        entry's previous filters back to QGIS layers.

        Returns a :class:`HistoryStep` describing the layer most affected
        by the operation, or ``None`` when the stack is empty.
        """
        entry = action()
        if entry is None:
            return None

        try:
            from qgis.core import QgsProject
            project = QgsProject.instance()
        except ImportError:
            project = None

        previous_filters = getattr(entry, "previous_filters", ()) or ()

        # P0-B (audit 2026-04-29): ``setSubsetString`` is not thread-safe
        # outside the Qt main thread. Batch all subset writes into a
        # single main-thread roundtrip rather than N round-trips.
        target_layer_name, target_expression, target_is_clear = run_on_main_thread(
            self._reapply_previous_filters_inline,
            project,
            previous_filters,
        )

        # If we couldn't reach any layer (no project / layer ids missing),
        # fall back to the entry's own metadata so the API still answers.
        if not target_layer_name:
            target_expression = getattr(entry, "expression", "") or ""
            target_is_clear = not target_expression
            target_layer_name = (
                getattr(entry, "layer_ids", ("",))[0]
                if getattr(entry, "layer_ids", None)
                else ""
            )

        return HistoryStep(
            layer_name=target_layer_name,
            expression=target_expression,
            is_clear=target_is_clear,
        )

    @staticmethod
    def _reapply_previous_filters_inline(project, previous_filters):
        """Apply ``previous_filters`` to project layers — main-thread only.

        Returns ``(layer_name, expression, is_clear)`` for the *last*
        layer successfully written, mirroring the original loop's
        behaviour. Skips missing layers and individual write failures
        silently because the API contract is "best-effort restoration"
        (the history step is always reported even when the project no
        longer carries every layer it referenced).
        """
        target_layer_name = ""
        target_expression = ""
        target_is_clear = True

        for layer_id, prev_subset in previous_filters:
            layer = project.mapLayer(layer_id) if project is not None else None
            if layer is None:
                continue
            try:
                layer.setSubsetString(prev_subset or "")
            except Exception:
                continue
            target_layer_name = _safe(layer.name, layer_id)
            target_expression = prev_subset or ""
            target_is_clear = not target_expression

        return target_layer_name, target_expression, target_is_clear

    @staticmethod
    def _favorite_from(entry: Any) -> Favorite:
        """Map FavoritesService entries to the API ``Favorite`` DTO."""
        return Favorite(
            favorite_id=str(getattr(entry, "favorite_id", "") or getattr(entry, "id", "")),
            name=str(getattr(entry, "name", "")),
            description=str(getattr(entry, "description", "") or ""),
            layer_name=str(getattr(entry, "layer_name", "") or ""),
            expression=str(getattr(entry, "expression", "") or ""),
        )


# Map QgsWkbTypes.GeometryType ints to the names the API exposes. Kept in
# this module rather than a domain enum because the REST contract is
# string-based (no need to leak QGIS enum values to clients).
_GEOMETRY_TYPE_NAMES: Dict[int, str] = {
    0: "Point",
    1: "LineString",
    2: "Polygon",
    3: "Unknown",
    4: "NoGeometry",
}

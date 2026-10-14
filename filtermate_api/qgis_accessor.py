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
    CrossFilterResult,
    Favorite,
    FavoritesUnavailable,
    FilterStatus,
    HistoryStep,
    LayerSummary,
)
from .main_thread import run_on_main_thread


def _plugin_module(name: str):
    """Import a module of the FilterMate plugin, whatever way the API package was loaded.

    Inside the plugin the API is ``filter_mate.filtermate_api`` (relative
    import); launched by uvicorn it is the top-level ``filtermate_api``.
    """
    import importlib
    for candidate in (f"..{name}", f"filter_mate.{name}", name):
        try:
            if candidate.startswith(".."):
                if not __package__ or "." not in __package__:
                    continue
                return importlib.import_module(candidate, __package__)
            return importlib.import_module(candidate)
        except ImportError:
            continue
    raise ImportError(name)


def _layer_kind(layer) -> str:
    """"vector", "raster", "point_cloud" or "other" (class based, see point_cloud_capability)."""
    try:
        from qgis.core import QgsVectorLayer
        if isinstance(QgsVectorLayer, type) and isinstance(layer, QgsVectorLayer):
            return "vector"
    except ImportError:
        pass
    try:
        return _plugin_module("adapters.qgis.point_cloud_capability").layer_kind_by_class(layer).value
    except Exception:
        return "other"


def _derived_marker(layer) -> str:
    """Short description of a FilterMate clip of a raster / point cloud layer, "" when none."""
    try:
        snapshot = _plugin_module("adapters.qgis.coverage_layers.snapshots").registry().get(layer.id())
    except Exception:
        return ""
    if snapshot is None:
        return ""
    return "filtermate:clip" if snapshot.geometry_wkt else "filtermate:selection"


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
        """Return all valid vector, raster and point cloud layers of the current QgsProject."""
        try:
            from qgis.core import QgsProject, QgsVectorLayer
        except ImportError:
            # Bridge running outside QGIS — fail soft with empty list.
            return []

        project = QgsProject.instance()
        active_filters = self.get_active_filters()

        out: List[LayerSummary] = []
        for layer in project.mapLayers().values():
            kind = "vector" if isinstance(layer, QgsVectorLayer) else _layer_kind(layer)
            if kind not in ("vector", "raster", "point_cloud"):
                continue
            if not _safe(layer.isValid, False):
                continue

            name = _safe(layer.name, "")
            subset = (_safe(layer.subsetString, "") or "") if hasattr(layer, "subsetString") else ""
            crs_obj = _safe(layer.crs, None)
            crs_authid = _safe(crs_obj.authid, "") if crs_obj else ""
            if kind == "vector":
                count = _safe(layer.featureCount, -1)
                geometry = _GEOMETRY_TYPE_NAMES.get(_safe(layer.geometryType, -1), "Unknown")
            elif kind == "point_cloud":
                count = _safe(layer.pointCount, -1)
                geometry = "PointCloud"
            else:
                count = -1
                geometry = "Raster"
            derived = _derived_marker(layer)

            out.append(
                LayerSummary(
                    layer_id=_safe(layer.id, ""),
                    name=name,
                    provider_type=_safe(layer.providerType, ""),
                    feature_count=count,
                    geometry_type=geometry,
                    crs_authid=crs_authid,
                    has_active_filter=bool((subset and subset.strip()) or derived),
                    active_filter_expression=active_filters.get(name, subset or derived),
                    layer_kind=kind,
                )
            )
        return out

    def cross_filter(self, source_layer: str, target_layers: List[str], predicates: List[str],
                     buffer: float = 0.0, coverage_min: float = 0.0, operator: Optional[str] = None,
                     selected_only: bool = True) -> Optional[CrossFilterResult]:
        """FilterMate 5 cross filter, run on the Qt main thread (it changes layers)."""
        # Clipping a point cloud can take a while: wait longer than for a subset.
        return run_on_main_thread(self._cross_filter_main_thread, source_layer, list(target_layers), list(predicates),
                                  float(buffer), float(coverage_min), operator, bool(selected_only), timeout=600.0)

    def _cross_filter_main_thread(self, source_layer, target_layers, predicates, buffer, coverage_min,
                                  operator, selected_only) -> Optional[CrossFilterResult]:
        try:
            from qgis.core import QgsProject
            cross_filter = _plugin_module("core.domain.cross_filter")
            CrossFilterRequest, TargetSpec = cross_filter.CrossFilterRequest, cross_filter.TargetSpec
            LayerKind = _plugin_module("core.domain.layer_kind").LayerKind
            get_cross_filter_service = _plugin_module("core.services.cross_filter_service").get_cross_filter_service
            VectorSourceJob = _plugin_module("adapters.qgis.coverage_layers.source_jobs").VectorSourceJob
        except ImportError as exc:
            return CrossFilterResult(error=str(exc))
        project = QgsProject.instance()
        sources = [l for l in project.mapLayersByName(source_layer) if _layer_kind(l) == "vector"]
        if not sources:
            return None
        source = sources[0]
        if selected_only and source.selectedFeatureCount():
            features = list(source.getSelectedFeatures())
        else:
            features = list(source.getFeatures())
        targets, failed = [], {}
        for name in target_layers:
            layers = [l for l in project.mapLayersByName(name) if l.id() != source.id()]
            kind = _layer_kind(layers[0]) if layers else "other"
            if not layers or kind == "other":
                failed[name] = "layer not found or not filterable"
                continue
            targets.append(TargetSpec(layers[0].id(), LayerKind(kind)))
        if not targets or not features:
            return CrossFilterResult(failed=failed, error=None if targets else "no filterable target")
        request = CrossFilterRequest(source_layer_id=source.id(), source_kind=LayerKind.VECTOR, targets=tuple(targets),
                                     predicates=tuple(predicates) or ("Intersect",), buffer_value=buffer,
                                     coverage_min=coverage_min, other_layers_combine_operator=operator)
        task = get_cross_filter_service().run(request, VectorSourceJob(source, features), synchronous=True)
        if task.error:
            return CrossFilterResult(failed=failed, error=task.error)
        filtered = []
        for outcome in task.outcomes:
            layer = project.mapLayer(outcome.layer_id)
            name = layer.name() if layer is not None else outcome.layer_id
            if outcome.success:
                filtered.append(name)
            else:
                failed[name] = outcome.message or "failed"
        self._last_applied_at = datetime.now(timezone.utc).isoformat()
        self._last_applied_layer = source_layer
        self._last_applied_source = "rest_api:cross"
        return CrossFilterResult(filtered=filtered, failed=failed)

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
            # P1-API-HARDEN: surface "not ready" distinctly from "no
            # favorites" so the router can answer 503 instead of [].
            raise FavoritesUnavailable(
                "FavoritesService not mounted on plugin instance"
            )
        try:
            entries = favorites_service.get_all_favorites() or []
        except FavoritesUnavailable:
            raise
        except Exception as exc:
            # ``FavoritesNotInitialized`` (and any other init-time failure
            # surfaced as a domain exception) propagates as a 503 too —
            # the favorites store is simply not available yet.
            if type(exc).__name__ == "FavoritesNotInitialized":
                raise FavoritesUnavailable(str(exc)) from exc
            return []
        return [self._favorite_from(entry) for entry in entries]

    def apply_favorite(self, favorite_id: str) -> Optional[HistoryStep]:
        favorites_service = getattr(self._plugin, "favorites_manager", None)
        if favorites_service is None:
            raise FavoritesUnavailable(
                "FavoritesService not mounted on plugin instance"
            )
        try:
            entry = favorites_service.get_favorite(favorite_id)
        except FavoritesUnavailable:
            raise
        except Exception as exc:
            if type(exc).__name__ == "FavoritesNotInitialized":
                raise FavoritesUnavailable(str(exc)) from exc
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
            except Exception:  # nosec B112 - skip layer whose subset string could not be restored, continue with others
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

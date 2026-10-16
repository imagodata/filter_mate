"""
QGIS-backed FilterMateAccessor — issue #45.

Bridges the standalone REST API to the running FilterMate QGIS plugin
by delegating each accessor method to:

* :class:`FilterMatePublicAPI` for ``apply_filter`` / ``get_active_filters``
  (the contract documented at #13).
* :class:`HistoryService` (the same instance shared with the legacy plugin
  via ``adapters.app_bridge.get_history_service`` after #41 M4) for the
  undo/redo stack.
* :class:`FavoritesService` (mounted on the plugin's ``FilterMateApp``,
  ``plugin.app``) for favorite listing and apply.
* ``adapters.public_api.operations`` for the FilterMate 5 operations
  (the same code as the Python API and the Processing algorithms).
* ``QgsProject.instance().mapLayers()`` for the layer enumeration.

The class is import-light: no Qt/QGIS imports at module top-level so it
can be loaded under the headless test harness. QGIS only enters the
picture when methods run, always on the Qt main thread
(:func:`run_on_main_thread`), and any QGIS access is wrapped in a defensive
try/except so a misconfigured plugin doesn't bring the API down.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .accessor import (
    CrossFilterResult,
    Favorite,
    FavoritesUnavailable,
    FilteredLayer,
    FilterStatus,
    HistoryStep,
    LayerSummary,
    OperationResult,
)
from .main_thread import QGISBusy, run_on_main_thread


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


def _unless_busy(fn, *args, **kwargs):
    """``fn(*args, **kwargs)`` (main thread), refused while FilterMate is busy.

    A FilterMate operation (possibly re-entered here through processEvents)
    or a filter task of the dock would land its own subsets over this
    change: :class:`QGISBusy` instead, nothing changed.
    """
    try:
        reason = _plugin_module("adapters.public_api.operations").busy_reason()
    except ImportError:
        reason = ""
    if reason:
        raise QGISBusy(reason)
    return fn(*args, **kwargs)


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


def _report_busy(report) -> None:
    """Raise :class:`QGISBusy` when ``report`` was refused because FilterMate is busy."""
    if report.details.get("busy"):
        raise QGISBusy(report.error)


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
    can reach ``history_manager`` and ``favorites_manager`` — these live
    on its application object (``plugin.app``, a ``FilterMateApp``) and
    aren't on the public API surface today (#13 EPIC scoped them out),
    but the bridge is plugin-internal so reaching in is fine.

    Every method that touches QGIS (project, layers, history, favorites)
    runs its whole body on the Qt main thread: uvicorn calls the routes
    from a pool of worker threads, concurrently.
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

    def _app_attribute(self, name: str):
        """``name`` of the plugin's application (``plugin.app``), or of the plugin itself."""
        for owner in (self._plugin, getattr(self._plugin, "app", None)):
            value = getattr(owner, name, None) if owner is not None else None
            if value is not None:
                return value
        return None

    # ------------------------------------------------------------------
    # Layer enumeration
    # ------------------------------------------------------------------

    def list_layers(self) -> List[LayerSummary]:
        """Return all valid vector, raster and point cloud layers of the current QgsProject."""
        return run_on_main_thread(self._list_layers_main_thread)

    def _list_layers_main_thread(self) -> List[LayerSummary]:
        try:
            from qgis.core import QgsProject, QgsVectorLayer
        except ImportError:
            # Bridge running outside QGIS — fail soft with empty list.
            return []

        project = QgsProject.instance()
        active_filters = self._active_filters_main_thread()

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
                geometry = _geometry_type_name(_safe(layer.geometryType, -1))
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

    # ------------------------------------------------------------------
    # FilterMate 5 operations — adapters.public_api.operations
    # ------------------------------------------------------------------

    def cross_filter(self, source_layer: str, target_layers: List[str], predicates: List[str],
                     buffer: float = 0.0, coverage_min: float = 0.0, operator: Optional[str] = None,
                     selected_only: bool = True, raster_selection: Optional[Dict] = None,
                     point_cloud_criteria: Optional[Dict] = None,
                     filter_source: bool = False) -> Optional[CrossFilterResult]:
        """FilterMate 5 cross filter, run on the Qt main thread (it changes layers)."""
        return run_on_main_thread(self._cross_filter_main_thread, source_layer, list(target_layers), list(predicates),
                                  float(buffer), float(coverage_min), operator, bool(selected_only),
                                  raster_selection, point_cloud_criteria, bool(filter_source))

    def _cross_filter_main_thread(self, source_layer, target_layers, predicates, buffer, coverage_min,
                                  operator, selected_only, raster_selection=None, point_cloud_criteria=None,
                                  filter_source=False) -> Optional[CrossFilterResult]:
        try:
            from qgis.core import QgsProject
            operations = _plugin_module("adapters.public_api.operations")
            requests = _plugin_module("core.domain.api_requests")
        except ImportError as exc:
            return CrossFilterResult(error=str(exc))
        project = QgsProject.instance()
        # Same resolution as the Python API and Processing: layer id, then name.
        source = operations.resolve_layer(source_layer, project)
        if source is None or _layer_kind(source) == "other":
            return None
        try:
            report = operations.cross_filter(
                source, list(target_layers), predicates=tuple(predicates) or ("Intersect",), buffer=buffer,
                coverage_min=coverage_min, operator=operator, selected_only=selected_only,
                raster_selection=requests.raster_selection_from_dict(raster_selection),
                point_cloud_criteria=requests.point_cloud_criteria_from_dict(point_cloud_criteria),
                filter_source=filter_source, project=project)
        except ValueError as exc:
            return CrossFilterResult(error=str(exc))
        _report_busy(report)
        result = self._cross_result(report)
        if not result.error:
            self._mark_applied(source_layer, "rest_api:cross")
        return result

    @staticmethod
    def _cross_result(report) -> CrossFilterResult:
        return CrossFilterResult(filtered=report.done_names, failed=dict(report.failed),
                                 skipped=dict(report.skipped), error=report.error or None)

    @staticmethod
    def _operation_result(report) -> OperationResult:
        return OperationResult(done=report.done_names, failed=dict(report.failed), skipped=dict(report.skipped),
                               error=report.error or None, outputs=dict(report.outputs))

    def _mark_applied(self, layer: str, source: str) -> None:
        self._last_applied_at = datetime.now(timezone.utc).isoformat()
        self._last_applied_layer = layer
        self._last_applied_source = source

    def cross_filter_by_geometry(self, wkt: str, crs: str, target_layers: List[str], predicates: List[str],
                                 buffer: float = 0.0, coverage_min: float = 0.0,
                                 operator: Optional[str] = None) -> CrossFilterResult:
        return run_on_main_thread(self._geometry_main_thread, wkt, crs, list(target_layers), list(predicates),
                                  float(buffer), float(coverage_min), operator)

    def _geometry_main_thread(self, wkt, crs, target_layers, predicates, buffer, coverage_min, operator):
        try:
            from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry
            operations = _plugin_module("adapters.public_api.operations")
        except ImportError as exc:
            return CrossFilterResult(error=str(exc))
        reference = QgsCoordinateReferenceSystem(crs)
        geometry = QgsGeometry.fromWkt(wkt)
        if not reference.isValid() or geometry.isNull():
            return CrossFilterResult(error="invalid geometry or CRS")
        report = operations.cross_filter_by_geometry(geometry, reference, target_layers,
                                                     predicates=tuple(predicates) or ("Intersect",), buffer=buffer,
                                                     coverage_min=coverage_min, operator=operator)
        _report_busy(report)
        result = self._cross_result(report)
        if not result.error:
            self._mark_applied("geometry", "rest_api:geometry")
        return result

    def filter_point_clouds(self, layers: List[str], criteria: Dict,
                            operator: Optional[str] = None) -> OperationResult:
        return run_on_main_thread(self._point_clouds_main_thread, list(layers), dict(criteria or {}), operator)

    def _point_clouds_main_thread(self, layers, criteria, operator):
        try:
            operations = _plugin_module("adapters.public_api.operations")
            requests = _plugin_module("core.domain.api_requests")
            report = operations.filter_point_clouds(layers, requests.point_cloud_criteria_from_dict(criteria),
                                                    operator=operator)
        except (ImportError, ValueError) as exc:
            return OperationResult(error=str(exc))
        _report_busy(report)
        if report.done:
            self._mark_applied(report.done_names[0], "rest_api:point_cloud")
        return self._operation_result(report)

    def clear_filters(self, layers: List[str]) -> OperationResult:
        return run_on_main_thread(self._clear_main_thread, list(layers))

    def _clear_main_thread(self, layers):
        try:
            report = _plugin_module("adapters.public_api.operations").clear_filters(layers)
        except ImportError as exc:
            return OperationResult(error=str(exc))
        _report_busy(report)
        if report.done:
            self._mark_applied(report.done_names[0], "rest_api:clear")
        return self._operation_result(report)

    def export_layers(self, layers: List[str], folder: str, vector_format: str, raster_format: str,
                      point_cloud_format: str, crs: Optional[str] = None) -> OperationResult:
        return run_on_main_thread(self._export_main_thread, list(layers), folder, vector_format, raster_format,
                                  point_cloud_format, crs)

    def _export_main_thread(self, layers, folder, vector_format, raster_format, point_cloud_format, crs):
        try:
            operations = _plugin_module("adapters.public_api.operations")
        except ImportError as exc:
            return OperationResult(error=str(exc))
        output_crs = None
        if crs:
            from qgis.core import QgsCoordinateReferenceSystem
            output_crs = QgsCoordinateReferenceSystem(crs)
            if not output_crs.isValid():
                return OperationResult(error="invalid CRS")
        report = operations.export_layers(layers, folder, vector_format=vector_format, raster_format=raster_format,
                                          point_cloud_format=point_cloud_format, crs=output_crs)
        _report_busy(report)
        return self._operation_result(report)

    def get_filter_state(self) -> List[FilteredLayer]:
        # A busy main thread raises QGISBusy (503): never answered as "no filter".
        return run_on_main_thread(self._filter_state_main_thread)

    @staticmethod
    def _filter_state_main_thread() -> List[FilteredLayer]:
        def _state():
            rows = _plugin_module("adapters.public_api.operations").filter_state()
            return [FilteredLayer(layer_id=row["id"], name=row["name"], layer_kind=row["kind"],
                                  subset=row["subset"], derived=row["derived"]) for row in rows]
        return _safe(_state, []) or []

    # ------------------------------------------------------------------
    # Filter mutations — delegated to the PublicAPI
    # ------------------------------------------------------------------

    def apply_filter(self, layer_name: str, expression: str, source: str) -> bool:
        # P0-B (audit 2026-04-29): ``PublicAPI.apply_filter`` ultimately
        # calls ``QgsVectorLayer.setSubsetString`` which is not
        # thread-safe outside the Qt main thread. ``uvicorn`` runs us
        # on a worker, so we marshal the call through the main-thread
        # dispatcher; under the headless test harness this is a no-op
        # inline call. Refused (QGISBusy) while a FilterMate operation or
        # filter task runs: its own subsets would land over this one.
        ok = run_on_main_thread(
            _unless_busy,
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
        return run_on_main_thread(self._active_filters_main_thread)

    def _active_filters_main_thread(self) -> Dict[str, str]:
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
        return self._step_via_history("undo")

    def redo_filter(self) -> Optional[HistoryStep]:
        return self._step_via_history("redo")

    # ------------------------------------------------------------------
    # Favorites — delegated to FavoritesService
    # ------------------------------------------------------------------

    def _favorites_service(self):
        favorites_service = self._app_attribute("favorites_manager")
        if favorites_service is None:
            # P1-API-HARDEN: surface "not ready" distinctly from "no
            # favorites" so the router can answer 503 instead of [].
            raise FavoritesUnavailable(
                "FavoritesService not mounted on the plugin application"
            )
        return favorites_service

    def list_favorites(self) -> List[Favorite]:
        return run_on_main_thread(self._list_favorites_main_thread)

    def _list_favorites_main_thread(self) -> List[Favorite]:
        favorites_service = self._favorites_service()
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
        return run_on_main_thread(self._apply_favorite_main_thread, favorite_id)

    def _apply_favorite_main_thread(self, favorite_id: str) -> Optional[HistoryStep]:
        favorites_service = self._favorites_service()
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
        try:
            operations = _plugin_module("adapters.public_api.operations")
        except ImportError:
            return None
        # Same replay as the dock's menu, the Python API and Processing: every
        # subset of the favorite (remote layers too, found by signature, id
        # then name), then its raster / point cloud clips.
        report = operations.apply_favorite(favorite_id, favorites_service)
        _report_busy(report)
        if report.error or not report.done:
            return None
        layer_name = getattr(entry, "layer_name", "") or report.done_names[0]
        self._mark_applied(layer_name, f"favorite:{favorite_id}")
        return HistoryStep(layer_name=layer_name, expression=getattr(entry, "expression", "") or "")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _step_via_history(self, direction: str) -> Optional[HistoryStep]:
        """Undo / redo one step of the HistoryService shared with the dock, on the main thread.

        The dock's vector filter history: neither ``apply_filter`` nor the
        FilterMate 5 operations record anything in it.
        """
        return run_on_main_thread(_unless_busy, self._step_via_history_inline, direction)

    def _step_via_history_inline(self, direction: str) -> Optional[HistoryStep]:
        """Run HistoryService.undo/redo (main thread) and re-apply the resulting
        entry's previous filters back to QGIS layers.

        The history is shared with the dock (its buttons, its change
        callbacks): it is only ever touched on the main thread. Returns a
        :class:`HistoryStep` describing the layer most affected by the
        operation, or ``None`` when the stack is empty.
        """
        svc = self._app_attribute("history_manager")
        action = getattr(svc, direction, None) if svc is not None else None
        entry = action() if action is not None else None
        if entry is None:
            return None

        try:
            from qgis.core import QgsProject
            project = QgsProject.instance()
        except ImportError:
            project = None

        previous_filters = getattr(entry, "previous_filters", ()) or ()
        target_layer_name, target_expression, target_is_clear = self._reapply_previous_filters_inline(
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


def _geometry_type_name(value) -> str:
    """API name of a geometry type: an int (PyQt5 enum) or an enum with ``.value`` (Qgis.GeometryType, PyQt6)."""
    try:
        return _GEOMETRY_TYPE_NAMES.get(int(getattr(value, "value", value)), "Unknown")
    except (TypeError, ValueError):
        return "Unknown"

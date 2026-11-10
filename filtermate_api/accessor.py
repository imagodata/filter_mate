"""
FilterMate accessor — Protocol + in-memory stub.

The HTTP API needs to read layer state and apply filters, but it must run
without QGIS in the loop (standalone tests, headless deployments). This
module defines the seam between the FastAPI routes and "the FilterMate
plugin running inside QGIS":

* :class:`FilterMateAccessor` — a Protocol that captures the operations the
  REST endpoints need. The QGIS plugin can implement it by delegating to
  ``FilterMatePublicAPI``; tests inject :class:`InMemoryAccessor` instead.

The dependency-injection seam is wired in ``server.create_app`` so a test
can do::

    app = create_app(accessor=InMemoryAccessor(layers=[...]))
    client = TestClient(app)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class FavoritesUnavailable(RuntimeError):
    """Raised when the favorites store is not (yet) ready to serve.

    P1-API-HARDEN (audit 2026-04-29): the QGIS-side FavoritesService
    can be missing entirely (plugin still booting, project not loaded
    yet, persistence layer offline) or raise ``FavoritesNotInitialized``
    on access. Routers translate this to ``503 Service Unavailable``
    with a ``Retry-After`` hint so callers don't get a silent ``[]``
    that misleads them into "no favorites configured".
    """


class FilterRejected(ValueError):
    """An existing layer refused an attribute filter without applying it."""


@dataclass(frozen=True)
class LayerSummary:
    """Lightweight projection of a QGIS layer for API consumers.

    Mirrors the subset of LayerInfo that REST clients care about — kept
    intentionally small so the response payload stays predictable across
    schema migrations.
    """
    layer_id: str
    name: str
    provider_type: str
    feature_count: int = -1
    geometry_type: str = ""
    crs_authid: str = ""
    has_active_filter: bool = False
    active_filter_expression: str = ""
    # FilterMate 5: "vector", "raster" or "point_cloud" (vector by default so
    # older clients and accessors keep working).
    layer_kind: str = "vector"


@dataclass(frozen=True)
class CrossFilterResult:
    """Outcome of a cross filter (FilterMate 5): targets of any kind filtered by a source of any kind."""
    filtered: List[str] = field(default_factory=list)
    failed: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    # Layers left out on purpose (not found, not filterable, the source itself), apart from ``failed``.
    skipped: Dict[str, str] = field(default_factory=dict)
    # Layers filtered with a reservation, also in ``filtered``: a web service read up to its
    # feature or time budget keeps exact features only, some may be missing (partial result).
    warnings: Dict[str, str] = field(default_factory=dict)
    # Features each filtered layer keeps, when it was counted.
    kept: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationResult:
    """Outcome of a FilterMate 5 operation on several layers (point clouds, unfilter, export)."""
    done: List[str] = field(default_factory=list)
    failed: Dict[str, str] = field(default_factory=dict)
    skipped: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    # Export: layer name -> file written (server side).
    outputs: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FilteredLayer:
    """A layer FilterMate currently filters: subset string and / or derived (clipped) source."""
    layer_id: str
    name: str
    layer_kind: str
    subset: str = ""
    derived: bool = False


@dataclass(frozen=True)
class HistoryStep:
    """One entry in the undo/redo stack — what an undo/redo response carries.

    Issue #33. Not the full HistoryService entry shape — clients only
    need to know *which* layer is now in *which* state.
    """
    layer_name: str
    expression: str  # "" when the step is "filter cleared"
    is_clear: bool = False


@dataclass(frozen=True)
class Favorite:
    """Stored filter preset surfaced to API consumers (issue #32)."""
    favorite_id: str
    name: str
    description: str = ""
    layer_name: str = ""
    expression: str = ""


@dataclass(frozen=True)
class FilterStatus:
    """Snapshot of the FilterMate session's filter state.

    Issue #31. The current PublicAPI is synchronous (apply returns when
    the filter is materialized) so ``status`` is always ``"idle"`` or
    ``"completed"``. The async ``"pending"`` / ``"running"`` states are
    reserved for the future task-based variant — keeping them in the
    enum stops a contract change when async lands.
    """
    status: str  # "idle" | "completed" | "pending" | "running" | "error"
    active_filters: Dict[str, str] = field(default_factory=dict)
    active_filters_count: int = 0
    last_applied_at: Optional[str] = None  # ISO-8601 UTC, None when idle
    last_applied_layer: Optional[str] = None
    last_applied_source: Optional[str] = None
    last_error: Optional[str] = None


@dataclass(frozen=True)
class LayerDetails:
    """What it takes to write a filter on a layer: its fields, bands or point attributes."""
    layer_id: str
    name: str
    layer_kind: str
    provider_type: str = ""
    crs_authid: str = ""
    geometry_type: str = ""
    feature_count: int = -1
    subset: str = ""
    # Vector: the language its filter is written in: postgresql, sqlite, ogr_sql or qgis_expression.
    sql_dialect: str = ""
    # Vector: {"name", "type", "alias", "filterable"}; virtual and joined fields are not filterable.
    fields: List[Dict[str, Any]] = field(default_factory=list)
    # Raster: {"band", "name", "classes": [{"value", "label"}]}, classes only on a paletted band.
    bands: List[Dict[str, Any]] = field(default_factory=list)
    # Raster: size of a pixel, in the units of the layer CRS.
    pixel_size: Optional[float] = None
    # Point cloud: attribute names (Z, Classification, Intensity...).
    attributes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class FieldValues:
    """Distinct values of a field, among the features the layer shows now."""
    layer_name: str
    field: str
    values: List[Any] = field(default_factory=list)
    # More values exist than ``values`` holds.
    truncated: bool = False
    minimum: Any = None
    maximum: Any = None


@dataclass(frozen=True)
class FilterPreview:
    """What a filter expression would keep, tried on a private copy of the layer."""
    layer_name: str
    expression: str
    valid: bool
    feature_count: int = -1
    error: str = ""


@dataclass(frozen=True)
class MapContext:
    """What the user is looking at. ``available`` is False without a map canvas (headless QGIS)."""
    available: bool = False
    project_crs: str = ""
    canvas_crs: str = ""
    extent_wkt: str = ""
    scale: Optional[float] = None
    active_layer_id: str = ""
    active_layer_name: str = ""
    # {"layer_id", "name", "selected_count"} of the vector layers with a selection.
    selections: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ViewState:
    """Where the map looks after a zoom."""
    extent_wkt: str = ""
    scale: Optional[float] = None


@dataclass(frozen=True)
class SelectionResult:
    """The selection of a vector layer after a change."""
    layer_id: str
    layer_name: str
    selected_count: int = 0


@dataclass(frozen=True)
class OpenDataResult:
    """Datasets an open data platform answered with; each has id, title, publisher, description, page, resources."""
    platform: str
    query: str
    datasets: List[Dict[str, Any]] = field(default_factory=list)
    count: int = 0


@runtime_checkable
class FilterMateAccessor(Protocol):
    """The contract REST routes use to talk to the running FilterMate plugin."""

    def list_layers(self) -> List[LayerSummary]:
        """Return all vector layers visible to the current FilterMate session."""
        ...

    def describe_layer(self, layer: str) -> Optional[LayerDetails]:
        """Fields, bands or attributes of a layer (id or name), ``None`` when it does not resolve."""
        ...

    def field_values(self, layer: str, field_name: str, search: str = "", limit: int = 50) -> Optional[FieldValues]:
        """Distinct values of a vector field, ``None`` when the layer or the field does not resolve.

        Raises FilterRejected on a layer that cannot answer (not vector, web service).
        """
        ...

    def preview_filter(self, layer_name: str, expression: str) -> Optional[FilterPreview]:
        """Try ``expression`` without touching the layer, ``None`` when the layer does not resolve.

        Raises FilterRejected on a layer that cannot be tried (not vector, web service).
        """
        ...

    def map_context(self) -> MapContext:
        """CRS, extent, active layer and selections of the QGIS window."""
        ...

    def zoom_to(self, layer: Optional[str] = None, extent_wkt: Optional[str] = None, crs: Optional[str] = None,
                selected_only: bool = False) -> ViewState:
        """Zoom the map; raises FilterRejected when there is no canvas or the target is empty."""
        ...

    def select_features(self, layer: str, expression: str = "", clear: bool = False, add: bool = False) -> SelectionResult:
        """Select by QGIS expression, or clear; raises FilterRejected on a bad layer or expression."""
        ...

    def set_layers_visibility(self, layers: List[str], visible: bool) -> OperationResult:
        """Check or uncheck layers in the layer tree."""
        ...

    def add_layer(self, source: str, name: str = "", kind: str = "vector") -> LayerSummary:
        """Add a layer from a file or a public https URL; raises FilterRejected on any other source."""
        ...

    def remove_layers(self, layers: List[str]) -> OperationResult:
        """Remove layers from the project."""
        ...

    def search_open_data(self, query: str, platform: str = "datagouv", limit: int = 10,
                         extra_domains: Optional[str] = None) -> OpenDataResult:
        """Datasets of an allowed platform; raises FilterRejected on a platform not allowed or unreachable."""
        ...

    def add_service_layer(self, platform: str, typename: str, name: str = "",
                          extra_domains: Optional[str] = None) -> LayerSummary:
        """Add a layer of a WFS platform; raises FilterRejected when it does not offer it."""
        ...

    def search_imagery(self, bbox: Optional[List[float]] = None, start: str = "", end: str = "", max_cloud: float = 20.0,
                       collections: Optional[List[str]] = None, limit: int = 5, platform: str = "earth_search",
                       extra_domains: Optional[str] = None) -> OpenDataResult:
        """Scenes of a STAC catalog; raises FilterRejected on a catalog not allowed or unreachable."""
        ...

    def apply_filter(self, layer_name: str, expression: str, source: str) -> bool:
        """Apply ``expression`` to ``layer_name``. Returns success."""
        ...

    def get_active_filters(self) -> Dict[str, str]:
        """Return ``{layer_name: expression}`` for layers with active filters."""
        ...

    def get_filter_status(self) -> FilterStatus:
        """Return a snapshot of the session's current filter state."""
        ...

    def undo_filter(self) -> Optional[HistoryStep]:
        """Pop the last filter from the history stack. Returns the restored
        step (the state we just rolled back TO), or ``None`` when there is
        nothing to undo — the route maps that to a 409.
        """
        ...

    def redo_filter(self) -> Optional[HistoryStep]:
        """Re-apply the most recently undone step. ``None`` when the redo
        stack is empty.
        """
        ...

    def list_favorites(self) -> List[Favorite]:
        """Return the favorites known to the FilterMate session."""
        ...

    def apply_favorite(self, favorite_id: str) -> Optional[HistoryStep]:
        """Apply the favorite identified by ``favorite_id``. Returns the
        resulting step, or ``None`` when the id doesn't resolve.
        """
        ...

    def cross_filter(self, source_layer: str, target_layers: List[str], predicates: List[str],
                     buffer: float = 0.0, coverage_min: float = 0.0, operator: Optional[str] = None,
                     selected_only: bool = True, raster_selection: Optional[Dict] = None,
                     point_cloud_criteria: Optional[Dict] = None,
                     filter_source: bool = False) -> Optional[CrossFilterResult]:
        """Filter vector / raster / point cloud ``target_layers`` by a selection on
        ``source_layer`` of any kind: selected features (vector), pixels of
        ``raster_selection`` (raster), points of ``point_cloud_criteria`` (point
        cloud). ``None`` when the source does not resolve (route: 404).
        """
        ...

    def cross_filter_by_geometry(self, wkt: str, crs: str, target_layers: List[str], predicates: List[str],
                                 buffer: float = 0.0, coverage_min: float = 0.0,
                                 operator: Optional[str] = None) -> CrossFilterResult:
        """Filter ``target_layers`` by a WKT geometry expressed in ``crs`` (``EPSG:2154``)."""
        ...

    def filter_point_clouds(self, layers: List[str], criteria: Dict,
                            operator: Optional[str] = None) -> OperationResult:
        """Apply the same point cloud criteria to several point cloud layers."""
        ...

    def clear_filters(self, layers: List[str]) -> OperationResult:
        """Put layers of any kind back on their original source, with no filter."""
        ...

    def export_layers(self, layers: List[str], folder: str, vector_format: str, raster_format: str,
                      point_cloud_format: str, crs: Optional[str] = None) -> OperationResult:
        """Write the layers as filtered now into ``folder`` (already resolved by the route)."""
        ...

    def get_filter_state(self) -> List[FilteredLayer]:
        """Every layer FilterMate currently filters."""
        ...


@dataclass
class InMemoryAccessor:
    """Test-only accessor backed by an in-memory layer list.

    Keeps a side-table of active filters + a tiny undo/redo history so
    apply/undo/redo behave consistently across requests in a single test.
    """
    layers: List[LayerSummary] = field(default_factory=list)
    favorites: List[Favorite] = field(default_factory=list)
    _active: Dict[str, str] = field(default_factory=dict)
    _last_applied_at: Optional[str] = None
    _last_applied_layer: Optional[str] = None
    _last_applied_source: Optional[str] = None
    # Stacks of HistoryStep — _undo_stack stores past states (newest first),
    # _redo_stack stores undone steps available for redo.
    _undo_stack: List[HistoryStep] = field(default_factory=list)
    _redo_stack: List[HistoryStep] = field(default_factory=list)

    def list_layers(self) -> List[LayerSummary]:
        return [self._with_active(layer) for layer in self.layers]

    def _find(self, reference: str) -> Optional[LayerSummary]:
        return next((layer for layer in self.layers if reference in (layer.layer_id, layer.name)), None)

    def describe_layer(self, layer: str) -> Optional[LayerDetails]:
        found = self._find(layer)
        if found is None:
            return None
        return LayerDetails(layer_id=found.layer_id, name=found.name, layer_kind=found.layer_kind,
                            provider_type=found.provider_type, crs_authid=found.crs_authid,
                            geometry_type=found.geometry_type, feature_count=found.feature_count,
                            subset=self._active.get(found.name, ""))

    def field_values(self, layer: str, field_name: str, search: str = "", limit: int = 50) -> Optional[FieldValues]:
        found = self._find(layer)
        return None if found is None else FieldValues(layer_name=found.name, field=field_name)

    def preview_filter(self, layer_name: str, expression: str) -> Optional[FilterPreview]:
        found = self._find(layer_name)
        if found is None:
            return None
        return FilterPreview(layer_name=found.name, expression=expression, valid=True,
                             feature_count=found.feature_count)

    def map_context(self) -> MapContext:
        return MapContext()

    def zoom_to(self, layer: Optional[str] = None, extent_wkt: Optional[str] = None, crs: Optional[str] = None,
                selected_only: bool = False) -> ViewState:
        if layer is not None and self._find(layer) is None:
            raise FilterRejected(f"layer {layer!r} not found")
        return ViewState(extent_wkt=extent_wkt or "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", scale=10000.0)

    def select_features(self, layer: str, expression: str = "", clear: bool = False, add: bool = False) -> SelectionResult:
        found = self._find(layer)
        if found is None:
            raise FilterRejected(f"layer {layer!r} not found")
        return SelectionResult(found.layer_id, found.name, 0 if clear else 3)

    def set_layers_visibility(self, layers: List[str], visible: bool) -> OperationResult:
        done = [found.name for found in (self._find(name) for name in layers) if found is not None]
        failed = {name: "layer not found" for name in layers if self._find(name) is None}
        return OperationResult(done=done, failed=failed)

    def add_layer(self, source: str, name: str = "", kind: str = "vector") -> LayerSummary:
        summary = LayerSummary(layer_id=f"L{len(self.layers) + 1}", name=name or source.rsplit("/", 1)[-1],
                               provider_type="ogr" if kind == "vector" else "gdal", layer_kind=kind)
        self.layers.append(summary)
        return summary

    def remove_layers(self, layers: List[str]) -> OperationResult:
        done, failed = [], {}
        for name in layers:
            found = self._find(name)
            if found is None:
                failed[name] = "layer not found"
            else:
                self.layers.remove(found)
                done.append(found.name)
        return OperationResult(done=done, failed=failed)

    def search_open_data(self, query: str, platform: str = "datagouv", limit: int = 10,
                         extra_domains: Optional[str] = None) -> OpenDataResult:
        return OpenDataResult(platform, query, [], 0)

    def search_imagery(self, bbox: Optional[List[float]] = None, start: str = "", end: str = "", max_cloud: float = 20.0,
                       collections: Optional[List[str]] = None, limit: int = 5, platform: str = "earth_search",
                       extra_domains: Optional[str] = None) -> OpenDataResult:
        return OpenDataResult(platform, "imagery", [], 0)

    def add_service_layer(self, platform: str, typename: str, name: str = "",
                          extra_domains: Optional[str] = None) -> LayerSummary:
        summary = LayerSummary(layer_id=f"L{len(self.layers) + 1}", name=name or typename, provider_type="WFS")
        self.layers.append(summary)
        return summary

    def apply_filter(self, layer_name: str, expression: str, source: str) -> bool:
        if not any(layer.name == layer_name for layer in self.layers):
            return False
        # Capture the previous state for undo BEFORE we overwrite it.
        previous = self._active.get(layer_name, "")
        self._undo_stack.append(
            HistoryStep(layer_name=layer_name, expression=previous, is_clear=not previous)
        )
        # A user-driven action invalidates the redo branch.
        self._redo_stack.clear()

        self._active[layer_name] = expression
        self._last_applied_at = datetime.now(timezone.utc).isoformat()
        self._last_applied_layer = layer_name
        self._last_applied_source = source
        return True

    def get_active_filters(self) -> Dict[str, str]:
        return dict(self._active)

    def get_filter_status(self) -> FilterStatus:
        active = self.get_active_filters()
        return FilterStatus(
            status="completed" if active else "idle",
            active_filters=active,
            active_filters_count=len(active),
            last_applied_at=self._last_applied_at,
            last_applied_layer=self._last_applied_layer,
            last_applied_source=self._last_applied_source,
        )

    def undo_filter(self) -> Optional[HistoryStep]:
        if not self._undo_stack:
            return None
        prev = self._undo_stack.pop()
        # Push the CURRENT state onto the redo stack so we can re-apply it later.
        current_expr = self._active.get(prev.layer_name, "")
        self._redo_stack.append(
            HistoryStep(layer_name=prev.layer_name, expression=current_expr,
                        is_clear=not current_expr)
        )
        # Restore the previous state (clear the active filter when prev.is_clear).
        if prev.is_clear:
            self._active.pop(prev.layer_name, None)
        else:
            self._active[prev.layer_name] = prev.expression
        return prev

    def redo_filter(self) -> Optional[HistoryStep]:
        if not self._redo_stack:
            return None
        nxt = self._redo_stack.pop()
        # Push the current state onto the undo stack to keep both directions consistent.
        current_expr = self._active.get(nxt.layer_name, "")
        self._undo_stack.append(
            HistoryStep(layer_name=nxt.layer_name, expression=current_expr,
                        is_clear=not current_expr)
        )
        if nxt.is_clear:
            self._active.pop(nxt.layer_name, None)
        else:
            self._active[nxt.layer_name] = nxt.expression
        return nxt

    def list_favorites(self) -> List[Favorite]:
        return list(self.favorites)

    def apply_favorite(self, favorite_id: str) -> Optional[HistoryStep]:
        fav = next((f for f in self.favorites if f.favorite_id == favorite_id), None)
        if fav is None or not fav.layer_name:
            return None
        applied = self.apply_filter(
            layer_name=fav.layer_name,
            expression=fav.expression,
            source=f"favorite:{favorite_id}",
        )
        if not applied:
            return None
        return HistoryStep(layer_name=fav.layer_name, expression=fav.expression)

    def cross_filter(self, source_layer: str, target_layers: List[str], predicates: List[str],
                     buffer: float = 0.0, coverage_min: float = 0.0, operator: Optional[str] = None,
                     selected_only: bool = True, raster_selection: Optional[Dict] = None,
                     point_cloud_criteria: Optional[Dict] = None,
                     filter_source: bool = False) -> Optional[CrossFilterResult]:
        names = {layer.name: layer for layer in self.layers}
        source = names.get(source_layer)
        if source is None:
            return None
        if source.layer_kind == "raster" and not raster_selection:
            return CrossFilterResult(error="a raster source needs a pixel selection")
        filtered = [name for name in target_layers if name in names and name != source_layer]
        failed = {name: "layer not found" for name in target_layers if name not in names}
        for name in filtered:
            self._active[name] = f"cross:{source_layer}"
        if source.layer_kind == "raster" and filter_source:
            self._active[source_layer] = "selection"  # the source changes, it is not a target
        return CrossFilterResult(filtered=filtered, failed=failed)

    def cross_filter_by_geometry(self, wkt: str, crs: str, target_layers: List[str], predicates: List[str],
                                 buffer: float = 0.0, coverage_min: float = 0.0,
                                 operator: Optional[str] = None) -> CrossFilterResult:
        names = {layer.name for layer in self.layers}
        filtered = [name for name in target_layers if name in names]
        for name in filtered:
            self._active[name] = "cross:geometry"
        return CrossFilterResult(filtered=filtered,
                                 failed={name: "layer not found" for name in target_layers if name not in names},
                                 error=None if filtered else "no filterable target layer")

    def filter_point_clouds(self, layers: List[str], criteria: Dict,
                            operator: Optional[str] = None) -> OperationResult:
        kinds = {layer.name: layer.layer_kind for layer in self.layers}
        done = [name for name in layers if kinds.get(name) == "point_cloud"]
        for name in done:
            self._active[name] = "point_cloud:criteria"
        skipped = {name: "not a point cloud layer" if name in kinds else "layer not found"
                   for name in layers if name not in done}
        return OperationResult(done=done, skipped=skipped, error=None if done else "no point cloud layer to filter")

    def clear_filters(self, layers: List[str]) -> OperationResult:
        done = [name for name in layers if name in self._active]
        for name in done:
            self._active.pop(name, None)
        return OperationResult(done=done, skipped={name: "not filtered" for name in layers if name not in done})

    def export_layers(self, layers: List[str], folder: str, vector_format: str, raster_format: str,
                      point_cloud_format: str, crs: Optional[str] = None) -> OperationResult:
        extensions = {"vector": ".gpkg", "raster": ".tif", "point_cloud": ".laz"}
        kinds = {layer.name: layer.layer_kind for layer in self.layers}
        outputs = {name: f"{folder}/{name}{extensions.get(kinds[name], '')}" for name in layers if name in kinds}
        return OperationResult(done=list(outputs), outputs=outputs,
                               skipped={name: "layer not found" for name in layers if name not in kinds})

    def get_filter_state(self) -> List[FilteredLayer]:
        by_name = {layer.name: layer for layer in self.layers}
        return [FilteredLayer(layer_id=by_name[name].layer_id, name=name, layer_kind=by_name[name].layer_kind,
                              subset=expression, derived=by_name[name].layer_kind != "vector")
                for name, expression in self._active.items() if name in by_name]

    def _with_active(self, layer: LayerSummary) -> LayerSummary:
        expr = self._active.get(layer.name, layer.active_filter_expression)
        if not expr:
            return layer
        return LayerSummary(
            layer_id=layer.layer_id,
            name=layer.name,
            provider_type=layer.provider_type,
            feature_count=layer.feature_count,
            geometry_type=layer.geometry_type,
            crs_authid=layer.crs_authid,
            has_active_filter=True,
            active_filter_expression=expr,
            layer_kind=layer.layer_kind,
        )

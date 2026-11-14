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


class LayerProtected(Exception):
    """The call would change a layer the user protected from the agent: nothing done (HTTP 403).

    Neither a ValueError nor a FilterRejected: the routes answer those 400 themselves.
    """


# Header of that 403, which tells it apart from a 403 of the access rules (the MCP server built on the REST API).
PROTECTED_HEADER = "X-FilterMate-Refusal"


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
    # Checked in the layer tree, with every group above it. The rows come in the order of the tree, top first.
    visible: bool = True
    # The groups it sits in, outermost first, joined by " / "; empty at the root.
    group: str = ""


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
    # Where it sits in the layer tree: checked with its groups, and those groups joined by " / ".
    visible: bool = True
    group: str = ""
    # [xmin, ymin, xmax, ymax] in the layer CRS; empty when unknown, and for a web service (not read to answer).
    extent: List[float] = field(default_factory=list)
    # How it is drawn: {"renderer", "field", "classes", "labels", "opacity", "min_scale", "max_scale"}, each only
    # when it applies. No attribute value is given.
    style: Dict[str, Any] = field(default_factory=dict)
    # Vector: {"layer", "field", "target_field", "prefix"} of each join; joined fields are not filterable.
    joins: List[Dict[str, Any]] = field(default_factory=list)
    # Vector: {"name", "role" (parent or child), "layer", "fields": [{"field", "other_field"}]} of the project.
    relations: List[Dict[str, Any]] = field(default_factory=list)
    # Vector: in editing mode, and holding changes not saved yet.
    editing: bool = False
    unsaved: bool = False


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
class LayerStatistics:
    """Statistics of a field or of the geometries of a vector layer, in all and by the values of another field."""
    layer_name: str
    # Empty when features are counted or geometries measured. No default: one would hide ``dataclasses.field`` below.
    field: str
    # "length" or "area" when the geometries are measured instead of a field; ``unit`` is then m or m2.
    measure: str = ""
    unit: str = ""
    # The ellipsoid the measure was made on; empty for a planar one.
    ellipsoid: str = ""
    selected_only: bool = False
    # Features read: those the layer shows now, or its selection.
    feature_count: int = 0
    # {"count", "nulls", "minimum", "maximum"} and "sum", "mean", "stdev" for numbers, "distinct" otherwise.
    # Empty when only features are counted.
    statistics: Dict[str, Any] = field(default_factory=dict)
    group_by: str = ""
    # {"value", "feature_count"} and the same statistics, the largest groups first.
    groups: List[Dict[str, Any]] = field(default_factory=list)
    groups_total: int = 0
    # More groups exist than ``groups`` holds.
    truncated: bool = False


@dataclass(frozen=True)
class FeatureSample:
    """A few features of a vector layer."""
    layer_name: str
    crs_authid: str = ""
    # {"fid", "attributes": {name: value}, "geometry": {"type", "centroid", "bbox"}}, geometry only when asked.
    features: List[Dict[str, Any]] = field(default_factory=list)
    # More features match than ``features`` holds.
    truncated: bool = False
    # The layer has more fields than a row holds.
    fields_truncated: bool = False


@dataclass(frozen=True)
class IdentifyResult:
    """What lies at a point of the map."""
    x: float
    y: float
    crs: str = ""
    tolerance: float = 0.0
    # {"layer_name", "layer_kind", "features": [{"fid", "attributes"}], "truncated"} for a vector layer,
    # {"layer_name", "layer_kind", "values": [{"band", "value"}]} for a raster; only the layers with something.
    layers: List[Dict[str, Any]] = field(default_factory=list)
    # Layers left out: web services, and those that could not answer.
    skipped: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AlgorithmList:
    """Processing algorithms the agent may run, found by words."""
    query: str
    # {"id", "name", "group", "summary"}
    algorithms: List[Dict[str, Any]] = field(default_factory=list)
    total: int = 0
    note: str = ""


@dataclass(frozen=True)
class AlgorithmDescription:
    """What a Processing algorithm does, its parameters and its outputs."""
    id: str
    name: str = ""
    group: str = ""
    help: str = ""
    # {"name", "type", "description", "optional", and when they apply "default", "options", "multiple", "parent",
    # "minimum", "maximum", "value" (how to give it), "destination" (an output FilterMate writes)}
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    # {"name", "type", "description"}
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    # Parameters that cannot be given (files, folders, connections): they stay unset.
    left_out: List[str] = field(default_factory=list)
    note: str = ""


@dataclass(frozen=True)
class AlgorithmRun:
    """What a Processing algorithm made: layers added to the project, and the values it answered."""
    algorithm: str
    name: str = ""
    # {"output", "layer_id", "name", "layer_kind", "feature_count"}
    layers: List[Dict[str, Any]] = field(default_factory=list)
    # Outputs the algorithm left empty or did not write.
    not_made: List[str] = field(default_factory=list)
    values: Dict[str, Any] = field(default_factory=dict)
    messages: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class StyleResult:
    """How a layer is drawn after a change: never the values of its classes."""
    layer_name: str
    mode: str = ""
    field: str = ""
    classes: int = 0
    ramp: str = ""
    method: str = ""
    # Raster: the band and the range of values stretched over the ramp.
    band: Optional[int] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    opacity: Optional[float] = None


@dataclass(frozen=True)
class LabelsResult:
    """The labels of a vector layer after a change."""
    layer_name: str
    labels: bool = False
    field: str = ""


@dataclass(frozen=True)
class EditResult:
    """An edit of features, in the edit buffer of the layer: nothing is saved until the user saves it."""
    layer_name: str
    changed: int = 0
    deleted: int = 0
    added: int = 0
    editing: bool = True
    unsaved: bool = True
    note: str = ""


@dataclass(frozen=True)
class LayoutResult:
    """A print layout added to the project."""
    name: str
    page: str = ""
    orientation: str = ""
    # map, title, legend, scale_bar, north_arrow: what it holds.
    items: List[str] = field(default_factory=list)
    # given, layer, view or layers: where the extent of its map comes from.
    extent_from: str = ""
    scale: Optional[float] = None
    layers: Any = None
    note: str = ""


@dataclass(frozen=True)
class LayoutExport:
    """A layout written to a file."""
    name: str
    format: str = ""
    dpi: int = 0
    # Relative to the export folder: the paths of this machine are not given out.
    path: str = ""
    bytes: int = 0


@dataclass(frozen=True)
class FieldAdded:
    """A field added to a layer, in its edit buffer."""
    layer_name: str
    field: str
    type: str = "text"
    computed: int = 0
    editing: bool = True
    unsaved: bool = True
    note: str = ""
    formula_error: str = ""


@dataclass(frozen=True)
class JoinAdded:
    """A join of the project: the fields of another layer beside each feature."""
    layer_name: str
    join_layer: str
    fields_added: List[str] = field(default_factory=list)
    note: str = ""


@dataclass(frozen=True)
class LayerTreeChange:
    """Layers put in a group of the layer tree."""
    group: str = ""
    groups_made: List[str] = field(default_factory=list)
    moved: List[str] = field(default_factory=list)
    not_found: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class LayerRename:
    """A layer under another name."""
    layer_id: str
    name: str
    previous: str = ""


@dataclass(frozen=True)
class Bookmarks:
    """The spatial bookmarks of the project after an action on one of them."""
    action: str
    name: str = ""
    bookmarks: List[str] = field(default_factory=list)
    replaced: bool = False
    extent_wkt: str = ""


@dataclass(frozen=True)
class MapThemes:
    """The map themes of the project after an action on one of them."""
    action: str
    name: str = ""
    themes: List[str] = field(default_factory=list)
    replaced: bool = False
    layers_shown: int = -1


@dataclass(frozen=True)
class ProjectCrs:
    """The CRS of the project after a change."""
    crs: str
    description: str = ""
    units: str = ""
    geographic: bool = False
    previous: str = ""
    note: str = ""


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
    # [xmin, ymin, xmax, ymax] of ``extent_wkt``, in ``canvas_crs``.
    extent: List[float] = field(default_factory=list)
    active_layer_id: str = ""
    active_layer_name: str = ""
    # {"layer_id", "name", "selected_count"} of the vector layers with a selection.
    selections: List[Dict[str, Any]] = field(default_factory=list)
    # Names of the print layouts of the project.
    layouts: List[str] = field(default_factory=list)
    # {"layer_id", "name", "crs_authid", "count", "area_m2", "extent_wkt"} of the rasters with objects drawn
    # in the dock (the SAM targets of the PIPETTE group): what ``dock_objects`` of a raster selection uses.
    drawn_objects: List[Dict[str, Any]] = field(default_factory=list)


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
class SegmentResult:
    """Objects SAM drew on a raster from guide features, added to the project as a polygon layer."""
    # Summary of the layer added: layer_id, name, layer_kind, provider_type, crs_authid, feature_count.
    layer: Dict[str, Any] = field(default_factory=dict)
    # Guide features given (-1 when not counted: a web service); those with an object; those without.
    guide_features: int = -1
    drawn: int = 0
    without_object: int = 0
    # The time allowed ran out before every feature was tried.
    stopped_early: bool = False
    seconds: float = 0.0
    # {"median", "minimum"} of the score SAM gives its masks.
    sam_score: Optional[Dict[str, Any]] = None
    # Polygon guides: {"median", "minimum", "below_half"} of the overlap of each footprint with its object.
    sam_iou: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class SimilarResult:
    """Objects that look like an example, found by SAM on a raster and added to the project as a polygon layer."""
    # Summary of the layer added; None when nothing was found (no layer added).
    layer: Optional[Dict[str, Any]] = None
    objects: int = 0
    # Places drawn by SAM; windows of 1024 pixels searched, and planned for the area.
    examined: int = 0
    windows: int = 0
    windows_planned: int = 0
    # The time allowed ran out before every window was searched.
    stopped_early: bool = False
    seconds: float = 0.0
    # {"count", "sam_score": {"median", "minimum"}, "area_m2": {"minimum", "maximum"}} of the examples as SAM drew them.
    examples: Dict[str, Any] = field(default_factory=dict)
    # {"median", "minimum"} of the appearance (cosine of the features with the example's) of the objects found.
    appearance: Optional[Dict[str, Any]] = None


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

    def layer_statistics(self, layer: str, field_name: str = "", group_by: str = "", measure: str = "",
                         selected_only: bool = False, limit: int = 20) -> Optional[LayerStatistics]:
        """Statistics of a field or of the geometries, ``None`` when the layer or a field does not resolve.

        Raises FilterRejected on a layer that cannot answer (not vector, web service, too many features).
        """
        ...

    def sample_features(self, layer: str, limit: int = 5, fields: Optional[List[str]] = None, expression: str = "",
                        selected_only: bool = False, geometry: bool = False) -> Optional[FeatureSample]:
        """A few features with their attributes, ``None`` when the layer does not resolve.

        Raises FilterRejected on a layer that cannot answer, an unknown field or a bad expression.
        """
        ...

    def identify_at(self, x: float, y: float, crs: str = "", layers: Optional[List[str]] = None,
                    tolerance: Optional[float] = None, limit: int = 5) -> IdentifyResult:
        """Features and raster values at a point; raises FilterRejected on a bad point, CRS or layer."""
        ...

    def find_algorithms(self, query: str, limit: int = 20) -> AlgorithmList:
        """Processing algorithms the agent may run whose id, name, group or tags hold every word of ``query``."""
        ...

    def describe_algorithm(self, algorithm_id: str) -> AlgorithmDescription:
        """Parameters and outputs of an algorithm; raises FilterRejected when it is unknown or may not be run."""
        ...

    def run_algorithm(self, algorithm_id: str, parameters: Optional[Dict[str, Any]] = None,
                      names: Optional[Dict[str, str]] = None, share_values: bool = True) -> AlgorithmRun:
        """Run an algorithm on project layers, its layers added to the project; raises FilterRejected when refused."""
        ...

    def set_layer_style(self, layer: str, mode: str, **options: Any) -> StyleResult:
        """Draw a layer anew (single, categorized, graduated, pseudocolor, gray); raises FilterRejected when refused."""
        ...

    def set_labels(self, layer: str, field: str = "", enabled: bool = True, size: Optional[float] = None,
                   color: str = "", buffer: bool = True) -> LabelsResult:
        """Label a vector layer with a field, or turn its labels off; raises FilterRejected when refused."""
        ...

    def update_features(self, layer: str, values: Optional[Dict[str, Any]] = None,
                        formulas: Optional[Dict[str, str]] = None, expression: str = "",
                        selected_only: bool = False) -> EditResult:
        """Set fields of chosen features in the edit buffer; raises FilterRejected when refused."""
        ...

    def delete_features(self, layer: str, expression: str = "", selected_only: bool = False) -> EditResult:
        """Delete chosen features in the edit buffer; raises FilterRejected when refused."""
        ...

    def add_features(self, layer: str, features: List[Dict[str, Any]], crs: str = "") -> EditResult:
        """Add features from WKT in the edit buffer; raises FilterRejected when refused."""
        ...

    def create_layout(self, name: str, **options: Any) -> LayoutResult:
        """A print layout of the map added to the project; raises FilterRejected when refused."""
        ...

    def export_layout(self, name: str, folder: str, file_format: str = "pdf", dpi: int = 150) -> LayoutExport:
        """Write a layout of the project into ``folder`` (resolved by the route); raises FilterRejected."""
        ...

    def set_project_crs(self, crs: str) -> ProjectCrs:
        """Set the CRS of the project and of the map; raises FilterRejected on an unknown CRS."""
        ...

    def add_field(self, layer: str, name: str, field_type: str = "text", length: int = 0,
                  formula: str = "") -> FieldAdded:
        """Add a field in the edit buffer, filled by ``formula`` when given; raises FilterRejected."""
        ...

    def join_layers(self, layer: str, join_layer: str, target_field: str, join_field: str,
                    fields: Optional[List[str]] = None, prefix: Optional[str] = None) -> JoinAdded:
        """Join ``join_layer`` to ``layer`` by a field; raises FilterRejected."""
        ...

    def group_layers(self, layers: List[str], group: str = "", at_top: bool = True,
                     above: str = "") -> LayerTreeChange:
        """Put layers in a group of the layer tree, made where missing, or just above a layer; raises FilterRejected
        when none is found."""
        ...

    def rename_layer(self, layer: str, name: str, group: bool = False) -> LayerRename:
        """Give a layer (or with ``group`` a group) another name; raises FilterRejected on an unknown one."""
        ...

    def bookmark(self, action: str, name: str = "", extent_wkt: str = "", crs: str = "") -> Bookmarks:
        """List, add, zoom to or remove a spatial bookmark; raises FilterRejected on an unknown one."""
        ...

    def map_theme(self, action: str, name: str = "") -> MapThemes:
        """List, save, apply or remove a map theme; raises FilterRejected on an unknown theme."""
        ...

    def preview_filter(self, layer_name: str, expression: str) -> Optional[FilterPreview]:
        """Try ``expression`` without touching the layer, ``None`` when the layer does not resolve.

        Raises FilterRejected on a layer that cannot be tried (not vector, web service).
        """
        ...

    def map_context(self) -> MapContext:
        """CRS, extent, active layer and selections of the QGIS window, and the objects drawn in the dock."""
        ...

    def segment_objects(self, raster: str, guide_layer: str, selected_only: bool = True, limit: int = 50,
                        name: str = "") -> SegmentResult:
        """SAM draws on a raster one object per guide feature, as a new polygon layer.

        Raises FilterRejected on layers that do not fit, too many features, or SAM not installed.
        """
        ...

    def similar_objects(self, raster: str, example_layer: str = "", use_dock_object: bool = False,
                        extent_wkt: str = "", extent_crs: str = "", same_shape: bool = True,
                        name: str = "") -> SimilarResult:
        """SAM finds on a raster the objects that look like an example, as a new polygon layer.

        Raises FilterRejected on layers or an example that do not fit, an area too large, or SAM not installed.
        """
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

    def add_basemap(self, platform: str, name: str = "", extra_domains: Optional[str] = None) -> LayerSummary:
        """Add a web basemap under the layers; raises FilterRejected when its server gives no tile."""
        ...

    def check_basemap(self, platform: str, extra_domains: Optional[str] = None) -> None:
        """Ask a basemap for one tile; raises FilterRejected when its server gives none."""
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
    # Rows of ``MapContext.drawn_objects``: the rasters that have objects drawn in the dock.
    drawn_objects: List[Dict[str, Any]] = field(default_factory=list)

    def list_layers(self) -> List[LayerSummary]:
        return [self._with_active(layer) for layer in self.layers]

    def _find(self, reference: str) -> Optional[LayerSummary]:
        """By id, then by name (the first of that name), as the plugin resolves a layer."""
        return (next((layer for layer in self.layers if layer.layer_id == reference), None)
                or next((layer for layer in self.layers if layer.name == reference), None))

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

    def layer_statistics(self, layer: str, field_name: str = "", group_by: str = "", measure: str = "",
                         selected_only: bool = False, limit: int = 20) -> Optional[LayerStatistics]:
        found = self._find(layer)
        if found is None:
            return None
        return LayerStatistics(layer_name=found.name, field=field_name, measure=measure, group_by=group_by,
                               selected_only=selected_only, feature_count=max(found.feature_count, 0))

    def sample_features(self, layer: str, limit: int = 5, fields: Optional[List[str]] = None, expression: str = "",
                        selected_only: bool = False, geometry: bool = False) -> Optional[FeatureSample]:
        found = self._find(layer)
        return None if found is None else FeatureSample(layer_name=found.name, crs_authid=found.crs_authid)

    def identify_at(self, x: float, y: float, crs: str = "", layers: Optional[List[str]] = None,
                    tolerance: Optional[float] = None, limit: int = 5) -> IdentifyResult:
        for reference in layers or []:
            if self._find(reference) is None:
                raise FilterRejected(f"layer {reference!r} not found")
        return IdentifyResult(x=x, y=y, crs=crs, tolerance=tolerance or 0.0)

    def find_algorithms(self, query: str, limit: int = 20) -> AlgorithmList:
        found = [{"id": "native:buffer", "name": "Buffer", "group": "Vector geometry", "summary": "Buffers"}]
        return AlgorithmList(query=query, algorithms=found if "buffer" in query.lower() else [],
                             total=1 if "buffer" in query.lower() else 0)

    def describe_algorithm(self, algorithm_id: str) -> AlgorithmDescription:
        if algorithm_id != "native:buffer":
            raise FilterRejected(f"no Processing algorithm {algorithm_id!r}")
        return AlgorithmDescription(id=algorithm_id, name="Buffer", parameters=[
            {"name": "INPUT", "type": "source", "description": "Input layer", "optional": False},
            {"name": "OUTPUT", "type": "sink", "description": "Buffered", "optional": False, "destination": "..."}])

    def run_algorithm(self, algorithm_id: str, parameters: Optional[Dict[str, Any]] = None,
                      names: Optional[Dict[str, str]] = None, share_values: bool = True) -> AlgorithmRun:
        self.describe_algorithm(algorithm_id)
        source = self._find(str((parameters or {}).get("INPUT", "")))
        if source is None:
            raise FilterRejected("INPUT is not a layer of the project")
        name = (names or {}).get("OUTPUT") or "Buffer"
        return AlgorithmRun(algorithm=algorithm_id, name="Buffer", layers=[
            {"output": "OUTPUT", "layer_id": "buffer_1", "name": name, "layer_kind": "vector",
             "feature_count": max(source.feature_count, 0)}])

    def set_layer_style(self, layer: str, mode: str, **options: Any) -> StyleResult:
        found = self._find(layer)
        if found is None:
            raise FilterRejected(f"layer {layer!r} not found")
        return StyleResult(layer_name=found.name, mode=mode, field=options.get("field") or "",
                           classes=options.get("classes", 5) if mode in ("categorized", "graduated") else 0)

    def set_labels(self, layer: str, field: str = "", enabled: bool = True, size: Optional[float] = None,
                   color: str = "", buffer: bool = True) -> LabelsResult:
        found = self._find(layer)
        if found is None:
            raise FilterRejected(f"layer {layer!r} not found")
        return LabelsResult(layer_name=found.name, labels=enabled, field=field if enabled else "")

    def create_layout(self, name: str, **options: Any) -> LayoutResult:
        if not name.strip():
            raise FilterRejected("a layout needs a name")
        return LayoutResult(name=name, page=options.get("page", "A4"), items=["map"])

    def export_layout(self, name: str, folder: str, file_format: str = "pdf", dpi: int = 150) -> LayoutExport:
        import os
        path = os.path.join(folder, f"{name}.{file_format}")
        return LayoutExport(name=name, format=file_format, dpi=dpi, path=path, bytes=1)

    def add_field(self, layer: str, name: str, field_type: str = "text", length: int = 0,
                  formula: str = "") -> FieldAdded:
        found = self._find(layer)
        if found is None:
            raise FilterRejected(f"layer {layer!r} not found")
        return FieldAdded(layer_name=found.name, field=name, type=field_type, computed=found.feature_count if formula else 0)

    def join_layers(self, layer: str, join_layer: str, target_field: str, join_field: str,
                    fields: Optional[List[str]] = None, prefix: Optional[str] = None) -> JoinAdded:
        found, other = self._find(layer), self._find(join_layer)
        if found is None or other is None or found is other:
            raise FilterRejected("give two different layers of the project")
        named = fields or [join_field]
        return JoinAdded(layer_name=found.name, join_layer=other.name,
                         fields_added=[f"{other.name + '_' if prefix is None else prefix}{name}" for name in named])

    def bookmark(self, action: str, name: str = "", extent_wkt: str = "", crs: str = "") -> Bookmarks:
        marks = getattr(self, "_bookmarks", [])
        if action in ("zoom", "remove") and name not in marks:
            raise FilterRejected(f"no bookmark {name!r}")
        if action == "add" and name not in marks:
            marks = marks + [name]
        elif action == "remove":
            marks = [mark for mark in marks if mark != name]
        self._bookmarks = marks
        return Bookmarks(action=action, name=name, bookmarks=list(marks))

    def group_layers(self, layers: List[str], group: str = "", at_top: bool = True,
                     above: str = "") -> LayerTreeChange:
        moved = [found.name for found in (self._find(name) for name in layers) if found is not None]
        if not moved:
            raise FilterRejected("no layer of the project among " + ", ".join(repr(name) for name in layers))
        return LayerTreeChange(group=group, groups_made=[group] if group else [], moved=moved,
                               not_found=[name for name in layers if self._find(name) is None])

    def rename_layer(self, layer: str, name: str, group: bool = False) -> LayerRename:
        if group:
            return LayerRename(layer_id="", name=name.strip(), previous=layer)
        found = self._find(layer)
        if found is None or not name.strip():
            raise FilterRejected(f"no layer {layer!r} in the project" if found is None else "give a name")
        return LayerRename(layer_id=found.layer_id, name=name.strip(), previous=found.name)

    def map_theme(self, action: str, name: str = "") -> MapThemes:
        themes = getattr(self, "_themes", [])
        if action == "save" and name not in themes:
            themes = themes + [name]
        elif action in ("apply", "remove") and name not in themes:
            raise FilterRejected(f"no map theme {name!r}")
        elif action == "remove":
            themes = [theme for theme in themes if theme != name]
        self._themes = themes
        return MapThemes(action=action, name=name, themes=list(themes))

    def set_project_crs(self, crs: str) -> ProjectCrs:
        if not crs.upper().startswith("EPSG:") and not crs.isdigit():
            raise FilterRejected(f"{crs!r} is no CRS QGIS knows")
        return ProjectCrs(crs=crs if ":" in crs else f"EPSG:{crs}")

    def _edited(self, layer: str, **counts: int) -> EditResult:
        found = self._find(layer)
        if found is None:
            raise FilterRejected(f"layer {layer!r} not found")
        return EditResult(layer_name=found.name, **counts)

    def update_features(self, layer: str, values: Optional[Dict[str, Any]] = None,
                        formulas: Optional[Dict[str, str]] = None, expression: str = "",
                        selected_only: bool = False) -> EditResult:
        if not values and not formulas:
            raise FilterRejected("give values or formulas")
        return self._edited(layer, changed=1)

    def delete_features(self, layer: str, expression: str = "", selected_only: bool = False) -> EditResult:
        return self._edited(layer, deleted=1)

    def add_features(self, layer: str, features: List[Dict[str, Any]], crs: str = "") -> EditResult:
        return self._edited(layer, added=len(features))

    def preview_filter(self, layer_name: str, expression: str) -> Optional[FilterPreview]:
        found = self._find(layer_name)
        if found is None:
            return None
        return FilterPreview(layer_name=found.name, expression=expression, valid=True,
                             feature_count=found.feature_count)

    def map_context(self) -> MapContext:
        return MapContext(drawn_objects=list(self.drawn_objects))

    def segment_objects(self, raster: str, guide_layer: str, selected_only: bool = True, limit: int = 50,
                        name: str = "") -> SegmentResult:
        image, guide = self._find(raster), self._find(guide_layer)
        if image is None or image.layer_kind != "raster":
            raise FilterRejected(f"raster layer {raster!r} not found")
        if guide is None or guide.layer_kind != "vector":
            raise FilterRejected(f"guide layer {guide_layer!r} not found")
        count = max(guide.feature_count, 0)
        if count > limit:
            raise FilterRejected(f"'{guide.name}' gives {count} guide features and at most {limit} are taken in one call")
        summary = LayerSummary(layer_id=f"L{len(self.layers) + 1}", name=name or f"{guide.name} (SAM)",
                               provider_type="memory", feature_count=count, geometry_type="MultiPolygon",
                               crs_authid=image.crs_authid)
        self.layers.append(summary)
        return SegmentResult(layer={"layer_id": summary.layer_id, "name": summary.name, "layer_kind": "vector",
                                    "provider_type": "memory", "crs_authid": summary.crs_authid, "feature_count": count},
                             guide_features=count, drawn=count)

    def similar_objects(self, raster: str, example_layer: str = "", use_dock_object: bool = False,
                        extent_wkt: str = "", extent_crs: str = "", same_shape: bool = True,
                        name: str = "") -> SimilarResult:
        image = self._find(raster)
        if image is None or image.layer_kind != "raster":
            raise FilterRejected(f"raster layer {raster!r} not found")
        if bool(example_layer) == bool(use_dock_object):
            raise FilterRejected("give an example: example_layer or use_dock_object, one of them")
        if use_dock_object and not any(image.layer_id == row.get("layer_id") for row in self.drawn_objects):
            raise FilterRejected(f"no object is drawn on '{image.name}' in the FilterMate dock")
        if example_layer and (self._find(example_layer) is None or self._find(example_layer).layer_kind != "vector"):
            raise FilterRejected(f"example layer {example_layer!r} not found among the vector layers")
        summary = LayerSummary(layer_id=f"L{len(self.layers) + 1}", name=name or f"{image.name} (similar objects)",
                               provider_type="ogr", feature_count=3, geometry_type="MultiPolygon",
                               crs_authid=image.crs_authid)
        self.layers.append(summary)
        return SimilarResult(layer={"layer_id": summary.layer_id, "name": summary.name, "layer_kind": "vector",
                                    "provider_type": "ogr", "crs_authid": summary.crs_authid, "feature_count": 3},
                             objects=3, examined=12, windows=1, windows_planned=1,
                             examples={"count": 1, "sam_score": {"median": 0.9, "minimum": 0.9}})

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

    def add_basemap(self, platform: str, name: str = "", extra_domains: Optional[str] = None) -> LayerSummary:
        summary = LayerSummary(layer_id=f"L{len(self.layers) + 1}", name=name or platform, provider_type="wms")
        self.layers.append(summary)
        return summary

    def check_basemap(self, platform: str, extra_domains: Optional[str] = None) -> None:
        return None

    def apply_filter(self, layer_name: str, expression: str, source: str) -> bool:
        found = self._find(layer_name)  # an id or a name
        if found is None:
            return False
        layer_name = found.name
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
        if (raster_selection or {}).get("dock_objects") and not any(
                source.layer_id == row.get("layer_id") for row in self.drawn_objects):
            return CrossFilterResult(error=f"no object is drawn on '{source.name}' in the FilterMate dock")
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

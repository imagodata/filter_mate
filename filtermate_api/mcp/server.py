"""MCP tools of FilterMate: one tool per REST endpoint, relayed by :class:`FilterMateClient`.

Compatible with ``mcp`` 1.x (``FastMCP``) and 2.x (``MCPServer``, the same
decorators under a new name).

The tool functions are ``async`` and run the blocking HTTP call in a worker
thread, so the server keeps answering protocol messages (cancellation, ping)
while QGIS works. A :class:`FilterMateAPIError` becomes a ``ToolError``: the SDK turns it into a
tool result flagged ``isError`` that carries the message.
"""

import asyncio
import json
import os
import sys
from typing import Annotated, Any, Dict, List, Literal, Optional, Sequence, Union
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field, model_validator

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
    from mcp.server.mcpserver.exceptions import ResourceError, ToolError
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server
    from mcp.server.fastmcp.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations

from ..layer_listing import DEFAULT_LIMIT, MAX_LIMIT, select_layers, short_filter
from .rest_client import FilterMateAPIError, FilterMateClient, quote_segment
from .settings import ConfigError, parse_settings

SERVER_NAME = "filtermate"
# How long a call that adds a layer may last before the client gives up, from the longest of the plugin's own limits
# (tests/api/test_mcp_add_layer_timeout.py reads them in the code):
#   30 s    the REST API waits that long for the main thread of QGIS to start the call (main_thread.py)
#   + 90 s  add_osm_features: Overpass has that long to answer (osm_features.REQUEST_TIMEOUT_MS)
#   + 240 s then the answer is converted, at most that long (terrain.READ_TIMEOUT_S, shared by elevation, population,
#           contours and OpenStreetMap; elevation asks its tiles for 20 s first, add_layer follows 4 redirects of
#           20 s and downloads for 180 s: both shorter)
#   + 60 s  what comes after the last limit: the reading that was told to stop ends its step, the layers are opened,
#           styled and added, the answer written
# 30 + 90 + 240 + 60 = 420. A client that gives up before the plugin does shows a timeout while the layers arrive,
# and a second call adds them again (330 s, the sum of the two limits alone, left no room for that).
ADD_LAYER_TIMEOUT = 420.0
# A local copy reads its service for STREAM_COPY.timeout_seconds at most (600 s by default), then writes its file.
LOCAL_COPY_TIMEOUT = 720.0

INSTRUCTIONS = """\
Drives FilterMate, the QGIS filtering plugin, through its local REST API. QGIS must be running with the API started.

Typical workflow: list_layers (names, ids, kinds), describe_layer and field_values (what a filter can test), \
preview_filter (try an expression), then cross_filter / select_features / zoom_to / geometry_filter / point_cloud_filter / \
apply_filter to filter, filter_state to see what is filtered now, export_layers to write the filtered layers, \
clear_filters to put layers back on their original source.
Objects on a raster: map_context lists those the user drew in the dock (cross_filter uses them with \
raster_selection dock_objects); segment_objects draws with SAM the objects that points or footprints point at, as a \
new layer; similar_objects finds the objects that look like an example, as a new layer to check.
undo_filter / redo_filter are not idempotent: after one (also after an error or a timeout), read filter_state \
before calling it again.

Filters change the layers of the open QGIS project in place (visible to the user at once). They can be reverted with \
clear_filters; undo_filter / redo_filter only cover the vector history of the dock. Nothing here edits the data \
itself. If a tool reports that QGIS is busy, nothing was changed: wait a few seconds and retry."""

Predicate = Literal["Intersect", "Contain", "Disjoint", "Equal", "Touch", "Overlap", "Are within", "Cross"]
Operator = Literal["AND", "OR", "AND NOT"]
LayerList = Annotated[List[str], Field(min_length=1, max_length=1000)]

_PREDICATES_DOC = (
    "Each tested as `target <predicate> source`, a target kept when any holds: Contain = the target contains the "
    "source, Are within = it lies inside, Disjoint = outside"
)
_OPERATOR_DOC = (
    "With each target's filter: AND narrows, OR widens, AND NOT removes this selection (from the whole layer when "
    "unfiltered); omit to replace it"
)


def _write(title: str, idempotent: bool, destructive: bool = False) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=False, destructiveHint=destructive,
                           idempotentHint=idempotent, openWorldHint=False)


class LayoutChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    do: Literal["add_text", "add_map", "add_legend", "add_scale_bar", "add_north_arrow", "add_table", "add_shape",
                "add_page", "move", "remove", "set_text", "set_map"]
    ref: str = Field(default="", max_length=100, description="The item (move, remove, set_*)")
    text: str = Field(default="", max_length=2000)
    font_size: Optional[float] = Field(default=None, ge=4, le=200)
    layer: str = Field(default="", max_length=1000, description="add_table")
    layers: Optional[List[str]] = Field(default=None, max_length=100)
    extent_layer: str = Field(default="", max_length=1000)
    overview_of: str = Field(default="", max_length=100)
    map: str = Field(default="", max_length=100, description="Linked map; default the largest")
    scale: Optional[float] = Field(default=None, ge=1)
    columns: Optional[List[str]] = Field(default=None, max_length=50)
    max_rows: Optional[int] = Field(default=None, ge=1, le=500)
    page: Optional[int] = Field(default=None, ge=1)
    x: Optional[float] = Field(default=None, ge=0, le=5000)
    y: Optional[float] = Field(default=None, ge=0, le=5000)
    width: Optional[float] = Field(default=None, ge=1, le=5000)
    height: Optional[float] = Field(default=None, ge=1, le=5000)


class RasterSelection(BaseModel):
    """Pixels kept on a raster source (same rules as the EXPLORING raster panel of the dock)."""

    model_config = ConfigDict(extra="forbid")

    band: int = Field(default=1, ge=1)
    mode: Literal["range", "classes", "expression"] = Field(
        default="range", description="range: minimum to maximum, inclusive; classes: pixel values in classes")
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    classes: List[int] = Field(default_factory=list)
    expression: str = Field(default="", max_length=2000, description='raster calculator: "mnt@1" > 1200')
    # derivative, segments, dock_objects: told by the skills terrain and raster-objects (token diet, lot 2)
    derivative: Literal["value", "slope_degrees", "slope_percent", "aspect", "hillshade", "roughness"] = Field(
        default="value", description="range: what the bounds apply to, the band read as a DTM")
    segments: List[str] = Field(default_factory=list, max_length=10000, description="WKT polygons, raster CRS")
    dock_objects: bool = Field(default=False, description="The objects drawn in the dock (drawn_objects); alone")

    @model_validator(mode="after")
    def _check_segments(self) -> "RasterSelection":
        if self.segments or self.dock_objects:
            from ..routers.filters import check_segments_selection
            check_segments_selection(self.segments, self.minimum, self.maximum, self.classes, self.expression,
                                     self.derivative, self.dock_objects)
        return self


class StyleRule(BaseModel):
    """One rule of a rule-based style: the features a condition keeps, and their color."""

    model_config = ConfigDict(extra="forbid")

    expression: str = Field(default="", max_length=2000, description=(
        'QGIS condition (NOT SQL): "population" > 10000; empty: every other feature'))
    color: str = Field(..., min_length=1, max_length=50)
    label: str = Field(default="", max_length=100, description="In the legend")
    width: Optional[float] = Field(default=None, gt=0, le=20, description="mm")


class OsmTag(BaseModel):
    """One OpenStreetMap tag asked: a key, and a value or nothing for any value."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1, max_length=60, pattern=r"^[A-Za-z][A-Za-z0-9_:.-]*$",
                     description="As OpenStreetMap writes it: amenity, building, highway, shop, landuse, addr:street")
    value: str = Field(default="", max_length=80, description="hospital, primary...; empty: any value of the key")


FormWidget = Literal["value_map", "value_relation", "range", "date", "checkbox", "text", "hidden",
                     "relation_reference", "default"]


class FormValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(..., min_length=1, max_length=1000)
    label: str = Field(default="", max_length=200)


class FormField(BaseModel):
    # How one field shows in the attribute form of its layer; what is left out stays as it is (no docstring: it would
    # weigh on every request that offers set_form).
    model_config = ConfigDict(extra="forbid")

    field: str = Field(..., min_length=1, max_length=200)
    alias: Optional[str] = Field(default=None, max_length=200)
    widget: Optional[FormWidget] = Field(default=None, description="default: QGIS chooses")
    values: Optional[List[Union[str, FormValue]]] = Field(default=None, max_length=500, description="value_map")
    layer: str = Field(default="", max_length=1000, description="value_relation: lookup layer")
    key: str = Field(default="", max_length=200, description="value_relation: field stored")
    value: str = Field(default="", max_length=200, description="value_relation: field shown")
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    format: str = Field(default="", max_length=200, description="date: shown as dd/MM/yyyy")
    multiline: Optional[bool] = None
    not_null: Optional[bool] = None
    unique: Optional[bool] = None
    expression: Optional[str] = Field(default=None, max_length=2000, description="Constraint, a QGIS condition")
    constraint_text: str = Field(default="", max_length=200)
    enforce: Optional[bool] = Field(default=None, description="Constraints refuse to save; default: they warn")
    default: Optional[str] = Field(default=None, max_length=2000, description=(
        "Expression: now(), @user_account_name, $area, 'text'"))
    default_on_update: Optional[bool] = None
    editable: Optional[bool] = Field(default=None, description="false: read only")


class PointCloudCriteria(BaseModel):
    """Points kept on a point cloud (ASPRS classes, ranges, return number, expression)."""

    model_config = ConfigDict(extra="forbid")

    classes: List[int] = Field(
        default_factory=list, description="ASPRS codes: 2 ground, 3-5 vegetation, 6 building, 9 water")
    z_min: Optional[float] = None
    z_max: Optional[float] = None
    intensity_min: Optional[float] = None
    intensity_max: Optional[float] = None
    return_number: Optional[int] = Field(default=None, ge=1, le=15)
    expression: str = Field(default="", max_length=2000, description="Classification = 6 AND Z > 1000; ANDed")


def _body(**fields: Any) -> Dict[str, Any]:
    """JSON body from tool arguments: models dumped, ``None`` left out (the API defaults apply)."""
    body: Dict[str, Any] = {}
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, BaseModel):
            value = value.model_dump(exclude_none=True)
        body[key] = value
    return body


def build_server(client: FilterMateClient) -> Any:
    """Build the MCP server whose tools call the REST API through ``client``."""
    mcp = _Server(SERVER_NAME, instructions=INSTRUCTIONS)

    async def call(method: str, path: str, body: Optional[Dict[str, Any]] = None,
                   timeout: Optional[float] = None) -> Any:
        try:
            return await asyncio.to_thread(client.request, method, path, body, timeout)
        except FilterMateAPIError as exc:
            # ToolError is the one exception whose message the SDK (2.x) shows the model.
            raise ToolError(str(exc)) from None

    # -- read-only tools -------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(title="List layers", readOnlyHint=True, openWorldHint=False))
    async def list_layers(
        kind: Annotated[Optional[Literal["vector", "raster", "point_cloud"]], Field(
            description="Only the layers of this kind")] = None,
        name_contains: Annotated[Optional[str], Field(max_length=200, description=(
            "Only the layers whose name holds this text (case ignored)"))] = None,
        limit: Annotated[int, Field(ge=1, le=MAX_LIMIT, description="At most this many layers")] = DEFAULT_LIMIT,
    ) -> Dict[str, Any]:
        """List the layers of the open QGIS project that FilterMate knows, as {"layers": [...]}.

        Each layer has layer_id, name, provider_type, feature_count (-1 when unknown), geometry_type, crs_authid,
        layer_kind (vector, raster or point_cloud), has_active_filter and active_filter_expression (cut past 200
        characters, with active_filter_expression_length: describe_layer gives it whole), visible (checked in the
        layer tree, with its groups) and group (the groups above it, joined by " / "). The layers come in the order
        of the layer tree, the one drawn on top first. "more" says how many matching layers were left out by limit.
        Call this first: the other tools take layer names or ids from it.
        """
        return select_layers(await call("GET", "/layers"), kind, name_contains, limit)

    @mcp.tool(annotations=ToolAnnotations(title="Filter status", readOnlyHint=True, openWorldHint=False))
    async def filter_status() -> Dict[str, Any]:
        """Snapshot of the filter session: status, active_filters ({layer name: subset string}), their count,
        last_applied_at / last_applied_layer / last_applied_source and last_error.

        Vector subset strings only. filter_state also covers raster and point cloud layers.
        """
        return await call("GET", "/filters/status")

    @mcp.tool(annotations=ToolAnnotations(title="Filter state", readOnlyHint=True, openWorldHint=False))
    async def filter_state() -> Dict[str, Any]:
        """Every layer FilterMate filters right now, of any kind, as {"layers": [...]}.

        Each row has layer_id, name, layer_kind, subset (the filter string, empty for a clipped raster; cut past 200
        characters, with subset_length: describe_layer gives it whole) and derived (true when the layer reads a
        clipped copy of its source). Use it to check what a filter did, and to find out what a previous call did
        when a request timed out.
        """
        return {"layers": [short_filter(row, "subset") for row in await call("GET", "/filters/state")]}

    @mcp.tool(annotations=ToolAnnotations(title="List favorites", readOnlyHint=True, openWorldHint=False))
    async def list_favorites() -> Dict[str, Any]:
        """List the favorites (saved filters) of the FilterMate project, as {"favorites": [...]}.

        Each has favorite_id (what apply_favorite takes), name, description, layer_name and expression.
        """
        return {"favorites": await call("GET", "/favorites")}

    @mcp.tool(annotations=ToolAnnotations(title="Describe a layer", readOnlyHint=True, openWorldHint=False))
    async def describe_layer(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Layer id or name, of any kind")],
    ) -> Dict[str, Any]:
        """What a layer is and what a filter can test on it: its fields, bands or point attributes.

        Returns its kind, provider, CRS, geometry, feature_count, subset (current filter), place in the tree, extent
        (own CRS), style; for a vector, sql_dialect (the language of its filter), fields [{name, type, alias?,
        filterable?}] (filterable false: virtual or joined, a filter cannot test it), joins and relations; for a
        raster, bands [{band, name, classes}] and pixel_size; for a point cloud, attributes.
        """
        return await call("GET", "/layers/details?" + urlencode({"layer": layer}))

    @mcp.tool(annotations=ToolAnnotations(title="Values of a field", readOnlyHint=True, openWorldHint=False))
    async def field_values(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        field: Annotated[str, Field(min_length=1, max_length=1000)],
        search: Annotated[str, Field(max_length=200, description="Values containing it, any case")] = "",
        limit: Annotated[int, Field(ge=1, le=200)] = 20,
    ) -> Dict[str, Any]:
        """Distinct values a field takes in what the layer shows now, to write a filter with their exact spelling.

        Returns values, truncated, and minimum and maximum of a number or date; no NULL. Refused on web services.
        """
        return await call("GET", "/layers/field-values?" + urlencode(
            {"layer": layer, "field": field, "search": search, "limit": limit}))

    @mcp.tool(annotations=ToolAnnotations(title="Statistics of a layer", readOnlyHint=True, openWorldHint=False))
    async def layer_statistics(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        field: Annotated[str, Field(max_length=1000, description="Empty: count the features, or use measure")] = "",
        group_by: Annotated[str, Field(max_length=1000, description="One row of statistics per value")] = "",
        measure: Annotated[Literal["", "length", "area"], Field(description=(
            "Of the geometries instead of a field: m (perimeter of polygons) or m2"))] = "",
        selected_only: bool = False,
        limit: Annotated[int, Field(ge=1, le=100, description=(
            "Top groups, by sum (else count)"))] = 10,
    ) -> Dict[str, Any]:
        """Count, sum, mean, minimum, maximum of a field or of the geometries of a layer, in all or by group,
        on what it shows or its selection: "how many", "what total", what a filter kept.

        Returns feature_count, statistics, unit, groups, groups_total, truncated, ranked_by. Refused on web services
        and above 500000 features: filter or select first.
        """
        return await call("POST", "/layers/statistics", _body(
            layer=layer, field=field, group_by=group_by, measure=measure, selected_only=selected_only, limit=limit))

    @mcp.tool(annotations=ToolAnnotations(title="Sample of features", readOnlyHint=True, openWorldHint=False))
    async def sample_features(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        limit: Annotated[int, Field(ge=1, le=20, description="At most this many features")] = 3,
        fields: Annotated[Optional[List[Annotated[str, Field(min_length=1, max_length=1000)]]], Field(
            max_length=50, description="Only these fields; the first 50 fields by default")] = None,
        expression: Annotated[str, Field(max_length=100_000, description=(
            'QGIS expression (NOT SQL) the features must match, as for select_features: "population" > 10000'))] = "",
        selected_only: Annotated[bool, Field(description="Only the selected features")] = False,
        geometry: Annotated[bool, Field(description=(
            "Also the type, centroid and bounding box of each geometry, in the layer CRS"))] = False,
    ) -> Dict[str, Any]:
        """A few features of a vector layer with their attributes, to see what its rows look like.

        Among the features the layer shows now (its filter applies). Returns crs_authid, features [{fid, attributes
        {field: value}, geometry {type, centroid, bbox}}], truncated (more features match), fields_truncated and
        scope. Long text is cut at 200 characters. A web service (WFS) is read only where the map shows it, without
        expression nor selection (scope: the features the map shows): zoom to the area first.
        """
        return await call("POST", "/layers/sample", _body(
            layer=layer, limit=limit, fields=fields, expression=expression, selected_only=selected_only,
            geometry=geometry))

    @mcp.tool(annotations=ToolAnnotations(title="Identify at a point", readOnlyHint=True, openWorldHint=False))
    async def identify_at(
        x: Annotated[float, Field(ge=-1e9, le=1e9, description="X or longitude of the point")],
        y: Annotated[float, Field(ge=-1e9, le=1e9, description="Y or latitude of the point")],
        crs: Annotated[str, Field(max_length=200, description=(
            "CRS of the point, such as EPSG:4326; the CRS of the map (canvas_crs of map_context) by default"))] = "",
        layers: Annotated[Optional[List[Annotated[str, Field(min_length=1, max_length=1000)]]], Field(
            max_length=20, description="Only these layers (ids or names); the visible layers by default")] = None,
        tolerance: Annotated[Optional[float], Field(ge=0, le=1e9, description=(
            "Search distance around the point, in the units of crs; five pixels of the map by default"))] = None,
        limit: Annotated[int, Field(ge=1, le=20, description="At most this many features per layer")] = 5,
    ) -> Dict[str, Any]:
        """What lies at a point of the map: the features of the vector layers and the values of the rasters there.

        As the Identify tool of QGIS. Returns layers, only those with something at the point: [{layer_name,
        layer_kind, features [{fid, attributes}], truncated}] for a vector layer, [{layer_name, layer_kind, values
        [{band, value}]}] for a raster; and skipped (web services, which are not read).
        """
        return await call("POST", "/map/identify", _body(
            x=x, y=y, crs=crs, layers=layers, tolerance=tolerance, limit=limit))

    @mcp.tool(annotations=ToolAnnotations(title="Find a Processing algorithm", readOnlyHint=True,
                                          openWorldHint=False))
    async def find_algorithms(
        query: Annotated[str, Field(min_length=1, max_length=200, description=(
            "Words in English, as QGIS names its algorithms: buffer, centroids, dissolve, clip, join attributes, "
            "voronoi, heatmap, slope..."))],
        limit: Annotated[int, Field(ge=1, le=50, description="At most this many algorithms")] = 20,
    ) -> Dict[str, Any]:
        """Find the Processing algorithms of QGIS the agent may run, by words of their id, name, group or tags.

        Only the algorithms of QGIS itself that make layers, or answer statistics, are listed: none that runs SQL
        or code, writes to a data source or a file, or reaches the network. Returns algorithms [{id, name, group,
        summary}] and total. Then describe_algorithm gives the parameters of one.
        """
        return await call("GET", "/processing/algorithms?" + urlencode({"query": query, "limit": limit}))

    @mcp.tool(annotations=ToolAnnotations(title="Describe a Processing algorithm", readOnlyHint=True,
                                          openWorldHint=False))
    async def describe_algorithm(
        algorithm_id: Annotated[str, Field(min_length=1, max_length=200, description=(
            "Id from find_algorithms, such as native:buffer"))],
    ) -> Dict[str, Any]:
        """What a Processing algorithm does, and how to give each of its parameters to run_algorithm.

        Returns help, parameters [{name, type, description, optional, default, options (an enum: give the index or
        the text), parent (the layer a field or a distance belongs to), minimum, maximum, value (how to give it),
        destination (an output: FilterMate writes it to a temporary layer)}] and outputs. left_out names parameters
        that cannot be given (files, folders, connections).
        """
        return await call("GET", "/processing/algorithm?" + urlencode({"id": algorithm_id}))

    @mcp.tool(annotations=_write("Run a Processing algorithm", idempotent=False))
    async def run_algorithm(
        algorithm_id: Annotated[str, Field(min_length=1, max_length=200, description="Id from find_algorithms")],
        parameters: Annotated[Optional[Dict[str, Any]], Field(description=(
            "Values by parameter name, as describe_algorithm says: layers by name or id, "
            '{"layer": ..., "selected_only": true} for the selected features of a source, numbers, text, the index '
            "or the text of an option. Outputs are written by FilterMate: leave them out, or pass false to skip an "
            "optional one."))] = None,
        names: Annotated[Optional[Dict[str, Annotated[str, Field(min_length=1, max_length=200)]]], Field(
            description="Name of the layer made by each output, by output name (OUTPUT...)")] = None,
    ) -> Dict[str, Any]:
        """Run a Processing algorithm of QGIS on layers of the project; the layers it makes are added to the project.

        Each output layer is a temporary file: export_layers keeps one for good. In the chat of FilterMate, undoing
        the turn removes them. Returns layers [{output, layer_id, name, layer_kind, feature_count}], values (what the
        algorithm answers besides layers: statistics...), not_made and messages (its warnings). Inputs are layers
        of the project only, never a path or a URL; expressions take the functions of select_features and math,
        text and geometry ones.
        """
        return await call("POST", "/processing/run", _body(algorithm_id=algorithm_id, parameters=parameters or {},
                                                           names=names))

    @mcp.tool(annotations=ToolAnnotations(title="Try a filter", readOnlyHint=True, openWorldHint=False))
    async def preview_filter(
        layer_name: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        expression: Annotated[str, Field(min_length=1, max_length=500_000, description="As for apply_filter")],
    ) -> Dict[str, Any]:
        """Try an expression alone on a private copy of the layer, never combined with its filter: nothing changes.

        Returns valid, feature_count (-1: unknown) and error. Refused on web services and memory layers.
        """
        return await call("POST", "/filters/preview", _body(layer_name=layer_name, expression=expression))

    @mcp.tool(annotations=ToolAnnotations(title="Map context", readOnlyHint=True, openWorldHint=False))
    async def map_context() -> Dict[str, Any]:
        """What the user is looking at in QGIS.

        Returns project_crs, canvas_crs, extent_wkt (the visible extent, usable as is with geometry_filter and
        canvas_crs), extent (the same as [xmin, ymin, xmax, ymax]), scale, layouts (the print layouts of the
        project, by name), active_layer_id, active_layer_name,
        selections [{layer_id, name, selected_count}] (the layers with selected features, which cross_filter uses as
        its source) and drawn_objects [{layer_id, name, crs_authid, count, area_m2, extent_wkt}] (the rasters on which
        the user drew objects in the FilterMate dock: cross_filter uses them with that raster as source_layer and
        raster_selection {"dock_objects": true}). available is false when QGIS has no map canvas.
        """
        return await call("GET", "/map/context")

    # -- filters ---------------------------------------------------------------

    @mcp.tool(annotations=_write("Apply a filter expression", idempotent=True))
    async def apply_filter(
        layer_name: Annotated[str, Field(min_length=1, max_length=1000, description="A VECTOR layer id or name")],
        expression: Annotated[str, Field(min_length=1, max_length=500_000, description=(
            "SQL WHERE clause without WHERE: \"population\" > 10000 AND \"dep\" = '31'. Comparisons, IN, LIKE, "
            "BETWEEN, IS NULL, simple functions; no subquery"))],
        source: Annotated[str, Field(max_length=200, description="Tag in the FilterMate log")] = "mcp",
        operator: Annotated[Optional[Operator], Field(description=(
            "With the current filter: AND narrows, OR widens, AND NOT takes the condition out; omit to replace"))]
            = None,
    ) -> Dict[str, Any]:
        """Set the filter (subset string) of one vector layer by its attributes; revert with clear_filters.

        Returns success, expression, replaced_filter (the filter it lost) and active_filters. GeoPackage and Shapefile
        may take an invalid expression silently and show nothing: a count of -1 or 0 says so, clear_filters recovers.
        """
        return await call("POST", "/filters/apply",
                          _body(layer_name=layer_name, expression=expression, source=source, operator=operator))

    @mcp.tool(annotations=_write("Undo the last vector filter", idempotent=False))
    async def undo_filter() -> Dict[str, Any]:
        """Undo the last step of the dock's vector filter history (the dock's Undo button).

        Returns the step rolled back to (layer_name, expression, is_clear) and active_filters. Only steps recorded
        by the dock itself are undone: nothing done through these tools (apply_filter, cross_filter,
        geometry_filter, point_cloud_filter, clear_filters, apply_favorite) is, so use clear_filters to revert
        those. Fails with 'Nothing to undo' when the history is empty. Not idempotent: each call undoes one more
        step, so after an error or a timeout read filter_state before calling again.
        """
        return await call("POST", "/filters/undo")

    @mcp.tool(annotations=_write("Redo the last undone vector filter", idempotent=False))
    async def redo_filter() -> Dict[str, Any]:
        """Redo the step undone last in the dock's vector filter history (the dock's Redo button).

        Same answer and same caution as undo_filter (not idempotent: read filter_state after an error or a timeout).
        Fails with 'Nothing to redo' when there is nothing to redo.
        """
        return await call("POST", "/filters/redo")

    @mcp.tool(annotations=_write("Cross filter", idempotent=True))
    async def cross_filter(
        source_layer: Annotated[str, Field(min_length=1, max_length=1000, description="Layer id or name")],
        target_layers: Annotated[LayerList, Field(description="Layers of any kind, not the source")],
        predicates: Annotated[List[Predicate], Field(max_length=8, description=_PREDICATES_DOC)] = ["Intersect"],  # noqa: B006
        buffer: Annotated[float, Field(ge=-1e7, le=1e7, description=(
            "Around the source, in metres (CRS units if projected); negative shrinks"))] = 0.0,
        coverage_min: Annotated[float, Field(ge=0, le=100, description=(
            "Polygon targets: minimum % of the target inside the source"))] = 0.0,
        operator: Annotated[Optional[Operator], Field(description=_OPERATOR_DOC)] = None,
        selected_only: Annotated[bool, Field(description=(
            "Vector source: its selected features, else what its filter keeps (a WFS is never read whole); "
            "false: all it shows"))] = True,
        raster_selection: Annotated[Optional[RasterSelection], Field(description=(
            "REQUIRED for a raster source: the pixels that make the area"))] = None,
        point_cloud_criteria: Annotated[Optional[PointCloudCriteria], Field(description=(
            "Point cloud source: the points that make the area (omit: those it shows)"))] = None,
        filter_source: Annotated[bool, Field(description="Raster source: mask it outside the selection too")] = False,
    ) -> Dict[str, Any]:
        """Filter layers of any kind (features, pixels, LiDAR points) by where they lie against the area of a source
        layer: a vector's selection, a raster's pixels, a point cloud's points. clear_filters reverts it.

        Returns filtered, failed, skipped and warnings ({layer: reason}; a warning: filtered, not exactly).
        """
        return await call("POST", "/filters/cross", _body(
            source_layer=source_layer, target_layers=target_layers, predicates=predicates, buffer=buffer,
            coverage_min=coverage_min, operator=operator, selected_only=selected_only,
            raster_selection=raster_selection, point_cloud_criteria=point_cloud_criteria,
            filter_source=filter_source))

    @mcp.tool(annotations=_write("Filter by a WKT geometry", idempotent=True))
    async def geometry_filter(
        wkt: Annotated[str, Field(min_length=1, max_length=1_000_000, description=(
            "WKT; an extent as a rectangle POLYGON"))],
        crs: Annotated[str, Field(min_length=1, max_length=64, description="EPSG:2154; x/longitude first")],
        target_layers: Annotated[LayerList, Field(description="Layers of any kind")],
        predicates: Annotated[List[Predicate], Field(max_length=8, description=_PREDICATES_DOC)] = ["Intersect"],  # noqa: B006
        buffer: Annotated[float, Field(ge=-1e7, le=1e7, description="In the CRS units of the first target")] = 0.0,
        coverage_min: Annotated[float, Field(ge=0, le=100, description=(
            "Polygon targets: minimum % inside"))] = 0.0,
        operator: Annotated[Optional[Operator], Field(description=_OPERATOR_DOC)] = None,
    ) -> Dict[str, Any]:
        """cross_filter with a WKT geometry (an extent, a drawn area) instead of a source layer.

        Same effect and answer; not in the undo history (clear_filters reverts).
        """
        return await call("POST", "/filters/geometry", _body(
            wkt=wkt, crs=crs, target_layers=target_layers, predicates=predicates, buffer=buffer,
            coverage_min=coverage_min, operator=operator))

    @mcp.tool(annotations=_write("Filter point clouds", idempotent=True))
    async def point_cloud_filter(
        layers: Annotated[LayerList, Field(description="Point cloud layers (LiDAR tiles...)")],
        criteria: Annotated[PointCloudCriteria, Field(description="At least one")],
        operator: Annotated[Optional[Operator], Field(description=(
            _OPERATOR_DOC))] = None,
    ) -> Dict[str, Any]:
        """Keep only some points (class, elevation, intensity, return, expression) on point cloud layers, the same
        criteria on each (all the tiles of a LiDAR set). undo_filter does not undo it: clear_filters does.

        Returns done, failed and skipped.
        """
        return await call("POST", "/filters/point-cloud", _body(layers=layers, criteria=criteria, operator=operator))

    @mcp.tool(annotations=_write("Clear filters", idempotent=True))
    async def clear_filters(
        layers: Annotated[LayerList, Field(description="Of any kind")],
    ) -> Dict[str, Any]:
        """Put layers back on their source with no filter (the dock's Unfilter): reverts cross_filter,
        geometry_filter, point_cloud_filter and apply_favorite.

        Returns done, failed and skipped.
        """
        return await call("POST", "/filters/clear", _body(layers=layers))

    @mcp.tool(annotations=_write("Apply a favorite", idempotent=True))
    async def apply_favorite(
        favorite_id: Annotated[str, Field(min_length=1, max_length=200, description=(
            "favorite_id from list_favorites"))],
    ) -> Dict[str, Any]:
        """Apply a saved favorite, as the dock's favorites menu does.

        Returns the step (layer_name, expression, is_clear) and active_filters. The favorite id must exist: use
        list_favorites first.
        """
        return await call("POST", f"/favorites/{quote_segment(favorite_id)}/apply")

    # -- driving QGIS ----------------------------------------------------------

    @mcp.tool(annotations=_write("Zoom the map", idempotent=True))
    async def zoom_to(
        layer: Annotated[Optional[str], Field(max_length=1000)] = None,
        extent_wkt: Annotated[Optional[str], Field(max_length=100_000, description="Instead of a layer")] = None,
        crs: Annotated[Optional[str], Field(max_length=64, description="Of the WKT: EPSG:2154")] = None,
        selected_only: Annotated[bool, Field(description="The layer's selection")] = False,
    ) -> Dict[str, Any]:
        """Zoom the map to a layer, its selection, a WKT extent, or everything (no argument); only the view changes.

        Returns extent_wkt and scale. Fails without a map window.
        """
        return await call("POST", "/map/zoom", _body(layer=layer, extent_wkt=extent_wkt, crs=crs, selected_only=selected_only))

    @mcp.tool(annotations=_write("Select features", idempotent=True))
    async def select_features(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        expression: Annotated[str, Field(max_length=100_000, description=(
            'QGIS expression (NOT SQL), plain conditions only: "population" > 10000, "nom" ILIKE \'saint%\', '
            "area($geometry) > 1000. Field names in double quotes, text in single quotes."))] = "",
        clear: Annotated[bool, Field(description="Empty the selection instead of selecting")] = False,
        add: Annotated[bool, Field(description="Add to the current selection instead of replacing it")] = False,
    ) -> Dict[str, Any]:
        """Select the features of a vector layer matching a QGIS expression, as the user would in QGIS.

        A selection is not a filter: the features stay visible, they are highlighted. Use it to make the source of
        cross_filter (which uses the selected features), or when the user asks to select. Returns layer_name and
        selected_count. Comparisons, IN, LIKE and simple text, number, date and geometry functions are accepted; other
        functions are refused.
        """
        return await call("POST", "/layers/select", _body(layer=layer, expression=expression, clear=clear, add=add))

    @mcp.tool(annotations=_write("Style a layer", idempotent=True))
    async def set_layer_style(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Layer id or name")],
        mode: Annotated[Literal["single", "categorized", "graduated", "rules", "pseudocolor", "gray", "hillshade", "keep"], Field(description=(
            "Vector: single, categorized, graduated, rules. Raster: pseudocolor, gray, hillshade. keep: only opacity "
            "and blend (the only mode for a WMS, WMTS or basemap)"))],
        rules: Annotated[Optional[List[StyleRule]], Field(max_length=20, description=(
            "rules: a feature takes the first rule it matches; end with an empty expression, or the rest is not "
            "drawn"))] = None,
        field: Annotated[str, Field(max_length=1000, description="categorized, graduated")] = "",
        color: Annotated[str, Field(max_length=50, description="single: #rrggbb or a name")] = "",
        ramp: Annotated[str, Field(max_length=100, description=(
            "QGIS ramp: Viridis, Spectral, Blues, RdYlGn, Magma, Turbo... Terrain for relief"))] = "",
        classes: Annotated[int, Field(ge=2, le=12, description="graduated, or pseudocolor with discrete")] = 5,
        method: Annotated[Literal["quantile", "equal_interval", "jenks", "pretty", "stddev"], Field(
            description="graduated")] = "quantile",
        invert: bool = False,
        opacity: Annotated[Optional[float], Field(ge=0, le=1)] = None,
        band: Annotated[int, Field(ge=1, le=1000, description="Raster")] = 1,
        minimum: Annotated[Optional[float], Field(description="Raster: ramp bounds (statistics by default)")] = None,
        maximum: Optional[float] = None,
        cut: Annotated[Optional[float], Field(gt=0, le=49, description=(
            "Raster: % left out at each end of the ramp"))] = None,
        discrete: Annotated[bool, Field(description="pseudocolor: flat steps")] = False,
        width: Annotated[Optional[float], Field(gt=0, le=20, description="single: line width, mm")] = None,
        blend: Annotated[Literal["", "normal", "multiply", "screen", "overlay", "soft_light"], Field(description=(
            "multiply darkens (a hillshade over colors); empty: unchanged"))] = "",
        z_factor: Annotated[Optional[float], Field(gt=0, le=1000, description=(
            "hillshade: 2 or 3 for a flat relief"))] = None,
        multidirectional: Annotated[bool, Field(description="hillshade")] = False,
    ) -> Dict[str, Any]:
        """Change how a layer is drawn: one symbol, categories, classes, rules, a raster ramp or a shaded relief,
        its opacity and blending. Replaces the style; a field of more than 100 values cannot be categorized.

        Returns mode, field, classes (how many), ramp, method; for a raster, band, minimum and maximum or a note. Undoing the turn of the
        chat brings the previous style back.
        """
        return await call("POST", "/layers/style", _body(
            layer=layer, mode=mode, field=field, color=color, ramp=ramp, classes=classes, method=method,
            invert=invert, opacity=opacity, band=band, minimum=minimum, maximum=maximum, cut=cut, discrete=discrete,
            width=width, blend=blend, z_factor=z_factor, multidirectional=multidirectional,
            rules=[rule.model_dump(exclude_none=True) for rule in rules] if rules else None))

    @mcp.tool(annotations=_write("Label a layer", idempotent=True))
    async def set_labels(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        field: Annotated[str, Field(max_length=1000)] = "",
        enabled: Annotated[bool, Field(description="false: labels off")] = True,
        size: Annotated[Optional[float], Field(ge=4, le=72, description="Points")] = None,
        color: Annotated[str, Field(max_length=50)] = "",
        buffer: Annotated[bool, Field(description="A halo, to read it on any background")] = True,
        expression: Annotated[str, Field(max_length=2000, description=(
            "Instead of field, QGIS (NOT SQL): \"nom\" || ' (' || \"population\" || ')'"))] = "",
        visible_from_scale: Annotated[Optional[float], Field(ge=1, le=1e9, description=(
            "50000: from 1:50 000 and closer"))] = None,
        placement: Annotated[Literal["auto", "curved", "horizontal"], Field(description=(
            "curved: along lines (contours, rivers)"))] = "auto",
    ) -> Dict[str, Any]:
        """Write the values of a field or an expression next to the features of a vector layer, or turn the labels
        off. Undoing the turn of the chat brings the previous labels back.

        Returns labels, field or expression, visible_from_scale and placement.
        """
        return await call("POST", "/layers/labels", _body(
            layer=layer, field=field, enabled=enabled, size=size, color=color, buffer=buffer, expression=expression,
            visible_from_scale=visible_from_scale, placement=placement))

    @mcp.tool(annotations=_write("Edit attributes of features", idempotent=False))  # a formula such as "pop" * 2
    async def update_features(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        values: Annotated[Optional[Dict[str, Any]], Field(description=(
            "Field: value, each converted to the type of its field (a number, a text, true or false, null)"))] = None,
        formulas: Annotated[Optional[Dict[str, Annotated[str, Field(max_length=10_000)]]], Field(description=(
            'Field: QGIS expression computed on each feature, such as "pop" * 2 or round($area / 10000, 2)'))] = None,
        expression: Annotated[str, Field(max_length=100_000, description=(
            'QGIS expression choosing the features ("nom" = \'Muret\'); the expression true for every feature'))] = "",
        selected_only: Annotated[bool, Field(description="Only the selected features")] = False,
    ) -> Dict[str, Any]:
        """Change attribute values of features, in the edit buffer of the layer: nothing is saved.

        The layer goes into editing mode; the user reviews the changes and saves them (Save Layer Edits) or discards
        them. Choose the features with expression and/or selected_only. Keys, joined and virtual fields are not
        changed; a value that does not fit its field is refused. Returns changed (features), editing and unsaved. In
        the chat of FilterMate, undoing the turn takes the changes back while they are not saved.
        """
        return await call("POST", "/layers/features/update", _body(
            layer=layer, values=values, formulas=formulas, expression=expression, selected_only=selected_only))

    @mcp.tool(annotations=_write("Delete features", idempotent=True, destructive=True))
    async def delete_features(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        expression: Annotated[str, Field(max_length=100_000, description="QGIS expression choosing the features")] = "",
        selected_only: Annotated[bool, Field(description="Only the selected features")] = False,
    ) -> Dict[str, Any]:
        """Delete features of a vector layer, in its edit buffer: they are gone from the data once the user saves.

        Only when the user asks to delete features; to hide them, filter the layer instead. The chat of FilterMate
        asks the user first. Returns deleted, editing and unsaved.
        """
        return await call("POST", "/layers/features/delete", _body(
            layer=layer, expression=expression, selected_only=selected_only))

    @mcp.tool(annotations=_write("Add features", idempotent=False))
    async def add_features(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        features: Annotated[List[Dict[str, Any]], Field(min_length=1, max_length=100, description=(
            '[{"wkt": "POINT(1.44 43.6)", "attributes": {"nom": "Puits"}}]: geometries of the type of the layer, coordinates in crs (the CRS of the layer by default; degrees only with EPSG:4326)'))],
        crs: Annotated[str, Field(max_length=200, description="CRS of the WKT, such as EPSG:4326; the layer's by default")] = "",
    ) -> Dict[str, Any]:
        """Add features to a vector layer from WKT geometries and attributes, in its edit buffer: nothing is saved.

        Returns added, editing and unsaved. In the chat of FilterMate, undoing the turn takes them back while they
        are not saved.
        """
        return await call("POST", "/layers/features/add", _body(layer=layer, features=features, crs=crs))

    @mcp.tool(annotations=_write("Make a print layout", idempotent=False))
    async def create_layout(
        name: Annotated[str, Field(min_length=1, max_length=100, description="New in the project")],
        title: Annotated[str, Field(max_length=200)] = "",
        page: Literal["A4", "A3", "A5", "Letter"] = "A4",
        orientation: Literal["landscape", "portrait"] = "landscape",
        layers: Annotated[Optional[List[Annotated[str, Field(min_length=1, max_length=1000)]]], Field(
            max_length=100, description="Default: those checked in the tree")] = None,
        extent: Annotated[Optional[List[float]], Field(min_length=4, max_length=4, description=(
            "xmin, ymin, xmax, ymax, project CRS; default: extent_layer, then the view"))] = None,
        extent_layer: Annotated[str, Field(max_length=1000, description="Show the whole of this layer")] = "",
        legend: bool = True,
        scale_bar: bool = True,
        north_arrow: bool = True,
        template: Annotated[str, Field(max_length=200, description=(
            "A template of the profile (describe_layout lists them): its page and items instead"))] = "",
    ) -> Dict[str, Any]:
        """Make a print layout of the map (title, legend, scale bar, north arrow), added to the project for the
        user to finish; export_layout writes it to a file. Undoing the turn of the chat removes it.

        Returns name, items, extent_from and the scale of its map.
        """
        return await call("POST", "/layouts", _body(
            name=name, title=title, page=page, orientation=orientation, layers=layers, extent=extent,
            extent_layer=extent_layer, legend=legend, scale_bar=scale_bar, north_arrow=north_arrow,
            template=template))

    @mcp.tool(annotations=_write("Export a print layout", idempotent=False, destructive=True))
    async def export_layout(
        name: Annotated[str, Field(min_length=1, max_length=100, description="A layout of the project (map_context lists them)")],
        format: Annotated[Literal["pdf", "png", "jpg", "svg", "tif"], Field(description="File format")] = "pdf",  # noqa: A002
        dpi: Annotated[int, Field(ge=72, le=600, description="Resolution")] = 150,
        subfolder: Annotated[str, Field(min_length=1, max_length=200, description=(
            "Sub-folder of the export root (a/b allowed, no ..)"))] = "layouts",
        georeference: Annotated[bool, Field(description="PDF: georeferenced; image: a world file beside it")] = True,
        atlas: Annotated[bool, Field(description="One page per feature of its atlas (set_atlas)")] = False,
        single_file: Annotated[bool, Field(description="Atlas in PDF: one file; false: one per feature")] = True,
    ) -> Dict[str, Any]:
        """Write a print layout of the project as PDF, PNG, JPG, SVG or TIFF in a sub-folder of the export root.

        A file of the same name there is kept: the new one is named <name>_2, <name>_3...; an image or SVG has one
        file per page. With atlas, a new folder <name>_atlas holds its pages (200 at most). The chat of FilterMate
        asks the user first. Returns path (relative to the sub-folder), bytes, and files and pages when several.
        """
        return await call("POST", "/layouts/export", _body(name=name, format=format, dpi=dpi, subfolder=subfolder,
                                                         georeference=georeference, atlas=atlas,
                                                         single_file=single_file))

    @mcp.tool(annotations=ToolAnnotations(title="Read a print layout", readOnlyHint=True, openWorldHint=False))
    async def describe_layout(
        name: Annotated[str, Field(max_length=100, description="A layout; empty: list the layouts and templates")] = "",
    ) -> Dict[str, Any]:
        """What a print layout holds: pages [{page, width_mm, height_mm}], items [{ref, type, page, x_mm, y_mm,
        width_mm, height_mm, and scale and layers of a map, text of a text}] and its atlas. Without a name, layouts
        and templates (the .qpt of the profile).
        """
        return await call("GET", "/layouts/details?" + urlencode({"name": name}))

    @mcp.tool(annotations=_write("Change a print layout", idempotent=False))
    async def edit_layout(
        layout: Annotated[str, Field(min_length=1, max_length=100, description="A layout of the project")],
        changes: Annotated[List[LayoutChange], Field(min_length=1, max_length=20)],
    ) -> Dict[str, Any]:
        """Change a print layout item by item, all or none: add a text ([% "nom" %] follows an atlas), a map
        (extent_layer, or overview_of a map: a map of situation), a legend, scale bar or north arrow (of map), an
        attribute table (layer, columns, max_rows), a frame or a page; move, remove; set_text, set_map (layers,
        extent_layer, scale). Items by ref (describe_layout); x, y, width, height in mm from the top left of page.
        Returns done and items. In the chat of FilterMate, undoing the turn puts the layout back.
        """
        return await call("POST", "/layouts/edit", _body(
            layout=layout, changes=[change.model_dump(exclude_defaults=True) | {"do": change.do}
                                    for change in changes]))

    @mcp.tool(annotations=_write("Set the atlas of a layout", idempotent=True))
    async def set_atlas(
        layout: Annotated[str, Field(min_length=1, max_length=100, description="A layout of the project")],
        coverage_layer: Annotated[str, Field(max_length=1000, description="Vector layer: one page per feature, as filtered now")] = "",
        enabled: Annotated[bool, Field(description="false turns the atlas off")] = True,
        filter: Annotated[str, Field(max_length=2000, description="QGIS expression: the features kept")] = "",  # noqa: A002
        page_name: Annotated[str, Field(max_length=2000, description="Expression naming each page")] = "",
        sort_by: Annotated[str, Field(max_length=2000, description="Expression ordering the pages")] = "",
        descending: bool = False,
        hide_coverage: Annotated[bool, Field(description="Hide the coverage layer on the maps")] = False,
        map_mode: Annotated[Literal["auto", "fixed", "predefined"], Field(description=(
            "auto: each feature plus margin; fixed: the scale of the map; predefined: the scales of the project"))] = "auto",
        margin: Annotated[float, Field(ge=0, le=500, description="%, auto")] = 10,
        file_name: Annotated[str, Field(max_length=2000, description="Expression naming the file of each page")] = "",
        maps: Annotated[Optional[List[Annotated[str, Field(max_length=100)]]], Field(
            max_length=20, description="refs of the maps that follow; default: the largest")] = None,
    ) -> Dict[str, Any]:
        """Turn the atlas of a print layout on: one page per feature of a vector layer as filtered now, its map
        following each feature; export_layout with atlas writes them. Returns pages, maps and map_mode. In the chat
        of FilterMate, undoing the turn puts the layout back as it was.
        """
        return await call("POST", "/layouts/atlas", _body(
            layout=layout, coverage_layer=coverage_layer, enabled=enabled, filter=filter, page_name=page_name,
            sort_by=sort_by, descending=descending, hide_coverage=hide_coverage, map_mode=map_mode, margin=margin,
            file_name=file_name, maps=maps))

    @mcp.tool(annotations=_write("Set the CRS of the project", idempotent=True))
    async def set_project_crs(
        crs: Annotated[str, Field(min_length=1, max_length=1000, description=(
            "EPSG:2154 (Lambert-93), EPSG:4326 (WGS 84), EPSG:3857 (Web Mercator), an EPSG code alone, a PROJ: "
            "string from suggest_crs, or a layer of the project whose CRS is taken"))],
    ) -> Dict[str, Any]:
        """Set the CRS of the project, which the map follows: what the user calls changing the CRS of the view.

        Layers in other CRS are reprojected on the fly, their data does not change. Returns crs, description, units,
        geographic and previous. In the chat of FilterMate, undoing the turn brings the previous CRS back.
        """
        return await call("POST", "/map/crs", _body(crs=crs))

    @mcp.tool(annotations=ToolAnnotations(title="Suggest projections", readOnlyHint=True, openWorldHint=False))
    async def suggest_crs(
        layers: Annotated[Optional[List[Annotated[str, Field(min_length=1, max_length=1000)]]], Field(
            max_length=100, description="Default: the layers shown, then the view")] = None,
        purpose: Annotated[Literal["general", "areas", "distances", "shapes", "world", "web"], Field(description=(
            "areas: equal-area; distances; shapes: conformal; world; web"))] = "general",
    ) -> Dict[str, Any]:
        """Projections suited to where the data lie and what the map is for, best first: the official system of the
        country, the local zone (UTM, Lambert CC), continental or world ones, and projections made for the data
        (PROJ: strings). Each says what it keeps. Returns bounds_wgs84, scale, current and suggestions [{crs, name,
        keeps, why, units}], each crs usable by set_project_crs. It changes nothing.
        """
        return await call("POST", "/map/crs/suggest", _body(layers=layers, purpose=purpose))

    @mcp.tool(annotations=_write("Add a field", idempotent=False))
    async def add_field(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        name: Annotated[str, Field(min_length=1, max_length=63, description="Name of the new field")],
        type: Annotated[Literal["integer", "integer64", "decimal", "text", "date", "datetime", "boolean"], Field(
            description="Type of the field")] = "text",
        length: Annotated[int, Field(ge=0, le=10000, description="Length of a text field; 0 lets the source choose")] = 0,
        formula: Annotated[str, Field(max_length=10000, description=(
            "QGIS expression computing the value of each feature (\"pop\" / $area * 1000000, upper(\"nom\")); "
            "empty leaves the field empty"))] = "",
    ) -> Dict[str, Any]:
        """Add a field to a vector layer, in its edit buffer: nothing is saved until the user saves the layer edits.

        With a formula the field is filled on every feature at once. Returns layer_name, field, type, computed (the
        features filled), and formula_error when the formula was refused (the field is then added, empty). In the chat
        of FilterMate, undoing the turn removes the field.
        """
        return await call("POST", "/layers/fields", _body(layer=layer, name=name, type=type, length=length,
                                                          formula=formula))

    @mcp.tool(annotations=_write("Join a layer", idempotent=False))
    async def join_layers(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Layer that gets the fields (id or name)")],
        join_layer: Annotated[str, Field(min_length=1, max_length=1000, description=(
            "Layer whose fields are shown beside it, a table without geometry too (id or name)"))],
        target_field: Annotated[str, Field(min_length=1, max_length=200, description="Field of layer to match")],
        join_field: Annotated[str, Field(min_length=1, max_length=200, description="Field of join_layer to match")],
        fields: Annotated[Optional[List[str]], Field(max_length=200, description=(
            "Fields of join_layer to show; all of them by default"))] = None,
        prefix: Annotated[Optional[str], Field(max_length=50, description=(
            "Put before the names of the fields shown; the name of join_layer and _ by default"))] = None,
    ) -> Dict[str, Any]:
        """Join two layers by a field: the fields of join_layer show beside each feature of layer whose target_field
        equals its join_field, as the Joins tab of the layer properties does. Nothing is written to either source.

        Returns layer_name, join_layer and fields_added (as they are named in layer). In the chat of FilterMate,
        undoing the turn removes the join.
        """
        return await call("POST", "/layers/join", _body(layer=layer, join_layer=join_layer, target_field=target_field,
                                                        join_field=join_field, fields=fields, prefix=prefix))

    @mcp.tool(annotations=_write("Set the form of a layer", idempotent=True))
    async def set_form(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        fields: Annotated[List[FormField], Field(min_length=1, max_length=50)],
    ) -> Dict[str, Any]:
        """Set how fields show in the attribute form of a layer, all or none; only what an entry gives changes, ""
        removes. Nothing is written to the data. Returns layer_name and fields. In the chat of FilterMate, undoing
        the turn puts the form back.
        """
        return await call("POST", "/layers/form", _body(
            layer=layer, fields=[entry.model_dump(exclude_defaults=True) for entry in fields]))

    @mcp.tool(annotations=_write("Relations of the project", idempotent=False))
    async def relations(
        action: Annotated[Literal["list", "add", "remove"], Field(description=(
            "add: each child feature points to a parent feature by a field"))],
        name: Annotated[str, Field(max_length=200, description="add: its name; remove: its id or name")] = "",
        parent_layer: Annotated[str, Field(max_length=1000, description="add, such as communes")] = "",
        parent_field: Annotated[str, Field(max_length=200, description="add: its key, such as insee")] = "",
        child_layer: Annotated[str, Field(max_length=1000, description="add, such as buildings")] = "",
        child_field: Annotated[str, Field(max_length=200, description="add: holds the parent's key")] = "",
        strength: Annotated[Literal["association", "composition"], Field(description=(
            "composition: children deleted with their parent"))] = "association",
    ) -> Dict[str, Any]:
        """The relations of the project: list, add or remove. The form of a parent lists its children. Nothing is
        written to the data. Returns relations [{id, name, parent, child, fields, strength}], or the relation added
        or removed. In the chat of FilterMate, undoing the turn takes it back.
        """
        return await call("POST", "/project/relations", _body(
            action=action, name=name, parent_layer=parent_layer, parent_field=parent_field, child_layer=child_layer,
            child_field=child_field, strength=strength))

    @mcp.tool(annotations=_write("Put layers in a group", idempotent=True))
    async def group_layers(
        layers: Annotated[LayerList, Field(description="Layer ids or names, in the order they take in the group")],
        group: Annotated[str, Field(max_length=1000, description=(
            "Group path from the top of the layer tree, such as Base or Base/Roads (made where missing); empty: "
            "the top of the tree itself"))] = "",
        at_top: Annotated[bool, Field(description="Put them first in the group (true) or last (false)")] = True,
        above: Annotated[str, Field(max_length=1000, description=(
            "A layer: put them just above it, in its group, so they are drawn over it; group and at_top are then "
            "not used"))] = "",
    ) -> Dict[str, Any]:
        """Organize the layer tree: put layers in a group, made where it is missing, first or last of it; or just above
        another layer, to draw them over it.

        Layers keep their data, style and visibility. Returns group, groups_made, moved and not_found. In the chat of
        FilterMate, undoing the turn puts each layer back and removes the groups it made.
        """
        return await call("POST", "/layers/group", _body(layers=layers, group=group, at_top=at_top, above=above))

    @mcp.tool(annotations=_write("Rename a layer", idempotent=True))
    async def rename_layer(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Layer id or name")],
        name: Annotated[str, Field(min_length=1, max_length=200, description="Its new name")],
        group: Annotated[bool, Field(description=(
            "true: layer is the path of a group of the layer tree (Base/Roads), and that group is renamed"))] = False,
    ) -> Dict[str, Any]:
        """Give a layer of the project another name, as shown in the layer tree and the legend; its data and source do
        not change. With group, rename a group of the layer tree instead. Returns layer_id, name and previous."""
        return await call("POST", "/layers/rename", _body(layer=layer, name=name, group=group))

    @mcp.tool(annotations=_write("Spatial bookmarks", idempotent=False))
    async def bookmark(
        action: Annotated[Literal["list", "add", "zoom", "remove"], Field(description=(
            "list the bookmarks; add one (the visible map, or extent_wkt; replaces a bookmark of that name); zoom the "
            "map to one; remove one"))],
        name: Annotated[str, Field(max_length=200, description="Name of the bookmark, for every action but list")] = "",
        extent_wkt: Annotated[str, Field(max_length=100000, description=(
            "For add: the area as WKT (its bounding box is kept); the visible map by default"))] = "",
        crs: Annotated[str, Field(max_length=200, description="CRS of extent_wkt; the CRS of the map by default")] = "",
    ) -> Dict[str, Any]:
        """Spatial bookmarks of the project: named places the user goes back to (Bookmarks panel of QGIS).

        Returns action, name, bookmarks (all names), replaced, and extent_wkt after a zoom. In the chat of FilterMate,
        undoing the turn brings the bookmarks back as they were.
        """
        return await call("POST", "/map/bookmarks", _body(action=action, name=name, extent_wkt=extent_wkt, crs=crs))

    @mcp.tool(annotations=_write("Map themes", idempotent=False))
    async def map_theme(
        action: Annotated[Literal["list", "save", "apply", "remove"], Field(description=(
            "list the themes; save the layers shown now and their styles under a name (replaces a theme of that "
            "name); apply a theme to the map; remove a theme"))],
        name: Annotated[str, Field(max_length=200, description="Name of the theme, for every action but list")] = "",
    ) -> Dict[str, Any]:
        """Map themes of the project: saved views of which layers are shown, with their styles, used by layouts and
        by the user to switch views. Returns action, name, themes (all of them), replaced and layers_shown. In the
        chat of FilterMate, undoing the turn brings the themes, the visibility and the styles back."""
        return await call("POST", "/map/themes", _body(action=action, name=name))

    @mcp.tool(annotations=_write("Show or hide layers", idempotent=True))
    async def set_layers_visibility(
        layers: Annotated[LayerList, Field(description="Layer ids or names")],
        visible: Annotated[bool, Field(description="true shows the layers, false hides them")],
    ) -> Dict[str, Any]:
        """Check or uncheck layers in the layer tree (shown or hidden on the map). Returns done and failed."""
        return await call("POST", "/layers/visibility", _body(layers=layers, visible=visible))

    @mcp.tool(annotations=ToolAnnotations(title="Options of a layer in the panels", readOnlyHint=True,
                                          openWorldHint=False))
    async def layer_options(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
    ) -> Dict[str, Any]:
        """What a layer shows in FilterMate's EXPLORING panel and its FILTERING options, with the values each takes;
        panel: whether EXPLORING shows it now, and then the buttons of its rail (set_exploring). Needs FilterMate's
        panel open."""
        return await call("GET", "/panels/layer?" + urlencode({"layer": layer}))

    @mcp.tool(annotations=_write("Set the options of layers in the panels", idempotent=True))
    async def set_layer_options(
        layers: Annotated[List[Dict[str, Any]], Field(min_length=1, max_length=50, description=(
            "[{layer, exploring, filtering}], each a vector layer id or name with the options to set"))],
        reason: Annotated[str, Field(max_length=500, description="Why, in the language of the user")] = "",
    ) -> Dict[str, Any]:
        """Set, all or none, what layers show in FilterMate's EXPLORING panel and their FILTERING options, as the user
        would in the panel. exploring: single_selection_expression and multiple_selection_expression (a field of the
        layer), custom_selection_expression (a QGIS expression), current_exploring_groupbox (single_selection,
        multiple_selection, custom_selection), is_tracking, is_linking. filtering: layers_to_filter,
        geometric_predicates, source_layer_combine_operator and other_layers_combine_operator (AND, AND NOT, OR),
        buffer_value (metres), buffer_type (Round, Flat, Square), buffer_segments, and the has_... box of each.
        Returns changed and shown_in_panel."""
        return await call("POST", "/panels/layer", _body(layers=layers, reason=reason))

    @mcp.tool(annotations=_write("Drive the EXPLORING panel", idempotent=True))
    async def set_exploring(
        layer: Annotated[str, Field(max_length=1000, description=(
            "Layer to show in EXPLORING, id or name; default: the one it shows"))] = "",
        tools: Annotated[Optional[Dict[str, bool]], Field(description="Buttons of the rail on (true) or off (false)")] = None,
        press: Annotated[Optional[List[str]], Field(max_length=4, description="Buttons pressed once")] = None,
        show: Annotated[bool, Field(description="Open EXPLORING in front: only when the user asks to see it")] = False,
        raster: Annotated[Optional[Dict[str, Any]], Field(description=(
            "band, quantity (value, slope_degrees, slope_percent, aspect, hillshade, roughness), minimum, maximum "
            "(null: no bound)"))] = None,
        point_cloud: Annotated[Optional[Dict[str, Any]], Field(description=(
            "classes [codes], or ranges [{attribute, minimum, maximum}]"))] = None,
    ) -> Dict[str, Any]:
        """Drive FilterMate's EXPLORING panel live, as the user does: show a layer in it, set what its panel keeps (the
        range of a raster on its histogram, the classes or ranges of a point cloud), turn the buttons of its rail on or
        off, press zoom or identify. The names of the buttons of each kind of layer: skill panels. One tool on the map
        at a time: it waits for the user's click, so say what to click. A button the user hid, or greyed, is refused:
        say so. In FilterMate's chat, undone with the turn. Returns layer_name, kind, in_view, tools (on, off, press,
        hidden, unavailable), changed, pressed, values."""
        return await call("POST", "/panels/exploring", _body(layer=layer, tools=tools, press=press, show=show,
                                                             raster=raster, point_cloud=point_cloud))

    @mcp.tool(annotations=ToolAnnotations(title="Export options of the panel", readOnlyHint=True,
                                          openWorldHint=False))
    async def export_options() -> Dict[str, Any]:
        """How the project exports from FilterMate's EXPORTING panel, with the formats it takes. Needs the panel."""
        return await call("GET", "/panels/export")

    @mcp.tool(annotations=_write("Set the export options of the panel", idempotent=True))
    async def set_export_options(
        changes: Annotated[Dict[str, Any], Field(description=(
            "layers_to_export, datatype_to_export (format), projection_to_export (EPSG:...), styles_to_export (QML, "
            "SLD), output_folder_to_export, zip_to_export (.zip path), batch_output_folder, batch_zip, and the has_... "
            "box of each"))],
        reason: Annotated[str, Field(max_length=500, description="Why, in the language of the user")] = "",
    ) -> Dict[str, Any]:
        """Prepare FilterMate's EXPORTING panel, all or none, for the user to export from it; this exports nothing
        (export_layers does). Returns changed and saved."""
        return await call("POST", "/panels/export", _body(changes=changes, reason=reason))

    @mcp.tool(annotations=_write("Draw objects with SAM", idempotent=False))
    async def segment_objects(
        raster: Annotated[str, Field(min_length=1, max_length=1000, description="An orthophoto, as on the map")],
        guide_layer: Annotated[str, Field(min_length=1, max_length=1000, description=(
            "Points (a click on each object) or polygons (footprints)"))],
        selected_only: Annotated[bool, Field(description=(
            "Its selection; with none, what it shows (a web service needs one)"))] = True,
        limit: Annotated[int, Field(ge=1, le=200, description="A guide that gives more is refused")] = 50,
        name: Annotated[str, Field(max_length=200, description="Default: the guide's, then (SAM)")] = "",
    ) -> Dict[str, Any]:
        """Draw with SAM, on a raster, the object each feature of a guide layer points at, as a new polygon layer
        with the guide's attributes, sam_score and, for footprints, sam_iou (low: a footprint to look at, no proof
        of a change). Good on buildings, not on parcels or trees.

        Returns layer, guide_features, drawn, without_object, sam_score, sam_iou, seconds and stopped_early (the
        20 s ran out: call again with fewer). QGIS is held about 2 s per 1024-pixel window. SAM is installed from
        the dock.
        """
        return await call("POST", "/objects/segment", _body(
            raster=raster, guide_layer=guide_layer, selected_only=selected_only, limit=limit, name=name))

    @mcp.tool(annotations=_write("Find objects like an example with SAM", idempotent=False))
    async def similar_objects(
        raster: Annotated[str, Field(min_length=1, max_length=1000, description="An orthophoto, as on the map")],
        example_layer: Annotated[str, Field(max_length=1000, description=(
            "Its ONE selected feature (point or footprint) is the example"))] = "",
        use_dock_object: Annotated[bool, Field(description=(
            "The examples: the objects drawn in the dock (drawn_objects of map_context)"))] = False,
        extent_wkt: Annotated[str, Field(max_length=100_000, description=(
            "Area searched (map_context's extent_wkt, its canvas_crs as extent_crs); empty: the map"))] = "",
        extent_crs: Annotated[str, Field(max_length=64, description="Empty: the raster's")] = "",
        same_shape: bool = True,
        name: Annotated[str, Field(max_length=200)] = "",
    ) -> Dict[str, Any]:
        """Find with SAM, on a raster, the objects that look like an example (0.5 to 2 times its area), as a new
        layer with appearance (0 to 1) and area_m2. About half is right and most are missed: no census, the user
        checks. Give only the place meant: past 20 s it stops, above 64 windows of 1024 pixels it is refused.

        Returns layer (null: nothing found), objects, windows, stopped_early, seconds, examples and appearance.
        SAM is installed from the dock.
        """
        return await call("POST", "/objects/similar", _body(
            raster=raster, example_layer=example_layer, use_dock_object=use_dock_object, extent_wkt=extent_wkt,
            extent_crs=extent_crs, same_shape=same_shape, name=name))

    @mcp.tool(annotations=ToolAnnotations(title="Add a layer", readOnlyHint=False, destructiveHint=False,
                                          idempotentHint=False, openWorldHint=True))
    async def add_layer(
        source: Annotated[str, Field(min_length=1, max_length=2000, description=(
            "A local data file on the QGIS machine (gpkg, shp, geojson, json, kml, gml, gpx, fgb, csv, xlsx, parquet, "
            "tif, or a point cloud: las, laz, copc.laz; a GeoPackage table with |layername=name), or a public https "
            "URL of a vector or raster file (a resource url from search_open_data). Nothing else: no http, no "
            "provider URI, no database connection."))],
        name: Annotated[str, Field(max_length=200, description="Name of the layer in the project (default: the file name)")] = "",
        kind: Annotated[Literal["vector", "raster", "point_cloud"], Field(description=(
            "vector (default), raster, or point_cloud (a local las or laz file is one whatever is given here)"))] = "vector",
    ) -> Dict[str, Any]:
        """Add a layer to the open project from a local file or a public https URL.

        Typical use after search_open_data: pick a geojson or gpkg resource url and add it, then filter it like any
        other layer. A remote file is read where it is when its server gives parts of it (GeoPackage, GeoTIFF, zip);
        any other is first copied to the QGIS profile (512 MB and 3 minutes at most). When it cannot be added the
        error says why: try another resource of the dataset, or a service layer. Returns the layer summary (layer_id,
        name, layer_kind, provider_type, crs_authid, feature_count). The chat of FilterMate asks the user first.
        """
        return await call("POST", "/layers/add", _body(source=source, name=name, kind=kind), timeout=ADD_LAYER_TIMEOUT)

    @mcp.tool(annotations=ToolAnnotations(title="Add a layer of a web service", readOnlyHint=False, destructiveHint=False,
                                          idempotentHint=False, openWorldHint=True))
    async def add_service_layer(
        platform: Annotated[str, Field(min_length=1, max_length=200, description=(
            "A WFS, WMS or WMTS platform the user allowed, e.g. ign_wfs (IGN Géoplateforme, data), ign_wmts or ign_wms "
            "(IGN Géoplateforme, images)"))],
        typename: Annotated[str, Field(min_length=1, max_length=300, description=(
            "Layer id given by search_open_data on that platform, e.g. ADMINEXPRESS-COG-CARTO.LATEST:commune"))],
        name: Annotated[str, Field(max_length=200, description="Name of the layer in the project (default: its title)")] = "",
    ) -> Dict[str, Any]:
        """Add a layer of a WFS, WMS or WMTS service, read from the service as the map moves.

        A WFS layer is data, filtered on the server. A WMS or WMTS layer is an image drawn by the service (old maps,
        orthophotos of a year, cadastre, land cover): put under the other layers, it has no values to filter, read
        nor export. Only a layer the service lists can be added. Returns the layer summary. The chat of FilterMate
        asks the user first.
        """
        return await call("POST", "/layers/add-service", _body(platform=platform, typename=typename, name=name))

    @mcp.tool(annotations=ToolAnnotations(title="Add a web basemap", readOnlyHint=False, destructiveHint=False,
                                          idempotentHint=False, openWorldHint=True))
    async def add_basemap(
        platform: Annotated[str, Field(min_length=1, max_length=2000, description=(
            "A basemap the user allowed: osm_tiles (OpenStreetMap), carto_light (neutral light grey), "
            "carto_light_nolabels (the same with no place names, under layers that have labels), carto_dark, "
            "carto_voyager, ign_plan and ign_ortho (France: map and aerial photographs), google_satellite (worldwide "
            "satellite and aerial photographs), opentopomap (relief), or one the user added, by the name the chat "
            "lists it under"))],
        name: Annotated[str, Field(max_length=200, description="Name of the layer in the project (default: its title)")] = "",
    ) -> Dict[str, Any]:
        """Add a web basemap (XYZ tiles) to the project, under every other layer.

        A basemap is an image drawn by its server as the map moves: a background, with no values to filter, read
        nor export. Only a basemap of the list can be added, and in the chat of FilterMate only one the user ticked;
        an address is never written here. Returns the layer summary. The chat of FilterMate asks the user first.
        """
        return await call("POST", "/layers/add-basemap", _body(platform=platform, name=name))

    @mcp.tool(annotations=ToolAnnotations(title="Add the elevation of an area", readOnlyHint=False,
                                          destructiveHint=False, idempotentHint=False, openWorldHint=True))
    async def add_elevation(
        extent_wkt: Annotated[str, Field(max_length=100_000, description=(
            "The area as WKT: the extent_wkt of find_place or of map_context. Empty: the visible map"))] = "",
        crs: Annotated[str, Field(max_length=64, description=(
            "CRS of extent_wkt: EPSG:4326 for find_place; the CRS of the map when empty"))] = "",
        platform: Annotated[str, Field(min_length=1, max_length=200, description=(
            "An elevation source the user allowed: copernicus_dem (worldwide, 30 m)"))] = "copernicus_dem",
        resolution: Annotated[Optional[float], Field(ge=10, le=5000, description=(
            "Pixel size in metres (default 30, coarser for a large area)"))] = None,
        target_crs: Annotated[str, Field(max_length=64, description=(
            "A CRS in metres to write in (default: the project's when its projection keeps angles, as UTM, Lambert "
            "conformal or a stereographic does, else the UTM zone)"))] = "",
        name: Annotated[str, Field(max_length=200, description="Name of the layer in the project")] = "",
    ) -> Dict[str, Any]:
        """Add the elevation of an area to the project as a raster layer (a digital elevation model), read from an
        elevation source the user allowed.

        Written on a grid in metres, added under the data and above the basemaps. Then set_layer_style (pseudocolor
        or hillshade) and contour_lines. Returns layer_id, name, crs_authid, resolution, minimum, maximum and mean
        (the heights, in metres) and note. The chat of FilterMate asks the user first.
        """
        return await call("POST", "/layers/add-elevation", _body(
            platform=platform, extent_wkt=extent_wkt, crs=crs, resolution=resolution, target_crs=target_crs,
            name=name), timeout=ADD_LAYER_TIMEOUT)

    @mcp.tool(annotations=ToolAnnotations(title="Add the population of an area", readOnlyHint=False,
                                          destructiveHint=False, idempotentHint=False, openWorldHint=True))
    async def add_population(
        extent_wkt: Annotated[str, Field(max_length=100_000, description=(
            "The area as WKT: the extent_wkt of find_place or of map_context. Empty: the visible map"))] = "",
        crs: Annotated[str, Field(max_length=64, description=(
            "CRS of extent_wkt: EPSG:4326 for find_place; the CRS of the map when empty"))] = "",
        platform: Annotated[str, Field(min_length=1, max_length=200, description=(
            "A population source the user allowed: meta_population (most countries, 30 m)"))] = "meta_population",
        resolution: Annotated[Optional[float], Field(ge=30, le=10_000, description=(
            "Pixel size in metres: 100 by default (a street), 1000 for a region"))] = None,
        name: Annotated[str, Field(max_length=200, description="Name of the layer in the project")] = "",
    ) -> Dict[str, Any]:
        """Add the people of an area to the project as a raster of people per pixel, read from a population source
        the user allowed: how many live there, where they are dense.

        Pixels are summed, never averaged. Returns layer_id, total (the people of the rectangle around the area),
        maximum (in one pixel), resolution and note. The chat of FilterMate asks the user first.
        """
        return await call("POST", "/layers/add-population", _body(
            platform=platform, extent_wkt=extent_wkt, crs=crs, resolution=resolution, name=name),
            timeout=ADD_LAYER_TIMEOUT)

    @mcp.tool(annotations=ToolAnnotations(title="Add OpenStreetMap features", readOnlyHint=False,
                                          destructiveHint=False, idempotentHint=False, openWorldHint=True))
    async def add_osm_features(
        tags: Annotated[List[OsmTag], Field(min_length=1, max_length=10, description=(
            'Features with ONE of these tags: [{"key": "amenity", "value": "hospital"}], [{"key": "building"}]'))],
        extent_wkt: Annotated[str, Field(max_length=100_000, description=(
            "extent_wkt of find_place or map_context; empty: the map"))] = "",
        crs: Annotated[str, Field(max_length=64, description=(
            "CRS of extent_wkt: EPSG:4326 for find_place; the CRS of the map when empty"))] = "",
        geometry: Annotated[Literal["as_mapped", "points", "lines", "polygons"], Field(description=(
            "as_mapped: a layer per geometry; points: one point each, to count or for a heatmap"))] = "as_mapped",
        platform: Annotated[str, Field(min_length=1, max_length=200, description=(
            "A server the user allowed"))] = "overpass_fr",
        name: Annotated[str, Field(max_length=180)] = "",
    ) -> Dict[str, Any]:
        """Add the OpenStreetMap features that carry given tags in an area (buildings, roads, hospitals, shops,
        parks...), anywhere, in EPSG:4326 with osm_id, name and a column per key (addr:street: addr_street). A town
        or a district, not a region.

        Returns layers [{layer_id, name, geometry, feature_count, fields}] and feature_count.
        """
        return await call("POST", "/layers/add-osm", _body(
            tags=[tag.model_dump() for tag in tags], platform=platform, extent_wkt=extent_wkt, crs=crs,
            geometry=geometry, name=name), timeout=ADD_LAYER_TIMEOUT)

    @mcp.tool(annotations=_write("Draw contour lines", idempotent=False))
    async def contour_lines(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description=(
            "Raster layer id or name: an elevation model (the layer of add_elevation)"))],
        interval: Annotated[float, Field(gt=0, le=100_000, description=(
            "Height between two contours, in the units of the raster: 25 for a line every 25 m"))],
        index_interval: Annotated[Optional[float], Field(gt=0, le=1_000_000, description=(
            "Height between two index contours, a multiple of interval (100)"))] = None,
        band: Annotated[int, Field(ge=1, le=1000, description="The band read")] = 1,
        name: Annotated[str, Field(max_length=200, description="Name of the layer made")] = "",
        min_length: Annotated[Optional[float], Field(ge=0, le=1e9, description=(
            "Closed contours shorter than this are left out (default: ten pixels; 0 keeps all)"))] = None,
    ) -> Dict[str, Any]:
        """Draw the contour lines of an elevation raster of the project as a new line layer, added on top.

        Each line has elevation (its height) and is_index (1 for an index contour); the layer comes in thin lines
        with the index contours thicker. A temporary file: export_layers keeps it. Returns layer_id, name,
        feature_count, index_count, left_out, minimum and maximum (the levels drawn).
        """
        return await call("POST", "/layers/contours", _body(
            layer=layer, interval=interval, index_interval=index_interval, band=band, name=name,
            min_length=min_length),
            timeout=ADD_LAYER_TIMEOUT)

    @mcp.tool(annotations=_write("Duplicate a layer", idempotent=False))
    async def duplicate_layer(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector or raster layer id or name")],
        name: Annotated[str, Field(max_length=200, description="Name of the new layer")] = "",
    ) -> Dict[str, Any]:
        """Add a second layer on the same data as a layer, with its style and filter, just above it: for what one
        layer cannot show at once (an elevation as colors and as a hillshade). Returns its summary.
        """
        return await call("POST", "/layers/duplicate", _body(layer=layer, name=name))

    @mcp.tool(annotations=ToolAnnotations(title="Copy a web service layer locally", readOnlyHint=False,
                                          destructiveHint=False, idempotentHint=False, openWorldHint=True))
    async def local_copy(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description=(
            "Layer id or name of a web service: WFS, OGC API Features, WMS, WMTS or XYZ tiles"))],
        action: Annotated[Literal["copy", "back", "again"], Field(description=(
            "copy: read the service over the area into a file the layer then reads; back: the layer reads its "
            "service again (the file stays); again: copy the area of its copy anew, the old file replaced"))] = "copy",
        extent_wkt: Annotated[str, Field(max_length=100_000, description=(
            "The area as WKT (the extent_wkt of find_place or map_context). Empty: the visible map"))] = "",
        crs: Annotated[str, Field(max_length=64, description=(
            "CRS of extent_wkt: EPSG:4326 for find_place; the CRS of the map when empty"))] = "",
    ) -> Dict[str, Any]:
        """Copy a web service layer over an area to a file next to the project (GeoPackage for features, GeoTIFF for
        a web map), and the layer reads it with its style and filter: faster, and without the network.

        A web map is copied as a still image at the finest level the budget affords. Returns reads, file,
        feature_count or resolution, complete and notes. OpenStreetMap and Google tiles are refused. The chat of
        FilterMate asks the user first.
        """
        return await call("POST", "/layers/local-copy", _body(layer=layer, action=action, extent_wkt=extent_wkt,
                                                               crs=crs), timeout=LOCAL_COPY_TIMEOUT)

    @mcp.tool(annotations=ToolAnnotations(title="Search satellite imagery", readOnlyHint=True, openWorldHint=True))
    async def search_imagery(
        bbox: Annotated[Optional[List[float]], Field(min_length=4, max_length=4, description=(
            "[west, south, east, north] in degrees; omit for the current map extent"))] = None,
        start: Annotated[str, Field(max_length=10, description="First day, YYYY-MM-DD")] = "",
        end: Annotated[str, Field(max_length=10, description="Last day, YYYY-MM-DD")] = "",
        max_cloud: Annotated[float, Field(ge=0, le=100, description="Maximum cloud cover, %")] = 20.0,
        collections: Annotated[Optional[List[str]], Field(max_length=5, description=(
            "STAC collections (default sentinel-2-l2a)"))] = None,
        limit: Annotated[int, Field(ge=1, le=20, description="Maximum number of scenes")] = 5,
        platform: Annotated[str, Field(max_length=200, description="STAC catalog the user allowed, e.g. earth_search")] = "earth_search",
    ) -> Dict[str, Any]:
        """Find satellite scenes over an area, newest first, with the GeoTIFF of each one.

        Returns datasets [{id, publisher (collection), description (date and cloud cover), resources: [{format, url}]}];
        format visual is the natural colour image. Then add_layer with its url and kind raster.
        """
        return await call("POST", "/open-data/imagery", _body(
            bbox=bbox, start=start, end=end, max_cloud=max_cloud, collections=collections, limit=limit, platform=platform))

    @mcp.tool(annotations=_write("Remove layers", idempotent=True, destructive=True))
    async def remove_layers(
        layers: Annotated[LayerList, Field(description="Layer ids or names to remove from the project")],
    ) -> Dict[str, Any]:
        """Remove layers from the project, only when the user asks to remove them: never to hide or to filter a
        layer (set_layers_visibility, apply_filter). Their files are not deleted. The chat of FilterMate asks the user first,
        and undoing the turn there brings the layers back with their styles and filters, except a layer held in
        memory, whose features are lost. From another client it cannot be undone. Returns done and failed."""
        return await call("POST", "/layers/remove", _body(layers=layers))

    @mcp.tool(annotations=ToolAnnotations(title="Search open data", readOnlyHint=True, openWorldHint=True))
    async def search_open_data(
        query: Annotated[str, Field(min_length=1, max_length=200, description="Words to search, in the language of the platform")],
        platform: Annotated[str, Field(max_length=200, description=(
            "datagouv (data.gouv.fr, France), opendatasoft (the public Opendatasoft hub), ign_wfs (IGN Géoplateforme "
            "layers), or a portal the user allowed"))] = "datagouv",
        limit: Annotated[int, Field(ge=1, le=20, description="Maximum number of datasets")] = 10,
    ) -> Dict[str, Any]:
        """Search datasets on an open data platform the user allowed, and get the URLs a layer can be made of.

        Returns datasets [{id, title, publisher, description, page, resources: [{title, format, url}]}], the
        resources kept to files add_layer can open (geojson, gpkg, zip, csv, tif...). Then add_layer with a
        resource url (geojson or gpkg first), or add_service_layer with the id on a WFS, WMS or WMTS platform. The query is sent to
        the platform.
        """
        return await call("POST", "/open-data/search", _body(query=query, platform=platform, limit=limit))

    @mcp.tool(annotations=ToolAnnotations(title="Find a place", readOnlyHint=True, openWorldHint=True))
    async def find_place(
        query: Annotated[str, Field(min_length=1, max_length=200, description=(
            "The name of a place or an address, as the user wrote it: Toulouse, 12 rue de la Paix Paris"))],
        platform: Annotated[str, Field(max_length=200, description=(
            "A geocoder the user allowed: ign_geocoder (IGN Géoplateforme: France, addresses and communes), photon "
            "(worldwide, from OpenStreetMap)"))] = "ign_geocoder",
        limit: Annotated[int, Field(ge=1, le=10, description="Maximum number of places")] = 5,
    ) -> Dict[str, Any]:
        """Find where a place is, by its name or its address, on a geocoder the user allowed.

        Returns places [{name, label, kind, longitude, latitude, extent_wkt}], the best match first. To show one, call
        zoom_to with its extent_wkt and crs EPSG:4326. When several places could be the one meant, ask the user
        which. The query is sent to the geocoder; nothing of the project is.
        """
        return await call("POST", "/places/find", _body(query=query, platform=platform, limit=limit))

    # -- export ----------------------------------------------------------------

    @mcp.tool(annotations=_write("Export filtered layers", idempotent=True, destructive=True))
    async def export_layers(
        layers: Annotated[LayerList, Field(description="Of any kind, one file each")],
        subfolder: Annotated[str, Field(max_length=300, description=(
            "Below the export root: a or a/b, letters, digits, _ . - only"))] = "export",
        vector_format: Literal["GPKG", "GeoJSON", "ESRI Shapefile", "FlatGeobuf", "CSV"] = "GPKG",
        raster_format: Literal["COG", "GTiff"] = "COG",
        point_cloud_format: Literal["LAZ", "COPC", "LAS", "GPKG", "CSV"] = "LAZ",
        crs: Annotated[Optional[str], Field(max_length=64, description="Omit: each layer's")] = None,
    ) -> Dict[str, Any]:
        """Write layers, as filtered now, to files on the QGIS machine below its export root; a file of the same
        name is overwritten.

        Returns done, outputs ({layer name: file path}), failed and skipped.
        """
        return await call("POST", "/export", _body(
            layers=layers, subfolder=subfolder, vector_format=vector_format, raster_format=raster_format,
            point_cloud_format=point_cloud_format, crs=crs))

    # -- resources (read-only mirrors of two GET tools) --------------------------
    # Synchronous on purpose: async resource functions return '<coroutine ...>' in mcp 1.9.0 / 1.10.0.

    def read(path: str) -> str:
        try:
            return json.dumps(client.request("GET", path), indent=2, ensure_ascii=False)
        except FilterMateAPIError as exc:
            raise ResourceError(str(exc)) from None

    @mcp.resource("filtermate://layers", name="layers", mime_type="application/json",
                  description="Layers of the open QGIS project known to FilterMate (same as list_layers).")
    def layers_resource() -> str:
        return read("/layers")

    @mcp.resource("filtermate://state", name="state", mime_type="application/json",
                  description="Layers FilterMate filters now (same as filter_state).")
    def state_resource() -> str:
        return read("/filters/state")

    return mcp


def main(argv: Optional[Sequence[str]] = None, environ: Optional[Dict[str, str]] = None) -> int:
    """Run the stdio server; returns the process exit code."""
    try:
        settings = parse_settings(argv, os.environ if environ is None else environ)
    except ConfigError as exc:
        print(f"filtermate-mcp: {exc}", file=sys.stderr)
        return 2
    client = FilterMateClient(settings.base_url, settings.api_key, settings.timeout,
                              use_proxy=not settings.is_loopback)
    build_server(client).run(transport="stdio")
    return 0


__all__ = ["build_server", "main", "RasterSelection", "PointCloudCriteria"]

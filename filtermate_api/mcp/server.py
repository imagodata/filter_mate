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
from typing import Annotated, Any, Dict, List, Literal, Optional, Sequence
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
# add_layer may follow redirects (4 x 20 s), download for 180 s, then open the copy: wait for all of it.
ADD_LAYER_TIMEOUT = 330.0

INSTRUCTIONS = """\
Drives FilterMate, the QGIS filtering plugin, through its local REST API. QGIS must be running with the API started.

Typical workflow: list_layers (names, ids, kinds), describe_layer and field_values (what a filter can test), \
preview_filter (try an expression), then cross_filter / select_features / zoom_to / geometry_filter / point_cloud_filter / \
apply_filter to filter, filter_state to see what is filtered now, export_layers to write the filtered layers, \
clear_filters to put layers back on their original source.
Objects on a raster: map_context lists those the user drew in the dock (cross_filter uses them with \
raster_selection dock_objects); segment_objects draws with SAM the objects that points or footprints point at, as a \
new layer.
undo_filter / redo_filter are not idempotent: after one (also after an error or a timeout), read filter_state \
before calling it again.

Filters change the layers of the open QGIS project in place (visible to the user at once). They can be reverted with \
clear_filters; undo_filter / redo_filter only cover the vector history of the dock. Nothing here edits the data \
itself. If a tool reports that QGIS is busy, nothing was changed: wait a few seconds and retry."""

Predicate = Literal["Intersect", "Contain", "Disjoint", "Equal", "Touch", "Overlap", "Are within", "Cross"]
Operator = Literal["AND", "OR", "AND NOT"]
LayerList = Annotated[List[str], Field(min_length=1, max_length=1000)]

_PREDICATES_DOC = (
    "Spatial predicates, each tested as `target <predicate> source`: Intersect (share any space), "
    "Contain (the target contains the source), Disjoint (share nothing; rasters and point clouds then keep the "
    "outside of the source), Equal (same geometry), Touch (borders meet, interiors do not), "
    "Overlap (partial overlap of same-dimension geometries), Are within (the target lies inside the source), "
    "Cross (lines crossing). A target is kept when ANY listed predicate holds."
)
_OPERATOR_DOC = (
    "How to combine with the previous filter of each target: AND (keep what both filters keep), OR (keep what "
    "either keeps), AND NOT (remove the new selection from the previous filter). Omit to replace the previous filter."
)


def _write(title: str, idempotent: bool, destructive: bool = False) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=False, destructiveHint=destructive,
                           idempotentHint=idempotent, openWorldHint=False)


class RasterSelection(BaseModel):
    """Pixels kept on a raster source (same rules as the EXPLORING raster panel of the dock)."""

    model_config = ConfigDict(extra="forbid")

    band: int = Field(default=1, ge=1, description="1-based band number")
    mode: Literal["range", "classes", "expression"] = Field(
        default="range",
        description="range: pixels between minimum and maximum; classes: pixels whose value is in `classes`; "
                    "expression: raster calculator expression")
    minimum: Optional[float] = Field(default=None, description="range: lower bound, inclusive (in band units)")
    maximum: Optional[float] = Field(default=None, description="range: upper bound, inclusive (in band units)")
    classes: List[int] = Field(default_factory=list, description="classes: pixel values kept (paletted rasters)")
    expression: str = Field(default="", max_length=2000,
                            description='expression: raster calculator expression, e.g. "mnt@1" > 1200')
    derivative: Literal["value", "slope_degrees", "slope_percent", "aspect", "hillshade", "roughness"] = Field(
        default="value",
        description="range only: quantity the bounds apply to. With anything but `value` the band is read as a "
                    "DTM (elevation model) and the bounds are in degrees / percent / etc.")
    segments: List[str] = Field(
        default_factory=list, max_length=10000,
        description="objects drawn on the raster (the SAM targets of the dock): WKT polygons in the CRS of the "
                    "raster. When given, they are the selection: leave the range, classes and expression unset.")
    dock_objects: bool = Field(
        default=False,
        description="true: the objects the user drew on this raster in the FilterMate dock are the selection "
                    "(map_context lists them as drawn_objects). Leave everything else unset, segments included.")

    @model_validator(mode="after")
    def _check_segments(self) -> "RasterSelection":
        if self.segments or self.dock_objects:
            from ..routers.filters import check_segments_selection
            check_segments_selection(self.segments, self.minimum, self.maximum, self.classes, self.expression,
                                     self.derivative, self.dock_objects)
        return self


class PointCloudCriteria(BaseModel):
    """Points kept on a point cloud (ASPRS classes, ranges, return number, expression)."""

    model_config = ConfigDict(extra="forbid")

    classes: List[int] = Field(
        default_factory=list,
        description="ASPRS classification codes kept (0-255), e.g. 2 ground, 3-5 vegetation, 6 building, 9 water")
    z_min: Optional[float] = Field(default=None, description="Minimum Z (elevation), in the layer CRS units")
    z_max: Optional[float] = Field(default=None, description="Maximum Z (elevation), in the layer CRS units")
    intensity_min: Optional[float] = Field(default=None, description="Minimum intensity")
    intensity_max: Optional[float] = Field(default=None, description="Maximum intensity")
    return_number: Optional[int] = Field(default=None, ge=1, le=15, description="Return number kept (1 = first return)")
    expression: str = Field(default="", max_length=2000,
                            description="Point cloud expression (e.g. Classification = 6 AND Z > 1000), ANDed with "
                                        "the other criteria")


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

        Returns layer_id, name, layer_kind, provider_type, crs_authid, geometry_type, feature_count, subset (its
        current filter), visible and group (its place in the layer tree), extent ([xmin, ymin, xmax, ymax] in its
        own CRS, empty for a web service), style (how it is drawn: renderer, and when they apply field, classes (how
        many), labels (the field labelled), opacity, min_scale and max_scale (it only shows between these scale
        denominators)), and by kind: joins [{layer, field, target_field, prefix}] and relations [{name, role (parent
        or child), layer, fields}] for a vector layer, with sql_dialect (postgresql, sqlite, ogr_sql or qgis_expression: the language of
        its filter) and fields [{name, type, alias, filterable}] for a vector layer (filterable is
        false for virtual and joined fields, which a filter expression cannot test); bands [{band, name, classes}]
        and pixel_size for a raster, classes [{value, label}] only on a paletted band; attributes [name] for a point
        cloud.
        """
        return await call("GET", "/layers/details?" + urlencode({"layer": layer}))

    @mcp.tool(annotations=ToolAnnotations(title="Values of a field", readOnlyHint=True, openWorldHint=False))
    async def field_values(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        field: Annotated[str, Field(min_length=1, max_length=1000, description="Field name, from describe_layer")],
        search: Annotated[str, Field(max_length=200, description=(
            "Text fields: only values containing this text, ignoring case"))] = "",
        limit: Annotated[int, Field(ge=1, le=200, description="Maximum number of values returned")] = 50,
    ) -> Dict[str, Any]:
        """Distinct values a field really takes, among the features the layer shows now (its filter applies).

        Use it to write a filter with the exact spelling of a value. Returns values, truncated (more values exist),
        and minimum and maximum for a numeric or date field. NULL is left out. Refused on web services (WFS...),
        which would have to be read whole.
        """
        return await call("GET", "/layers/field-values?" + urlencode(
            {"layer": layer, "field": field, "search": search, "limit": limit}))

    @mcp.tool(annotations=ToolAnnotations(title="Statistics of a layer", readOnlyHint=True, openWorldHint=False))
    async def layer_statistics(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        field: Annotated[str, Field(max_length=1000, description=(
            "Field to sum up, from describe_layer. Leave empty to count features, or to use measure"))] = "",
        group_by: Annotated[str, Field(max_length=1000, description=(
            "Field whose values make the groups: one row of statistics per value"))] = "",
        measure: Annotated[Literal["", "length", "area"], Field(description=(
            "Measure the geometries instead of a field: length of lines (perimeter of polygons) in metres, or "
            "area of polygons in square metres"))] = "",
        selected_only: Annotated[bool, Field(description="Only the selected features")] = False,
        limit: Annotated[int, Field(ge=1, le=100, description="At most this many groups, the largest first")] = 20,
    ) -> Dict[str, Any]:
        """Count, sum, mean, minimum, maximum of a field or of the geometries of a vector layer, in all or by group.

        Computed on the features the layer shows now (its filter applies), or on its selection: use it to answer
        "how many", "what total", "which is the largest", and to check what a filter kept. With neither field nor
        measure it counts features, by group when group_by is given. Returns feature_count (features read),
        statistics {count, nulls, minimum, maximum, and sum, mean, stdev for numbers or distinct for text}, unit (m or
        m2 for a measure), and with group_by: groups [{value, feature_count, and the same statistics}], groups_total
        and truncated. Refused on web services and above 500000 features: filter or select first.
        """
        return await call("POST", "/layers/statistics", _body(
            layer=layer, field=field, group_by=group_by, measure=measure, selected_only=selected_only, limit=limit))

    @mcp.tool(annotations=ToolAnnotations(title="Sample of features", readOnlyHint=True, openWorldHint=False))
    async def sample_features(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        limit: Annotated[int, Field(ge=1, le=20, description="At most this many features")] = 5,
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
        {field: value}, geometry {type, centroid, bbox}}], truncated (more features match) and fields_truncated. Long
        text is cut at 200 characters. Refused on web services.
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
        expression: Annotated[str, Field(min_length=1, max_length=500_000, description=(
            "Subset string, as for apply_filter"))],
    ) -> Dict[str, Any]:
        """Try a filter expression on a private copy of the layer: nothing changes in the project.

        It is what apply_filter would do, and it replaces the layer's current filter in the same way. Returns valid,
        feature_count (features kept, -1 when unknown) and error (the reason when valid is false). Refused on web
        services and memory layers, and for anything but a plain condition (subqueries, most functions).
        """
        return await call("POST", "/filters/preview", _body(layer_name=layer_name, expression=expression))

    @mcp.tool(annotations=ToolAnnotations(title="Map context", readOnlyHint=True, openWorldHint=False))
    async def map_context() -> Dict[str, Any]:
        """What the user is looking at in QGIS.

        Returns project_crs, canvas_crs, extent_wkt (the visible extent, usable as is with geometry_filter and
        canvas_crs), extent (the same as [xmin, ymin, xmax, ymax]), scale, active_layer_id, active_layer_name,
        selections [{layer_id, name, selected_count}] (the layers with selected features, which cross_filter uses as
        its source) and drawn_objects [{layer_id, name, crs_authid, count, area_m2, extent_wkt}] (the rasters on which
        the user drew objects in the FilterMate dock: cross_filter uses them with that raster as source_layer and
        raster_selection {"dock_objects": true}). available is false when QGIS has no map canvas.
        """
        return await call("GET", "/map/context")

    # -- filters ---------------------------------------------------------------

    @mcp.tool(annotations=_write("Apply a filter expression", idempotent=True))
    async def apply_filter(
        layer_name: Annotated[str, Field(min_length=1, max_length=1000, description=(
            "Name of a VECTOR layer (not its id; the first vector layer of that name is used)"))],
        expression: Annotated[str, Field(min_length=1, max_length=500_000, description=(
            "Subset string: the provider's SQL WHERE clause, without the WHERE keyword. For a PostgreSQL, "
            "GeoPackage, Shapefile or Spatialite layer: \"population\" > 10000 AND \"dep\" = '31'. "
            "Quote field names with double quotes and text values with single quotes. Plain conditions only: "
            "comparisons, IN, LIKE, BETWEEN, IS NULL and simple text or number functions; a subquery or another "
            "function is refused."))],
        source: Annotated[str, Field(max_length=200, description=(
            "Free-text tag shown in the FilterMate log to tell where the filter came from"))] = "mcp",
        operator: Annotated[Optional[Operator], Field(description=(
            "Combine with the layer's current filter instead of replacing it: AND narrows it (the new condition "
            "only, never a copy of the current filter), OR widens it, AND NOT removes the new condition from it"))]
            = None,
    ) -> Dict[str, Any]:
        """Set the filter (subset string) of one vector layer; without operator it replaces the previous filter.

        Returns success, expression (as applied), replaced_filter (the filter the layer had and lost, when no
        operator was given) and active_filters ({layer name: subset string} after the call). For spatial filtering
        between layers use cross_filter or geometry_filter. Revert with clear_filters.

        Caution: some providers (GeoPackage, Shapefile through OGR) accept an invalid SQL expression without any
        error and the layer then shows no feature. Check list_layers afterwards (feature_count -1, or 0 when you
        expected matches) and use clear_filters to recover.
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
        source_layer: Annotated[str, Field(min_length=1, max_length=1000, description=(
            "Source layer, vector, raster or point cloud: layer id or name"))],
        target_layers: Annotated[LayerList, Field(description=(
            "Layers to filter, of any kind: layer ids or names. The source itself is not filtered "
            "(except with filter_source)."))],
        predicates: Annotated[List[Predicate], Field(max_length=8, description=_PREDICATES_DOC)] = ["Intersect"],  # noqa: B006
        buffer: Annotated[float, Field(ge=-1e7, le=1e7, description=(
            "Buffer applied to the source geometry before testing, in the source CRS units "
            "(metres for a projected CRS; for a geographic CRS the API treats them as metres). "
            "Negative shrinks. 0 = none."))] = 0.0,
        coverage_min: Annotated[float, Field(ge=0, le=100, description=(
            "Polygon targets only: minimum share (%) of the target that must lie inside the source"))] = 0.0,
        operator: Annotated[Optional[Operator], Field(description=_OPERATOR_DOC)] = None,
        selected_only: Annotated[bool, Field(description=(
            "Vector source: use the features currently selected in QGIS; with none selected, the features its "
            "filter keeps. A web service source such as WFS must be selected or already filtered, it is never read "
            "whole. select_features changes the selection; false uses all the features the source shows."))] = True,
        raster_selection: Annotated[Optional[RasterSelection], Field(description=(
            "REQUIRED when the source is a raster: which pixels are the source area"))] = None,
        point_cloud_criteria: Annotated[Optional[PointCloudCriteria], Field(description=(
            "Point cloud source: which points make the source area (omit = the points it shows now)"))] = None,
        filter_source: Annotated[bool, Field(description=(
            "Raster source: also mask the source raster outside the selection"))] = False,
    ) -> Dict[str, Any]:
        """Filter layers by their spatial relation to a selection made on a source layer, any kind to any kind.

        Source kinds: a vector layer (its selected features), a raster (pixels kept by raster_selection, e.g.
        elevation between 1200 and 1300) or a point cloud (points kept by point_cloud_criteria, e.g. class 6).
        Targets keep what satisfies the predicates: vector features, raster pixels or LiDAR points inside the source
        area (outside with Disjoint). Filters apply in place to the project layers and replace the previous filter
        of each target unless operator is given. Not recorded in the undo history: revert with clear_filters.

        Returns filtered (names of the layers filtered), failed ({layer: reason}), skipped ({layer: reason}) and
        warnings ({layer: reason}: filtered, but a web service read up to its budget, so features may be missing).
        A layer that is not found is reported in failed; a source that is not found is an error.
        """
        return await call("POST", "/filters/cross", _body(
            source_layer=source_layer, target_layers=target_layers, predicates=predicates, buffer=buffer,
            coverage_min=coverage_min, operator=operator, selected_only=selected_only,
            raster_selection=raster_selection, point_cloud_criteria=point_cloud_criteria,
            filter_source=filter_source))

    @mcp.tool(annotations=_write("Filter by a WKT geometry", idempotent=True))
    async def geometry_filter(
        wkt: Annotated[str, Field(min_length=1, max_length=1_000_000, description=(
            "Geometry in WKT, e.g. POLYGON((650000 6860000, 651000 6860000, 651000 6861000, 650000 6861000, "
            "650000 6860000)); an extent as a rectangle polygon"))],
        crs: Annotated[str, Field(min_length=1, max_length=64, description=(
            "CRS of the geometry, authority code such as EPSG:2154 or EPSG:4326 (the coordinate order is "
            "x/longitude first)"))],
        target_layers: Annotated[LayerList, Field(description="Layers to filter, of any kind: layer ids or names")],
        predicates: Annotated[List[Predicate], Field(max_length=8, description=_PREDICATES_DOC)] = ["Intersect"],  # noqa: B006
        buffer: Annotated[float, Field(ge=-1e7, le=1e7, description=(
            "Buffer applied to the geometry, in the units of the CRS of the first target"))] = 0.0,
        coverage_min: Annotated[float, Field(ge=0, le=100, description=(
            "Polygon targets only: minimum share (%) of the target inside the geometry"))] = 0.0,
        operator: Annotated[Optional[Operator], Field(description=_OPERATOR_DOC)] = None,
    ) -> Dict[str, Any]:
        """Filter layers of any kind by a WKT geometry (a drawn area, an extent, a commune outline).

        Same effect and answer as cross_filter, with a geometry given inline instead of a source layer: the way to
        filter by an area when no source feature can be selected in QGIS. Replaces the previous filter of each
        target unless operator is given. Not in the undo history: revert with clear_filters.
        Returns filtered, failed, skipped and warnings.
        """
        return await call("POST", "/filters/geometry", _body(
            wkt=wkt, crs=crs, target_layers=target_layers, predicates=predicates, buffer=buffer,
            coverage_min=coverage_min, operator=operator))

    @mcp.tool(annotations=_write("Filter point clouds", idempotent=True))
    async def point_cloud_filter(
        layers: Annotated[LayerList, Field(description=(
            "Point cloud layers (LiDAR tiles...): layer ids or names"))],
        criteria: Annotated[PointCloudCriteria, Field(description=(
            "Points to keep; at least one criterion is required"))],
        operator: Annotated[Optional[Operator], Field(description=(
            _OPERATOR_DOC + " AND NOT needs an existing filter on each layer."))] = None,
    ) -> Dict[str, Any]:
        """Keep only some points (by class, elevation, intensity, return number or expression) on point cloud layers.

        The same criteria apply to every listed layer, e.g. all the tiles of a LiDAR HD dataset. Sets the layer
        filter (e.g. 'Classification = 6 AND Z >= 1000'). It is one step of the dock's history of those point clouds
        (the dock's Undo on the layer reverts it) but undo_filter does not undo it: revert with clear_filters.
        Returns done (layers filtered), failed and skipped.
        """
        return await call("POST", "/filters/point-cloud", _body(layers=layers, criteria=criteria, operator=operator))

    @mcp.tool(annotations=_write("Clear filters", idempotent=True))
    async def clear_filters(
        layers: Annotated[LayerList, Field(description="Layers of any kind to unfilter: layer ids or names")],
    ) -> Dict[str, Any]:
        """Put layers back on their original source with no filter (the dock's Unfilter).

        Removes subset strings and restores the original source of raster and point cloud layers that were clipped.
        This is the way to revert cross_filter, geometry_filter, point_cloud_filter and apply_favorite.
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
        layer: Annotated[Optional[str], Field(max_length=1000, description=(
            "Layer id or name to zoom to (its whole extent, or its selection with selected_only)"))] = None,
        extent_wkt: Annotated[Optional[str], Field(max_length=100_000, description=(
            "Instead of a layer: an extent or geometry as WKT"))] = None,
        crs: Annotated[Optional[str], Field(max_length=64, description="CRS of the WKT, e.g. EPSG:2154")] = None,
        selected_only: Annotated[bool, Field(description="With layer: zoom to its selected features")] = False,
    ) -> Dict[str, Any]:
        """Zoom the QGIS map to a layer, to its selected features, to a WKT extent, or to everything (no argument).

        Changes only the view, never the data or the filters. Returns extent_wkt and scale after the zoom. Fails
        without a map window (headless QGIS).
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
        mode: Annotated[Literal["single", "categorized", "graduated", "pseudocolor", "gray"], Field(description=(
            "Vector: single (one symbol, color), categorized (one color per value of field), graduated (classes of "
            "a numeric field). Raster: pseudocolor (a color ramp over band values), gray (a gray stretch)"))],
        field: Annotated[str, Field(max_length=1000, description="Field for categorized and graduated")] = "",
        color: Annotated[str, Field(max_length=50, description="single: #rrggbb or a color name")] = "",
        ramp: Annotated[str, Field(max_length=100, description=(
            "Color ramp of QGIS: Viridis, Spectral, Blues, Reds, Greens, RdYlGn, Magma, Turbo..."))] = "",
        classes: Annotated[int, Field(ge=2, le=12, description="graduated: number of classes")] = 5,
        method: Annotated[Literal["quantile", "equal_interval", "jenks", "pretty", "stddev"], Field(
            description="graduated: how the class breaks are found")] = "quantile",
        invert: Annotated[bool, Field(description="Reverse the color ramp")] = False,
        opacity: Annotated[Optional[float], Field(ge=0, le=1, description="Opacity of the layer, 0 to 1")] = None,
        band: Annotated[int, Field(ge=1, le=1000, description="Raster: the band drawn")] = 1,
        minimum: Annotated[Optional[float], Field(description="Raster: lowest value of the ramp (statistics by default)")] = None,
        maximum: Annotated[Optional[float], Field(description="Raster: highest value of the ramp")] = None,
    ) -> Dict[str, Any]:
        """Change how a layer is drawn on the map: one symbol, categories, graduated classes, a raster ramp.

        Returns mode, field, classes (how many were made), ramp, method, and for a raster band, minimum and
        maximum. The values of the classes are not returned: describe_layer and layer_statistics read the data. A
        field with more than 100 values cannot be categorized. In the chat of FilterMate, undoing the turn brings
        the previous style back.
        """
        return await call("POST", "/layers/style", _body(
            layer=layer, mode=mode, field=field, color=color, ramp=ramp, classes=classes, method=method,
            invert=invert, opacity=opacity, band=band, minimum=minimum, maximum=maximum))

    @mcp.tool(annotations=_write("Label a layer", idempotent=True))
    async def set_labels(
        layer: Annotated[str, Field(min_length=1, max_length=1000, description="Vector layer id or name")],
        field: Annotated[str, Field(max_length=1000, description="Field whose values are written on the map")] = "",
        enabled: Annotated[bool, Field(description="false turns the labels off")] = True,
        size: Annotated[Optional[float], Field(ge=4, le=72, description="Text size in points")] = None,
        color: Annotated[str, Field(max_length=50, description="Text color, #rrggbb or a name")] = "",
        buffer: Annotated[bool, Field(description="A light halo around the text, to read it on any background")] = True,
    ) -> Dict[str, Any]:
        """Write the values of a field next to the features of a vector layer on the map, or turn the labels off.

        Returns labels (on or off) and field. In the chat of FilterMate, undoing the turn brings the previous labels
        back.
        """
        return await call("POST", "/layers/labels", _body(layer=layer, field=field, enabled=enabled, size=size,
                                                          color=color, buffer=buffer))

    @mcp.tool(annotations=_write("Edit attributes of features", idempotent=True))
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
            '[{"wkt": "POINT(1.44 43.6)", "attributes": {"nom": "Puits"}}]: geometries of the type of the layer'))],
        crs: Annotated[str, Field(max_length=200, description="CRS of the WKT, such as EPSG:4326; the layer's by default")] = "",
    ) -> Dict[str, Any]:
        """Add features to a vector layer from WKT geometries and attributes, in its edit buffer: nothing is saved.

        Returns added, editing and unsaved. In the chat of FilterMate, undoing the turn takes them back while they
        are not saved.
        """
        return await call("POST", "/layers/features/add", _body(layer=layer, features=features, crs=crs))

    @mcp.tool(annotations=_write("Show or hide layers", idempotent=True))
    async def set_layers_visibility(
        layers: Annotated[LayerList, Field(description="Layer ids or names")],
        visible: Annotated[bool, Field(description="true shows the layers, false hides them")],
    ) -> Dict[str, Any]:
        """Check or uncheck layers in the layer tree (shown or hidden on the map). Returns done and failed."""
        return await call("POST", "/layers/visibility", _body(layers=layers, visible=visible))

    @mcp.tool(annotations=_write("Draw objects with SAM", idempotent=False))
    async def segment_objects(
        raster: Annotated[str, Field(min_length=1, max_length=1000, description=(
            "Raster to draw on, as it shows on the map (an orthophoto): layer id or name"))],
        guide_layer: Annotated[str, Field(min_length=1, max_length=1000, description=(
            "Vector layer whose features point at the objects: points (each a click on an object) or polygons "
            "(each a footprint: its bounding box and a point inside it). Layer id or name."))],
        selected_only: Annotated[bool, Field(description=(
            "Use the selected features of the guide; with none selected, the features it shows"))] = True,
        limit: Annotated[int, Field(ge=1, le=200, description=(
            "The most guide features taken in one call; a guide that gives more is refused, select fewer"))] = 50,
        name: Annotated[str, Field(max_length=200, description=(
            "Name of the layer added (default: the name of the guide followed by (SAM))"))] = "",
    ) -> Dict[str, Any]:
        """Draw with SAM, on a raster, the object each feature of a guide layer points at; adds them as a layer.

        The new polygon layer is a temporary GeoPackage, in the CRS of the raster, one object per guide feature, with the
        attributes of the feature, sam_score (the confidence of SAM, 0 to 1) and, for a polygon guide, sam_iou (overlap
        of the footprint with the drawn object, 0 to 1: a low value flags a footprint to look at, such as a building
        that changed, it does not prove a change). Then select_features on that layer (e.g. "sam_iou" < 0.5) or
        cross_filter with it as the source. No other layer is changed.

        Returns layer (layer_id, name, feature_count...), guide_features, drawn, without_object (features with no
        object: off the raster, nothing found by SAM, or never tried when stopped_early), sam_score {median, minimum},
        sam_iou {median, minimum, below_half}, seconds and stopped_early (true when the 20 s allowed ran out before
        every window was drawn: call again with fewer features). QGIS is held while SAM draws, about 2 s for each
        window of 1024 pixels; other changes are refused meanwhile. A guide whose features cannot be counted (a web
        service) needs a selection. SAM (the model and its runtime) is installed by the user from the FilterMate
        dock; without it the call fails and says so. Good on buildings and other well delimited objects; parcels and
        trees are not reliable.
        """
        return await call("POST", "/objects/segment", _body(
            raster=raster, guide_layer=guide_layer, selected_only=selected_only, limit=limit, name=name))

    @mcp.tool(annotations=ToolAnnotations(title="Add a layer", readOnlyHint=False, destructiveHint=False,
                                          idempotentHint=False, openWorldHint=True))
    async def add_layer(
        source: Annotated[str, Field(min_length=1, max_length=2000, description=(
            "A local data file on the QGIS machine (gpkg, shp, geojson, json, kml, gml, fgb, csv, tif; a GeoPackage "
            "table with |layername=name), or a public https URL of such a file (a resource url from "
            "search_open_data). Nothing else: no http, no provider URI, no database connection."))],
        name: Annotated[str, Field(max_length=200, description="Name of the layer in the project (default: the file name)")] = "",
        kind: Annotated[Literal["vector", "raster"], Field(description="vector (default) or raster")] = "vector",
    ) -> Dict[str, Any]:
        """Add a layer to the open project from a local file or a public https URL.

        Typical use after search_open_data: pick a geojson or gpkg resource url and add it, then filter it like any
        other layer. A remote file is read where it is when its server gives parts of it (GeoPackage, GeoTIFF, zip);
        any other is first copied to the QGIS profile (512 MB and 3 minutes at most). When it cannot be added the
        error says why: try another resource of the dataset, or a service layer. Returns the layer summary (layer_id,
        name, layer_kind, provider_type, crs_authid, feature_count). The chat of FilterMate asks the user first.
        """
        return await call("POST", "/layers/add", _body(source=source, name=name, kind=kind), timeout=ADD_LAYER_TIMEOUT)

    @mcp.tool(annotations=ToolAnnotations(title="Add a layer of a WFS service", readOnlyHint=False, destructiveHint=False,
                                          idempotentHint=False, openWorldHint=True))
    async def add_service_layer(
        platform: Annotated[str, Field(min_length=1, max_length=200, description=(
            "A WFS platform the user allowed, e.g. ign_wfs (IGN Géoplateforme)"))],
        typename: Annotated[str, Field(min_length=1, max_length=300, description=(
            "Layer id given by search_open_data on that platform, e.g. ADMINEXPRESS-COG-CARTO.LATEST:commune"))],
        name: Annotated[str, Field(max_length=200, description="Name of the layer in the project (default: its title)")] = "",
    ) -> Dict[str, Any]:
        """Add a layer of a WFS service, read from the service as the map moves and filtered on the server.

        Only a layer the service lists can be added. Returns the layer summary. The chat of FilterMate asks the
        user first.
        """
        return await call("POST", "/layers/add-service", _body(platform=platform, typename=typename, name=name))

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
        """Remove layers from the project. Their files are not deleted. The chat of FilterMate asks the user first,
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
        resource url (geojson or gpkg first), or add_service_layer with the id on a WFS platform. The query is sent to
        the platform.
        """
        return await call("POST", "/open-data/search", _body(query=query, platform=platform, limit=limit))

    # -- export ----------------------------------------------------------------

    @mcp.tool(annotations=_write("Export filtered layers", idempotent=True, destructive=True))
    async def export_layers(
        layers: Annotated[LayerList, Field(description=(
            "Layers of any kind to export as they are filtered now, one file per layer: ids or names"))],
        subfolder: Annotated[str, Field(max_length=300, description=(
            "Sub-folder of the export root configured on the QGIS machine (a or a/b, letters, digits, _ . - only, "
            "no .. and never an absolute path)"))] = "export",
        vector_format: Annotated[Literal["GPKG", "GeoJSON", "ESRI Shapefile", "FlatGeobuf", "CSV"], Field(
            description="Format of vector layers")] = "GPKG",
        raster_format: Annotated[Literal["COG", "GTiff"], Field(description="Format of raster layers")] = "COG",
        point_cloud_format: Annotated[Literal["LAZ", "COPC", "LAS", "GPKG", "CSV"], Field(
            description="Format of point cloud layers")] = "LAZ",
        crs: Annotated[Optional[str], Field(max_length=64, description=(
            "Output CRS such as EPSG:2154 (omit = each layer's CRS)"))] = None,
    ) -> Dict[str, Any]:
        """Write layers, as filtered now, to files on the QGIS machine, below the server's export root.

        Writes files: a file with the same name already in the sub-folder is overwritten. The files stay on the
        machine running QGIS; the answer gives their paths there. Returns done (layers written),
        outputs ({layer name: file path}), failed and skipped.
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

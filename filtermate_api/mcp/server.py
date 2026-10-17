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

from pydantic import BaseModel, ConfigDict, Field

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server
    from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from .rest_client import FilterMateAPIError, FilterMateClient, quote_segment
from .settings import ConfigError, parse_settings

SERVER_NAME = "filtermate"

INSTRUCTIONS = """\
Drives FilterMate, the QGIS filtering plugin, through its local REST API. QGIS must be running with the API started.

Typical workflow: list_layers (names, ids, kinds), then cross_filter / geometry_filter / point_cloud_filter / \
apply_filter to filter, filter_state to see what is filtered now, export_layers to write the filtered layers, \
clear_filters to put layers back on their original source.

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
_LAYERS_DOC = "Layers are designated by QGIS layer id or by name (the first layer of that name); list_layers gives both."


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

    async def call(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        try:
            return await asyncio.to_thread(client.request, method, path, body)
        except FilterMateAPIError as exc:
            # ToolError is the one exception whose message the SDK (2.x) shows the model.
            raise ToolError(str(exc)) from None

    # -- read-only tools -------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(title="List layers", readOnlyHint=True, openWorldHint=False))
    async def list_layers() -> Dict[str, Any]:
        """List the layers of the open QGIS project that FilterMate knows, as {"layers": [...]}.

        Each layer has layer_id, name, provider_type, feature_count (-1 when unknown), geometry_type, crs_authid,
        layer_kind (vector, raster or point_cloud), has_active_filter and active_filter_expression.
        Call this first: the other tools take layer names or ids from it.
        """
        return {"layers": await call("GET", "/layers")}

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

        Each row has layer_id, name, layer_kind, subset (the filter string, empty for a clipped raster) and
        derived (true when the layer reads a clipped copy of its source). Use it to check what a filter did, and to
        find out what a previous call did when a request timed out.
        """
        return {"layers": await call("GET", "/filters/state")}

    @mcp.tool(annotations=ToolAnnotations(title="List favorites", readOnlyHint=True, openWorldHint=False))
    async def list_favorites() -> Dict[str, Any]:
        """List the favorites (saved filters) of the FilterMate project, as {"favorites": [...]}.

        Each has favorite_id (what apply_favorite takes), name, description, layer_name and expression.
        """
        return {"favorites": await call("GET", "/favorites")}

    # -- filters ---------------------------------------------------------------

    @mcp.tool(annotations=_write("Apply a filter expression", idempotent=True))
    async def apply_filter(
        layer_name: Annotated[str, Field(min_length=1, max_length=1000, description=(
            "Name of a VECTOR layer (not its id; the first vector layer of that name is used)"))],
        expression: Annotated[str, Field(min_length=1, max_length=500_000, description=(
            "Subset string: the provider's SQL WHERE clause, without the WHERE keyword. For a PostgreSQL, "
            "GeoPackage, Shapefile or Spatialite layer: \"population\" > 10000 AND \"dep\" = '31'. "
            "Quote field names with double quotes and text values with single quotes."))],
        source: Annotated[str, Field(max_length=200, description=(
            "Free-text tag shown in the FilterMate log to tell where the filter came from"))] = "mcp",
    ) -> Dict[str, Any]:
        """Set the filter (subset string) of one vector layer; it replaces the layer's previous filter.

        Returns success and active_filters ({layer name: subset string} after the call). For spatial filtering
        between layers use cross_filter or geometry_filter. Revert with clear_filters.
        """
        return await call("POST", "/filters/apply",
                          _body(layer_name=layer_name, expression=expression, source=source))

    @mcp.tool(annotations=_write("Undo the last vector filter", idempotent=False))
    async def undo_filter() -> Dict[str, Any]:
        """Undo the last step of the dock's vector filter history (the dock's Undo button).

        Returns the step rolled back to (layer_name, expression, is_clear) and active_filters. Only covers steps
        recorded by the dock itself: nothing done through these tools (apply_filter, cross_filter,
        geometry_filter, point_cloud_filter, clear_filters, apply_favorite) is recorded there, so use
        clear_filters to revert those. Fails with 'Nothing to undo' when the history is empty.
        """
        return await call("POST", "/filters/undo")

    @mcp.tool(annotations=_write("Redo the last undone vector filter", idempotent=False))
    async def redo_filter() -> Dict[str, Any]:
        """Redo the step undone last in the dock's vector filter history (the dock's Redo button).

        Same answer as undo_filter. Fails with 'Nothing to redo' when there is nothing to redo.
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
            "Vector source: use the features currently selected in QGIS (all features when none is selected). "
            "You cannot change the QGIS selection with these tools: ask the user to select the features, "
            "or use geometry_filter with a WKT geometry."))] = True,
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

        Returns filtered (names of the layers filtered), failed ({layer: reason}) and skipped ({layer: reason}).
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
        Returns filtered, failed and skipped.
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
        filter (e.g. 'Classification = 6 AND Z >= 1000'). Not in the undo history: revert with clear_filters.
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

    @mcp.resource("filtermate://layers", name="layers", mime_type="application/json",
                  description="Layers of the open QGIS project known to FilterMate (same as list_layers).")
    async def layers_resource() -> str:
        return json.dumps(await call("GET", "/layers"), indent=2)

    @mcp.resource("filtermate://state", name="state", mime_type="application/json",
                  description="Layers FilterMate filters now (same as filter_state).")
    async def state_resource() -> str:
        return json.dumps(await call("GET", "/filters/state"), indent=2)

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

"""Driving QGIS beyond filters (agent mode): view, selection, layer tree, layers, objects drawn by SAM, open data."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..accessor import (
    ContourResult, ElevationResult, LocalCopyResult, OsmResult, PopulationResult,
    AddedServiceLayer, Bookmarks, FieldAdded, FilterRejected, JoinAdded, LayerRename, LayerSummary, LayerTreeChange,
    MapThemes, OpenDataResult, OperationResult, PlacesResult, ProjectCrs, SegmentResult, SelectionResult,
    SimilarResult, ViewState,
)
from ..export_root import ExportRootError, resolve_exported_file
from ..source_gate import open_data_refusal
from .filters import LayerName

try:
    from ...core.agent.open_data import KIND_ELEVATION, KIND_OVERPASS, KIND_POPULATION, KIND_XYZ
except ImportError:  # repo root on sys.path
    from core.agent.open_data import KIND_ELEVATION, KIND_OVERPASS, KIND_POPULATION, KIND_XYZ

router = APIRouter(tags=["project"])
_MAX_NAME = 1000


def _accessor(request: Request):
    return request.app.state.accessor


class ZoomBody(BaseModel):
    layer: Optional[str] = Field(default=None, max_length=_MAX_NAME, description="Layer id or name")
    extent_wkt: Optional[str] = Field(default=None, max_length=100_000, description="Extent or geometry as WKT")
    crs: Optional[str] = Field(default=None, max_length=64, description="CRS of the WKT, e.g. EPSG:2154")
    selected_only: bool = Field(default=False, description="Zoom to the selected features of the layer")


@router.post("/map/zoom", response_model=ViewState)
def zoom(payload: ZoomBody, request: Request) -> ViewState:
    """Zoom the map to a layer, its selection, a WKT extent, or everything."""
    try:
        return _accessor(request).zoom_to(layer=payload.layer, extent_wkt=payload.extent_wkt, crs=payload.crs,
                                          selected_only=payload.selected_only)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class CrsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crs: str = Field(..., min_length=1, max_length=_MAX_NAME, description="EPSG:2154, 2154, or a layer of the project")


class CrsSuggestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layers: Optional[List[str]] = Field(None, max_length=100)
    purpose: Literal["general", "areas", "distances", "shapes", "world", "web"] = "general"


@router.post("/map/crs/suggest")
def suggest_crs(payload: CrsSuggestBody, request: Request) -> Dict[str, Any]:
    """Projections for the data of layers (default: those shown) and what the map is for, best first."""
    try:
        return _accessor(request).suggest_crs(layers=payload.layers, purpose=payload.purpose)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class CartogramBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME)
    field: str = Field(..., min_length=1, max_length=200)
    kind: Literal["contiguous", "noncontiguous", "dorling", "demers"] = "contiguous"
    iterations: int = Field(8, ge=1, le=30)
    name: str = Field("", max_length=200)


@router.post("/layers/cartogram")
def make_cartogram(payload: CartogramBody, request: Request) -> Dict[str, Any]:
    """A new layer whose areas show a field of a layer, as it is filtered now."""
    try:
        return _accessor(request).make_cartogram(payload.layer, payload.field, kind=payload.kind,
                                                 iterations=payload.iterations, name=payload.name)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@router.post("/map/crs", response_model=ProjectCrs)
def set_project_crs(payload: CrsBody, request: Request) -> ProjectCrs:
    """Set the CRS of the project, which the map follows."""
    try:
        return _accessor(request).set_project_crs(payload.crs)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class SelectBody(BaseModel):
    layer: str = Field(..., min_length=1, max_length=_MAX_NAME, description="Vector layer id or name")
    expression: str = Field(default="", max_length=100_000, description="QGIS expression (not SQL)")
    clear: bool = Field(default=False, description="Empty the selection instead")
    add: bool = Field(default=False, description="Add to the current selection instead of replacing it")


@router.post("/layers/select", response_model=SelectionResult)
def select(payload: SelectBody, request: Request) -> SelectionResult:
    """Select the features matching a QGIS expression."""
    try:
        return _accessor(request).select_features(payload.layer, expression=payload.expression, clear=payload.clear,
                                                  add=payload.add)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class VisibilityBody(BaseModel):
    layers: List[LayerName] = Field(..., min_length=1, max_length=1000)
    visible: bool


@router.post("/layers/visibility", response_model=OperationResult)
def visibility(payload: VisibilityBody, request: Request) -> OperationResult:
    """Check or uncheck layers in the layer tree."""
    return _accessor(request).set_layers_visibility(payload.layers, payload.visible)


# --- The options of FilterMate's panels -------------------------------------------------------------------------


class LayerOptionsItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: LayerName
    exploring: Dict[str, Any] = Field(default_factory=dict, description="EXPLORING options of the layer")
    filtering: Dict[str, Any] = Field(default_factory=dict, description="FILTERING options of the layer")


class LayerOptionsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layers: List[LayerOptionsItem] = Field(..., min_length=1, max_length=50)
    reason: str = Field(default="", max_length=500)


class ExploringBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field(default="", max_length=_MAX_NAME, description="Layer to show, id or name; the one shown by default")
    tools: Dict[str, bool] = Field(default_factory=dict, max_length=10,
                                   description="Buttons of the rail turned on (true) or off (false), by name")
    press: List[str] = Field(default_factory=list, max_length=4, description="Buttons of the rail pressed once")
    show: bool = Field(default=False, description="Open EXPLORING in front of the user")
    raster: Optional[Dict[str, Any]] = Field(default=None, description="band, quantity, minimum, maximum of a raster")
    point_cloud: Optional[Dict[str, Any]] = Field(default=None, description="classes, or ranges, of a point cloud")


class ExportOptionsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changes: Dict[str, Any] = Field(..., min_length=1)
    reason: str = Field(default="", max_length=500)


def _panels(call):
    try:
        return call()
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@router.get("/panels/layer")
def panel_layer(request: Request, layer: str = Query(..., min_length=1, max_length=_MAX_NAME)) -> Dict[str, Any]:
    """What a layer shows in EXPLORING and how it filters, in FilterMate's panel."""
    return _panels(lambda: _accessor(request).layer_options(layer))


@router.post("/panels/layer")
def set_panel_layers(payload: LayerOptionsBody, request: Request) -> Dict[str, Any]:
    """Set the EXPLORING and FILTERING options of layers in FilterMate's panel, all or none."""
    return _panels(lambda: _accessor(request).set_layer_options([item.model_dump() for item in payload.layers]))


@router.post("/panels/exploring")
def drive_exploring(payload: ExploringBody, request: Request) -> Dict[str, Any]:
    """Drive FilterMate's EXPLORING panel as the user does: its layer, the buttons of its rail."""
    return _panels(lambda: _accessor(request).set_exploring(
        layer=payload.layer, tools=payload.tools, press=payload.press, show=payload.show, raster=payload.raster,
        point_cloud=payload.point_cloud))


@router.get("/panels/export")
def panel_export(request: Request) -> Dict[str, Any]:
    """How the project exports from FilterMate's EXPORTING panel."""
    return _panels(lambda: _accessor(request).export_options())


@router.post("/panels/export")
def set_panel_export(payload: ExportOptionsBody, request: Request) -> Dict[str, Any]:
    """Set export options of the project in FilterMate's EXPORTING panel, all or none."""
    return _panels(lambda: _accessor(request).set_export_options(payload.changes))


class AddLayerBody(BaseModel):
    source: str = Field(..., min_length=1, max_length=2000, description="Local data file or public https URL")
    name: str = Field(default="", max_length=200)
    kind: Literal["vector", "raster", "point_cloud"] = "vector"


@router.post("/layers/add", response_model=LayerSummary)
def add_layer(payload: AddLayerBody, request: Request) -> LayerSummary:
    """Add a layer to the project; a relative source is a file ``POST /export`` wrote below the export root."""
    try:
        source, title = resolve_exported_file(request.app.state.config.export_root, payload.source)
    except ExportRootError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Export root unavailable") from None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    try:
        return _accessor(request).add_layer(source, name=payload.name or title, kind=payload.kind)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class AddServiceLayerBody(BaseModel):
    platform: str = Field(..., min_length=1, max_length=200, description="WFS, WMS or WMTS platform, e.g. ign_wfs")
    typename: str = Field(..., min_length=1, max_length=300, description="Layer id given by the search")
    name: str = Field(default="", max_length=200)


@router.post("/layers/add-service", response_model=AddedServiceLayer)
def add_service_layer(payload: AddServiceLayerBody, request: Request) -> AddedServiceLayer:
    """Add a layer of a WFS platform the user allowed."""
    try:
        return _accessor(request).add_service_layer(payload.platform, payload.typename, name=payload.name)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class AddBasemapBody(BaseModel):
    platform: str = Field(..., min_length=1, max_length=2000, description="Basemap, e.g. carto_light")
    name: str = Field(default="", max_length=200)


@router.post("/layers/add-basemap", response_model=LayerSummary)
def add_basemap(payload: AddBasemapBody, request: Request) -> LayerSummary:
    """Add a web basemap the user allowed, under the layers of the project."""
    refused = open_data_refusal(KIND_XYZ, "basemap")
    if refused is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=refused)
    try:
        return _accessor(request).add_basemap(payload.platform, name=payload.name)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class AddElevationBody(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    platform: str = Field(default="copernicus_dem", min_length=1, max_length=200, description="Elevation source")
    extent_wkt: str = Field(default="", max_length=100_000, description="Area as WKT (default: the visible map)")
    crs: str = Field(default="", max_length=64, description="CRS of extent_wkt (default: the CRS of the map)")
    resolution: Optional[float] = Field(default=None, ge=10, le=5000, description="Pixel size in metres")
    target_crs: str = Field(default="", max_length=64, description="CRS in metres the raster is written in")
    name: str = Field(default="", max_length=200)


@router.post("/layers/add-elevation", response_model=ElevationResult)
def add_elevation(payload: AddElevationBody, request: Request) -> ElevationResult:
    """Add the elevation of an area, read from an elevation model the user allowed, as a raster layer."""
    refused = open_data_refusal(KIND_ELEVATION, "elevation")
    if refused is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=refused)
    try:
        return _accessor(request).add_elevation(
            payload.platform, extent_wkt=payload.extent_wkt, crs=payload.crs, resolution=payload.resolution,
            target_crs=payload.target_crs, name=payload.name)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class AddPopulationBody(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    platform: str = Field(default="meta_population", min_length=1, max_length=200, description="Population source")
    extent_wkt: str = Field(default="", max_length=100_000, description="Area as WKT (default: the visible map)")
    crs: str = Field(default="", max_length=64, description="CRS of extent_wkt (default: the CRS of the map)")
    resolution: Optional[float] = Field(default=None, ge=30, le=10_000, description="Pixel size in metres")
    name: str = Field(default="", max_length=200)


@router.post("/layers/add-population", response_model=PopulationResult)
def add_population(payload: AddPopulationBody, request: Request) -> PopulationResult:
    """Add the people of an area, read from a population grid the user allowed, as a raster of people per pixel."""
    refused = open_data_refusal(KIND_POPULATION, "population")
    if refused is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=refused)
    try:
        return _accessor(request).add_population(
            payload.platform, extent_wkt=payload.extent_wkt, crs=payload.crs, resolution=payload.resolution,
            name=payload.name)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class OsmTagBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1, max_length=60, pattern=r"^[A-Za-z][A-Za-z0-9_:.-]*$")
    value: str = Field(default="", max_length=80, description="Empty: any value")


class AddOsmBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tags: List[OsmTagBody] = Field(..., min_length=1, max_length=10, description="Features with one of these tags")
    platform: str = Field(default="overpass_fr", min_length=1, max_length=200, description="Overpass server")
    extent_wkt: str = Field(default="", max_length=100_000, description="Area as WKT (default: the visible map)")
    crs: str = Field(default="", max_length=64, description="CRS of extent_wkt (default: the CRS of the map)")
    geometry: Literal["as_mapped", "points", "lines", "polygons"] = "as_mapped"
    name: str = Field(default="", max_length=180)


@router.post("/layers/add-osm", response_model=OsmResult)
def add_osm_features(payload: AddOsmBody, request: Request) -> OsmResult:
    """Add the OpenStreetMap features that carry given tags in an area, read from an Overpass server."""
    refused = open_data_refusal(KIND_OVERPASS, "Overpass")
    if refused is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=refused)
    try:
        return _accessor(request).add_osm_features(
            payload.platform, [tag.model_dump() for tag in payload.tags], extent_wkt=payload.extent_wkt,
            crs=payload.crs, geometry=payload.geometry, name=payload.name)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class ContoursBody(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    layer: LayerName
    interval: float = Field(..., gt=0, le=100_000, description="Height between two contours")
    index_interval: Optional[float] = Field(default=None, gt=0, le=1_000_000,
                                            description="Height between two index contours, a multiple of interval")
    band: int = Field(default=1, ge=1, le=1000)
    name: str = Field(default="", max_length=200)
    min_length: Optional[float] = Field(default=None, ge=0, le=1e9,
                                        description="Closed contours shorter than this are left out; 0 keeps all")


@router.post("/layers/contours", response_model=ContourResult)
def contour_lines(payload: ContoursBody, request: Request) -> ContourResult:
    """Draw the contour lines of a raster of the project as a new line layer."""
    try:
        return _accessor(request).contour_lines(payload.layer, payload.interval,
                                                index_interval=payload.index_interval, band=payload.band,
                                                name=payload.name, min_length=payload.min_length)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class DuplicateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: LayerName
    name: str = Field(default="", max_length=200)


class LocalCopyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: LayerName
    action: Literal["copy", "back", "again"] = "copy"
    extent_wkt: str = Field(default="", max_length=100_000, description="Area as WKT; empty: the visible map")
    crs: str = Field(default="", max_length=64, description="CRS of extent_wkt; empty: the CRS of the map")


@router.post("/layers/local-copy", response_model=LocalCopyResult)
def local_copy(payload: LocalCopyBody, request: Request) -> LocalCopyResult:
    """Copy a web service layer over the visible map (or an area) to a file next to the project and read it; read
    its service again (action back); copy the area of its copy anew (action again)."""
    try:
        return _accessor(request).local_copy(payload.layer, action=payload.action, extent_wkt=payload.extent_wkt,
                                             crs=payload.crs)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@router.post("/layers/duplicate", response_model=LayerSummary)
def duplicate_layer(payload: DuplicateBody, request: Request) -> LayerSummary:
    """Add a second layer on the same data as a layer, just above it."""
    try:
        return _accessor(request).duplicate_layer(payload.layer, name=payload.name)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class FieldBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: LayerName
    name: str = Field(..., min_length=1, max_length=63)
    type: Literal["integer", "integer64", "decimal", "text", "date", "datetime", "boolean"] = "text"
    length: int = Field(default=0, ge=0, le=10_000, description="Length of a text field; 0 lets the source choose")
    formula: str = Field(default="", max_length=10_000, description="QGIS expression filling the field")


@router.post("/layers/fields", response_model=FieldAdded)
def add_field(payload: FieldBody, request: Request) -> FieldAdded:
    """Add a field to a vector layer, in its edit buffer: nothing is saved."""
    try:
        return _accessor(request).add_field(payload.layer, payload.name, field_type=payload.type,
                                            length=payload.length, formula=payload.formula)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class JoinBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: LayerName
    join_layer: LayerName
    target_field: str = Field(..., min_length=1, max_length=200)
    join_field: str = Field(..., min_length=1, max_length=200)
    fields: Optional[List[str]] = Field(default=None, max_length=200)
    prefix: Optional[str] = Field(default=None, max_length=50)


@router.post("/layers/join", response_model=JoinAdded)
def join_layers(payload: JoinBody, request: Request) -> JoinAdded:
    """Show the fields of another layer beside each feature, matched by a field; nothing is written."""
    try:
        return _accessor(request).join_layers(payload.layer, payload.join_layer, payload.target_field,
                                              payload.join_field, fields=payload.fields, prefix=payload.prefix)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class FormValueBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(..., min_length=1, max_length=1000)
    label: str = Field(default="", max_length=200)


class FormFieldBody(BaseModel):
    """How one field shows in the form; what is left out stays as it is ("" removes an alias, expression, default)."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(..., min_length=1, max_length=200)
    alias: Optional[str] = Field(default=None, max_length=200)
    widget: Optional[Literal["value_map", "value_relation", "range", "date", "checkbox", "text", "hidden",
                             "relation_reference", "default"]] = None
    values: Optional[List[Union[str, FormValueBody]]] = Field(default=None, max_length=500)
    layer: str = Field(default="", max_length=_MAX_NAME)
    key: str = Field(default="", max_length=200)
    value: str = Field(default="", max_length=200)
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    format: str = Field(default="", max_length=200)
    multiline: Optional[bool] = None
    not_null: Optional[bool] = None
    unique: Optional[bool] = None
    expression: Optional[str] = Field(default=None, max_length=2000)
    constraint_text: str = Field(default="", max_length=200)
    enforce: Optional[bool] = None
    default: Optional[str] = Field(default=None, max_length=2000)
    default_on_update: Optional[bool] = None
    editable: Optional[bool] = None


class FormBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: LayerName
    fields: List[FormFieldBody] = Field(..., min_length=1, max_length=50)


@router.post("/layers/form")
def set_form(payload: FormBody, request: Request) -> Dict[str, Any]:
    """Set how fields show in the attribute form of a layer, all or none; nothing is written to the data."""
    return _accessor(request).set_form(payload.layer, [entry.model_dump(exclude_defaults=True)
                                                       for entry in payload.fields])


class RelationsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["list", "add", "remove"]
    name: str = Field(default="", max_length=200, description="add: its name; remove: its id or name")
    parent_layer: str = Field(default="", max_length=_MAX_NAME)
    parent_field: str = Field(default="", max_length=200)
    child_layer: str = Field(default="", max_length=_MAX_NAME)
    child_field: str = Field(default="", max_length=200)
    strength: Literal["association", "composition"] = "association"


@router.post("/project/relations")
def relations(payload: RelationsBody, request: Request) -> Dict[str, Any]:
    """List, add or remove a relation of the project: a child layer linked to a parent layer by a field."""
    return _accessor(request).relations(payload.action, **payload.model_dump(exclude={"action"}))


class GroupBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layers: List[LayerName] = Field(..., min_length=1, max_length=1000)
    group: str = Field(default="", max_length=_MAX_NAME, description="Group path such as Base/Roads; empty: the top")
    at_top: bool = Field(default=True, description="First of the group, or last")
    above: str = Field(default="", max_length=_MAX_NAME, description="A layer: put them just above it, in its group")


@router.post("/layers/group", response_model=LayerTreeChange)
def group_layers(payload: GroupBody, request: Request) -> LayerTreeChange:
    """Put layers in a group of the layer tree, made where missing, or just above a layer."""
    try:
        return _accessor(request).group_layers(payload.layers, group=payload.group, at_top=payload.at_top,
                                               above=payload.above)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class RenameBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: LayerName
    name: str = Field(..., min_length=1, max_length=200)
    group: bool = Field(default=False, description="layer is the path of a group (Base/Roads), renamed instead")


@router.post("/layers/rename", response_model=LayerRename)
def rename_layer(payload: RenameBody, request: Request) -> LayerRename:
    """Give a layer (or a group) of the project another name; its data does not change."""
    try:
        return _accessor(request).rename_layer(payload.layer, payload.name, group=payload.group)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class BookmarkBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["list", "add", "zoom", "remove"]
    name: str = Field(default="", max_length=200)
    extent_wkt: str = Field(default="", max_length=100_000)
    crs: str = Field(default="", max_length=200)


@router.post("/map/bookmarks", response_model=Bookmarks)
def bookmark(payload: BookmarkBody, request: Request) -> Bookmarks:
    """List, add, zoom to or remove a spatial bookmark of the project."""
    try:
        return _accessor(request).bookmark(payload.action, payload.name, extent_wkt=payload.extent_wkt,
                                           crs=payload.crs)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class ThemeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["list", "save", "apply", "remove"]
    name: str = Field(default="", max_length=200)


@router.post("/map/themes", response_model=MapThemes)
def map_theme(payload: ThemeBody, request: Request) -> MapThemes:
    """List, save, apply or remove a map theme of the project."""
    try:
        return _accessor(request).map_theme(payload.action, payload.name)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class RemoveBody(BaseModel):
    layers: List[LayerName] = Field(..., min_length=1, max_length=1000)


@router.post("/layers/remove", response_model=OperationResult)
def remove_layers(payload: RemoveBody, request: Request) -> OperationResult:
    """Remove layers from the project; their files stay."""
    return _accessor(request).remove_layers(payload.layers)


class SegmentObjectsBody(BaseModel):
    raster: str = Field(..., min_length=1, max_length=_MAX_NAME, description="Raster layer id or name (e.g. an orthophoto)")
    guide_layer: str = Field(..., min_length=1, max_length=_MAX_NAME,
                             description="Vector layer id or name: points (clicks) or polygons (footprints)")
    selected_only: bool = Field(default=True, description="Use the selected guide features (all it shows when none is selected)")
    limit: int = Field(default=50, ge=1, le=200, description="The most guide features taken in one call")
    name: str = Field(default="", max_length=200, description="Name of the layer added (default: the guide name and (SAM))")


@router.post("/objects/segment", response_model=SegmentResult)
def segment_objects(payload: SegmentObjectsBody, request: Request) -> SegmentResult:
    """SAM draws on a raster one object per guide feature, added to the project as a polygon layer.

    QGIS is held while it draws; past 20 s the run stops and answers with what it drew.
    """
    try:
        return _accessor(request).segment_objects(payload.raster, payload.guide_layer, selected_only=payload.selected_only,
                                                  limit=payload.limit, name=payload.name)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class SimilarObjectsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raster: str = Field(..., min_length=1, max_length=_MAX_NAME, description="Raster layer id or name (e.g. an orthophoto)")
    example_layer: str = Field(default="", max_length=_MAX_NAME,
                               description="Vector layer id or name whose one selected feature is the example")
    use_dock_object: bool = Field(default=False,
                                  description="The examples are the objects drawn on this raster in the FilterMate dock")
    extent_wkt: str = Field(default="", max_length=100_000, description="Area searched as WKT (default: the visible map)")
    extent_crs: str = Field(default="", max_length=64, description="CRS of extent_wkt, e.g. EPSG:2154 (default: the raster's)")
    same_shape: bool = Field(default=True, description="Keep only objects shaped like the example (compactness)")
    name: str = Field(default="", max_length=200, description="Name of the layer added")

    @model_validator(mode="after")
    def _one_example(self) -> "SimilarObjectsBody":
        if bool(self.example_layer) == bool(self.use_dock_object):
            raise ValueError("give an example: example_layer or use_dock_object, one of them")
        return self


@router.post("/objects/similar", response_model=SimilarResult)
def similar_objects(payload: SimilarObjectsBody, request: Request) -> SimilarResult:
    """SAM finds on a raster the objects that look like an example, added to the project as a polygon layer.

    QGIS is held while it searches; past 20 s the search stops between two windows and answers with what it found.
    """
    try:
        return _accessor(request).similar_objects(
            payload.raster, example_layer=payload.example_layer, use_dock_object=payload.use_dock_object,
            extent_wkt=payload.extent_wkt, extent_crs=payload.extent_crs, same_shape=payload.same_shape,
            name=payload.name)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class OpenDataBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    platform: str = Field(default="datagouv", min_length=1, max_length=200)
    limit: int = Field(default=10, ge=1, le=20)


@router.post("/open-data/search", response_model=OpenDataResult)
def search_open_data(payload: OpenDataBody, request: Request) -> OpenDataResult:
    """Datasets of an allowed open data platform. A POST: a web page must not be able to trigger it."""
    try:
        return _accessor(request).search_open_data(payload.query, platform=payload.platform, limit=payload.limit)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class PlaceBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="Name of a place, an address")
    platform: str = Field(default="ign_geocoder", max_length=200)
    limit: int = Field(default=5, ge=1, le=10)


@router.post("/places/find", response_model=PlacesResult)
def find_place(payload: PlaceBody, request: Request) -> PlacesResult:
    """Places of an allowed geocoder. A POST: a web page must not be able to trigger it."""
    try:
        return _accessor(request).find_place(payload.query, platform=payload.platform, limit=payload.limit)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class ImageryBody(BaseModel):
    bbox: Optional[List[float]] = Field(default=None, min_length=4, max_length=4, description="[west, south, east, north] in degrees")
    start: str = Field(default="", max_length=10, description="First day, YYYY-MM-DD")
    end: str = Field(default="", max_length=10, description="Last day, YYYY-MM-DD")
    max_cloud: float = Field(default=20.0, ge=0, le=100)
    collections: Optional[List[str]] = Field(default=None, max_length=5)
    limit: int = Field(default=5, ge=1, le=20)
    platform: str = Field(default="earth_search", max_length=200)


@router.post("/open-data/imagery", response_model=OpenDataResult)
def search_imagery(payload: ImageryBody, request: Request) -> OpenDataResult:
    """Satellite scenes of an allowed STAC catalog."""
    try:
        return _accessor(request).search_imagery(bbox=payload.bbox, start=payload.start, end=payload.end,
                                                 max_cloud=payload.max_cloud, collections=payload.collections,
                                                 limit=payload.limit, platform=payload.platform)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

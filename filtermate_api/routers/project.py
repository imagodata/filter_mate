"""Driving QGIS beyond filters (agent mode): view, selection, layer tree, layers, objects drawn by SAM, open data."""

from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..accessor import (
    Bookmarks, FieldAdded, FilterRejected, JoinAdded, LayerRename, LayerSummary, LayerTreeChange, MapThemes, OpenDataResult, OperationResult, ProjectCrs, SegmentResult, SelectionResult,
    SimilarResult, ViewState,
)
from .filters import LayerName

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


class AddLayerBody(BaseModel):
    source: str = Field(..., min_length=1, max_length=2000, description="Local data file or public https URL")
    name: str = Field(default="", max_length=200)
    kind: Literal["vector", "raster", "point_cloud"] = "vector"


@router.post("/layers/add", response_model=LayerSummary)
def add_layer(payload: AddLayerBody, request: Request) -> LayerSummary:
    """Add a layer to the project."""
    try:
        return _accessor(request).add_layer(payload.source, name=payload.name, kind=payload.kind)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class AddServiceLayerBody(BaseModel):
    platform: str = Field(..., min_length=1, max_length=200, description="WFS platform, e.g. ign_wfs")
    typename: str = Field(..., min_length=1, max_length=300, description="Layer id given by the search")
    name: str = Field(default="", max_length=200)


@router.post("/layers/add-service", response_model=LayerSummary)
def add_service_layer(payload: AddServiceLayerBody, request: Request) -> LayerSummary:
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
    try:
        return _accessor(request).add_basemap(payload.platform, name=payload.name)
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

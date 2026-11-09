"""Driving QGIS beyond filters (agent mode): view, selection, layer tree, layers, open data."""

from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..accessor import FilterRejected, LayerSummary, OpenDataResult, OperationResult, SelectionResult, ViewState
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
    kind: Literal["vector", "raster"] = "vector"


@router.post("/layers/add", response_model=LayerSummary)
def add_layer(payload: AddLayerBody, request: Request) -> LayerSummary:
    """Add a layer to the project."""
    try:
        return _accessor(request).add_layer(payload.source, name=payload.name, kind=payload.kind)
    except FilterRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


class RemoveBody(BaseModel):
    layers: List[LayerName] = Field(..., min_length=1, max_length=1000)


@router.post("/layers/remove", response_model=OperationResult)
def remove_layers(payload: RemoveBody, request: Request) -> OperationResult:
    """Remove layers from the project; their files stay."""
    return _accessor(request).remove_layers(payload.layers)


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

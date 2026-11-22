"""/layouts — print layouts of the map, added to the project, and their export under the export root."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from ..accessor import FilterRejected, LayoutExport, LayoutResult
from ..export_root import ExportRootError, prepare_export_root, resolve_export_folder

router = APIRouter(prefix="/layouts", tags=["layouts"])


class LayoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)
    title: str = Field("", max_length=200)
    page: Literal["A4", "A3", "A5", "Letter"] = "A4"
    orientation: Literal["landscape", "portrait"] = "landscape"
    layers: Optional[List[str]] = Field(None, max_length=100)
    extent: Optional[List[float]] = Field(None, min_length=4, max_length=4)
    extent_layer: str = Field("", max_length=1000)
    legend: bool = True
    scale_bar: bool = True
    north_arrow: bool = True


@router.post("", response_model=LayoutResult)
def create_layout(payload: LayoutRequest, request: Request) -> LayoutResult:
    """A print layout of the map, with its title, legend, scale bar and north arrow, added to the project."""
    options = payload.model_dump(exclude={"name"})
    return request.app.state.accessor.create_layout(payload.name, **options)


class LayoutExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)
    format: Literal["pdf", "png", "jpg", "svg", "tif"] = "pdf"
    dpi: int = Field(150, ge=72, le=600)
    subfolder: str = Field("layouts", min_length=1, max_length=200, description="Sub-folder of the export root")
    georeference: bool = True
    atlas: bool = False
    single_file: bool = True


@router.post("/export", response_model=LayoutExport)
def export_layout(payload: LayoutExportRequest, request: Request) -> LayoutExport:
    """Write a layout of the project as PDF or PNG into a sub-folder of the export root."""
    try:
        folder = resolve_export_folder(prepare_export_root(request.app.state.config.export_root), payload.subfolder)
    except ExportRootError:
        raise HTTPException(status_code=503, detail="The export folder is not available") from None
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid subfolder") from None
    written = request.app.state.accessor.export_layout(payload.name, str(folder), file_format=payload.format,
                                                       dpi=payload.dpi, georeference=payload.georeference,
                                                       atlas=payload.atlas, single_file=payload.single_file)
    return LayoutExport(name=written.name, format=written.format, dpi=written.dpi,
                        path=os.path.relpath(written.path, str(folder)), bytes=written.bytes, files=written.files,
                        pages=written.pages, atlas=written.atlas)


@router.get("/details")
def describe_layout(request: Request, name: str = Query("", max_length=100)) -> Dict[str, Any]:
    """A layout: its pages, its items and its atlas; without a name, the layouts and the templates."""
    try:
        return request.app.state.accessor.describe_layout(name)
    except FilterRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


class AtlasRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout: str = Field(..., min_length=1, max_length=100)
    coverage_layer: str = Field("", max_length=1000)
    enabled: bool = True
    filter: str = Field("", max_length=2000)
    page_name: str = Field("", max_length=2000)
    sort_by: str = Field("", max_length=2000)
    descending: bool = False
    hide_coverage: bool = False
    map_mode: Literal["auto", "fixed", "predefined"] = "auto"
    margin: float = Field(10, ge=0, le=500)
    file_name: str = Field("", max_length=2000)
    maps: Optional[List[str]] = Field(None, max_length=20)


@router.post("/atlas")
def set_atlas(payload: AtlasRequest, request: Request) -> Dict[str, Any]:
    """Turn the atlas of a layout on (one page per feature of a layer, as filtered) or off."""
    options = payload.model_dump(exclude={"layout", "filter"})
    options["filter_expression"] = payload.filter
    try:
        return request.app.state.accessor.set_atlas(payload.layout, **options)
    except FilterRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

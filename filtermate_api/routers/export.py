"""POST /export — write layers of any kind as they are filtered (FilterMate 5).

The files are written on the QGIS machine, below ``APIConfig.export_root``:
clients give a sub-folder name, never a path, so the API cannot be used to
write anywhere else on the host.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..accessor import FilterMateAccessor, OperationResult

router = APIRouter(prefix="/export", tags=["export"])

_SUBFOLDER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}(/[A-Za-z0-9][A-Za-z0-9_.-]{0,63}){0,3}$")


class ExportRequestBody(BaseModel):
    layers: List[str] = Field(..., min_length=1, description="Layers of any kind, exported as filtered now")
    subfolder: str = Field(default="export", description="Sub-folder of the server export root (a/b allowed, no ..)")
    vector_format: Literal["GPKG", "GeoJSON", "ESRI Shapefile", "FlatGeobuf", "CSV"] = "GPKG"
    raster_format: Literal["COG", "GTiff"] = "COG"
    point_cloud_format: Literal["LAZ", "COPC", "LAS", "GPKG", "CSV"] = "LAZ"
    crs: Optional[str] = Field(default=None, max_length=64, description="Output CRS, e.g. EPSG:2154 (null = layer CRS)")


def resolve_export_folder(root: Path, subfolder: str) -> Path:
    """Folder below ``root`` for ``subfolder``; ValueError when it would escape it."""
    if not _SUBFOLDER.match(subfolder or "") or ".." in subfolder.split("/"):
        raise ValueError("invalid subfolder")
    root = Path(root).resolve()
    folder = (root / subfolder).resolve()
    if folder != root and root not in folder.parents:
        raise ValueError("invalid subfolder")
    return folder


@router.post("", response_model=OperationResult)
async def export_layers(payload: ExportRequestBody, request: Request) -> OperationResult:
    """Write each layer (vector, raster, point cloud) as filtered now, one file per layer."""
    try:
        folder = resolve_export_folder(request.app.state.config.export_root, payload.subfolder)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid subfolder")
    accessor: FilterMateAccessor = request.app.state.accessor
    result = accessor.export_layers(
        layers=payload.layers, folder=str(folder), vector_format=payload.vector_format,
        raster_format=payload.raster_format, point_cloud_format=payload.point_cloud_format, crs=payload.crs)
    if result.error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Export failed")
    return result

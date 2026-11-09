"""POST /export — write layers of any kind as they are filtered (FilterMate 5).

The files are written on the QGIS machine, below ``APIConfig.export_root``:
clients give a sub-folder name, never a path, so the API cannot be used to
write anywhere else on the host. The root must be a real folder of the user
running QGIS (created private, mode 0700).
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..accessor import FilterMateAccessor, OperationResult
from ..export_root import ExportRootError, prepare_export_root, resolve_export_folder
from .filters import LayerName

router = APIRouter(prefix="/export", tags=["export"])
logger = logging.getLogger("filtermate_api")


class ExportRequestBody(BaseModel):
    layers: List[LayerName] = Field(..., min_length=1, max_length=1000,
                                    description="Layers of any kind, exported as filtered now")
    subfolder: str = Field(default="export", description="Sub-folder of the server export root (a/b allowed, no ..)")
    vector_format: Literal["GPKG", "GeoJSON", "ESRI Shapefile", "FlatGeobuf", "CSV"] = "GPKG"
    raster_format: Literal["COG", "GTiff"] = "COG"
    point_cloud_format: Literal["LAZ", "COPC", "LAS", "GPKG", "CSV"] = "LAZ"
    crs: Optional[str] = Field(default=None, max_length=64, description="Output CRS, e.g. EPSG:2154 (null = layer CRS)")


@router.post("", response_model=OperationResult)
def export_layers(payload: ExportRequestBody, request: Request) -> OperationResult:
    """Write each layer (vector, raster, point cloud) as filtered now, one file per layer."""
    try:
        root = prepare_export_root(request.app.state.config.export_root)
    except ExportRootError as exc:
        # Server side configuration: the client can do nothing about it, the operator reads why here.
        logger.error("POST /export refused: %s (%s)", exc, request.app.state.config.export_root)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Export root unavailable")
    try:
        folder = resolve_export_folder(root, payload.subfolder)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid subfolder")
    accessor: FilterMateAccessor = request.app.state.accessor
    result = accessor.export_layers(
        layers=payload.layers, folder=str(folder), vector_format=payload.vector_format,
        raster_format=payload.raster_format, point_cloud_format=payload.point_cloud_format, crs=payload.crs)
    if result.error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Export failed: {result.error}")
    return result

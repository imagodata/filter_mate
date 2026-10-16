"""POST /export — write layers of any kind as they are filtered (FilterMate 5).

The files are written on the QGIS machine, below ``APIConfig.export_root``:
clients give a sub-folder name, never a path, so the API cannot be used to
write anywhere else on the host. The root must be a real folder of the user
running QGIS (created private, mode 0700).
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..accessor import FilterMateAccessor, OperationResult
from .filters import LayerName

router = APIRouter(prefix="/export", tags=["export"])

_SUBFOLDER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}(/[A-Za-z0-9][A-Za-z0-9_.-]{0,63}){0,3}$")


class ExportRequestBody(BaseModel):
    layers: List[LayerName] = Field(..., min_length=1, max_length=1000,
                                    description="Layers of any kind, exported as filtered now")
    subfolder: str = Field(default="export", description="Sub-folder of the server export root (a/b allowed, no ..)")
    vector_format: Literal["GPKG", "GeoJSON", "ESRI Shapefile", "FlatGeobuf", "CSV"] = "GPKG"
    raster_format: Literal["COG", "GTiff"] = "COG"
    point_cloud_format: Literal["LAZ", "COPC", "LAS", "GPKG", "CSV"] = "LAZ"
    crs: Optional[str] = Field(default=None, max_length=64, description="Output CRS, e.g. EPSG:2154 (null = layer CRS)")


class ExportRootError(RuntimeError):
    """The export root cannot be written safely (link, not a folder, another owner)."""


def prepare_export_root(root: Path) -> Path:
    """Create ``root`` when missing (mode 0700) and check it is safe to write below.

    Refused: a symbolic link (whoever made it chose where the files go), a
    file, or on POSIX a folder owned by another user (who could swap its
    content between the check and the write).
    """
    root = Path(root).expanduser()
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = os.lstat(root)
    except OSError as exc:
        raise ExportRootError(f"export root unavailable: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ExportRootError("export root is not a real folder")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ExportRootError("export root belongs to another user")
    return root


def resolve_export_folder(root: Path, subfolder: str) -> Path:
    """Folder below ``root`` for ``subfolder``; ValueError when it would escape it."""
    # fullmatch: ``$`` alone would let a trailing newline through ("a\n").
    if not _SUBFOLDER.fullmatch(subfolder or "") or ".." in subfolder.split("/"):
        raise ValueError("invalid subfolder")
    root = Path(root).resolve()
    folder = (root / subfolder).resolve()
    if folder != root and root not in folder.parents:
        raise ValueError("invalid subfolder")
    return folder


@router.post("", response_model=OperationResult)
def export_layers(payload: ExportRequestBody, request: Request) -> OperationResult:
    """Write each layer (vector, raster, point cloud) as filtered now, one file per layer."""
    try:
        root = prepare_export_root(request.app.state.config.export_root)
    except ExportRootError:
        # Server side configuration: the client can do nothing about it (details in no log of theirs).
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

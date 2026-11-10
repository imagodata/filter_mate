"""GET /map/context — what the user is looking at in QGIS."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from ..accessor import IdentifyResult, MapContext

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/context", response_model=MapContext)
def map_context(request: Request) -> MapContext:
    """CRS, extent as WKT, scale, active layer and the layers with selected features."""
    return request.app.state.accessor.map_context()


class IdentifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(..., ge=-1e9, le=1e9)
    y: float = Field(..., ge=-1e9, le=1e9)
    crs: str = Field("", max_length=200, description="CRS of the point (EPSG:2154); the CRS of the map by default")
    layers: Optional[List[str]] = Field(None, max_length=20, description="Only these layers; the visible ones by default")
    tolerance: Optional[float] = Field(None, ge=0, le=1e9, description="Search distance, in the units of the CRS")
    limit: int = Field(5, ge=1, le=20, description="At most this many features per layer")


@router.post("/identify", response_model=IdentifyResult)
def identify_at(payload: IdentifyRequest, request: Request) -> IdentifyResult:
    """The features and the raster values at a point of the map."""
    return request.app.state.accessor.identify_at(
        payload.x, payload.y, crs=payload.crs, layers=payload.layers, tolerance=payload.tolerance, limit=payload.limit)

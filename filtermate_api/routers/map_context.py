"""GET /map/context — what the user is looking at in QGIS."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..accessor import MapContext

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/context", response_model=MapContext)
def map_context(request: Request) -> MapContext:
    """CRS, extent as WKT, scale, active layer and the layers with selected features."""
    return request.app.state.accessor.map_context()

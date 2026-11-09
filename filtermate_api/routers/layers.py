"""GET /layers — list layers visible to the FilterMate session.

Issue #30. Read-only endpoint, returns the projection from
:class:`filtermate_api.accessor.LayerSummary`.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query, Request, status

from ..accessor import FieldValues, FilterMateAccessor, LayerDetails, LayerSummary

router = APIRouter(prefix="/layers", tags=["layers"])

_MAX_NAME = 1000


def _accessor(request: Request) -> FilterMateAccessor:
    """Pull the configured accessor off the FastAPI app state.

    Routes use ``Request`` rather than a ``Depends(...)`` factory because
    the accessor is bound at app construction time — there's no request-
    scoped state to plumb through.
    """
    accessor: FilterMateAccessor = request.app.state.accessor
    return accessor


@router.get("", response_model=List[LayerSummary])
def list_layers(request: Request) -> List[LayerSummary]:
    """Return every layer the FilterMate session knows about."""
    return _accessor(request).list_layers()


@router.get("/details", response_model=LayerDetails)
def layer_details(request: Request, layer: str = Query(..., min_length=1, max_length=_MAX_NAME)) -> LayerDetails:
    """Fields, bands or point attributes of a layer (id or name)."""
    details = _accessor(request).describe_layer(layer)
    if details is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layer not found")
    return details


@router.get("/field-values", response_model=FieldValues)
def field_values(
    request: Request,
    layer: str = Query(..., min_length=1, max_length=_MAX_NAME),
    field: str = Query(..., min_length=1, max_length=_MAX_NAME),
    search: str = Query("", max_length=200, description="Text fields: only values containing this text"),
    limit: int = Query(50, ge=1, le=200),
) -> FieldValues:
    """Distinct values of a vector field, among the features the layer shows now."""
    values = _accessor(request).field_values(layer, field, search=search, limit=limit)
    if values is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layer or field not found")
    return values

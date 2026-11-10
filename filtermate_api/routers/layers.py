"""GET /layers — list layers visible to the FilterMate session.

Issue #30. Read-only endpoint, returns the projection from
:class:`filtermate_api.accessor.LayerSummary`.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from ..accessor import FeatureSample, FieldValues, FilterMateAccessor, LayerDetails, LayerStatistics, LayerSummary

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


class StatisticsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME, description="Vector layer id or name")
    field: str = Field("", max_length=_MAX_NAME, description="Field whose values are summed up")
    group_by: str = Field("", max_length=_MAX_NAME, description="Field whose values make the groups")
    measure: Literal["", "length", "area"] = Field("", description="Measure the geometries instead of a field")
    selected_only: bool = Field(False, description="Only the selected features")
    limit: int = Field(20, ge=1, le=100, description="At most this many groups")


@router.post("/statistics", response_model=LayerStatistics)
def layer_statistics(payload: StatisticsRequest, request: Request) -> LayerStatistics:
    """Statistics of a field or of the geometries of a vector layer, in all and by group."""
    statistics = _accessor(request).layer_statistics(
        payload.layer, field_name=payload.field, group_by=payload.group_by, measure=payload.measure,
        selected_only=payload.selected_only, limit=payload.limit)
    if statistics is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layer or field not found")
    return statistics


class SampleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME, description="Vector layer id or name")
    limit: int = Field(5, ge=1, le=20, description="At most this many features")
    fields: Optional[List[str]] = Field(None, max_length=50, description="Only these fields; all by default")
    expression: str = Field("", max_length=100_000, description="QGIS expression the features must match")
    selected_only: bool = Field(False, description="Only the selected features")
    geometry: bool = Field(False, description="Also the type, centroid and bounding box of each geometry")


@router.post("/sample", response_model=FeatureSample)
def sample_features(payload: SampleRequest, request: Request) -> FeatureSample:
    """A few features of a vector layer, with their attributes."""
    sample = _accessor(request).sample_features(
        payload.layer, limit=payload.limit, fields=payload.fields, expression=payload.expression,
        selected_only=payload.selected_only, geometry=payload.geometry)
    if sample is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layer not found")
    return sample

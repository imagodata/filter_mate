"""GET /layers — list layers visible to the FilterMate session.

Issue #30. Read-only endpoint, returns the projection from
:class:`filtermate_api.accessor.LayerSummary`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..accessor import (
    EditResult, FeatureSample, FieldValues, FilterMateAccessor, LabelsResult, LayerDetails, LayerStatistics, LayerSummary,
    StyleResult,
)

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


class StyleRequest(BaseModel):
    # 2026-11-12: NaN and Infinity refused (422), as the filter routes do
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME)
    mode: Literal["single", "categorized", "graduated", "pseudocolor", "gray"]
    field: str = Field("", max_length=_MAX_NAME)
    color: str = Field("", max_length=50)
    ramp: str = Field("", max_length=100)
    classes: int = Field(5, ge=2, le=12)
    method: Literal["quantile", "equal_interval", "jenks", "pretty", "stddev"] = "quantile"
    invert: bool = False
    opacity: Optional[float] = Field(None, ge=0, le=1)
    band: int = Field(1, ge=1, le=1000)
    minimum: Optional[float] = None
    maximum: Optional[float] = None

    @model_validator(mode="after")
    def _check_range(self) -> "StyleRequest":
        if self.minimum is not None and self.maximum is not None and self.minimum >= self.maximum:
            raise ValueError("minimum must be below maximum")
        return self


@router.post("/style", response_model=StyleResult)
def set_layer_style(payload: StyleRequest, request: Request) -> StyleResult:
    """Draw a layer anew: one symbol, categories, classes, a raster ramp or gray stretch, its opacity."""
    options = payload.model_dump(exclude={"layer", "mode"})
    return _accessor(request).set_layer_style(payload.layer, payload.mode, **options)


class LabelsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME)
    field: str = Field("", max_length=_MAX_NAME)
    enabled: bool = True
    size: Optional[float] = Field(None, ge=4, le=72)
    color: str = Field("", max_length=50)
    buffer: bool = True


@router.post("/labels", response_model=LabelsResult)
def set_labels(payload: LabelsRequest, request: Request) -> LabelsResult:
    """Label a vector layer with a field, or turn its labels off."""
    return _accessor(request).set_labels(payload.layer, field=payload.field, enabled=payload.enabled,
                                         size=payload.size, color=payload.color, buffer=payload.buffer)


class UpdateFeaturesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME)
    values: Optional[Dict[str, Any]] = Field(None, description="Field: value")
    formulas: Optional[Dict[str, str]] = Field(None, description="Field: QGIS expression computed on each feature")
    expression: str = Field("", max_length=100_000, description="QGIS expression choosing the features")
    selected_only: bool = False


@router.post("/features/update", response_model=EditResult)
def update_features(payload: UpdateFeaturesRequest, request: Request) -> EditResult:
    """Set fields of the chosen features, in the edit buffer of the layer (not saved)."""
    return _accessor(request).update_features(payload.layer, values=payload.values, formulas=payload.formulas,
                                              expression=payload.expression, selected_only=payload.selected_only)


class DeleteFeaturesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME)
    expression: str = Field("", max_length=100_000)
    selected_only: bool = False


@router.post("/features/delete", response_model=EditResult)
def delete_features(payload: DeleteFeaturesRequest, request: Request) -> EditResult:
    """Delete the chosen features, in the edit buffer of the layer (not saved)."""
    return _accessor(request).delete_features(payload.layer, expression=payload.expression,
                                              selected_only=payload.selected_only)


class NewFeature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wkt: str = Field(..., min_length=1, max_length=1_000_000)
    attributes: Optional[Dict[str, Any]] = None


class AddFeaturesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME)
    features: List[NewFeature] = Field(..., min_length=1, max_length=100)
    crs: str = Field("", max_length=200)


@router.post("/features/add", response_model=EditResult)
def add_features(payload: AddFeaturesRequest, request: Request) -> EditResult:
    """Add features from WKT geometries, in the edit buffer of the layer (not saved)."""
    return _accessor(request).add_features(payload.layer, features=[item.model_dump() for item in payload.features],
                                           crs=payload.crs)

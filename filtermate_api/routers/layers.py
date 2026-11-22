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


class StyleRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expression: str = Field("", max_length=2000, description="QGIS condition; empty for every other feature")
    color: str = Field(..., min_length=1, max_length=50)
    label: str = Field("", max_length=100)
    width: Optional[float] = Field(None, gt=0, le=20, description="Line or outline width, point size, in mm")


class StyleRequest(BaseModel):
    # 2026-11-12: NaN and Infinity refused (422), as the filter routes do
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME)
    mode: Literal["single", "categorized", "graduated", "rules", "proportional", "heatmap", "point_cluster",
                  "point_displacement", "dot_density", "2.5d", "pseudocolor", "gray", "hillshade", "keep"]
    rules: Optional[List[StyleRule]] = Field(None, max_length=20)
    field: str = Field("", max_length=_MAX_NAME)
    color: str = Field("", max_length=50)
    ramp: str = Field("", max_length=100)
    classes: int = Field(5, ge=2, le=12)
    method: Literal["quantile", "equal_interval", "jenks", "pretty", "stddev"] = "quantile"
    center: Optional[float] = Field(None, description="graduated: classes diverging from this value")
    invert: bool = False
    opacity: Optional[float] = Field(None, ge=0, le=1)
    band: int = Field(1, ge=1, le=1000)
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    width: Optional[float] = Field(None, gt=0, le=20, description=(
        "mm: line or outline width, point size; heatmap radius; point_cluster or point_displacement distance; the "
        "largest proportional symbol; the size of a dot"))
    per_dot: Optional[float] = Field(None, gt=0, description="dot_density: how much of the field one dot stands for")
    blend: Literal["", "normal", "multiply", "screen", "overlay", "darken", "lighten", "soft_light",
                   "hard_light"] = ""
    cut: Optional[float] = Field(None, gt=0, le=49, description="Raster: percent of the values left out at each end")
    discrete: bool = Field(False, description="pseudocolor: flat steps (classes of them) instead of a continuous ramp")
    azimuth: float = Field(315.0, ge=0, le=360, description="hillshade: where the light comes from, in degrees")
    altitude: float = Field(45.0, ge=0, le=90, description="hillshade: height of the light above the horizon")
    z_factor: Optional[float] = Field(None, gt=0, le=1000, description="hillshade, 2.5d: stretch of the heights")
    multidirectional: bool = Field(False, description="hillshade: lit from several directions")

    @model_validator(mode="after")
    def _check_range(self) -> "StyleRequest":
        if self.minimum is not None and self.maximum is not None and self.minimum >= self.maximum:
            raise ValueError("minimum must be below maximum")
        return self


@router.post("/style", response_model=StyleResult)
def set_layer_style(payload: StyleRequest, request: Request) -> StyleResult:
    """Draw a layer anew: one symbol, categories, classes, rules, proportional symbols, a heatmap, clusters, dots,
    2.5D blocks, a raster ramp, gray stretch or hillshade, its opacity and how it blends with what is under it."""
    options = payload.model_dump(exclude={"layer", "mode"})
    return _accessor(request).set_layer_style(payload.layer, payload.mode, **options)


class StylePresetsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field("", max_length=_MAX_NAME, description="Those that fit it; empty: every preset")


@router.post("/style/presets")
def list_style_presets(payload: StylePresetsRequest, request: Request) -> Dict[str, Any]:
    """The official styles of data producers (BD TOPO of IGN, OpenStreetMap), or those that fit a layer."""
    return _accessor(request).list_style_presets(payload.layer)


class StylePresetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME)
    preset: str = Field(..., min_length=1, max_length=200, description="ign/bdtopo/classique; /table to force one")
    variant: Literal["", "gris", "sombre"] = ""
    all_scales: bool = Field(False, description="Drawn at every scale, the zoom levels of the producer dropped")


@router.post("/style/preset")
def apply_style_preset(payload: StylePresetRequest, request: Request) -> Dict[str, Any]:
    """Draw a vector layer in an official style: its rules, symbols, labels and scale ranges."""
    return _accessor(request).apply_style_preset(payload.layer, payload.preset, variant=payload.variant,
                                                 all_scales=payload.all_scales)


class LabelsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    layer: str = Field(..., min_length=1, max_length=_MAX_NAME)
    field: str = Field("", max_length=_MAX_NAME)
    enabled: bool = True
    size: Optional[float] = Field(None, ge=4, le=72)
    color: str = Field("", max_length=50)
    buffer: bool = True
    expression: str = Field("", max_length=2000)
    visible_from_scale: Optional[float] = Field(None, ge=1, le=1e9)
    placement: Literal["auto", "curved", "parallel", "horizontal", "centroid", "free", "around", "perimeter"] = "auto"
    visible_to_scale: Optional[float] = Field(None, ge=1, le=1e9, description="Hidden when the map is closer")
    background: str = Field("", max_length=50, description="Color of a box behind the text")
    background_opacity: Optional[float] = Field(None, ge=0, le=1)
    callouts: bool = Field(False, description="A line from a label moved away to its feature")
    font: str = Field("", max_length=100, description="Font family")
    bold: bool = False
    italic: bool = False
    wrap: Optional[int] = Field(None, ge=5, le=200, description="Characters per line at most")
    priority: Optional[int] = Field(None, ge=0, le=10, description="Labels of a higher priority are placed first")
    obstacle: Optional[bool] = Field(None, description="false: other labels may cover the features of the layer")

    @model_validator(mode="after")
    def _check_scales(self) -> "LabelsRequest":
        if (self.visible_from_scale is not None and self.visible_to_scale is not None
                and self.visible_to_scale >= self.visible_from_scale):
            raise ValueError("visible_to_scale must be below visible_from_scale")
        return self


@router.post("/labels", response_model=LabelsResult)
def set_labels(payload: LabelsRequest, request: Request) -> LabelsResult:
    """Label a vector layer with a field, or turn its labels off."""
    options = payload.model_dump(exclude={"layer", "field", "enabled", "size", "color", "buffer", "expression",
                                          "visible_from_scale", "placement"}, exclude_none=True)
    return _accessor(request).set_labels(payload.layer, field=payload.field, enabled=payload.enabled,
                                         size=payload.size, color=payload.color, buffer=payload.buffer,
                                         expression=payload.expression, visible_from_scale=payload.visible_from_scale,
                                         placement=payload.placement, **options)


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


class DesignStyleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer: str = Field(..., min_length=1, max_length=1000)
    mode: Literal["single", "categorized", "graduated"] = "single"
    field: str = Field("", max_length=200)
    palette: str = Field("", max_length=40)
    look: Literal["flat", "outlined", "hatched", "casing", "halo", "dashed", "icon", "badge"] = "flat"
    icon: str = Field("", max_length=60)
    variant: Literal["light", "dark", "print", "discreet"] = "light"
    classes: int = Field(5, ge=2, le=9)
    method: Literal["quantile", "equal_interval", "jenks", "pretty"] = "quantile"
    limit: int = Field(8, ge=1, le=12)
    reverse: bool = False
    size: Optional[float] = Field(None, gt=0, le=20)
    opacity: Optional[float] = Field(None, ge=0, le=1)
    color: str = Field("", max_length=20)


@router.post("/design-style")
def design_style(payload: DesignStyleRequest, request: Request) -> Dict[str, Any]:
    """Compose a style for a vector layer from a validated palette (a refusal: FilterRejected, 400)."""
    options = payload.model_dump(exclude={"layer"}, exclude_none=True)
    return _accessor(request).design_style(payload.layer, **options)


@router.get("/palettes")
def list_palettes(request: Request, role: str = Query("", max_length=20)) -> Dict[str, Any]:
    """The palettes of a role, or all, and what the check of colours says of them."""
    return _accessor(request).list_palettes(role)

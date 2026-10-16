"""POST /filters/apply — apply a filter expression to a named layer.

Issue #29. Mirrors ``FilterMatePublicAPI.apply_filter``: client supplies
``layer_name`` + ``expression`` (+ optional ``source`` tag for telemetry),
the accessor delegates to the running plugin, and the response carries
the resulting active-filter map so callers don't need a follow-up GET to
sync state.
"""

from __future__ import annotations

from typing import Annotated, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..accessor import (
    CrossFilterResult,
    FilteredLayer,
    FilterMateAccessor,
    FilterStatus,
    HistoryStep,
    OperationResult,
)
from ..main_thread import QGISBusy

router = APIRouter(prefix="/filters", tags=["filters"])

# Field caps, below the 1 MiB body cap (server.BodySizeLimitMiddleware):
# no single field may carry the whole body.
_MAX_NAME = 1000          # layer names
_MAX_EXPRESSION = 500_000  # subset strings (long IN lists stay possible)
_MAX_LAYERS = 1000        # layers per request
# Buffer bound, in layer units (metres for a geographic CRS): 10 000 km.
_MAX_BUFFER = 1e7

# A layer name (or id) in a list: capped like a single one.
LayerName = Annotated[str, Field(max_length=_MAX_NAME)]


class ApplyFilterRequest(BaseModel):
    layer_name: str = Field(..., min_length=1, max_length=_MAX_NAME, description="Target QGIS layer name")
    expression: str = Field(
        ..., min_length=1, max_length=_MAX_EXPRESSION, description="QGIS filter expression to apply"
    )
    source: str = Field(
        default="rest_api",
        max_length=200,
        description=(
            "Free-text tag identifying the caller — surfaced in plugin "
            "logs / signals so end users can tell where a filter came from"
        ),
    )


class ApplyFilterResponse(BaseModel):
    success: bool
    layer_name: str
    expression: str
    source: str
    active_filters: Dict[str, str] = Field(
        default_factory=dict,
        description="Snapshot of all active filters after this apply call",
    )


def _accessor(request: Request) -> FilterMateAccessor:
    accessor: FilterMateAccessor = request.app.state.accessor
    return accessor


def active_filters_after_change(accessor: FilterMateAccessor) -> Dict[str, str]:
    """Snapshot sent back with a change, ``{}`` when QGIS is too busy to read it.

    The change is done by then: answering 503 would make the client retry
    it (an undo applied twice). ``GET /filters/state`` reads the state.
    """
    try:
        return accessor.get_active_filters()
    except QGISBusy:
        return {}


def _failed(operation: str, error: str) -> HTTPException:
    """400 naming what stopped the operation (a busy QGIS is a 503, see server)."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{operation} failed: {error}")


@router.post("/apply", response_model=ApplyFilterResponse)
def apply_filter(
    payload: ApplyFilterRequest, request: Request
) -> ApplyFilterResponse:
    """Apply a QGIS filter expression to the named layer."""
    accessor = _accessor(request)

    success = accessor.apply_filter(
        layer_name=payload.layer_name,
        expression=payload.expression,
        source=payload.source,
    )
    if not success:
        # 404 — the layer name didn't resolve. Distinct from a 400 (bad
        # expression) so clients can branch on it. P1-API-HARDEN (audit
        # 2026-04-29): don't echo the user-supplied name into the error
        # body — caller already has it from the request payload, and a
        # static message removes the reflected-input surface.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layer not found",
        )

    return ApplyFilterResponse(
        success=True,
        layer_name=payload.layer_name,
        expression=payload.expression,
        source=payload.source,
        active_filters=active_filters_after_change(accessor),
    )


@router.get("/status", response_model=FilterStatus)
def get_filter_status(request: Request) -> FilterStatus:
    """Issue #31 — return a snapshot of the session's current filter state."""
    return _accessor(request).get_filter_status()


class HistoryStepResponse(BaseModel):
    status: str = "ok"
    step: HistoryStep
    active_filters: Dict[str, str] = Field(default_factory=dict)


@router.post("/undo", response_model=HistoryStepResponse)
def undo_filter(request: Request) -> HistoryStepResponse:
    """Issue #33 — pop the last filter step from the undo stack.

    Returns the step we just rolled back TO. 409 when there is nothing
    to undo so clients can disable the button without polling /status
    first.

    This is the dock's Undo for vector filters: the same history, whatever
    added the last step. ``POST /filters/apply`` and the FilterMate 5
    operations (cross, geometry, point cloud, clear) record nothing in it:
    revert those with ``POST /filters/clear``.
    """
    accessor = _accessor(request)
    step = accessor.undo_filter()
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nothing to undo",
        )
    return HistoryStepResponse(
        step=step,
        active_filters=active_filters_after_change(accessor),
    )


@router.post("/redo", response_model=HistoryStepResponse)
def redo_filter(request: Request) -> HistoryStepResponse:
    """Issue #33 — re-apply the most recently undone step (the dock's Redo for vector filters)."""
    accessor = _accessor(request)
    step = accessor.redo_filter()
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nothing to redo",
        )
    return HistoryStepResponse(
        step=step,
        active_filters=active_filters_after_change(accessor),
    )


# --- FilterMate 5: cross filter -----------------------------------------------

_PREDICATES = ("Intersect", "Contain", "Disjoint", "Equal", "Touch", "Overlap", "Are within", "Cross")
_OPERATORS = ("AND", "OR", "AND NOT")


class RasterSelectionBody(BaseModel):
    """Pixels kept on a raster source (same rules as the EXPLORING raster panel)."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    band: int = Field(default=1, ge=1, description="1-based band number")
    mode: Literal["range", "classes", "expression"] = Field(default="range")
    minimum: Optional[float] = Field(default=None, description="range: lower bound (inclusive)")
    maximum: Optional[float] = Field(default=None, description="range: upper bound (inclusive)")
    classes: List[int] = Field(default_factory=list, description="classes: pixel values kept")
    expression: str = Field(default="", max_length=2000,
                            description='expression: raster calculator expression, e.g. "mnt@1" > 1200')

    @model_validator(mode="after")
    def _check_mode(self) -> "RasterSelectionBody":
        if self.mode == "range":
            if self.minimum is None and self.maximum is None:
                raise ValueError("a range needs a minimum, a maximum or both")
            if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
                raise ValueError("minimum is greater than maximum")
        elif self.mode == "classes" and not self.classes:
            raise ValueError("a classes selection needs at least one class")
        elif self.mode == "expression" and not self.expression.strip():
            raise ValueError("an expression selection needs an expression")
        return self


class PointCloudCriteriaBody(BaseModel):
    """Points kept on a point cloud (ASPRS classes, ranges, return number, expression)."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    classes: List[int] = Field(default_factory=list, description="ASPRS classification codes kept")
    z_min: Optional[float] = None
    z_max: Optional[float] = None
    intensity_min: Optional[float] = None
    intensity_max: Optional[float] = None
    return_number: Optional[int] = Field(default=None, ge=1, le=15)
    expression: str = Field(default="", max_length=2000, description="Point cloud expression, ANDed with the rest")

    @model_validator(mode="after")
    def _check_bounds(self) -> "PointCloudCriteriaBody":
        for low, high in ((self.z_min, self.z_max), (self.intensity_min, self.intensity_max)):
            if low is not None and high is not None and low > high:
                raise ValueError("minimum is greater than maximum")
        if any(code < 0 or code > 255 for code in self.classes):
            raise ValueError("classification codes are 0-255")
        return self

    def is_empty(self) -> bool:
        return not (self.classes or self.expression.strip() or self.return_number is not None
                    or any(v is not None for v in (self.z_min, self.z_max, self.intensity_min, self.intensity_max)))


class _RelationBody(BaseModel):
    # NaN / Infinity (accepted by Python's JSON parser) are refused: NaN slips
    # through every comparison and a buffer of Infinity covers everything.
    model_config = ConfigDict(allow_inf_nan=False)

    target_layers: List[LayerName] = Field(..., min_length=1, max_length=_MAX_LAYERS,
                                           description="Layers to filter: vector, raster or point cloud")
    predicates: List[Annotated[str, Field(max_length=32)]] = Field(
        default_factory=lambda: ["Intersect"], max_length=len(_PREDICATES),
        description=f"Any of {', '.join(_PREDICATES)}")
    buffer: float = Field(default=0.0, ge=-_MAX_BUFFER, le=_MAX_BUFFER,
                          description="Buffer of the source geometry (source CRS units, metres for a geographic CRS)")
    coverage_min: float = Field(default=0.0, ge=0.0, le=100.0, description="Minimum share of a polygon target inside the source (%)")
    operator: Optional[str] = Field(default=None, description="Combine with the targets' previous filter: AND, OR, AND NOT (null = replace)")


def _check_relation(payload: _RelationBody) -> None:
    if any(p not in _PREDICATES for p in payload.predicates):
        raise HTTPException(status_code=422, detail="Unknown predicate")
    if payload.operator is not None and payload.operator not in _OPERATORS:
        raise HTTPException(status_code=422, detail="Unknown operator")


class CrossFilterRequestBody(_RelationBody):
    source_layer: str = Field(..., min_length=1, max_length=_MAX_NAME,
                              description="Source layer: id or name, vector, raster or point cloud")
    selected_only: bool = Field(default=True, description="Vector source: use the selected features (all when none is selected)")
    raster_selection: Optional[RasterSelectionBody] = Field(
        default=None, description="Raster source (required): pixels kept")
    point_cloud_criteria: Optional[PointCloudCriteriaBody] = Field(
        default=None, description="Point cloud source: points kept (null = the points it shows now)")
    filter_source: bool = Field(default=False, description="Raster source: also mask the source outside the selection")


@router.post("/cross", response_model=CrossFilterResult)
def cross_filter(payload: CrossFilterRequestBody, request: Request) -> CrossFilterResult:
    """Filter layers of any kind (vector, raster, point cloud) by a source of any kind."""
    _check_relation(payload)
    result = _accessor(request).cross_filter(
        source_layer=payload.source_layer, target_layers=payload.target_layers, predicates=payload.predicates,
        buffer=payload.buffer, coverage_min=payload.coverage_min, operator=payload.operator,
        selected_only=payload.selected_only,
        raster_selection=payload.raster_selection.model_dump() if payload.raster_selection else None,
        point_cloud_criteria=(payload.point_cloud_criteria.model_dump()
                              if payload.point_cloud_criteria and not payload.point_cloud_criteria.is_empty() else None),
        filter_source=payload.filter_source)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source layer not found")
    if result.error:
        raise _failed("Cross filter", result.error)
    return result


class GeometryFilterRequestBody(_RelationBody):
    wkt: str = Field(..., min_length=1, max_length=1_000_000, description="Geometry in WKT (polygon, extent...)")
    crs: str = Field(..., min_length=1, max_length=64, description="CRS of the geometry, e.g. EPSG:2154")


@router.post("/geometry", response_model=CrossFilterResult)
def geometry_filter(payload: GeometryFilterRequestBody, request: Request) -> CrossFilterResult:
    """Filter layers of any kind by a WKT geometry (an area drawn by a web client, an extent)."""
    _check_relation(payload)
    result = _accessor(request).cross_filter_by_geometry(
        wkt=payload.wkt, crs=payload.crs, target_layers=payload.target_layers, predicates=payload.predicates,
        buffer=payload.buffer, coverage_min=payload.coverage_min, operator=payload.operator)
    if result.error:
        raise _failed("Geometry filter", result.error)
    return result


class PointCloudFilterRequestBody(BaseModel):
    layers: List[LayerName] = Field(..., min_length=1, max_length=_MAX_LAYERS,
                                    description="Point cloud layers (LiDAR tiles...)")
    criteria: PointCloudCriteriaBody
    operator: Optional[str] = Field(default=None, description="Combine with each layer's filter: AND, OR, AND NOT (null = replace)")


@router.post("/point-cloud", response_model=OperationResult)
def point_cloud_filter(payload: PointCloudFilterRequestBody, request: Request) -> OperationResult:
    """Apply the same criteria to several point cloud layers."""
    if payload.criteria.is_empty():
        raise HTTPException(status_code=422, detail="Empty point cloud criteria")
    if payload.operator is not None and payload.operator not in _OPERATORS:
        raise HTTPException(status_code=422, detail="Unknown operator")
    result = _accessor(request).filter_point_clouds(
        layers=payload.layers, criteria=payload.criteria.model_dump(), operator=payload.operator)
    if result.error:
        raise _failed("Point cloud filter", result.error)
    return result


class ClearFiltersRequestBody(BaseModel):
    layers: List[LayerName] = Field(..., min_length=1, max_length=_MAX_LAYERS,
                                    description="Layers of any kind to unfilter")


@router.post("/clear", response_model=OperationResult)
def clear_filters(payload: ClearFiltersRequestBody, request: Request) -> OperationResult:
    """Put layers of any kind back on their original source, with no filter.

    Not in the dock's undo history (its own Unfilter records nothing either).
    """
    result = _accessor(request).clear_filters(layers=payload.layers)
    if result.error:
        raise _failed("Clear", result.error)
    return result


@router.get("/state", response_model=List[FilteredLayer])
def filter_state(request: Request) -> List[FilteredLayer]:
    """Every layer FilterMate filters now: subset string and / or clipped source."""
    return _accessor(request).get_filter_state()

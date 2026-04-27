"""POST /filters/apply — apply a filter expression to a named layer.

Issue #29. Mirrors ``FilterMatePublicAPI.apply_filter``: client supplies
``layer_name`` + ``expression`` (+ optional ``source`` tag for telemetry),
the accessor delegates to the running plugin, and the response carries
the resulting active-filter map so callers don't need a follow-up GET to
sync state.
"""

from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..accessor import FilterMateAccessor, FilterStatus, HistoryStep

router = APIRouter(prefix="/filters", tags=["filters"])


class ApplyFilterRequest(BaseModel):
    layer_name: str = Field(..., min_length=1, description="Target QGIS layer name")
    expression: str = Field(
        ..., min_length=1, description="QGIS filter expression to apply"
    )
    source: str = Field(
        default="rest_api",
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


@router.post("/apply", response_model=ApplyFilterResponse)
async def apply_filter(
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
        # 404 — the layer name didn't resolve. We surface this distinctly
        # from a 400 (bad expression) so clients can branch on it.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer not found: {payload.layer_name!r}",
        )

    return ApplyFilterResponse(
        success=True,
        layer_name=payload.layer_name,
        expression=payload.expression,
        source=payload.source,
        active_filters=accessor.get_active_filters(),
    )


@router.get("/status", response_model=FilterStatus)
async def get_filter_status(request: Request) -> FilterStatus:
    """Issue #31 — return a snapshot of the session's current filter state."""
    return _accessor(request).get_filter_status()


class HistoryStepResponse(BaseModel):
    status: str = "ok"
    step: HistoryStep
    active_filters: Dict[str, str] = Field(default_factory=dict)


@router.post("/undo", response_model=HistoryStepResponse)
async def undo_filter(request: Request) -> HistoryStepResponse:
    """Issue #33 — pop the last filter step from the undo stack.

    Returns the step we just rolled back TO. 409 when there is nothing
    to undo so clients can disable the button without polling /status
    first.
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
        active_filters=accessor.get_active_filters(),
    )


@router.post("/redo", response_model=HistoryStepResponse)
async def redo_filter(request: Request) -> HistoryStepResponse:
    """Issue #33 — re-apply the most recently undone step."""
    accessor = _accessor(request)
    step = accessor.redo_filter()
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nothing to redo",
        )
    return HistoryStepResponse(
        step=step,
        active_filters=accessor.get_active_filters(),
    )

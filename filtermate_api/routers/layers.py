"""GET /layers — list layers visible to the FilterMate session.

Issue #30. Read-only endpoint, returns the projection from
:class:`filtermate_api.accessor.LayerSummary`.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Request

from ..accessor import FilterMateAccessor, LayerSummary

router = APIRouter(prefix="/layers", tags=["layers"])


def _accessor(request: Request) -> FilterMateAccessor:
    """Pull the configured accessor off the FastAPI app state.

    Routes use ``Request`` rather than a ``Depends(...)`` factory because
    the accessor is bound at app construction time — there's no request-
    scoped state to plumb through.
    """
    accessor: FilterMateAccessor = request.app.state.accessor
    return accessor


@router.get("", response_model=List[LayerSummary])
async def list_layers(request: Request) -> List[LayerSummary]:
    """Return every layer the FilterMate session knows about."""
    return _accessor(request).list_layers()

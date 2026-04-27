"""GET /favorites and POST /favorites/{id}/apply — issue #32.

Read-mostly endpoints that surface the FilterMate favorites store to
external clients (Narractive). The mutating side (create / delete) is
deferred — the plugin's own UI owns favorite authorship for now.
"""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..accessor import Favorite, FilterMateAccessor, HistoryStep

router = APIRouter(prefix="/favorites", tags=["favorites"])


def _accessor(request: Request) -> FilterMateAccessor:
    accessor: FilterMateAccessor = request.app.state.accessor
    return accessor


@router.get("", response_model=List[Favorite])
async def list_favorites(request: Request) -> List[Favorite]:
    """Return every favorite the FilterMate session knows about."""
    return _accessor(request).list_favorites()


class ApplyFavoriteResponse(BaseModel):
    status: str = "ok"
    step: HistoryStep
    active_filters: Dict[str, str] = Field(default_factory=dict)


@router.post("/{favorite_id}/apply", response_model=ApplyFavoriteResponse)
async def apply_favorite(favorite_id: str, request: Request) -> ApplyFavoriteResponse:
    """Apply the favorite identified by ``favorite_id``."""
    accessor = _accessor(request)
    step = accessor.apply_favorite(favorite_id)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Favorite not found or has no target layer: {favorite_id!r}",
        )
    return ApplyFavoriteResponse(
        step=step,
        active_filters=accessor.get_active_filters(),
    )

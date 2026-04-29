"""GET /favorites and POST /favorites/{id}/apply — issue #32.

Read-mostly endpoints that surface the FilterMate favorites store to
external clients (Narractive). The mutating side (create / delete) is
deferred — the plugin's own UI owns favorite authorship for now.
"""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..accessor import Favorite, FavoritesUnavailable, FilterMateAccessor, HistoryStep

router = APIRouter(prefix="/favorites", tags=["favorites"])

# P1-API-HARDEN (audit 2026-04-29): the plugin can come up before its
# favorites store is fully wired (project not loaded, persistence layer
# offline). Tell clients to retry rather than letting them silently
# treat "not ready" as "no favorites configured". 30s is the empirical
# warm-up budget for a typical QGIS startup.
_FAVORITES_RETRY_AFTER_SECONDS = 30


def _accessor(request: Request) -> FilterMateAccessor:
    accessor: FilterMateAccessor = request.app.state.accessor
    return accessor


def _favorites_unavailable_response() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Favorites store not ready",
        headers={"Retry-After": str(_FAVORITES_RETRY_AFTER_SECONDS)},
    )


@router.get("", response_model=List[Favorite])
async def list_favorites(request: Request) -> List[Favorite]:
    """Return every favorite the FilterMate session knows about."""
    try:
        return _accessor(request).list_favorites()
    except FavoritesUnavailable:
        raise _favorites_unavailable_response()


class ApplyFavoriteResponse(BaseModel):
    status: str = "ok"
    step: HistoryStep
    active_filters: Dict[str, str] = Field(default_factory=dict)


@router.post("/{favorite_id}/apply", response_model=ApplyFavoriteResponse)
async def apply_favorite(favorite_id: str, request: Request) -> ApplyFavoriteResponse:
    """Apply the favorite identified by ``favorite_id``."""
    accessor = _accessor(request)
    try:
        step = accessor.apply_favorite(favorite_id)
    except FavoritesUnavailable:
        raise _favorites_unavailable_response()
    if step is None:
        # P1-API-HARDEN: don't echo the user-supplied id back into the
        # error body — clients already have it from the URL, and a
        # static message removes a tiny reflected-input surface.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found or has no target layer",
        )
    return ApplyFavoriteResponse(
        step=step,
        active_filters=accessor.get_active_filters(),
    )

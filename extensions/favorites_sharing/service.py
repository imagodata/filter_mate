# -*- coding: utf-8 -*-
"""
FavoritesSharing service layer.

Pure-Python orchestration between the :class:`ResourceSharingScanner`
(filesystem-level) and the :class:`FavoritesService` (plugin-level).

Responsibilities:
- Cache of shared favorites (re-scan on demand).
- Fork a shared favorite into the current project's DB, rebinding
  portable signatures to local layer UUIDs when possible.
- Provide filtered views for the "Shared" dialog section (by collection,
  by search query).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .scanner import ResourceSharingScanner, SharedFavorite

logger = logging.getLogger('FilterMate.FavoritesSharing.Service')


class FavoritesSharingService:
    """Bridge between discovered shared favorites and the local DB."""

    def __init__(self, scanner: ResourceSharingScanner):
        self._scanner = scanner

    # ─── Discovery ─────────────────────────────────────────────────────

    def list_shared(self, search_query: Optional[str] = None) -> List[SharedFavorite]:
        """Return shared favorites matching an optional search query.

        Search is case-insensitive and applied on name, description,
        collection name, and tags.
        """
        items = self._scanner.scan()
        if not search_query:
            return items

        needle = search_query.lower().strip()
        if not needle:
            return items

        def _matches(fav: SharedFavorite) -> bool:
            if needle in fav.name.lower():
                return True
            if needle in fav.description.lower():
                return True
            if needle in fav.source.collection_name.lower():
                return True
            tags = fav.payload.get('tags') or []
            if isinstance(tags, list) and any(needle in str(t).lower() for t in tags):
                return True
            return False

        return [f for f in items if _matches(f)]

    def invalidate_cache(self) -> None:
        self._scanner.invalidate_cache()

    def collections_summary(self) -> Dict[str, int]:
        """Return {collection_name: shared_favorites_count}."""
        summary: Dict[str, int] = {}
        for fav in self._scanner.scan():
            summary[fav.source.collection_name] = (
                summary.get(fav.source.collection_name, 0) + 1
            )
        return summary

    # ─── Fork ──────────────────────────────────────────────────────────

    def fork(
        self,
        shared: SharedFavorite,
        favorites_service: Any,
        override_name: Optional[str] = None,
    ) -> Optional[str]:
        """Materialize a shared favorite into the user's local DB.

        The forked favorite:
        - gets a new UUID (the original is never touched);
        - preserves the author's ``created_at`` as ``_extra.original_created_at``;
        - resets ``use_count`` to 0;
        - has its portable ``layer_signature`` entries re-resolved to
          current-project layer UUIDs via ``_rebind_imported_favorite``.

        Args:
            shared: The SharedFavorite discovered by the scanner.
            favorites_service: The running :class:`FavoritesService`
                (obtained from ``dockwidget._favorites_manager``).
            override_name: When provided, used instead of the bundled name
                (the Fork dialog lets users rename on the fly).

        Returns:
            New favorite id on success, ``None`` otherwise.
        """
        try:
            from filter_mate.core.services.favorites_service import FavoritesService
            from filter_mate.core.domain.favorites_manager import FilterFavorite
        except Exception:  # pragma: no cover — plugin package import guard
            logger.exception("Cannot import FilterMate core for Fork")
            return None

        # Re-bind signatures to local layer UUIDs using the existing helper.
        rebound = FavoritesService._rebind_imported_favorite(
            dict(shared.payload),
            str(shared.schema_version),
        )

        # Record provenance in _extra so it round-trips through re-export.
        extra = dict(rebound.get('_extra') or {})
        extra.setdefault('original_created_at', shared.payload.get('created_at'))
        extra.setdefault('forked_from', {
            'collection': shared.source.collection_name,
            'file': shared.source.file_path,
        })
        rebound['_extra'] = extra

        # Apply rename if requested
        if override_name:
            rebound['name'] = override_name

        # Strip identity fields that would collide with existing rows
        rebound.pop('id', None)
        rebound.pop('project_uuid', None)
        # Reset usage stats on fork — it's a brand-new copy
        rebound['use_count'] = 0
        rebound['last_used_at'] = None

        favorite = FilterFavorite.from_dict(rebound)
        favorite.id = None  # Will generate new ID in add_favorite

        manager = getattr(favorites_service, 'favorites_manager', favorites_service)
        add_fn = getattr(manager, 'add_favorite', None)
        if not callable(add_fn):
            logger.error("Fork failed: manager has no add_favorite()")
            return None

        # Use preserve_timestamps=True so the fork keeps the author's
        # original created_at. If the caller wants a fresh timestamp, they
        # can override via favorite.created_at before fork.
        try:
            success = add_fn(favorite, preserve_timestamps=True)
        except TypeError:
            # Raw FavoritesManager without the preserve_timestamps kwarg
            success = add_fn(favorite)

        if not success:
            return None

        # Let the service emit favorites_changed so the UI refreshes.
        emit_fn = getattr(favorites_service, 'favorites_changed', None)
        if emit_fn is not None and hasattr(emit_fn, 'emit'):
            try:
                emit_fn.emit()
            except Exception:
                pass

        # Also persist the .qgz backup so the fork survives installer wipes.
        backup_fn = getattr(favorites_service, 'save_to_project_file', None)
        if callable(backup_fn):
            try:
                backup_fn()
            except Exception as e:
                logger.debug(f"Post-fork .qgz backup skipped: {e}")

        logger.info(
            f"Forked shared favorite '{favorite.name}' from collection "
            f"'{shared.source.collection_name}' → id={favorite.id}"
        )
        return favorite.id

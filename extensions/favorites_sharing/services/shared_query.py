# -*- coding: utf-8 -*-
"""Read-side of the favorites-sharing service: list / filter / cache.

EXT-2 stage 1 (audit 2026-04-29): split out from
``FavoritesSharingService`` so the read path (which the
``SharedFavoritesPickerDialog`` uses heavily) has its own boundary
against the writer / fork paths. Same scanner instance backs all
three services.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ..scanner import ResourceSharingScanner, SharedFavorite

logger = logging.getLogger('FilterMate.FavoritesSharing.SharedQuery')


class SharedFavoritesQuery:
    """List + filter shared favorites discovered by the scanner.

    Stateless aside from the scanner reference: every call goes back to
    ``scanner.scan()`` which carries its own caching policy. Keep this
    class read-only — anything that mutates the local DB belongs in
    :class:`FavoritesForkService`.
    """

    def __init__(self, scanner: ResourceSharingScanner):
        self._scanner = scanner

    def list_shared(
        self,
        search_query: Optional[str] = None,
        author: Optional[str] = None,
    ) -> List[SharedFavorite]:
        """Return shared favorites matching the given filters.

        Search is case-insensitive and applied on name, description,
        collection name, and tags. ``author`` is an exact (case-
        insensitive) match on the collection-level ``author`` — None /
        empty means "any author".
        """
        items = self._scanner.scan()

        if author:
            needle_author = author.strip().lower()
            if needle_author:
                items = [f for f in items if f.author.lower() == needle_author]

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
            if fav.author and needle in fav.author.lower():
                return True
            tags = fav.payload.get('tags') or []
            if isinstance(tags, list) and any(needle in str(t).lower() for t in tags):
                return True
            return False

        return [f for f in items if _matches(f)]

    def list_authors(self) -> List[str]:
        """Return the distinct collection authors found across all shared
        favorites, sorted alphabetically. Empty/anonymous authors are
        omitted — the picker shows them under the "All authors" entry.
        """
        seen: Dict[str, None] = {}
        for fav in self._scanner.scan():
            a = fav.author
            if a and a not in seen:
                seen[a] = None
        return sorted(seen.keys(), key=str.lower)

    def invalidate_cache(self) -> None:
        """Forget cached scan results — next list_*() call re-scans."""
        self._scanner.invalidate_cache()

    def collections_summary(self) -> Dict[str, int]:
        """Return ``{collection_name: shared_favorites_count}``."""
        summary: Dict[str, int] = {}
        for fav in self._scanner.scan():
            summary[fav.source.collection_name] = (
                summary.get(fav.source.collection_name, 0) + 1
            )
        return summary

# -*- coding: utf-8 -*-
"""Decomposed FavoritesSharingService — split per responsibility.

EXT-2 (audit 2026-04-29): the original ``FavoritesSharingService`` was
a 607-LOC god-class mixing five domains (scan, fork, publish targets,
bundle production, helpers). It now hosts three focused services:

- :class:`SharedFavoritesQuery` — listing / filtering / cache.
- :class:`FavoritesForkService` — materialising a shared favorite into
  the local DB (the trust-boundary path: third-party content lands
  here, sanitiser runs, owner is reset).
- :class:`BundlePublisher` — serialising favorites to a Resource-Sharing
  collection bundle (the writer path).

``FavoritesSharingService`` (in the parent module) keeps the public
surface as a thin facade so callers (extension entry point, dialogs,
tests) need not relearn the new layout.
"""

from .shared_query import SharedFavoritesQuery

__all__ = [
    "SharedFavoritesQuery",
]

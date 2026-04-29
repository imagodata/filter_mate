# -*- coding: utf-8 -*-
"""FavoritesSharing service layer — facade over three focused services.

EXT-2 (audit 2026-04-29): the original 607-LOC god-class is now a
thin facade. The actual work lives in:

- :class:`SharedFavoritesQuery` — read path / filter / cache.
- :class:`FavoritesForkService` — trust boundary / materialise into
  the local DB (with sanitiser, signature rebind, owner reset).
- :class:`BundlePublisher` — writer path / produce a v3 bundle inside
  a Resource Sharing collection.

This module keeps the public surface (``list_shared``, ``fork``,
``publish_bundle`` and friends) so callers — extension entry point,
publish + shared-picker dialogs, tests — need not relearn the layout.
The two dataclasses (:class:`CollectionTarget`, :class:`PublishResult`)
also stay here so they remain importable from ``extensions
.favorites_sharing.service`` as before.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .scanner import ResourceSharingScanner, SharedFavorite
from .services import BundlePublisher, FavoritesForkService, SharedFavoritesQuery

logger = logging.getLogger('FilterMate.FavoritesSharing.Service')


@dataclass
class CollectionTarget:
    """Location where a bundle can be published.

    ``collection_dir`` is the root of the collection (contains or will
    contain ``collection.json`` and ``filter_mate/favorites/``).
    ``display_name`` is what we show in the dropdown; it defaults to the
    directory basename but is overridden by any ``name`` key found in an
    existing ``collection.json``.
    """
    collection_dir: str
    display_name: str
    is_new: bool = False  # True when the directory does not exist yet
    existing_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishResult:
    """Outcome of :meth:`FavoritesSharingService.publish_bundle`."""
    success: bool
    bundle_path: str = ""
    collection_manifest_path: str = ""
    favorites_count: int = 0
    error_message: str = ""


class FavoritesSharingService:
    """Bridge between discovered shared favorites and the local DB."""

    def __init__(self, scanner: ResourceSharingScanner):
        self._scanner = scanner
        # EXT-2 (audit 2026-04-29): the god-class is now a facade over
        # focused services. Same public surface — delegations preserve
        # BC for the dialogs / extension entry point / tests.
        self._query = SharedFavoritesQuery(scanner)
        self._fork = FavoritesForkService()
        self._publisher = BundlePublisher(scanner)

    @property
    def extension(self):
        """Owning FavoritesSharingExtension (or None when used standalone)."""
        return getattr(self._scanner, "_extension", None)

    # ─── Discovery (delegated to SharedFavoritesQuery) ────────────────

    def list_shared(
        self,
        search_query: Optional[str] = None,
        author: Optional[str] = None,
    ) -> List[SharedFavorite]:
        return self._query.list_shared(search_query=search_query, author=author)

    def list_authors(self) -> List[str]:
        return self._query.list_authors()

    def invalidate_cache(self) -> None:
        self._query.invalidate_cache()

    def collections_summary(self) -> Dict[str, int]:
        return self._query.collections_summary()

    # ─── Fork ──────────────────────────────────────────────────────────

    def fork(
        self,
        shared: SharedFavorite,
        favorites_service: Any,
        override_name: Optional[str] = None,
    ) -> Optional[str]:
        """Materialize a shared favorite into the user's local DB.

        Delegates to :class:`FavoritesForkService` (EXT-2 stage 2). See
        that class's docstring for the trust-boundary contract.
        """
        return self._fork.fork(shared, favorites_service, override_name=override_name)

    # ─── Publish ───────────────────────────────────────────────────────

    def has_configured_collections_root(self) -> bool:
        return self._publisher.has_configured_collections_root()

    def list_publish_targets(self) -> List[CollectionTarget]:
        return self._publisher.list_publish_targets()

    def suggest_new_collection_dir(self, folder_name: str) -> Optional[str]:
        return self._publisher.suggest_new_collection_dir(folder_name)

    @staticmethod
    def _sanitize_bundle_filename(raw: str, default: str = "favorites") -> str:
        """Backwards-compat alias of :meth:`BundlePublisher.sanitize_bundle_filename`."""
        return BundlePublisher.sanitize_bundle_filename(raw, default=default)

    def publish_bundle(
        self,
        favorites_service: Any,
        target: CollectionTarget,
        bundle_filename: str,
        favorite_ids: List[str],
        collection_metadata: Dict[str, Any],
        overwrite: bool = False,
    ) -> PublishResult:
        """Write a v3 favorites bundle into a Resource Sharing collection.

        Delegates to :class:`BundlePublisher` (EXT-2 stage 3). See that
        class's docstring for the writer-path contract.
        """
        return self._publisher.publish_bundle(
            favorites_service, target, bundle_filename,
            favorite_ids, collection_metadata, overwrite=overwrite,
        )

    @staticmethod
    def _strip_owner_from_bundle(bundle_path: str) -> None:
        """Backwards-compat alias of :meth:`BundlePublisher._strip_owner_from_bundle`.

        Kept on the facade because three favorites-owner-scope tests
        still call it as a class-level helper (independent of the
        publish path).
        """
        BundlePublisher._strip_owner_from_bundle(bundle_path)

    

    

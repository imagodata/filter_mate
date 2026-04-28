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

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .scanner import ResourceSharingScanner, SharedFavorite

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

    @property
    def extension(self):
        """Owning FavoritesSharingExtension (or None when used standalone)."""
        return getattr(self._scanner, "_extension", None)

    # ─── Discovery ─────────────────────────────────────────────────────

    def list_shared(
        self,
        search_query: Optional[str] = None,
        author: Optional[str] = None,
    ) -> List[SharedFavorite]:
        """Return shared favorites matching the given filters.

        Search is case-insensitive and applied on name, description,
        collection name, and tags. ``author`` is an exact (case-insensitive)
        match on the collection-level ``author`` — None / empty means
        "any author".
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
          current-project layer UUIDs via
          :meth:`FavoriteImportHandler.rebind_to_project`.

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
            from filter_mate.core.domain.favorite_import_handler import FavoriteImportHandler
            from filter_mate.core.domain.favorites_manager import FilterFavorite
            from filter_mate.core.domain.layer_signature import LayerSignatureIndex
        except Exception:  # pragma: no cover — plugin package import guard
            logger.exception("Cannot import FilterMate core for Fork")
            return None

        # Re-bind signatures to local layer UUIDs. We use the canonical
        # domain handler directly rather than going through a service
        # wrapper — the handler is stateless and the index is a per-call
        # snapshot of the current QgsProject.
        rebound = FavoriteImportHandler.rebind_to_project(
            dict(shared.payload),
            LayerSignatureIndex(),
            file_version=str(shared.schema_version),
        )

        # Trust boundary: a shared favorite is authored by an arbitrary
        # third party. Run the local subset-string sanitizer on the
        # expression before it lands in the DB so a poisoned display
        # expression / unsafe construct is rejected at fork time, not at
        # apply time. ``sanitize_subset_string`` returns '' for a
        # standalone display expression — refuse the fork in that case.
        raw_expr = str(rebound.get('expression') or '')
        if raw_expr:
            try:
                try:
                    from filter_mate.core.filter import sanitize_subset_string
                except ImportError:
                    from core.filter import sanitize_subset_string  # type: ignore
                cleaned_expr = sanitize_subset_string(raw_expr)
            except Exception:
                logger.exception("Sanitizer unavailable; refusing fork to be safe")
                return None
            if not cleaned_expr:
                logger.warning(
                    "Refusing fork: shared favorite '%s' carries a non-boolean "
                    "expression that the sanitizer rejected.", shared.name,
                )
                return None
            if cleaned_expr != raw_expr:
                logger.info(
                    "Sanitized expression on fork of '%s' (length %d → %d)",
                    shared.name, len(raw_expr), len(cleaned_expr),
                )
                rebound['expression'] = cleaned_expr

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
        # v5.1: also strip ``owner`` — a shared bundle should never pin
        # the forker to the author's identity. ``add_favorite`` will
        # re-stamp with the current user via the cascade.
        rebound.pop('owner', None)
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

    # ─── Publish ───────────────────────────────────────────────────────

    BUNDLE_FILENAME_RE = r'^[a-zA-Z0-9_\-]+\.fmfav(-pack)?\.json$'

    def list_publish_targets(self) -> List[CollectionTarget]:
        """Enumerate directories under the Resource Sharing collections
        root that the user can publish into.

        Every existing sub-directory is considered a valid target; its
        current ``collection.json`` (if any) is loaded so the UI can
        pre-fill the metadata fields when publishing into it. When no
        Resource Sharing root exists yet we return an empty list — the
        caller is expected to ask the user for a custom directory.
        """
        root = self._scanner.get_collections_root()
        targets: List[CollectionTarget] = []
        if not root or not os.path.isdir(root):
            return targets

        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            if not os.path.isdir(path) or name.startswith('.'):
                continue
            manifest_path = os.path.join(path, 'collection.json')
            metadata: Dict[str, Any] = {}
            display = name
            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f) or {}
                    if isinstance(metadata, dict) and metadata.get('name'):
                        display = str(metadata['name'])
                except (OSError, ValueError) as e:
                    logger.debug(f"Cannot read {manifest_path}: {e}")
                    metadata = {}
            targets.append(CollectionTarget(
                collection_dir=path,
                display_name=display,
                is_new=False,
                existing_metadata=metadata,
            ))
        return targets

    def suggest_new_collection_dir(self, folder_name: str) -> Optional[str]:
        """Build a path for a brand-new collection under the Resource
        Sharing root. Returns ``None`` when there is no root to write into.

        The directory is NOT created — :meth:`publish_bundle` will create
        it on first write if it does not already exist.
        """
        root = self._scanner.get_collections_root()
        if not root:
            return None
        # Sanitize folder name — no path separators, collapse spaces.
        safe = ''.join(
            c if (c.isalnum() or c in '_-') else '_' for c in folder_name.strip()
        ) or 'filter_mate_collection'
        return os.path.join(root, safe)

    @staticmethod
    def _sanitize_bundle_filename(raw: str, default: str = "favorites") -> str:
        """Produce a safe bundle filename ending in .fmfav-pack.json.

        1. strip whitespace, fall back to ``default`` when empty;
        2. strip any recognised trailing extension the user may have
           typed (``.fmfav-pack.json`` / ``.fmfav.json`` / ``.json``);
        3. replace anything that isn't alnum / ``_`` / ``-`` with ``_``;
        4. re-append the canonical suffix.

        Order matters: we strip suffixes BEFORE sanitising so
        ``"my.bundle.fmfav-pack.json"`` becomes ``"my_bundle"`` then
        ``"my_bundle.fmfav-pack.json"`` — not a double-suffixed
        ``"my_bundle_fmfav-pack_json.fmfav-pack.json"``.
        """
        cleaned = (raw or '').strip()
        if not cleaned:
            cleaned = default
        for suffix in ('.fmfav-pack.json', '.fmfav.json', '.json'):
            if cleaned.lower().endswith(suffix):
                cleaned = cleaned[: -len(suffix)]
                break
        if not cleaned:
            cleaned = default
        safe = ''.join(
            c if (c.isalnum() or c in '_-') else '_' for c in cleaned
        )
        return f"{safe}.fmfav-pack.json"

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

        Args:
            favorites_service: Running :class:`FavoritesService` — used
                for its ``export_favorites`` path which guarantees v3
                canonical output (signatures stripped of UUIDs,
                display_name preserved, use_count reset).
            target: Target collection directory. ``is_new=True`` creates
                the directory tree on first write.
            bundle_filename: User-supplied name; sanitized with
                ``_sanitize_bundle_filename``.
            favorite_ids: Subset of the user's favorites to publish.
            collection_metadata: Free-form dict used both as the
                ``collection.json`` manifest and embedded inside the
                bundle envelope for provenance.
            overwrite: When False, refuses to overwrite an existing
                bundle at the target path. When True, replaces it.

        Returns:
            :class:`PublishResult` with paths and count on success, or
            ``error_message`` on failure. Never raises.
        """
        if not favorite_ids:
            return PublishResult(
                success=False,
                error_message="No favorites selected for publishing.",
            )
        if not target or not target.collection_dir:
            return PublishResult(
                success=False,
                error_message="No target collection provided.",
            )

        collection_dir = os.path.abspath(target.collection_dir)
        favorites_dir = os.path.join(collection_dir, 'filter_mate', 'favorites')

        try:
            os.makedirs(favorites_dir, exist_ok=True)
        except OSError as e:
            return PublishResult(
                success=False,
                error_message=f"Cannot create directory tree: {e}",
            )

        safe_name = self._sanitize_bundle_filename(bundle_filename)
        bundle_path = os.path.join(favorites_dir, safe_name)
        if os.path.exists(bundle_path) and not overwrite:
            return PublishResult(
                success=False,
                bundle_path=bundle_path,
                error_message=(
                    f"A bundle already exists at {bundle_path}. "
                    "Use overwrite=True to replace it."
                ),
            )

        # Sanitize metadata — only keep the whitelisted keys; drop anything
        # the caller may have inadvertently added so nothing sensitive leaks.
        allowed = {'name', 'author', 'license', 'description',
                   'tags', 'homepage', 'icon'}
        clean_metadata = {
            k: v for k, v in (collection_metadata or {}).items()
            if k in allowed
        }
        if not clean_metadata.get('name'):
            clean_metadata['name'] = target.display_name or os.path.basename(collection_dir)

        # Delegate to FavoritesService.export_favorites — it produces a
        # fully canonical v3 envelope (schema / schema_version / generator
        # / signature-keyed remote_layers / stripped UUIDs).
        export_fn = getattr(favorites_service, 'export_favorites', None)
        if not callable(export_fn):
            return PublishResult(
                success=False,
                error_message="FavoritesService does not expose export_favorites().",
            )
        owner_already_stripped = False
        try:
            result = export_fn(
                bundle_path,
                favorite_ids=list(favorite_ids),
                collection_metadata=clean_metadata,
                strip_owner=True,
            )
            owner_already_stripped = True
        except TypeError:
            # Older FavoritesService without ``collection_metadata``/
            # ``strip_owner`` kwargs — fall back to a two-step path: a
            # plain export, then patch the envelope and strip the owner
            # via the static helper below.
            try:
                result = export_fn(bundle_path, favorite_ids=list(favorite_ids))
                self._inject_collection_metadata(bundle_path, clean_metadata)
            except Exception as e:
                return PublishResult(
                    success=False,
                    bundle_path=bundle_path,
                    error_message=f"Export failed: {e}",
                )

        success = getattr(result, 'success', False)
        if not success:
            return PublishResult(
                success=False,
                bundle_path=bundle_path,
                error_message=getattr(
                    result, 'error_message', 'Unknown export failure'
                ),
            )

        # Owner is a local/team scope attribute — it identifies the author
        # inside a single DB and must never leak when a bundle crosses
        # organisation boundaries (fork, share via git, upload to QGIS
        # Resource Sharing index). The canonical export now does this in
        # the same pass; the legacy fallback path needs the post-rewrite.
        if not owner_already_stripped:
            self._strip_owner_from_bundle(bundle_path)

        # Write / refresh collection.json manifest
        manifest_path = os.path.join(collection_dir, 'collection.json')
        manifest_written = self._write_collection_manifest(
            manifest_path, clean_metadata,
        )

        # Invalidate cache so a subsequent scan picks up the new bundle
        self._scanner.invalidate_cache()

        logger.info(
            "Published %d favorite(s) to %s (collection: %s)",
            len(favorite_ids), bundle_path, clean_metadata.get('name'),
        )
        return PublishResult(
            success=True,
            bundle_path=bundle_path,
            collection_manifest_path=manifest_path if manifest_written else "",
            favorites_count=getattr(result, 'favorites_count', len(favorite_ids)),
        )

    @staticmethod
    def _strip_owner_from_bundle(bundle_path: str) -> None:
        """Remove the ``owner`` key from every favorite in a bundle file.

        Covers every plausible envelope shape:

        - ``{"favorites": [...]}`` (v3 canonical)
        - ``{"favorites": {id: {...}}}`` (dict-keyed variant)
        - top-level list (legacy single-file export)

        Best-effort: a malformed bundle is logged and left untouched so
        publishing never fails on a stripping concern alone.
        """
        try:
            with open(bundle_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            logger.debug("Cannot strip owner from %s: %s", bundle_path, exc)
            return

        def _strip_one(fav: Any) -> None:
            if isinstance(fav, dict) and 'owner' in fav:
                fav.pop('owner', None)

        if isinstance(data, dict):
            favorites = data.get('favorites')
            if isinstance(favorites, list):
                for fav in favorites:
                    _strip_one(fav)
            elif isinstance(favorites, dict):
                for fav in favorites.values():
                    _strip_one(fav)
        elif isinstance(data, list):
            for fav in data:
                _strip_one(fav)
        else:
            return  # Unknown envelope shape — leave as-is

        try:
            from .path_utils import atomic_json_write
            atomic_json_write(bundle_path, data)
        except OSError as exc:
            logger.warning("Could not rewrite bundle after owner strip: %s", exc)

    @staticmethod
    def _inject_collection_metadata(bundle_path: str, metadata: Dict[str, Any]) -> None:
        """Patch a bundle file in-place to add the ``collection`` block.

        Used only on the TypeError fallback path (older FavoritesService
        without the ``collection_metadata`` kwarg). Best-effort: swallows
        errors so publishing still succeeds even if the patch fails.
        """
        try:
            with open(bundle_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                data['collection'] = metadata
                from .path_utils import atomic_json_write
                atomic_json_write(bundle_path, data)
        except (OSError, ValueError) as e:
            logger.debug(f"Could not inject collection metadata into {bundle_path}: {e}")

    @staticmethod
    def _write_collection_manifest(
        manifest_path: str,
        metadata: Dict[str, Any],
    ) -> bool:
        """Write / merge a ``collection.json`` for Resource Sharing.

        When a manifest already exists its existing keys are preserved
        unless the caller is explicitly overriding them — this avoids
        clobbering fields the user may have set manually (``qgis_min``,
        ``qgis_max``, ``tags``, etc.) that we don't collect in our
        publish form.
        """
        try:
            existing: Dict[str, Any] = {}
            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        loaded = json.load(f)
                    if isinstance(loaded, dict):
                        existing = loaded
                except (OSError, ValueError):
                    existing = {}
            merged = dict(existing)
            # Caller-provided values win for the keys we control
            for k, v in (metadata or {}).items():
                if v is not None and v != "":
                    merged[k] = v
            from .path_utils import atomic_json_write
            atomic_json_write(manifest_path, merged)
            return True
        except OSError as e:
            logger.warning(f"Could not write {manifest_path}: {e}")
            return False

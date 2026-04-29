# -*- coding: utf-8 -*-
"""Writer-side of the favorites-sharing service: bundle production.

EXT-2 stage 3 (audit 2026-04-29): split out from
``FavoritesSharingService`` so the writer path (everything that
produces a Resource-Sharing collection bundle on disk) is isolated
from the read path (:class:`SharedFavoritesQuery`) and the
trust-boundary fork path (:class:`FavoritesForkService`).

Owns:
- target enumeration (``has_configured_collections_root``,
  ``list_publish_targets``, ``suggest_new_collection_dir``);
- filename sanitisation (``_sanitize_bundle_filename``);
- the two-phase publish itself (``publish_bundle``) with its
  fallback-mode helpers (``_strip_owner_from_bundle``,
  ``_inject_collection_metadata``, ``_write_collection_manifest``).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..scanner import ResourceSharingScanner

if TYPE_CHECKING:
    from ..service import CollectionTarget, PublishResult


logger = logging.getLogger('FilterMate.FavoritesSharing.BundlePublisher')


BUNDLE_FILENAME_RE = r'^[a-zA-Z0-9_\-]+\.fmfav(-pack)?\.json$'


class BundlePublisher:
    """Produce a v3 favorites bundle inside a Resource Sharing collection.

    Always returns a :class:`PublishResult` — never raises. The fork
    boundary is owned by :class:`FavoritesForkService`; the publish
    boundary is owned here.
    """

    def __init__(self, scanner: ResourceSharingScanner):
        self._scanner = scanner

    # ── Target enumeration --------------------------------------------

    def has_configured_collections_root(self) -> bool:
        """Whether a Resource Sharing collections root is configured.

        Lets UI flows surface the "New collection in root..." offer
        without having to reach into ``self._scanner`` directly (EXT-4).
        """
        return self._scanner.get_collections_root() is not None

    def list_publish_targets(self) -> List["CollectionTarget"]:
        """Enumerate directories under the Resource Sharing collections
        root that the user can publish into.

        Every existing sub-directory is considered a valid target; its
        current ``collection.json`` (if any) is loaded so the UI can
        pre-fill the metadata fields when publishing into it. When no
        Resource Sharing root exists yet we return an empty list — the
        caller is expected to ask the user for a custom directory.
        """
        from ..service import CollectionTarget  # avoid import cycle

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

    # ── Filename sanitiser --------------------------------------------

    @staticmethod
    def sanitize_bundle_filename(raw: str, default: str = "favorites") -> str:
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

    # ── Publish -------------------------------------------------------

    def publish_bundle(
        self,
        favorites_service: Any,
        target: "CollectionTarget",
        bundle_filename: str,
        favorite_ids: List[str],
        collection_metadata: Dict[str, Any],
        overwrite: bool = False,
    ) -> "PublishResult":
        """Write a v3 favorites bundle into a Resource Sharing collection.

        Args:
            favorites_service: Running :class:`FavoritesService` — used
                for its ``export_favorites`` path which guarantees v3
                canonical output (signatures stripped of UUIDs,
                display_name preserved, use_count reset).
            target: Target collection directory. ``is_new=True`` creates
                the directory tree on first write.
            bundle_filename: User-supplied name; sanitized with
                :meth:`sanitize_bundle_filename`.
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
        from ..service import PublishResult  # avoid import cycle

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

        safe_name = self.sanitize_bundle_filename(bundle_filename)
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

        clean_metadata = self._whitelist_metadata(
            collection_metadata, target, collection_dir,
        )

        result, owner_already_stripped = self._invoke_export(
            favorites_service, bundle_path, favorite_ids, clean_metadata,
        )
        if result is None:
            return PublishResult(
                success=False,
                bundle_path=bundle_path,
                error_message="FavoritesService does not expose export_favorites().",
            )
        if not getattr(result, 'success', False):
            return PublishResult(
                success=False,
                bundle_path=bundle_path,
                error_message=getattr(
                    result, 'error_message', 'Unknown export failure'
                ),
            )

        # Owner is a local/team scope attribute — it identifies the
        # author inside a single DB and must never leak when a bundle
        # crosses organisation boundaries (fork, share via git, upload
        # to QGIS Resource Sharing index). The canonical export now
        # does this in the same pass; the legacy fallback path needs
        # the post-rewrite.
        if not owner_already_stripped:
            self._strip_owner_from_bundle(bundle_path)

        # Write / refresh collection.json manifest.
        manifest_path = os.path.join(collection_dir, 'collection.json')
        manifest_written = self._write_collection_manifest(
            manifest_path, clean_metadata,
        )

        # Invalidate cache so a subsequent scan picks up the new bundle.
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

    # ── publish_bundle internals --------------------------------------

    def _whitelist_metadata(
        self,
        collection_metadata: Dict[str, Any],
        target: "CollectionTarget",
        collection_dir: str,
    ) -> Dict[str, Any]:
        """Sanitize metadata — only keep the whitelisted keys; drop
        anything the caller may have inadvertently added so nothing
        sensitive leaks. Falls back to the target display name when
        ``name`` is missing.
        """
        allowed = {'name', 'author', 'license', 'description',
                   'tags', 'homepage', 'icon'}
        clean = {
            k: v for k, v in (collection_metadata or {}).items()
            if k in allowed
        }
        if not clean.get('name'):
            clean['name'] = target.display_name or os.path.basename(collection_dir)
        return clean

    def _invoke_export(
        self,
        favorites_service: Any,
        bundle_path: str,
        favorite_ids: List[str],
        clean_metadata: Dict[str, Any],
    ):
        """Call ``favorites_service.export_favorites`` with the modern
        kwargs and fall back to the two-step legacy path on TypeError.

        Returns ``(result_or_none, owner_already_stripped)``. The first
        element is None when the service has no export_favorites().
        """
        export_fn = getattr(favorites_service, 'export_favorites', None)
        if not callable(export_fn):
            return None, False
        try:
            result = export_fn(
                bundle_path,
                favorite_ids=list(favorite_ids),
                collection_metadata=clean_metadata,
                strip_owner=True,
            )
            return result, True
        except TypeError:
            # Older FavoritesService without ``collection_metadata``/
            # ``strip_owner`` kwargs — fall back to a two-step path: a
            # plain export, then patch the envelope and strip the
            # owner via the static helper below.
            try:
                result = export_fn(bundle_path, favorite_ids=list(favorite_ids))
                self._inject_collection_metadata(bundle_path, clean_metadata)
                return result, False
            except Exception as e:
                logger.warning("Legacy export path failed: %s", e)
                return None, False

    @staticmethod
    def _strip_owner_from_bundle(bundle_path: str) -> None:
        """Remove the ``owner`` key from every favorite in a bundle file.

        Covers every plausible envelope shape:

        - ``{"favorites": [...]}`` (v3 canonical)
        - ``{"favorites": {id: {...}}}`` (dict-keyed variant)
        - top-level list (legacy single-file export)

        Best-effort: a malformed bundle is logged and left untouched
        so publishing never fails on a stripping concern alone.
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
            from ..path_utils import atomic_json_write
            atomic_json_write(bundle_path, data)
        except OSError as exc:
            logger.warning("Could not rewrite bundle after owner strip: %s", exc)

    @staticmethod
    def _inject_collection_metadata(
        bundle_path: str, metadata: Dict[str, Any],
    ) -> None:
        """Patch a bundle file in-place to add the ``collection`` block.

        Used only on the TypeError fallback path (older FavoritesService
        without the ``collection_metadata`` kwarg). Best-effort:
        swallows errors so publishing still succeeds even if the patch
        fails.
        """
        try:
            with open(bundle_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                data['collection'] = metadata
                from ..path_utils import atomic_json_write
                atomic_json_write(bundle_path, data)
        except (OSError, ValueError) as e:
            logger.debug(
                f"Could not inject collection metadata into {bundle_path}: {e}",
            )

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
            # Caller-provided values win for the keys we control.
            for k, v in (metadata or {}).items():
                if v is not None and v != "":
                    merged[k] = v
            from ..path_utils import atomic_json_write
            atomic_json_write(manifest_path, merged)
            return True
        except OSError as e:
            logger.warning(f"Could not write {manifest_path}: {e}")
            return False

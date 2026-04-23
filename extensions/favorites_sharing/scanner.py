# -*- coding: utf-8 -*-
"""
Resource Sharing scanner for favorites collections.

Walks the QGIS Resource Sharing directory tree and yields any JSON file
matching the FilterMate convention:

    {profile}/resource_sharing/collections/<any>/filter_mate/favorites/*.fmfav.json
    {profile}/resource_sharing/collections/<any>/filter_mate/favorites/*.fmfav-pack.json

The scanner is intentionally filesystem-only so it works whether or not
the ``resource_sharing`` QGIS plugin is installed — users can drop
collections manually under that path.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger('FilterMate.FavoritesSharing.Scanner')


@dataclass(frozen=True)
class SharedFavoriteSource:
    """Metadata about where a shared favorite came from."""
    file_path: str
    collection_name: str
    collection_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SharedFavorite:
    """A favorite loaded from a Resource Sharing bundle.

    The ``payload`` is the raw per-favorite dict straight out of the JSON
    (already canonical after ``FilterFavorite.from_dict`` normalization).
    ``source`` carries provenance for UI and Fork operations.
    """
    payload: Dict[str, Any]
    source: SharedFavoriteSource

    @property
    def name(self) -> str:
        return str(self.payload.get('name') or '(unnamed)')

    @property
    def description(self) -> str:
        return str(self.payload.get('description') or '')

    @property
    def schema_version(self) -> int:
        return int(self.payload.get('_schema_version') or 1)


class ResourceSharingScanner:
    """Enumerate favorites bundles installed under Resource Sharing.

    The scanner exposes two entry points:

    - :meth:`get_collections_root` — single directory where bundles live.
    - :meth:`scan` — walk the tree and return :class:`SharedFavorite`
      objects, each annotated with its source collection.

    Results are cached; call :meth:`invalidate_cache` to force a rescan
    (e.g. after a new subscription).
    """

    FAVORITE_FILE_SUFFIXES: Tuple[str, ...] = ('.fmfav.json', '.fmfav-pack.json')

    def __init__(self, collections_root: Optional[str] = None):
        self._explicit_root = collections_root
        self._cache: Optional[List[SharedFavorite]] = None

    # ─── Path discovery ────────────────────────────────────────────────

    def get_collections_root(self) -> Optional[str]:
        """Resolve the Resource Sharing collections directory.

        Resolution order (first hit wins):
        1. explicit ``collections_root`` passed to the constructor;
        2. ``EXTENSIONS.favorites_sharing.resource_sharing_root`` in
           FilterMate config — lets users override the auto-detected
           path (e.g., point at a shared network mount);
        3. ``QgsApplication.qgisSettingsDirPath()`` + ``/resource_sharing/collections``
           (matches the resource_sharing plugin convention);
        4. ``QGIS_CUSTOM_CONFIG_PATH`` / ``QGIS_AUTH_CUSTOM_CONFIG_PATH``
           environment overrides;
        5. Platform-specific fallbacks under ``~``.

        Returns ``None`` when nothing resolves to an existing directory.
        """
        if self._explicit_root and os.path.isdir(self._explicit_root):
            return self._explicit_root

        # Config override — users can point at a custom collections dir
        configured = self._read_configured_root()
        if configured and os.path.isdir(configured):
            return configured

        candidate_roots: List[str] = []
        try:
            from qgis.core import QgsApplication
            settings_dir = QgsApplication.qgisSettingsDirPath()
            if settings_dir:
                candidate_roots.append(os.path.join(
                    settings_dir, 'resource_sharing', 'collections',
                ))
        except Exception:
            pass

        # Environment override (set by some Resource Sharing setups)
        for env_key in ('QGIS_CUSTOM_CONFIG_PATH', 'QGIS_AUTH_CUSTOM_CONFIG_PATH'):
            raw = os.environ.get(env_key)
            if raw:
                candidate_roots.append(os.path.join(
                    raw, 'resource_sharing', 'collections',
                ))

        # Fallback: default profile path
        home = os.path.expanduser('~')
        candidate_roots.append(os.path.join(
            home, '.qgis3', 'resource_sharing', 'collections',
        ))
        candidate_roots.append(os.path.join(
            home, 'AppData', 'Roaming', 'QGIS', 'QGIS3',
            'profiles', 'default', 'resource_sharing', 'collections',
        ))

        for root in candidate_roots:
            if os.path.isdir(root):
                return root
        return None

    # ─── Scanning ──────────────────────────────────────────────────────

    def invalidate_cache(self) -> None:
        self._cache = None

    def scan(self, force_refresh: bool = False) -> List[SharedFavorite]:
        """Walk the collections tree and collect shared favorites.

        Args:
            force_refresh: Re-read the filesystem even if a cached list
                is available.

        Returns:
            List of :class:`SharedFavorite` — may be empty if no
            Resource Sharing directory exists or no collection carries
            FilterMate bundles.
        """
        if self._cache is not None and not force_refresh:
            return list(self._cache)

        root = self.get_collections_root()
        collected: List[SharedFavorite] = []
        if not root:
            logger.debug("Resource Sharing root not found — scan skipped")
            self._cache = []
            return []

        for collection_name, collection_dir in self._iter_collections(root):
            collection_meta = self._read_collection_metadata(collection_dir)
            favorites_dir = os.path.join(collection_dir, 'filter_mate', 'favorites')
            if not os.path.isdir(favorites_dir):
                continue

            for filename in sorted(os.listdir(favorites_dir)):
                lowered = filename.lower()
                if not any(lowered.endswith(suffix) for suffix in self.FAVORITE_FILE_SUFFIXES):
                    continue
                file_path = os.path.join(favorites_dir, filename)
                source = SharedFavoriteSource(
                    file_path=file_path,
                    collection_name=collection_name,
                    collection_metadata=collection_meta,
                )
                collected.extend(self._load_file(file_path, source))

        logger.info(
            "Resource Sharing scan: %d shared favorite(s) across %d file(s)",
            len(collected),
            len({f.source.file_path for f in collected}),
        )
        self._cache = list(collected)
        return collected

    # ─── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _read_configured_root() -> Optional[str]:
        """Read ``EXTENSIONS.favorites_sharing.resource_sharing_root``
        from FilterMate config, if set.
        """
        try:
            from filter_mate.config.config import ENV_VARS, _get_option_value
        except Exception:
            return None
        try:
            cfg = (ENV_VARS.get("CONFIG_DATA", {}) or {}) \
                .get("EXTENSIONS", {}) \
                .get("favorites_sharing", {})
            value = _get_option_value(cfg.get("resource_sharing_root"), default="")
            return str(value) if value else None
        except Exception:
            return None

    @staticmethod
    def _read_allowed_collections() -> List[str]:
        """Read the opt-in allow-list of collection basenames from config.

        Empty list means "allow everything" — mirrors the config default.
        """
        try:
            from filter_mate.config.config import ENV_VARS, _get_option_value
        except Exception:
            return []
        try:
            cfg = (ENV_VARS.get("CONFIG_DATA", {}) or {}) \
                .get("EXTENSIONS", {}) \
                .get("favorites_sharing", {})
            value = _get_option_value(cfg.get("allowed_collections"), default=[])
            if isinstance(value, list):
                return [str(v) for v in value if v]
        except Exception:
            pass
        return []

    @classmethod
    def _iter_collections(cls, root: str) -> Iterable[Tuple[str, str]]:
        try:
            entries = sorted(os.listdir(root))
        except OSError as e:
            logger.debug(f"Cannot list Resource Sharing root {root}: {e}")
            return []

        allowed = set(cls._read_allowed_collections())
        for name in entries:
            path = os.path.join(root, name)
            if not os.path.isdir(path) or name.startswith('.'):
                continue
            # Opt-in allow-list: when non-empty only accept whitelisted basenames.
            if allowed and name not in allowed:
                continue
            yield name, path

    @staticmethod
    def _read_collection_metadata(collection_dir: str) -> Dict[str, Any]:
        """Read ``collection.json`` (Resource Sharing manifest) when present.

        The Resource Sharing plugin itself uses INI-format metadata.txt but
        newer collections carry a JSON manifest. We accept either and fall
        back to an empty dict.
        """
        manifest = os.path.join(collection_dir, 'collection.json')
        if os.path.isfile(manifest):
            try:
                with open(manifest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except (ValueError, OSError) as e:
                logger.debug(f"Cannot read collection.json at {manifest}: {e}")

        return {}

    @staticmethod
    def _load_file(file_path: str, source: SharedFavoriteSource) -> List[SharedFavorite]:
        """Parse a .fmfav.json / .fmfav-pack.json file into SharedFavorite objects.

        Accepts both the envelope format (dict with ``favorites`` list,
        schema v1/v2/v3) and a bare favorite payload (dict without the
        envelope), for quick-share snippets.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (ValueError, OSError) as e:
            logger.warning(f"Shared favorite bundle unreadable: {file_path}: {e}")
            return []

        items: List[SharedFavorite] = []
        schema_version = 1

        if isinstance(data, dict) and 'favorites' in data:
            try:
                schema_version = int(data.get('schema_version') or 1)
            except (ValueError, TypeError):
                schema_version = 1
            payload_list = data.get('favorites') or []
            if not isinstance(payload_list, list):
                logger.warning(
                    f"Shared bundle {file_path}: 'favorites' is not a list — skipped"
                )
                return []
            # Merge collection metadata from file envelope into source
            file_collection = data.get('collection')
            if isinstance(file_collection, dict):
                merged = dict(source.collection_metadata)
                merged.update(file_collection)
                source = SharedFavoriteSource(
                    file_path=source.file_path,
                    collection_name=source.collection_name,
                    collection_metadata=merged,
                )
            for payload in payload_list:
                if not isinstance(payload, dict):
                    continue
                annotated = dict(payload)
                annotated['_schema_version'] = schema_version
                items.append(SharedFavorite(payload=annotated, source=source))
        elif isinstance(data, dict) and data.get('name'):
            # Bare favorite payload (snippet form)
            annotated = dict(data)
            annotated.setdefault('_schema_version', 1)
            items.append(SharedFavorite(payload=annotated, source=source))
        else:
            logger.debug(f"Shared bundle {file_path} has no favorites payload")

        return items

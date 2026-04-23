# -*- coding: utf-8 -*-
"""
FavoritesSharing Extension — BaseExtension entry point.

Discovers favorites JSON bundles published through the QGIS
``resource_sharing`` plugin, exposes them to FilterMate's Favorites Manager
dialog as a read-only "Shared" section, and provides a "Fork" action that
copies a shared favorite into the current project's DB.

Has **no required runtime dependency** on ``resource_sharing`` — absent
that plugin, the scanner still looks at the conventional profile path
(``{profile}/resource_sharing/collections``) and just returns an empty
list. Users can still install collections manually under that tree.
"""

import logging
from typing import Any, Dict, List, Optional

from qgis.PyQt.QtCore import QCoreApplication

from ..base import BaseExtension, ExtensionMetadata
from .remote_repo_manager import RemoteRepoManager
from .scanner import ResourceSharingScanner
from .service import FavoritesSharingService

logger = logging.getLogger('FilterMate.Extensions.FavoritesSharing')


class FavoritesSharingExtension(BaseExtension):
    """Favorites collections via QGIS Resource Sharing."""

    EXTENSION_ID = "favorites_sharing"
    EXTENSION_VERSION = "1.0.0"

    @staticmethod
    def tr(message: str) -> str:
        return QCoreApplication.translate('FavoritesSharingExtension', message)

    def __init__(self):
        super().__init__()
        self._iface = None
        self._scanner: Optional[ResourceSharingScanner] = None
        self._service: Optional[FavoritesSharingService] = None
        self._remote_repos: Optional[RemoteRepoManager] = None

    @property
    def metadata(self) -> ExtensionMetadata:
        return ExtensionMetadata(
            id=self.EXTENSION_ID,
            name="Favorites Sharing",
            version=self.EXTENSION_VERSION,
            description=(
                "Distribute and consume FilterMate favorite collections "
                "through the QGIS Resource Sharing plugin."
            ),
            author="FilterMate Team",
            min_qgis_version="3.28",
            dependencies=[],
            optional_dependencies=["resource_sharing"],
            icon_name="favorites_shared.png",
        )

    def config_schema(self) -> Dict[str, Dict[str, Any]]:
        """Declare user-facing options under ``EXTENSIONS.favorites_sharing``."""
        return {
            "resource_sharing_root": {
                "value": "",
                "description": (
                    "Absolute path to the Resource Sharing 'collections' "
                    "directory. Leave empty to auto-detect from QGIS profile. "
                    "Example: /home/user/.local/share/QGIS/QGIS3/profiles/"
                    "default/resource_sharing/collections"
                ),
            },
            "default_publish_collection": {
                "value": "",
                "description": (
                    "Absolute path (or sub-directory name under "
                    "resource_sharing_root) of the collection pre-selected "
                    "when publishing a bundle. Empty = first available."
                ),
            },
            "default_publish_metadata": {
                "value": {"author": "", "license": "", "homepage": ""},
                "description": (
                    "Default metadata pre-filled in the Publish dialog "
                    "(author, license, homepage). Saves re-typing across "
                    "publishes."
                ),
            },
            "allowed_collections": {
                "value": [],
                "description": (
                    "Opt-in allow-list of collection directory basenames. "
                    "When non-empty, only these collections are scanned. "
                    "Empty list = scan everything under resource_sharing_root."
                ),
            },
            "auto_refresh_on_project_load": {
                "value": True,
                "choices": [True, False],
                "description": (
                    "Re-scan Resource Sharing collections whenever a QGIS "
                    "project is loaded so signature resolution uses the "
                    "current project's layers."
                ),
            },
            "remote_repos": {
                "value": [],
                "description": (
                    "List of git-backed collection repos that can be "
                    "selected as publish targets. Each entry: "
                    "{name, git_url, branch, local_clone, "
                    "target_collection, is_default?, auth_header?}. "
                    "local_clone is resolved under the QGIS roaming "
                    "profile dir by default: an empty value maps to "
                    "[profile]/FilterMate/repos/<name>; a relative path "
                    "maps to [profile]/FilterMate/repos/<path>; absolute "
                    "or ~-prefixed paths are used verbatim (useful for "
                    "shared network mounts). Clones NEVER land inside "
                    "the plugin folder — they'd be wiped on plugin "
                    "updates. target_collection is the sub-directory "
                    "under collections/ where bundles are written. "
                    "When git_url is omitted and local_clone exists, "
                    "FilterMate writes the bundle locally and leaves the "
                    "push to the user (fallback A: SMB mount / external sync)."
                ),
            },
        }

    def check_dependencies(self) -> bool:
        """No hard dependencies — always available.

        The resource_sharing plugin is optional: when absent, we still
        scan the conventional ``~/.qgis/.../resource_sharing/collections``
        tree (users can populate it manually). When present, nothing
        changes — we just read the same directory.
        """
        return True

    def initialize(self, iface: Any) -> None:
        self._iface = iface
        self._scanner = ResourceSharingScanner(extension=self)
        self._service = FavoritesSharingService(self._scanner)
        self._remote_repos = RemoteRepoManager(extension=self)
        self.register_service('scanner', self._scanner)
        self.register_service('service', self._service)
        self.register_service('remote_repos', self._remote_repos)
        logger.info("FavoritesSharing extension initialized")

    # ------------------------------------------------------------------
    # Convenience typed accessors (keep call sites short & untyped-safe)
    # ------------------------------------------------------------------

    def get_resource_sharing_root(self) -> Optional[str]:
        value = self.get_config("resource_sharing_root", default="")
        return str(value) if value else None

    def get_allowed_collections(self) -> List[str]:
        value = self.get_config("allowed_collections", default=[])
        if isinstance(value, list):
            return [str(v) for v in value if v]
        return []

    def get_default_publish_collection(self) -> str:
        return str(self.get_config("default_publish_collection", default="") or "")

    def get_default_publish_metadata(self) -> Dict[str, str]:
        meta = self.get_config(
            "default_publish_metadata",
            default={"author": "", "license": "", "homepage": ""},
        )
        if not isinstance(meta, dict):
            meta = {}
        return {
            "author": str(meta.get("author") or ""),
            "license": str(meta.get("license") or ""),
            "homepage": str(meta.get("homepage") or ""),
        }

    def is_auto_refresh_enabled(self) -> bool:
        return bool(self.get_config("auto_refresh_on_project_load", default=True))

    def get_remote_repos(self) -> List[Dict[str, Any]]:
        """Return the configured remote repos (never None, never malformed).

        Entries with no ``name`` are dropped; unknown fields are preserved
        for forward compatibility.
        """
        raw = self.get_config("remote_repos", default=[])
        if not isinstance(raw, list):
            return []
        repos: List[Dict[str, Any]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            repos.append(entry)
        return repos

    def create_ui(self, toolbar: Any, menu_name: str) -> List[Any]:
        """No toolbar button — UI is injected into the Favorites Manager
        dialog via the service when the dialog opens.
        """
        return []

    def teardown(self) -> None:
        self._scanner = None
        self._service = None
        self._remote_repos = None
        self._iface = None

    def on_project_loaded(self) -> None:
        """Re-scan so a newly-loaded project's layers can resolve shared
        favorites' signatures — unless the user has opted out via
        ``auto_refresh_on_project_load``.
        """
        if self._service is None or not self.is_auto_refresh_enabled():
            return
        try:
            self._service.invalidate_cache()
        except Exception as e:
            logger.debug(f"Scanner cache invalidation skipped: {e}")

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


# Lazy availability flag — set on first check_dependencies() call.
# Mirrors the qfieldcloud pattern so both extensions gate activation
# on the presence of their companion QGIS plugin, visibly in the
# Configuration panel under EXTENSIONS.<ext_id>.enabled.
_RESOURCE_SHARING_AVAILABLE: Optional[bool] = None

# The QGIS plugin is published under two package names depending on the
# source: the official repo installs it as ``qgis_resource_sharing``; some
# forks / zip installs keep the historical ``resource_sharing`` name. Probe
# both so FilterMate works with either.
_RESOURCE_SHARING_PLUGIN_NAMES = ('qgis_resource_sharing', 'resource_sharing')


def _check_resource_sharing_available() -> bool:
    """True when a QGIS Resource Sharing plugin is installed.

    Detection order:
      1. ``qgis.utils.plugins[<name>]`` for each candidate — the
         authoritative registry, populated only when the plugin is
         *loaded* by QGIS.
      2. ``import <name>`` — catches installed-but-not-loaded cases
         (plugin present on disk but disabled in the plugin manager).
         FilterMate still accepts that state so users can simply enable
         the plugin without restarting.
    """
    global _RESOURCE_SHARING_AVAILABLE
    if _RESOURCE_SHARING_AVAILABLE is not None:
        return _RESOURCE_SHARING_AVAILABLE

    try:
        from qgis.utils import plugins as _qgis_plugins  # type: ignore
        for name in _RESOURCE_SHARING_PLUGIN_NAMES:
            if name in _qgis_plugins:
                _RESOURCE_SHARING_AVAILABLE = True
                return True
    except ImportError:
        pass

    import importlib
    for name in _RESOURCE_SHARING_PLUGIN_NAMES:
        try:
            importlib.import_module(name)
            _RESOURCE_SHARING_AVAILABLE = True
            return True
        except ImportError:
            continue

    _RESOURCE_SHARING_AVAILABLE = False
    return False


def reset_resource_sharing_cache() -> None:
    """Clear the availability cache (used by tests + after plugin toggle)."""
    global _RESOURCE_SHARING_AVAILABLE
    _RESOURCE_SHARING_AVAILABLE = None


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
            # Hard dep on the Resource Sharing plugin: without it, there's
            # no canonical collections/ tree to scan and publishing has
            # nowhere to target. The extension still seeds its config so
            # it shows up in the panel (greyed/disabled) until the user
            # installs the companion plugin — same UX as qfieldcloud.
            dependencies=["resource_sharing"],
            optional_dependencies=[],
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
                    "target_collection, is_default?, authcfg_id?, "
                    "auth_header?}. local_clone is resolved under the "
                    "QGIS roaming profile dir by default: an empty value "
                    "maps to [profile]/FilterMate/repos/<name>; a "
                    "relative path maps to [profile]/FilterMate/repos/"
                    "<path>; absolute or ~-prefixed paths are used "
                    "verbatim (useful for shared network mounts). Clones "
                    "NEVER land inside the plugin folder — they'd be "
                    "wiped on plugin updates. target_collection is the "
                    "sub-directory under collections/ where bundles are "
                    "written. When git_url is omitted and local_clone "
                    "exists, FilterMate writes the bundle locally and "
                    "leaves the push to the user (fallback A: SMB mount "
                    "/ external sync). authcfg_id references a QGIS Auth "
                    "Manager entry — preferred over auth_header (which "
                    "stores the token in plain text and is deprecated). "
                    "Use the 'Manage Repos…' dialog to create entries."
                ),
            },
            "git_binary_path": {
                "value": "",
                "description": (
                    "Absolute path to the git executable. Empty = "
                    "auto-detect via the resolver chain: "
                    "explicit config → bundled portable Git "
                    "([profile]/FilterMate/tools/PortableGit) → "
                    "system PATH. Useful on locked-down Windows "
                    "where Git for Windows cannot be installed "
                    "system-wide — the Manage Repos dialog can "
                    "download a portable copy on demand."
                ),
            },
        }

    def missing_deps_hint(self) -> Dict[str, str]:
        """Resource Sharing is a QGIS plugin — not a pip package."""
        return {
            "method": "qgis_plugin",
            "install_command": (
                "Extensions → Installer/Gérer les extensions → "
                "Chercher « Resource Sharing » → Installer"
            ),
            "details": (
                "Le plugin officiel est disponible dans le dépôt QGIS "
                "standard (packages: qgis_resource_sharing ou "
                "resource_sharing). Aucun pip install requis."
            ),
        }

    def check_dependencies(self) -> bool:
        """Gate activation on the QGIS ``resource_sharing`` plugin.

        FIX 2026-04-23: previously always True, which meant the extension
        reported "ready" even when the Resource Sharing plugin wasn't
        installed — at which point every publish/fork action would fail
        with a confusing "collections root not found" error. Aligning
        with the qfieldcloud pattern: the extension config still seeds
        (so it's visible under EXTENSIONS in the Configuration panel),
        but the extension is flagged as ``MISSING_DEPS`` until the user
        installs the companion plugin.
        """
        return _check_resource_sharing_available()

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

    # ------------------------------------------------------------------
    # F5 menu contribution — favorites context menu
    # ------------------------------------------------------------------

    def get_menu_actions(self, context: Any) -> List[Any]:
        """Contribute the Resource Sharing entries to the favorites menu.

        Implementation of the ``MenuActionsProvider`` protocol declared
        in :mod:`ui.controllers.favorites_menu_builder`. The bridge
        passes itself as ``context`` (read-only handle exposing
        ``favorite_count``, ``has_default_repo`` and ``tr``); this
        method returns ``MenuActionSpec`` instances describing what
        should appear, in order. The bridge writes them to QActions and
        the controller dispatches them by sentinel.

        Done here (not in the bridge) so the Resource Sharing UX —
        which entries exist, which icons, which gating conditions — is
        owned by the same module that owns the extension.
        """
        # Imported inline so the extension module stays loadable even if
        # the UI controllers package isn't on sys.path (e.g. headless
        # tests instantiating the extension in isolation).
        from ...ui.controllers.favorites_menu_builder import (
            ACTION_MANAGE_SHARING_REPOS,
            ACTION_PUBLISH_SHARING,
            ACTION_QUICK_PUBLISH_SHARING,
            ACTION_SHARED_PICKER,
            MenuActionSpec,
        )

        tr = context.tr
        actions: List[Any] = [
            MenuActionSpec(
                sentinel=ACTION_SHARED_PICKER,
                label="\U0001F4E1 " + tr("Import from Resource Sharing..."),
            ),
        ]

        publish_enabled = context.favorite_count > 0
        actions.append(MenuActionSpec(
            sentinel=ACTION_PUBLISH_SHARING,
            label="\U0001F4E4 " + tr("Publish to Resource Sharing..."),
            enabled=publish_enabled,
            disabled_label="\U0001F4E4 " + tr("Publish (no favorites saved)"),
        ))

        # Quick-publish only surfaces when both pre-conditions are met.
        # Hiding (rather than disabling) because there's no useful
        # affordance to communicate "configure a default repo" from this
        # menu entry — we'd just be teaching the user about a feature
        # they can't use yet.
        if publish_enabled and context.has_default_repo():
            actions.append(MenuActionSpec(
                sentinel=ACTION_QUICK_PUBLISH_SHARING,
                label="\U0001F680 " + tr("Quick publish to default repo"),
            ))

        actions.append(MenuActionSpec(
            sentinel=ACTION_MANAGE_SHARING_REPOS,
            label="\U0001F310 " + tr("Manage Resource Sharing repos..."),
        ))

        return actions

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

    def get_git_binary_path(self) -> str:
        """Explicit user-configured git binary, or empty string for auto."""
        return str(self.get_config("git_binary_path", default="") or "").strip()

    def set_git_binary_path(self, path: str) -> bool:
        """Persist a user-configured git binary path (or clear with empty)."""
        return bool(self.set_config("git_binary_path", (path or "").strip()))

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

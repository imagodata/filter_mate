# -*- coding: utf-8 -*-
"""Single coupling point between FavoritesController and the favorites_sharing extension.

The controller used to host seven inline methods (~240 lines) for
extension lookup, capability checks, dialog launching and the quick
publish flow. They were the loudest hint that the controller had grown
into a god class — and they tied the controller directly to the
extension's UI module imports, blocking the F5 registry pattern.

The bridge consolidates them in one place. Eventually F5 will let the
extension register its own actions; until then, the bridge is the
single file we touch when the extension API evolves.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, List, Optional

from .favorites_menu_builder import MenuActionSpec

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .favorites_controller import FavoritesController


class FavoritesExtensionBridge:
    """Proxy methods used by FavoritesController to talk to ``favorites_sharing``.

    Owns:
      - extension/service lookup (registry indirection)
      - capability checks (active, has default repo)
      - dialog launchers (shared picker, publish, repo manager)
      - the quick-publish 1-click flow

    Reads back into the controller for UI helpers (``tr``,
    ``_show_warning``, ``_show_success``, ``dockwidget``, ``count``,
    ``_favorites_manager``, ``favorites_changed`` signal,
    ``update_indicator``). The dependency direction stays
    controller → bridge → extension; the bridge never imports controller
    types except for type-checking.
    """

    def __init__(self, controller: "FavoritesController") -> None:
        self._controller = controller

    # ── Lookup / capability ──────────────────────────────────────────

    def get_extension(self) -> Optional[Any]:
        """Return the favorites_sharing extension instance if loaded."""
        try:
            from ...extensions.registry import get_extension_registry
        except ImportError:
            return None
        try:
            return get_extension_registry().get_extension('favorites_sharing')
        except Exception:
            return None

    def is_active(self) -> bool:
        """True when the extension is loaded AND in a usable state."""
        ext = self.get_extension()
        if ext is None:
            return False
        try:
            from ...extensions.base import ExtensionState
            return ext.state in (ExtensionState.INITIALIZED, ExtensionState.UI_CREATED)
        except Exception:
            return False

    def has_default_repo(self) -> bool:
        """True when a default git-backed publish target is configured."""
        ext = self.get_extension()
        if ext is None:
            return False
        try:
            mgr = ext.get_service('remote_repos')
            return mgr is not None and mgr.get_default() is not None
        except Exception:
            return False

    # ── Menu contribution (F5 minimal) ───────────────────────────────

    def get_menu_actions(self) -> List[MenuActionSpec]:
        """Return the favorites-menu entries contributed by the extension.

        F5 stage 2: the bridge is now a pure relay. The extension owns
        its menu shape via its own ``get_menu_actions`` method (duck-
        typed, see :class:`MenuActionsProvider`); the bridge passes
        itself as the :class:`MenuActionsContext` and returns whatever
        the provider produces. If the extension is missing or doesn't
        implement the contract, no entries are rendered.
        """
        ext = self.get_extension()
        if ext is None:
            return []
        provider = getattr(ext, "get_menu_actions", None)
        if not callable(provider):
            return []
        try:
            return list(provider(self))
        except Exception:
            logger.exception("favorites_sharing.get_menu_actions failed; rendering empty section")
            return []

    # ── MenuActionsContext implementation ────────────────────────────
    #
    # Implemented implicitly via duck typing — the extension calls these
    # back from inside ``get_menu_actions`` to gate entries. Keeping them
    # on the bridge (rather than exposing the controller directly) lets
    # the bridge remain the only seam between the controller's internals
    # and any future menu provider.

    @property
    def favorite_count(self) -> int:
        """Current favorite count, used by providers to gate entries."""
        return self._controller.count

    def tr(self, message: str) -> str:
        """Translate via the controller's Qt translation bag."""
        return self._controller.tr(message)

    # ── Dialog launchers ─────────────────────────────────────────────

    def open_shared_picker(self, *, parent: Optional[Any] = None) -> None:
        """Open the Resource Sharing picker dialog when the extension is active.

        ``parent`` defaults to the controller's dockwidget. Callers that
        already have a dialog open (``FavoritesManagerDialog``) pass
        ``parent=self`` so the picker is modal to the manager rather than
        to the dockwidget.
        """
        ctrl = self._controller
        ext = self.get_extension()
        if ext is None or ctrl._favorites_manager is None:
            ctrl._show_warning(ctrl.tr(
                "Resource Sharing extension is not active. "
                "Enable 'favorites_sharing' in FilterMate settings."
            ))
            return

        service = ext.get_service('service')
        if service is None:
            ctrl._show_warning(ctrl.tr("Shared favorites service is not available."))
            return

        try:
            from ...extensions.favorites_sharing.ui import SharedFavoritesPickerDialog
            dialog = SharedFavoritesPickerDialog(
                service,
                ctrl._favorites_manager,
                parent=parent if parent is not None else ctrl.dockwidget,
            )
            dialog.exec()
            ctrl.update_indicator()
            ctrl.favorites_changed.emit()
        except Exception as e:
            logger.exception("Shared picker failed to open")
            ctrl._show_warning(ctrl.tr("Shared picker failed: {0}").format(e))

    def open_publish_dialog(
        self,
        *,
        parent: Optional[Any] = None,
        preselected_ids: Optional[List[str]] = None,
    ) -> None:
        """Open the PublishFavoritesDialog when the extension is active.

        ``parent`` defaults to the controller's dockwidget. ``preselected_ids``
        lets callers (e.g. the manager dialog) bias the dialog towards the
        currently selected favorite — the dialog's checklist still allows
        the user to toggle other favorites on/off.
        """
        ctrl = self._controller
        ext = self.get_extension()
        if ext is None or ctrl._favorites_manager is None:
            ctrl._show_warning(ctrl.tr(
                "Resource Sharing extension is not active. "
                "Enable 'favorites_sharing' in FilterMate settings."
            ))
            return

        service = ext.get_service('service')
        if service is None:
            ctrl._show_warning(ctrl.tr("Shared favorites service is not available."))
            return

        if ctrl.count == 0:
            ctrl._show_warning(ctrl.tr(
                "You have no favorites to publish yet. Save a filter via "
                "the ★ menu first."
            ))
            return

        try:
            from ...extensions.favorites_sharing.ui import PublishFavoritesDialog
            kwargs: dict = {
                "parent": parent if parent is not None else ctrl.dockwidget,
            }
            if preselected_ids:
                kwargs["preselected_ids"] = list(preselected_ids)
            dialog = PublishFavoritesDialog(
                service,
                ctrl._favorites_manager,
                **kwargs,
            )
            dialog.exec()
        except Exception as e:
            logger.exception("Publish dialog failed to open")
            ctrl._show_warning(ctrl.tr("Publish dialog failed: {0}").format(e))

    def open_repo_manager_dialog(self) -> None:
        """Open the Repo Manager (CRUD on the configured remote repos)."""
        ctrl = self._controller
        ext = self.get_extension()
        if ext is None:
            ctrl._show_warning(ctrl.tr(
                "Resource Sharing extension is not active. "
                "Enable 'favorites_sharing' in FilterMate settings."
            ))
            return
        mgr = ext.get_service('remote_repos')
        if mgr is None:
            ctrl._show_warning(ctrl.tr("Remote repo manager is not available."))
            return
        try:
            from ...extensions.favorites_sharing.ui import RepoManagerDialog
            dialog = RepoManagerDialog(mgr, parent=ctrl.dockwidget)
            dialog.exec()
        except Exception as e:
            logger.exception("Repo manager dialog failed to open")
            ctrl._show_warning(ctrl.tr("Repo manager failed: {0}").format(e))

    # ── Quick publish flow ───────────────────────────────────────────

    def quick_publish_to_default_repo(self) -> None:
        """Publish ALL favorites to the configured default repo without
        opening the full Publish dialog. Confirms once, then runs the
        clone → write → commit → push pipeline.
        """
        ctrl = self._controller
        ext = self.get_extension()
        if ext is None or ctrl._favorites_manager is None:
            ctrl._show_warning(ctrl.tr(
                "Resource Sharing extension is not active."
            ))
            return
        service = ext.get_service('service')
        mgr = ext.get_service('remote_repos')
        if service is None or mgr is None:
            ctrl._show_warning(ctrl.tr(
                "Resource Sharing services are not available."
            ))
            return
        repo = mgr.get_default()
        if repo is None:
            ctrl._show_warning(ctrl.tr(
                "No default repo is configured. Open 'Manage Resource "
                "Sharing repos…' to add one and mark it as default."
            ))
            return
        if ctrl.count == 0:
            ctrl._show_warning(ctrl.tr(
                "No favorites to publish."
            ))
            return

        try:
            from qgis.PyQt.QtWidgets import QApplication, QMessageBox
            from qgis.PyQt.QtCore import Qt
        except ImportError:
            return

        try:
            favorites = ctrl._favorites_manager.get_all_favorites()
        except Exception:
            favorites = []
        # F11 policy: stays a modal QMessageBox.question. Quick-publish
        # writes a signed bundle to a remote git repo + pushes it; user
        # must consciously decide before we touch the remote.
        confirm = QMessageBox.question(
            ctrl.dockwidget,
            ctrl.tr("Quick publish"),
            ctrl.tr(
                "Publish {0} favorite(s) to <b>{1}</b>?<br><br>"
                "<small>Target: <code>{2}</code></small>"
            ).format(
                len(favorites), repo.name,
                repo.collection_dir or repo.expanded_local_clone or "(default)",
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        from ...extensions.favorites_sharing.service import CollectionTarget

        bundle_name = "favorites"
        metadata = ext.get_default_publish_metadata() if hasattr(
            ext, 'get_default_publish_metadata'
        ) else {}
        metadata = dict(metadata)
        metadata.setdefault("name", repo.target_collection or repo.name)

        fav_ids = [getattr(f, 'id', '') for f in favorites if getattr(f, 'id', '')]

        def _write_bundle(collection_dir: str) -> str:
            result = service.publish_bundle(
                favorites_service=ctrl._favorites_manager,
                target=CollectionTarget(
                    collection_dir=collection_dir,
                    display_name=metadata.get('name') or repo.name,
                    is_new=not os.path.isdir(collection_dir),
                ),
                bundle_filename=bundle_name,
                favorite_ids=fav_ids,
                collection_metadata=metadata,
                overwrite=True,
            )
            if not result.success:
                raise RuntimeError(result.error_message or "bundle write failed")
            return result.bundle_path

        author = (metadata.get('author') or '').strip()
        commit_author = f"{author} <filter_mate@imagodata.local>" if author else None

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            sync = mgr.publish_to_remote(repo, _write_bundle, commit_author=commit_author)
        finally:
            QApplication.restoreOverrideCursor()

        if not sync.success:
            ctrl._show_warning(ctrl.tr(
                "Quick publish to {0} failed: {1}"
            ).format(repo.name, sync.error_message or "?"))
            return

        if sync.pushed:
            ctrl._show_success(ctrl.tr(
                "Published {0} favorite(s) to {1} (commit {2})."
            ).format(len(favorites), repo.name, sync.commit_sha or "?"))
        elif sync.skipped_push_reason == "no_changes":
            ctrl._show_success(ctrl.tr(
                "Bundle unchanged — nothing to commit."
            ))
        elif sync.skipped_push_reason == "no_remote":
            ctrl._show_success(ctrl.tr(
                "Wrote bundle locally — push manually."
            ))

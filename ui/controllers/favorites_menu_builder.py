# -*- coding: utf-8 -*-
"""Favorites context menu construction, factored out of FavoritesController.

The menu is large (~140 lines, 5 sections + 2 sub-menus) and stateless.
Splitting it into ``FavoritesMenuBuilder`` lets the controller stay
focused on lifecycle and dispatch, and lets the action sentinels be
single-sourced — the builder writes them, ``_handle_menu_action`` reads
the same names back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    from qgis.PyQt.QtWidgets import QMenu, QWidget
    HAS_QT = True
except ImportError:  # pragma: no cover
    HAS_QT = False
    QMenu = object  # type: ignore[misc,assignment]
    QWidget = object  # type: ignore[misc,assignment]

from ..styles.favorites_styles import FAVORITES_MENU_STYLESHEET

if TYPE_CHECKING:
    from .favorites_controller import FavoritesController


# ── Action sentinels ────────────────────────────────────────────────
# Single source of truth: the builder writes these to ``QAction.setData``,
# the controller reads them back in ``_handle_menu_action``. A typo
# anywhere shows up immediately because the constant is referenced from
# both sides.

ACTION_ADD_FAVORITE = "__ADD_FAVORITE__"
ACTION_MANAGE = "__MANAGE__"
ACTION_EXPORT = "__EXPORT__"
ACTION_IMPORT = "__IMPORT__"
ACTION_SHOW_ALL = "__SHOW_ALL__"
ACTION_SHOW_GLOBAL = "__SHOW_GLOBAL__"
ACTION_SHARED_PICKER = "__SHARED_PICKER__"
ACTION_PUBLISH_SHARING = "__PUBLISH_SHARING__"
ACTION_QUICK_PUBLISH_SHARING = "__QUICK_PUBLISH_SHARING__"
ACTION_MANAGE_SHARING_REPOS = "__MANAGE_SHARING_REPOS__"
ACTION_BACKUP_TO_PROJECT = "__BACKUP_TO_PROJECT__"
ACTION_RESTORE_FROM_PROJECT = "__RESTORE_FROM_PROJECT__"
ACTION_CLEANUP_ORPHANS = "__CLEANUP_ORPHANS__"
ACTION_SHOW_STATS = "__SHOW_STATS__"

# Tuple sentinels (action_name, favorite_id)
ACTION_APPLY = "apply"
ACTION_APPLY_GLOBAL = "apply_global"
ACTION_COPY_TO_GLOBAL = "copy_to_global"


class FavoritesMenuBuilder:
    """Construct the favorites QMenu from a controller's state.

    All methods are static — the builder owns no state, it just reads
    from the controller it's given. Each section is its own helper so a
    future split (e.g. moving the sharing actions to the extension via
    a registry pattern, F5) can replace one method without touching the
    rest.
    """

    @staticmethod
    def build(controller: "FavoritesController", parent: Any) -> QMenu:
        """Return a fully populated QMenu, ready to ``exec_()``."""
        menu = QMenu(parent)
        menu.setStyleSheet(FAVORITES_MENU_STYLESHEET)

        favorites = controller.get_all_favorites()
        FavoritesMenuBuilder._add_quick_filter_section(menu, favorites, controller)
        FavoritesMenuBuilder._add_create_section(menu, controller)
        FavoritesMenuBuilder._add_management_section(menu, controller)
        if controller._is_sharing_extension_active():
            FavoritesMenuBuilder._add_sharing_section(menu, controller)
        FavoritesMenuBuilder._add_global_submenu(menu, favorites, controller)
        FavoritesMenuBuilder._add_maintenance_submenu(menu, controller)
        return menu

    # ── Section helpers ──────────────────────────────────────────────

    @staticmethod
    def _add_quick_filter_section(menu: QMenu, favorites: list, controller: "FavoritesController") -> None:
        """Top-of-menu shortcut to apply one of the most-used favorites."""
        if not favorites:
            return

        header = menu.addAction(f"⚡ Filtrage Rapide ({len(favorites)})")
        header.setEnabled(False)
        font = header.font()
        font.setBold(True)
        header.setFont(font)

        # Most used first, then alphabetical for ties.
        sorted_favs = sorted(favorites, key=lambda f: (-f.use_count, f.name.lower()))
        display_favs = sorted_favs[:8]

        for fav in display_favs:
            layers_count = fav.get_layers_count() if hasattr(fav, "get_layers_count") else 1
            fav_text = f"★ {fav.get_display_name(30)}"
            if layers_count > 1:
                fav_text += f" [{layers_count}]"

            action = menu.addAction(fav_text)
            action.setData((ACTION_APPLY, fav.id))
            tooltip = f"{fav.name}\n{fav.get_preview(100)}"
            if fav.use_count > 0:
                tooltip += "\n" + controller.tr("Used {0} times").format(fav.use_count)
            action.setToolTip(tooltip)

        if len(favorites) > 8:
            more_action = menu.addAction(f"  ➤ Voir tous ({len(favorites)})...")
            more_action.setData(ACTION_SHOW_ALL)

        menu.addSeparator()

    @staticmethod
    def _add_create_section(menu: QMenu, controller: "FavoritesController") -> None:
        """Single 'Add current filter to favorites' entry, disabled when
        there's no active filter to capture."""
        current_expression = controller.get_current_filter_expression()
        add_action = menu.addAction("⭐ " + controller.tr("Add current filter to favorites"))
        add_action.setData(ACTION_ADD_FAVORITE)
        if not current_expression:
            add_action.setEnabled(False)
            add_action.setText("⭐ " + controller.tr("Add filter (no active filter)"))
        menu.addSeparator()

    @staticmethod
    def _add_management_section(menu: QMenu, controller: "FavoritesController") -> None:
        """Manage / Export / Import — the always-on management triplet."""
        manage_action = menu.addAction("⚙️ " + controller.tr("Manage favorites..."))
        manage_action.setData(ACTION_MANAGE)

        export_action = menu.addAction("📤 " + controller.tr("Export..."))
        export_action.setData(ACTION_EXPORT)

        import_action = menu.addAction("📥 " + controller.tr("Import..."))
        import_action.setData(ACTION_IMPORT)

    @staticmethod
    def _add_sharing_section(menu: QMenu, controller: "FavoritesController") -> None:
        """Resource Sharing actions — only when the extension is active.

        Hidden entirely when ``favorites_sharing`` is not registered. The
        intent is the prelude to F5 (registry pattern): once the extension
        owns its menu actions, this method becomes a single delegation.
        """
        shared_action = menu.addAction("📡 " + controller.tr("Import from Resource Sharing..."))
        shared_action.setData(ACTION_SHARED_PICKER)

        publish_action = menu.addAction("📤 " + controller.tr("Publish to Resource Sharing..."))
        publish_action.setData(ACTION_PUBLISH_SHARING)
        if controller.count == 0:
            publish_action.setEnabled(False)
            publish_action.setText("📤 " + controller.tr("Publish (no favorites saved)"))

        # 1-click flow that bypasses the dialog and pushes ALL favorites
        # to the configured default repo. Hidden when no default is set
        # (no point in failing silently from the menu).
        if controller.count > 0 and controller._has_default_remote_repo():
            quick_action = menu.addAction("🚀 " + controller.tr("Quick publish to default repo"))
            quick_action.setData(ACTION_QUICK_PUBLISH_SHARING)

        manage_repos_action = menu.addAction(
            "🌐 " + controller.tr("Manage Resource Sharing repos...")
        )
        manage_repos_action.setData(ACTION_MANAGE_SHARING_REPOS)

    @staticmethod
    def _add_global_submenu(menu: QMenu, favorites: list, controller: "FavoritesController") -> None:
        """Sub-menu collecting the global-favorite operations."""
        menu.addSeparator()
        global_menu = menu.addMenu("🌐 " + controller.tr("Global favorites"))

        if favorites:
            copy_global_menu = global_menu.addMenu(controller.tr("Copy to global..."))
            for fav in favorites[:5]:
                action = copy_global_menu.addAction(f"  {fav.name}")
                action.setData((ACTION_COPY_TO_GLOBAL, fav.id))
            if len(favorites) > 5:
                copy_global_menu.addAction("  ...").setEnabled(False)

        global_favorites = controller._get_global_favorites()
        if global_favorites:
            global_menu.addSeparator()
            global_menu.addAction(controller.tr("── Available global favorites ──")).setEnabled(False)
            for gfav in global_favorites[:5]:
                action = global_menu.addAction(f"  📌 {gfav.name}")
                action.setData((ACTION_APPLY_GLOBAL, gfav.id))
            if len(global_favorites) > 5:
                more_action = global_menu.addAction(
                    f"  ➤ Voir tous ({len(global_favorites)})..."
                )
                more_action.setData(ACTION_SHOW_GLOBAL)
        else:
            global_menu.addAction(controller.tr("(No global favorites)")).setEnabled(False)

    @staticmethod
    def _add_maintenance_submenu(menu: QMenu, controller: "FavoritesController") -> None:
        """Backup / restore / cleanup / stats operations under one sub-menu."""
        menu.addSeparator()
        maintenance_menu = menu.addMenu("🔧 " + controller.tr("Maintenance"))

        backup_action = maintenance_menu.addAction("💾 " + controller.tr("Save to project (.qgz)"))
        backup_action.setData(ACTION_BACKUP_TO_PROJECT)

        restore_action = maintenance_menu.addAction("📂 " + controller.tr("Restore from project"))
        restore_action.setData(ACTION_RESTORE_FROM_PROJECT)

        maintenance_menu.addSeparator()

        cleanup_action = maintenance_menu.addAction("🧹 " + controller.tr("Clean up orphan projects"))
        cleanup_action.setData(ACTION_CLEANUP_ORPHANS)

        stats_action = maintenance_menu.addAction("📊 " + controller.tr("Database statistics"))
        stats_action.setData(ACTION_SHOW_STATS)

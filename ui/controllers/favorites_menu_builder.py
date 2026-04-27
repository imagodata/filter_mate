# -*- coding: utf-8 -*-
"""Favorites context menu construction, factored out of FavoritesController.

The menu is large (~140 lines, 5 sections + 2 sub-menus) and stateless.
Splitting it into ``FavoritesMenuBuilder`` lets the controller stay
focused on lifecycle and dispatch, and lets the action sentinels be
single-sourced — the builder writes them, ``_handle_menu_action`` reads
the same names back.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, List

try:
    from qgis.PyQt.QtWidgets import QMenu, QWidget
    HAS_QT = True
except ImportError:  # pragma: no cover
    HAS_QT = False
    QMenu = object  # type: ignore[misc,assignment]
    QWidget = object  # type: ignore[misc,assignment]

from ..styles.favorites_styles import FAVORITES_MENU_STYLESHEET


@dataclass(frozen=True)
class MenuActionSpec:
    """Declarative description of one entry in a contributed menu section.

    Used by :class:`FavoritesExtensionBridge` (and, eventually, any
    future extension that registers favorites menu items via F5) to
    declare what should appear without learning the QMenu API.
    """

    sentinel: str
    """Action data string written via ``QAction.setData`` and dispatched
    by ``FavoritesController._handle_menu_action``."""

    label: str
    """Final user-visible label, already translated and icon-prefixed."""

    enabled: bool = True
    """Disabled entries stay visible but greyed out (the user sees the
    feature exists but the gating condition isn't met)."""

    disabled_label: str = ""
    """When ``enabled`` is False, override ``label`` with this text so
    callers can swap "Publish..." for "Publish (no favorites saved)"."""

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
        """Resource Sharing actions — declarative, sourced from the bridge.

        F5 minimal: instead of hardcoding the three or four sharing
        entries, we ask the bridge for a list of :class:`MenuActionSpec`
        and render each one. A future extension that wants to contribute
        more entries (or a different set entirely) only needs to extend
        the bridge's ``get_menu_actions`` — neither the menu nor the
        action dispatcher needs to know the new entries exist as long
        as their sentinels are routed in ``_handle_menu_action``.
        """
        for spec in controller._extension_bridge.get_menu_actions():
            label = spec.disabled_label if (not spec.enabled and spec.disabled_label) else spec.label
            action = menu.addAction(label)
            action.setData(spec.sentinel)
            if not spec.enabled:
                action.setEnabled(False)

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

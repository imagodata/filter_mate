"""
Favorites Controller for FilterMate.

Manages the favorites indicator and favorites operations UI.
Extracted from filter_mate_dockwidget.py (lines 1966-2897).

Story: MIG-072
Phase: 6 - God Class DockWidget Migration
"""

from typing import TYPE_CHECKING, Optional, List, Any
import logging

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QMenu, QInputDialog, QMessageBox, QFileDialog,
    QLabel
)
from qgis.PyQt.QtGui import QCursor
from qgis.core import QgsProject

from ...core.domain.exceptions import (
    FavoritePersistenceError,
    FavoritesError,
    FavoritesNotInitialized,
)
from .base_controller import BaseController
from .favorites_spatial_helpers import (
    exact_filtered_feature_count,
    favorite_matches_current_layer,
    layer_signature_for,
    resolve_favorite_source_layer,
    resolve_remote_layer_entry,
    should_downgrade_single_selection,
)

if TYPE_CHECKING:
    from filter_mate_dockwidget import FilterMateDockWidget
    from ...core.services.favorites_service import FilterFavorite
    from ...core.domain.favorites_manager import FavoritesManager

from ..styles.favorites_styles import (
    FAVORITES_STYLES,
    build_indicator_stylesheet,
)
from .favorites_extension_bridge import FavoritesExtensionBridge
from .favorites_spatial_handler import FavoritesSpatialHandler
from .favorites_menu_builder import (
    FavoritesMenuBuilder,
    ACTION_ADD_FAVORITE,
    ACTION_MANAGE,
    ACTION_EXPORT,
    ACTION_IMPORT,
    ACTION_SHOW_ALL,
    ACTION_SHOW_GLOBAL,
    ACTION_SHARED_PICKER,
    ACTION_PUBLISH_SHARING,
    ACTION_QUICK_PUBLISH_SHARING,
    ACTION_MANAGE_SHARING_REPOS,
    ACTION_BACKUP_TO_PROJECT,
    ACTION_RESTORE_FROM_PROJECT,
    ACTION_CLEANUP_ORPHANS,
    ACTION_SHOW_STATS,
    ACTION_APPLY,
    ACTION_APPLY_GLOBAL,
    ACTION_COPY_TO_GLOBAL,
)

logger = logging.getLogger(__name__)


class FavoritesController(BaseController):
    """
    Controller for favorites management.

    Handles:
    - Favorites indicator display and styling
    - Add/Remove/Apply favorites
    - Import/Export favorites
    - Favorites menu and dialogs

    Signals:
        favorite_added: Emitted when a favorite is added (favorite_name)
        favorite_applied: Emitted when a favorite is applied (favorite_name)
        favorite_removed: Emitted when a favorite is removed (favorite_name)

    Example:
        controller = FavoritesController(dockwidget)
        controller.setup()

        # React to favorites changes
        controller.favorite_added.connect(on_favorite_added)
    """

    favorite_added = pyqtSignal(str)  # favorite_name
    favorite_applied = pyqtSignal(str)  # favorite_name
    favorite_removed = pyqtSignal(str)  # favorite_name
    favorites_changed = pyqtSignal()  # generic change signal

    def __init__(self, dockwidget: 'FilterMateDockWidget') -> None:
        """
        Initialize the favorites controller.

        Args:
            dockwidget: Main dockwidget reference
        """
        super().__init__(dockwidget)
        self._favorites_manager: Optional['FavoritesManager'] = None
        self._indicator_label: Optional[QLabel] = None
        self._initialized: bool = False
        self._extension_bridge = FavoritesExtensionBridge(self)
        # _spatial is lazy via the property below — tests that bypass
        # __init__ via __new__ get a fresh handler on first access.
        self._spatial_instance: Optional[FavoritesSpatialHandler] = None

    @property
    def _spatial(self) -> FavoritesSpatialHandler:
        """Lazy access to the spatial-config handler.

        Eager construction in ``__init__`` would force every test that
        builds the controller via ``FavoritesController.__new__`` to wire
        the handler manually — the lazy form keeps the test rigging
        small while production paths get the same single instance.
        """
        cached = getattr(self, "_spatial_instance", None)
        if cached is None:
            cached = FavoritesSpatialHandler(self)
            self._spatial_instance = cached
        return cached

    @property
    def favorites_manager(self) -> Optional['FavoritesManager']:
        """Get the favorites manager instance."""
        return self._favorites_manager

    @property
    def count(self) -> int:
        """Get the number of favorites."""
        if self._favorites_manager:
            return self._favorites_manager.count
        return 0

    def setup(self) -> None:
        """
        Setup favorites indicator and manager.

        Initializes the favorites manager and connects to indicator.
        """
        self._find_indicator_label()
        self._init_favorites_manager()

        # CRITICAL FIX 2026-01-18: Connect to favorites_changed signal from FavoritesService
        # This ensures the UI is updated when favorites are loaded from database
        if self._favorites_manager:
            self._favorites_manager.favorites_changed.connect(self._on_favorites_loaded)
            logger.debug("✓ Connected to FavoritesService.favorites_changed signal")

        self._initialized = True
        logger.debug("FavoritesController setup complete")

    def teardown(self) -> None:
        """Clean up resources."""
        self._favorites_manager = None
        super().teardown()

    def sync_with_dockwidget_manager(self) -> bool:
        """
        Re-synchronize with the favorites manager from dockwidget.

        FIX 2026-01-19: Called when the dockwidget's _favorites_manager is updated
        (e.g., after init_filterMate_db() configures it).

        Returns:
            bool: True if sync was successful
        """
        if not hasattr(self.dockwidget, '_favorites_manager'):
            logger.debug("sync_with_dockwidget_manager: dockwidget has no _favorites_manager")
            return False

        new_manager = self.dockwidget._favorites_manager
        if new_manager is None:
            logger.debug("sync_with_dockwidget_manager: dockwidget._favorites_manager is None")
            return False

        # Disconnect old signal if any
        if self._favorites_manager:
            try:
                self._favorites_manager.favorites_changed.disconnect(self._on_favorites_loaded)
            except (TypeError, RuntimeError):
                pass  # Signal wasn't connected

        # Update reference
        old_count = self.count
        self._favorites_manager = new_manager

        # Connect new signal
        self._favorites_manager.favorites_changed.connect(self._on_favorites_loaded)

        # Update UI
        self.update_indicator()

        logger.info(f"✓ FavoritesController synced with dockwidget manager (was {old_count}, now {self.count} favorites)")
        return True

    def on_tab_activated(self) -> None:
        """Handle tab activation."""
        super().on_tab_activated()
        self.update_indicator()

    def on_tab_deactivated(self) -> None:
        """Handle tab deactivation."""
        super().on_tab_deactivated()

    # === Public API ===

    def _on_favorites_loaded(self) -> None:
        """
        Handler for favorites_changed signal from FavoritesService.
        Updates the indicator when favorites are loaded/added/removed.
        """
        logger.info(f"✓ Favorites changed - updating UI (count: {self.count})")
        self.update_indicator()
        self.favorites_changed.emit()  # Propagate signal

    def update_indicator(self) -> None:
        """Update the favorites indicator badge with current count."""
        if not self._indicator_label:
            return

        count = self.count

        # Update text and styling
        if count > 0:
            self._indicator_label.setText(f"★ {count}")
            tooltip = f"★ {count} Favorites saved\nClick to apply or manage"
            style = self._get_indicator_style('active')
        else:
            self._indicator_label.setText("★")
            tooltip = "★ No favorites saved\nClick to add current filter"
            style = self._get_indicator_style('empty')

        self._indicator_label.setStyleSheet(style)
        self._indicator_label.setToolTip(tooltip)
        self._indicator_label.adjustSize()

    def handle_indicator_clicked(self) -> None:
        """
        Handle click on favorites indicator.

        Shows the favorites context menu.
        """

        # Lazy initialization fallback - if setup() was never called, do it now
        if not self._initialized:
            self.setup()

        self._show_favorites_menu()

    def add_current_to_favorites(self, name: Optional[str] = None) -> bool:
        """
        Add current filter configuration to favorites.

        Args:
            name: Optional favorite name (prompts if not provided)

        Returns:
            True if favorite was added successfully
        """
        expression = self.get_current_filter_expression()
        if not expression:
            self._show_warning(self.tr("No active filter to save."))
            return False

        if not name:
            name, ok = QInputDialog.getText(
                self.dockwidget,
                self.tr("Add Favorite"),
                self.tr("Favorite name:"),
                text=""
            )
            if not ok or not name:
                return False

        if not self._validate_favorite_name(name):
            return False

        # Create favorite with current filter state
        success = self._create_favorite(name, expression)
        if success:
            self.favorite_added.emit(name)
            self.favorites_changed.emit()
            self.update_indicator()
            self._show_success(self.tr("Favorite '{0}' added successfully").format(name))

        return success

    def apply_favorite(self, favorite_id: str) -> bool:
        """
        Apply a saved favorite filter.

        Args:
            favorite_id: ID of the favorite to apply

        Returns:
            True if favorite was applied successfully

        A4 (audit 2026-04-29): :class:`FavoritesNotInitialized` is now
        caught and surfaced as a warning. The early ``if not
        self._favorites_manager`` guard above only covers the "service
        slot is None" case — once the slot is set, the service can still
        be in a non-initialised internal state (project not loaded yet,
        re-init in progress) and raise from any of its mutators.
        """
        if not self._favorites_manager:
            return False

        try:
            favorite = self._favorites_manager.get_favorite(favorite_id)
        except FavoritesNotInitialized as e:
            self._show_warning(self.tr(
                "Favorites are not ready yet: {0}"
            ).format(e))
            return False

        if not favorite:
            logger.warning(f"Favorite not found: {favorite_id}")
            return False

        # Legacy favorites (saved before the predicate-capture fix) carry
        # remote_layers but no geometric_predicates in spatial_config. The
        # restore would otherwise wipe the live predicate selection with
        # an empty list, leaving the filter task with no predicate. Heal
        # them in place with an "Intersect" default and surface a warning
        # so the user knows the recovery happened.
        self._backfill_legacy_predicate_default(favorite)

        # Apply the favorite expression
        success = self._apply_favorite_expression(favorite)
        if success:
            try:
                # Update use count
                self._favorites_manager.mark_favorite_used(favorite_id)
            except FavoritesError as e:
                # Use-count bump is non-critical; log and keep the apply
                # success — the user already sees the filter applied.
                logger.warning(f"Failed to mark favorite used: {e}")
            self.favorite_applied.emit(favorite.name)
            # FIX 2026-04-22: surface the use_count bump so consumers (manager
            # dialog, menu preview) can redraw. mark_favorite_used() only
            # updates the SQLite row; no signal was emitted and the menu's
            # "Used N times" label stayed frozen until full reload.
            self.favorites_changed.emit()
            logger.info(f"Applied favorite: {favorite.name}")

        return success

    def remove_favorite(self, favorite_id: str) -> bool:
        """
        Remove a favorite.

        Args:
            favorite_id: ID of the favorite to remove

        Returns:
            True if favorite was removed successfully

        A4 (audit 2026-04-29): same defensive catch as ``apply_favorite``
        for :class:`FavoritesNotInitialized`. Persistence failures keep
        the existing :class:`FavoritePersistenceError` handling.
        """
        if not self._favorites_manager:
            return False

        try:
            favorite = self._favorites_manager.get_favorite(favorite_id)
        except FavoritesNotInitialized as e:
            self._show_warning(self.tr(
                "Favorites are not ready yet: {0}"
            ).format(e))
            return False

        if not favorite:
            return False

        name = favorite.name
        try:
            success = self._favorites_manager.remove_favorite(favorite_id)
        except FavoritesNotInitialized as e:
            self._show_warning(self.tr(
                "Favorites are not ready yet: {0}"
            ).format(e))
            return False
        except FavoritePersistenceError as e:
            self._show_error(self.tr(
                "Could not remove '{0}': {1}"
            ).format(name, e.__cause__ or e))
            return False
        if success:
            try:
                self._favorites_manager.save()
            except FavoritePersistenceError as e:
                logger.warning(f"Save after remove failed: {e}")
            except FavoritesNotInitialized as e:
                logger.warning(f"Save after remove skipped (not initialized): {e}")
            self.favorite_removed.emit(name)
            self.favorites_changed.emit()
            self.update_indicator()
            logger.info(f"Removed favorite: {name}")

        return success

    def get_current_filter_expression(self) -> str:
        """
        Get the current filter expression.

        Tries multiple sources in order:
        1. Expression widget (if exists and has content)
        2. Current layer's subsetString (the actual applied filter)
        3. Source layer from combobox's subsetString

        Returns:
            The current filter expression, or empty string if none

        FIX 2026-04-23: filter out standalone display expressions (COALESCE,
        CONCAT, bare field refs…) so favorites never capture a non-boolean
        clause that would blow up as `WHERE COALESCE(...)` on reapply.
        """
        def _clean(candidate: Optional[str]) -> str:
            if not candidate or not candidate.strip():
                return ""
            try:
                from ...core.filter import sanitize_subset_string
                sanitized = sanitize_subset_string(candidate)
            except ImportError:
                return candidate
            if not sanitized or not sanitized.strip():
                logger.info(
                    "get_current_filter_expression: dropping non-boolean expression "
                    f"(display expr, not a filter): '{candidate[:80]}...'"
                )
                return ""
            return sanitized

        try:
            # Source 1: Try expression widget
            if hasattr(self.dockwidget, 'mQgsFieldExpressionWidget_filtering_active_expression'):
                widget = self.dockwidget.mQgsFieldExpressionWidget_filtering_active_expression
                if hasattr(widget, 'expression'):
                    cleaned = _clean(widget.expression())
                    if cleaned:
                        return cleaned
                elif hasattr(widget, 'currentText'):
                    cleaned = _clean(widget.currentText())
                    if cleaned:
                        return cleaned

            # Source 2: Try current layer's subsetString
            if hasattr(self.dockwidget, 'current_layer') and self.dockwidget.current_layer:
                cleaned = _clean(self.dockwidget.current_layer.subsetString())
                if cleaned:
                    return cleaned

            # Source 3: Try filtering source layer combobox
            if hasattr(self.dockwidget, 'comboBox_filtering_current_layer'):
                layer = self.dockwidget.comboBox_filtering_current_layer.currentLayer()
                if layer:
                    cleaned = _clean(layer.subsetString())
                    if cleaned:
                        return cleaned

            return ""
        except Exception as e:
            logger.debug(f"Could not get current expression: {e}")
            return ""

    def get_all_favorites(self) -> List['FilterFavorite']:
        """
        Get all favorites.

        Returns:
            List of all favorites
        """
        if not self._favorites_manager:
            return []
        return self._favorites_manager.get_all_favorites()

    def get_recent_favorites(self, limit: int = 10) -> List['FilterFavorite']:
        """
        Get recent favorites.

        Args:
            limit: Maximum number of favorites to return

        Returns:
            List of recent favorites
        """
        if not self._favorites_manager:
            return []
        return self._favorites_manager.get_recent_favorites(limit=limit)

    def export_favorites(self, filepath: Optional[str] = None) -> bool:
        """
        Export favorites to a JSON file.

        Args:
            filepath: Path to export file (prompts if not provided)

        Returns:
            True if export was successful
        """
        if not filepath:
            filepath, _ = QFileDialog.getSaveFileName(
                self.dockwidget,
                self.tr("Export Favorites"),
                "favorites.json",
                "JSON Files (*.json)"
            )

        if not filepath or not self._favorites_manager:
            return False

        # FIX 2026-04-21: route through FavoritesService.export_favorites
        # which produces the portable v2 format (signature-based).
        export_fn = getattr(self._favorites_manager, 'export_favorites', None)
        if callable(export_fn):
            result = export_fn(filepath)
            success = getattr(result, 'success', False)
            count = getattr(result, 'favorites_count', self.count)
        else:
            # Fallback for managers that still expose export_to_file
            legacy_fn = getattr(self._favorites_manager, 'export_to_file', None)
            success = bool(legacy_fn(filepath)) if callable(legacy_fn) else False
            count = self.count

        if success:
            self._show_success(self.tr("Exported {0} favorites").format(count))
            return True
        self._show_warning(self.tr("Failed to export favorites"))
        return False

    def import_favorites(
        self,
        filepath: Optional[str] = None,
        merge: Optional[bool] = None
    ) -> int:
        """
        Import favorites from a JSON file.

        Args:
            filepath: Path to import file (prompts if not provided)
            merge: True to merge, False to replace (prompts if not provided)

        Returns:
            Number of favorites imported
        """
        if not filepath:
            filepath, _ = QFileDialog.getOpenFileName(
                self.dockwidget,
                self.tr("Import Favorites"),
                "",
                "JSON Files (*.json)"
            )

        if not filepath or not self._favorites_manager:
            return 0

        if merge is None:
            # F11 policy: stays a modal QMessageBox.question. Replace-all
            # is destructive (drops every existing favorite); the user
            # must consciously decide before we touch the DB.
            result = QMessageBox.question(
                self.dockwidget,
                self.tr("Import Favorites"),
                self.tr("Merge with existing favorites?\n\n"
                         "Yes = Add to existing\n"
                         "No = Replace all existing"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if result == QMessageBox.StandardButton.Cancel:
                return 0
            merge = (result == QMessageBox.StandardButton.Yes)

        # FIX 2026-04-21: route through FavoritesService.import_favorites which
        # re-resolves portable signatures against the current project.
        import_fn = getattr(self._favorites_manager, 'import_favorites', None)
        if callable(import_fn):
            # skip_duplicates is the inverse of merge:
            #   merge=True  -> skip_duplicates=True  (add the rest alongside existing)
            #   merge=False -> skip_duplicates=False (replace - currently we still
            #                  skip duplicates because the underlying manager only
            #                  supports additive import; replace semantics would
            #                  need a prior remove_all which is out of scope here).
            result = import_fn(filepath, skip_duplicates=True)
            count = getattr(result, 'imported_count', 0)
        else:
            legacy_fn = getattr(self._favorites_manager, 'import_from_file', None)
            count = legacy_fn(filepath, merge=merge) if callable(legacy_fn) else 0

        if count > 0:
            # FIX 2026-04-22: FavoritesService exposes save() (not save_to_project),
            # which delegates to the underlying manager. Calling save_to_project()
            # directly raised AttributeError and swallowed the import success
            # signal + indicator update.
            save_fn = getattr(self._favorites_manager, 'save', None)
            if callable(save_fn):
                save_fn()
            self.favorites_changed.emit()
            self.update_indicator()
            self._show_success(self.tr("Imported {0} favorites").format(count))
        else:
            self._show_warning(self.tr("No favorites imported"))

        return count

    def show_manager_dialog(self) -> None:
        """Show the favorites manager dialog."""
        try:
            # Check if favorites manager is available
            if not self._favorites_manager:
                self._show_warning(self.tr("Favorites manager not initialized. Please restart FilterMate."))
                return

            # FIX 2026-04-23 (LOW-3): when there are no favorites AND the
            # favorites_sharing extension isn't active, opening an empty
            # manager is confusing — surface the suggested next step
            # instead. When sharing IS active we still open the dialog so
            # the user can reach the "📡 Shared..." button.
            if self.count == 0 and not self._is_sharing_extension_active():
                self._show_info(self.tr(
                    "No favorites saved yet — apply a filter then click the "
                    "★ indicator to save your first one."
                ))
                return

            from ..dialogs import FavoritesManagerDialog
            # F5 invariant: pass the extension bridge so the dialog's
            # sharing flows route through the same single coupling point
            # as the controller's menu, rather than reaching directly
            # into ``extensions.favorites_sharing.ui``.
            dialog = FavoritesManagerDialog(
                self._favorites_manager,
                self.dockwidget,
                extension_bridge=self._extension_bridge,
            )

            # Connect the favoriteApplied signal to apply the favorite.
            # UI-6 (2026-04-29): the dialog is parented to ``dockwidget``
            # so the connection would otherwise outlive each Open/Close/
            # Open cycle and re-fire ``apply_favorite`` for every prior
            # session. Disconnect in ``finally`` so the lifetime is
            # bounded by this call.
            dialog.favoriteApplied.connect(self.apply_favorite)
            try:
                dialog.exec()
            finally:
                try:
                    dialog.favoriteApplied.disconnect(self.apply_favorite)
                except (TypeError, RuntimeError):
                    pass
            # Refresh after dialog closes
            self.favorites_changed.emit()
            self.update_indicator()
        except ImportError as e:
            logger.warning(f"FavoritesManagerDialog not available: {e}")
            self._show_warning(self.tr("Favorites manager dialog not available"))
        except Exception as e:
            logger.error(f"Error showing favorites manager: {e}")
            self._show_warning(self.tr("Error: {0}").format(e))

    # === Private Methods ===

    def _find_indicator_label(self) -> None:
        """Find the favorites indicator label in dockwidget."""
        if hasattr(self.dockwidget, 'favorites_indicator_label'):
            self._indicator_label = self.dockwidget.favorites_indicator_label

    def _init_favorites_manager(self) -> None:
        """
        Initialize the favorites manager.

        FIX 2026-04-23 (CRIT-4): the controller no longer creates its own
        FavoritesService. FilterMateApp owns the singleton and assigns it
        to ``dockwidget._favorites_manager`` once ``init_filterMate_db()``
        has resolved the project uuid. Creating a rogue service here meant
        signals emitted before the sync were silently lost, and if the
        sync was ever skipped (unit tests, dockwidget re-open on a project
        reload without a db re-init) the UI pointed at a permanently-empty
        service.

        The controller now binds to whatever dockwidget exposes, or stays
        dormant (None) until ``sync_with_dockwidget_manager()`` is called.
        """

        # PRIORITY 1: Use the service that FilterMateApp attached to the
        # dockwidget. This is the canonical path in production.
        if hasattr(self.dockwidget, '_favorites_manager') and self.dockwidget._favorites_manager:
            self._favorites_manager = self.dockwidget._favorites_manager
            return

        # No service available yet — stay dormant. sync_with_dockwidget_manager()
        # will wire us up once FilterMateApp finishes init_filterMate_db.
        self._favorites_manager = None
        logger.debug(
            "FavoritesController: no favorites service yet — waiting for "
            "FilterMateApp to publish one via sync_with_dockwidget_manager()."
        )

    def _restore_spatial_config(self, favorite: 'FilterFavorite') -> bool:
        """Delegate — see :meth:`FavoritesSpatialHandler.restore_spatial_config`."""
        return self._spatial.restore_spatial_config(favorite)

    def _get_indicator_style(self, state: str) -> str:
        """Get stylesheet for indicator state."""
        return build_indicator_stylesheet(state)

    def _show_favorites_menu(self) -> None:
        """Show context menu with favorites options.

        Construction is delegated to :class:`FavoritesMenuBuilder` so the
        controller stays focused on lifecycle and dispatch. The builder
        owns the QSS, the section layout, and the action sentinels;
        ``_handle_menu_action`` resolves those sentinels back to
        controller methods.
        """
        menu = FavoritesMenuBuilder.build(self, self.dockwidget)
        selected_action = menu.exec_(QCursor.pos())
        if selected_action:
            self._handle_menu_action(selected_action.data())

    def _handle_menu_action(self, action_data: Any) -> None:
        """Resolve a menu action sentinel back to a controller method."""
        if action_data == ACTION_ADD_FAVORITE:
            self.add_current_to_favorites()
        elif action_data == ACTION_MANAGE:
            self.show_manager_dialog()
        elif action_data == ACTION_EXPORT:
            self.export_favorites()
        elif action_data == ACTION_IMPORT:
            self.import_favorites()
        elif action_data == ACTION_SHOW_ALL:
            self.show_manager_dialog()
        elif action_data == ACTION_SHOW_GLOBAL:
            # The unified manager dialog's scope filter (F10) already
            # covers the "Global · All projects" view; route there
            # rather than maintain a placeholder dialog.
            self.show_manager_dialog()
        elif action_data == ACTION_BACKUP_TO_PROJECT:
            self._backup_to_project()
        elif action_data == ACTION_RESTORE_FROM_PROJECT:
            self._restore_from_project()
        elif action_data == ACTION_CLEANUP_ORPHANS:
            self._cleanup_orphan_projects()
        elif action_data == ACTION_SHOW_STATS:
            self._show_database_stats()
        elif action_data == ACTION_SHARED_PICKER:
            self._open_shared_picker()
        elif action_data == ACTION_PUBLISH_SHARING:
            self._open_publish_dialog()
        elif action_data == ACTION_QUICK_PUBLISH_SHARING:
            self._quick_publish_to_default_repo()
        elif action_data == ACTION_MANAGE_SHARING_REPOS:
            self._open_repo_manager_dialog()
        elif isinstance(action_data, tuple):
            if action_data[0] == ACTION_APPLY:
                self.apply_favorite(action_data[1])
            elif action_data[0] == ACTION_APPLY_GLOBAL:
                self._apply_global_favorite(action_data[1])
            elif action_data[0] == ACTION_COPY_TO_GLOBAL:
                self._copy_to_global(action_data[1])

    def _validate_favorite_name(self, name: str) -> bool:
        """Validate favorite name."""
        if not name or not name.strip():
            self._show_warning(self.tr("Favorite name cannot be empty."))
            return False

        # Check for duplicates
        if self._favorites_manager:
            existing = self._favorites_manager.get_favorite_by_name(name)
            if existing:
                # F11 policy: stays a modal QMessageBox.question because
                # the user must decide before the save proceeds. A toast
                # would risk silent data loss if missed.
                result = QMessageBox.question(
                    self.dockwidget,
                    self.tr("Duplicate Name"),
                    self.tr("A favorite named '{0}' already exists.\n"
                             "Do you want to replace it?").format(name),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if result != QMessageBox.StandardButton.Yes:
                    return False
                # Remove existing
                try:
                    self._favorites_manager.remove_favorite(existing.id)
                except FavoritePersistenceError as e:
                    self._show_error(self.tr(
                        "Could not replace '{0}': {1}"
                    ).format(name, e.__cause__ or e))
                    return False

        return True

    def _create_favorite(self, name: str, expression: str) -> bool:
        """
        Create a new favorite.

        ENHANCEMENT 2026-01-18: Capture spatial_config (task_features, predicates, etc.)
        so favorites can be properly restored with full geometric context.
        """
        if not self._favorites_manager:
            return False

        try:
            # Get layer info
            layer = self.dockwidget.current_layer
            layer_name = layer.name() if layer else None
            layer_provider = layer.providerType() if layer else None

            # Collect all filtered layers (remote layers with active filters)
            # Iterate through all vector layers to find those with filters.
            # FIX 2026-04-21: also persist a project-portable layer_signature
            # (provider::schema.table) so favorites can be re-resolved after
            # project reopen OR imported into a sibling project with different
            # layer UUIDs (multi-project JSON sharing).
            remote_layers = {}
            source_layer_id = layer.id() if layer else None
            project = QgsProject.instance()

            for layer_id, map_layer in project.mapLayers().items():
                # Skip non-vector layers
                if not hasattr(map_layer, 'subsetString'):
                    continue
                # Skip the source layer (already captured in main expression)
                if layer_id == source_layer_id:
                    continue
                # Check if layer has an active filter
                subset = map_layer.subsetString()
                if subset and subset.strip():
                    signature = layer_signature_for(map_layer)
                    display_name = map_layer.name()
                    # FIX 2026-04-23 (CRIT-3): key remote_layers by the
                    # portable signature (postgres::schema.table, ...) so the
                    # dict is stable across users and never collides when two
                    # PG tables share a display name. display_name stays in
                    # the payload for UI rendering.
                    canonical_key = signature if signature else display_name
                    if canonical_key in remote_layers:
                        logger.debug(
                            "Skipping duplicate remote layer signature '%s' (display '%s')",
                            canonical_key, display_name,
                        )
                        continue
                    remote_layers[canonical_key] = {
                        'expression': subset,
                        # FIX 2026-04-27: layer.featureCount() returns an
                        # *estimate* on PostgreSQL (pg_class.reltuples) that
                        # tends to collapse to 1 for complex EXISTS subsets,
                        # making the favorites manager show "1" everywhere.
                        # Iterate the filtered cursor with no attrs/geom for
                        # an exact count at minimal I/O cost.
                        'feature_count': exact_filtered_feature_count(map_layer),
                        'layer_id': layer_id,
                        'layer_signature': signature,
                        'display_name': display_name,
                        'provider': map_layer.providerType()
                    }

            # ENHANCEMENT 2026-01-18: Capture spatial configuration
            spatial_config = self._capture_spatial_config()

            # FIX 2026-04-21: embed source layer signature in spatial_config so
            # the export/import path can resolve the source layer across projects.
            if layer is not None:
                if spatial_config is None:
                    spatial_config = {}
                spatial_config['source_layer_signature'] = layer_signature_for(layer)

            # Use FavoritesService.add_favorite() with individual parameters
            favorite_id = self._favorites_manager.add_favorite(
                name=name,
                expression=expression,
                layer_name=layer_name,
                layer_provider=layer_provider,
                remote_layers=remote_layers if remote_layers else None,
                spatial_config=spatial_config
            )

            if favorite_id:
                # Note: Favorite already saved to database in add_favorite()
                # save() is a no-op but we call it for consistency
                logger.debug(f"Favorite '{name}' created successfully (ID: {favorite_id})")
                self._favorites_manager.save()  # No-op, already persisted
                return True
            else:
                logger.warning(f"Failed to create favorite '{name}' - add_favorite() returned None")
            return False

        except FavoritePersistenceError as e:
            self._show_error(self.tr(
                "Could not save '{0}': {1}"
            ).format(name, e.__cause__ or e))
            return False
        except Exception as e:
            logger.error(f"Failed to create favorite: {e}")
            return False

    def _capture_spatial_config(self) -> Optional[dict]:
        """Delegate — see :meth:`FavoritesSpatialHandler.capture_spatial_config`."""
        return self._spatial.capture_spatial_config()

    def _apply_favorite_expression(self, favorite: 'FilterFavorite') -> bool:
        """Apply a favorite by pushing its saved subset strings directly.

        REWRITE 2026-04-27: favorites are subset snapshots, not state
        recordings. The previous implementation rebuilt the spatial filter
        from ``spatial_config`` (predicates, task_feature_ids, exploring
        groupbox …) by re-firing ``launchTaskEvent``. That dance failed
        silently when the favorite's source layer differed from the
        current layer, because the rebuild ran against the wrong source
        feature set even though the task reported success.

        We now treat ``favorite.expression`` as the source-layer subset
        and ``favorite.remote_layers[*].expression`` as the target-layer
        subsets, and push them through ``safe_set_subset_string()``
        directly. The cleaner only strips malformed ``__source`` patterns
        — well-formed ``EXISTS(... AS __source ...)`` payloads (the only
        shape favorites store) pass through unchanged.
        """
        try:
            return self._apply_favorite_subsets_directly(favorite)
        except Exception as e:
            logger.error(f"Failed to apply favorite: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def _apply_favorite_subsets_directly(self, favorite: 'FilterFavorite') -> bool:
        """Delegate — see :meth:`FavoritesSpatialHandler.apply_favorite_subsets_directly`."""
        return self._spatial.apply_favorite_subsets_directly(favorite)

    

    

    

    

    

    def _ensure_applicable_groupbox_for_favorite(self, favorite: 'FilterFavorite') -> None:
        """Delegate — see :meth:`FavoritesSpatialHandler.ensure_applicable_groupbox_for_favorite`."""
        self._spatial.ensure_applicable_groupbox_for_favorite(favorite)

    def _restore_filtering_ui_from_favorite(self, favorite: 'FilterFavorite') -> None:
        """Delegate — see :meth:`FavoritesSpatialHandler.restore_filtering_ui_from_favorite`."""
        self._spatial.restore_filtering_ui_from_favorite(favorite)

    

    

    def _backfill_legacy_predicate_default(self, favorite: 'FilterFavorite') -> bool:
        """Delegate — see :meth:`FavoritesSpatialHandler.backfill_legacy_predicate_default`."""
        return self._spatial.backfill_legacy_predicate_default(favorite)

    def _show_info(self, message: str) -> None:
        """Push an info to the QGIS message bar (transient, non-blocking)."""
        try:
            from ...infrastructure.feedback import show_info
            show_info(message)
        except ImportError:
            logger.info(message)

    def _show_success(self, message: str) -> None:
        """Push a success notification to the QGIS message bar."""
        try:
            from ...infrastructure.feedback import show_success
            show_success(message)
        except ImportError:
            logger.info(f"Success: {message}")

    def _show_warning(self, message: str) -> None:
        """Push a warning to the QGIS message bar (transient, non-blocking)."""
        try:
            from ...infrastructure.feedback import show_warning
            show_warning(message)
        except ImportError:
            logger.warning(message)

    def _show_error(self, message: str) -> None:
        """Push a critical/error notification to the QGIS message bar.

        For transactional failures (save/persist/IO). Stays visible until
        dismissed. The user can read the full traceback in
        View → Panels → Log Messages.
        """
        try:
            from ...infrastructure.feedback import show_error
            show_error(message)
        except ImportError:
            logger.error(message)

    # ─────────────────────────────────────────────────────────────────
    # Global Favorites & Maintenance Methods
    # ─────────────────────────────────────────────────────────────────

    def _get_global_favorites(self) -> List['FilterFavorite']:
        """Get global favorites from the manager."""
        if not self._favorites_manager:
            return []
        return self._favorites_manager.get_global_favorites()

    def _apply_global_favorite(self, favorite_id: str) -> bool:
        """Apply a global favorite."""
        if not self._favorites_manager:
            return False

        # First, import the global favorite to the current project
        try:
            new_id = self._favorites_manager.import_global_to_project(favorite_id)
        except FavoritePersistenceError as e:
            self._show_error(self.tr(
                "Could not import global favorite: {0}"
            ).format(e.__cause__ or e))
            return False
        if not new_id:
            return False
        # Then apply the newly imported favorite
        self.update_indicator()
        return self.apply_favorite(new_id)

    def _copy_to_global(self, favorite_id: str) -> bool:
        """Copy a favorite to global favorites."""
        if not self._favorites_manager:
            return False

        try:
            new_id = self._favorites_manager.copy_to_global(favorite_id)
        except FavoritePersistenceError as e:
            self._show_error(self.tr(
                "Could not copy to global: {0}"
            ).format(e.__cause__ or e))
            return False
        if new_id:
            self._show_success(self.tr("Favorite copied to global favorites"))
            return True

        self._show_warning(self.tr("Failed to copy to global favorites"))
        return False

    

    def _backup_to_project(self) -> None:
        """Backup favorites to the QGIS project file."""
        if not self._favorites_manager:
            return

        from qgis.core import QgsProject
        try:
            success = self._favorites_manager.save_to_project_file(QgsProject.instance())
        except FavoritePersistenceError as e:
            self._show_error(self.tr(
                "Could not save favorites to project file: {0}"
            ).format(e.__cause__ or e))
            return
        if success:
            self._show_success(self.tr("Saved {0} favorite(s) to project file").format(self.count))
        else:
            self._show_warning(self.tr("Save failed"))

    def _restore_from_project(self) -> None:
        """Restore favorites from the QGIS project file."""
        if not self._favorites_manager:
            return

        from qgis.core import QgsProject
        count = self._favorites_manager.restore_from_project_file(QgsProject.instance())
        if count > 0:
            self.update_indicator()
            self._show_success(self.tr("Restored {0} favorite(s) from project file").format(count))
        else:
            self._show_warning(self.tr("No favorites to restore found in project"))

    def _build_migration_service(self):
        """Bootstrap a FavoritesMigrationService against the FilterMate db.

        Shared by the two menu actions (cleanup orphans, show stats);
        returns None and warns the user when the plugin config directory
        is uninitialized (MED-1: would otherwise build a bogus filesystem-
        root path on Linux or a drive-less path on Windows).
        """
        from ...core.services.favorites_migration_service import FavoritesMigrationService
        from ...config.config import ENV_VARS
        import os
        plugin_dir = ENV_VARS.get("PLUGIN_CONFIG_DIRECTORY", "") or ""
        if not plugin_dir:
            self._show_warning(self.tr(
                "FilterMate config directory is not initialized yet — "
                "open a QGIS project with FilterMate first."
            ))
            return None
        db_path = os.path.normpath(os.path.join(plugin_dir, 'filterMate_db.sqlite'))
        return FavoritesMigrationService(db_path)

    def _cleanup_orphan_projects(self) -> None:
        """Clean up orphan projects from the database."""
        migration_service = self._build_migration_service()
        if migration_service is None:
            return
        try:
            deleted_count, _deleted_ids = migration_service.cleanup_orphan_projects()
            if deleted_count > 0:
                self._show_success(self.tr("Cleaned up {0} orphan project(s)").format(deleted_count))
            else:
                self._show_success(self.tr("No orphan projects to clean up"))
        except Exception as e:
            logger.error(f"Error cleaning up orphan projects: {e}")
            self._show_warning(self.tr("Error: {0}").format(e))

    # ─────────────────────────────────────────────────────────────────
    # favorites_sharing extension integration (optional)
    # ─────────────────────────────────────────────────────────────────

    # ── Sharing extension delegation ────────────────────────────────
    # All sharing-related logic moved to FavoritesExtensionBridge so the
    # controller stays focused on the favorites domain. These thin
    # wrappers are kept so the menu builder + action dispatcher can call
    # ``self._extension_bridge_*`` indirectly without learning the bridge
    # API. Once F5 lands (registry pattern), even these wrappers can go.

    # ── Public surface for FavoritesMenuBuilder (UI-8) ──────────────
    # The builder is typed against ``BuilderContext`` (Protocol) — these
    # aliases expose the underscored internals through that contract.

    @property
    def extension_bridge(self) -> "FavoritesExtensionBridge":
        return self._extension_bridge

    def is_sharing_extension_active(self) -> bool:
        return self._is_sharing_extension_active()

    def get_global_favorites(self) -> List['FilterFavorite']:
        return self._get_global_favorites()

    def _is_sharing_extension_active(self) -> bool:
        return self._extension_bridge.is_active()

    def _has_default_remote_repo(self) -> bool:
        return self._extension_bridge.has_default_repo()

    def _open_shared_picker(self) -> None:
        self._extension_bridge.open_shared_picker()

    def _open_publish_dialog(self) -> None:
        self._extension_bridge.open_publish_dialog()

    def _open_repo_manager_dialog(self) -> None:
        self._extension_bridge.open_repo_manager_dialog()

    def _quick_publish_to_default_repo(self) -> None:
        self._extension_bridge.quick_publish_to_default_repo()

    def _show_database_stats(self) -> None:
        """Show database statistics dialog."""
        migration_service = self._build_migration_service()
        if migration_service is None:
            return
        try:
            stats = migration_service.get_database_statistics()
            if 'error' in stats:
                self._show_warning(self.tr("Error: {0}").format(stats['error']))
                return

            # Format statistics message
            msg = self.tr(
                "FilterMate Database Statistics\n\n"
                "Total favorites: {0}\n"
                "   Project: {1}\n"
                "   Orphans: {2}\n"
                "   Global: {3}\n"
            ).format(
                stats.get('total_favorites', 0),
                stats.get('project_favorites', 0),
                stats.get('orphan_favorites', 0),
                stats.get('global_favorites', 0),
            )

            # Add top projects
            top_projects = stats.get('top_projects', [])
            if top_projects:
                msg += "\n" + self.tr("Top projects by favorites:") + "\n"
                for proj in top_projects[:3]:
                    msg += f"   • {proj['name']}: {proj['favorites']}\n"

            QMessageBox.information(
                self.dockwidget,
                self.tr("FilterMate Statistics"),
                msg
            )
        except Exception as e:
            logger.error(f"Error showing database stats: {e}")
            self._show_warning(self.tr("Error: {0}").format(e))

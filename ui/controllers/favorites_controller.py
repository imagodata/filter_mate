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

from .base_controller import BaseController

if TYPE_CHECKING:
    from filter_mate_dockwidget import FilterMateDockWidget
    from ...core.services.favorites_service import FilterFavorite
    from ...core.domain.favorites_manager import FavoritesManager

from ..styles.favorites_styles import (
    FAVORITES_STYLES,
    build_indicator_stylesheet,
)
from .favorites_extension_bridge import FavoritesExtensionBridge
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
        if self._favorites_manager and hasattr(self._favorites_manager, 'favorites_changed'):
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
        if self._favorites_manager and hasattr(self._favorites_manager, 'favorites_changed'):
            try:
                self._favorites_manager.favorites_changed.disconnect(self._on_favorites_loaded)
            except (TypeError, RuntimeError):
                pass  # Signal wasn't connected

        # Update reference
        old_count = self.count
        self._favorites_manager = new_manager

        # Connect new signal
        if hasattr(self._favorites_manager, 'favorites_changed'):
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
        """
        if not self._favorites_manager:
            return False

        favorite = self._favorites_manager.get_favorite(favorite_id)
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
            # Update use count
            self._favorites_manager.mark_favorite_used(favorite_id)
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
        """
        if not self._favorites_manager:
            return False

        favorite = self._favorites_manager.get_favorite(favorite_id)
        if not favorite:
            return False

        name = favorite.name
        success = self._favorites_manager.remove_favorite(favorite_id)
        if success:
            self._favorites_manager.save()
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

            # Connect the favoriteApplied signal to apply the favorite
            dialog.favoriteApplied.connect(self.apply_favorite)

            dialog.exec()
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
        """
        Restore spatial configuration from favorite to dockwidget.

        This ensures task_features (selected FIDs) are available when
        launchTaskEvent is called, so the filter task can rebuild
        EXISTS expressions correctly.

        Args:
            favorite: Favorite containing spatial_config

        Returns:
            True if config was restored successfully
        """
        if not favorite.spatial_config:
            logger.warning(f"Favorite '{favorite.name}' has no spatial_config to restore")
            return False

        try:
            config = favorite.spatial_config

            # FIX 2026-04-21: restore the exploring groupbox mode FIRST so
            # downstream widgets (picker, multi-select combo, custom
            # selection expression) are in the right state when
            # task_features / predicates are read back.
            saved_groupbox = config.get('exploring_groupbox')
            if saved_groupbox and hasattr(self.dockwidget, '_restore_groupbox_ui_state'):
                try:
                    self.dockwidget._restore_groupbox_ui_state(saved_groupbox)
                    logger.info(f"  ✓ Restored exploring_groupbox = {saved_groupbox}")
                except (AttributeError, RuntimeError) as e:
                    logger.debug(f"Could not restore exploring_groupbox: {e}")

            # Repopulate the EXPLORING custom_selection expression widget
            # when the favorite was saved in that mode.
            custom_expr = config.get('custom_selection_expression')
            if custom_expr:
                try:
                    widget = self.dockwidget.widgets.get("EXPLORING", {}) \
                        .get("CUSTOM_SELECTION_EXPRESSION", {}).get("WIDGET")
                    if widget is not None and hasattr(widget, 'setExpression'):
                        widget.setExpression(custom_expr)
                        logger.info("  ✓ Restored custom_selection_expression")
                except (AttributeError, KeyError, RuntimeError) as e:
                    logger.debug(f"Could not restore custom_selection_expression: {e}")

            # Restore selected feature IDs (task_features)
            if 'task_feature_ids' in config and self.dockwidget.current_layer:
                feature_ids = config['task_feature_ids']
                logger.info(f"Restoring {len(feature_ids)} task_feature IDs from favorite")

                source_layer = self.dockwidget.current_layer

                # FIX 2026-04-21: only push IDs / fetch features when the
                # current layer is the same one the favorite was captured
                # against. If the user applies a favorite while on a
                # different layer (cross-layer apply), pushing those FIDs
                # would corrupt the wrong layer's selection with IDs from
                # an unrelated feature set.
                if self._favorite_matches_current_layer(favorite, source_layer):
                    # Push feature IDs into the QGIS layer selection so the
                    # feature picker / multi-select widgets surface them.
                    # Without this the single_selection picker may still
                    # report no feature after project reopen even though
                    # _restored_task_features is set, causing the filter
                    # to abort with "single_selection mode requires a
                    # selected feature".
                    try:
                        source_layer.selectByIds(feature_ids)
                        logger.info(
                            f"  ✓ Pushed {len(feature_ids)} feature IDs to QGIS selection on '{source_layer.name()}'"
                        )
                    except (AttributeError, RuntimeError) as e:
                        logger.debug(f"Could not selectByIds on source layer: {e}")

                    # Fetch actual QgsFeature objects from the source layer
                    features = []
                    for fid in feature_ids:
                        feature = source_layer.getFeature(fid)
                        if feature and feature.isValid():
                            features.append(feature)
                        else:
                            logger.warning(f"  ⚠️ Could not fetch feature {fid} from {source_layer.name()}")

                    if features:
                        logger.info(f"  → Loaded {len(features)} features from {len(feature_ids)} FIDs")
                        # Store in dockwidget for get_current_features() to pick up
                        self.dockwidget._restored_task_features = features
                        logger.info(f"  ✓ Stored {len(features)} features in dockwidget._restored_task_features")
                    else:
                        logger.warning(f"  ⚠️ Could not load any features from {len(feature_ids)} FIDs!")
                else:
                    logger.info(
                        f"  ↪ Skipping selectByIds: current layer '{source_layer.name()}' "
                        f"does not match favorite's source layer — FIDs would be meaningless."
                    )

            # Restore predicates if present
            if 'predicates' in config:
                predicates = config['predicates']
                logger.info(f"Restoring predicates: {list(predicates.keys())}")
                # Store in dockwidget for task to pick up
                self.dockwidget._restored_predicates = predicates

            # Restore buffer settings if present
            if 'buffer_value' in config:
                buffer_value = config['buffer_value']
                logger.info(f"Restoring buffer_value: {buffer_value}")
                # v5.0: Set buffer widget value
                if hasattr(self.dockwidget, 'mQgsDoubleSpinBox_filtering_buffer_value'):
                    self.dockwidget.mQgsDoubleSpinBox_filtering_buffer_value.setValue(float(buffer_value))
                    logger.info(f"  ✓ Buffer widget set to {buffer_value}")

            logger.info(f"✓ Spatial config restored from favorite '{favorite.name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to restore spatial_config: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

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
            self._show_global_favorites_dialog()
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
                self._favorites_manager.remove_favorite(existing.id)

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
                    signature = self._layer_signature_for(map_layer)
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
                        'feature_count': self._exact_filtered_feature_count(map_layer),
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
                spatial_config['source_layer_signature'] = self._layer_signature_for(layer)

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

        except Exception as e:
            logger.error(f"Failed to create favorite: {e}")
            return False

    def _capture_spatial_config(self) -> Optional[dict]:
        """
        Capture current spatial configuration for favorite restoration.

        This ensures favorites can be restored with full geometric context,
        including selected features, predicates, buffer settings, etc.

        Returns:
            Spatial configuration dict, or ``None`` when nothing worth
            capturing was present (callers must handle None — matches
            the contract used by ``_create_favorite``).
        """
        config = {}

        try:
            # FIX 2026-04-21: capture the exploring groupbox mode so the
            # favorite restores into the same selection context on apply.
            # Without this, a favorite created in custom_selection fires
            # after reopen with the default single_selection mode and
            # aborts because no source feature is selected.
            groupbox = getattr(self.dockwidget, 'current_exploring_groupbox', None)
            if groupbox:
                config['exploring_groupbox'] = groupbox
                logger.info(f"Captured exploring_groupbox: {groupbox}")

                # For custom_selection, also capture the expression driving
                # source feature selection so the exploring widget can be
                # repopulated on apply.
                if groupbox == 'custom_selection':
                    try:
                        widget = self.dockwidget.widgets.get("EXPLORING", {}) \
                            .get("CUSTOM_SELECTION_EXPRESSION", {}).get("WIDGET")
                        if widget is not None and hasattr(widget, 'expression'):
                            custom_expr = widget.expression()
                            if custom_expr and custom_expr.strip():
                                config['custom_selection_expression'] = custom_expr
                                logger.info(f"Captured custom_selection_expression ({len(custom_expr)} chars)")
                    except (AttributeError, KeyError, RuntimeError) as e:
                        logger.debug(f"Could not capture custom_selection_expression: {e}")

            # Capture task_features (selected feature IDs)
            features, _ = self.dockwidget.get_current_features()
            if features:
                feature_ids = [f.id() for f in features if f.isValid()]
                if feature_ids:
                    config['task_feature_ids'] = feature_ids
                    logger.info(f"Captured {len(feature_ids)} task_feature IDs for favorite")

            # Capture geometric predicates from the actual filtering widgets.
            #
            # FIX 2026-04-23: the previous implementation read a dict from
            # ``PROJECT_LAYERS[layer_id]['filtering']['predicates']`` — but that
            # key is never populated anywhere in the codebase. The canonical
            # keys (written by sync_ui_to_project_layers and task_builder) are
            # ``has_geometric_predicates`` (bool) and ``geometric_predicates``
            # (list, e.g. ``['Intersect']``). As a result, favorites were
            # silently saved *without* predicate info, and on restore the
            # ``pushButton_checkable_filtering_geometric_predicates`` toggle
            # stayed off even though the combobox still showed Intersect
            # checked (from QGIS' own project persistence) — the task then
            # reported ``has_geometric_predicates=False`` and refused to
            # filter the distant layers.
            #
            # We now read both values, preferring the live widget state and
            # falling back to PROJECT_LAYERS so the capture works even when
            # the widgets are not reachable (headless / test contexts).
            predicate_list: list = []
            has_predicates: bool = False

            combo_widget = getattr(
                self.dockwidget, 'comboBox_filtering_geometric_predicates', None
            )
            if combo_widget is not None and hasattr(combo_widget, 'checkedItems'):
                try:
                    predicate_list = list(combo_widget.checkedItems() or [])
                except (RuntimeError, AttributeError) as e:
                    logger.debug(f"Could not read checkedItems from combobox: {e}")

            has_pred_btn = getattr(
                self.dockwidget, 'pushButton_checkable_filtering_geometric_predicates', None
            )
            if has_pred_btn is not None and hasattr(has_pred_btn, 'isChecked'):
                try:
                    has_predicates = bool(has_pred_btn.isChecked())
                except (RuntimeError, AttributeError) as e:
                    logger.debug(f"Could not read isChecked from geometric predicates button: {e}")

            # Fallback to PROJECT_LAYERS when the widgets are unavailable.
            if (not predicate_list or not has_predicates) and \
                    hasattr(self.dockwidget, 'PROJECT_LAYERS') and \
                    self.dockwidget.current_layer:
                layer_id = self.dockwidget.current_layer.id()
                layer_data = self.dockwidget.PROJECT_LAYERS.get(layer_id, {})
                filtering_data = layer_data.get('filtering', {}) if isinstance(layer_data, dict) else {}
                if not predicate_list:
                    stored_list = filtering_data.get('geometric_predicates', [])
                    if isinstance(stored_list, (list, tuple)):
                        predicate_list = list(stored_list)
                if not has_predicates:
                    has_predicates = bool(filtering_data.get('has_geometric_predicates', False))

            if predicate_list or has_predicates:
                config['geometric_predicates'] = predicate_list
                config['has_geometric_predicates'] = bool(has_predicates or predicate_list)
                logger.info(
                    f"Captured geometric_predicates: {predicate_list} "
                    f"(has_geometric_predicates={config['has_geometric_predicates']})"
                )

            # Capture buffer value if set
            # v5.0: Read buffer value from widget
            if hasattr(self.dockwidget, 'mQgsDoubleSpinBox_filtering_buffer_value'):
                buffer_value = self.dockwidget.mQgsDoubleSpinBox_filtering_buffer_value.value()
                if buffer_value != 0.0:
                    config['buffer_value'] = buffer_value
                    logger.info(f"Captured buffer_value: {buffer_value}")

            logger.info(f"Spatial config captured: {list(config.keys())}")

        except Exception as e:
            logger.warning(f"Failed to capture spatial config: {e}")

        return config if config else None

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
        """Push the favorite's saved subset strings to source + target layers.

        Resolution order for each layer (source uses favorite.layer_id /
        spatial_config.source_layer_signature / favorite.layer_name; targets
        use the same chain plus the per-entry ``layer_signature`` and
        ``layer_id`` fields). Layers that can't be resolved produce a
        warning but don't abort the rest of the apply.

        Args:
            favorite: Favorite carrying ``expression`` (source subset) and
                ``remote_layers`` (target → subset map).

        Returns:
            True when at least one layer received its subset.
        """
        from qgis.core import QgsProject

        try:
            from ...infrastructure.database.sql_utils import safe_set_subset_string
        except ImportError:
            from filter_mate.infrastructure.database.sql_utils import safe_set_subset_string

        project = QgsProject.instance()
        # Pre-build name + signature lookups so we resolve each entry in O(1).
        name_to_layer: dict = {}
        signature_to_layer: dict = {}
        for lid, lobj in project.mapLayers().items():
            try:
                name_to_layer[lobj.name()] = lobj
            except (RuntimeError, AttributeError):
                pass
            try:
                signature_to_layer[self._layer_signature_for(lobj)] = lobj
            except Exception:
                pass

        applied: List[str] = []
        skipped: List[str] = []
        zoom_layers: list = []  # Source + targets actually filtered, for auto-zoom

        spatial_config = favorite.spatial_config or {}

        # --- Source layer subset ----------------------------------------
        source_layer = self._resolve_favorite_source_layer(
            favorite, spatial_config, project, name_to_layer, signature_to_layer
        )
        source_subset = favorite.expression or ''
        if source_layer is not None:
            try:
                if safe_set_subset_string(source_layer, source_subset):
                    applied.append(source_layer.name())
                    zoom_layers.append(source_layer)
                    logger.info(
                        f"  ✓ Source layer '{source_layer.name()}' subset applied "
                        f"({len(source_subset)} chars)"
                    )
                else:
                    skipped.append(getattr(source_layer, 'name', lambda: '?')())
                    logger.warning(
                        f"  ⚠️ safe_set_subset_string rejected source subset on '{source_layer.name()}'"
                    )
            except Exception as e:
                logger.warning(f"Failed to apply source subset: {e}")
                skipped.append(getattr(source_layer, 'name', lambda: '?')())
        else:
            logger.warning(
                f"Favorite '{favorite.name}': source layer could not be resolved "
                f"(layer_id={favorite.layer_id}, layer_name={favorite.layer_name}, "
                f"signature={spatial_config.get('source_layer_signature')})"
            )
            skipped.append(favorite.layer_name or '<unknown source>')

        # --- Target layer subsets ---------------------------------------
        # Track count changes so the favorite's stored snapshot can be
        # refreshed in one persist at the end (legacy favorites had wrong
        # counts because layer.featureCount() returns estimates on PG).
        refreshed_remote_layers: dict = {}
        counts_changed = False

        for key, payload in (favorite.remote_layers or {}).items():
            target_layer = self._resolve_remote_layer_entry(
                key, payload, project, name_to_layer, signature_to_layer
            )
            target_subset = ''
            if isinstance(payload, dict):
                target_subset = payload.get('expression', '') or ''

            if target_layer is None:
                logger.warning(
                    f"  ⚠️ Could not resolve target layer for entry '{key}' — skipped"
                )
                skipped.append(str(key))
                if isinstance(payload, dict):
                    refreshed_remote_layers[key] = dict(payload)
                else:
                    refreshed_remote_layers[key] = payload
                continue

            try:
                if safe_set_subset_string(target_layer, target_subset):
                    applied.append(target_layer.name())
                    zoom_layers.append(target_layer)
                    fresh_count = self._exact_filtered_feature_count(target_layer)
                    if isinstance(payload, dict):
                        new_payload = dict(payload)
                    else:
                        new_payload = {'expression': target_subset}
                    if new_payload.get('feature_count') != fresh_count:
                        counts_changed = True
                    new_payload['feature_count'] = fresh_count
                    refreshed_remote_layers[key] = new_payload
                    logger.info(
                        f"  ✓ Target layer '{target_layer.name()}' subset applied "
                        f"({len(target_subset)} chars, {fresh_count} feature(s))"
                    )
                else:
                    skipped.append(target_layer.name())
                    if isinstance(payload, dict):
                        refreshed_remote_layers[key] = dict(payload)
                    else:
                        refreshed_remote_layers[key] = payload
                    logger.warning(
                        f"  ⚠️ safe_set_subset_string rejected target subset on '{target_layer.name()}'"
                    )
            except Exception as e:
                logger.warning(f"Failed to apply subset on '{target_layer.name()}': {e}")
                skipped.append(target_layer.name())
                if isinstance(payload, dict):
                    refreshed_remote_layers[key] = dict(payload)
                else:
                    refreshed_remote_layers[key] = payload

        # Persist refreshed counts so the favorites manager UI reflects
        # reality without forcing the user to re-save the favorite.
        if counts_changed and refreshed_remote_layers:
            favorite.remote_layers = refreshed_remote_layers
            try:
                if self._favorites_manager and hasattr(self._favorites_manager, 'update_favorite'):
                    self._favorites_manager.update_favorite(
                        favorite.id,
                        bump_updated_at=False,
                        remote_layers=refreshed_remote_layers,
                    )
                    logger.info(f"  ↻ Refreshed feature_count snapshot for favorite '{favorite.name}'")
            except Exception as exc:
                logger.debug(f"Could not persist refreshed feature_counts: {exc}")

        if not applied:
            self._show_warning(self.tr(
                "Favorite '{0}' could not be applied: no layer matched the saved source / targets."
            ).format(favorite.name))
            return False

        if skipped:
            logger.info(
                f"Favorite '{favorite.name}': applied={applied}, skipped={skipped}"
            )

        # Refresh the canvas so users see the new filter immediately
        # without waiting for the next idle event.
        try:
            from qgis.utils import iface
            if iface and hasattr(iface, 'mapCanvas'):
                canvas = iface.mapCanvas()
                if canvas is not None and hasattr(canvas, 'refreshAllLayers'):
                    canvas.refreshAllLayers()
        except Exception:
            pass

        # Auto-zoom on the union extent of every layer the favorite touched
        # (mirrors the normal filter completion flow).
        try:
            from ...adapters.auto_zoom import auto_zoom_to_filtered

            project_layers = {}
            try:
                project_layers = getattr(self.dockwidget, 'PROJECT_LAYERS', {}) or {}
            except (RuntimeError, AttributeError):
                project_layers = {}

            auto_zoom_to_filtered(
                zoom_layers,
                project_layers,
                dockwidget=self.dockwidget,
            )
        except Exception as exc:
            logger.debug(f"Favorite auto-zoom skipped: {exc}")

        logger.info(
            f"Favorite '{favorite.name}' applied directly: "
            f"{len(applied)} layer(s) updated, {len(skipped)} skipped"
        )
        return True

    def _resolve_favorite_source_layer(
        self,
        favorite: 'FilterFavorite',
        spatial_config: dict,
        project,
        name_to_layer: dict,
        signature_to_layer: dict,
    ):
        """Find the project layer the favorite was captured against."""
        # Stronger first: project-portable signature
        sig = spatial_config.get('source_layer_signature') if isinstance(spatial_config, dict) else None
        if sig and sig in signature_to_layer:
            return signature_to_layer[sig]

        # UUID match (same project as save-time)
        layer_id = getattr(favorite, 'layer_id', None)
        if layer_id:
            try:
                layer = project.mapLayer(layer_id)
                if layer is not None:
                    return layer
            except (RuntimeError, AttributeError):
                pass

        # Last resort: name match
        layer_name = getattr(favorite, 'layer_name', None)
        if layer_name and layer_name in name_to_layer:
            return name_to_layer[layer_name]

        return None

    def _resolve_remote_layer_entry(
        self,
        key,
        payload,
        project,
        name_to_layer: dict,
        signature_to_layer: dict,
    ):
        """Find the QgsMapLayer matching a ``favorite.remote_layers[key]`` entry."""
        # Signature stored in the payload (v2+).
        if isinstance(payload, dict):
            payload_sig = payload.get('layer_signature')
            if payload_sig and payload_sig in signature_to_layer:
                return signature_to_layer[payload_sig]

        # FIX 2026-04-23 (CRIT-3): when the dict key is itself a signature.
        if isinstance(key, str) and '::' in key and key in signature_to_layer:
            return signature_to_layer[key]

        # Legacy: payload carries layer_id (UUID)
        if isinstance(payload, dict):
            legacy_id = payload.get('layer_id')
            if legacy_id:
                try:
                    layer = project.mapLayer(legacy_id)
                    if layer is not None:
                        return layer
                except (RuntimeError, AttributeError):
                    pass

        # Last-chance: display name (or the dict key when it's a plain name).
        candidate_name = None
        if isinstance(payload, dict):
            candidate_name = payload.get('display_name')
        if not candidate_name and isinstance(key, str) and '::' not in key:
            candidate_name = key
        if candidate_name and candidate_name in name_to_layer:
            return name_to_layer[candidate_name]

        return None

    @staticmethod
    def _collect_filtering_widgets_for_favorite(dw: Any) -> List[Any]:
        """Collect the widgets whose signals must be silenced while we
        restore a favorite, so only the final launchTaskEvent fires a task.
        """
        candidates = [
            getattr(dw, 'mQgsFieldExpressionWidget_filtering_active_expression', None),
            getattr(dw, 'pushButton_checkable_filtering_layers_to_filter', None),
            getattr(dw, 'pushButton_checkable_filtering_geometric_predicates', None),
            getattr(dw, 'pushButton_checkable_filtering_buffer_value', None),
            getattr(dw, 'mQgsDoubleSpinBox_filtering_buffer_value', None),
            getattr(dw, 'checkableComboBoxLayer_filtering_layers_to_filter', None),
        ]
        try:
            layers_widget = dw.widgets.get("FILTERING", {}).get("LAYERS_TO_FILTER", {}).get("WIDGET")
            if layers_widget is not None:
                candidates.append(layers_widget)
        except (AttributeError, TypeError):
            pass
        return [w for w in candidates if w is not None]

    def _favorite_matches_current_layer(
        self,
        favorite: 'FilterFavorite',
        current_layer: Any,
    ) -> bool:
        """Decide whether task_feature_ids from the favorite can be safely
        pushed onto `current_layer`.

        Matching order (strongest first):
        1. spatial_config.source_layer_signature matches current layer's
           signature — portable across projects (v2 favorites).
        2. favorite.layer_id matches current_layer.id() — same QGIS project.
        3. favorite.layer_name matches current_layer.name() — last-chance fuzzy.

        Returns False as soon as we can prove mismatch; returns True only
        with a positive match on at least one of the three.
        """
        if current_layer is None:
            return False

        try:
            current_layer_id = current_layer.id()
        except (RuntimeError, AttributeError):
            current_layer_id = None
        try:
            current_layer_name = current_layer.name()
        except (RuntimeError, AttributeError):
            current_layer_name = None

        # Strongest check: project-portable signature
        spatial_config = getattr(favorite, 'spatial_config', None) or {}
        source_sig = spatial_config.get('source_layer_signature') if isinstance(spatial_config, dict) else None
        if source_sig:
            try:
                current_sig = self._layer_signature_for(current_layer)
                if current_sig == source_sig:
                    return True
            except Exception as e:
                logger.debug(f"Could not compute signature for current layer: {e}")

        # UUID match (same project)
        fav_layer_id = getattr(favorite, 'layer_id', None)
        if fav_layer_id and current_layer_id and fav_layer_id == current_layer_id:
            return True

        # Name match as last resort
        fav_layer_name = getattr(favorite, 'layer_name', None)
        if fav_layer_name and current_layer_name and fav_layer_name == current_layer_name:
            return True

        return False

    @staticmethod
    def _should_downgrade_single_selection(
        current_groupbox: Optional[str],
        has_restored_features: bool,
        picker_feature_valid: bool,
        selected_feature_count: int,
    ) -> bool:
        """Pure predicate: should we swap single_selection -> custom_selection?

        single_selection aborts when no source feature is available.
        custom_selection with an empty source expression runs with
        skip_source_filter=True and filters against the full source layer,
        which is what legacy favourites (no captured task_feature_ids) expect.
        """
        if current_groupbox != 'single_selection':
            return False
        if has_restored_features:
            return False
        if picker_feature_valid:
            return False
        if selected_feature_count > 0:
            return False
        return True

    def _ensure_applicable_groupbox_for_favorite(self, favorite: 'FilterFavorite') -> None:
        """Downgrade the exploring groupbox when the favorite cannot supply a
        source feature, so launchTaskEvent doesn't abort in single_selection.
        """
        dw = self.dockwidget
        if not dw or not getattr(dw, 'widgets_initialized', False):
            return

        current_groupbox = getattr(dw, 'current_exploring_groupbox', None)
        has_restored = bool(getattr(dw, '_restored_task_features', None))

        picker_feature = None
        try:
            picker = dw.widgets.get("EXPLORING", {}) \
                .get("SINGLE_SELECTION_FEATURES", {}).get("WIDGET")
            if picker is not None and hasattr(picker, 'feature'):
                picker_feature = picker.feature()
        except (AttributeError, KeyError, RuntimeError):
            picker_feature = None

        picker_valid = bool(picker_feature and getattr(picker_feature, 'isValid', lambda: False)())

        selected_count = 0
        current_layer = getattr(dw, 'current_layer', None)
        if current_layer is not None:
            try:
                selected_count = current_layer.selectedFeatureCount()
            except (AttributeError, RuntimeError):
                selected_count = 0

        if not self._should_downgrade_single_selection(
            current_groupbox=current_groupbox,
            has_restored_features=has_restored,
            picker_feature_valid=picker_valid,
            selected_feature_count=selected_count,
        ):
            return

        if not hasattr(dw, '_restore_groupbox_ui_state'):
            logger.debug("Cannot downgrade groupbox: _restore_groupbox_ui_state missing")
            return

        logger.info(
            f"Favorite '{favorite.name}': single_selection has no feature — "
            "downgrading to custom_selection so the filter doesn't abort."
        )
        try:
            dw._restore_groupbox_ui_state('custom_selection')
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Could not downgrade groupbox to custom_selection: {e}")

    def _restore_filtering_ui_from_favorite(self, favorite: 'FilterFavorite') -> None:
        """Restore filtering UI state (checkboxes, predicate toggle, buffer, layers list)
        from a favorite so launchTaskEvent runs with a fully populated config.

        Mirrors the non-UI restoration done in _restore_spatial_config but
        actually ticks the widgets (Intersect predicate button, layers_to_filter
        combobox, has_layers_to_filter button) and persists into PROJECT_LAYERS.
        """
        from qgis.PyQt.QtCore import Qt

        dw = self.dockwidget
        if not dw or not getattr(dw, 'widgets_initialized', False):
            logger.debug("Skipping UI restore: dockwidget not ready")
            return

        spatial_config = favorite.spatial_config or {}

        # FIX 2026-04-23: resolve geometric predicates from the canonical
        # fields first. Fall back to the legacy ``predicates`` dict shape
        # (written by pre-fix favorites and a handful of portability tests)
        # so existing favorites keep restoring without a manual rebuild.
        predicate_list = spatial_config.get('geometric_predicates')
        if isinstance(predicate_list, (list, tuple)):
            predicate_list = list(predicate_list)
            predicate_explicit = True
        else:
            legacy_predicates = spatial_config.get('predicates') or {}
            if isinstance(legacy_predicates, dict) and legacy_predicates:
                predicate_list = list(legacy_predicates.keys())
                predicate_explicit = True
            elif isinstance(legacy_predicates, (list, tuple)) and legacy_predicates:
                predicate_list = list(legacy_predicates)
                predicate_explicit = True
            else:
                predicate_list = []
                predicate_explicit = False

        has_predicates_flag = spatial_config.get('has_geometric_predicates')
        if has_predicates_flag is None:
            has_predicates_flag = bool(predicate_list)
        else:
            has_predicates_flag = bool(has_predicates_flag)
            predicate_explicit = True

        # FIX 2026-04-27: when the favorite carries no predicate info at
        # all, leave the live combobox / toggle untouched instead of
        # silently clearing them. ``apply_favorite`` already backfills
        # legacy favorites with an "Intersect" default, so reaching this
        # branch means a portability path bypassed the heal — preserve
        # the user's manual selection rather than regressing.

        buffer_value = spatial_config.get('buffer_value')

        current_layer = getattr(dw, 'current_layer', None)
        layer_props = None
        if current_layer is not None and hasattr(dw, 'PROJECT_LAYERS'):
            try:
                layer_props = dw.PROJECT_LAYERS.get(current_layer.id())
            except (RuntimeError, AttributeError):
                layer_props = None

        # --- 1. Resolve target layer ids from remote_layers payload ---
        resolved_layer_ids: List[str] = []
        try:
            from qgis.core import QgsProject
            project = QgsProject.instance()
            name_to_id = {}
            signature_to_id = {}
            for lid, lobj in project.mapLayers().items():
                try:
                    name_to_id[lobj.name()] = lid
                    signature_to_id[self._layer_signature_for(lobj)] = lid
                except (RuntimeError, AttributeError):
                    continue
            for key, payload in (favorite.remote_layers or {}).items():
                resolved = None
                # Signature stored in payload (v2+) — portable across projects
                if isinstance(payload, dict) and payload.get('layer_signature'):
                    resolved = signature_to_id.get(payload['layer_signature'])
                # FIX 2026-04-23 (CRIT-3): when dict key itself is a signature
                # (v3 canonical form produced by _create_favorite), resolve
                # directly from the signature->id map.
                if not resolved and isinstance(key, str) and '::' in key:
                    resolved = signature_to_id.get(key)
                # Legacy format: key is layer name, payload carries layer_id (UUID)
                if not resolved and isinstance(payload, dict):
                    legacy_id = payload.get('layer_id')
                    if legacy_id and legacy_id in project.mapLayers():
                        resolved = legacy_id
                # Last-chance resolution by display name. Skip when key is a
                # signature (contains "::") — that lookup would always miss
                # and might accidentally hit a user-named layer called
                # "postgres::..." — unlikely but not worth risking.
                if not resolved:
                    candidate_name = None
                    if isinstance(payload, dict):
                        candidate_name = payload.get('display_name')
                    if not candidate_name and isinstance(key, str) and '::' not in key:
                        candidate_name = key
                    if candidate_name:
                        resolved = name_to_id.get(candidate_name)
                if resolved and resolved != getattr(current_layer, 'id', lambda: None)():
                    resolved_layer_ids.append(resolved)
        except Exception as e:
            logger.debug(f"Could not resolve favorite target layers: {e}")

        # --- 2. Tick the layers_to_filter combobox ---
        try:
            layers_widget = dw.widgets.get("FILTERING", {}).get("LAYERS_TO_FILTER", {}).get("WIDGET")
            if layers_widget is not None and resolved_layer_ids:
                resolved_set = set(resolved_layer_ids)
                for i in range(layers_widget.count()):
                    data = layers_widget.itemData(i, Qt.ItemDataRole.UserRole)
                    lid = data.get("layer_id") if isinstance(data, dict) else data
                    state = Qt.CheckState.Checked if lid in resolved_set else Qt.CheckState.Unchecked
                    layers_widget.model().item(i).setCheckState(state)
                logger.info(f"  ✓ Favorite restore: ticked {len(resolved_set)} target layer(s)")
        except Exception as e:
            logger.debug(f"Could not tick layers_to_filter: {e}")

        # --- 3. Tick the HAS_LAYERS_TO_FILTER button ---
        try:
            has_layers_btn = getattr(dw, 'pushButton_checkable_filtering_layers_to_filter', None)
            if has_layers_btn is not None:
                has_layers_btn.setChecked(bool(resolved_layer_ids))
        except Exception as e:
            logger.debug(f"Could not toggle HAS_LAYERS_TO_FILTER: {e}")

        # --- 4. Tick the HAS_GEOMETRIC_PREDICATES button + propagate predicates ---
        #
        # FIX 2026-04-23: previously only the push-button was toggled, so the
        # combobox items came from whatever QGIS had persisted at the project
        # level — typically out-of-sync with the favorite. We now drive both
        # widgets from the favorite's ``geometric_predicates`` list so
        # ``sync_ui_to_project_layers`` / task_builder see a consistent state.
        if predicate_explicit:
            try:
                combo_widget = getattr(dw, 'comboBox_filtering_geometric_predicates', None)
                if combo_widget is not None and hasattr(combo_widget, 'setCheckedItems'):
                    combo_widget.setCheckedItems(predicate_list)
            except Exception as e:
                logger.debug(f"Could not set checkedItems on geometric_predicates combobox: {e}")

            try:
                has_pred_btn = getattr(dw, 'pushButton_checkable_filtering_geometric_predicates', None)
                if has_pred_btn is not None:
                    has_pred_btn.setChecked(bool(has_predicates_flag))
            except Exception as e:
                logger.debug(f"Could not toggle HAS_GEOMETRIC_PREDICATES: {e}")
        else:
            logger.info(
                "  ↪ Favorite carries no predicate info — leaving live "
                "geometric_predicates widgets untouched."
            )

        # --- 5. Tick the HAS_BUFFER_VALUE button ---
        # FIX 2026-04-21: the spinbox value is set in _restore_spatial_config,
        # but sync_ui_to_project_layers reads has_buffer_value from the
        # pushButton_checkable_filtering_buffer_value toggle state, not from
        # the spinbox. Without this, a favorite with buffer_value=2.0
        # restored as expected in the spinbox but has_buffer_value stayed
        # False — meaning the buffer was silently ignored in the filter.
        try:
            has_buffer_btn = getattr(dw, 'pushButton_checkable_filtering_buffer_value', None)
            if has_buffer_btn is not None:
                wants_buffer = buffer_value is not None and float(buffer_value) != 0.0
                has_buffer_btn.setChecked(bool(wants_buffer))
        except (AttributeError, TypeError, ValueError) as e:
            logger.debug(f"Could not toggle HAS_BUFFER_VALUE: {e}")

        # --- 6. Persist restored state into PROJECT_LAYERS so sync_ui_to_project_layers sees it ---
        #
        # FIX 2026-04-23: write to the canonical keys (has_geometric_predicates
        # + geometric_predicates list) that task_builder + filtering orchestrator
        # actually read. The previous ``filtering_props["predicates"] = dict``
        # write was dead: nothing in the task pipeline ever reads it.
        if layer_props is not None:
            filtering_props = layer_props.setdefault("filtering", {})
            filtering_props["has_layers_to_filter"] = bool(resolved_layer_ids)
            filtering_props["layers_to_filter"] = resolved_layer_ids
            if predicate_explicit:
                filtering_props["has_geometric_predicates"] = bool(has_predicates_flag)
                filtering_props["geometric_predicates"] = list(predicate_list)
            if buffer_value is not None:
                filtering_props["has_buffer_value"] = float(buffer_value) != 0.0
                filtering_props["buffer_value"] = float(buffer_value)
            logger.debug(
                f"Favorite restore persisted into PROJECT_LAYERS[{current_layer.id()}]: "
                f"layers={len(resolved_layer_ids)}, "
                f"geometric_predicates={predicate_list} "
                f"(has_geometric_predicates={bool(has_predicates_flag)})"
            )

    @staticmethod
    def _exact_filtered_feature_count(layer) -> int:
        """Count features matching the layer's current subsetString exactly.

        ``QgsVectorLayer.featureCount()`` is fast but returns an estimate on
        PostgreSQL (pulled from ``pg_class.reltuples``). For EXISTS subsets
        with intersect predicates the estimate often collapses to 1 even
        when the real cursor returns hundreds of rows, so the favorites
        manager would display ``1`` everywhere. Iterate the filtered cursor
        with no attributes / no geometry — this is an indexed COUNT-like
        scan that respects ``subsetString`` and stays cheap.

        Falls back to ``layer.featureCount()`` if anything goes wrong
        (invalid layer, provider that doesn't honor NoGeometry, …).
        """
        if layer is None:
            return 0
        try:
            if not layer.isValid():
                return 0
        except (RuntimeError, AttributeError):
            return 0

        try:
            from qgis.core import QgsFeatureRequest
            request = QgsFeatureRequest()
            try:
                request.setNoAttributes()
            except (AttributeError, TypeError):
                pass
            try:
                request.setFlags(QgsFeatureRequest.NoGeometry)
            except (AttributeError, TypeError):
                pass
            count = 0
            for _ in layer.getFeatures(request):
                count += 1
            return count
        except Exception as e:
            logger.debug(f"_exact_filtered_feature_count fallback for '{getattr(layer, 'name', lambda: '?')()}': {e}")
            try:
                fallback = layer.featureCount()
                return fallback if fallback is not None and fallback >= 0 else 0
            except Exception:
                return 0

    @staticmethod
    def _layer_signature_for(layer: Any) -> str:
        """Build a project-portable signature for a ``QgsMapLayer``.

        Delegates to :class:`LayerSignature` (domain) so the provider
        parsing rules live in a single module — this method is kept as
        a controller-side shortcut because the controller's static
        callsites read more naturally as ``self._layer_signature_for(...)``.
        """
        from ...core.domain.layer_signature import LayerSignature
        return LayerSignature.compute(layer)

    def _backfill_legacy_predicate_default(self, favorite: 'FilterFavorite') -> bool:
        """Heal pre-fix favorites that lack geometric_predicates in spatial_config.

        Favorites saved before commit 10d35be1 captured nothing for the
        predicate combobox even when the user had ``Intersect`` ticked.
        On apply, the post-fix restore would push ``setCheckedItems([])``
        and clear the live selection. We default such favorites to
        ``["Intersect"]`` (the most common case, and the predicate the
        already-baked ``remote_layers`` SQL was generated against) and
        persist the patched spatial_config so the heal is one-shot.

        Args:
            favorite: Favorite to patch in place.

        Returns:
            True when the favorite was patched and persisted.
        """
        if not favorite or not getattr(favorite, 'remote_layers', None):
            return False

        spatial_config = dict(favorite.spatial_config or {})
        if 'geometric_predicates' in spatial_config or 'has_geometric_predicates' in spatial_config:
            return False

        spatial_config['geometric_predicates'] = ['Intersect']
        spatial_config['has_geometric_predicates'] = True

        favorite.spatial_config = spatial_config

        persisted = False
        try:
            if self._favorites_manager and hasattr(self._favorites_manager, 'update_favorite'):
                persisted = bool(self._favorites_manager.update_favorite(
                    favorite.id,
                    bump_updated_at=False,
                    spatial_config=spatial_config,
                ))
        except Exception as exc:
            logger.debug(f"Could not persist legacy-predicate backfill: {exc}")

        logger.info(
            f"Favorite '{favorite.name}': backfilled missing geometric_predicates "
            f"with default ['Intersect'] (persisted={persisted})"
        )
        self._show_warning(self.tr(
            "Favorite '{0}' was missing predicate info — defaulting to 'Intersect'. "
            "Re-save it after adjusting if you need a different predicate."
        ).format(favorite.name))
        return True

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

        if hasattr(self._favorites_manager, 'get_global_favorites'):
            return self._favorites_manager.get_global_favorites()

        return []

    def _apply_global_favorite(self, favorite_id: str) -> bool:
        """Apply a global favorite."""
        if not self._favorites_manager:
            return False

        # First, import the global favorite to the current project
        if hasattr(self._favorites_manager, 'import_global_to_project'):
            new_id = self._favorites_manager.import_global_to_project(favorite_id)
            if new_id:
                # Then apply the newly imported favorite
                self.update_indicator()
                return self.apply_favorite(new_id)

        return False

    def _copy_to_global(self, favorite_id: str) -> bool:
        """Copy a favorite to global favorites."""
        if not self._favorites_manager:
            return False

        if hasattr(self._favorites_manager, 'copy_to_global'):
            new_id = self._favorites_manager.copy_to_global(favorite_id)
            if new_id:
                self._show_success(self.tr("Favorite copied to global favorites"))
                return True

        self._show_warning(self.tr("Failed to copy to global favorites"))
        return False

    def _show_global_favorites_dialog(self) -> None:
        """Show dialog for managing global favorites."""
        # For now, show a message - full dialog can be added later
        global_count = len(self._get_global_favorites())
        QMessageBox.information(
            self.dockwidget,
            self.tr("Global Favorites"),
            self.tr("{0} global favorite(s) available.\n\n"
                     "Global favorites are shared across all projects.").format(global_count)
        )

    def _backup_to_project(self) -> None:
        """Backup favorites to the QGIS project file."""
        if not self._favorites_manager:
            return

        if hasattr(self._favorites_manager, 'save_to_project_file'):
            from qgis.core import QgsProject
            success = self._favorites_manager.save_to_project_file(QgsProject.instance())
            if success:
                self._show_success(self.tr("Saved {0} favorite(s) to project file").format(self.count))
            else:
                self._show_warning(self.tr("Save failed"))

    def _restore_from_project(self) -> None:
        """Restore favorites from the QGIS project file."""
        if not self._favorites_manager:
            return

        if hasattr(self._favorites_manager, 'restore_from_project_file'):
            from qgis.core import QgsProject
            count = self._favorites_manager.restore_from_project_file(QgsProject.instance())
            if count > 0:
                self.update_indicator()
                self._show_success(self.tr("Restored {0} favorite(s) from project file").format(count))
            else:
                self._show_warning(self.tr("No favorites to restore found in project"))

    def _cleanup_orphan_projects(self) -> None:
        """Clean up orphan projects from the database."""
        try:
            from ...core.services.favorites_migration_service import FavoritesMigrationService
            from ...config.config import ENV_VARS
            import os

            # MED-1 fix: guard against an uninitialized ENV_VARS — without this
            # we'd build '/filterMate_db.sqlite' on Linux (filesystem root) or
            # a Windows-drive-free path, then silently hit a bogus location.
            plugin_dir = ENV_VARS.get("PLUGIN_CONFIG_DIRECTORY", "") or ""
            if not plugin_dir:
                self._show_warning(self.tr(
                    "FilterMate config directory is not initialized yet — "
                    "open a QGIS project with FilterMate first."
                ))
                return
            db_path = os.path.normpath(
                os.path.join(plugin_dir, 'filterMate_db.sqlite')
            )

            migration_service = FavoritesMigrationService(db_path)
            deleted_count, deleted_ids = migration_service.cleanup_orphan_projects()

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
        try:
            from ...core.services.favorites_migration_service import FavoritesMigrationService
            from ...config.config import ENV_VARS
            import os

            # MED-1 fix: guard against an uninitialized ENV_VARS — without this
            # we'd build '/filterMate_db.sqlite' on Linux (filesystem root) or
            # a Windows-drive-free path, then silently hit a bogus location.
            plugin_dir = ENV_VARS.get("PLUGIN_CONFIG_DIRECTORY", "") or ""
            if not plugin_dir:
                self._show_warning(self.tr(
                    "FilterMate config directory is not initialized yet — "
                    "open a QGIS project with FilterMate first."
                ))
                return
            db_path = os.path.normpath(
                os.path.join(plugin_dir, 'filterMate_db.sqlite')
            )

            migration_service = FavoritesMigrationService(db_path)
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

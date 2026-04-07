# -*- coding: utf-8 -*-
"""
ConfigModelManager - Extracted from filter_mate_dockwidget.py

v5.0 Phase 2 P2-2 E2: Extract configuration model management
from God Class (7,029 lines).

Manages:
    - Configuration JSON model creation and lifecycle
    - Config change tracking (pending changes)
    - Config model signal connections (itemChanged)
    - Config view setup (SearchableJsonView / JsonView)
    - Reload button and plugin reload
    - OK/Cancel button handling for config panel

Author: FilterMate Team
Created: February 2026
"""

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from filter_mate_dockwidget import FilterMateDockWidget

logger = logging.getLogger(__name__)


class ConfigModelManager:
    """
    Manages the configuration model, view, and persistence for FilterMate.

    Extracted from FilterMateDockWidget to reduce God Class complexity.

    Args:
        dockwidget: Reference to FilterMateDockWidget instance.
    """

    def __init__(self, dockwidget: 'FilterMateDockWidget'):
        self.dockwidget = dockwidget
        logger.debug("ConfigModelManager initialized")

    # ========================================
    # CONFIG CHANGE TRACKING
    # ========================================

    def data_changed_configuration_model(self, input_data=None):
        """Track configuration changes and apply live-preview changes immediately.

        Delegates to ConfigController for change tracking.
        Also applies LANGUAGE changes immediately (live preview) for instant feedback.
        """
        dw = self.dockwidget
        if dw._controller_integration:
            dw._controller_integration.delegate_config_data_changed(input_data)

        # Live-apply language change immediately (don't wait for OK)
        if input_data is not None:
            self._try_live_language_change(input_data)

    def _try_live_language_change(self, item):
        """If the changed item is the LANGUAGE setting, apply it immediately."""
        from qgis.PyQt.QtCore import Qt
        try:
            # Check if this item's key (column 0 sibling) is LANGUAGE
            index = item.index()
            model = self.dockwidget.config_view.model
            key_item = model.itemFromIndex(index.siblingAtColumn(0))
            if not key_item:
                return
            key_name = key_item.data(Qt.ItemDataRole.DisplayRole)
            if key_name != 'LANGUAGE':
                return

            # Extract locale from the changed value item
            value_data = item.data(Qt.ItemDataRole.UserRole)
            new_locale = None
            if isinstance(value_data, dict) and 'value' in value_data:
                new_locale = value_data['value']
            elif isinstance(value_data, str):
                new_locale = value_data

            if not new_locale:
                return

            logger.info(f"Live language change: {new_locale}")

            from qgis.utils import plugins
            plugin = plugins.get('filter_mate')
            if plugin and hasattr(plugin, 'reload_translator'):
                plugin.reload_translator(new_locale)
                if hasattr(plugin, 'retranslate_actions'):
                    plugin.retranslate_actions()
                if hasattr(self.dockwidget, 'retranslate_all_ui'):
                    self.dockwidget.retranslate_all_ui()
                logger.info(f"Live language change applied: {new_locale}")

                # Also save to disk immediately so it persists on restart
                self.save_configuration_model()

        except Exception as e:
            logger.warning(f"_try_live_language_change failed: {e}")

    def apply_pending_config_changes(self):
        """Apply all pending configuration changes when OK button is clicked.

        Delegates to ConfigController. The controller handles button state,
        saving, and clearing pending changes.
        """
        dw = self.dockwidget
        if dw._controller_integration:
            dw._controller_integration.delegate_config_apply_pending_changes()

    def cancel_pending_config_changes(self):
        """Cancel pending configuration changes.

        Delegates to ConfigController which handles model reload,
        signal reconnection, and state cleanup.
        """
        dw = self.dockwidget
        if dw._controller_integration:
            dw._controller_integration.delegate_config_cancel_pending_changes()

    # ========================================
    # OK / CANCEL BUTTON HANDLERS
    # ========================================

    def on_config_buttonbox_accepted(self):
        """Handle OK button click in config panel."""
        logger.info("Configuration OK button clicked")
        self.apply_pending_config_changes()

    def on_config_buttonbox_rejected(self):
        """Handle Cancel button click in config panel."""
        logger.info("Configuration Cancel button clicked")
        self.cancel_pending_config_changes()

    # ========================================
    # MODEL RELOAD & SAVE
    # ========================================

    def reload_configuration_model(self):
        """Reload config model from CONFIG_DATA and save to file."""
        from ...config.config import ENV_VARS
        dw = self.dockwidget
        if not dw.widgets_initialized:
            return
        try:
            from ...ui.widgets.json_view.model import JsonModel
            dw.config_model = JsonModel(
                data=dw.CONFIG_DATA,
                editable_keys=False,
                editable_values=True,
                plugin_dir=dw.plugin_dir,
            )
            if hasattr(dw, 'config_view') and dw.config_view:
                dw.config_view.setModel(dw.config_model)
                dw.config_view.model = dw.config_model
            # Sync ENV_VARS so all code reading from it sees updated values
            ENV_VARS["CONFIG_DATA"] = dw.CONFIG_DATA
            config_path = ENV_VARS.get(
                'CONFIG_JSON_PATH', dw.plugin_dir + '/config/config.json'
            )
            with open(config_path, 'w') as f:
                f.write(json.dumps(dw.CONFIG_DATA, indent=4))
        except Exception as e:
            logger.error(f"Error reloading configuration model: {e}")

    def save_configuration_model(self):
        """Save current config model to file and sync ENV_VARS."""
        from ...config.config import ENV_VARS
        dw = self.dockwidget
        if not dw.widgets_initialized:
            return
        dw.CONFIG_DATA = dw.config_model.serialize()
        # Sync ENV_VARS so all code reading from it sees updated values
        ENV_VARS["CONFIG_DATA"] = dw.CONFIG_DATA
        config_path = ENV_VARS.get(
            'CONFIG_JSON_PATH', dw.plugin_dir + '/config/config.json'
        )
        with open(config_path, 'w') as f:
            f.write(json.dumps(dw.CONFIG_DATA, indent=4))

    # ========================================
    # SIGNAL MANAGEMENT
    # ========================================

    def disconnect_config_model_signal(self):
        """Disconnect itemChanged signal from config_model.

        Prevents signal accumulation when model is recreated (v4.0.7 FIX).
        """
        dw = self.dockwidget
        try:
            if hasattr(dw, 'config_model') and dw.config_model is not None:
                try:
                    dw.config_model.itemChanged.disconnect(
                        dw.data_changed_configuration_model
                    )
                    logger.debug("Config model itemChanged signal disconnected")
                except (TypeError, RuntimeError):
                    # Signal was not connected or already disconnected
                    pass
        except Exception as e:
            logger.debug(f"Could not disconnect config_model signal: {e}")

    def connect_config_model_signal(self):
        """Connect itemChanged signal to config_model.

        Centralized connection method for consistency (v4.0.7 FIX).
        """
        dw = self.dockwidget
        try:
            if hasattr(dw, 'config_model') and dw.config_model is not None:
                dw.config_model.itemChanged.connect(
                    dw.data_changed_configuration_model
                )
                logger.debug("Config model itemChanged signal connected")
        except Exception as e:
            logger.error(f"Could not connect config_model signal: {e}")

    # ========================================
    # MODEL & VIEW SETUP
    # ========================================

    def manage_configuration_model(self):
        """Setup config model, view, and signals.

        Creates JsonModel from CONFIG_DATA, sets up SearchableJsonView
        (with fallback to standard JsonView), connects signals,
        and adds reload button.
        """
        dw = self.dockwidget
        try:
            # Disconnect any existing signal first
            self.disconnect_config_model_signal()

            # Reload CONFIG_DATA from disk to pick up any new entries (e.g. new languages)
            import os
            config_path = os.path.join(dw.plugin_dir, 'config', 'config.json')
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    fresh_config = json.load(f)
                dw.CONFIG_DATA = fresh_config
                try:
                    from ...config.config import ENV_VARS
                    ENV_VARS["CONFIG_DATA"] = fresh_config
                except Exception:
                    pass
                logger.info(f"Config reloaded from {config_path}")
            except Exception as e:
                logger.warning(f"Could not reload config from disk: {e}")

            from ...ui.widgets.json_view.model import JsonModel
            dw.config_model = JsonModel(
                data=dw.CONFIG_DATA,
                editable_keys=False,
                editable_values=True,
                plugin_dir=dw.plugin_dir,
            )

            # Use SearchableJsonView with integrated search bar
            try:
                from ui.widgets.json_view import SearchableJsonView
                dw.config_view_container = SearchableJsonView(
                    dw.config_model, dw.plugin_dir
                )
                dw.config_view = dw.config_view_container.json_view
                dw.CONFIGURATION.layout().insertWidget(0, dw.config_view_container)
                dw.config_view_container.setAnimated(True)
                dw.config_view_container.setEnabled(True)
                dw.config_view_container.show()
                logger.debug("Using SearchableJsonView with search bar")
            except ImportError:
                # Fallback to standard JsonView
                from ...ui.widgets.json_view.view import JsonView
                dw.config_view = JsonView(dw.config_model, dw.plugin_dir)
                dw.config_view_container = None
                dw.CONFIGURATION.layout().insertWidget(0, dw.config_view)
                dw.config_view.setAnimated(True)
                dw.config_view.setEnabled(True)
                dw.config_view.show()
                logger.debug(
                    "Using standard JsonView (SearchableJsonView not available)"
                )

            # Connect signal using centralized method
            self.connect_config_model_signal()

            # Hide OK/Cancel — config changes are applied live
            if hasattr(dw, 'buttonBox'):
                dw.buttonBox.hide()
        except Exception as e:
            logger.error(f"Error creating configuration model: {e}")


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
        self._language_change_pending = False
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
        """Apply language change live: reload translator, retranslate, save.

        Patches CONFIG_DATA directly (no serialize) to avoid psycopg2.connection
        leaking into JSON. Defers the save to next event loop tick so it doesn't
        interfere with the delegate's setModelData still in progress.
        No tree rebuild — the tree already shows the correct value from setModelData.
        """
        if self._language_change_pending:
            return

        from qgis.PyQt.QtCore import Qt
        try:
            # Use the item's own model (not config_view.model which may be a proxy)
            index = item.index()
            if not index.isValid():
                return
            model = index.model()
            if not model or not hasattr(model, 'itemFromIndex'):
                return
            key_item = model.itemFromIndex(index.siblingAtColumn(0))
            if not key_item:
                return
            key_name = key_item.data(Qt.ItemDataRole.DisplayRole)
            if key_name != 'LANGUAGE':
                return

            value_data = item.data(Qt.ItemDataRole.UserRole)
            new_locale = None
            if isinstance(value_data, dict) and 'value' in value_data:
                new_locale = value_data['value']
            elif isinstance(value_data, str):
                new_locale = value_data

            if not new_locale:
                return

            # Ignore if this matches the currently active translator locale
            # (spurious itemChanged when editor opens / setEditorData runs)
            from qgis.utils import plugins
            plugin = plugins.get('filter_mate')
            active_locale = getattr(plugin, '_current_locale', None) if plugin else None
            if new_locale == active_locale:
                return

            self._language_change_pending = True
            self._pending_locale = new_locale
            logger.info(f"Live language change: {active_locale} -> {new_locale}")

            # Defer everything to next event loop tick
            # (setModelData is still in progress — retranslateUi during it can cause issues)
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(0, self._deferred_language_apply)

        except Exception as e:
            self._language_change_pending = False
            logger.warning(f"_try_live_language_change failed: {e}")

    def _deferred_language_apply(self):
        """Apply language change: reload translator, retranslate UI, save to disk.

        Runs in the next event loop tick after setModelData has completed.
        Patches CONFIG_DATA directly (no full serialize) to avoid
        psycopg2.connection leak from CURRENT_PROJECT.
        """
        try:
            new_locale = getattr(self, '_pending_locale', None)
            dw = self.dockwidget
            if not new_locale or not hasattr(dw, 'CONFIG_DATA'):
                return

            # 1) Reload translator + retranslate UI
            from qgis.utils import plugins
            plugin = plugins.get('filter_mate')
            if plugin and hasattr(plugin, 'reload_translator'):
                try:
                    plugin.reload_translator(new_locale)
                    logger.info(f"reload_translator OK for {new_locale}")
                except Exception as tr_err:
                    logger.error(f"reload_translator FAILED: {tr_err}")
                try:
                    if hasattr(plugin, 'retranslate_actions'):
                        plugin.retranslate_actions()
                    if hasattr(dw, 'retranslate_all_ui'):
                        dw.retranslate_all_ui()
                except Exception as rt_err:
                    logger.error(f"retranslate FAILED: {rt_err}")
            else:
                logger.warning("SKIP: plugin not found or no reload_translator")

            # 2) Patch CONFIG_DATA in place
            app = dw.CONFIG_DATA.get('APP')
            if isinstance(app, dict):
                dock = app.get('DOCKWIDGET')
                if isinstance(dock, dict):
                    lang = dock.get('LANGUAGE')
                    if isinstance(lang, dict):
                        lang['value'] = new_locale
                    else:
                        dock['LANGUAGE'] = {'value': new_locale}

            # 3) Sync ENV_VARS + save to disk
            from ...config.config import ENV_VARS
            ENV_VARS["CONFIG_DATA"] = dw.CONFIG_DATA
            config_path = ENV_VARS.get(
                'CONFIG_JSON_PATH', dw.plugin_dir + '/config/config.json')
            clean = self._sanitize_for_json(dw.CONFIG_DATA)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(clean, f, indent=4, ensure_ascii=False)
            logger.info(f"Language saved to disk: {new_locale}")

        except Exception as e:
            logger.error(f"_deferred_language_apply failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self._language_change_pending = False
            self._pending_locale = None

    def _rebuild_config_tree_after_language_change(self):
        """Rebuild the config tree model so tr()-based strings use the new locale.

        Disconnects itemChanged before rebuilding to avoid infinite recursion,
        then reconnects afterwards.
        """
        dw = self.dockwidget
        try:
            self.disconnect_config_model_signal()

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

            self.connect_config_model_signal()
            logger.info("Config tree rebuilt after language change")
        except Exception as e:
            logger.warning(f"_rebuild_config_tree_after_language_change failed: {e}")
            # Ensure signal is reconnected even on failure
            self.connect_config_model_signal()

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

    @staticmethod
    def _sanitize_for_json(obj):
        """Recursively remove non-JSON-serializable values from a data structure.

        Returns a clean copy safe for json.dumps(). Drops any value that is not
        a JSON primitive, dict, or list (e.g. Qt objects, database connections).
        """
        if isinstance(obj, dict):
            return {
                k: ConfigModelManager._sanitize_for_json(v)
                for k, v in obj.items()
                if isinstance(v, (dict, list, str, int, float, bool, type(None)))
            }
        if isinstance(obj, list):
            return [
                ConfigModelManager._sanitize_for_json(v)
                for v in obj
                if isinstance(v, (dict, list, str, int, float, bool, type(None)))
            ]
        return obj

    def save_configuration_model(self):
        """Save current config model to file and sync ENV_VARS."""
        from ...config.config import ENV_VARS
        dw = self.dockwidget
        if not dw.widgets_initialized:
            return
        serialized = dw.config_model.serialize()
        # Strip any non-JSON objects that leaked from Qt model data
        serialized = self._sanitize_for_json(serialized)

        # Validate critical path before accepting serialized data
        if isinstance(serialized, dict) and 'APP' in serialized:
            # FIX 2026-04-27: mutate in place rather than rebinding the
            # attribute. ``dw.CONFIG_DATA`` is shared with the registry's
            # seeded extension slices and ``app.CONFIG_DATA``; rebinding
            # orphans those references and the next persist drops keys
            # that only existed on the orphaned dict.
            if isinstance(dw.CONFIG_DATA, dict):
                dw.CONFIG_DATA.clear()
                dw.CONFIG_DATA.update(serialized)
            else:
                dw.CONFIG_DATA = serialized
        else:
            # serialize produced wrong keys (e.g. _display_name as key)
            # — skip overwriting CONFIG_DATA, just patch from model
            logger.warning(
                f"save_configuration_model: serialize produced unexpected "
                f"top-level keys {list(serialized.keys()) if isinstance(serialized, dict) else type(serialized)}, "
                f"keeping existing CONFIG_DATA"
            )

        # Sync ENV_VARS so all code reading from it sees updated values.
        # Mutate in place when ENV_VARS already holds a dict so other live
        # references stay aligned.
        live_env = ENV_VARS.get("CONFIG_DATA")
        if isinstance(live_env, dict) and live_env is not dw.CONFIG_DATA:
            live_env.clear()
            live_env.update(dw.CONFIG_DATA)
        else:
            ENV_VARS["CONFIG_DATA"] = dw.CONFIG_DATA
        config_path = ENV_VARS.get(
            'CONFIG_JSON_PATH', dw.plugin_dir + '/config/config.json'
        )
        # Sanitize again before writing (CONFIG_DATA may have runtime objects)
        clean = self._sanitize_for_json(dw.CONFIG_DATA)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(clean, f, indent=4, ensure_ascii=False)

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

            # Reload CONFIG_DATA from disk to pick up any new entries
            # (new extensions seeded by the registry, language packs, …).
            #
            # FIX 2026-04-27: previously read from
            # ``dw.plugin_dir/config/config.json`` — that's the **plugin
            # template** baked into the .zip, not the runtime user config
            # under the QGIS profile. The template ships with a fresh
            # `EXTENSIONS: {qfieldcloud: {...}}` only, so every time the
            # user opened the Configuration panel this would overwrite
            # ``dw.CONFIG_DATA`` (and ``ENV_VARS["CONFIG_DATA"]``) with the
            # template, dropping any extension the registry had seeded
            # in the runtime config (favorites_sharing in particular).
            # The subsequent ``save_configuration_model`` then wrote this
            # stripped state back to the runtime config — making the
            # extension permanently invisible until manually re-seeded.
            #
            # Now: prefer ``CONFIG_JSON_PATH`` from ``ENV_VARS`` (the
            # active runtime path) and only fall back to the template
            # when the env hasn't been initialised yet.
            import os
            try:
                from ...config.config import ENV_VARS
            except Exception:
                ENV_VARS = {}
            config_path = ENV_VARS.get("CONFIG_JSON_PATH") or os.path.join(
                dw.plugin_dir, 'config', 'config.json'
            )
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    fresh_config = json.load(f)
                # Mutate dw.CONFIG_DATA in place when possible so other
                # holders of the live reference (registry seed slices,
                # app.CONFIG_DATA) are not orphaned.
                if isinstance(dw.CONFIG_DATA, dict):
                    dw.CONFIG_DATA.clear()
                    dw.CONFIG_DATA.update(fresh_config)
                else:
                    dw.CONFIG_DATA = fresh_config
                # Keep ENV_VARS pointing at the same live dict.
                live = ENV_VARS.get("CONFIG_DATA")
                if isinstance(live, dict) and live is not dw.CONFIG_DATA:
                    live.clear()
                    live.update(fresh_config)
                else:
                    ENV_VARS["CONFIG_DATA"] = dw.CONFIG_DATA
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

            # Hide OK/Cancel — all changes are applied live
            if hasattr(dw, 'buttonBox'):
                dw.buttonBox.hide()
        except Exception as e:
            logger.error(f"Error creating configuration model: {e}")


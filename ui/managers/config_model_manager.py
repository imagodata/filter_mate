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

from ...infrastructure.utils.atomic_io import atomic_json_write

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
            from ...core.domain.plugin_package import PLUGIN_PACKAGE
            plugin = plugins.get(PLUGIN_PACKAGE)
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
            from ...core.domain.plugin_package import PLUGIN_PACKAGE
            plugin = plugins.get(PLUGIN_PACKAGE)
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
            atomic_json_write(config_path, clean, indent=4)
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
            container = getattr(dw, 'config_view_container', None)
            if container is not None:
                container.model = dw.config_model  # its search reads this model, not the view's
            elif hasattr(dw, 'config_view') and dw.config_view:
                dw.config_view.setModel(dw.config_model)
                dw.config_view.model = dw.config_model
            # Sync ENV_VARS so all code reading from it sees updated values
            ENV_VARS["CONFIG_DATA"] = dw.CONFIG_DATA
            config_path = ENV_VARS.get(
                'CONFIG_JSON_PATH', dw.plugin_dir + '/config/config.json'
            )
            atomic_json_write(config_path, self._sanitize_for_json(dw.CONFIG_DATA), indent=4)
        except Exception as e:
            logger.error(f"Error reloading configuration model: {e}")

    def apply_settings(self, values):
        """Settings changed by the agent (``{"APP.OPTIONS.X.y": value}``, checked by core.agent.settings_reference),
        applied as the user edits them in the configuration tree.

        Each setting the tree shows gets its new value the way the editor of its row sets it (ChoicesType /
        ConfigValueType.setModelData: the text shown, then the value): the tree emits itemChanged and the usual
        handlers run, the theme, the profile, the action bar, the language, the layer kinds and the timers follow,
        and the configuration is saved, exactly as for the user. A setting missing from the tree (a leaf the user's
        config.json lacks) is written in CONFIG_DATA from the defaults, the tree is built again and saved.

        All or none: when an edit fails, CONFIG_DATA, the tree and the file go back to what they were. Returns the
        paths applied.
        """
        import copy
        from ...config.config import ENV_VARS
        dw = self.dockwidget
        if not getattr(dw, 'widgets_initialized', False) or not isinstance(dw.CONFIG_DATA, dict) \
                or getattr(dw, 'config_model', None) is None:
            raise RuntimeError("the FilterMate panel is not ready")
        if 'APP.DOCKWIDGET.LANGUAGE' in values and self._language_change_pending:
            # The tree skips a change while one is pending, and the pending one would then be saved over it.
            raise RuntimeError("a change of language is under way: try again in a moment")
        saved = copy.deepcopy(dw.CONFIG_DATA)
        try:
            missing = {path: value for path, value in values.items()
                       if not self._editable_leaf(self._value_item(dw.config_model, path.split(".")))}
            if missing:
                self._add_missing_leaves(missing, ENV_VARS)
            applied = []
            for path, value in values.items():
                item = self._value_item(dw.config_model, path.split("."))
                if not self._editable_leaf(item):
                    raise RuntimeError(f"{path} is not in the configuration tree")
                if path in missing:
                    self.data_changed_configuration_model(item)  # already holds its value: run the handlers
                else:
                    self._edit_leaf(item, value)  # itemChanged: the handlers of an edit in the tree
                applied.append(path)
            return applied
        except Exception as exc:  # all or none: the configuration in use goes back to what it was
            logger.warning(f"Settings of the agent not applied: {exc}")
            kinds_before, targets_before = self._layer_kind_flags(), self._target_option_flags()
            dw.CONFIG_DATA.clear()
            dw.CONFIG_DATA.update(saved)
            self._sync_env(ENV_VARS)
            try:
                self._rebuild_tree()
                self._write_config(ENV_VARS)
                self._realign_layer_kinds(kinds_before)
                self._realign_target_options(targets_before)
            except Exception:
                logger.exception("Configuration not put back after a failed change")
            raise RuntimeError(f"the settings could not be applied ({exc})") from exc

    @staticmethod
    def _editable_leaf(item):
        """A value item of the tree holding a setting (its value in a dict with 'value'), as the editors expect."""
        if item is None:
            return False
        from qgis.PyQt.QtCore import Qt
        data = item.data(Qt.ItemDataRole.UserRole)
        return isinstance(data, dict) and 'value' in data

    @staticmethod
    def _edit_leaf(item, value):
        """What the editor of the row does (datatypes.ChoicesType / ConfigValueType.setModelData)."""
        from qgis.PyQt.QtCore import Qt
        data = dict(item.data(Qt.ItemDataRole.UserRole))
        data['value'] = value
        display = 'true' if value is True else 'false' if value is False else str(value)
        choices, labels = data.get('choices'), data.get('available_translations')
        if isinstance(choices, list) and labels and value in choices:  # LANGUAGE shows names, not codes
            index = choices.index(value)
            if len(labels) == len(choices) - 1:
                display = 'auto' if index == 0 else labels[index - 1]
            elif len(labels) == len(choices):
                display = labels[index]
        item.setData(display, Qt.ItemDataRole.DisplayRole)
        item.setData(data, Qt.ItemDataRole.UserRole)

    def _add_missing_leaves(self, values, ENV_VARS):
        """Leaves the tree does not show: written in CONFIG_DATA from the defaults, the tree built again, saved."""
        from ...core.agent.settings_reference import load_default, set_leaf
        dw = self.dockwidget
        default = load_default()
        for path, value in values.items():
            set_leaf(dw.CONFIG_DATA, path, value, default)
        self._sync_env(ENV_VARS)
        self._rebuild_tree()
        self._write_config(ENV_VARS)

    def _write_config(self, ENV_VARS):
        dw = self.dockwidget
        config_path = ENV_VARS.get('CONFIG_JSON_PATH', dw.plugin_dir + '/config/config.json')
        atomic_json_write(config_path, self._sanitize_for_json(dw.CONFIG_DATA), indent=4)

    def _sync_env(self, ENV_VARS):
        """ENV_VARS follows CONFIG_DATA, the same dict when it can (other holders keep their reference)."""
        dw = self.dockwidget
        live = ENV_VARS.get("CONFIG_DATA")
        if isinstance(live, dict) and live is not dw.CONFIG_DATA:
            live.clear()
            live.update(dw.CONFIG_DATA)
        else:
            ENV_VARS["CONFIG_DATA"] = dw.CONFIG_DATA

    def _rebuild_tree(self):
        """The configuration tree built again from CONFIG_DATA, its signal off meanwhile."""
        dw = self.dockwidget
        self.disconnect_config_model_signal()
        try:
            from ...ui.widgets.json_view.model import JsonModel
            dw.config_model = JsonModel(data=dw.CONFIG_DATA, editable_keys=False, editable_values=True,
                                        plugin_dir=dw.plugin_dir)
            container = getattr(dw, 'config_view_container', None)
            if container is not None:
                container.model = dw.config_model  # sets the model of its view too
            elif getattr(dw, 'config_view', None) is not None:
                dw.config_view.setModel(dw.config_model)
                dw.config_view.model = dw.config_model
        finally:
            self.connect_config_model_signal()

    @staticmethod
    def _value_item(model, keys):
        """The value item (column 1) of the leaf ``keys`` in the configuration tree, None when absent.

        A section shown under its ``_display_name`` keeps its JSON key in the UserRole of its key item."""
        from qgis.PyQt.QtCore import Qt
        parent = model.invisibleRootItem()
        for depth, key in enumerate(keys):
            found = None
            for row in range(parent.rowCount()):
                key_item = parent.child(row, 0)
                if key_item is None:
                    continue
                original = key_item.data(Qt.ItemDataRole.UserRole)
                name = original if isinstance(original, str) and original else key_item.data(Qt.ItemDataRole.DisplayRole)
                if name == key:
                    found = (key_item, parent.child(row, 1))
                    break
            if found is None:
                return None
            if depth == len(keys) - 1:
                return found[1]
            parent = found[0]
        return None

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
        atomic_json_write(config_path, clean, indent=4)

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

    @staticmethod
    def _layer_kind_flags():
        """(point clouds usable, rasters usable) as the options say now, None when unreadable."""
        try:
            from ...adapters.qgis.point_cloud_capability import get_point_cloud_layer_type, get_raster_layer_type
            return get_point_cloud_layer_type() is not None, get_raster_layer_type() is not None
        except Exception as e:
            logger.debug(f"Layer kind flags unreadable: {e}")
            return None

    def _realign_layer_kinds(self, before):
        """The configuration read from disk turned rasters / point clouds on or off: register or
        unregister those layers and re-filter the current-layer list (FilterMateApp.apply_layer_kind_options).

        2026-10-18: a reload switching both kinds off left them in the current-layer list while
        the next add_layers task ignored them (« not in PROJECT_LAYERS »).
        """
        after = self._layer_kind_flags()
        if before is None or after is None or after == before:
            return
        dw = self.dockwidget
        app = getattr(dw, 'filter_mate_app', None) or getattr(dw, 'app', None)
        apply_options = getattr(app, 'apply_layer_kind_options', None)
        if callable(apply_options):
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(0, apply_options)
            logger.info(f"Layer kinds changed by the configuration reload (point clouds={after[0]}, rasters={after[1]})")

    @staticmethod
    def _target_option_flags():
        """(rasters, point clouds) listed as targets of a vector source (CROSS_FILTER), None when unreadable."""
        try:
            from ...adapters.qgis.point_cloud_capability import (
                is_vector_source_point_cloud_targets_enabled, is_vector_source_raster_targets_enabled)
            return is_vector_source_raster_targets_enabled(), is_vector_source_point_cloud_targets_enabled()
        except Exception as e:
            logger.debug(f"Target options unreadable: {e}")
            return None

    def _realign_target_options(self, before):
        """The configuration read from disk changed which rasters / point clouds a vector source
        lists as targets: fill the FILTERING targets list again (PropertyController)."""
        after = self._target_option_flags()
        if before is None or after is None or after == before:
            return
        integration = getattr(self.dockwidget, '_controller_integration', None)
        properties = getattr(integration, 'property_controller', None)
        if properties is not None:
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(0, properties.refill_layers_to_filter)
            logger.info(f"Targets of a vector source changed by the configuration reload "
                        f"(rasters={after[0]}, point clouds={after[1]})")

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
                from ...config.config import ENV_VARS, load_migrated_config
            except Exception:
                ENV_VARS = {}
                load_migrated_config = None
            config_path = ENV_VARS.get("CONFIG_JSON_PATH") or os.path.join(
                dw.plugin_dir, 'config', 'config.json'
            )
            kinds_before = self._layer_kind_flags()
            targets_before = self._target_option_flags()
            try:
                # 2026-10-18: migrated like at start (a file without the RASTER /
                # POINT_CLOUD sections turned both layer kinds off here).
                if load_migrated_config is not None:
                    fresh_config = load_migrated_config(config_path)
                    if fresh_config is None:
                        raise ValueError(f"{config_path} unreadable or without APP section")
                else:
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
            self._realign_layer_kinds(kinds_before)
            self._realign_target_options(targets_before)

            from ...ui.widgets.json_view.model import JsonModel
            dw.config_model = JsonModel(
                data=dw.CONFIG_DATA,
                editable_keys=False,
                editable_values=True,
                plugin_dir=dw.plugin_dir,
            )

            # Use SearchableJsonView with integrated search bar
            try:
                from ..widgets.json_view import SearchableJsonView
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

            if hasattr(dw, '_refresh_config_view_theme'):
                try:
                    dw._refresh_config_view_theme()  # plugin theme, not the QGIS palette
                except Exception as e:
                    logger.debug(f"Config view theme not refreshed: {e}")

            # Connect signal using centralized method
            self.connect_config_model_signal()

            # Hide OK/Cancel — all changes are applied live
            if hasattr(dw, 'buttonBox'):
                dw.buttonBox.hide()
        except Exception as e:
            logger.error(f"Error creating configuration model: {e}")

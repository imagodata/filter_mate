# -*- coding: utf-8 -*-
"""
Extension Registry for FilterMate.

Discovers, loads, initializes, and manages extension lifecycle.
Extensions are discovered from the `extensions/` directory by looking
for subpackages that define an `Extension` class inheriting BaseExtension.

Usage:
    registry = get_extension_registry()
    registry.discover_extensions()
    registry.initialize_all(iface)

    # Later, on plugin unload:
    registry.teardown_all()
"""

import importlib
import logging
import os
from typing import Any, Dict, List, Optional

from .base import BaseExtension, ExtensionState

logger = logging.getLogger('FilterMate.Extensions.Registry')

_registry_instance: Optional['ExtensionRegistry'] = None


class ExtensionRegistry:
    """
    Registry for discovering and managing FilterMate extensions.

    Extensions are Python subpackages under `extensions/` that expose
    an `Extension` class inheriting from `BaseExtension`.

    The registry handles the full lifecycle:
        discover → check_dependencies → initialize → create_ui → teardown
    """

    def __init__(self):
        self._extensions: Dict[str, BaseExtension] = {}
        self._load_order: List[str] = []
        self._initialized = False

    @property
    def extensions(self) -> Dict[str, BaseExtension]:
        """All registered extensions (keyed by extension ID)."""
        return dict(self._extensions)

    def discover_extensions(self) -> List[str]:
        """
        Discover extensions in the extensions/ directory.

        Scans for subpackages containing a module with an `Extension` class
        that inherits from BaseExtension.

        Returns:
            List of discovered extension IDs
        """
        extensions_dir = os.path.dirname(os.path.abspath(__file__))
        discovered = []

        config_dirty = False
        for entry in sorted(os.listdir(extensions_dir)):
            entry_path = os.path.join(extensions_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            if entry.startswith(('_', '.')):
                continue
            init_file = os.path.join(entry_path, '__init__.py')
            if not os.path.isfile(init_file):
                continue

            try:
                extension = self._load_extension_module(entry)
                if extension:
                    ext_id = extension.metadata.id
                    self._extensions[ext_id] = extension
                    self._load_order.append(ext_id)
                    discovered.append(ext_id)
                    logger.info(
                        "Discovered extension: %s v%s",
                        extension.metadata.name,
                        extension.metadata.version,
                    )
                    # Auto-seed any schema keys missing from config.json
                    # (non-destructive: existing user values are preserved).
                    try:
                        if extension.seed_default_config():
                            config_dirty = True
                            logger.info(
                                "Seeded missing config keys for extension '%s'",
                                ext_id,
                            )
                    except Exception as seed_err:
                        logger.warning(
                            "Config seeding failed for '%s': %s",
                            ext_id, seed_err,
                        )
            except Exception as e:
                logger.warning("Failed to load extension '%s': %s", entry, e)

        # Persist when something changed. Also persist when discover_extensions
        # inserted *any* new extension namespace (even empty) — callers rely
        # on EXTENSIONS.<ext_id> existing on disk so the Configuration UI
        # enumerates them.
        if config_dirty:
            if self._persist_config():
                logger.info("Extension config persisted to config.json")
            else:
                logger.warning(
                    "Could not persist extension config — %d extension(s) "
                    "may show stale options in the Configuration panel",
                    len(discovered),
                )

        return discovered

    def _load_extension_module(self, package_name: str) -> Optional[BaseExtension]:
        """
        Load an extension from a subpackage.

        Args:
            package_name: Name of the subpackage under extensions/

        Returns:
            Extension instance or None
        """
        module_path = f".extensions.{package_name}"
        try:
            # Import relative to filter_mate package
            module = importlib.import_module(
                module_path, package="filter_mate"
            )
        except ImportError as e:
            logger.debug("Cannot import %s: %s", module_path, e)
            return None

        extension_cls = getattr(module, 'Extension', None)
        if extension_cls is None:
            logger.debug("No 'Extension' class in %s", module_path)
            return None

        if not isinstance(extension_cls, type) or not issubclass(extension_cls, BaseExtension):
            logger.warning(
                "'Extension' in %s does not inherit BaseExtension", module_path
            )
            return None

        return extension_cls()

    def register(self, extension: BaseExtension) -> None:
        """
        Manually register an extension instance.

        Args:
            extension: Extension to register
        """
        ext_id = extension.metadata.id
        if ext_id in self._extensions:
            logger.warning("Extension '%s' already registered, replacing", ext_id)
        self._extensions[ext_id] = extension
        if ext_id not in self._load_order:
            self._load_order.append(ext_id)

    def get_extension(self, ext_id: str) -> Optional[BaseExtension]:
        """
        Get a registered extension by ID.

        Args:
            ext_id: Extension identifier

        Returns:
            Extension instance or None
        """
        return self._extensions.get(ext_id)

    def get_available_extensions(self) -> List[BaseExtension]:
        """Get all extensions whose dependencies are met."""
        return [
            ext for ext in self._extensions.values()
            if ext.is_available()
        ]

    def initialize_all(self, iface: Any) -> Dict[str, bool]:
        """
        Initialize all available extensions.

        Args:
            iface: QGIS interface instance

        Returns:
            Dict mapping extension ID to success status
        """
        results = {}
        for ext_id in self._load_order:
            ext = self._extensions[ext_id]
            results[ext_id] = self._initialize_extension(ext, iface)
        self._initialized = True
        return results

    def _persist_config(self) -> bool:
        """Write ENV_VARS['CONFIG_DATA'] back to config.json (single I/O point)."""
        try:
            from filter_mate.config.config import ENV_VARS
            import json
        except Exception:
            return False
        config_path = ENV_VARS.get("CONFIG_JSON_PATH")
        config_data = ENV_VARS.get("CONFIG_DATA")
        if not config_path or not isinstance(config_data, dict):
            return False
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            return True
        except OSError as exc:
            logger.warning("Could not persist config.json: %s", exc)
            return False

    def _show_missing_deps_message(self, ext: BaseExtension, iface: Any) -> None:
        """Show a message when extension deps are missing, with dismiss option."""
        ext_id = ext.metadata.id

        if ext.is_warning_dismissed():
            return

        try:
            from qgis.PyQt.QtWidgets import QCheckBox, QMessageBox

            deps = ", ".join(ext.metadata.dependencies) if ext.metadata.dependencies else "?"
            msg = QMessageBox(iface.mainWindow())
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle(f"FilterMate — Extension {ext.metadata.name}")
            msg.setText(
                f"L'extension <b>{ext.metadata.name}</b> est désactivée car "
                f"les dépendances requises ne sont pas installées.\n"
            )
            msg.setInformativeText(
                f"Paquets manquants : {deps}\n\n"
                f"Pour l'activer :\n"
                f"  1. Installez : pip install {deps}\n"
                f"  2. Redémarrez QGIS\n\n"
                f"L'extension peut aussi être activée/désactivée dans\n"
                f"config.json → EXTENSIONS → {ext_id} → enabled"
            )

            checkbox = QCheckBox("Ne plus afficher ce message")
            msg.setCheckBox(checkbox)
            msg.exec()

            if checkbox.isChecked():
                ext.dismiss_warning()

        except Exception as e:
            logger.debug("Could not show missing deps message: %s", e)

    def _initialize_extension(self, ext: BaseExtension, iface: Any) -> bool:
        """Initialize a single extension."""
        ext_id = ext.metadata.id
        try:
            # Check config enable/disable
            if not ext.is_enabled():
                logger.info("Extension '%s' disabled in config", ext_id)
                return False

            # Check dependencies
            if not ext.is_available():
                logger.info(
                    "Extension '%s' not available (missing dependencies)",
                    ext_id,
                )
                # Auto-disable in config and notify user
                ext.set_enabled(False)
                self._show_missing_deps_message(ext, iface)
                return False

            ext.initialize(iface)
            ext._set_state(ExtensionState.INITIALIZED)
            logger.info("Extension '%s' initialized", ext_id)
            return True

        except Exception as e:
            ext._set_error(f"Initialization failed: {e}")
            logger.exception("Failed to initialize extension '%s'", ext_id)
            return False

    def create_all_ui(self, toolbar: Any, menu_name: str) -> Dict[str, List[Any]]:
        """
        Create UI for all initialized extensions.

        Args:
            toolbar: QGIS toolbar
            menu_name: Menu name

        Returns:
            Dict mapping extension ID to list of QActions created
        """
        results = {}
        for ext_id in self._load_order:
            ext = self._extensions[ext_id]
            if ext.state != ExtensionState.INITIALIZED:
                continue
            try:
                actions = ext.create_ui(toolbar, menu_name)
                ext._set_state(ExtensionState.UI_CREATED)
                results[ext_id] = actions
            except Exception as e:
                ext._set_error(f"UI creation failed: {e}")
                logger.exception("Failed to create UI for extension '%s'", ext_id)
                results[ext_id] = []
        return results

    def create_all_dockwidget_ui(self, dockwidget: Any) -> Dict[str, List[Any]]:
        """
        Create dockwidget UI for all initialized extensions.

        Called after the FilterMate dockwidget is created and shown,
        allowing extensions to inject buttons/widgets into the dockwidget.

        Args:
            dockwidget: FilterMate dockwidget instance

        Returns:
            Dict mapping extension ID to list of widgets created
        """
        results = {}
        for ext_id in self._load_order:
            ext = self._extensions.get(ext_id)
            if ext is None:
                continue
            if ext.state not in (ExtensionState.INITIALIZED, ExtensionState.UI_CREATED):
                continue
            try:
                widgets = ext.create_dockwidget_ui(dockwidget)
                results[ext_id] = widgets or []
            except Exception as e:
                logger.warning(
                    "Failed to create dockwidget UI for extension '%s': %s",
                    ext_id, e,
                )
                results[ext_id] = []
        return results

    def teardown_all(self) -> None:
        """Teardown all extensions in reverse load order."""
        for ext_id in reversed(self._load_order):
            ext = self._extensions[ext_id]
            if ext.state in (ExtensionState.INITIALIZED, ExtensionState.UI_CREATED):
                try:
                    ext.teardown()
                    ext._set_state(ExtensionState.TORN_DOWN)
                    logger.debug("Extension '%s' torn down", ext_id)
                except Exception as e:
                    logger.warning(
                        "Error tearing down extension '%s': %s", ext_id, e
                    )
        self._extensions.clear()
        self._load_order.clear()
        self._initialized = False

    def notify_project_loaded(self) -> None:
        """Notify all active extensions that a project was loaded."""
        for ext in self._extensions.values():
            if ext.state in (ExtensionState.INITIALIZED, ExtensionState.UI_CREATED):
                try:
                    ext.on_project_loaded()
                except Exception as e:
                    logger.warning(
                        "Extension '%s' project_loaded error: %s",
                        ext.metadata.id, e,
                    )

    def notify_project_closed(self) -> None:
        """Notify all active extensions that a project was closed."""
        for ext in self._extensions.values():
            if ext.state in (ExtensionState.INITIALIZED, ExtensionState.UI_CREATED):
                try:
                    ext.on_project_closed()
                except Exception as e:
                    logger.warning(
                        "Extension '%s' project_closed error: %s",
                        ext.metadata.id, e,
                    )

    def get_status_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get a summary of all extensions and their states."""
        summary = {}
        for ext_id, ext in self._extensions.items():
            summary[ext_id] = {
                'name': ext.metadata.name,
                'version': ext.metadata.version,
                'state': ext.state.value,
                'available': ext.is_available(),
                'error': ext.error_message,
            }
        return summary


def get_extension_registry() -> ExtensionRegistry:
    """
    Get the global extension registry singleton.

    Returns:
        ExtensionRegistry instance
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ExtensionRegistry()
    return _registry_instance


def reset_extension_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry_instance
    if _registry_instance is not None:
        _registry_instance.teardown_all()
    _registry_instance = None

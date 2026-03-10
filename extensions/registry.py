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
            except Exception as e:
                logger.warning("Failed to load extension '%s': %s", entry, e)

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

    def _initialize_extension(self, ext: BaseExtension, iface: Any) -> bool:
        """Initialize a single extension."""
        ext_id = ext.metadata.id
        try:
            if not ext.is_available():
                logger.info(
                    "Extension '%s' not available (missing dependencies)",
                    ext_id,
                )
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

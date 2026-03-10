# -*- coding: utf-8 -*-
"""
FilterMate Extension System.

Provides a plugin-within-a-plugin architecture for optional modules.
Extensions are discovered, loaded, and managed through the ExtensionRegistry.

Usage:
    from .extensions import get_extension_registry

    registry = get_extension_registry()
    registry.discover_extensions()
    registry.initialize_all(iface)

    # Access a specific extension
    qfc = registry.get_extension('qfieldcloud')
    if qfc and qfc.is_available():
        qfc.get_service('push').push_current_filter(...)
"""

from .registry import ExtensionRegistry, get_extension_registry

__all__ = [
    'ExtensionRegistry',
    'get_extension_registry',
]

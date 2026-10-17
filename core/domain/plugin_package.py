# -*- coding: utf-8 -*-
"""
Name of the plugin's root package.

PURE PYTHON module (no QGIS dependency).

The folder QGIS installs the plugin in is not always ``filter_mate`` (a GitHub zip gives
``filter_mate-main``, a user may rename it), and that folder name is the key of
``qgis.utils.plugins`` and the ``package`` of ``importlib.import_module('.x', package=...)``.
This module sits at ``<root>/core/domain/plugin_package.py``: the root is its own name minus
the last three components. Code needing the key reads :data:`PLUGIN_PACKAGE`, never a literal.
"""

DEFAULT_PLUGIN_PACKAGE = 'filter_mate'


def package_from_module_name(module_name: str, default: str = DEFAULT_PLUGIN_PACKAGE) -> str:
    """Root of ``<root>.core.domain.plugin_package``; ``default`` when loaded as a top-level ``core`` (unit tests)."""
    parts = module_name.split('.')
    return '.'.join(parts[:-3]) if len(parts) > 3 else default


PLUGIN_PACKAGE = package_from_module_name(__name__)

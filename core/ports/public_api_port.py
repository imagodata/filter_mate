# -*- coding: utf-8 -*-
"""
Public API Port Interface.

Defines the abstract contract for inter-plugin communication.
External plugins (e.g., Narractive) can use this API to apply
and manage filters on QGIS layers without coupling to FilterMate internals.

This is a PURE PYTHON module with NO QGIS dependencies.

Version: 4.7.0 (Sprint 1 - Narractive Integration)
"""
from abc import ABC, abstractmethod
from typing import Dict


class IFilterMatePublicAPI(ABC):
    """
    Public API port for inter-plugin communication.

    This port defines the contract that external plugins use to
    interact with FilterMate filtering capabilities.

    Usage from another plugin:
        from qgis.utils import plugins
        fm = plugins.get('filter_mate')
        if fm:
            api = fm.get_public_api()
            api.apply_filter('my_layer', 'population > 10000', source_plugin='narractive')
    """

    @abstractmethod
    def apply_filter(self, layer_name: str, filter_expr: str,
                     source_plugin: str = "external") -> bool:
        """
        Apply a filter expression to a named layer.

        Args:
            layer_name: Name of the QGIS layer to filter.
            filter_expr: SQL WHERE clause (without WHERE keyword).
            source_plugin: Name of the calling plugin (for logging/audit).

        Returns:
            True if filter was applied successfully, False otherwise.
        """

    @abstractmethod
    def get_active_filters(self) -> Dict[str, str]:
        """
        Return active filters for all layers.

        Returns:
            Dict mapping layer_name to filter_expression for all layers
            that currently have an active subset string filter.
        """

    @abstractmethod
    def clear_filter(self, layer_name: str) -> bool:
        """
        Clear the filter on a specific layer.

        Args:
            layer_name: Name of the QGIS layer to clear.

        Returns:
            True if filter was cleared successfully, False otherwise.
        """

    @abstractmethod
    def clear_all_filters(self) -> int:
        """
        Clear all active filters on all layers.

        Returns:
            Number of filters that were cleared.
        """

    @abstractmethod
    def get_version(self) -> str:
        """
        Return FilterMate version string.

        Returns:
            Version string from metadata.txt (e.g., '4.6.1').
        """

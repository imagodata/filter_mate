# -*- coding: utf-8 -*-
"""
FilterMate Public API Adapter.

Concrete implementation of IFilterMatePublicAPI for inter-plugin communication.
Delegates to QGIS layer API and the existing FilterMate infrastructure.

This adapter uses PyQt signals for event notification and delegates
filter operations to QGIS's native setSubsetString mechanism.

Version: 4.7.0 (Sprint 1 - Narractive Integration)
"""
import os
from typing import Dict

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import QgsProject, QgsVectorLayer

from ...core.ports.public_api_port import IFilterMatePublicAPI
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


class FilterMatePublicAPI(QObject, IFilterMatePublicAPI):
    """
    Public API for inter-plugin communication with FilterMate.

    Emits PyQt signals so external plugins can react to filter changes.

    Signals:
        filter_applied(str, str, str): layer_name, expression, source_plugin
        filter_cleared(str, str): layer_name, source_plugin
        error_occurred(str, str): operation, error_message
        about_to_unload(): Emitted when FilterMate is about to unload.

    Example:
        api = fm.get_public_api()
        api.filter_applied.connect(my_handler)
        api.apply_filter('communes', 'population > 10000', 'narractive')
    """

    # Signals for external consumers
    filter_applied = pyqtSignal(str, str, str)   # layer_name, expression, source_plugin
    filter_cleared = pyqtSignal(str, str)         # layer_name, source_plugin
    error_occurred = pyqtSignal(str, str)          # operation, error_message
    about_to_unload = pyqtSignal()

    def __init__(self, plugin_instance):
        """
        Initialize the public API adapter.

        Args:
            plugin_instance: The main FilterMate plugin instance.
        """
        super().__init__()
        self._plugin = plugin_instance
        self._version = None
        logger.info("FilterMatePublicAPI initialized")

    def apply_filter(self, layer_name: str, filter_expr: str,
                     source_plugin: str = "external") -> bool:
        """
        Apply a filter expression to a named layer.

        Uses QGIS native setSubsetString for reliable filter application.
        Falls back to safe_set_subset_string when available for enhanced
        error handling on PostgreSQL layers.

        Args:
            layer_name: Name of the QGIS layer to filter.
            filter_expr: SQL WHERE clause (without WHERE keyword).
            source_plugin: Name of the calling plugin (for logging/audit).

        Returns:
            True if filter was applied successfully, False otherwise.
        """
        operation = f"apply_filter({layer_name!r})"
        logger.info(
            f"PublicAPI: {operation} from {source_plugin!r}, "
            f"expr={filter_expr!r}"
        )

        try:
            layer = self._find_vector_layer(layer_name)
            if layer is None:
                msg = f"Layer not found: {layer_name!r}"
                logger.warning(f"PublicAPI: {msg}")
                self.error_occurred.emit(operation, msg)
                return False

            if not layer.isValid():
                msg = f"Layer is not valid: {layer_name!r}"
                logger.warning(f"PublicAPI: {msg}")
                self.error_occurred.emit(operation, msg)
                return False

            # Use safe_set_subset_string if available (handles PostgreSQL type casting)
            success = self._safe_set_subset(layer, filter_expr)

            if success:
                logger.info(
                    f"PublicAPI: Filter applied on {layer_name!r} "
                    f"by {source_plugin!r}"
                )
                self.filter_applied.emit(layer_name, filter_expr, source_plugin)
            else:
                msg = (
                    f"setSubsetString failed for layer {layer_name!r}. "
                    f"Check expression syntax."
                )
                logger.warning(f"PublicAPI: {msg}")
                self.error_occurred.emit(operation, msg)

            return success

        except Exception as e:
            msg = f"Unexpected error: {e}"
            logger.error(f"PublicAPI: {operation} - {msg}", exc_info=True)
            self.error_occurred.emit(operation, msg)
            return False

    def get_active_filters(self) -> Dict[str, str]:
        """
        Return active filters for all vector layers in the project.

        Returns:
            Dict mapping layer_name to filter_expression for all layers
            that currently have an active subset string filter.
        """
        active_filters = {}
        try:
            project = QgsProject.instance()
            for layer in project.mapLayers().values():
                if not isinstance(layer, QgsVectorLayer):
                    continue
                if not layer.isValid():
                    continue
                subset = layer.subsetString()
                if subset and subset.strip():
                    active_filters[layer.name()] = subset
        except Exception as e:
            logger.error(
                f"PublicAPI: get_active_filters error: {e}", exc_info=True
            )
            self.error_occurred.emit("get_active_filters", str(e))

        return active_filters

    def clear_filter(self, layer_name: str) -> bool:
        """
        Clear the filter on a specific layer.

        Args:
            layer_name: Name of the QGIS layer to clear.

        Returns:
            True if filter was cleared successfully, False otherwise.
        """
        operation = f"clear_filter({layer_name!r})"
        logger.info(f"PublicAPI: {operation}")

        try:
            layer = self._find_vector_layer(layer_name)
            if layer is None:
                msg = f"Layer not found: {layer_name!r}"
                logger.warning(f"PublicAPI: {msg}")
                self.error_occurred.emit(operation, msg)
                return False

            if not layer.isValid():
                msg = f"Layer is not valid: {layer_name!r}"
                logger.warning(f"PublicAPI: {msg}")
                self.error_occurred.emit(operation, msg)
                return False

            success = layer.setSubsetString("")
            if success:
                logger.info(f"PublicAPI: Filter cleared on {layer_name!r}")
                self.filter_cleared.emit(layer_name, "external")
            else:
                msg = f"Failed to clear filter on layer {layer_name!r}"
                logger.warning(f"PublicAPI: {msg}")
                self.error_occurred.emit(operation, msg)

            return success

        except Exception as e:
            msg = f"Unexpected error: {e}"
            logger.error(f"PublicAPI: {operation} - {msg}", exc_info=True)
            self.error_occurred.emit(operation, msg)
            return False

    def clear_all_filters(self) -> int:
        """
        Clear all active filters on all vector layers.

        Returns:
            Number of filters that were cleared.
        """
        logger.info("PublicAPI: clear_all_filters")
        cleared_count = 0

        try:
            project = QgsProject.instance()
            for layer in project.mapLayers().values():
                if not isinstance(layer, QgsVectorLayer):
                    continue
                if not layer.isValid():
                    continue
                subset = layer.subsetString()
                if subset and subset.strip():
                    layer_name = layer.name()
                    success = layer.setSubsetString("")
                    if success:
                        cleared_count += 1
                        self.filter_cleared.emit(layer_name, "external")
                        logger.debug(
                            f"PublicAPI: Cleared filter on {layer_name!r}"
                        )
                    else:
                        logger.warning(
                            f"PublicAPI: Failed to clear filter on "
                            f"{layer_name!r}"
                        )

        except Exception as e:
            msg = f"Unexpected error: {e}"
            logger.error(
                f"PublicAPI: clear_all_filters - {msg}", exc_info=True
            )
            self.error_occurred.emit("clear_all_filters", msg)

        logger.info(f"PublicAPI: Cleared {cleared_count} filter(s)")
        return cleared_count

    def get_version(self) -> str:
        """
        Return FilterMate version string from metadata.txt.

        Returns:
            Version string (e.g., '4.6.1').
        """
        if self._version is not None:
            return self._version

        try:
            plugin_dir = self._plugin.plugin_dir
            metadata_path = os.path.join(plugin_dir, "metadata.txt")

            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("version="):
                            self._version = line.split("=", 1)[1].strip()
                            return self._version

            self._version = "unknown"
            logger.warning("PublicAPI: Could not read version from metadata.txt")

        except Exception as e:
            self._version = "unknown"
            logger.error(f"PublicAPI: Error reading version: {e}")

        return self._version

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_vector_layer(self, layer_name: str):
        """
        Find a vector layer by name in the current QGIS project.

        Args:
            layer_name: Layer name to search for.

        Returns:
            QgsVectorLayer or None if not found.
        """
        project = QgsProject.instance()
        layers = project.mapLayersByName(layer_name)
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):
                return layer
        return None

    def _safe_set_subset(self, layer, expression: str) -> bool:
        """
        Apply subset string with enhanced error handling.

        Tries to use safe_set_subset_string from infrastructure
        (which handles PostgreSQL type casting), falls back to
        native setSubsetString.

        Args:
            layer: QgsVectorLayer to filter.
            expression: SQL WHERE clause.

        Returns:
            True if successful.
        """
        try:
            from ...infrastructure.database.sql_utils import safe_set_subset_string
            return safe_set_subset_string(layer, expression)
        except ImportError:
            logger.debug(
                "PublicAPI: safe_set_subset_string not available, "
                "using native setSubsetString"
            )
            return layer.setSubsetString(expression)

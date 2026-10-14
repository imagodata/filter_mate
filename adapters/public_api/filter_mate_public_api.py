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
from typing import Any, Callable, Dict, List, Optional, Union

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import QgsProject, QgsVectorLayer

from ...core.ports.public_api_port import IFilterMatePublicAPI
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


def _common_metaclass(*bases):
    """Metaclass deriving from the metaclasses of every base.

    QObject (sip wrapper type) and the ABC port (ABCMeta) have unrelated
    metaclasses: without a common one the class cannot even be defined in a
    real QGIS ("metaclass conflict").
    """
    metas = []
    for base in bases:
        meta = type(base)
        if any(issubclass(known, meta) for known in metas):
            continue
        metas = [known for known in metas if not issubclass(meta, known)] + [meta]
    return metas[0] if len(metas) == 1 else type("_QObjectABCMeta", tuple(metas), {})


class FilterMatePublicAPI(QObject, IFilterMatePublicAPI, metaclass=_common_metaclass(QObject, IFilterMatePublicAPI)):
    """
    Public API for inter-plugin communication with FilterMate.

    Emits PyQt signals so external plugins can react to filter changes.

    Signals:
        filter_applied(str, str, str): layer_name, expression, source_plugin
        filter_cleared(str, str): layer_name, source_plugin
        error_occurred(str, str): operation, error_message
        operation_completed(str, dict): FilterMate 5 operation name, report dict
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
    operation_completed = pyqtSignal(str, dict)    # operation, report dict (FilterMate 5)
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
    # FilterMate 5: layers of any kind
    # ------------------------------------------------------------------

    def cross_filter(self, source_layer: str, target_layers: List[str],
                     predicates: Optional[List[str]] = None, buffer: float = 0.0,
                     coverage_min: float = 0.0, operator: Optional[str] = None,
                     selected_only: bool = True,
                     raster_selection: Optional[Dict[str, Any]] = None,
                     point_cloud_criteria: Union[None, str, Dict[str, Any]] = None,
                     filter_source: bool = False) -> Dict[str, Any]:
        """Filter layers of any kind by a source of any kind (see the port)."""
        def run():
            from ...core.domain import api_requests
            from . import operations
            return operations.cross_filter(
                source_layer, list(target_layers or []),
                predicates=api_requests.normalize_predicates(predicates),
                buffer=buffer, coverage_min=coverage_min,
                operator=api_requests.normalize_operator(operator),
                selected_only=selected_only,
                raster_selection=api_requests.raster_selection_from_dict(raster_selection),
                point_cloud_criteria=api_requests.point_cloud_criteria_from_dict(point_cloud_criteria),
                filter_source=filter_source)
        return self._run_operation("cross_filter", run)

    def cross_filter_by_geometry(self, wkt: str, crs_authid: str, target_layers: List[str],
                                 predicates: Optional[List[str]] = None, buffer: float = 0.0,
                                 coverage_min: float = 0.0,
                                 operator: Optional[str] = None) -> Dict[str, Any]:
        """Filter layers of any kind by a WKT geometry (see the port)."""
        def run():
            from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry
            from ...core.domain import api_requests
            from . import operations
            crs = QgsCoordinateReferenceSystem(crs_authid or "")
            if not crs.isValid():
                raise ValueError(f"invalid CRS: {crs_authid!r}")
            geometry = QgsGeometry.fromWkt(wkt or "")
            if geometry.isNull():
                raise ValueError("invalid WKT geometry")
            return operations.cross_filter_by_geometry(
                geometry, crs, list(target_layers or []),
                predicates=api_requests.normalize_predicates(predicates), buffer=buffer,
                coverage_min=coverage_min, operator=api_requests.normalize_operator(operator))
        return self._run_operation("cross_filter_by_geometry", run)

    def filter_point_clouds(self, layers: List[str], criteria: Union[str, Dict[str, Any]],
                            operator: Optional[str] = None) -> Dict[str, Any]:
        """Apply point cloud criteria to several layers (see the port)."""
        def run():
            from ...core.domain import api_requests
            from . import operations
            return operations.filter_point_clouds(
                list(layers or []), api_requests.point_cloud_criteria_from_dict(criteria),
                operator=api_requests.normalize_operator(operator))
        return self._run_operation("filter_point_clouds", run)

    def clear_filters(self, layers: List[str]) -> Dict[str, Any]:
        """Unfilter layers of any kind (see the port)."""
        def run():
            from . import operations
            return operations.clear_filters(list(layers or []))
        return self._run_operation("clear_filters", run)

    def export_layers(self, layers: List[str], folder: str, vector_format: str = "GPKG",
                      raster_format: str = "COG", point_cloud_format: str = "LAZ",
                      crs_authid: Optional[str] = None) -> Dict[str, Any]:
        """Export layers as filtered now (see the port)."""
        def run():
            from . import operations
            crs = None
            if crs_authid:
                from qgis.core import QgsCoordinateReferenceSystem
                crs = QgsCoordinateReferenceSystem(crs_authid)
                if not crs.isValid():
                    raise ValueError(f"invalid CRS: {crs_authid!r}")
            return operations.export_layers(list(layers or []), folder, vector_format=vector_format,
                                            raster_format=raster_format,
                                            point_cloud_format=point_cloud_format, crs=crs)
        return self._run_operation("export_layers", run)

    def list_favorites(self) -> List[Dict[str, Any]]:
        """Favorites of the running plugin, or those saved in the project file."""
        from . import operations
        try:
            favorites = operations.list_favorites(operations.find_favorites_service(self._plugin))
        except Exception as e:
            logger.error(f"PublicAPI: list_favorites error: {e}", exc_info=True)
            self.error_occurred.emit("list_favorites", str(e))
            return []
        return [{"id": f.id, "name": f.name, "layer_name": f.layer_name or "",
                 "description": getattr(f, "description", "") or ""} for f in favorites]

    def apply_favorite(self, name_or_id: str) -> Dict[str, Any]:
        """Apply a favorite by name or id (see the port)."""
        def run():
            from . import operations
            return operations.apply_favorite(name_or_id, operations.find_favorites_service(self._plugin))
        return self._run_operation("apply_favorite", run)

    def get_filter_state(self) -> List[Dict[str, Any]]:
        """Every filtered layer of the project (see the port)."""
        from . import operations
        try:
            return operations.filter_state()
        except Exception as e:
            logger.error(f"PublicAPI: get_filter_state error: {e}", exc_info=True)
            self.error_occurred.emit("get_filter_state", str(e))
            return []

    def _run_operation(self, operation: str, run: Callable) -> Dict[str, Any]:
        """Run an operation, turn invalid arguments into an error report, emit the signals."""
        logger.info(f"PublicAPI: {operation}")
        try:
            report = run().to_dict()
        except ValueError as e:
            report = {"ok": False, "done": [], "failed": {}, "skipped": {}, "error": str(e),
                      "outputs": {}, "details": {}}
        except Exception as e:
            logger.error(f"PublicAPI: {operation} - {e}", exc_info=True)
            report = {"ok": False, "done": [], "failed": {}, "skipped": {}, "error": f"Unexpected error: {e}",
                      "outputs": {}, "details": {}}
        if report["error"]:
            self.error_occurred.emit(operation, report["error"])
        self.operation_completed.emit(operation, report)
        return report

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

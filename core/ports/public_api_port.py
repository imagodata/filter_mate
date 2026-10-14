# -*- coding: utf-8 -*-
"""
Public API Port Interface.

Defines the abstract contract for inter-plugin communication.
External plugins (e.g., Narractive) can use this API to apply
and manage filters on QGIS layers without coupling to FilterMate internals.

This is a PURE PYTHON module with NO QGIS dependencies.

Version: 4.7.0 (Sprint 1 - Narractive Integration)
FilterMate 5: layers of any kind (vector, raster, point cloud), cross
filters, point cloud criteria, exports and favorites. These methods return
plain dicts (JSON compatible) built by ``OperationReport.to_dict``::

    {"ok": bool, "done": [layer names], "failed": {name: message},
     "skipped": {name: reason}, "error": str, "outputs": {name: path},
     "details": {...}}
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


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

    # --- FilterMate 5 ------------------------------------------------------

    @abstractmethod
    def cross_filter(self, source_layer: str, target_layers: List[str],
                     predicates: Optional[List[str]] = None, buffer: float = 0.0,
                     coverage_min: float = 0.0, operator: Optional[str] = None,
                     selected_only: bool = True,
                     raster_selection: Optional[Dict[str, Any]] = None,
                     point_cloud_criteria: Union[None, str, Dict[str, Any]] = None,
                     filter_source: bool = False) -> Dict[str, Any]:
        """
        Filter layers of any kind by a selection made on a source of any kind.

        Args:
            source_layer: Source layer name or id (vector, raster or point cloud).
            target_layers: Names or ids of the layers to filter (any kind).
            predicates: ``Intersect``, ``Contain``, ``Disjoint``, ``Equal``, ``Touch``,
                ``Overlap``, ``Are within``, ``Cross`` (default ``Intersect``).
            buffer: Buffer of the source geometry (source CRS units).
            coverage_min: Minimum share (%) of a polygon target inside the source.
            operator: ``AND``, ``OR``, ``AND NOT`` with each target's previous
                filter, None to replace it.
            selected_only: Vector source: selected features only (all when none).
            raster_selection: Raster source (required): ``{"band": 1, "mode":
                "range"|"classes"|"expression", "minimum", "maximum", "classes",
                "expression"}``.
            point_cloud_criteria: Point cloud source: an expression or ``{"classes",
                "z_min", "z_max", "intensity_min", "intensity_max", "return_number",
                "expression"}``; None = the points it shows now.
            filter_source: Raster source: also mask the source outside the selection.

        Returns:
            Operation report (see module docstring).
        """

    @abstractmethod
    def cross_filter_by_geometry(self, wkt: str, crs_authid: str, target_layers: List[str],
                                 predicates: Optional[List[str]] = None, buffer: float = 0.0,
                                 coverage_min: float = 0.0,
                                 operator: Optional[str] = None) -> Dict[str, Any]:
        """
        Filter layers of any kind by a geometry (WKT in ``crs_authid``, e.g. ``EPSG:2154``).

        Returns:
            Operation report.
        """

    @abstractmethod
    def filter_point_clouds(self, layers: List[str], criteria: Union[str, Dict[str, Any]],
                            operator: Optional[str] = None) -> Dict[str, Any]:
        """
        Apply the same criteria (dict or expression) to several point cloud layers.

        Returns:
            Operation report.
        """

    @abstractmethod
    def clear_filters(self, layers: List[str]) -> Dict[str, Any]:
        """
        Put layers of any kind back on their original source with no filter.

        Returns:
            Operation report.
        """

    @abstractmethod
    def export_layers(self, layers: List[str], folder: str, vector_format: str = "GPKG",
                      raster_format: str = "COG", point_cloud_format: str = "LAZ",
                      crs_authid: Optional[str] = None) -> Dict[str, Any]:
        """
        Write layers as they are filtered now, one file per layer, into ``folder``.

        Returns:
            Operation report; ``outputs`` maps layer names to the files written.
        """

    @abstractmethod
    def list_favorites(self) -> List[Dict[str, Any]]:
        """
        Return the favorites: ``[{"id", "name", "layer_name", "description"}]``.
        """

    @abstractmethod
    def apply_favorite(self, name_or_id: str) -> Dict[str, Any]:
        """
        Apply a favorite (subsets, raster and point cloud clips) by name or id.

        Returns:
            Operation report.
        """

    @abstractmethod
    def get_filter_state(self) -> List[Dict[str, Any]]:
        """
        Return every filtered layer: ``[{"id", "name", "kind", "subset", "derived", "source"}]``.
        """

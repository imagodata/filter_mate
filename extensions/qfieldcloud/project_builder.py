# -*- coding: utf-8 -*-
"""
Build a .qgs project file optimized for QFieldCloud from a FilterMate GPKG export.

The builder:
1. Creates a QGIS project programmatically
2. Adds layers from the exported GeoPackage
3. Applies QFieldSync custom properties (layer action modes)
4. Loads and applies QML styles if available
5. Saves as .qgs file ready for QFieldCloud upload
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger('FilterMate.Extensions.QFieldCloud.ProjectBuilder')

# QFieldCloud / QFieldSync action modes
ACTION_OFFLINE = "offline"
ACTION_COPY = "copy"
ACTION_NO_ACTION = "no_action"
ACTION_REMOVE = "remove"
ACTION_HYBRID = "hybrid"

# Default layer mode mapping for WYRE FTTH
WYRE_LAYER_ACTIONS: Dict[str, str] = {
    "structures": ACTION_OFFLINE,
    "demand_points": ACTION_OFFLINE,
    "zone_drop": ACTION_OFFLINE,
    "zone_distribution": ACTION_OFFLINE,
    "sheaths": ACTION_COPY,
    "ducts": ACTION_COPY,
    "subducts": ACTION_COPY,
    "zone_pop": ACTION_COPY,
    "zone_mro": ACTION_NO_ACTION,
}


class QFieldProjectBuilder:
    """
    Build a .qgs project file for QFieldCloud from a GeoPackage export.

    The generated project references the GPKG with relative paths,
    applies QFieldSync action modes, and embeds layer styles.

    Usage:
        builder = QFieldProjectBuilder(
            gpkg_path=Path("/tmp/export/WYRE-POP_001.gpkg"),
            output_dir=Path("/tmp/export/"),
            project_name="WYRE-POP_001",
        )
        qgs_path = builder.build()
    """

    def __init__(
        self,
        gpkg_path: Path,
        output_dir: Path,
        project_name: str,
        srid: int = 31370,
        styles_dir: Optional[Path] = None,
        layer_actions: Optional[Dict[str, str]] = None,
    ):
        """
        Args:
            gpkg_path: Path to the GeoPackage file
            output_dir: Directory to write the .qgs file
            project_name: Name for the generated project
            srid: EPSG code for the project CRS (default: 31370 Belgium Lambert)
            styles_dir: Optional directory containing QML style files
            layer_actions: Mapping of layer_name -> QFieldSync action mode
        """
        self._gpkg_path = Path(gpkg_path)
        self._output_dir = Path(output_dir)
        self._project_name = project_name
        self._srid = srid
        self._styles_dir = Path(styles_dir) if styles_dir else None
        self._layer_actions = layer_actions or WYRE_LAYER_ACTIONS

    def build(self) -> Path:
        """
        Generate the .qgs project file.

        Returns:
            Path to the generated .qgs file

        Raises:
            FileNotFoundError: If GPKG file doesn't exist
            RuntimeError: If project generation fails
        """
        from qgis.core import (
            QgsCoordinateReferenceSystem,
            QgsProject,
            QgsVectorLayer,
        )

        if not self._gpkg_path.is_file():
            raise FileNotFoundError(f"GeoPackage not found: {self._gpkg_path}")

        self._output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._output_dir / f"{self._project_name}.qgs"

        # Create a new QGIS project
        project = QgsProject.instance()

        # We work with a clean project context
        project.clear()
        project.setTitle(self._project_name)

        # Set CRS
        crs = QgsCoordinateReferenceSystem(f"EPSG:{self._srid}")
        project.setCrs(crs)

        # Discover layers in the GeoPackage
        layer_names = self._discover_gpkg_layers()
        if not layer_names:
            raise RuntimeError(f"No layers found in {self._gpkg_path}")

        added_layers: List[QgsVectorLayer] = []
        for layer_name in layer_names:
            uri = f"{self._gpkg_path}|layername={layer_name}"
            vlayer = QgsVectorLayer(uri, layer_name, "ogr")

            if not vlayer.isValid():
                logger.warning("Invalid layer '%s' in GPKG, skipping", layer_name)
                continue

            # Apply QML style if available
            self._apply_style(vlayer, layer_name)

            # Apply QFieldSync custom properties
            action = self._layer_actions.get(layer_name, ACTION_COPY)
            self._apply_qfieldsync_properties(vlayer, action)

            project.addMapLayer(vlayer)
            added_layers.append(vlayer)
            logger.debug("Added layer '%s' (action: %s)", layer_name, action)

        if not added_layers:
            raise RuntimeError("No valid layers could be added to the project")

        # Make GPKG path relative in the project
        project.setFileName(str(output_path))
        project.write(str(output_path))

        logger.info(
            "Generated project '%s' with %d layers at %s",
            self._project_name, len(added_layers), output_path,
        )
        return output_path

    def _discover_gpkg_layers(self) -> List[str]:
        """
        Discover layer names in the GeoPackage.

        Returns:
            List of layer names
        """
        try:
            from osgeo import ogr

            ds = ogr.Open(str(self._gpkg_path))
            if ds is None:
                logger.error("Cannot open GeoPackage: %s", self._gpkg_path)
                return []

            layer_names = []
            for i in range(ds.GetLayerCount()):
                lyr = ds.GetLayerByIndex(i)
                if lyr:
                    layer_names.append(lyr.GetName())

            ds = None  # Close
            return layer_names

        except ImportError:
            # Fallback: try ogr provider via QGIS
            return self._discover_gpkg_layers_qgis()

    def _discover_gpkg_layers_qgis(self) -> List[str]:
        """Discover GPKG layers using QGIS provider."""
        try:
            from qgis.core import QgsVectorLayer

            # Try well-known layer names from the action mapping
            found = []
            for name in self._layer_actions:
                uri = f"{self._gpkg_path}|layername={name}"
                vlayer = QgsVectorLayer(uri, name, "ogr")
                if vlayer.isValid():
                    found.append(name)
            return found
        except Exception as e:
            logger.error("Failed to discover GPKG layers: %s", e)
            return []

    def _apply_style(self, layer, layer_name: str) -> None:
        """Apply QML style to a layer if style file exists."""
        if not self._styles_dir:
            return

        qml_path = self._styles_dir / f"{layer_name}.qml"
        if qml_path.is_file():
            result = layer.loadNamedStyle(str(qml_path))
            if result[1]:  # success boolean
                logger.debug("Applied style from %s", qml_path)
            else:
                logger.warning(
                    "Failed to apply style %s: %s", qml_path, result[0]
                )

    @staticmethod
    def _apply_qfieldsync_properties(layer, action: str) -> None:
        """
        Set QFieldSync/QFieldCloud custom properties on a layer.

        These properties tell QFieldCloud how to handle each layer:
        - offline: Layer is downloaded and editable on device
        - copy: Layer is downloaded read-only
        - no_action: Layer is not included in the package
        """
        layer.setCustomProperty("QFieldSync/action", action)
        layer.setCustomProperty("QFieldSync/cloud_action", action)

    def get_output_path(self) -> Path:
        """Get the expected output path for the .qgs file."""
        return self._output_dir / f"{self._project_name}.qgs"

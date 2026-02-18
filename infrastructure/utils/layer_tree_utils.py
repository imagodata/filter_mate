"""
Utilities for traversing QGIS layer tree and extracting group hierarchy.

Used by the GPKG export feature to preserve layer group structure.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from qgis.core import QgsProject, QgsLayerTreeGroup, QgsLayerTreeLayer, QgsVectorLayer
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


def get_layer_group_hierarchy(
    layer_ids: List[str],
    project: Optional['QgsProject'] = None
) -> dict:
    """Traverse QgsProject layer tree and return hierarchy for selected layer IDs.

    Prunes empty groups (groups that contain none of the selected layers).

    Args:
        layer_ids: List of layer IDs to include in the hierarchy.
        project: QgsProject instance (defaults to QgsProject.instance()).

    Returns:
        dict with structure:
        {
            "groups": [
                {"name": str, "layers": [layer_id, ...], "groups": [...]},
                ...
            ],
            "ungrouped": [layer_id, ...]
        }
    """
    if not QGIS_AVAILABLE:
        return {"groups": [], "ungrouped": list(layer_ids)}

    if project is None:
        project = QgsProject.instance()

    root = project.layerTreeRoot()
    if not root:
        return {"groups": [], "ungrouped": list(layer_ids)}

    layer_id_set = set(layer_ids)
    result = _traverse_group(root, layer_id_set)

    # Layers at root level (not in any group)
    ungrouped = []
    for child in root.children():
        if isinstance(child, QgsLayerTreeLayer):
            lid = child.layerId()
            if lid in layer_id_set:
                ungrouped.append(lid)

    return {
        "groups": result["groups"],
        "ungrouped": ungrouped,
    }


def _traverse_group(group: 'QgsLayerTreeGroup', layer_id_set: set) -> dict:
    """Recursively traverse a layer tree group.

    Returns:
        dict with "groups" (list of sub-group dicts) and "layers" (list of layer IDs).
    """
    sub_groups = []
    layers_in_group = []

    for child in group.children():
        if isinstance(child, QgsLayerTreeGroup):
            sub = _traverse_group(child, layer_id_set)
            child_layers = sub["layers"]
            child_groups = sub["groups"]
            # Only include non-empty groups
            if child_layers or child_groups:
                sub_groups.append({
                    "name": child.name(),
                    "layers": child_layers,
                    "groups": child_groups,
                })
        elif isinstance(child, QgsLayerTreeLayer):
            lid = child.layerId()
            if lid in layer_id_set:
                layers_in_group.append(lid)

    return {"groups": sub_groups, "layers": layers_in_group}


def build_layer_tree_for_gpkg(
    layer_ids: List[str],
    gpkg_path: str,
    project: Optional['QgsProject'] = None,
) -> Optional['QgsLayerTreeGroup']:
    """Build a QgsLayerTreeGroup mirroring the project structure for selected layers.

    Each layer node points to the GPKG file as its data source.

    Args:
        layer_ids: Layer IDs to include.
        gpkg_path: Path to the exported GPKG file.
        project: QgsProject instance (defaults to QgsProject.instance()).

    Returns:
        QgsLayerTreeGroup root, or None if QGIS not available.
    """
    if not QGIS_AVAILABLE:
        return None

    if project is None:
        project = QgsProject.instance()

    root = project.layerTreeRoot()
    if not root:
        return None

    layer_id_set = set(layer_ids)
    new_root = QgsLayerTreeGroup()
    _clone_tree_structure(root, new_root, layer_id_set, gpkg_path, project)
    return new_root


def _clone_tree_structure(
    source_group: 'QgsLayerTreeGroup',
    target_group: 'QgsLayerTreeGroup',
    layer_id_set: set,
    gpkg_path: str,
    project: 'QgsProject',
) -> bool:
    """Recursively clone tree structure, keeping only selected layers.

    Returns True if this group contains at least one selected layer.
    """
    has_content = False

    for child in source_group.children():
        if isinstance(child, QgsLayerTreeGroup):
            new_sub = target_group.addGroup(child.name())
            sub_has = _clone_tree_structure(child, new_sub, layer_id_set, gpkg_path, project)
            if not sub_has:
                # Remove empty group
                target_group.removeChildNode(new_sub)
            else:
                has_content = True

        elif isinstance(child, QgsLayerTreeLayer):
            lid = child.layerId()
            if lid in layer_id_set:
                original_layer = project.mapLayer(lid)
                if original_layer and isinstance(original_layer, QgsVectorLayer):
                    layer_name = original_layer.name()
                    gpkg_uri = f"{gpkg_path}|layername={layer_name}"
                    gpkg_layer = QgsVectorLayer(gpkg_uri, layer_name, "ogr")
                    if gpkg_layer.isValid():
                        target_group.addLayer(gpkg_layer)
                        has_content = True
                    else:
                        logger.warning(
                            f"Could not create valid GPKG layer for '{layer_name}' "
                            f"from {gpkg_uri}"
                        )

    return has_content


def format_tree_for_display(hierarchy: dict, indent: int = 0) -> str:
    """Format hierarchy dict as indented text for the recap dialog.

    Args:
        hierarchy: Output from get_layer_group_hierarchy().
        indent: Current indentation level.

    Returns:
        Human-readable indented string.
    """
    if not QGIS_AVAILABLE:
        project = None
    else:
        project = QgsProject.instance()

    lines = []
    prefix = "  " * indent

    for group in hierarchy.get("groups", []):
        lines.append(f"{prefix}{group['name']}/")
        # Layers directly in this group
        for lid in group.get("layers", []):
            layer_name = _resolve_layer_name(lid, project)
            lines.append(f"{prefix}  {layer_name}")
        # Sub-groups
        if group.get("groups"):
            sub_text = format_tree_for_display(
                {"groups": group["groups"], "ungrouped": []},
                indent + 1,
            )
            if sub_text:
                lines.append(sub_text)

    # Ungrouped layers (root level)
    for lid in hierarchy.get("ungrouped", []):
        layer_name = _resolve_layer_name(lid, project)
        lines.append(f"{prefix}{layer_name}")

    return "\n".join(lines)


def _resolve_layer_name(layer_id: str, project) -> str:
    """Resolve a layer ID to its display name."""
    if project:
        layer = project.mapLayer(layer_id)
        if layer:
            return layer.name()
    return layer_id


def count_groups(hierarchy: dict) -> int:
    """Count total number of groups in the hierarchy."""
    count = len(hierarchy.get("groups", []))
    for group in hierarchy.get("groups", []):
        if group.get("groups"):
            count += count_groups({"groups": group["groups"], "ungrouped": []})
    return count

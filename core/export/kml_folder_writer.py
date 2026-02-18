"""
Merge individual KML files into a single KML with Folder structure.

After the standard per-layer KML export, this module reads each
individual .kml file, extracts its placemarks/features, and writes
them into a unified KML document with <Folder> elements matching
the QGIS layer group hierarchy.

Pure Python (xml.etree), no QGIS objects created.
"""

import logging
import os
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

# KML namespace
KML_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace('', KML_NS)


def merge_kml_with_folders(
    kml_files: Dict[str, str],
    hierarchy: dict,
    output_path: str,
    project_title: str = "FilterMate Export",
) -> bool:
    """Merge individual KML files into one with Folder structure.

    Args:
        kml_files: Mapping of layer_id → path to individual .kml file.
        hierarchy: Output from get_layer_group_hierarchy() — tree structure
                   with "groups" and "ungrouped" keys.
        output_path: Path for the merged output .kml file.
        project_title: Name for the root Document element.

    Returns:
        True on success, False on failure.
    """
    try:
        return _do_merge(kml_files, hierarchy, output_path, project_title)
    except Exception as e:
        logger.error(f"KML folder merge failed: {e}", exc_info=True)
        return False


def _do_merge(
    kml_files: Dict[str, str],
    hierarchy: dict,
    output_path: str,
    project_title: str,
) -> bool:
    """Internal merge implementation."""
    # 1. Parse each individual KML and extract content
    layer_content = {}  # layer_id → list of XML elements (placemarks, styles, etc.)
    layer_names = {}    # layer_id → layer name (from KML Document/name)

    for layer_id, kml_path in kml_files.items():
        if not os.path.isfile(kml_path):
            logger.warning(f"KML file not found: {kml_path}")
            continue

        elements, name = _extract_kml_content(kml_path)
        if elements:
            layer_content[layer_id] = elements
            layer_names[layer_id] = name or os.path.splitext(os.path.basename(kml_path))[0]

    if not layer_content:
        logger.warning("No KML content found to merge")
        return False

    # 2. Build the merged KML
    kml_root = ET.Element(f"{{{KML_NS}}}kml")
    document = ET.SubElement(kml_root, f"{{{KML_NS}}}Document")
    ET.SubElement(document, f"{{{KML_NS}}}name").text = project_title

    # 3. Build folder structure from hierarchy
    _build_folders(document, hierarchy, layer_content, layer_names)

    # 4. Write output
    tree = ET.ElementTree(kml_root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    logger.info(
        f"Merged {len(layer_content)} layers into KML with folders: {output_path}"
    )
    return True


def _extract_kml_content(kml_path: str) -> tuple:
    """Parse a KML file and extract its placemarks and styles.

    Returns:
        (list_of_elements, document_name) — elements are Placemarks,
        Styles, StyleMaps, etc. found in the Document.
    """
    try:
        tree = ET.parse(kml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        logger.warning(f"Failed to parse KML {kml_path}: {e}")
        return [], None

    # Find the Document element (handles namespace)
    doc = root.find(f"{{{KML_NS}}}Document")
    if doc is None:
        # Try without namespace
        doc = root.find("Document")
    if doc is None:
        doc = root  # Fallback: use root directly

    # Extract document name
    name_el = doc.find(f"{{{KML_NS}}}name")
    if name_el is None:
        name_el = doc.find("name")
    doc_name = name_el.text if name_el is not None else None

    # Extract all meaningful child elements
    elements = []
    skip_tags = {'name', 'description', 'open', 'visibility',
                 f'{{{KML_NS}}}name', f'{{{KML_NS}}}description',
                 f'{{{KML_NS}}}open', f'{{{KML_NS}}}visibility'}

    for child in doc:
        tag = child.tag
        # Skip metadata elements, keep everything else (Placemarks, Styles, etc.)
        if tag not in skip_tags:
            elements.append(child)

    return elements, doc_name


def _build_folders(
    parent: ET.Element,
    hierarchy: dict,
    layer_content: Dict[str, list],
    layer_names: Dict[str, str],
) -> None:
    """Recursively build <Folder> structure in the KML Document."""
    # Process groups
    for group in hierarchy.get("groups", []):
        folder = ET.SubElement(parent, f"{{{KML_NS}}}Folder")
        ET.SubElement(folder, f"{{{KML_NS}}}name").text = group["name"]

        # Add layers directly in this group
        for layer_id in group.get("layers", []):
            _add_layer_to_parent(folder, layer_id, layer_content, layer_names)

        # Recurse into sub-groups
        if group.get("groups"):
            _build_folders(folder, {"groups": group["groups"], "ungrouped": []},
                           layer_content, layer_names)

    # Process ungrouped layers (at root level)
    for layer_id in hierarchy.get("ungrouped", []):
        _add_layer_to_parent(parent, layer_id, layer_content, layer_names)


def _add_layer_to_parent(
    parent: ET.Element,
    layer_id: str,
    layer_content: Dict[str, list],
    layer_names: Dict[str, str],
) -> None:
    """Add a layer's content to a parent element.

    Wraps the layer's placemarks in a Folder named after the layer.
    """
    if layer_id not in layer_content:
        return

    elements = layer_content[layer_id]
    name = layer_names.get(layer_id, layer_id)

    # Wrap in a layer-level Folder
    layer_folder = ET.SubElement(parent, f"{{{KML_NS}}}Folder")
    ET.SubElement(layer_folder, f"{{{KML_NS}}}name").text = name

    for el in elements:
        layer_folder.append(el)


def cleanup_individual_kmls(kml_files: Dict[str, str]) -> int:
    """Delete individual KML files after successful merge.

    Args:
        kml_files: Mapping of layer_id → path to individual .kml file.

    Returns:
        Number of files deleted.
    """
    deleted = 0
    for layer_id, kml_path in kml_files.items():
        try:
            if os.path.isfile(kml_path):
                os.remove(kml_path)
                deleted += 1
        except OSError as e:
            logger.warning(f"Could not delete {kml_path}: {e}")
    return deleted

"""
Write QGIS layer tree structure into an exported GeoPackage.

Embeds a minimal QGIS project inside the GPKG that preserves
the layer group hierarchy. When the GPKG is opened in QGIS,
the embedded project restores the group structure.

Implementation uses sqlite3 + xml.etree to avoid creating
QgsProject/QgsVectorLayer objects whose lifecycle crashes
QGIS 3.44 (access violation in QgsCustomization::preNotify).
"""

import io
import logging
import os
import sqlite3
import uuid
import zipfile
from datetime import datetime
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

try:
    from qgis.core import (
        Qgis,
        QgsProject,
        QgsLayerTreeGroup,
        QgsLayerTreeLayer,
    )
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


# OGR/GPKG geometry type → (QGIS geometry attr, wkbType attr, simplifyDrawingHints)
_GEOM_TYPE_MAP = {
    'POINT': ('Point', 'Point', '0'),
    'MULTIPOINT': ('Point', 'MultiPoint', '0'),
    'LINESTRING': ('Line', 'LineString', '1'),
    'MULTILINESTRING': ('Line', 'MultiLineString', '1'),
    'POLYGON': ('Polygon', 'Polygon', '1'),
    'MULTIPOLYGON': ('Polygon', 'MultiPolygon', '1'),
    'GEOMETRY': ('Unknown', 'Unknown', '0'),
    'GEOMETRYCOLLECTION': ('Unknown', 'GeometryCollection', '0'),
}


def write_layer_tree_to_gpkg(
    gpkg_path: str,
    layer_ids: List[str],
    project_title: str = "FilterMate Export",
    export_crs_authid: Optional[str] = None,
    save_styles: bool = False,
) -> bool:
    """Embed a QGIS project with layer tree groups into a GeoPackage.

    Safe for QGIS 3.44: uses sqlite3 + xml.etree instead of temporary
    QgsProject/QgsVectorLayer objects.

    Args:
        gpkg_path: Path to the exported GPKG file.
        layer_ids: Original layer IDs from the source project.
        project_title: Title for the embedded project.
        export_crs_authid: If set, override layer CRS (data was reprojected).
        save_styles: Whether to embed layer styles in the project.

    Returns:
        True on success, False on failure.
    """
    if not QGIS_AVAILABLE:
        logger.warning("QGIS not available - cannot write layer tree to GPKG")
        return False

    if not os.path.isfile(gpkg_path):
        logger.warning(f"GPKG file not found: {gpkg_path}")
        return False

    try:
        return _do_write(gpkg_path, layer_ids, project_title, export_crs_authid, save_styles)
    except Exception as e:
        logger.error(f"Failed to write layer tree to GPKG: {e}", exc_info=True)
        return False


def _do_write(
    gpkg_path: str,
    layer_ids: List[str],
    project_title: str,
    export_crs_authid: Optional[str] = None,
    save_styles: bool = False,
) -> bool:
    """Build project XML and write it into the GPKG via sqlite3."""
    gpkg_filename = os.path.basename(gpkg_path)

    # 1. Read GPKG metadata (layer names, geometry types, SRS) via sqlite3
    gpkg_meta = _read_gpkg_metadata(gpkg_path)
    if not gpkg_meta:
        logger.warning(f"No vector layers found in GPKG: {gpkg_path}")
        return False

    # 2. Read source project layer tree (read-only, no object creation)
    source_project = QgsProject.instance()
    layer_map = _map_layer_ids_to_gpkg(source_project, layer_ids, gpkg_meta)
    if not layer_map:
        logger.warning("No matching layers between source project and GPKG")
        return False

    hierarchy = _extract_hierarchy(source_project, set(layer_map.keys()))

    # 3. Extract styles (if requested) and CRS from source layers
    layer_styles = {}   # layer_id → style XML string (from exportNamedStyle)
    layer_crs = {}      # layer_id → {authid, proj4, wkt, srid, description}

    # If export reprojected data, build CRS info from the export CRS
    override_crs = None
    if export_crs_authid:
        try:
            from qgis.core import QgsCoordinateReferenceSystem
            crs = QgsCoordinateReferenceSystem(export_crs_authid)
            if crs.isValid():
                override_crs = {
                    'authid': crs.authid(),
                    'proj4': crs.toProj(),
                    'wkt': crs.toWkt(),
                    'srid': crs.postgisSrid(),
                    'description': crs.description(),
                }
                logger.info(f"Export CRS override: {crs.authid()}")
        except Exception as e:
            logger.debug(f"Could not resolve export CRS {export_crs_authid}: {e}")

    for lid in layer_map:
        layer = source_project.mapLayer(lid)
        if not layer:
            continue
        # Extract style only when save_styles is checked
        if save_styles:
            try:
                from qgis.PyQt.QtXml import QDomDocument
                doc = QDomDocument()
                layer.exportNamedStyle(doc)
                layer_styles[lid] = doc.toString()
            except Exception as e:
                logger.debug(f"Could not export style for layer {lid}: {e}")
        # CRS: use export CRS if data was reprojected, else source layer CRS
        if override_crs:
            layer_crs[lid] = override_crs
        else:
            try:
                crs = layer.crs()
                if crs.isValid():
                    layer_crs[lid] = {
                        'authid': crs.authid(),
                        'proj4': crs.toProj(),
                        'wkt': crs.toWkt(),
                        'srid': crs.postgisSrid(),
                        'description': crs.description(),
                    }
            except Exception as e:
                logger.debug(f"Could not read CRS for layer {lid}: {e}")

    # 4. Build project XML
    qgis_version = getattr(Qgis, 'QGIS_VERSION', '3.44.0-Unknown')
    xml_str = _build_project_xml(
        project_title, qgis_version, gpkg_filename,
        layer_map, gpkg_meta, hierarchy,
        layer_styles=layer_styles,
        layer_crs=layer_crs,
    )

    # 5. Write into GPKG via sqlite3
    _insert_project_into_gpkg(gpkg_path, project_title, xml_str)

    logger.info(f"Layer tree project written to GPKG: {gpkg_path}")
    return True


# ---------------------------------------------------------------------------
# GPKG metadata reading (pure sqlite3, no QGIS objects)
# ---------------------------------------------------------------------------

def _read_gpkg_metadata(gpkg_path: str) -> Dict[str, dict]:
    """Read layer metadata from GPKG tables.

    Returns:
        Dict mapping table_name → {geom_column, geom_type, srs_id, authid}
    """
    meta = {}
    conn = sqlite3.connect(gpkg_path)
    try:
        cur = conn.cursor()

        # Get SRS mapping: srs_id → "ORG:CODE"
        srs_map = {}
        try:
            cur.execute(
                "SELECT srs_id, organization, organization_coordsys_id "
                "FROM gpkg_spatial_ref_sys"
            )
            for srs_id, org, code in cur.fetchall():
                srs_map[srs_id] = f"{org.upper()}:{code}" if org else f"EPSG:{code}"
        except sqlite3.OperationalError:
            pass

        # Get geometry columns
        try:
            cur.execute(
                "SELECT table_name, column_name, geometry_type_name, srs_id "
                "FROM gpkg_geometry_columns"
            )
            for table_name, geom_col, geom_type, srs_id in cur.fetchall():
                meta[table_name] = {
                    'geom_column': geom_col,
                    'geom_type': geom_type.upper() if geom_type else 'GEOMETRY',
                    'srs_id': srs_id,
                    'authid': srs_map.get(srs_id, f'EPSG:{srs_id}'),
                }
        except sqlite3.OperationalError:
            pass

        # Also include non-spatial tables from gpkg_contents
        try:
            cur.execute(
                "SELECT table_name FROM gpkg_contents "
                "WHERE data_type IN ('features', 'attributes')"
            )
            for (table_name,) in cur.fetchall():
                if table_name not in meta:
                    meta[table_name] = {
                        'geom_column': '',
                        'geom_type': 'NONE',
                        'srs_id': 0,
                        'authid': 'EPSG:4326',
                    }
        except sqlite3.OperationalError:
            pass

    finally:
        conn.close()

    return meta


def _map_layer_ids_to_gpkg(
    project: 'QgsProject',
    layer_ids: List[str],
    gpkg_meta: Dict[str, dict],
) -> Dict[str, str]:
    """Map original layer IDs to GPKG table names.

    Returns:
        Dict mapping layer_id → gpkg_table_name (only for matching layers).
    """
    result = {}
    gpkg_names_lower = {n.lower(): n for n in gpkg_meta}

    for lid in layer_ids:
        layer = project.mapLayer(lid)
        if not layer:
            continue
        layer_name = layer.name()
        # Try exact match first, then case-insensitive
        if layer_name in gpkg_meta:
            result[lid] = layer_name
        elif layer_name.lower() in gpkg_names_lower:
            result[lid] = gpkg_names_lower[layer_name.lower()]
        else:
            logger.debug(f"Layer '{layer_name}' (id={lid}) not found in GPKG")

    return result


# ---------------------------------------------------------------------------
# Layer tree hierarchy extraction (read-only on source project)
# ---------------------------------------------------------------------------

def _extract_hierarchy(
    project: 'QgsProject',
    layer_id_set: set,
) -> dict:
    """Extract the layer tree hierarchy from the source project.

    Returns a tree structure:
    {
        "type": "group", "name": "root",
        "children": [
            {"type": "group", "name": "GroupA", "children": [...]},
            {"type": "layer", "layer_id": "xxx"},
        ]
    }
    """
    root = project.layerTreeRoot()
    if not root:
        return {"type": "group", "name": "root", "children": []}

    return _extract_node(root, layer_id_set)


def _extract_node(group, layer_id_set: set) -> dict:
    """Recursively extract tree structure (read-only)."""
    children = []

    for child in group.children():
        if isinstance(child, QgsLayerTreeGroup):
            sub = _extract_node(child, layer_id_set)
            if sub["children"]:  # Only include non-empty groups
                children.append(sub)
        elif isinstance(child, QgsLayerTreeLayer):
            lid = child.layerId()
            if lid in layer_id_set:
                children.append({"type": "layer", "layer_id": lid})

    name = group.name() if hasattr(group, 'name') and callable(group.name) else "root"
    return {"type": "group", "name": name, "children": children}


# ---------------------------------------------------------------------------
# Project XML generation (pure Python, no QGIS objects)
# ---------------------------------------------------------------------------


def _build_srs_xml(parent: ET.Element, crs_info: dict) -> None:
    """Build a <spatialrefsys> element with full CRS info."""
    spatial = ET.SubElement(parent, "spatialrefsys", attrib={"nativeFormat": "Wkt"})
    ET.SubElement(spatial, "authid").text = crs_info.get('authid', 'EPSG:4326')
    if 'wkt' in crs_info:
        ET.SubElement(spatial, "wkt").text = crs_info['wkt']
    if 'proj4' in crs_info:
        ET.SubElement(spatial, "proj4").text = crs_info['proj4']
    if 'srid' in crs_info:
        ET.SubElement(spatial, "srid").text = str(crs_info['srid'])
    if 'description' in crs_info:
        ET.SubElement(spatial, "description").text = crs_info['description']


def _embed_style_elements(maplayer: ET.Element, style_xml: str) -> None:
    """Parse exportNamedStyle() XML and embed style elements into <maplayer>.

    The style XML has a <qgis> root with child elements like <renderer-v2>,
    <labeling>, <blendMode>, etc. We extract these and append to maplayer.
    """
    try:
        style_root = ET.fromstring(style_xml)
    except ET.ParseError as e:
        logger.debug(f"Could not parse style XML: {e}")
        return

    # Copy labelsEnabled from style root attributes if present
    labels_enabled = style_root.get('labelsEnabled')
    if labels_enabled is not None:
        maplayer.set('labelsEnabled', labels_enabled)

    # Elements to skip (already set in maplayer or not relevant)
    skip_tags = {'id', 'datasource', 'layername', 'provider', 'srs',
                 'shortname', 'title', 'abstract', 'keywordList'}

    for child in style_root:
        tag = child.tag
        # Skip elements already defined in maplayer
        if tag in skip_tags:
            continue
        maplayer.append(child)

def _build_project_xml(
    project_title: str,
    qgis_version: str,
    gpkg_filename: str,
    layer_map: Dict[str, str],
    gpkg_meta: Dict[str, dict],
    hierarchy: dict,
    layer_styles: Optional[Dict[str, str]] = None,
    layer_crs: Optional[Dict[str, dict]] = None,
) -> str:
    """Build QGIS project XML with styles and CRS from source layers.

    Args:
        project_title: Project title.
        qgis_version: QGIS version string (e.g. "3.44.6-Solothurn").
        gpkg_filename: Basename of the GPKG file (for relative datasource).
        layer_map: layer_id → gpkg_table_name.
        gpkg_meta: gpkg_table_name → {geom_column, geom_type, srs_id, authid}.
        hierarchy: Tree structure from _extract_hierarchy.
        layer_styles: layer_id → style XML string (from exportNamedStyle).
        layer_crs: layer_id → {authid, proj4, wkt, srid, description}.

    Returns:
        Project XML as string.
    """
    if layer_styles is None:
        layer_styles = {}
    if layer_crs is None:
        layer_crs = {}

    # Generate stable IDs for each layer in the embedded project
    embedded_ids = {}
    for lid, table_name in layer_map.items():
        embedded_ids[lid] = f"{table_name}_{uuid.uuid4().hex[:8]}"

    root = ET.Element("qgis", attrib={
        "version": qgis_version,
        "projectname": project_title,
    })

    ET.SubElement(root, "homePath", attrib={"path": ""})
    ET.SubElement(root, "title").text = project_title

    # --- Project CRS (use first layer's CRS) ---
    first_crs = None
    if layer_map:
        first_lid = next(iter(layer_map))
        first_crs = layer_crs.get(first_lid)
    if not first_crs:
        first_table = next(iter(layer_map.values())) if layer_map else None
        first_authid = gpkg_meta.get(first_table, {}).get('authid', 'EPSG:4326') if first_table else 'EPSG:4326'
        first_crs = {'authid': first_authid}

    pcrs = ET.SubElement(root, "projectCrs")
    _build_srs_xml(pcrs, first_crs)

    # --- layer-tree-group ---
    tree_root = ET.SubElement(root, "layer-tree-group")
    cp = ET.SubElement(tree_root, "customproperties")
    ET.SubElement(cp, "Option")
    _build_tree_xml(
        tree_root, hierarchy, embedded_ids, layer_map,
        gpkg_meta, gpkg_filename,
    )
    ET.SubElement(tree_root, "custom-order", attrib={"enabled": "0"})

    # --- projectlayers ---
    proj_layers = ET.SubElement(root, "projectlayers")
    for lid, table_name in layer_map.items():
        emb_id = embedded_ids[lid]
        meta = gpkg_meta.get(table_name, {})
        geom_type_raw = meta.get('geom_type', 'GEOMETRY')
        geom_str, wkb_type, simplify_hints = _GEOM_TYPE_MAP.get(
            geom_type_raw, ('Unknown', 'Unknown', '0')
        )
        datasource = f"./{gpkg_filename}|layername={table_name}"

        ml = ET.SubElement(proj_layers, "maplayer", attrib={
            "type": "vector",
            "geometry": geom_str,
            "wkbType": wkb_type,
            "maxScale": "0",
            "minScale": "1e+08",
            "autoRefreshEnabled": "0",
            "hasScaleBasedVisibilityFlag": "0",
            "simplifyDrawingHints": simplify_hints,
            "simplifyDrawingTol": "1",
            "simplifyAlgorithm": "0",
            "simplifyMaxScale": "1",
            "simplifyLocal": "1",
            "readOnly": "0",
        })
        ET.SubElement(ml, "id").text = emb_id
        ET.SubElement(ml, "datasource").text = datasource
        ET.SubElement(ml, "layername").text = table_name
        provider_el = ET.SubElement(ml, "provider", attrib={"encoding": "UTF-8"})
        provider_el.text = "ogr"

        # CRS from source layer (full info) or fallback to GPKG metadata
        crs_info = layer_crs.get(lid)
        if not crs_info:
            crs_info = {'authid': meta.get('authid', 'EPSG:4326')}
        srs = ET.SubElement(ml, "srs")
        _build_srs_xml(srs, crs_info)

        # Embed style from source layer (renderer, labeling, etc.)
        style_xml = layer_styles.get(lid)
        if style_xml:
            _embed_style_elements(ml, style_xml)

    # Serialize with DOCTYPE
    xml_body = ET.tostring(root, encoding="unicode", xml_declaration=True)
    doctype = "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"
    # Insert DOCTYPE after XML declaration
    if xml_body.startswith("<?xml"):
        decl_end = xml_body.index("?>") + 2
        return xml_body[:decl_end] + "\n" + doctype + xml_body[decl_end:]
    return doctype + xml_body


def _build_tree_xml(
    parent_el: ET.Element,
    node: dict,
    embedded_ids: Dict[str, str],
    layer_map: Dict[str, str],
    gpkg_meta: Dict[str, dict],
    gpkg_filename: str,
) -> None:
    """Recursively build <layer-tree-group> / <layer-tree-layer> elements."""
    for child in node.get("children", []):
        if child["type"] == "group":
            group_el = ET.SubElement(parent_el, "layer-tree-group", attrib={
                "name": child["name"],
                "expanded": "1",
                "checked": "Qt::Checked",
            })
            cp = ET.SubElement(group_el, "customproperties")
            ET.SubElement(cp, "Option")
            _build_tree_xml(
                group_el, child, embedded_ids, layer_map,
                gpkg_meta, gpkg_filename,
            )
        elif child["type"] == "layer":
            lid = child["layer_id"]
            if lid not in embedded_ids:
                continue
            emb_id = embedded_ids[lid]
            table_name = layer_map[lid]
            datasource = f"./{gpkg_filename}|layername={table_name}"

            layer_el = ET.SubElement(parent_el, "layer-tree-layer", attrib={
                "id": emb_id,
                "source": datasource,
                "providerKey": "ogr",
                "name": table_name,
                "expanded": "0",
                "checked": "Qt::Checked",
            })
            cp = ET.SubElement(layer_el, "customproperties")
            ET.SubElement(cp, "Option")


# ---------------------------------------------------------------------------
# GPKG sqlite3 writer
# ---------------------------------------------------------------------------

def _insert_project_into_gpkg(
    gpkg_path: str,
    project_name: str,
    xml_str: str,
) -> None:
    """Insert the project XML into the GPKG's qgis_projects table.

    Uses the QGIS GeoPackage project storage format:
    - Table: qgis_projects (name TEXT PK, metadata BLOB, content BLOB)
    - Content is hex-encoded QGZ (ZIP containing .qgs XML)
    - QGIS always calls unzip() on storage-retrieved projects (no format check)
    """
    xml_bytes = xml_str.encode("utf-8")

    # Wrap XML in QGZ format (ZIP archive containing a .qgs file).
    # QGIS unconditionally calls unzip() on project storage content
    # (see QgsProject::read() — no isZipFile check for storage URIs).
    qgz_buffer = io.BytesIO()
    with zipfile.ZipFile(qgz_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{project_name}.qgs", xml_bytes)
    qgz_bytes = qgz_buffer.getvalue()

    # QGIS stores content as hex-encoded text (see writeProject in
    # qgsgeopackageprojectstorage.cpp: content.toHex())
    hex_content = qgz_bytes.hex()

    # Metadata JSON matching QGIS format
    metadata = (
        f'{{"last_modified_time": "{datetime.now().isoformat()}", '
        f'"last_modified_user": "FilterMate"}}'
    )

    conn = sqlite3.connect(gpkg_path)
    try:
        cur = conn.cursor()

        # Create table if needed (matches QgsGeoPackageProjectStorage schema)
        cur.execute(
            "CREATE TABLE IF NOT EXISTS qgis_projects ("
            "  name TEXT PRIMARY KEY NOT NULL,"
            "  metadata BLOB,"
            "  content BLOB"
            ")"
        )

        # Register GPKG extension (URL matches QGIS source)
        try:
            cur.execute(
                "INSERT OR IGNORE INTO gpkg_extensions "
                "(table_name, column_name, extension_name, definition, scope) "
                "VALUES ('qgis_projects', NULL, 'qgis', "
                "'https://github.com/qgis/QGIS', 'read-write')"
            )
        except sqlite3.OperationalError:
            pass  # gpkg_extensions might not exist in minimal GPKGs

        # Insert or replace the project (content as hex-encoded QGZ)
        cur.execute(
            "INSERT OR REPLACE INTO qgis_projects (name, metadata, content) "
            "VALUES (?, ?, ?)",
            (project_name, metadata, hex_content),
        )

        conn.commit()
        logger.debug(
            f"Inserted project '{project_name}' into GPKG "
            f"({len(xml_bytes)} bytes XML, {len(qgz_bytes)} bytes QGZ, "
            f"{len(hex_content)} chars hex)"
        )
    finally:
        conn.close()

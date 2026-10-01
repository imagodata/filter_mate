"""
Point Cloud Support - Pure Python helpers for point cloud layer registration.

Constants, capability predicate and the ``PROJECT_LAYERS`` property template
used when a ``QgsPointCloudLayer`` (LAS/LAZ/COPC) is registered by FilterMate.

This is a PURE PYTHON module with NO QGIS dependencies.
"""
import copy
from typing import Dict, Optional

POINT_CLOUD_PROVIDER_TYPE = "pointcloud"
POINT_CLOUD_GEOMETRY_TYPE = "GeometryType.PointCloud"
POINT_CLOUD_MIN_QGIS_VERSION_INT = 32600

ASPRS_CLASS_NAMES: Dict[int, str] = {
    0: "Created, never classified",
    1: "Unclassified",
    2: "Ground",
    3: "Low vegetation",
    4: "Medium vegetation",
    5: "High vegetation",
    6: "Building",
    7: "Low point (noise)",
    8: "Reserved",
    9: "Water",
    10: "Rail",
    11: "Road surface",
    12: "Reserved",
    13: "Wire - guard (shield)",
    14: "Wire - conductor (phase)",
    15: "Transmission tower",
    16: "Wire-structure connector",
    17: "Bridge deck",
    18: "High noise",
}


def asprs_class_label(code: int) -> str:
    """Return a display label for an ASPRS classification code.

    Args:
        code: Classification code (0-255).

    Returns:
        ``"2 - Ground"`` for known codes, ``"42 - Class 42"`` otherwise.
    """
    name = ASPRS_CLASS_NAMES.get(code)
    if name is None:
        name = f"Class {code}"
    return f"{code} - {name}"


def supports_point_cloud_filtering(
    qgis_version_int: int,
    feature_enabled: bool,
    has_point_cloud_type: bool = True,
) -> bool:
    """Tell whether point cloud filtering can be offered.

    Args:
        qgis_version_int: ``Qgis.QGIS_VERSION_INT``; anything that is not a
            plain ``int`` (e.g. a mock) disables the feature.
        feature_enabled: Value of ``APP.OPTIONS.POINT_CLOUD.enabled``.
        has_point_cloud_type: Whether ``QgsPointCloudLayer`` resolved to a real type.

    Returns:
        True only when every condition holds and the version is recent enough.
    """
    if not feature_enabled or not has_point_cloud_type:
        return False
    if isinstance(qgis_version_int, bool) or not isinstance(qgis_version_int, int):
        return False
    return qgis_version_int >= POINT_CLOUD_MIN_QGIS_VERSION_INT


def build_point_cloud_layer_properties(
    layer_id: str,
    layer_name: str,
    crs_authid: str,
    qgis_provider: str,
    default_is_linking: bool = False,
) -> dict:
    """Build the ``PROJECT_LAYERS`` entry for a point cloud layer.

    The key set mirrors the vector templates of ``LayersManagementEngineTask``
    so downstream consumers can index the sections without ``KeyError``.

    Args:
        layer_id: QGIS layer id.
        layer_name: Layer display name (also used as table name).
        crs_authid: CRS authority id (``"EPSG:2154"``), empty when unknown.
        qgis_provider: QGIS provider key (``copc``, ``ept``, ``vpc``, ``pdal``).
        default_is_linking: Initial value of ``exploring.is_linking``.

    Returns:
        Fresh dict with ``infos``, ``exploring`` and ``filtering`` sections.
    """
    return {
        "infos": {
            "layer_geometry_type": POINT_CLOUD_GEOMETRY_TYPE,
            "layer_name": layer_name,
            "layer_table_name": layer_name,
            "layer_id": layer_id,
            "layer_schema": "",
            "is_already_subset": False,
            "layer_provider_type": POINT_CLOUD_PROVIDER_TYPE,
            "layer_crs_authid": crs_authid or "",
            "primary_key_name": "",
            "primary_key_idx": -1,
            "primary_key_type": "",
            "layer_geometry_field": "",
            "primary_key_is_numeric": False,
            "is_current_layer": False,
            "postgresql_connection_available": False,
            "psycopg2_connection_available": False,
            "point_cloud_provider": qgis_provider or "",
        },
        "exploring": {
            "is_changing_all_layer_properties": True,
            "is_tracking": False,
            "is_selecting": False,
            "is_linking": bool(default_is_linking),
            "current_exploring_groupbox": "single_selection",
            "single_selection_expression": "",
            "multiple_selection_expression": "",
            "custom_selection_expression": "",
        },
        "filtering": {
            "has_layers_to_filter": False,
            "layers_to_filter": [],
            "has_combine_operator": False,
            "source_layer_combine_operator": "AND",
            "other_layers_combine_operator": "AND",
            "has_geometric_predicates": False,
            "geometric_predicates": [],
            "use_centroids_source_layer": False,
            "use_centroids_distant_layers": False,
            "has_buffer_value": False,
            "buffer_value": 0.0,
            "buffer_value_property": False,
            "buffer_value_expression": "",
            "has_buffer_type": False,
            "buffer_type": "Round",
            "buffer_segments": 5,
            "has_simplify_tolerance": False,
            "simplify_tolerance": 0.0,
        },
    }


def ensure_point_cloud_layer_properties(layer_props: dict, template: dict) -> bool:
    """Fill in-place the keys missing from ``layer_props`` using ``template``.

    Existing values are never overwritten; a section that is missing or not a
    dict is replaced by a deep copy of the template section.

    Args:
        layer_props: Properties loaded from persistence (mutated in place).
        template: Reference dict from :func:`build_point_cloud_layer_properties`.

    Returns:
        True when at least one key or section was added.
    """
    added = False
    for section, defaults in template.items():
        current = layer_props.get(section)
        if not isinstance(current, dict):
            layer_props[section] = copy.deepcopy(defaults)
            added = True
            continue
        for key, value in defaults.items():
            if key not in current:
                current[key] = copy.deepcopy(value)
                added = True
    return added


def is_point_cloud_layer_props(layer_props: Optional[dict]) -> bool:
    """Tell whether a ``PROJECT_LAYERS`` entry describes a point cloud layer.

    Args:
        layer_props: Entry to inspect, possibly None or malformed.

    Returns:
        True when ``infos.layer_provider_type`` equals ``POINT_CLOUD_PROVIDER_TYPE``.
    """
    if not isinstance(layer_props, dict):
        return False
    infos = layer_props.get("infos")
    if not isinstance(infos, dict):
        return False
    return infos.get("layer_provider_type") == POINT_CLOUD_PROVIDER_TYPE

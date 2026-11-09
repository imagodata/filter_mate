# -*- coding: utf-8 -*-
"""
Raster Support - Pure Python helpers for raster layer registration.

Constants, capability predicate and the ``PROJECT_LAYERS`` property template
used when a ``QgsRasterLayer`` is registered by FilterMate. The template keeps
the vector key set so the shared FILTERING widgets (predicates, buffer, layers
to filter, combine operators) can store their values for a raster source.

This is a PURE PYTHON module with NO QGIS dependencies.
"""
import copy

RASTER_PROVIDER_TYPE = "raster"
RASTER_GEOMETRY_TYPE = "GeometryType.Raster"
RASTER_MIN_QGIS_VERSION_INT = 32200

# Providers whose file can be read by GDAL directly, which is what the
# derived (clipped) VRT of a raster target is built from.
GDAL_FILE_PROVIDERS = ("gdal",)


def supports_raster_filtering(qgis_version_int: int, feature_enabled: bool, has_raster_type: bool = True) -> bool:
    """Tell whether raster exploring and filtering can be offered.

    Args:
        qgis_version_int: ``Qgis.QGIS_VERSION_INT``; anything that is not a
            plain ``int`` (e.g. a mock) disables the feature.
        feature_enabled: Value of ``APP.OPTIONS.RASTER.enabled``.
        has_raster_type: Whether ``QgsRasterLayer`` resolved to a real type.

    Returns:
        True only when every condition holds and the version is recent enough.
    """
    if not feature_enabled or not has_raster_type:
        return False
    if isinstance(qgis_version_int, bool) or not isinstance(qgis_version_int, int):
        return False
    return qgis_version_int >= RASTER_MIN_QGIS_VERSION_INT


def build_raster_layer_properties(
    layer_id: str,
    layer_name: str,
    crs_authid: str,
    qgis_provider: str,
    default_is_linking: bool = False,
) -> dict:
    """Build the ``PROJECT_LAYERS`` entry for a raster layer.

    The key set mirrors the vector templates of ``LayersManagementEngineTask``
    so downstream consumers can index the sections without ``KeyError``.

    Args:
        layer_id: QGIS layer id.
        layer_name: Layer display name (also used as table name).
        crs_authid: CRS authority id (``"EPSG:2154"``), empty when unknown.
        qgis_provider: QGIS provider key (``gdal``, ``wms``, ``postgresraster``...).
        default_is_linking: Initial value of ``exploring.is_linking``.

    Returns:
        Fresh dict with ``infos``, ``exploring`` and ``filtering`` sections.
    """
    return {
        "infos": {
            "layer_geometry_type": RASTER_GEOMETRY_TYPE,
            "layer_name": layer_name,
            "layer_table_name": layer_name,
            "layer_id": layer_id,
            "layer_schema": "",
            "is_already_subset": False,
            "layer_provider_type": RASTER_PROVIDER_TYPE,
            "layer_crs_authid": crs_authid or "",
            "primary_key_name": "",
            "primary_key_idx": -1,
            "primary_key_type": "",
            "layer_geometry_field": "",
            "primary_key_is_numeric": False,
            "is_current_layer": False,
            "postgresql_connection_available": False,
            "psycopg2_connection_available": False,
            "raster_provider": qgis_provider or "",
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


def ensure_raster_layer_properties(layer_props: dict, template: dict) -> bool:
    """Add the template keys missing from a stored raster entry, in place.

    Args:
        layer_props: Entry read back from the FilterMate database.
        template: Fresh template from :func:`build_raster_layer_properties`.

    Returns:
        True when at least one key was added.
    """
    changed = False
    for section, values in template.items():
        current = layer_props.get(section)
        if not isinstance(current, dict):
            layer_props[section] = copy.deepcopy(values)
            changed = True
            continue
        for key, value in values.items():
            if key not in current:
                current[key] = copy.deepcopy(value)
                changed = True
    return changed

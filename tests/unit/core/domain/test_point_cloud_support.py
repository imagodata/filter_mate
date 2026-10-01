# -*- coding: utf-8 -*-
"""
Tests for core.domain.point_cloud_support.

PURE PYTHON tests -- no QGIS dependency. They pin the constants, the
capability predicate and the exact ``PROJECT_LAYERS`` key schema that the
registration path (WP-D) and the UI consumers rely on.
"""
import ast
import inspect
from unittest.mock import MagicMock

import pytest

import core.domain as domain_pkg
import core.domain.point_cloud_support as support_module
from core.domain.point_cloud_support import (
    ASPRS_CLASS_NAMES,
    POINT_CLOUD_GEOMETRY_TYPE,
    POINT_CLOUD_MIN_QGIS_VERSION_INT,
    POINT_CLOUD_PROVIDER_TYPE,
    asprs_class_label,
    build_point_cloud_layer_properties,
    ensure_point_cloud_layer_properties,
    is_point_cloud_layer_props,
    supports_point_cloud_filtering,
)


EXPECTED_INFOS_KEYS = [
    "layer_geometry_type",
    "layer_name",
    "layer_table_name",
    "layer_id",
    "layer_schema",
    "is_already_subset",
    "layer_provider_type",
    "layer_crs_authid",
    "primary_key_name",
    "primary_key_idx",
    "primary_key_type",
    "layer_geometry_field",
    "primary_key_is_numeric",
    "is_current_layer",
    "postgresql_connection_available",
    "psycopg2_connection_available",
    "point_cloud_provider",
]

EXPECTED_EXPLORING_KEYS = [
    "is_changing_all_layer_properties",
    "is_tracking",
    "is_selecting",
    "is_linking",
    "current_exploring_groupbox",
    "single_selection_expression",
    "multiple_selection_expression",
    "custom_selection_expression",
]

EXPECTED_FILTERING_KEYS = [
    "has_layers_to_filter",
    "layers_to_filter",
    "has_combine_operator",
    "source_layer_combine_operator",
    "other_layers_combine_operator",
    "has_geometric_predicates",
    "geometric_predicates",
    "use_centroids_source_layer",
    "use_centroids_distant_layers",
    "has_buffer_value",
    "buffer_value",
    "buffer_value_property",
    "buffer_value_expression",
    "has_buffer_type",
    "buffer_type",
    "buffer_segments",
    "has_simplify_tolerance",
    "simplify_tolerance",
]


def _imported_modules(module) -> set:
    tree = ast.parse(inspect.getsource(module))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    return names


# =========================================================================
# Module hygiene
# =========================================================================

class TestModuleHygiene:
    """The module must stay pure Python."""

    def test_no_qgis_import(self):
        for name in _imported_modules(support_module):
            assert not name.startswith("qgis"), name

    def test_package_reexports(self):
        for name in (
            "POINT_CLOUD_PROVIDER_TYPE",
            "POINT_CLOUD_GEOMETRY_TYPE",
            "POINT_CLOUD_MIN_QGIS_VERSION_INT",
            "ASPRS_CLASS_NAMES",
            "asprs_class_label",
            "supports_point_cloud_filtering",
            "build_point_cloud_layer_properties",
            "ensure_point_cloud_layer_properties",
            "is_point_cloud_layer_props",
        ):
            assert name in domain_pkg.__all__
            assert getattr(domain_pkg, name) is getattr(support_module, name)


# =========================================================================
# Constants
# =========================================================================

class TestConstants:
    """Contract values used as PROJECT_LAYERS markers."""

    def test_provider_and_geometry_markers(self):
        assert POINT_CLOUD_PROVIDER_TYPE == "pointcloud"
        assert POINT_CLOUD_GEOMETRY_TYPE == "GeometryType.PointCloud"

    def test_min_qgis_version(self):
        assert POINT_CLOUD_MIN_QGIS_VERSION_INT == 32600

    def test_asprs_table_covers_standard_codes(self):
        assert sorted(ASPRS_CLASS_NAMES) == list(range(19))
        assert ASPRS_CLASS_NAMES[0] == "Created, never classified"
        assert ASPRS_CLASS_NAMES[1] == "Unclassified"
        assert ASPRS_CLASS_NAMES[2] == "Ground"
        assert ASPRS_CLASS_NAMES[3] == "Low vegetation"
        assert ASPRS_CLASS_NAMES[4] == "Medium vegetation"
        assert ASPRS_CLASS_NAMES[5] == "High vegetation"
        assert ASPRS_CLASS_NAMES[6] == "Building"
        assert ASPRS_CLASS_NAMES[7] == "Low point (noise)"
        assert ASPRS_CLASS_NAMES[8] == "Reserved"
        assert ASPRS_CLASS_NAMES[9] == "Water"
        assert ASPRS_CLASS_NAMES[10] == "Rail"
        assert ASPRS_CLASS_NAMES[11] == "Road surface"
        assert ASPRS_CLASS_NAMES[12] == "Reserved"
        assert ASPRS_CLASS_NAMES[13] == "Wire - guard (shield)"
        assert ASPRS_CLASS_NAMES[14] == "Wire - conductor (phase)"
        assert ASPRS_CLASS_NAMES[15] == "Transmission tower"
        assert ASPRS_CLASS_NAMES[16] == "Wire-structure connector"
        assert ASPRS_CLASS_NAMES[17] == "Bridge deck"
        assert ASPRS_CLASS_NAMES[18] == "High noise"


# =========================================================================
# asprs_class_label
# =========================================================================

class TestAsprsClassLabel:
    """Display labels for classification codes."""

    def test_known_code(self):
        assert asprs_class_label(2) == "2 - Ground"
        assert asprs_class_label(0) == "0 - Created, never classified"
        assert asprs_class_label(18) == "18 - High noise"

    def test_unknown_code(self):
        assert asprs_class_label(42) == "42 - Class 42"
        assert asprs_class_label(255) == "255 - Class 255"


# =========================================================================
# supports_point_cloud_filtering
# =========================================================================

class TestSupportsPointCloudFiltering:
    """Capability predicate combining flag, class availability and version."""

    def test_all_conditions_met(self):
        assert supports_point_cloud_filtering(32600, True) is True
        assert supports_point_cloud_filtering(34400, True, True) is True

    def test_flag_off(self):
        assert supports_point_cloud_filtering(34400, False) is False

    def test_missing_type(self):
        assert supports_point_cloud_filtering(34400, True, has_point_cloud_type=False) is False

    def test_version_too_old(self):
        assert supports_point_cloud_filtering(32599, True) is False
        assert supports_point_cloud_filtering(32200, True) is False

    def test_non_int_version_is_rejected(self):
        assert supports_point_cloud_filtering(MagicMock(), True) is False
        assert supports_point_cloud_filtering("34400", True) is False
        assert supports_point_cloud_filtering(34400.0, True) is False
        assert supports_point_cloud_filtering(None, True) is False
        assert supports_point_cloud_filtering(True, True) is False

    def test_truthy_flag_returns_strict_bool(self):
        result = supports_point_cloud_filtering(34400, "yes")
        assert result is True


# =========================================================================
# build_point_cloud_layer_properties
# =========================================================================

class TestBuildPointCloudLayerProperties:
    """Exact PROJECT_LAYERS schema for a point cloud entry."""

    def _build(self, **overrides):
        params = dict(
            layer_id="pc_layer_1",
            layer_name="lidar_tile",
            crs_authid="EPSG:2154",
            qgis_provider="copc",
        )
        params.update(overrides)
        return build_point_cloud_layer_properties(**params)

    def test_top_level_sections(self):
        props = self._build()
        assert list(props.keys()) == ["infos", "exploring", "filtering"]

    def test_infos_keys_exact(self):
        props = self._build()
        assert list(props["infos"].keys()) == EXPECTED_INFOS_KEYS

    def test_exploring_keys_exact(self):
        props = self._build()
        assert list(props["exploring"].keys()) == EXPECTED_EXPLORING_KEYS

    def test_filtering_keys_exact(self):
        props = self._build()
        assert list(props["filtering"].keys()) == EXPECTED_FILTERING_KEYS

    def test_infos_values(self):
        infos = self._build()["infos"]
        assert infos["layer_geometry_type"] == POINT_CLOUD_GEOMETRY_TYPE
        assert infos["layer_name"] == "lidar_tile"
        assert infos["layer_table_name"] == "lidar_tile"
        assert infos["layer_id"] == "pc_layer_1"
        assert infos["layer_schema"] == ""
        assert infos["is_already_subset"] is False
        assert infos["layer_provider_type"] == POINT_CLOUD_PROVIDER_TYPE
        assert infos["layer_crs_authid"] == "EPSG:2154"
        assert infos["primary_key_name"] == ""
        assert infos["primary_key_idx"] == -1
        assert infos["primary_key_type"] == ""
        assert infos["layer_geometry_field"] == ""
        assert infos["primary_key_is_numeric"] is False
        assert infos["is_current_layer"] is False
        assert infos["postgresql_connection_available"] is False
        assert infos["psycopg2_connection_available"] is False
        assert infos["point_cloud_provider"] == "copc"

    def test_exploring_values(self):
        exploring = self._build()["exploring"]
        assert exploring["is_changing_all_layer_properties"] is True
        assert exploring["is_tracking"] is False
        assert exploring["is_selecting"] is False
        assert exploring["is_linking"] is False
        assert exploring["current_exploring_groupbox"] == "single_selection"
        assert exploring["single_selection_expression"] == ""
        assert exploring["multiple_selection_expression"] == ""
        assert exploring["custom_selection_expression"] == ""

    def test_filtering_values(self):
        filtering = self._build()["filtering"]
        assert filtering["has_layers_to_filter"] is False
        assert filtering["layers_to_filter"] == []
        assert filtering["has_combine_operator"] is False
        assert filtering["source_layer_combine_operator"] == "AND"
        assert filtering["other_layers_combine_operator"] == "AND"
        assert filtering["has_geometric_predicates"] is False
        assert filtering["geometric_predicates"] == []
        assert filtering["use_centroids_source_layer"] is False
        assert filtering["use_centroids_distant_layers"] is False
        assert filtering["has_buffer_value"] is False
        assert filtering["buffer_value"] == 0.0
        assert isinstance(filtering["buffer_value"], float)
        assert filtering["buffer_value_property"] is False
        assert filtering["buffer_value_expression"] == ""
        assert filtering["has_buffer_type"] is False
        assert filtering["buffer_type"] == "Round"
        assert filtering["buffer_segments"] == 5
        assert filtering["has_simplify_tolerance"] is False
        assert filtering["simplify_tolerance"] == 0.0
        assert isinstance(filtering["simplify_tolerance"], float)

    def test_default_is_linking_propagated(self):
        assert self._build(default_is_linking=True)["exploring"]["is_linking"] is True

    def test_no_spatial_index_pending(self):
        assert "spatial_index_pending" not in self._build()["infos"]

    def test_empty_crs_and_provider_become_empty_strings(self):
        infos = self._build(crs_authid=None, qgis_provider=None)["infos"]
        assert infos["layer_crs_authid"] == ""
        assert infos["point_cloud_provider"] == ""

    def test_each_call_returns_independent_containers(self):
        first = self._build()
        second = self._build()
        first["filtering"]["layers_to_filter"].append("other")
        assert second["filtering"]["layers_to_filter"] == []
        assert first["infos"] is not second["infos"]

    def test_recognised_as_point_cloud(self):
        assert is_point_cloud_layer_props(self._build()) is True


# =========================================================================
# ensure_point_cloud_layer_properties
# =========================================================================

class TestEnsurePointCloudLayerProperties:
    """Backfill of missing keys from a template."""

    def _template(self):
        return build_point_cloud_layer_properties("id", "name", "EPSG:2154", "copc")

    def test_complete_props_untouched(self):
        props = self._template()
        snapshot = build_point_cloud_layer_properties("id", "name", "EPSG:2154", "copc")
        assert ensure_point_cloud_layer_properties(props, self._template()) is False
        assert props == snapshot

    def test_missing_keys_are_added_without_overwriting(self):
        props = {
            "infos": {"layer_id": "id", "layer_name": "custom"},
            "exploring": {"is_linking": True},
            "filtering": {"buffer_value": 12.5},
        }
        assert ensure_point_cloud_layer_properties(props, self._template()) is True
        assert set(props["infos"]) == set(EXPECTED_INFOS_KEYS)
        assert set(props["exploring"]) == set(EXPECTED_EXPLORING_KEYS)
        assert set(props["filtering"]) == set(EXPECTED_FILTERING_KEYS)
        assert props["infos"]["layer_name"] == "custom"
        assert props["exploring"]["is_linking"] is True
        assert props["filtering"]["buffer_value"] == 12.5

    def test_missing_section_is_created(self):
        props = {"infos": {"layer_id": "id"}}
        assert ensure_point_cloud_layer_properties(props, self._template()) is True
        assert set(props) == {"infos", "exploring", "filtering"}
        assert props["filtering"]["buffer_type"] == "Round"

    def test_non_dict_section_is_replaced(self):
        props = {"infos": {}, "exploring": None, "filtering": "broken"}
        assert ensure_point_cloud_layer_properties(props, self._template()) is True
        assert isinstance(props["exploring"], dict)
        assert isinstance(props["filtering"], dict)

    def test_added_values_are_copies(self):
        template = self._template()
        props = {"infos": {}, "exploring": {}, "filtering": {}}
        ensure_point_cloud_layer_properties(props, template)
        props["filtering"]["layers_to_filter"].append("x")
        assert template["filtering"]["layers_to_filter"] == []

    def test_empty_props_dict(self):
        props = {}
        assert ensure_point_cloud_layer_properties(props, self._template()) is True
        assert props == self._template()


# =========================================================================
# is_point_cloud_layer_props
# =========================================================================

class TestIsPointCloudLayerProps:
    """Provider marker detection on PROJECT_LAYERS entries."""

    def test_point_cloud_entry(self):
        assert is_point_cloud_layer_props({"infos": {"layer_provider_type": "pointcloud"}}) is True

    def test_vector_entry(self):
        assert is_point_cloud_layer_props({"infos": {"layer_provider_type": "postgresql"}}) is False
        assert is_point_cloud_layer_props({"infos": {"layer_provider_type": "ogr"}}) is False

    def test_missing_marker(self):
        assert is_point_cloud_layer_props({"infos": {}}) is False
        assert is_point_cloud_layer_props({}) is False

    def test_none_and_malformed(self):
        assert is_point_cloud_layer_props(None) is False
        assert is_point_cloud_layer_props("pointcloud") is False
        assert is_point_cloud_layer_props({"infos": "pointcloud"}) is False
        assert is_point_cloud_layer_props({"infos": None}) is False


@pytest.mark.parametrize("code,expected", [(6, "6 - Building"), (9, "9 - Water"), (100, "100 - Class 100")])
def test_asprs_class_label_parametrized(code, expected):
    assert asprs_class_label(code) == expected

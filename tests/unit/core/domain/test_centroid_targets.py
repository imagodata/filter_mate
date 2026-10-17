# -*- coding: utf-8 -*-
"""FilterMate 5: centroids of the FILTERING targets, chosen layer by layer."""
from pathlib import Path

import pytest

from core.domain.centroid_targets import (
    centroid_eligible,
    distant_centroids_for,
    global_centroid_state,
    initial_centroid_layers,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("geometry_type,eligible", [
    ("GeometryType.Polygon", True),
    ("GeometryType.Line", True),
    ("GeometryType.Point", False),
    ("GeometryType.Raster", False),
    ("GeometryType.PointCloud", False),
    (None, False),
])
def test_only_lines_and_polygons_have_centroids(geometry_type, eligible):
    assert centroid_eligible(geometry_type) is eligible


class TestPerTarget:
    def test_the_list_decides_layer_by_layer(self):
        filtering = {"centroid_layers": ["roads"], "use_centroids_distant_layers": True}
        assert distant_centroids_for("roads", filtering, default=True) is True
        assert distant_centroids_for("buildings", filtering, default=True) is False

    def test_an_empty_list_turns_every_target_off(self):
        assert distant_centroids_for("roads", {"centroid_layers": []}, default=True) is False

    def test_without_list_the_global_flag_applies(self):
        assert distant_centroids_for("roads", {"use_centroids_distant_layers": True}, default=True) is True
        assert distant_centroids_for("roads", {}, default=False) is False
        assert distant_centroids_for("roads", None, default=True) is True

    def test_unknown_layer_is_never_tested_by_centroids(self):
        assert distant_centroids_for(None, {"centroid_layers": ["roads"]}) is False


class TestInitialToggles:
    def test_stored_list_restricted_to_listed_targets(self):
        filtering = {"centroid_layers": ["roads", "gone"]}
        assert initial_centroid_layers(filtering, ["roads", "parcels"]) == ["roads"]

    def test_old_projects_with_the_global_flag_turn_every_target_on(self):
        assert initial_centroid_layers({"use_centroids_distant_layers": True}, ["roads", "parcels"]) == ["roads", "parcels"]
        assert initial_centroid_layers({"use_centroids_distant_layers": False}, ["roads"]) == []


class TestGlobalButton:
    def test_all_some_none(self):
        assert global_centroid_state(["a", "b"], ["a", "b", "z"]) is True
        assert global_centroid_state(["a", "b"], ["a"]) is None
        assert global_centroid_state(["a", "b"], []) is False

    def test_no_checked_line_or_polygon_target(self):
        assert global_centroid_state([], ["a"]) is False


@pytest.mark.parametrize("path", ["core/filter/expression_builder.py", "core/services/backend_expression_builder.py"])
def test_both_expression_builders_decide_per_target(path):
    source = (_ROOT / path).read_text(encoding="utf-8")
    assert "distant_centroids_for(" in source or "get('centroid_layers')" in source
    assert "use_centroids=use_centroids" in source

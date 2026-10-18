# -*- coding: utf-8 -*-
"""FilterMate 5 pure domain: layer kinds, cross filter rules, filter states, raster selection."""
import pytest

from core.domain.layer_kind import LayerKind, kind_label
from core.domain.cross_filter import (
    CoverageSide,
    CrossFilterRequest,
    TargetSpec,
    build_in_expression,
    combine_subset,
    coverage_ratio_ok,
    coverage_side_for_predicates,
    predicate_methods,
)
from core.domain.filter_state import CrossOperation, CrossOperationHistory, LayerSnapshot
from core.domain.raster_filter_criteria import RasterSelection, RasterSelectionMode
from core.domain.raster_support import (
    RASTER_GEOMETRY_TYPE,
    build_raster_layer_properties,
    ensure_raster_layer_properties,
    supports_raster_filtering,
)
from core.domain.point_cloud_support import CLASS_PRESETS, LIDAR_HD_CLASS_NAMES, asprs_class_label

pytestmark = pytest.mark.unit


class TestLayerKind:
    def test_flags(self):
        assert LayerKind.VECTOR.is_vector and not LayerKind.VECTOR.is_coverage
        assert LayerKind.RASTER.is_coverage and LayerKind.POINT_CLOUD.is_coverage
        assert not LayerKind.OTHER.is_coverage

    def test_labels(self):
        assert kind_label(LayerKind.POINT_CLOUD) == "Point cloud"
        assert kind_label(LayerKind.OTHER) == "Other"


class TestPredicates:
    def test_labels_map_to_methods(self):
        assert predicate_methods(["Intersect", "Are within", "Contain"]) == ["intersects", "within", "contains"]

    def test_default_is_intersects(self):
        assert predicate_methods([]) == ["intersects"]
        assert predicate_methods(["nonsense"]) == ["intersects"]

    def test_duplicates_removed(self):
        assert predicate_methods(["Intersect", "intersects"]) == ["intersects"]

    @pytest.mark.parametrize("predicates,side", [
        ([], CoverageSide.INSIDE),
        (["Intersect"], CoverageSide.INSIDE),
        (["Are within", "Touch"], CoverageSide.INSIDE),
        (["Disjoint"], CoverageSide.OUTSIDE),
        (["Disjoint", "Intersect"], CoverageSide.ALL),
    ])
    def test_coverage_side(self, predicates, side):
        assert coverage_side_for_predicates(predicates) is side

    def test_request_side_and_targets(self):
        request = CrossFilterRequest(
            "src", LayerKind.RASTER,
            targets=(TargetSpec("a", LayerKind.VECTOR), TargetSpec("b", LayerKind.POINT_CLOUD), TargetSpec("c", LayerKind.VECTOR)),
            predicates=("Disjoint",),
        )
        assert request.side is CoverageSide.OUTSIDE
        assert [t.layer_id for t in request.targets_of(LayerKind.VECTOR)] == ["a", "c"]
        assert request.methods == ["disjoint"]


class TestCoverage:
    def test_disabled(self):
        assert coverage_ratio_ok(100, 0, 0)
        assert coverage_ratio_ok(100, 0, None)

    def test_threshold(self):
        assert coverage_ratio_ok(100, 50, 50)
        assert not coverage_ratio_ok(100, 49.9, 50)

    def test_zero_area_target_passes(self):
        assert coverage_ratio_ok(0, 0, 50)


class TestSubsets:
    def test_in_expression_numbers(self):
        assert build_in_expression("fid", [3, 1, 3]) == '"fid" IN (3, 1)'

    def test_in_expression_strings_escaped(self):
        assert build_in_expression("code", ["a'b"]) == '"code" IN (\'a\'\'b\')'

    def test_in_expression_raw_field(self):
        assert build_in_expression("FID", [1, 2], raw_field=True) == "FID IN (1, 2)"

    def test_in_expression_empty_is_false(self):
        assert build_in_expression("fid", []) == "1 = 0"

    @pytest.mark.parametrize("previous,operator,expected", [
        ("", "AND", "x"),
        ("a = 1", None, "x"),
        ("a = 1", "AND", "(a = 1) AND (x)"),
        ("a = 1", "OR", "(a = 1) OR (x)"),
        ("a = 1", "AND NOT", "(a = 1) AND NOT (x)"),
        ("a = 1", "XOR", "x"),
    ])
    def test_combine(self, previous, operator, expected):
        assert combine_subset(previous, "x", operator) == expected


class TestSnapshotsAndHistory:
    def _snap(self, layer_id, source, derived=False, original=""):
        return LayerSnapshot(layer_id, "raster", source=source, provider="gdal", derived=derived, original_source=original, original_provider="gdal" if original else "")

    def test_snapshot_roundtrip(self):
        snap = self._snap("r", "/c/cut.vrt", True, "/c/mnt.tif")
        assert LayerSnapshot.from_dict(snap.to_dict()) == snap
        assert snap.base_source == "/c/mnt.tif" and snap.base_provider == "gdal"
        assert self._snap("r", "/c/mnt.tif").base_source == "/c/mnt.tif"

    def test_from_dict_ignores_unknown_keys(self):
        assert LayerSnapshot.from_dict({"layer_id": "x", "kind": "vector", "future": 1}).layer_id == "x"

    def test_undo_redo_per_source(self):
        history = CrossOperationHistory()
        before, after = self._snap("r", "/mnt.tif"), self._snap("r", "/cut.vrt", True, "/mnt.tif")
        op = CrossOperation("src", ((before, after),))
        history.push(op)
        assert history.can_undo("src") and not history.can_undo("other")
        assert history.undo("src") is op
        assert history.can_redo("src") and not history.can_undo("src")
        assert history.redo("src") is op
        history.push(CrossOperation("src", ((after, before),)))
        assert not history.can_redo("src")

    def test_empty_operation_ignored(self):
        history = CrossOperationHistory()
        history.push(CrossOperation("src", ()))
        assert not history.can_undo("src")

    def test_depth_and_forget(self):
        history = CrossOperationHistory(max_depth=2)
        for i in range(3):
            history.push(CrossOperation("src", ((self._snap(f"r{i}", "a"), self._snap(f"r{i}", "b")),)))
        assert history.peek_undo("src").layer_ids == ("r2",)
        history.forget_layer("r2")
        assert history.peek_undo("src").layer_ids == ("r1",)
        history.clear()
        assert not history.can_undo("src")

    def test_forget_keeps_the_other_layers_of_an_operation(self):
        history = CrossOperationHistory()
        first = CrossOperation("v", ((self._snap("r2", "a"), self._snap("r2", "b")),))
        second = CrossOperation("v", ((self._snap("r1", "a"), self._snap("r1", "b")),
                                      (self._snap("r2", "b"), self._snap("r2", "c"))))
        r1_alone = CrossOperation("v2", ((self._snap("r1", "a"), self._snap("r1", "b")),))
        for operation in (first, second, r1_alone):
            history.push(operation)
        history.undo("v")  # second is on the redo stack
        history.forget_layer("r1")
        kept = history.peek_redo("v")
        assert kept.op_id == second.op_id and kept.layer_ids == ("r2",)
        assert kept.changes == second.changes[1:]
        assert history.peek_undo("v") is first
        assert not history.can_undo("v2")  # nothing left of an operation on the removed layer alone


class TestRasterSelection:
    def test_seeds_are_points_in_order_without_duplicates(self):
        sel = RasterSelection(minimum=1, seeds=[[1, 2], (3.5, 4), (1.0, 2.0)])
        assert sel.seeds == ((1.0, 2.0), (3.5, 4.0))
        with pytest.raises(ValueError):
            RasterSelection(minimum=1, seeds=[(1, float("nan"))])
        with pytest.raises(ValueError):
            RasterSelection(minimum=1, seeds=[(1, 2, 3)])

    def test_seeds_round_trip_and_older_dicts(self):
        sel = RasterSelection(mode=RasterSelectionMode.EXPRESSION, expression='"o@1" > 3', seeds=((10.0, 20.0),))
        assert sel.to_dict()["seeds"] == [[10.0, 20.0]]
        assert RasterSelection.from_dict(sel.to_dict()) == sel
        assert "seeds" not in RasterSelection(minimum=1).to_dict()  # same dict as before without detection
        assert RasterSelection.from_dict({"mode": "range", "minimum": 1}).seeds == ()

    def test_objects_have_one_seed_each_and_give_the_seeds(self):
        pool = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1}), seeds=((1, 2),))
        roof = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({2}), seeds=((3, 4),))
        both = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1, 2}), objects=(pool, roof))
        assert both.seeds == ((1.0, 2.0), (3.0, 4.0))
        assert RasterSelection.from_dict(both.to_dict()) == both
        with pytest.raises(ValueError):
            RasterSelection(minimum=1, objects=(RasterSelection(minimum=1),))  # an object without its seed

    def test_seeds_are_described(self):
        sel = RasterSelection(minimum=1, maximum=2, seeds=((0, 0), (1, 1)))
        assert sel.describe() == "band 1 in [1 ; 2] · object(s) under 2 click(s)"

    def test_range_formula_and_keeps(self):
        sel = RasterSelection(band=2, minimum=200.0, maximum=260.5)
        assert sel.to_calc_formula("mnt") == '("mnt@2" >= 200 AND "mnt@2" <= 260.5)'
        assert sel.keeps(200) and sel.keeps(260.5) and not sel.keeps(261)

    def test_open_range(self):
        assert RasterSelection(minimum=10).to_calc_formula("r") == '("r@1" >= 10)'
        assert RasterSelection().is_empty
        assert RasterSelection().to_calc_formula("r") == "1"

    def test_classes(self):
        sel = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({6, 2}))
        assert sel.to_calc_formula("ocs") == '("ocs@1" = 2 OR "ocs@1" = 6)'
        assert sel.keeps(2.0) and not sel.keeps(3)
        assert RasterSelection(mode=RasterSelectionMode.CLASSES).is_empty

    def test_expression(self):
        sel = RasterSelection(mode=RasterSelectionMode.EXPRESSION, expression=' "a@1" > 3 ')
        assert sel.to_calc_formula("ignored") == '("a@1" > 3)'
        with pytest.raises(ValueError):
            sel.keeps(1)

    def test_validation(self):
        with pytest.raises(ValueError):
            RasterSelection(band=0)
        with pytest.raises(ValueError):
            RasterSelection(minimum=5, maximum=1)

    def test_roundtrip_and_describe(self):
        sel = RasterSelection(mode=RasterSelectionMode.CLASSES, classes=frozenset({1, 3}))
        assert RasterSelection.from_dict(sel.to_dict()) == sel
        assert "classes 1, 3" in sel.describe()
        assert "[200 ; +∞]" in RasterSelection(minimum=200.0).describe()


class TestRasterSupport:
    def test_supports(self):
        assert supports_raster_filtering(32200, True)
        assert not supports_raster_filtering(32199, True)
        assert not supports_raster_filtering(34000, False)
        assert not supports_raster_filtering(True, True)
        assert not supports_raster_filtering(34000, True, has_raster_type=False)

    def test_template_and_ensure(self):
        props = build_raster_layer_properties("id1", "mnt", "EPSG:2154", "gdal", True)
        assert props["infos"]["layer_geometry_type"] == RASTER_GEOMETRY_TYPE
        assert props["infos"]["raster_provider"] == "gdal"
        assert props["exploring"]["is_linking"] is True
        assert props["filtering"]["geometric_predicates"] == []
        stored = {"infos": {"layer_id": "id1"}, "exploring": "broken"}
        assert ensure_raster_layer_properties(stored, props)
        assert stored["exploring"]["is_tracking"] is False
        assert stored["filtering"]["buffer_type"] == "Round"
        assert not ensure_raster_layer_properties(stored, props)


class TestLidarHdClasses:
    def test_labels(self):
        assert asprs_class_label(66) == "66 - Virtual point"
        assert asprs_class_label(2) == "2 - Ground"
        assert asprs_class_label(200) == "200 - Class 200"
        assert set(LIDAR_HD_CLASS_NAMES) == {64, 65, 66, 67}
        assert CLASS_PRESETS["Buildings"] == (6,)


class TestHistoryTrimming:
    def _op(self, source, layer, name):
        snap = LayerSnapshot(layer, "raster", source=f"/c/{name}.vrt", provider="gdal")
        return CrossOperation(source, ((snap, snap),), description=name)

    def _names(self, history):
        return sorted(op.description for op in history.operations())

    def test_operations_lists_undo_and_redo(self):
        history = CrossOperationHistory()
        history.push(self._op("a", "r", "1"))
        history.push(self._op("a", "r", "2"))
        history.undo("a")
        assert self._names(history) == ["1", "2"]

    def test_drop_oldest_across_sources(self):
        history = CrossOperationHistory()
        for source, name in (("a", "1"), ("b", "2"), ("a", "3")):
            history.push(self._op(source, "r", name))
        assert history.oldest().description == "1"
        step = history.drop_oldest()
        assert step.operation.description == "1" and step.from_undo
        assert history.drop_oldest().operation.description == "2"
        assert not history.can_undo("b")
        assert history.drop_oldest().operation.description == "3"
        assert history.drop_oldest() is None and history.oldest() is None

    def test_drop_keeps_undo_and_redo_order(self):
        history = CrossOperationHistory()
        for name in ("1", "2", "3"):
            history.push(self._op("a", "r", name))
        history.undo("a")  # 3 to redo
        history.undo("a")  # 2 to redo
        assert history.drop_oldest().operation.description == "1"
        assert history.redo("a").description == "2"
        assert history.redo("a").description == "3"

    def test_redo_bottom_is_the_furthest_step(self):
        history = CrossOperationHistory()
        history.push(self._op("a", "r", "1"))
        history.push(self._op("a", "r", "2"))
        history.undo("a")
        history.undo("a")  # redo stack: [2, 1]
        step = history.drop_oldest()
        assert step.operation.description == "2" and not step.from_undo
        assert history.redo("a").description == "1"

    def test_holds_limits_the_stacks_considered(self):
        history = CrossOperationHistory()
        history.push(self._op("a", "r", "1"))
        history.push(self._op("b", "p", "2"))
        holds = lambda op: op.description == "2"  # noqa: E731
        assert history.oldest(holds).description == "2"
        assert history.drop_oldest(holds).operation.description == "2"
        assert history.drop_oldest(holds) is None and history.can_undo("a")

# -*- coding: utf-8 -*-
"""
Unit tests for PostgreSQL Expression Builder.

Tests the PostgreSQLExpressionBuilder class for:
- Predicate sorting and mapping
- Simple WKT expression generation
- EXISTS subquery generation
- Source table reference parsing
- ST_Buffer with endcap styles
- Geographic CRS handling
- Column case normalization
- Numeric type casting
- Geometric filter detection
- Complex query detection
- Supports_layer check

All QGIS dependencies are mocked via the root conftest.py.
"""
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Module-level mock setup -- must run before importing the builder
# ---------------------------------------------------------------------------

def _ensure_module_mocks():
    """Install mock modules required by PostgreSQLExpressionBuilder imports."""
    ROOT = "filter_mate"

    if ROOT not in sys.modules:
        fm = types.ModuleType(ROOT)
        fm.__path__ = []
        fm.__package__ = ROOT
        sys.modules[ROOT] = fm

    mocks_needed = {
        f"{ROOT}.core": MagicMock(),
        f"{ROOT}.core.ports": MagicMock(),
        f"{ROOT}.core.ports.geometric_filter_port": MagicMock(),
        f"{ROOT}.core.filter": MagicMock(),
        f"{ROOT}.core.filter.expression_combiner": MagicMock(),
        f"{ROOT}.infrastructure": MagicMock(),
        f"{ROOT}.infrastructure.database": MagicMock(),
        f"{ROOT}.infrastructure.database.sql_utils": MagicMock(),
        f"{ROOT}.infrastructure.utils": MagicMock(),
        f"{ROOT}.infrastructure.constants": MagicMock(),
        f"{ROOT}.adapters": MagicMock(),
        f"{ROOT}.adapters.backends": MagicMock(),
        f"{ROOT}.adapters.backends.postgresql": MagicMock(),
        f"{ROOT}.adapters.backends.postgresql.filter_chain_optimizer": MagicMock(),
        f"{ROOT}.adapters.backends.postgresql.filter_executor": MagicMock(),
    }

    for mod_name, mock_obj in mocks_needed.items():
        if mod_name not in sys.modules:
            sys.modules[mod_name] = mock_obj

    # Provide a real ABC base for GeometricFilterPort so the builder can subclass
    from abc import ABC

    class _FakeGeometricFilterPort(ABC):
        def __init__(self, task_params):
            self.task_params = task_params
            self._warnings = []

        def log_debug(self, msg): pass
        def log_info(self, msg): pass
        def log_warning(self, msg): self._warnings.append(msg)
        def log_error(self, msg): pass

        def _get_buffer_endcap_style(self):
            return self.task_params.get("buffer_endcap_style", "round")

        def _apply_centroid_transform(self, geom_expr, layer_props):
            return f"ST_PointOnSurface({geom_expr})"

    sys.modules[f"{ROOT}.core.ports.geometric_filter_port"].GeometricFilterPort = _FakeGeometricFilterPort
    # Also ensure safe_set_subset_string is a callable
    sys.modules[f"{ROOT}.infrastructure.database.sql_utils"].safe_set_subset_string = MagicMock(return_value=True)
    sys.modules[f"{ROOT}.infrastructure.database.sql_utils"].sanitize_sql_identifier = lambda x: x

    # Mark chain optimizer as unavailable so import doesn't fail
    chain_mod = sys.modules[f"{ROOT}.adapters.backends.postgresql.filter_chain_optimizer"]
    chain_mod.FilterChainOptimizer = MagicMock
    chain_mod.FilterChainContext = MagicMock
    chain_mod.OptimizationStrategy = MagicMock


_ensure_module_mocks()


# Now import the class under test
import importlib.util
import os


def _load_real_cleanup():
    """The builder names its buffer tables with cleanup.session_token (2026-10-17)."""
    name = "filter_mate.adapters.backends.postgresql.cleanup"
    if isinstance(sys.modules.get(name), types.ModuleType):
        return
    path = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "..",
        "adapters", "backends", "postgresql", "cleanup.py"
    ))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "filter_mate.adapters.backends.postgresql"
    sys.modules[name] = module
    spec.loader.exec_module(module)


_load_real_cleanup()

_builder_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "..",
    "adapters", "backends", "postgresql", "expression_builder.py"
))

_spec = importlib.util.spec_from_file_location(
    "filter_mate.adapters.backends.postgresql.expression_builder",
    _builder_path,
)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = "filter_mate.adapters.backends.postgresql"
sys.modules[_mod.__name__] = _mod
_spec.loader.exec_module(_mod)

PostgreSQLExpressionBuilder = _mod.PostgreSQLExpressionBuilder


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def builder():
    """Create a default PostgreSQLExpressionBuilder with minimal task_params."""
    return PostgreSQLExpressionBuilder(task_params={
        "buffer_endcap_style": "round",
        "buffer_segments": 5,
    })


@pytest.fixture
def mock_pg_layer():
    """Create a mock PostgreSQL layer."""
    layer = MagicMock()
    layer.providerType.return_value = "postgres"
    layer.name.return_value = "test_buildings"
    layer.source.return_value = "dbname='mydb' host=localhost port=5432 sslmode=disable"

    # Fields
    field1 = MagicMock()
    field1.name.return_value = "id"
    field1.typeName.return_value = "integer"
    field2 = MagicMock()
    field2.name.return_value = "Name"
    field2.typeName.return_value = "varchar"
    layer.fields.return_value = [field1, field2]

    return layer


# ===========================================================================
# Tests -- supports_layer
# ===========================================================================

class TestSupportsLayer:
    def test_supports_postgres_layer(self, builder, mock_pg_layer):
        assert builder.supports_layer(mock_pg_layer) is True

    def test_rejects_ogr_layer(self, builder):
        layer = MagicMock()
        layer.providerType.return_value = "ogr"
        assert builder.supports_layer(layer) is False

    def test_rejects_none(self, builder):
        assert builder.supports_layer(None) is False


# ===========================================================================
# Tests -- get_backend_name
# ===========================================================================

class TestGetBackendName:
    def test_returns_postgresql(self, builder):
        assert builder.get_backend_name() == "PostgreSQL"


# ===========================================================================
# Tests -- _sort_predicates
# ===========================================================================

class TestSortPredicates:
    def test_sorts_by_selectivity(self, builder):
        predicates = {
            "intersects": "ST_Intersects",
            "within": "ST_Within",
            "contains": "ST_Contains",
        }
        sorted_result = builder._sort_predicates(predicates)
        names = [item[0] for item in sorted_result]
        # within is most selective (order 1), then contains (2), then intersects (8)
        assert names == ["within", "contains", "intersects"]

    def test_single_predicate(self, builder):
        predicates = {"intersects": "ST_Intersects"}
        sorted_result = builder._sort_predicates(predicates)
        assert len(sorted_result) == 1
        assert sorted_result[0][1] == "ST_Intersects"

    def test_empty_predicates(self, builder):
        assert builder._sort_predicates({}) == []


# ===========================================================================
# Tests -- _parse_source_table_reference
# ===========================================================================

class TestParseSourceTableReference:
    def test_parses_three_part_reference(self, builder):
        ref = '"public"."buildings"."geom"'
        result = builder._parse_source_table_reference(ref)
        assert result == {"schema": "public", "table": "buildings", "geom_field": "geom"}

    def test_parses_two_part_reference(self, builder):
        ref = '"roads"."geometry"'
        result = builder._parse_source_table_reference(ref)
        assert result == {"schema": "public", "table": "roads", "geom_field": "geometry"}

    def test_parses_reference_inside_function(self, builder):
        ref = 'ST_Buffer("ref"."demand_points"."geom", 100)'
        result = builder._parse_source_table_reference(ref)
        assert result["schema"] == "ref"
        assert result["table"] == "demand_points"
        assert result["geom_field"] == "geom"

    def test_returns_none_for_unparseable(self, builder):
        result = builder._parse_source_table_reference("some_random_text")
        assert result is None


# ===========================================================================
# Tests -- _build_simple_wkt_expression
# ===========================================================================

class TestBuildSimpleWktExpression:
    def test_basic_intersects(self, builder):
        expr = builder._build_simple_wkt_expression(
            geom_expr='"buildings"."geom"',
            predicate_func="ST_Intersects",
            source_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            source_srid=2154,
            buffer_value=None,
        )
        assert "ST_Intersects" in expr
        assert "ST_GeomFromText" in expr
        assert "ST_MakeValid" in expr
        assert "2154" in expr

    def test_with_buffer(self, builder):
        expr = builder._build_simple_wkt_expression(
            geom_expr='"t"."geom"',
            predicate_func="ST_Within",
            source_wkt="POINT(0 0)",
            source_srid=2154,
            buffer_value=100,
        )
        assert "ST_Buffer" in expr
        assert "100" in expr

    def test_geographic_crs_buffer(self, builder):
        expr = builder._build_simple_wkt_expression(
            geom_expr='"t"."geom"',
            predicate_func="ST_Intersects",
            source_wkt="POINT(2.3 48.8)",
            source_srid=4326,
            buffer_value=500,
        )
        # 2026-10-17: metric buffer on the geography (EPSG:3857 metres are
        # 1/cos(latitude) too short)
        assert "::geography, 500" in expr
        assert "3857" not in expr

    def test_zero_buffer_ignored(self, builder):
        expr = builder._build_simple_wkt_expression(
            geom_expr='"t"."geom"',
            predicate_func="ST_Intersects",
            source_wkt="POINT(0 0)",
            source_srid=2154,
            buffer_value=0,
        )
        assert "ST_Buffer" not in expr


# ===========================================================================
# Tests -- _build_st_buffer_with_style
# ===========================================================================

class TestBuildStBufferWithStyle:
    def test_positive_buffer_round_endcap(self, builder):
        result = builder._build_st_buffer_with_style('"t"."geom"', 100.0)
        assert "ST_Buffer" in result
        assert "100.0" in result
        assert "quad_segs=5" in result
        # No CASE WHEN for positive buffer
        assert "CASE WHEN" not in result

    def test_negative_buffer_wrapped_in_makevalid(self, builder):
        result = builder._build_st_buffer_with_style('"t"."geom"', -50.0)
        assert "ST_MakeValid" in result
        assert "ST_IsEmpty" in result
        assert "CASE WHEN" in result
        assert "-50.0" in result

    def test_flat_endcap_style(self):
        b = PostgreSQLExpressionBuilder(task_params={
            "buffer_endcap_style": "flat",
            "buffer_segments": 8,
        })
        result = b._build_st_buffer_with_style('"t"."geom"', 25.0)
        assert "endcap=flat" in result
        assert "quad_segs=8" in result


# ===========================================================================
# Tests -- _normalize_column_case
# ===========================================================================

class TestNormalizeColumnCase:
    def test_normalizes_case_mismatch(self, builder, mock_pg_layer):
        expr = '"name" = \'foo\''
        result = builder._normalize_column_case(expr, mock_pg_layer)
        # "name" should become "Name" (matching the field)
        assert '"Name"' in result

    def test_preserves_correct_case(self, builder, mock_pg_layer):
        expr = '"Name" = \'foo\''
        result = builder._normalize_column_case(expr, mock_pg_layer)
        assert '"Name"' in result

    def test_returns_empty_for_empty_expr(self, builder, mock_pg_layer):
        assert builder._normalize_column_case("", mock_pg_layer) == ""
        assert builder._normalize_column_case(None, mock_pg_layer) is None

    def test_returns_expr_for_none_layer(self, builder):
        expr = '"field" = 1'
        assert builder._normalize_column_case(expr, None) == expr


# ===========================================================================
# Tests -- _apply_numeric_type_casting
# ===========================================================================

class TestApplyNumericTypeCasting:
    def test_casts_varchar_comparison(self, builder, mock_pg_layer):
        expr = '"Name" > 100'
        result = builder._apply_numeric_type_casting(expr, mock_pg_layer)
        assert "::numeric" in result

    def test_no_cast_for_integer_field(self, builder, mock_pg_layer):
        expr = '"id" > 100'
        result = builder._apply_numeric_type_casting(expr, mock_pg_layer)
        # "id" is integer, so no ::numeric needed
        assert "::numeric" not in result

    def test_no_double_cast(self, builder, mock_pg_layer):
        expr = '"Name"::numeric > 100'
        result = builder._apply_numeric_type_casting(expr, mock_pg_layer)
        # Should not add a second ::numeric
        assert result.count("::numeric") == 1

    def test_empty_expression(self, builder, mock_pg_layer):
        assert builder._apply_numeric_type_casting("", mock_pg_layer) == ""
        assert builder._apply_numeric_type_casting(None, mock_pg_layer) is None


# ===========================================================================
# Tests -- _is_geometric_filter
# ===========================================================================

class TestIsGeometricFilter:
    def test_detects_exists(self, builder):
        assert builder._is_geometric_filter("EXISTS (SELECT 1 FROM ...)") is True

    def test_detects_st_intersects(self, builder):
        assert builder._is_geometric_filter('ST_INTERSECTS("t"."geom", ...)') is True

    def test_detects_source_alias(self, builder):
        assert builder._is_geometric_filter("__source.geom") is True

    def test_non_geometric_filter(self, builder):
        assert builder._is_geometric_filter('"id" IN (1, 2, 3)') is False

    def test_detects_st_buffer(self, builder):
        assert builder._is_geometric_filter("ST_Buffer(geom, 100)") is True


# ===========================================================================
# Tests -- _detect_and_warn_complex_query
# ===========================================================================

class TestDetectComplexQuery:
    def test_detects_buffer_plus_chaining(self, builder):
        builder._detect_and_warn_complex_query(
            buffer_expression="if(homecount > 100, 50, 1)",
            source_filter="EXISTS (SELECT 1 FROM zone_pop ...)",
            layer_name="test"
        )
        assert builder._is_complex_query is True

    def test_no_complex_when_no_buffer(self, builder):
        builder._detect_and_warn_complex_query(
            buffer_expression=None,
            source_filter="EXISTS (SELECT 1 FROM zone_pop ...)",
            layer_name="test"
        )
        assert builder._is_complex_query is False

    def test_no_complex_when_no_exists(self, builder):
        builder._detect_and_warn_complex_query(
            buffer_expression="100",
            source_filter='"id" IN (1, 2, 3)',
            layer_name="test"
        )
        assert builder._is_complex_query is False


# ===========================================================================
# Tests -- PREDICATE_FUNCTIONS mapping
# ===========================================================================

class TestPredicateFunctions:
    def test_all_standard_predicates_mapped(self, builder):
        expected = [
            "intersects", "contains", "within", "touches",
            "overlaps", "crosses", "disjoint", "equals",
            "covers", "coveredby",
        ]
        for pred in expected:
            assert pred in builder.PREDICATE_FUNCTIONS, f"Missing predicate: {pred}"
            assert builder.PREDICATE_FUNCTIONS[pred].startswith("ST_")

    def test_intersects_maps_correctly(self, builder):
        assert builder.PREDICATE_FUNCTIONS["intersects"] == "ST_Intersects"


# ===========================================================================
# Tests -- build_expression (integration-style with mocks)
# ===========================================================================

class TestBuildExpression:
    def test_no_predicates_returns_no_results(self, builder):
        result = builder.build_expression(
            layer_props={"layer_name": "test", "layer_schema": "public"},
            predicates={},
            source_wkt="POINT(0 0)",
            source_srid=2154,
            source_feature_count=10,
        )
        assert result == "1 = 0"

    def test_simple_wkt_mode_small_dataset(self, builder):
        result = builder.build_expression(
            layer_props={"layer_name": "test", "layer_table_name": "test"},
            predicates={"intersects": "ST_Intersects"},
            source_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            source_srid=2154,
            source_feature_count=10,
        )
        assert "ST_Intersects" in result
        assert "ST_GeomFromText" in result

    def test_exists_mode_large_dataset(self, builder):
        result = builder.build_expression(
            layer_props={"layer_name": "test", "layer_table_name": "test"},
            predicates={"intersects": "ST_Intersects"},
            source_geom='"public"."source"."geom"',
            source_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            source_srid=2154,
            source_feature_count=500,
        )
        assert "EXISTS" in result
        assert "__source" in result


class TestNoSilentEmptyFilter:
    """2026-10-16: a WKT-only source (non-PostgreSQL source layer) must never end as "1 = 0".

    MAX_WKT_LENGTH relied on the SpatiaLite executor shrinking the source to
    ~100 KB; with an exact source the EXISTS branch received a WKT, could not
    parse a table reference and every PostgreSQL target came out empty.
    """

    def _build(self, builder, **kwargs):
        args = dict(
            layer_props={"layer_name": "roads", "layer_table_name": "roads"},
            predicates={"crosses": "ST_Crosses"},
            source_srid=2154,
        )
        args.update(kwargs)
        return builder.build_expression(**args)

    def test_many_features_small_wkt_without_source_table_inlines_the_wkt(self, builder):
        wkt = "MULTILINESTRING((0 0, 1 1), (2 2, 3 3))"
        result = self._build(builder, source_geom=wkt, source_wkt=wkt, source_feature_count=691)
        assert result != "1 = 0"
        assert "ST_Crosses" in result and "ST_GeomFromText" in result
        assert "EXISTS" not in result

    def test_large_wkt_without_source_table_returns_none_for_ogr_fallback(self, builder):
        wkt = "MULTILINESTRING((0 0" + ", 1 1" * (builder.MAX_WKT_LENGTH // 5) + "))"
        result = self._build(builder, source_geom=wkt, source_wkt=wkt, source_feature_count=691)
        assert result is None

    def test_no_source_at_all_returns_none(self, builder):
        assert self._build(builder, source_geom=None, source_wkt=None, source_feature_count=691) is None

    def test_large_wkt_with_source_table_uses_exists(self, builder):
        wkt = "MULTILINESTRING((0 0" + ", 1 1" * (builder.MAX_WKT_LENGTH // 5) + "))"
        result = self._build(
            builder, source_geom='"public"."rivers"."geom"', source_wkt=wkt, source_feature_count=691
        )
        # 2026-10-17: crosses runs against the union of the source table rows
        assert 'ST_Crosses("roads"."geom", (SELECT ST_Union(__source."geom") FROM "public"."rivers" AS __source))' in result
        assert "ST_GeomFromText" not in result

    def test_unbuildable_predicates_return_none_not_empty_filter(self, builder, monkeypatch):
        monkeypatch.setattr(builder, "_build_exists_expression", lambda **kwargs: None)
        result = self._build(
            builder, source_geom='"public"."rivers"."geom"', source_wkt=None, source_feature_count=691
        )
        assert result is None


class TestApplyFilterQueueRouting:
    """2026-04-29: same Qt-thread-safety fix as the spatialite backend.

    The PostgreSQL apply_filter previously called `safe_set_subset_string`
    synchronously on the worker thread. In practice this often "worked"
    (PostgreSQL EXISTS subsets are short and the QGIS PG provider is more
    forgiving) but the race is the same as spatialite — and the contract
    in `FilterEngineTask.queue_subset_request` says any subset apply MUST
    be deferred to `finished()` on the Qt main thread. Routing through
    the queue when the orchestrator wires one removes the race.
    """

    def test_uses_queue_callback_when_present(self, mock_pg_layer):
        callback = MagicMock()
        builder = PostgreSQLExpressionBuilder(task_params={
            "buffer_endcap_style": "round",
            "buffer_segments": 5,
            "_subset_queue_callback": callback,
        })

        expr = (
            'EXISTS (SELECT 1 FROM "tmp"."fm_chain_xxx" AS __source '
            'WHERE ST_Intersects("buildings"."geom", __source.geom))'
        )
        result = builder.apply_filter(mock_pg_layer, expr)

        assert result is True
        callback.assert_called_once_with(mock_pg_layer, expr)

    def test_falls_back_to_direct_when_callback_missing(self, builder, mock_pg_layer):
        # Default builder fixture has no queue callback in task_params,
        # so apply_filter must keep using safe_set_subset_string and
        # return its result (mocked to True).
        expr = "EXISTS (SELECT 1 FROM s WHERE ST_Intersects(geom, source.geom))"
        result = builder.apply_filter(mock_pg_layer, expr)
        assert result is True

    def test_callback_not_invoked_for_empty_expression(self, mock_pg_layer):
        callback = MagicMock()
        builder = PostgreSQLExpressionBuilder(task_params={
            "_subset_queue_callback": callback,
        })

        result = builder.apply_filter(mock_pg_layer, "")

        assert result is False
        callback.assert_not_called()


# ===========================================================================
# PERF 2026-09-12: index-aware predicate with the centroid optimisation
# ===========================================================================

class TestIndexAwarePredicate:
    """``ST_PointOnSurface("t"."geom")`` cannot use the GiST index of ``geom``;
    a ``"t"."geom" && source`` test in front of the predicate restores it."""

    def test_centroid_predicate_gets_a_bbox_test(self, builder):
        expr = builder._index_aware_predicate(
            "ST_Intersects", 'ST_PointOnSurface("b"."geom")', '__source."geom"', raw_geom_expr='"b"."geom"'
        )
        assert expr == '("b"."geom" && __source."geom" AND ST_Intersects(ST_PointOnSurface("b"."geom"), __source."geom"))'

    def test_raw_column_predicate_is_left_alone(self, builder):
        expr = builder._index_aware_predicate("ST_Intersects", '"b"."geom"', '__source."geom"', raw_geom_expr='"b"."geom"')
        assert expr == 'ST_Intersects("b"."geom", __source."geom")'

    def test_disjoint_and_reprojected_geometry_are_left_alone(self, builder):
        disjoint = builder._index_aware_predicate(
            "ST_Disjoint", 'ST_PointOnSurface("b"."geom")', '__source."geom"', raw_geom_expr='"b"."geom"'
        )
        transformed = builder._index_aware_predicate(
            "ST_Intersects", 'ST_PointOnSurface(ST_Transform("b"."geom", 2154))', '__source."geom"', raw_geom_expr='"b"."geom"'
        )
        assert disjoint == 'ST_Disjoint(ST_PointOnSurface("b"."geom"), __source."geom")'
        assert transformed.startswith("ST_Intersects(")

    def test_simple_wkt_path(self, builder):
        expr = builder._build_simple_wkt_expression(
            geom_expr='ST_PointOnSurface("t"."geom")',
            predicate_func="ST_Intersects",
            source_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            source_srid=2154,
            buffer_value=None,
            raw_geom_expr='"t"."geom"',
        )
        assert expr.startswith('("t"."geom" && ST_MakeValid(ST_GeomFromText(')
        assert 'AND ST_Intersects(ST_PointOnSurface("t"."geom"), ST_MakeValid(' in expr

    def test_exists_path(self, builder):
        expr = builder._build_exists_expression(
            geom_expr='ST_PointOnSurface("batiment"."geometrie")',
            predicate_func="ST_Intersects",
            source_geom='"ign"."commune"."geometrie"',
            source_filter='"commune"."fid" IN (8, 34)',
            buffer_value=None,
            layer_props={},
            original_source_table="commune",
            raw_geom_expr='"batiment"."geometrie"',
        )
        # 2026-09-13: envelope prefilter (GiST on the target) in front of the EXISTS
        assert expr.startswith('("batiment"."geometrie" && (SELECT ST_SetSRID(ST_Expand(ST_Extent(__source."geometrie")::geometry, 0.0), ')
        assert 'FROM "ign"."commune" AS __source WHERE (__source."fid" IN (8, 34))) AND EXISTS (SELECT 1 FROM "ign"."commune" AS __source WHERE ' in expr
        assert ('("batiment"."geometrie" && __source."geometrie" AND '
                'ST_Intersects(ST_PointOnSurface("batiment"."geometrie"), __source."geometrie"))') in expr
        assert '__source."fid" IN (8, 34)' in expr

    def test_exists_path_with_buffer_tests_the_buffered_source(self, builder):
        expr = builder._build_exists_expression(
            geom_expr='ST_PointOnSurface("b"."geom")',
            predicate_func="ST_Intersects",
            source_geom='"s"."commune"."geom"',
            source_filter=None,
            buffer_value=50,
            layer_props={},
            raw_geom_expr='"b"."geom"',
        )
        # 2026-09-13: intersects + positive round buffer → ST_DWithin (no buffer
        # geometry), bbox test on the raw column against the expanded source
        assert '"b"."geom" && ST_Expand(__source."geom", 50)' in expr
        assert 'ST_DWithin(ST_PointOnSurface("b"."geom"), __source."geom", 50)' in expr
        assert 'ST_Buffer' not in expr

    def test_exists_path_keeps_st_buffer_for_other_predicates_and_caps(self, builder):
        expr = builder._build_exists_expression(
            geom_expr='"b"."geom"',
            predicate_func="ST_Within",
            source_geom='"s"."commune"."geom"',
            source_filter=None,
            buffer_value=50,
            layer_props={},
            raw_geom_expr='"b"."geom"',
        )
        # 2026-10-17: within runs against the union of the source rows
        assert 'ST_Within("b"."geom", ST_Buffer((SELECT ST_Union(__source."geom") FROM "s"."commune" AS __source), 50' in expr
        builder.task_params["buffer_endcap_style"] = "flat"
        expr = builder._build_exists_expression(
            geom_expr='"b"."geom"',
            predicate_func="ST_Intersects",
            source_geom='"s"."commune"."geom"',
            source_filter=None,
            buffer_value=50,
            layer_props={},
            raw_geom_expr='"b"."geom"',
        )
        assert 'ST_Buffer(__source."geom", 50' in expr and 'ST_DWithin' not in expr

    def test_negative_buffer_keeps_st_buffer(self, builder):
        expr = builder._build_exists_expression(
            geom_expr='"b"."geom"',
            predicate_func="ST_Intersects",
            source_geom='"s"."commune"."geom"',
            source_filter=None,
            buffer_value=-10,
            layer_props={},
            raw_geom_expr='"b"."geom"',
        )
        # 2026-10-17: the erosion applies to the union of the source rows
        assert 'ST_Buffer((SELECT ST_Union(__source."geom") FROM "s"."commune" AS __source), -10' in expr
        assert 'ST_DWithin' not in expr

    def test_simple_wkt_path_uses_dwithin(self, builder):
        expr = builder._build_simple_wkt_expression(
            geom_expr='"b"."geom"',
            predicate_func="ST_Intersects",
            source_wkt="POINT(0 0)",
            source_srid=2154,
            buffer_value=20,
            raw_geom_expr='"b"."geom"',
        )
        assert expr.startswith('ST_DWithin("b"."geom", ST_MakeValid(ST_GeomFromText(')
        assert expr.endswith(', 20)')


class TestSourceEnvelopePrefilter:
    def _expr(self, builder, **kwargs):
        params = dict(
            geom_expr='"b"."geom"',
            predicate_func="ST_Intersects",
            source_geom='"s"."commune"."geom"',
            source_filter='"commune"."fid" IN (1, 2)',
            buffer_value=None,
            layer_props={},
            original_source_table="commune",
            raw_geom_expr='"b"."geom"',
        )
        params.update(kwargs)
        return builder._build_exists_expression(**params)

    def test_buffer_grows_the_envelope(self, builder):
        expr = self._expr(builder, buffer_value=20)
        assert expr.startswith(
            '("b"."geom" && (SELECT ST_SetSRID(ST_Expand(ST_Extent(__source."geom")::geometry, 20.0), '
            'MAX(ST_SRID(__source."geom"))) FROM "s"."commune" AS __source WHERE (__source."fid" IN (1, 2))) '
            'AND EXISTS ('
        )
        assert 'ST_DWithin("b"."geom", __source."geom", 20)' in expr

    def test_no_prefilter_without_source_filter(self, builder):
        expr = self._expr(builder, source_filter=None)
        assert expr.startswith('EXISTS (')
        assert 'ST_Extent' not in expr

    def test_no_prefilter_for_disjoint(self, builder):
        expr = self._expr(builder, predicate_func="ST_Disjoint")
        assert expr.startswith('NOT EXISTS (')

    def test_no_prefilter_for_combined_exists_filters(self, builder):
        expr = self._expr(builder, source_filter='EXISTS (SELECT 1 FROM "s"."zone" AS __source WHERE 1=1)')
        assert expr.startswith('EXISTS (')
        assert 'ST_Extent' not in expr


class TestSourceSelectionMvAsSource:
    MV_FILTER = '"troncon_de_route"."fid" IN (SELECT pk FROM "filtermate_temp"."fm_temp_mv_session_ab_cd")'

    def test_mv_ref_parsing(self, builder):
        assert builder._source_selection_mv_ref(self.MV_FILTER) == ("filtermate_temp", "fm_temp_mv_session_ab_cd")
        assert builder._source_selection_mv_ref('"fid" IN (SELECT pk FROM "filtermate_temp"."x")') == ("filtermate_temp", "x")
        assert builder._source_selection_mv_ref('"troncon_de_route"."fid" IN (1, 2, 3)') is None
        assert builder._source_selection_mv_ref(None) is None

    def test_exists_reads_the_mv_directly(self, builder):
        expr = builder._build_exists_expression(
            geom_expr='"b"."geom"',
            predicate_func="ST_Intersects",
            source_geom='"ign"."troncon_de_route"."geometrie"',
            source_filter=self.MV_FILTER,
            buffer_value=20,
            layer_props={},
            original_source_table="troncon_de_route",
            raw_geom_expr='"b"."geom"',
        )
        assert ('EXISTS (SELECT 1 FROM "filtermate_temp"."fm_temp_mv_session_ab_cd" AS __source '
                'WHERE ST_DWithin("b"."geom", __source."geom", 20))') in expr
        assert expr.startswith('("b"."geom" && (SELECT ST_SetSRID(ST_Expand(ST_Extent(__source."geom")::geometry, 20.0), ')
        assert 'FROM "filtermate_temp"."fm_temp_mv_session_ab_cd" AS __source WHERE (TRUE))' in expr
        assert '"ign"."troncon_de_route"' not in expr
        assert 'IN (SELECT pk' not in expr


# ===========================================================================
# Tests -- dynamic buffer tables (2026-10-17)
# ===========================================================================

class _RecordingCursor:
    """Cursor double: records (sql, params) and answers the existence check."""

    def __init__(self, existing_tables=()):
        self.calls = []
        self._existing = set(existing_tables)
        self._last = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        self._last = (sql, params)

    def fetchone(self):
        sql, params = self._last
        if "information_schema.tables" in sql:
            return (params is not None and (params[0], params[1]) in self._existing,)
        if "COUNT(*)" in sql:
            return (3,)
        return None


class _RecordingConnexion:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass


class TestDynamicBufferTable:
    """The pre-computed buffer table of a dynamic buffer must never serve another selection.

    It was named fm_temp_buf_<table>_<md5(expression)[:8]> and reused when it
    existed: a second filter on another selection (or by another user, or
    after an edit) got the buffers of the first one.
    """

    @pytest.fixture(autouse=True)
    def _constants(self, monkeypatch):
        constants = sys.modules["filter_mate.infrastructure.constants"]
        monkeypatch.setattr(constants, "TABLE_PREFIX_BUFFER", "fm_temp_buf_", raising=False)
        executor = sys.modules["filter_mate.adapters.backends.postgresql.filter_executor"]
        monkeypatch.setattr(executor, "qgis_expression_to_postgis", lambda expr: expr, raising=False)

    @staticmethod
    def _builder(session_id="sess01"):
        return PostgreSQLExpressionBuilder(task_params={
            "buffer_endcap_style": "round",
            "buffer_segments": 5,
            "task": {"session_id": session_id},
        })

    def test_name_depends_on_the_selection(self):
        b = self._builder()
        first = b._buffer_table_name("ref", "demand_points", '"homecount" * 2', '"demand_points"."fid" IN (1, 2)')
        second = b._buffer_table_name("ref", "demand_points", '"homecount" * 2', '"demand_points"."fid" IN (3)')
        assert first != second

    def test_name_depends_on_schema_table_and_expression(self):
        b = self._builder()
        base = b._buffer_table_name("ref", "demand_points", '"homecount" * 2', None)
        assert base != b._buffer_table_name("other", "demand_points", '"homecount" * 2', None)
        assert base != b._buffer_table_name("ref", "ducts", '"homecount" * 2', None)
        assert base != b._buffer_table_name("ref", "demand_points", '"homecount" * 3', None)

    def test_name_carries_the_session_for_cleanup(self):
        name = self._builder("ab12cd34")._buffer_table_name("ref", "t", "10", None)
        assert name.startswith("fm_temp_buf_ab12cd34_")
        other_session = self._builder("ff00ff00")._buffer_table_name("ref", "t", "10", None)
        assert other_session != name

    def test_same_task_reuses_the_name_another_task_does_not(self):
        b = self._builder()
        name = b._buffer_table_name("ref", "t", "10", None)
        assert b._buffer_table_name("ref", "t", "10", None) == name
        # a new task (new task_parameters) never picks up the old table
        assert self._builder()._buffer_table_name("ref", "t", "10", None) != name
        # the app reuses the layer's PROJECT_LAYERS entry and rebuilds its "task" section
        b.task_params["task"] = {"session_id": "sess01"}
        assert b._buffer_table_name("ref", "t", "10", None) != name

    def test_name_fits_a_postgresql_identifier(self):
        b = self._builder("a" * 40)
        name = b._buffer_table_name("s" * 80, "t" * 80, "10", "x" * 500)
        assert len(name) <= 63
        assert len(f"idx_{name}_geom") <= 63

    def _build(self, b, cursor, monkeypatch, schema="ref", table="demand_points", source_filter='"fid" IN (1)'):
        utils = sys.modules["filter_mate.infrastructure.utils"]
        monkeypatch.setattr(
            utils, "get_datasource_connexion_from_layer",
            lambda layer: (_RecordingConnexion(cursor), None), raising=False
        )
        return b._build_exists_with_buffer_table(
            geom_expr='"ducts"."geom"',
            predicate_func="ST_Intersects",
            source_schema=schema,
            source_table=table,
            source_geom_field="geom",
            buffer_expression='"homecount" * 2',
            source_filter=source_filter,
            layer_props={"layer": MagicMock()},
            buffer_table_name=b._buffer_table_name(schema, table, '"homecount" * 2', source_filter),
        )

    def test_existence_check_and_regclass_are_bound_parameters(self, monkeypatch):
        b = self._builder()
        cursor = _RecordingCursor()
        self._build(b, cursor, monkeypatch, schema="l'ouest", table='bâti "neuf"')
        exists_sql, exists_params = next(c for c in cursor.calls if "information_schema.tables" in c[0])
        assert "l'ouest" not in exists_sql and exists_params[0] == "l'ouest"
        regclass_sql, regclass_params = next(c for c in cursor.calls if "regclass" in c[0])
        assert "%s::regclass" in regclass_sql
        assert regclass_params == ('"l\'ouest"."bâti ""neuf"""',)
        create_sql = next(sql for sql, _ in cursor.calls if "CREATE TABLE" in sql)
        assert 'FROM "l\'ouest"."bâti ""neuf"""' in create_sql

    def test_creates_the_table_from_the_selection(self, monkeypatch):
        b = self._builder()
        cursor = _RecordingCursor()
        expr = self._build(b, cursor, monkeypatch)
        create_sql = next(sql for sql, _ in cursor.calls if "CREATE TABLE" in sql)
        assert 'WHERE "fid" IN (1)' in create_sql
        name = b._buffer_table_name("ref", "demand_points", '"homecount" * 2', '"fid" IN (1)')
        assert f'"ref"."{name}"' in create_sql
        assert f'"ref"."{name}" AS __buffer' in expr

    def test_exists_expression_names_the_table_after_the_selection(self, monkeypatch):
        b = self._builder()
        seen = {}

        def fake_table_expr(**kwargs):
            seen.update(kwargs)
            return "EXISTS (buffer)"

        monkeypatch.setattr(b, "_build_exists_with_buffer_table", fake_table_expr)
        b._build_exists_expression(
            geom_expr='"ducts"."geom"',
            predicate_func="ST_Intersects",
            source_geom='"ref"."demand_points"."geom"',
            source_filter='"demand_points"."fid" IN (7)',
            buffer_value=None,
            layer_props={},
            original_source_table="demand_points",
            buffer_expression='"homecount" * 2',
        )
        assert seen["buffer_table_name"] == b._buffer_table_name(
            "ref", "demand_points", '"homecount" * 2', '"demand_points"."fid" IN (7)'
        )


# ===========================================================================
# Tests -- predicates against the union of the selected source features
# ===========================================================================

class TestPredicatesAgainstSourceUnion:
    """2026-10-17: a target is tested against the UNION of the selected source features.

    Spatialite and OGR test the target against one geometry, the union of the
    selection. ``EXISTS (... ST_<pred>(target, __source.geom) ...)`` tested it
    against each source feature: ST_Disjoint kept every target disjoint from
    ONE feature (almost the whole layer with two distant sources), ST_Within
    rejected a target spanning two adjacent source polygons, ST_Contains kept
    a target containing one of the selected features only.

    Semantics checked on PostGIS 3.4 (A = [0,10]x[0,10], B = [10,20]x[0,10]):
    - intersects: EXISTS(any feature) == ST_Intersects(t, A u B) - unchanged;
    - disjoint: ST_Disjoint(t, A u B) == NOT EXISTS(ST_Intersects(t, feature));
    - within / contains / touches / overlaps / crosses / equals / covers /
      coveredby: not distributive over the features, tested against the
      union, e.g. [5,15]x[2,8] is within A u B but within neither A nor B.
    """

    FILTER = '"commune"."fid" IN (1, 2)'
    UNION = '(SELECT ST_Union(__source."geom") FROM "s"."commune" AS __source WHERE (__source."fid" IN (1, 2)))'

    def _expr(self, builder, predicate_func, **kwargs):
        params = dict(
            geom_expr='"b"."geom"',
            predicate_func=predicate_func,
            source_geom='"s"."commune"."geom"',
            source_filter=self.FILTER,
            buffer_value=None,
            layer_props={},
            original_source_table="commune",
            raw_geom_expr='"b"."geom"',
        )
        params.update(kwargs)
        return builder._build_exists_expression(**params)

    def test_intersects_keeps_the_exists_form(self, builder):
        expr = self._expr(builder, "ST_Intersects")
        assert ('EXISTS (SELECT 1 FROM "s"."commune" AS __source WHERE '
                'ST_Intersects("b"."geom", __source."geom") AND (__source."fid" IN (1, 2)))') in expr
        assert "ST_Union" not in expr

    def test_disjoint_is_not_exists_intersects(self, builder):
        expr = self._expr(builder, "ST_Disjoint")
        assert expr == ('NOT EXISTS (SELECT 1 FROM "s"."commune" AS __source WHERE '
                        'ST_Intersects("b"."geom", __source."geom") AND (__source."fid" IN (1, 2)))')

    def test_disjoint_with_buffer_is_not_exists_dwithin(self, builder):
        expr = self._expr(builder, "ST_Disjoint", buffer_value=20)
        assert expr == ('NOT EXISTS (SELECT 1 FROM "s"."commune" AS __source WHERE '
                        'ST_DWithin("b"."geom", __source."geom", 20) AND (__source."fid" IN (1, 2)))')

    @pytest.mark.parametrize("predicate_func", [
        "ST_Within", "ST_Contains", "ST_Touches", "ST_Overlaps", "ST_Crosses", "ST_Equals",
        "ST_Covers", "ST_CoveredBy",
    ])
    def test_other_predicates_test_the_union(self, builder, predicate_func):
        expr = self._expr(builder, predicate_func)
        assert f'{predicate_func}("b"."geom", {self.UNION})' in expr
        assert "EXISTS" not in expr

    def test_union_with_buffer_buffers_the_union(self, builder):
        expr = self._expr(builder, "ST_Within", buffer_value=20)
        assert f'ST_Within("b"."geom", ST_Buffer({self.UNION}, 20, \'quad_segs=5\'))' in expr

    def test_negative_buffer_erodes_the_union_for_intersects_too(self, builder):
        # erosion does not distribute over the union: buffer(A u B, -d) != buffer(A, -d) u buffer(B, -d)
        expr = self._expr(builder, "ST_Intersects", buffer_value=-5)
        assert f"ST_Buffer({self.UNION}, -5, 'quad_segs=5')" in expr
        assert "EXISTS" not in expr

    def test_whole_source_union_without_filter(self, builder):
        expr = self._expr(builder, "ST_Within", source_filter=None)
        assert expr == 'ST_Within("b"."geom", (SELECT ST_Union(__source."geom") FROM "s"."commune" AS __source))'

    def test_centroid_mode_keeps_the_bbox_test(self, builder):
        expr = self._expr(builder, "ST_Within", geom_expr='ST_PointOnSurface("b"."geom")', source_filter=None)
        union = '(SELECT ST_Union(__source."geom") FROM "s"."commune" AS __source)'
        assert expr == f'("b"."geom" && {union} AND ST_Within(ST_PointOnSurface("b"."geom"), {union}))'

    def test_buffer_table_disjoint_and_within(self, builder):
        disjoint = builder._predicate_against_sources(
            "ST_Disjoint", '"b"."geom"', "__buffer.buffered_geom", '"s"."fm_temp_buf_x" AS __buffer', [], None, None
        )
        assert disjoint == ('NOT EXISTS (SELECT 1 FROM "s"."fm_temp_buf_x" AS __buffer '
                            'WHERE ST_Intersects("b"."geom", __buffer.buffered_geom))')
        within = builder._predicate_against_sources(
            "ST_Within", '"b"."geom"', "__buffer.buffered_geom", '"s"."fm_temp_buf_x" AS __buffer', [], None, None
        )
        assert within == ('ST_Within("b"."geom", (SELECT ST_Union(__buffer.buffered_geom) '
                          'FROM "s"."fm_temp_buf_x" AS __buffer))')

    def test_chained_disjoint_filter_stays_negated(self, builder, monkeypatch):
        """A source already filtered with disjoint chains NOT EXISTS, not EXISTS."""
        inner = 'EXISTS (SELECT 1 FROM "s"."zone" AS __source WHERE ST_Intersects("src"."geom", __source."geom"))'
        combiner = sys.modules["filter_mate.core.filter.expression_combiner"]
        monkeypatch.setattr(combiner, "extract_exists_clauses", lambda expr: [{"sql": inner}], raising=False)
        monkeypatch.setattr(
            combiner, "adapt_exists_for_nested_context",
            lambda exists_sql, original_table, new_alias, original_schema=None:
                exists_sql.replace(f'"{original_table}".', f"{new_alias}."),
            raising=False,
        )
        result = builder.build_expression(
            layer_props={"layer_name": "b", "layer_table_name": "b"},
            predicates={"intersects": "ST_Intersects"},
            source_geom='"s"."src"."geom"',
            source_filter=f"NOT {inner}",
            source_feature_count=500,
            source_table_name="src",
        )
        assert result.endswith(
            ' AND NOT EXISTS (SELECT 1 FROM "s"."zone" AS __source WHERE ST_Intersects("b"."geom", __source."geom"))'
        )

    def test_chain_mv_expression_uses_the_same_semantics(self, builder):
        expr = builder._build_optimized_mv_expression(
            geom_expr='"b"."geom"', predicates={"disjoint": "ST_Disjoint"}, mv_name='"filtermate_temp"."fm_temp_chain_x"'
        )
        assert expr.startswith('NOT EXISTS (SELECT 1 FROM "filtermate_temp"."fm_temp_chain_x" AS __chain')
        assert 'ST_Intersects("b"."geom", __chain."geom")' in expr


# ===========================================================================
# Tests -- source and target SRIDs (2026-10-17)
# ===========================================================================

class TestSourceTargetSrid:
    """The source geometry is brought to the SRID of the target, the buffer stays metric.

    A GeoJSON source in EPSG:4326 against a BD TOPO table in EPSG:2154 gave
    "Operation on mixed SRID geometries"; a 100 m buffer around a source in
    degrees was 100 degrees.
    """

    WKT_4326 = "ST_MakeValid(ST_GeomFromText('POINT(1.44 43.6)', 4326))"
    WKT_2154 = "ST_MakeValid(ST_GeomFromText('POINT(574000 6280000)', 2154))"

    @staticmethod
    def _builder(source_authid=None):
        params = {"buffer_endcap_style": "round", "buffer_segments": 5}
        if source_authid:
            params["infos"] = {"layer_crs_authid": source_authid}
        return PostgreSQLExpressionBuilder(task_params=params)

    def _wkt(self, builder, wkt, source_srid, target_srid, buffer_value=None, predicate_func="ST_Intersects"):
        return builder._build_simple_wkt_expression(
            geom_expr='"t"."geom"',
            predicate_func=predicate_func,
            source_wkt=wkt,
            source_srid=source_srid,
            buffer_value=buffer_value,
            raw_geom_expr='"t"."geom"',
            target_srid=target_srid,
        )

    def test_layer_srid(self):
        layer = MagicMock()
        layer.dataProvider.return_value.crs.return_value.postgisSrid.return_value = 2154
        assert PostgreSQLExpressionBuilder._layer_srid(layer) == 2154
        assert PostgreSQLExpressionBuilder._layer_srid(MagicMock()) is None  # no integer SRID
        assert PostgreSQLExpressionBuilder._layer_srid(None) is None

    def test_authid_to_srid(self):
        assert PostgreSQLExpressionBuilder._authid_to_srid("EPSG:4326") == 4326
        assert PostgreSQLExpressionBuilder._authid_to_srid("USER:100000") is None
        assert PostgreSQLExpressionBuilder._authid_to_srid(None) is None

    def test_wkt_is_reprojected_to_the_target(self, builder):
        expr = self._wkt(builder, "POINT(1.44 43.6)", 4326, 2154)
        assert expr == f'ST_Intersects("t"."geom", ST_Transform({self.WKT_4326}, 2154))'

    def test_wkt_same_srid_is_left_alone(self, builder):
        expr = self._wkt(builder, "POINT(574000 6280000)", 2154, 2154)
        assert expr == f'ST_Intersects("t"."geom", {self.WKT_2154})'

    def test_wkt_geographic_source_metric_target_buffers_in_target_metres(self, builder):
        expr = self._wkt(builder, "POINT(1.44 43.6)", 4326, 2154, buffer_value=100)
        assert expr == f'ST_DWithin("t"."geom", ST_Transform({self.WKT_4326}, 2154), 100)'

    def test_wkt_metric_source_geographic_target_buffers_before_the_transform(self, builder):
        expr = self._wkt(builder, "POINT(574000 6280000)", 2154, 4326, buffer_value=100)
        assert expr == (
            f"ST_Intersects(\"t\".\"geom\", ST_Transform(ST_Buffer({self.WKT_2154}, 100, 'quad_segs=5'), 4326))"
        )

    def test_wkt_geographic_source_and_target_buffer_on_the_geography(self, builder):
        expr = self._wkt(builder, "POINT(1.44 43.6)", 4326, 4326, buffer_value=500)
        assert expr == (
            f"ST_Intersects(\"t\".\"geom\", ST_Buffer(({self.WKT_4326})::geography, 500, 'quad_segs=5')::geometry)"
        )

    def test_wkt_negative_geography_buffer_is_validated(self, builder):
        expr = self._wkt(builder, "POINT(1.44 43.6)", 4326, 4326, buffer_value=-5)
        assert "ST_IsEmpty(ST_MakeValid(ST_Buffer((" in expr and "::geography, -5" in expr

    def _exists(self, builder, target_srid, buffer_value=None, source_filter=None, predicate_func="ST_Intersects"):
        return builder._build_exists_expression(
            geom_expr='"b"."geom"',
            predicate_func=predicate_func,
            source_geom='"s"."commune"."geom"',
            source_filter=source_filter,
            buffer_value=buffer_value,
            layer_props={},
            original_source_table="commune",
            raw_geom_expr='"b"."geom"',
            target_srid=target_srid,
        )

    def test_exists_reprojects_the_source_rows(self):
        expr = self._exists(self._builder("EPSG:4326"), 2154)
        assert expr == ('EXISTS (SELECT 1 FROM "s"."commune" AS __source WHERE '
                        'ST_Intersects("b"."geom", ST_Transform(__source."geom", 2154)))')

    def test_exists_same_srid_is_left_alone(self):
        expr = self._exists(self._builder("EPSG:2154"), 2154, buffer_value=50)
        assert expr == ('EXISTS (SELECT 1 FROM "s"."commune" AS __source WHERE '
                        'ST_DWithin("b"."geom", __source."geom", 50))')

    def test_exists_geographic_source_buffers_in_target_metres(self):
        expr = self._exists(self._builder("EPSG:4326"), 2154, buffer_value=50)
        assert 'ST_DWithin("b"."geom", ST_Transform(__source."geom", 2154), 50)' in expr

    def test_exists_geographic_source_and_target_buffer_on_the_geography(self):
        expr = self._exists(self._builder("EPSG:4326"), 4326, buffer_value=50)
        assert "ST_DWithin" not in expr
        assert "ST_Intersects(\"b\".\"geom\", ST_Buffer((__source.\"geom\")::geography, 50, 'quad_segs=5')::geometry)" in expr

    def test_exists_envelope_prefilter_is_in_the_target_srid(self):
        expr = self._exists(self._builder("EPSG:4326"), 2154, buffer_value=20, source_filter='"commune"."fid" IN (1)')
        assert expr.startswith(
            '("b"."geom" && (SELECT ST_SetSRID(ST_Expand(ST_Extent(ST_Transform(__source."geom", 2154))::geometry, 20.0), '
            'MAX(ST_SRID(ST_Transform(__source."geom", 2154))))'
        )

    def test_union_predicates_reproject_the_rows(self):
        expr = self._exists(self._builder("EPSG:4326"), 2154, predicate_func="ST_Within")
        assert expr == ('ST_Within("b"."geom", (SELECT ST_Union(ST_Transform(__source."geom", 2154)) '
                        'FROM "s"."commune" AS __source))')

    def test_buffer_table_rows_are_reprojected(self, monkeypatch):
        b = TestDynamicBufferTable._builder()
        b.task_params["infos"] = {"layer_crs_authid": "EPSG:4326"}
        constants = sys.modules["filter_mate.infrastructure.constants"]
        monkeypatch.setattr(constants, "TABLE_PREFIX_BUFFER", "fm_temp_buf_", raising=False)
        executor = sys.modules["filter_mate.adapters.backends.postgresql.filter_executor"]
        monkeypatch.setattr(executor, "qgis_expression_to_postgis", lambda expr: expr, raising=False)
        cursor = _RecordingCursor()
        utils = sys.modules["filter_mate.infrastructure.utils"]
        monkeypatch.setattr(utils, "get_datasource_connexion_from_layer",
                            lambda layer: (_RecordingConnexion(cursor), None), raising=False)
        expr = b._build_exists_with_buffer_table(
            geom_expr='"ducts"."geom"', predicate_func="ST_Intersects", source_schema="ref",
            source_table="demand_points", source_geom_field="geom", buffer_expression='"homecount" * 2',
            source_filter=None, layer_props={"layer": MagicMock()}, target_srid=2154,
        )
        assert 'ST_Intersects("ducts"."geom", ST_Transform(__buffer.buffered_geom, 2154))' in expr

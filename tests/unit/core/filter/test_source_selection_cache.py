# -*- coding: utf-8 -*-
"""Source-selection MV filter memoised per task (2026-09-13)."""
from core.filter.expression_builder import ExpressionBuilder


def test_selection_cache_key_is_order_insensitive():
    key_a = ExpressionBuilder._selection_cache_key([3, 1, 2], "fid", "troncon_de_route")
    key_b = ExpressionBuilder._selection_cache_key([2, 3, 1], "fid", "troncon_de_route")
    assert key_a == key_b
    assert key_a != ExpressionBuilder._selection_cache_key([1, 2], "fid", "troncon_de_route")
    assert key_a != ExpressionBuilder._selection_cache_key([3, 1, 2], "id", "troncon_de_route")


def test_cached_filter_is_returned_without_creating_a_new_mv():
    builder = ExpressionBuilder.__new__(ExpressionBuilder)
    builder._source_selection_mv_cache = {}
    builder._source_selection_mvs = []
    key = ExpressionBuilder._selection_cache_key([1, 2, 3], "fid", "troncon_de_route")
    builder._source_selection_mv_cache[key] = '"troncon_de_route"."fid" IN (SELECT pk FROM "filtermate_temp"."mv")'

    def explode():
        raise AssertionError("MV creation attempted")
    builder._get_source_geom_field = explode
    result = builder._create_source_selection_mv_filter([3, 2, 1], "fid", "troncon_de_route")
    assert result == '"troncon_de_route"."fid" IN (SELECT pk FROM "filtermate_temp"."mv")'

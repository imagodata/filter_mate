# -*- coding: utf-8 -*-
"""Regression tests for issue #36 — schema-aware cache keys.

These tests pin two contracts:

1. ``FilterService._build_cache_key`` differentiates two layers that share
   the same id/name/buffer/expression but have a different
   ``fields_signature`` (e.g. a column was added). Without this, a stale
   cached result computed against the old schema could leak into a query
   issued against the new schema.

2. ``QueryExpressionCache.get_cache_key`` differentiates two calls that
   share every parameter except ``target_schema_signature``.

Both tests target the public seams exposed in the patch — they do NOT
require QGIS to be importable.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from core.domain.filter_expression import FilterExpression, ProviderType
from core.domain.layer_info import LayerInfo
from core.services.filter_service import FilterService
from infrastructure.cache.query_cache import QueryExpressionCache


def _make_layer(layer_id: str, signature: str) -> LayerInfo:
    return LayerInfo.create(
        layer_id=layer_id,
        name=f"layer-{layer_id}",
        provider_type=ProviderType.OGR,
        fields_signature=signature,
    )


def _make_expression() -> FilterExpression:
    return FilterExpression(
        raw='"population" > 1000',
        sql='"population" > 1000',
        provider=ProviderType.OGR,
        source_layer_id="src",
    )


class TestFilterServiceCacheKeySchemaAware:
    """#36: cache key must change when target schema changes."""

    def setup_method(self) -> None:
        # FilterService deps are not exercised by _build_cache_key, so MagicMocks
        # are sufficient.
        self.service = FilterService(
            layer_repository=MagicMock(),
            expression_service=MagicMock(),
            backends={},
            cache=MagicMock(),
        )

    def test_target_schema_change_invalidates_key(self) -> None:
        expr = _make_expression()
        source = _make_layer("src", "src-sig-v1")
        target_v1 = _make_layer("tgt", "tgt-sig-v1")
        target_v2 = _make_layer("tgt", "tgt-sig-v2")  # field added/retyped

        key_v1 = self.service._build_cache_key(expr, source, target_v1)
        key_v2 = self.service._build_cache_key(expr, source, target_v2)

        assert key_v1 != key_v2, (
            "Schema change on the target layer must invalidate the cache key — "
            "issue #36 stale-hit risk"
        )

    def test_source_schema_change_invalidates_key(self) -> None:
        expr = _make_expression()
        source_v1 = _make_layer("src", "src-sig-v1")
        source_v2 = _make_layer("src", "src-sig-v2")
        target = _make_layer("tgt", "tgt-sig")

        key_v1 = self.service._build_cache_key(expr, source_v1, target)
        key_v2 = self.service._build_cache_key(expr, source_v2, target)

        assert key_v1 != key_v2

    def test_identical_signatures_share_cache_key(self) -> None:
        expr = _make_expression()
        source = _make_layer("src", "src-sig")
        target = _make_layer("tgt", "tgt-sig")

        key_a = self.service._build_cache_key(expr, source, target)
        key_b = self.service._build_cache_key(expr, source, target)

        assert key_a == key_b

    def test_empty_signature_falls_back_without_collision(self) -> None:
        """Layers without a known signature use a sentinel — but two distinct
        layers must still produce distinct keys via their ids."""
        expr = _make_expression()
        source = _make_layer("src", "")
        target_a = _make_layer("tgt-a", "")
        target_b = _make_layer("tgt-b", "")

        key_a = self.service._build_cache_key(expr, source, target_a)
        key_b = self.service._build_cache_key(expr, source, target_b)

        assert key_a != key_b


class TestQueryExpressionCacheSchemaSignature:
    """#36: get_cache_key must include target_schema_signature."""

    def setup_method(self) -> None:
        self.cache = QueryExpressionCache(max_size=4)

    def _key(self, schema_sig):
        return self.cache.get_cache_key(
            layer_id="L1",
            predicates={"intersects": "ST_Intersects"},
            buffer_value=None,
            source_geometry_hash="h",
            provider_type="postgresql",
            target_schema_signature=schema_sig,
        )

    def test_schema_signature_change_yields_distinct_keys(self) -> None:
        assert self._key("v1") != self._key("v2")

    def test_none_signature_distinct_from_value(self) -> None:
        assert self._key(None) != self._key("v1")

    def test_default_signature_is_backwards_compatible(self) -> None:
        """Callers that don't pass target_schema_signature still get a usable
        key — the param defaults to None."""
        legacy_key = self.cache.get_cache_key(
            layer_id="L1",
            predicates={"intersects": "ST_Intersects"},
            buffer_value=None,
            source_geometry_hash="h",
            provider_type="postgresql",
        )
        assert legacy_key == self._key(None)

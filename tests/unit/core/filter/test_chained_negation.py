# -*- coding: utf-8 -*-
"""A chained disjoint filter stays negated (2026-10-17).

Disjoint is now ``NOT EXISTS (...)`` on PostgreSQL. The filter chaining
rebuilt the source filter from the extracted ``EXISTS (...)`` clauses only:
the NOT was lost and the next layer kept the opposite features.
"""
from core.filter.expression_builder import ExpressionBuilder

INNER = 'EXISTS (SELECT 1 FROM "ref"."zone" AS __source WHERE ST_Intersects("a"."geom", __source."geom"))'
OTHER = 'EXISTS (SELECT 1 FROM "ref"."route" AS __source WHERE ST_Intersects("a"."geom", __source."geom"))'


def test_not_exists_keeps_its_not():
    subset = f'("a"."geom" IS NOT NULL AND NOT {INNER})'
    assert ExpressionBuilder._with_negations(subset, [INNER]) == [f"NOT {INNER}"]


def test_and_not_parenthesised_keeps_its_not():
    subset = f'({OTHER}) AND NOT ({INNER})'
    assert ExpressionBuilder._with_negations(subset, [OTHER, INNER]) == [OTHER, f"NOT {INNER}"]


def test_positive_clauses_are_unchanged():
    assert ExpressionBuilder._with_negations(f"{INNER} AND {OTHER}", [INNER, OTHER]) == [INNER, OTHER]
    assert ExpressionBuilder._with_negations(None, [INNER]) == [INNER]

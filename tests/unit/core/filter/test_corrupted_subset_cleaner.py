# -*- coding: utf-8 -*-
"""``contains_well_formed_exists`` (2026-09-13), used by the corrupted-subset cleaner.

Regression coverage: a PostgreSQL subset preceded by the source envelope
prefilter (``("t"."geom" && (SELECT ... AS __source WHERE ...)) AND EXISTS
(...)``) was judged corrupted and cleared - the queued empty subset was
applied after the worker's filter, leaving every target unfiltered.
"""
from core.filter.expression_sanitizer import contains_well_formed_exists

EXISTS = (
    'EXISTS (SELECT 1 FROM "ign"."troncon_de_route" AS __source '
    'WHERE ST_DWithin("batiment"."geometrie", __source."geometrie", 20.0) AND (__source."fid" IN (1, 2)))'
)
PREFILTER = (
    '"batiment"."geometrie" && (SELECT ST_SetSRID(ST_Expand(ST_Extent(__source."geometrie")::geometry, 20.0), '
    'MAX(ST_SRID(__source."geometrie"))) FROM "ign"."troncon_de_route" AS __source WHERE (__source."fid" IN (1, 2)))'
)


def test_plain_exists():
    assert contains_well_formed_exists(EXISTS)


def test_exists_behind_envelope_prefilter():
    assert contains_well_formed_exists(f"({PREFILTER} AND {EXISTS})")


def test_truncated_expression_is_not_well_formed():
    assert not contains_well_formed_exists('EXISTS (SELECT 1 FROM "ign"."commune" AS __source')


def test_prefilter_alone_is_not_well_formed():
    assert not contains_well_formed_exists(PREFILTER)


def test_empty():
    assert not contains_well_formed_exists(None)
    assert not contains_well_formed_exists("")

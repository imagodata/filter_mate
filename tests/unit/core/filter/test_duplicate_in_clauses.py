# -*- coding: utf-8 -*-
"""optimize_duplicate_in_clauses removes only exact duplicates.

2026-10-17: it kept the first ``IN`` clause of each FIELD, so
``("fid" IN (1,2,3)) AND ("fid" IN (2,3))`` became ``("fid" IN (1,2,3))``
(feature 1 kept although the second condition excludes it). It also counted
parentheses inside values and squeezed their spaces. Dropping an operand is
only exact when it is the same condition as one already kept in the same AND
chain (``X AND X`` is ``X``).

Module tested: core.filter.expression_sanitizer
"""
from core.filter.expression_sanitizer import optimize_duplicate_in_clauses


def test_different_lists_on_the_same_field_are_both_kept():
    expression = '("fid" IN (1,2,3)) AND ("fid" IN (2,3))'
    assert optimize_duplicate_in_clauses(expression) == expression


def test_identical_lists_are_deduplicated():
    expression = '( "a" = 1 AND "fid" IN (1, 2, 3) ) AND ( "fid" IN (1,  2, 3) )'
    assert optimize_duplicate_in_clauses(expression) == '( "a" = 1 AND "fid" IN (1, 2, 3) )'


def test_multi_step_repetition_collapses_to_one():
    expression = '(A AND "fid" IN (1,2,3)) AND ("fid" IN (1,2,3)) AND ("fid" IN (1,2,3))'
    assert optimize_duplicate_in_clauses(expression) == '(A AND "fid" IN (1,2,3))'


def test_qualified_field_duplicates():
    expression = '("t"."fid" IN (1, 2)) AND ("t"."fid" in (1,2))'
    assert optimize_duplicate_in_clauses(expression) == '("t"."fid" IN (1, 2))'


def test_identical_lists_around_or_are_kept():
    # C OR (D AND C) is C, not C OR D: nothing is removed outside a plain AND chain.
    expression = '( "fid" IN (1, 2) ) OR ( "b" = 2 ) AND ( "fid" IN (1, 2) )'
    assert optimize_duplicate_in_clauses(expression) == expression


def test_and_of_between_is_not_an_operand_separator():
    expression = '"x" BETWEEN 1 AND 5 AND "fid" IN (1) AND "y" BETWEEN 2 AND 5'
    assert optimize_duplicate_in_clauses(expression) == expression


def test_not_in_list_is_not_a_duplicate_of_the_list():
    expression = 'NOT ("fid" IN (1, 2)) AND ("fid" IN (1, 2))'
    assert optimize_duplicate_in_clauses(expression) == expression


def test_values_with_parentheses_are_compared_whole():
    expression = "( \"nom\" IN ('a)', 'b') ) AND ( \"nom\" IN ('a)', 'c') )"
    assert optimize_duplicate_in_clauses(expression) == expression


def test_value_case_matters():
    expression = "( \"nom\" IN ('Paris') ) AND ( \"nom\" IN ('PARIS') )"
    assert optimize_duplicate_in_clauses(expression) == expression


def test_spaces_inside_values_are_kept():
    expression = "( \"nom\" IN ('Saint  Jean') ) AND ( \"x\" = 1 ) AND ( \"nom\" IN ('Saint  Jean') )"
    assert optimize_duplicate_in_clauses(expression) == "( \"nom\" IN ('Saint  Jean') ) AND ( \"x\" = 1 )"

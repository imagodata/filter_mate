# -*- coding: utf-8 -*-
"""Expressions of a layout or a form written by a model (2026-11-22 review): what an atlas needs, never what reads
the environment, a file or another layer."""
import pytest

from core.agent.sql_guard import expression_problem, layout_expression_problem, text_expressions_problem

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("text", ['"nom"', "\"nom\" || '_' || lpad(@atlas_featurenumber, 3, '0')", "now()",
                                  "format_date(now(), 'yyyy')", "@user_account_name", "$area", "@atlas_pagename",
                                  "round($area / 10000, 1)"])
def test_what_an_atlas_and_a_form_need(text):
    assert layout_expression_problem(text) == ""


@pytest.mark.parametrize("text", ["env('HOME')", "eval('1')",
                                  "sqlite_fetch_and_increment('/tmp/x', 't', 'i', 'k', 'v')",
                                  "layer_property(load_layer('/etc/passwd', 'ogr'), 'name')", "@project_folder",
                                  "aggregate('l', 'sum', \"a\")"])
def test_what_reads_the_machine_is_refused(text):
    assert layout_expression_problem(text)


def test_texts_are_checked_expression_by_expression():
    assert text_expressions_problem('Commune [% "nom" %], page [% @atlas_featurenumber %]') == ""
    assert "env" in text_expressions_problem("[% env('HOME') %]")
    assert text_expressions_problem("[% 1 + ") != ""
    assert text_expressions_problem("no expression at all") == ""


def test_a_filter_still_takes_no_variable_of_a_layout():
    assert expression_problem("@atlas_pagename")

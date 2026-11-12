# -*- coding: utf-8 -*-
"""The distant PostgreSQL filter reads the source selection of this filter, not of the previous one.

2026-11-12: a subset is set on the main thread once the task is over
(``_pending_subset_requests``, applied in finished()). While the distant layers
are filtered the source layer still holds its PREVIOUS subset.
ExpressionBuilder._prepare_source_filter, written when the new subset was
already set, read ``source_layer.subsetString()``: with a buffer expression
(which prefers the source subset to the selected features), or a custom
selection the selected features could not stand for, the distant layers were
filtered by the previous selection of the source, or by all its features on a
first filter. The subset the source will have is recorded when it is queued.
"""
from unittest.mock import MagicMock

import pytest

from core.filter.expression_builder import ExpressionBuilder

pytestmark = pytest.mark.unit

PREVIOUS = '"src"."fid" IN (1, 2)'
NEW = '"src"."fid" IN (7, 8)'


def _source(subset):
    layer = MagicMock()
    layer.name.return_value = "src"
    layer.subsetString.return_value = subset
    layer.selectedFeatureCount.return_value = 0
    return layer


def _builder(task, source_subset=PREVIOUS, buffer_expression=None):
    return ExpressionBuilder(task_parameters=task, source_layer=_source(source_subset),
                             current_predicates={"ST_Intersects": "ST_Intersects"},
                             buffer_expression=buffer_expression)


class _Feature:
    """A selected QgsFeature, as the dock hands them to the task."""

    def __init__(self, fid):
        self._fid = fid

    def id(self):
        return self._fid

    def geometry(self):
        return None


def _fids(builder, monkeypatch):
    monkeypatch.setattr(builder, "_generate_fid_filter",
                        lambda features, backend_name=None: f"<FIDS {[f.id() for f in features]}>")
    return builder


def test_a_buffer_expression_without_features_reads_the_new_subset_of_the_source():
    task = {"task": {"features": [], "expression": ""}, "param_source_table": "src",
            "source_subset_after_task": NEW}

    source_filter = _builder(task, buffer_expression='"radius"')._prepare_source_filter("PostgreSQL")

    assert source_filter == NEW


@pytest.mark.parametrize("subset", [
    '( "src"."fid" IN (1, 2) ) OR ( "src"."fid" IN (7, 8) )',      # a second filter combined by OR
    '"src"."v" BETWEEN 1 AND 5',
    '"src"."name" = \'Black AND White\'',
    '( "src"."a" = 1 AND "src"."b" = 2 ) OR ( "src"."c" = 3 )',
])
def test_the_new_subset_is_used_as_it_is(subset):
    # review of the first version: split on AND / OR and joined with AND, OR became AND,
    # BETWEEN a syntax error and a literal holding AND another value
    task = {"task": {"features": [], "expression": ""}, "param_source_table": "src",
            "source_subset_after_task": subset}

    source_filter = _builder(task, buffer_expression='"radius"')._prepare_source_filter("PostgreSQL")

    assert source_filter == subset


@pytest.mark.parametrize("buffer_expression", ['"radius"', None])
def test_selected_features_are_the_source_selection_with_or_without_a_buffer_expression(monkeypatch,
                                                                                        buffer_expression):
    task = {"task": {"features": [_Feature(7), _Feature(8)], "expression": ""}, "param_source_table": "src",
            "source_subset_after_task": '( "src"."fid" IN (1, 2) ) OR ( "src"."fid" IN (7, 8) )'}
    builder = _fids(_builder(task, buffer_expression=buffer_expression), monkeypatch)

    assert builder._prepare_source_filter("PostgreSQL") == "<FIDS [7, 8]>"


def test_a_custom_selection_without_features_reads_the_new_subset_of_the_source():
    # values of a complex custom expression cannot stand for the selection: the subset is used
    task = {"task": {"features": ["a", "b"], "expression": '"id" <= 100'}, "param_source_table": "src",
            "source_subset_after_task": NEW}

    source_filter = _builder(task)._prepare_source_filter("PostgreSQL")

    assert "7, 8" in source_filter and "1, 2" not in source_filter


def test_a_source_whose_subset_does_not_change_keeps_its_subset():
    # all features / field-based modes queue no subset for the source
    task = {"task": {"features": [], "expression": ""}, "param_source_table": "src"}

    source_filter = _builder(task, buffer_expression='"radius"')._prepare_source_filter("PostgreSQL")

    assert "1, 2" in source_filter

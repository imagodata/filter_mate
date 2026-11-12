# -*- coding: utf-8 -*-
"""PostgreSQL targets are filtered by the source selection, not by the new subset of the source (2026-11-12).

The source operator combines the new selection x with the old subset of the
source only: NOT (x) under AND NOT, (old) OR (x) under OR. Without selected
features the distant PostgreSQL filter (ExpressionBuilder, PATH 2) used that
subset as the source of the targets: under AND NOT they were filtered by every
source feature but the selection, by all of them when x kept none, while
SpatiaLite / OGR read x (refused when it keeps nothing). The selection is read
as those backends read it (selection_reads_whole_layer): through the old subset
under AND and AND NOT, on the whole layer under OR and replace.

The facade is loaded by path under the conftest's mocked ``filter_mate`` tree
(see test_source_subset_after_task_recorded.py).
"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.filter.expression_builder import ExpressionBuilder

pytestmark = pytest.mark.unit

_TASKS_DIR = Path(__file__).resolve().parents[4] / "core" / "tasks"
X = '"src"."pop" > 1000'
OLD = '"src"."dep" = \'31\''


@pytest.fixture
def facade_module():
    name = "filter_mate.core.tasks.expression_facade_handler"
    spec = importlib.util.spec_from_file_location(name, _TASKS_DIR / "expression_facade_handler.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(name, None)


def _task(old_subset, operator):
    """A task whose source filter is combined by the real core combiner."""
    from filtermate_core.filter.expression_combiner import combine_with_old_subset
    executor = MagicMock(old_subset=old_subset, combine_operator=operator, provider_type="postgresql")
    executor.combine_with_old_subset.side_effect = lambda expression: combine_with_old_subset(
        expression, old_subset, operator, provider_type="postgresql")
    task = MagicMock()
    task._get_attribute_executor.return_value = executor
    task.param_source_provider_type = "ogr"   # no PostgreSQL history step in a unit test
    task._pending_subset_requests = []
    task.task_parameters = {"task": {"features": [], "expression": ""}, "param_source_table": "src"}
    return task


def _queue(facade_module, task, expression=X):
    """What SourceLayerFilterExecutor does: combine with the old subset, then queue the source filter."""
    facade = facade_module.ExpressionFacadeHandler(task)
    combined = facade.combine_with_old_subset(expression)
    assert facade.apply_filter_and_update_subset(combined) is True
    return combined


def _distant_source_filter(task, layer_subset):
    """The source filter of the distant PostgreSQL layers, the source layer still holding its old subset."""
    layer = MagicMock()
    layer.name.return_value = "src"
    layer.subsetString.return_value = layer_subset
    layer.selectedFeatureCount.return_value = 0
    builder = ExpressionBuilder(task_parameters=task.task_parameters, source_layer=layer,
                                current_predicates={"ST_Intersects": "ST_Intersects"})
    return builder._prepare_source_filter("PostgreSQL")


@pytest.mark.parametrize("old_subset, operator, subset, selection", [
    # AND NOT without a filter: the source keeps every feature but x, the targets follow x
    ("", "AND NOT", f"NOT (\n{X}\n)", X),
    # AND NOT after a filter: x read through the old subset, as the dock selects
    (OLD, "AND NOT", f"( {OLD} ) AND NOT ( {X} )", f"( {OLD} ) AND ( {X} )"),
    # OR: x read on the whole layer
    (OLD, "OR", f"( {OLD} ) OR ( {X} )", X),
    # AND: the new subset is the selection, unchanged
    (OLD, "AND", f"( {OLD} ) AND ( {X} )", f"( {OLD} ) AND ( {X} )"),
    ("", "AND", X, X),
    # replace: the new subset is x
    (OLD, None, X, X),
])
def test_the_targets_follow_the_selection_without_features(facade_module, old_subset, operator, subset, selection):
    task = _task(old_subset, operator)

    _queue(facade_module, task)

    # the source itself gets the combined subset
    assert task._pending_subset_requests == [(task.source_layer, subset)]
    assert task.task_parameters["source_subset_after_task"] == subset
    # its targets the selection
    assert task.task_parameters["source_selection_after_task"] == selection
    assert _distant_source_filter(task, old_subset) == selection


def test_and_not_with_a_selection_keeping_nothing_never_filters_by_the_whole_source(facade_module):
    # x keeps nothing: the dock sends no feature. NOT (x) matched every source feature.
    task = _task("", "AND NOT")
    nothing = '"src"."pop" > 1e12'

    _queue(facade_module, task, nothing)

    assert _distant_source_filter(task, "") == nothing


def test_with_features_the_selected_features_stay_the_source_selection(facade_module, monkeypatch):
    task = _task(OLD, "AND NOT")
    _queue(facade_module, task)

    class _Feature:
        def __init__(self, fid):
            self._fid = fid

        def id(self):
            return self._fid

        def geometry(self):
            return None

    task.task_parameters["task"]["features"] = [_Feature(7)]
    layer = MagicMock()
    layer.subsetString.return_value = OLD
    layer.selectedFeatureCount.return_value = 0
    builder = ExpressionBuilder(task_parameters=task.task_parameters, source_layer=layer,
                                current_predicates={"ST_Intersects": "ST_Intersects"})
    monkeypatch.setattr(builder, "_generate_fid_filter",
                        lambda features, backend_name=None: f"<FIDS {[f.id() for f in features]}>")

    assert builder._prepare_source_filter("PostgreSQL") == "<FIDS [7]>"


def test_another_queued_filter_records_no_stale_selection(facade_module):
    # the expression was combined, then a key list queued instead (its apply failed):
    # the selection of the expression must not stand for the key list
    task = _task("", "AND NOT")
    facade = facade_module.ExpressionFacadeHandler(task)
    facade.combine_with_old_subset(X)

    assert facade.apply_filter_and_update_subset('NOT (\n"src"."fid" IN (7)\n)') is True

    assert task.task_parameters["source_selection_after_task"] is None
    assert task.task_parameters["source_subset_after_task"] == 'NOT (\n"src"."fid" IN (7)\n)'


class _Request:
    """QgsFeatureRequest recording its filter expression."""

    class Flag:
        NoGeometry = 1

    def __init__(self):
        self.expression = None

    def setFlags(self, flags):
        return self

    def setFilterExpression(self, expression):
        self.expression = expression
        return self


EXISTS_OLD = ('EXISTS (SELECT 1 FROM "public"."zone" AS __source '
              'WHERE ST_Intersects("src"."geom", __source."geom"))')


def _path_3a(monkeypatch, task, kept):
    """PATH 3A: the selection holds an EXISTS of a previous geometric filter, no feature was sent."""
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsFeatureRequest", _Request, raising=False)
    layer = MagicMock()
    layer.name.return_value = "src"
    layer.subsetString.return_value = EXISTS_OLD
    layer.selectedFeatureCount.return_value = 0
    layer.featureCount.return_value = 3
    requests = []
    layer.getFeatures.side_effect = lambda request: requests.append(request) or list(kept)
    builder = ExpressionBuilder(task_parameters=task.task_parameters, source_layer=layer,
                                current_predicates={"ST_Intersects": "ST_Intersects"})
    monkeypatch.setattr(builder, "_generate_fid_filter",
                        lambda features, backend_name=None: f"<FIDS {list(features)}>")
    return builder._prepare_source_filter("PostgreSQL"), requests


def test_path_3a_reads_the_selection_through_the_old_subset(facade_module, monkeypatch):
    # the layer still holds its previous (EXISTS) subset: its features were the
    # source of the targets whatever the new selection
    task = _task(EXISTS_OLD, "AND NOT")
    task.task_parameters["task"]["expression"] = '"pop" > 1000'
    _queue(facade_module, task)

    source_filter, requests = _path_3a(monkeypatch, task, kept=[4])

    assert [request.expression for request in requests] == ['"pop" > 1000']
    assert source_filter == "<FIDS [4]>"


def test_path_3a_selection_keeping_nothing_matches_no_source_feature(facade_module, monkeypatch):
    # None meant every source feature
    task = _task(EXISTS_OLD, "AND")
    task.task_parameters["task"]["expression"] = '"pop" > 1e12'
    _queue(facade_module, task)

    source_filter, _ = _path_3a(monkeypatch, task, kept=[])

    assert source_filter == "FALSE"


def test_path_3a_without_a_recorded_selection_reads_the_layer_as_before(monkeypatch):
    # all features / field-based modes queue no subset: the filtered layer is the source
    task = MagicMock()
    task.task_parameters = {"task": {"features": [], "expression": "pop"}, "param_source_table": "src"}

    source_filter, requests = _path_3a(monkeypatch, task, kept=[])

    assert [request.expression for request in requests] == [None]
    assert source_filter is None

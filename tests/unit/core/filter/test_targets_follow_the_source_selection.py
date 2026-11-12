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

    def setLimit(self, limit):
        self.limit = limit
        return self


class _Expression:
    """QgsExpression whose parse result follows the texts the test marks as unreadable."""

    unreadable = set()

    def __init__(self, text):
        self.text = text

    def hasParserError(self):
        return self.text in self.unreadable

    def parserErrorString(self):
        return "syntax error"


EXISTS_OLD = ('EXISTS (SELECT 1 FROM "public"."zone" AS __source '
              'WHERE ST_Intersects("src"."geom", __source."geom"))')


def _source_layer(kept, subset=EXISTS_OLD, requests=None):
    """A source layer holding ``subset`` whose reading gives ``kept``, recording its requests."""
    layer = MagicMock()
    layer.name.return_value = "src"
    layer.subsetString.return_value = subset
    layer.selectedFeatureCount.return_value = 0
    layer.featureCount.return_value = 3
    requests = [] if requests is None else requests
    layer.getFeatures.side_effect = lambda request: requests.append(request) or list(kept)
    return layer, requests


def _builder(monkeypatch, task, layer, unfiltered=None):
    """The builder of the distant filters; ``unfiltered``: the copy of the source without its subset."""
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsFeatureRequest", _Request, raising=False)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsExpression", _Expression, raising=False)
    builder = ExpressionBuilder(task_parameters=task.task_parameters, source_layer=layer,
                                current_predicates={"ST_Intersects": "ST_Intersects"})
    monkeypatch.setattr(builder, "_generate_fid_filter",
                        lambda features, backend_name=None: f"<FIDS {list(features)}>")
    monkeypatch.setattr(builder, "_unfiltered_source", lambda: unfiltered, raising=False)
    return builder


def _path_3a(monkeypatch, task, kept):
    """PATH 3A: the selection holds an EXISTS of a previous geometric filter, no feature was sent."""
    layer, requests = _source_layer(kept)
    return _builder(monkeypatch, task, layer)._prepare_source_filter("PostgreSQL"), requests


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


# ---------------------------------------------------------------------------
# 2026-11-12 (review of #387): where the selection is read, and the refusals
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[4]
X_EXISTS = 'EXISTS (SELECT 1 FROM "public"."other" AS o WHERE o."id" = "src"."id")'


@pytest.fixture
def refusal(monkeypatch):
    """SourceSelectionError, its module importable by its top-level name and the translation plain.

    The builder is imported from the repository root here, so it falls back on
    ``adapters.backends.source_refusal``; the ``adapters`` package itself
    cannot be imported that way (relative imports beyond it).
    """
    import types
    for name, path in (("adapters", _ROOT / "adapters"), ("adapters.backends", _ROOT / "adapters" / "backends")):
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        monkeypatch.setitem(sys.modules, name, package)
    name = "adapters.backends.source_refusal"
    spec = importlib.util.spec_from_file_location(name, _ROOT / "adapters" / "backends" / "source_refusal.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys.modules["qgis.PyQt.QtCore"], "QCoreApplication",
                        MagicMock(translate=lambda context, text: text), raising=False)
    monkeypatch.setattr(_Expression, "unreadable", set())
    return module.SourceSelectionError


@pytest.mark.parametrize("old_subset, operator, whole_layer", [
    (OLD, "AND NOT", False),
    (OLD, "AND", False),
    ("", "AND NOT", False),
    (OLD, "OR", True),
    (OLD, None, True),
])
def test_the_facade_records_where_the_selection_is_read(facade_module, old_subset, operator, whole_layer):
    # as selection_reads_whole_layer on SpatiaLite / OGR: through the old subset
    # under AND and AND NOT, on the whole layer under OR and replace
    task = _task(old_subset, operator)

    _queue(facade_module, task)

    assert task.task_parameters["source_selection_reads_whole_layer"] is whole_layer


def test_no_reading_recorded_for_another_queued_filter(facade_module):
    task = _task(OLD, "OR")
    facade = facade_module.ExpressionFacadeHandler(task)
    facade.combine_with_old_subset(X)

    assert facade.apply_filter_and_update_subset('"src"."fid" IN (7)') is True

    assert task.task_parameters["source_selection_reads_whole_layer"] is None


@pytest.mark.parametrize("operator", ["OR", None])
def test_path_3a_reads_the_selection_on_the_whole_layer_under_or_and_replace(
        facade_module, monkeypatch, refusal, operator):
    # Review probe: OR, old subset "dep" = '31', x holding an EXISTS. The layer
    # still holds the old subset: x read through it kept nothing (FALSE).
    task = _task(OLD, operator)
    task.task_parameters["task"]["expression"] = '"pop" > 1000'
    _queue(facade_module, task, X_EXISTS)
    assert task.task_parameters["source_selection_after_task"] == X_EXISTS
    layer, layer_requests = _source_layer(kept=[], subset=OLD)
    unfiltered, copy_requests = _source_layer(kept=[5, 6], subset="")

    source_filter = _builder(monkeypatch, task, layer, unfiltered)._prepare_source_filter("PostgreSQL")

    assert layer_requests == []
    assert [request.expression for request in copy_requests] == ['"pop" > 1000']
    assert source_filter == "<FIDS [5, 6]>"


def test_path_3a_reads_the_selection_through_the_old_subset_under_and_not(facade_module, monkeypatch, refusal):
    task = _task(EXISTS_OLD, "AND NOT")
    task.task_parameters["task"]["expression"] = '"pop" > 1000'
    _queue(facade_module, task)
    layer, layer_requests = _source_layer(kept=[4])
    unfiltered = MagicMock(name="never read")

    source_filter = _builder(monkeypatch, task, layer, unfiltered)._prepare_source_filter("PostgreSQL")

    assert [request.expression for request in layer_requests] == ['"pop" > 1000']
    unfiltered.getFeatures.assert_not_called()
    assert source_filter == "<FIDS [4]>"


def _checked(monkeypatch, task, kept, subset=EXISTS_OLD, unfiltered=None):
    layer, requests = _source_layer(kept, subset=subset)
    _builder(monkeypatch, task, layer, unfiltered).check_source_selection()
    return requests


@pytest.mark.parametrize("old_subset", [EXISTS_OLD, OLD])  # PATH 3A, PATH 2
@pytest.mark.parametrize("operator", ["AND", "AND NOT"])
def test_a_selection_keeping_nothing_is_refused_before_the_targets(
        facade_module, monkeypatch, refusal, old_subset, operator):
    # Both paths emptied the targets with no word (FALSE, or the SQL of a
    # selection keeping nothing); SpatiaLite / OGR refuse.
    task = _task(old_subset, operator)
    task.task_parameters["task"]["expression"] = '"pop" > 1e12'
    _queue(facade_module, task)

    with pytest.raises(refusal, match="keeps no feature: nothing was filtered"):
        _checked(monkeypatch, task, kept=[], subset=old_subset)


def test_an_unreadable_selection_is_refused_as_such(facade_module, monkeypatch, refusal):
    # PATH 3A read nothing from an expression QGIS cannot parse: FALSE, the
    # targets emptied. Refused as SpatiaLite / OGR do (_features_matching).
    task = _task(EXISTS_OLD, "AND NOT")
    task.task_parameters["task"]["expression"] = '"pop"::int > 3'
    _queue(facade_module, task)
    monkeypatch.setattr(_Expression, "unreadable", {'"pop"::int > 3'})

    with pytest.raises(refusal, match="cannot be evaluated: nothing was filtered"):
        _checked(monkeypatch, task, kept=[4])


def test_a_selection_failing_to_evaluate_is_refused_as_unreadable(facade_module, monkeypatch, refusal):
    task = _task(EXISTS_OLD, "AND")
    task.task_parameters["task"]["expression"] = '"pop" > 3'
    _queue(facade_module, task)
    layer, _ = _source_layer(kept=[])
    layer.getFeatures.side_effect = RuntimeError("evaluation failed")

    with pytest.raises(refusal, match="cannot be evaluated"):
        _builder(monkeypatch, task, layer).check_source_selection()


def test_a_selection_keeping_features_is_read_once_and_not_refused(facade_module, monkeypatch, refusal):
    task = _task(EXISTS_OLD, "AND NOT")
    task.task_parameters["task"]["expression"] = '"pop" > 1000'
    _queue(facade_module, task)

    requests = _checked(monkeypatch, task, kept=[4])

    assert [(request.expression, request.limit) for request in requests] == [('"pop" > 1000', 1)]


def test_the_check_reads_the_whole_layer_under_or(facade_module, monkeypatch, refusal):
    # the old subset keeps none of x: not a reason to refuse under OR
    task = _task(OLD, "OR")
    task.task_parameters["task"]["expression"] = '"pop" > 1000'
    _queue(facade_module, task)
    unfiltered, copy_requests = _source_layer(kept=[9], subset="")

    layer_requests = _checked(monkeypatch, task, kept=[], subset=OLD, unfiltered=unfiltered)

    assert layer_requests == []
    assert [request.expression for request in copy_requests] == ['"pop" > 1000']


def test_no_check_when_features_were_sent(facade_module, monkeypatch, refusal):
    # the selected features are the source of the targets (PATH 1)
    task = _task(EXISTS_OLD, "AND NOT")
    task.task_parameters["task"]["expression"] = '"pop" > 1e12'
    _queue(facade_module, task)
    task.task_parameters["task"]["features"] = [MagicMock()]

    assert _checked(monkeypatch, task, kept=[]) == []


def test_no_check_without_a_recorded_selection(monkeypatch, refusal):
    # all features / field-based modes: the filtered layer is the source, as before
    task = MagicMock()
    task.task_parameters = {"task": {"features": [], "expression": "pop"}, "param_source_table": "src"}

    assert _checked(monkeypatch, task, kept=[]) == []


def _filter_task_method(name):
    import ast
    path = _ROOT / "core" / "tasks" / "filter_task.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                namespace = {}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)  # nosec B102
                return namespace[name]
    raise AssertionError(f"{name} not found")


def test_the_postgresql_source_preparation_checks_the_selection_first():
    # the refusal must come before any target: the orchestrator only drops the
    # source subset of a refused filter, not the subsets of targets already filtered
    prepare = _filter_task_method("prepare_postgresql_source_geom")
    task = MagicMock()
    task._get_expression_builder.return_value.check_source_selection.side_effect = ValueError("refused")

    with pytest.raises(ValueError, match="refused"):
        prepare(task)

    task._source_geom_preparer.prepare_postgresql_source_geom.assert_not_called()


# ---------------------------------------------------------------------------
# Chain with a buffer expression (spatial_chain)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("operator", ["AND", "AND NOT"])
def test_the_chain_with_a_buffer_expression_keeps_the_selection(facade_module, monkeypatch, refusal, operator):
    # Review probe: the old subset holds an EXISTS and a buffer expression is
    # set. The chain kept the EXISTS of ( EXISTS old ) AND ( x ) only: x was
    # lost and the buffer covered the whole source table.
    task = _task(EXISTS_OLD, operator)
    task.task_parameters["task"]["expression"] = '"pop" > 1000'
    task.task_parameters["param_combine_operator"] = "AND"
    _queue(facade_module, task)
    layer, requests = _source_layer(kept=[4])
    builder = _builder(monkeypatch, task, layer)
    builder.buffer_expression = '"radius"'

    source_filter = builder._prepare_source_filter("PostgreSQL")

    assert [request.expression for request in requests] == ['"pop" > 1000']
    assert source_filter == "<FIDS [4]>"


def test_the_chain_without_a_recorded_selection_is_unchanged(monkeypatch, refusal):
    # all features: the source is its filtered layer, its EXISTS chained to the targets
    task = MagicMock()
    task.task_parameters = {"task": {"features": [], "expression": ""}, "param_source_table": "src",
                            "param_combine_operator": "AND"}
    layer, requests = _source_layer(kept=[])
    builder = _builder(monkeypatch, task, layer)
    builder.buffer_expression = '"radius"'

    assert builder._prepare_source_filter("PostgreSQL") == f"({EXISTS_OLD})"
    assert requests == []

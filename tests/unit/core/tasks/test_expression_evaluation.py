# -*- coding: utf-8 -*-
"""
Tests for ExpressionEvaluationManager and ExpressionEvaluationTask.

Covers:
- Manager lifecycle: evaluate, cancel, cancel_all, is_evaluating
- Validation guards: invalid layer / empty expression
- Signal wiring and active-task tracking
- Task parse cache added in commit 0514548b (self._qgs_expr reused by
  _build_feature_request instead of re-parsing self.expression_string)
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


# The conftest in this directory has already loaded
# 'filter_mate.core.tasks.expression_evaluation_task' via importlib.
# We pull the classes out of that module.
_EET_MODULE = sys.modules.get('filter_mate.core.tasks.expression_evaluation_task')

if _EET_MODULE is None:
    pytest.skip(
        "expression_evaluation_task module not loaded by conftest",
        allow_module_level=True,
    )

ExpressionEvaluationManager = _EET_MODULE.ExpressionEvaluationManager
ExpressionEvaluationTask = _EET_MODULE.ExpressionEvaluationTask
get_expression_manager = _EET_MODULE.get_expression_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_layer():
    layer = MagicMock()
    layer.isValid.return_value = True
    layer.id.return_value = "layer_42"
    layer.name.return_value = "test_layer"
    return layer


@pytest.fixture
def invalid_layer():
    layer = MagicMock()
    layer.isValid.return_value = False
    layer.id.return_value = "layer_invalid"
    return layer


@pytest.fixture
def manager():
    """Fresh manager instance per test."""
    return ExpressionEvaluationManager()


@pytest.fixture
def patched_task():
    """Patch ExpressionEvaluationTask so evaluate() doesn't create a real task.

    Also patches QgsApplication so addTask is observable.
    """
    with patch.object(_EET_MODULE, 'ExpressionEvaluationTask') as mock_task_cls, \
         patch.object(_EET_MODULE, 'QgsApplication') as mock_qgs_app:

        # Each call returns a fresh MagicMock so we can track per-task state
        def make_task(*args, **kwargs):
            task = MagicMock()
            task.signals = MagicMock()
            task.isCanceled.return_value = False
            return task

        mock_task_cls.side_effect = make_task
        yield mock_task_cls, mock_qgs_app


# ---------------------------------------------------------------------------
# Validation guards
# ---------------------------------------------------------------------------

class TestValidationGuards:

    def test_invalid_layer_returns_none_and_calls_error_callback(
        self, manager, invalid_layer
    ):
        on_error = MagicMock()
        result = manager.evaluate(
            layer=invalid_layer,
            expression='"a" > 0',
            on_error=on_error,
        )
        assert result is None
        on_error.assert_called_once()
        # First positional arg is the message
        assert "Invalid layer" in on_error.call_args[0][0]

    def test_none_layer_returns_none(self, manager):
        on_error = MagicMock()
        result = manager.evaluate(
            layer=None,
            expression='"a" > 0',
            on_error=on_error,
        )
        assert result is None
        on_error.assert_called_once()

    def test_empty_expression_returns_none(self, manager, valid_layer):
        on_error = MagicMock()
        result = manager.evaluate(
            layer=valid_layer,
            expression="",
            on_error=on_error,
        )
        assert result is None
        on_error.assert_called_once()
        assert "Empty expression" in on_error.call_args[0][0]
        # layer_id is passed as second arg
        assert on_error.call_args[0][1] == "layer_42"


# ---------------------------------------------------------------------------
# Task creation, tracking, cancel semantics
# ---------------------------------------------------------------------------

class TestEvaluate:

    def test_creates_task_and_submits_to_task_manager(
        self, manager, valid_layer, patched_task
    ):
        _, mock_qgs_app = patched_task
        task = manager.evaluate(layer=valid_layer, expression='"a" > 0')
        assert task is not None
        mock_qgs_app.taskManager.return_value.addTask.assert_called_once_with(task)

    def test_tracks_active_task_by_layer_id(
        self, manager, valid_layer, patched_task
    ):
        manager.evaluate(layer=valid_layer, expression='"a" > 0')
        assert manager.is_evaluating("layer_42") is True
        assert manager.is_evaluating("other_layer") is False

    def test_connects_user_callbacks(self, manager, valid_layer, patched_task):
        on_complete = MagicMock()
        on_error = MagicMock()
        on_progress = MagicMock()
        on_cancelled = MagicMock()

        task = manager.evaluate(
            layer=valid_layer,
            expression='"a" > 0',
            on_complete=on_complete,
            on_error=on_error,
            on_progress=on_progress,
            on_cancelled=on_cancelled,
        )

        task.signals.finished.connect.assert_any_call(on_complete)
        task.signals.error.connect.assert_any_call(on_error)
        task.signals.progress.connect.assert_any_call(on_progress)
        task.signals.cancelled.connect.assert_any_call(on_cancelled)

    def test_cancels_existing_task_for_same_layer_by_default(
        self, manager, valid_layer, patched_task
    ):
        first = manager.evaluate(layer=valid_layer, expression='"a" > 0')
        second = manager.evaluate(layer=valid_layer, expression='"b" > 0')

        # First task was cancelled because cancel_existing=True is the default
        first.cancel.assert_called_once()
        # Second task exists and is tracked
        assert second is not None
        assert manager.is_evaluating("layer_42") is True

    def test_preserves_existing_task_when_cancel_existing_false(
        self, manager, valid_layer, patched_task
    ):
        first = manager.evaluate(layer=valid_layer, expression='"a" > 0')
        manager.evaluate(
            layer=valid_layer,
            expression='"b" > 0',
            cancel_existing=False,
        )

        first.cancel.assert_not_called()

    def test_skips_cancel_if_existing_already_cancelled(
        self, manager, valid_layer, patched_task
    ):
        first = manager.evaluate(layer=valid_layer, expression='"a" > 0')
        first.isCanceled.return_value = True  # already done
        manager.evaluate(layer=valid_layer, expression='"b" > 0')

        first.cancel.assert_not_called()

    def test_different_layers_tracked_independently(
        self, manager, patched_task
    ):
        layer_a = MagicMock(); layer_a.isValid.return_value = True; layer_a.id.return_value = "A"; layer_a.name.return_value = "A"
        layer_b = MagicMock(); layer_b.isValid.return_value = True; layer_b.id.return_value = "B"; layer_b.name.return_value = "B"

        manager.evaluate(layer=layer_a, expression='"x" > 0')
        manager.evaluate(layer=layer_b, expression='"x" > 0')

        assert manager.is_evaluating("A") is True
        assert manager.is_evaluating("B") is True


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------

class TestCancel:

    def test_cancel_returns_true_and_cancels_task(
        self, manager, valid_layer, patched_task
    ):
        task = manager.evaluate(layer=valid_layer, expression='"a" > 0')
        result = manager.cancel("layer_42")
        assert result is True
        task.cancel.assert_called_once()

    def test_cancel_returns_false_when_no_active(self, manager):
        assert manager.cancel("nonexistent") is False

    def test_cancel_returns_false_when_already_cancelled(
        self, manager, valid_layer, patched_task
    ):
        task = manager.evaluate(layer=valid_layer, expression='"a" > 0')
        task.isCanceled.return_value = True
        assert manager.cancel("layer_42") is False

    def test_cancel_all_cancels_every_active_task(self, manager, patched_task):
        layer_a = MagicMock(); layer_a.isValid.return_value = True; layer_a.id.return_value = "A"; layer_a.name.return_value = "A"
        layer_b = MagicMock(); layer_b.isValid.return_value = True; layer_b.id.return_value = "B"; layer_b.name.return_value = "B"

        t_a = manager.evaluate(layer=layer_a, expression='"x" > 0')
        t_b = manager.evaluate(layer=layer_b, expression='"x" > 0')

        manager.cancel_all()

        t_a.cancel.assert_called_once()
        t_b.cancel.assert_called_once()


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

class TestGetExpressionManager:

    def test_returns_same_instance_across_calls(self):
        # Reset the module-level singleton for isolation
        _EET_MODULE._expression_manager = None

        m1 = get_expression_manager()
        m2 = get_expression_manager()
        assert m1 is m2
        assert isinstance(m1, ExpressionEvaluationManager)


# ---------------------------------------------------------------------------
# Parse cache regression (commit 0514548b)
# ---------------------------------------------------------------------------

class TestParseCacheRegression:
    """
    Regression tests for the expression parse cache added to
    ExpressionEvaluationTask. Before the fix, _validate_inputs() and
    _build_feature_request() each called QgsExpression(expression_string),
    parsing the same string twice per task run.
    """

    def _make_fake_self(self):
        """
        Build a plain-object "self" we can pass explicitly to unbound methods.
        ExpressionEvaluationTask inherits from QgsTask, which is MagicMock in
        this test env, so direct instantiation hits MagicMock __setattr__
        quirks. We sidestep that by using a SimpleNamespace-equivalent
        object and calling methods via `Class.method(fake_self)`.
        """
        class _Fake:
            pass
        fake = _Fake()
        fake.expression_string = '"population" > 10000'
        fake.layer = MagicMock()
        fake.layer_name = "test_layer"
        fake._feature_source = MagicMock()
        fake.limit = 0
        fake.request_fields = None
        fake.include_geometry = True
        fake._qgs_expr = None
        fake.exception = None
        fake._options = lambda request: ExpressionEvaluationTask._options(fake, request)
        fake._prepare_context = MagicMock()
        return fake

    def test_validate_inputs_populates_parsed_expression_cache(self):
        fake = self._make_fake_self()

        with patch.object(_EET_MODULE, 'QgsExpression') as mock_expr_cls:
            parsed = MagicMock()
            parsed.hasParserError.return_value = False
            mock_expr_cls.return_value = parsed

            ok = ExpressionEvaluationTask._validate_inputs(fake)

        assert ok is True
        assert fake._qgs_expr is parsed

    def test_build_feature_request_reuses_cached_expression(self):
        fake = self._make_fake_self()
        cached = MagicMock()
        fake._qgs_expr = cached

        with patch.object(_EET_MODULE, 'QgsExpression') as mock_expr_cls, \
             patch.object(_EET_MODULE, 'QgsFeatureRequest') as mock_req_cls:
            mock_req_cls.return_value = MagicMock()

            ExpressionEvaluationTask._build_feature_request(fake)

        # The cached instance was used — no new QgsExpression was constructed
        mock_expr_cls.assert_not_called()
        mock_req_cls.assert_called_once_with(cached)

    def test_build_feature_request_falls_back_when_cache_empty(self):
        fake = self._make_fake_self()
        fake._qgs_expr = None  # e.g. _validate_inputs was skipped

        with patch.object(_EET_MODULE, 'QgsExpression') as mock_expr_cls, \
             patch.object(_EET_MODULE, 'QgsFeatureRequest') as mock_req_cls:
            fresh = MagicMock()
            mock_expr_cls.return_value = fresh
            mock_req_cls.return_value = MagicMock()

            ExpressionEvaluationTask._build_feature_request(fake)

        # Fallback path: a new QgsExpression is constructed once
        mock_expr_cls.assert_called_once_with('"population" > 10000')
        mock_req_cls.assert_called_once_with(fresh)


# ---------------------------------------------------------------------------
# 2026-10-17: the worker never reads the layer; a canceled task keeps its successor
# ---------------------------------------------------------------------------

class TestThreadSafety:

    def test_the_end_of_a_replaced_task_keeps_its_successor(self, manager, valid_layer, patched_task):
        first = manager.evaluate(layer=valid_layer, expression='"a" > 0')
        second = manager.evaluate(layer=valid_layer, expression='"b" > 0')
        first_done = first.signals.cancelled.connect.call_args.args[0]
        first_done()  # the canceled first task ends after the second one started
        assert manager._active_tasks["layer_42"] is second
        second.signals.finished.connect.call_args.args[0]()
        assert "layer_42" not in manager._active_tasks

    def test_the_fields_are_read_on_the_main_thread(self):
        fake = TestParseCacheRegression()._make_fake_self()
        fake.request_fields = ["population"]
        fields = fake._fields = MagicMock()
        with patch.object(_EET_MODULE, 'QgsExpression'), \
             patch.object(_EET_MODULE, 'QgsFeatureRequest') as mock_req_cls:
            ExpressionEvaluationTask._build_feature_request(fake)
        mock_req_cls.return_value.setSubsetOfAttributes.assert_called_once_with(["population"], fields)
        fake.layer.fields.assert_not_called()

    def test_prepare_reads_source_count_and_fields(self):
        fake = TestParseCacheRegression()._make_fake_self()
        fake.layer.isValid.return_value = True
        ExpressionEvaluationTask._prepare_feature_source(fake)
        assert fake._feature_source is fake.layer.dataProvider.return_value.featureSource.return_value
        assert fake._fields is fake.layer.fields.return_value

    def test_run_does_not_refresh_the_source_from_the_worker(self):
        fake = TestParseCacheRegression()._make_fake_self()
        fake._validate_inputs = MagicMock(return_value=False)
        ExpressionEvaluationTask.run(fake)
        fake.layer.dataProvider.assert_not_called()
        fake.layer.isValid.assert_not_called()

    def test_a_subset_change_before_the_end_restarts_the_evaluation(self, manager, valid_layer, patched_task):
        """2026-10-17 review: the snapshot of the source predates a filter applied while it was queued."""
        slots = []
        valid_layer.subsetStringChanged.connect.side_effect = slots.append
        valid_layer.subsetStringChanged.disconnect.side_effect = lambda slot: slots.remove(slot)
        on_complete = MagicMock()
        first = manager.evaluate(layer=valid_layer, expression='"a" > 0', on_complete=on_complete)
        assert len(slots) == 1
        slots[0]()  # the filter task applied its subset
        second = manager._active_tasks["layer_42"]
        assert second is not first
        first.cancel.assert_called_once_with()
        second.signals.finished.connect.assert_any_call(on_complete)  # same callbacks
        assert len(slots) == 1  # the first watch is gone, the second one remains

    def test_the_watch_ends_with_the_task(self, manager, valid_layer, patched_task):
        slots = []
        valid_layer.subsetStringChanged.connect.side_effect = slots.append
        valid_layer.subsetStringChanged.disconnect.side_effect = lambda slot: slots.remove(slot)
        task = manager.evaluate(layer=valid_layer, expression='"a" > 0')
        task.signals.finished.connect.call_args_list[-1].args[0]()  # _on_task_done
        assert slots == []


# ---------------------------------------------------------------------------
# 2026-11-13: the worker evaluates as the main thread does, or the main thread reads
# ---------------------------------------------------------------------------

class TestContext:
    """2026-11-13: above async_expression_threshold the same custom selection kept other features: the
    worker had the variables of the expression only ($area planar on a layer in degrees, is_selected() and
    mean("pop") without their layer). It now gets the variables and measure settings as values, read on the
    main thread; an expression that needs the layer itself is read on the main thread."""

    @staticmethod
    def _prepare(fake, worker_context, needs_layer=False, features=()):
        """Run _prepare_context with the adapters it imports replaced; returns the with_layer_context mock."""
        import types
        fake._options = lambda request: ExpressionEvaluationTask._options(fake, request)
        iterator = MagicMock()
        iterator.__iter__.return_value = iter(features)
        fake.layer.getFeatures.return_value = iterator
        with_layer_context = MagicMock(side_effect=lambda request, layer: request)
        modules = {
            'filter_mate.adapters.qgis.async_query': types.SimpleNamespace(
                worker_expression_context=MagicMock(return_value=worker_context)),
            'filter_mate.adapters.backends.source_refusal': types.SimpleNamespace(
                with_layer_context=with_layer_context),
        }
        with patch.dict(sys.modules, modules), \
                patch.object(_EET_MODULE, 'QgsExpression') as mock_expr_cls, \
                patch.object(_EET_MODULE, 'QgsFeatureRequest') as mock_req_cls, \
                patch.object(_EET_MODULE, 'needs_the_layer', return_value=needs_layer):
            mock_expr_cls.return_value.hasParserError.return_value = False
            mock_req_cls.return_value.setFilterExpression.return_value = mock_req_cls.return_value
            ExpressionEvaluationTask._prepare_context(fake, MagicMock(name='provider'))
        return with_layer_context

    def test_a_worker_gets_the_context_of_values_read_on_the_main_thread(self):
        fake = TestParseCacheRegression()._make_fake_self()
        fake.expression_string = '$area > 500000 AND "pop" > @seuil'
        context = MagicMock(name='values')
        with_layer_context = self._prepare(fake, context)
        assert fake._context is context
        assert getattr(fake, '_main_thread_features', None) is None
        fake.layer.getFeatures.assert_not_called()  # the worker reads the provider snapshot
        with_layer_context.assert_not_called()

    def test_the_worker_request_holds_the_context(self):
        fake = TestParseCacheRegression()._make_fake_self()
        fake._context = MagicMock(name='values')
        with patch.object(_EET_MODULE, 'QgsExpression'), \
             patch.object(_EET_MODULE, 'QgsFeatureRequest') as mock_req_cls:
            ExpressionEvaluationTask._build_feature_request(fake)
        mock_req_cls.return_value.setExpressionContext.assert_called_once_with(fake._context)
        fake.layer.fields.assert_not_called()

    @pytest.mark.parametrize('worker_context, needs_layer', [
        (None, False),  # is_selected(), mean("pop"), @layer...: no context of values
        (MagicMock(name='values'), True),  # a virtual field, unsaved edits
    ])
    def test_an_expression_needing_the_layer_is_read_on_the_main_thread(self, worker_context, needs_layer):
        fake = TestParseCacheRegression()._make_fake_self()
        fake.expression_string = 'is_selected() = false'
        kept = [MagicMock(name='f1'), MagicMock(name='f2')]
        with_layer_context = self._prepare(fake, worker_context, needs_layer, kept)
        assert fake._main_thread_features == kept
        fake.layer.getFeatures.return_value.close.assert_called_once_with()
        assert with_layer_context.call_args.args[1] is fake.layer  # the full context of the layer, as EXPLORING
        fake._validate_inputs = MagicMock()
        assert ExpressionEvaluationTask.run(fake) is True
        assert fake.result_features == kept
        fake._validate_inputs.assert_not_called()  # the worker reads nothing

    def test_a_failed_reading_on_the_main_thread_is_an_error_of_the_task(self):
        fake = TestParseCacheRegression()._make_fake_self()
        fake.layer.getFeatures.side_effect = RuntimeError('layer deleted')
        self._prepare(fake, None)
        assert isinstance(fake.exception, RuntimeError)
        fake._validate_inputs = MagicMock()
        assert ExpressionEvaluationTask.run(fake) is False
        fake._validate_inputs.assert_not_called()

    def test_an_expression_that_does_not_parse_is_left_to_run(self):
        fake = TestParseCacheRegression()._make_fake_self()
        fake._context = None
        with patch.object(_EET_MODULE, 'QgsExpression') as mock_expr_cls:
            mock_expr_cls.return_value.hasParserError.return_value = True
            ExpressionEvaluationTask._prepare_context(fake, MagicMock())
        assert fake._context is None and getattr(fake, '_main_thread_features', None) is None
        fake.layer.getFeatures.assert_not_called()


class TestNeedsTheLayer:

    @staticmethod
    def _fields(names):
        fields = MagicMock()
        fields.lookupField.side_effect = lambda name: names.index(name) if name in names else -1
        fields.count.return_value = len(names)
        attributes = []
        for name in names:
            field = MagicMock()
            field.name.return_value = name
            attributes.append(field)
        fields.__iter__.side_effect = lambda: iter(attributes)
        return fields

    def _check(self, columns, layer_names=('id', 'pop'), modified=False, request_fields=None):
        layer, provider = MagicMock(), MagicMock()
        layer.isModified.return_value = modified
        layer.fields.return_value = self._fields(list(layer_names))
        provider.fields.return_value = self._fields(['id', 'pop'])
        with patch.object(_EET_MODULE, 'QgsExpression') as mock_expr_cls:
            mock_expr_cls.return_value.referencedColumns.return_value = set(columns)
            return _EET_MODULE.needs_the_layer(layer, provider, 'expression', request_fields)

    def test_fields_of_the_provider_are_read_by_the_worker(self):
        assert self._check({'pop'}) is False
        assert self._check(set()) is False

    def test_a_virtual_or_joined_field_needs_the_layer(self):
        assert self._check({'pop', 'density'}, ('id', 'pop', 'density')) is True

    def test_all_attributes_need_the_layer_only_with_fields_beyond_the_provider(self):
        assert self._check({'#!allattributes!#'}) is False
        assert self._check({'#!allattributes!#'}, ('id', 'pop', 'density')) is True

    def test_unsaved_edits_need_the_layer(self):
        assert self._check({'pop'}, modified=True) is True

    def test_a_virtual_field_returned_but_not_used_by_the_filter_needs_the_layer(self):
        assert self._check({'pop'}, ('id', 'pop', 'density')) is True

    def test_only_provider_fields_requested_can_use_the_worker(self):
        assert self._check({'pop'}, ('id', 'pop', 'density'), request_fields=['pop']) is False

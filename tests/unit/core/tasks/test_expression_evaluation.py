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

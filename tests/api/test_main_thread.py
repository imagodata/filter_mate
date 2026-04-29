"""Tests for ``filtermate_api.main_thread.run_on_main_thread`` — P0-B.

The helper has two paths:

1. **Headless** — QGIS / Qt is not importable (or only mocked). The
   function runs the callable inline and emits a one-time warning.
2. **QGIS-loaded** — exercised at runtime, not under the headless test
   harness (``pragma: no cover`` markers in the source).

Tests below cover (1) and the wiring on the accessor side: that
``QGISFilterMateAccessor.apply_filter`` and the undo/redo path now
route through the helper rather than calling ``setSubsetString``
straight from the worker thread.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from filtermate_api import main_thread  # noqa: E402
from filtermate_api.main_thread import run_on_main_thread  # noqa: E402


# ---------------------------------------------------------------------------
# Headless path — what the unit-test harness actually exercises
# ---------------------------------------------------------------------------


class TestHeadlessInline:
    def setup_method(self) -> None:
        main_thread.reset_for_tests()

    def test_runs_callable_inline_and_returns_result(self):
        # _HAS_QT is False under conftest mocks (QCoreApplication is a
        # MagicMock instance, not a class). The call should run inline.
        captured = []

        def _fn(a, b, *, c):
            captured.append((a, b, c))
            return a + b + c

        result = run_on_main_thread(_fn, 1, 2, c=3)
        assert result == 6
        assert captured == [(1, 2, 3)]

    def test_propagates_exception_from_callable(self):
        def _explode():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            run_on_main_thread(_explode)

    def test_one_time_headless_warning(self, caplog):
        with caplog.at_level("WARNING", logger="filtermate_api.main_thread"):
            run_on_main_thread(lambda: None)
            run_on_main_thread(lambda: None)
            run_on_main_thread(lambda: None)
        warnings = [r for r in caplog.records if "QGIS/Qt not importable" in r.message]
        # Exactly one warning across three calls — gate via _HEADLESS_WARNED.
        assert len(warnings) == 1, (
            f"Expected one headless warning, got {len(warnings)}"
        )

    def test_zero_args_callable(self):
        # The wrapper used by QMetaObject.invokeMethod expects a no-arg
        # closure; verify the inline path handles a no-arg callable.
        called = []
        run_on_main_thread(lambda: called.append("x"))
        assert called == ["x"]


# ---------------------------------------------------------------------------
# Wiring: ``QGISFilterMateAccessor`` routes via run_on_main_thread
# ---------------------------------------------------------------------------


class TestAccessorRoutesThroughDispatcher:
    def setup_method(self) -> None:
        main_thread.reset_for_tests()

    def _make_accessor(self):
        # Lazy import — avoids picking up Qt mocks before conftest runs.
        from filtermate_api.qgis_accessor import QGISFilterMateAccessor

        public_api = MagicMock()
        public_api.apply_filter.return_value = True
        plugin = MagicMock()
        return QGISFilterMateAccessor(public_api=public_api, plugin=plugin), public_api

    def test_apply_filter_dispatches_via_main_thread_helper(self):
        accessor, public_api = self._make_accessor()

        with patch(
            "filtermate_api.qgis_accessor.run_on_main_thread",
            wraps=run_on_main_thread,
        ) as spy:
            ok = accessor.apply_filter("Layer", "expr", "test")

        assert ok is True
        # Helper was called exactly once for apply_filter.
        assert spy.call_count == 1
        # The first positional arg is the callable to dispatch — must
        # be the public_api method, NOT the result of calling it.
        first_call_args = spy.call_args_list[0]
        assert first_call_args.args[0] is public_api.apply_filter
        # Original kwargs preserved.
        assert first_call_args.kwargs == {
            "layer_name": "Layer",
            "filter_expr": "expr",
            "source_plugin": "test",
        }
        # Public API was actually invoked downstream.
        public_api.apply_filter.assert_called_once_with(
            layer_name="Layer", filter_expr="expr", source_plugin="test"
        )

    def test_apply_filter_returns_false_on_public_api_false(self):
        accessor, public_api = self._make_accessor()
        public_api.apply_filter.return_value = False

        ok = accessor.apply_filter("Layer", "expr", "test")
        assert ok is False
        assert "returned False" in (accessor._last_error or "")

    def test_reapply_previous_filters_inline_skips_missing_layer(self):
        from filtermate_api.qgis_accessor import QGISFilterMateAccessor

        # Project with one resolvable layer and one missing layer.
        layer = MagicMock()
        layer.name.return_value = "Resolved"
        layer.setSubsetString.return_value = None

        project = MagicMock()
        project.mapLayer.side_effect = lambda lid: layer if lid == "ok" else None

        result = QGISFilterMateAccessor._reapply_previous_filters_inline(
            project,
            [("missing", "x"), ("ok", "field='value'")],
        )
        name, expr, is_clear = result
        # Only the resolved layer counts — and its subset was applied.
        assert name == "Resolved"
        assert expr == "field='value'"
        assert is_clear is False
        layer.setSubsetString.assert_called_once_with("field='value'")

    def test_reapply_previous_filters_inline_swallows_setsubset_failure(self):
        from filtermate_api.qgis_accessor import QGISFilterMateAccessor

        bad = MagicMock()
        bad.setSubsetString.side_effect = RuntimeError("locked")
        good = MagicMock()
        good.name.return_value = "Good"

        project = MagicMock()
        project.mapLayer.side_effect = lambda lid: bad if lid == "bad" else good

        result = QGISFilterMateAccessor._reapply_previous_filters_inline(
            project,
            [("bad", "fail-here"), ("good", "succeed-here")],
        )
        name, expr, _ = result
        # The failing layer is skipped; the next one wins.
        assert name == "Good"
        assert expr == "succeed-here"

    def test_reapply_previous_filters_inline_empty_list_returns_clear(self):
        from filtermate_api.qgis_accessor import QGISFilterMateAccessor

        project = MagicMock()
        result = QGISFilterMateAccessor._reapply_previous_filters_inline(
            project, []
        )
        assert result == ("", "", True)

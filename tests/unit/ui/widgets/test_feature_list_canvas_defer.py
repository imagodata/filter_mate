# -*- coding: utf-8 -*-
"""
PERF 2026-09-14: a PostgreSQL feature-list population issued while the canvas
is rendering (project just opened) blocked the main thread for 17.7 s although
the same request takes 12 ms on an idle layer. The widget postpones it until
the canvas has refreshed, or CANVAS_DEFER_FALLBACK_MS at the latest. Methods
extracted with ast so the Qt widget module is never imported.
"""
import ast
import sys
import types
import weakref
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_MODULE = Path(__file__).resolve().parents[4] / "ui" / "widgets" / "custom_widgets.py"
_NAMES = ("_canvas_is_drawing", "_defer_populate_while_canvas_draws", "_orders_server_side",
          "_layer_id_or_none", "_cancel_deferred_populate")


def _methods(timer):
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    ns = {"__name__": "fm_test_feature_list_canvas_defer", "logger": MagicMock(), "weakref": weakref, "QTimer": timer}
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name in _NAMES:
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), ns)
    assert all(name in ns for name in _NAMES)
    return ns


class _Widget:
    CANVAS_DEFER_FALLBACK_MS = 15000
    CANVAS_DEFER_MAX_ROUNDS = 3
    _cached_layer_name = "troncon_de_route"


def _widget(provider, drawing, timer):
    ns = _methods(timer)
    widget = _Widget()
    widget.layer = MagicMock()
    widget.layer.providerType.return_value = provider
    widget._populate_features_sync = MagicMock()
    for name in _NAMES:
        setattr(widget, name, types.MethodType(ns[name], widget))
    canvas = sys.modules["qgis.utils"].iface.mapCanvas.return_value
    canvas.isDrawing.return_value = drawing
    canvas.mapCanvasRefreshed = MagicMock()
    return widget, canvas


@pytest.mark.unit
class TestDeferWhileCanvasDraws:

    def test_postgres_population_waits_for_the_canvas(self):
        timer = MagicMock()
        widget, canvas = _widget("postgres", True, timer)

        deferred = widget._defer_populate_while_canvas_draws('"cleabs"', True, False, None)

        assert deferred is True
        canvas.mapCanvasRefreshed.connect.assert_called_once()
        assert timer.singleShot.call_args.args[0] == 15000
        widget._populate_features_sync.assert_not_called()

        # the canvas refresh runs the population once, without deferring again
        run_deferred = canvas.mapCanvasRefreshed.connect.call_args.args[0]
        canvas.isDrawing.return_value = True  # still drawing (a second job)
        run_deferred()
        widget._populate_features_sync.assert_called_once_with(
            '"cleabs"', preserve_checked=True, force_full=False, search_text=None)
        canvas.mapCanvasRefreshed.disconnect.assert_called_once_with(run_deferred)
        assert widget._skip_canvas_defer is False

        # the fallback timer firing afterwards is a no-op
        timer.singleShot.call_args.args[1]()
        widget._populate_features_sync.assert_called_once()

    def test_second_request_while_armed_is_absorbed(self):
        timer = MagicMock()
        widget, canvas = _widget("postgres", True, timer)
        widget._defer_populate_while_canvas_draws("a", False, False, None)
        assert widget._defer_populate_while_canvas_draws("b", False, False, None) is True
        canvas.mapCanvasRefreshed.connect.assert_called_once()

    def test_idle_canvas_does_not_defer(self):
        widget, canvas = _widget("postgres", False, MagicMock())
        assert widget._defer_populate_while_canvas_draws("a", False, False, None) is False
        canvas.mapCanvasRefreshed.connect.assert_not_called()

    def test_other_providers_never_defer(self):
        widget, canvas = _widget("ogr", True, MagicMock())
        assert widget._defer_populate_while_canvas_draws("a", False, False, None) is False

    def test_deferred_run_is_forced_even_if_still_drawing(self):
        timer = MagicMock()
        widget, canvas = _widget("postgres", True, timer)
        widget._defer_populate_while_canvas_draws("a", False, False, None)
        widget._skip_canvas_defer = True
        assert widget._defer_populate_while_canvas_draws("a", False, False, None) is False

    def test_fallback_while_still_drawing_waits_more_rounds_then_runs(self):
        timer = MagicMock()
        widget, canvas = _widget("postgres", True, timer)
        widget._defer_populate_while_canvas_draws("a", False, False, None)

        for _ in range(3):  # three more rounds while the canvas keeps drawing
            timer.singleShot.call_args.args[1]()
            widget._populate_features_sync.assert_not_called()
        assert timer.singleShot.call_count == 4

        timer.singleShot.call_args.args[1]()  # rounds exhausted: run anyway
        widget._populate_features_sync.assert_called_once()

    def test_fallback_on_an_idle_canvas_runs_at_once(self):
        timer = MagicMock()
        widget, canvas = _widget("postgres", True, timer)
        widget._defer_populate_while_canvas_draws("a", False, False, None)
        canvas.isDrawing.return_value = False
        timer.singleShot.call_args.args[1]()
        widget._populate_features_sync.assert_called_once()


@pytest.mark.unit
class TestDeferredRequestFollowsTheLayer:
    """2026-10-17: the closure ran the first request's expression on whatever layer the widget showed then."""

    def test_the_latest_request_runs(self):
        timer = MagicMock()
        widget, canvas = _widget("postgres", True, timer)
        widget._defer_populate_while_canvas_draws('"a"', False, False, None)
        widget._defer_populate_while_canvas_draws('"b"', True, False, "rue")  # absorbed, but remembered
        canvas.mapCanvasRefreshed.connect.call_args.args[0]()
        widget._populate_features_sync.assert_called_once_with('"b"', preserve_checked=True, force_full=False,
                                                               search_text="rue")

    def test_a_layer_change_drops_the_waiting_population(self):
        timer = MagicMock()
        widget, canvas = _widget("postgres", True, timer)
        widget.layer.id.return_value = "roads"
        widget._defer_populate_while_canvas_draws('"cleabs"', False, False, None)
        widget._cancel_deferred_populate()  # setLayer with another layer
        widget.layer = MagicMock()
        widget.layer.id.return_value = "rivers"
        run_deferred = canvas.mapCanvasRefreshed.connect.call_args.args[0]
        run_deferred()
        widget._populate_features_sync.assert_not_called()
        canvas.mapCanvasRefreshed.disconnect.assert_called_with(run_deferred)  # no longer waits

    def test_a_layer_changed_without_cancel_is_not_populated_with_the_old_request(self):
        timer = MagicMock()
        widget, canvas = _widget("postgres", True, timer)
        widget.layer.id.return_value = "roads"
        widget._defer_populate_while_canvas_draws('"cleabs"', False, False, None)
        widget.layer = MagicMock()
        widget.layer.id.return_value = "rivers"
        canvas.mapCanvasRefreshed.connect.call_args.args[0]()
        widget._populate_features_sync.assert_not_called()

    def test_a_canceled_wait_does_not_run_with_the_next_one(self):
        timer = MagicMock()
        widget, canvas = _widget("postgres", True, timer)
        widget._defer_populate_while_canvas_draws('"a"', False, False, None)
        first = canvas.mapCanvasRefreshed.connect.call_args.args[0]
        widget._cancel_deferred_populate()
        widget._defer_populate_while_canvas_draws('"b"', False, False, None)  # armed again
        second = canvas.mapCanvasRefreshed.connect.call_args.args[0]
        first()  # the old wait: superseded
        widget._populate_features_sync.assert_not_called()
        second()
        widget._populate_features_sync.assert_called_once_with('"b"', preserve_checked=False, force_full=False,
                                                               search_text=None)

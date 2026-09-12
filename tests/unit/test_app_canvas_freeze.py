# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: the canvas is frozen while a filter task runs and thawed once
at the end (taskCompleted / taskTerminated / watchdog). The two methods are
extracted from filter_mate_app.py with ast, like the other app tests, so the
plugin module itself is never imported.
"""
import ast
import gc
import types
import weakref
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_APP = Path(__file__).resolve().parents[2] / "filter_mate_app.py"


def _extract(names, namespace):
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace


class _App:
    """Weak-referenceable stand-in for FilterMateApp."""


def _app():
    fake_iface = MagicMock()
    canvas = fake_iface.mapCanvas.return_value
    canvas.isFrozen.return_value = False
    canvas.freeze.side_effect = lambda flag: setattr(canvas.isFrozen, "return_value", flag)
    timer = MagicMock()
    namespace = _extract(
        ["_freeze_canvas_for_task", "_unfreeze_canvas_after_task"],
        {"iface": fake_iface, "QTimer": timer, "logger": MagicMock(), "weakref": weakref,
         "CANVAS_FREEZE_WATCHDOG_MS": 600000},
    )
    app = _App()
    app._freeze_canvas_for_task = types.MethodType(namespace["_freeze_canvas_for_task"], app)
    app._unfreeze_canvas_after_task = types.MethodType(namespace["_unfreeze_canvas_after_task"], app)
    return app, canvas, timer


@pytest.mark.unit
class TestCanvasFreezeDuringTask:

    def test_freeze_then_thaw_refreshes_once(self):
        app, canvas, timer = _app()

        token = app._freeze_canvas_for_task("filter")

        canvas.stopRendering.assert_called_once()
        canvas.freeze.assert_called_once_with(True)
        timer.singleShot.assert_called_once()
        assert timer.singleShot.call_args.args[0] == 600000

        app._unfreeze_canvas_after_task(token)
        app._unfreeze_canvas_after_task(token)  # taskCompleted and taskTerminated both fire at most once each

        assert canvas.freeze.call_args_list[-1].args == (False,)
        canvas.refresh.assert_called_once()

    def test_stale_token_does_not_thaw_a_newer_freeze(self):
        app, canvas, timer = _app()
        first = app._freeze_canvas_for_task("filter")
        second = app._freeze_canvas_for_task("filter")

        app._unfreeze_canvas_after_task(first)

        assert canvas.isFrozen() is True
        app._unfreeze_canvas_after_task(second)
        assert canvas.isFrozen() is False

    def test_already_thawed_canvas_is_not_refreshed_again(self):
        app, canvas, timer = _app()
        token = app._freeze_canvas_for_task("filter")
        canvas.freeze(False)  # apply_pending_subset_requests thawed it already

        app._unfreeze_canvas_after_task(token)

        canvas.refresh.assert_not_called()

    def test_watchdog_thaws_and_warns(self):
        app, canvas, timer = _app()
        token = app._freeze_canvas_for_task("filter")
        watchdog = timer.singleShot.call_args.args[1]

        watchdog()

        assert canvas.isFrozen() is False
        canvas.refresh.assert_called_once()
        app._unfreeze_canvas_after_task(token)
        canvas.refresh.assert_called_once()

    def test_failed_thaw_keeps_the_token_for_a_retry(self):
        app, canvas, timer = _app()
        token = app._freeze_canvas_for_task("filter")
        canvas.freeze.side_effect = [RuntimeError("wrapped C/C++ object has been deleted")]

        app._unfreeze_canvas_after_task(token)
        assert app._canvas_frozen_token == token

        canvas.freeze.side_effect = lambda flag: setattr(canvas.isFrozen, "return_value", flag)
        app._unfreeze_canvas_after_task(token)
        assert app._canvas_frozen_token is None
        canvas.refresh.assert_called_once()

    def test_watchdog_does_not_keep_the_app_alive(self):
        app, canvas, timer = _app()
        app._freeze_canvas_for_task("filter")
        watchdog = timer.singleShot.call_args.args[1]
        ref = weakref.ref(app)
        del app
        gc.collect()  # the bound methods stored on the stand-in form a cycle

        assert ref() is None
        watchdog()  # nothing to thaw any more, must not raise

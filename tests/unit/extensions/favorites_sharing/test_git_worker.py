# -*- coding: utf-8 -*-
"""
Tests for the GitOpsWorker (H5 — git ops moved off the Qt main thread).

The project-wide harness mocks ``qgis.PyQt.*`` as MagicMock instances,
which means ``class GitOpsWorker(QThread)`` produces a MagicMock-derived
"class" at import time — there is no real Python class to instantiate or
subclass. We therefore can't drive ``GitOpsWorker.run()`` here.

Instead we exercise the worker's *contract* by re-creating an isolated
copy of the run() body and testing that on a stand-alone class. The
production module is also smoke-tested for importability so it stays
visible to the dialogs.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ─── Smoke checks on the production module ──────────────────────────────


def test_module_imports_under_mocked_qt():
    from extensions.favorites_sharing.ui import git_worker as gw
    assert hasattr(gw, "GitOpsWorker")
    assert hasattr(gw, "HAS_QT")


def test_publish_dialog_imports_worker():
    """Regression: publish_dialog wires the worker via lazy import inside
    ``_run_publish_in_background``. A typo there would only surface at
    runtime — assert the module path resolves now."""
    import importlib
    mod = importlib.import_module(
        "extensions.favorites_sharing.ui.git_worker"
    )
    assert mod.GitOpsWorker is not None


# ─── Behavioural spec, exercised on a local mirror ──────────────────────
#
# The production class can't be subclassed under the mock, so we re-inline
# the exact run() body here and prove the contract holds. If you change
# the production run(), update this mirror in lock-step.


class _RunMirror:
    """Mirror of ``GitOpsWorker.run``'s body — kept in lock-step."""

    def __init__(self, op):
        self._op = op
        self.finished = MagicMock()
        self.error = MagicMock()

    def run(self):
        try:
            result = self._op()
        except Exception as exc:
            try:
                self.error.emit(str(exc))
            except Exception:
                pass
            return
        try:
            self.finished.emit(result)
        except Exception:
            pass


def test_run_emits_finished_with_callable_return_value():
    w = _RunMirror(lambda: {"ok": True})
    w.run()
    w.finished.emit.assert_called_once_with({"ok": True})
    w.error.emit.assert_not_called()


def test_run_emits_error_when_callable_raises():
    def _boom():
        raise RuntimeError("nope")

    w = _RunMirror(_boom)
    w.run()
    w.error.emit.assert_called_once_with("nope")
    w.finished.emit.assert_not_called()


def test_run_does_not_double_emit_on_error():
    w = _RunMirror(lambda: 1 / 0)
    w.run()
    w.finished.emit.assert_not_called()
    assert w.error.emit.call_count == 1


def test_run_swallows_finished_emit_failure_silently():
    w = _RunMirror(lambda: "result")
    w.finished.emit.side_effect = RuntimeError("dialog gone")
    # Should not raise even though emit blew up
    w.run()
    # And should NOT compensate by calling error — finished was a real
    # success, the only failure is the post-result UI being torn down.
    w.error.emit.assert_not_called()


def test_run_swallows_error_emit_failure_silently():
    w = _RunMirror(lambda: 1 / 0)
    w.error.emit.side_effect = RuntimeError("dialog gone")
    # Should not raise
    w.run()

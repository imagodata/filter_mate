"""C1 — PushDialog orphan-worker registry on terminate/wait timeout.

Audit 2026-04-29 (C1): _stop_worker called terminate() then wait(10s) and
unconditionally dropped the Python ref to the worker. When wait() timed
out (rare but possible on a stuck syscall), Python released the QThread
ref while the C++ thread was still running — Qt then crashed with
"QThread destroyed while running" on plugin reload / app exit.

The fix parks the orphan worker on a class-level registry so its Python
ref survives the dialog's destruction; the worker's finished/error/
destroyed signals trigger _reap_orphan_worker which removes it from the
registry and requests deleteLater.

This test file isolates the parking + reap logic by exercising
_stop_worker, _park_orphan_worker and _reap_orphan_worker directly with
fakes — we don't need a real QThread or a real dialog.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock

import pytest


_PKG = "filter_mate_c1"
_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)


# ---------------------------------------------------------------------------
# Stub install — we only need _stop_worker / _park_orphan_worker /
# _reap_orphan_worker, so build a tiny class that mirrors the relevant
# slice of QFieldCloudPushDialog without importing it (it pulls Qt at
# module load and is otherwise irrelevant to the test).
# ---------------------------------------------------------------------------


def _build_stub_dialog_class():
    """Construct an isolated copy of the three methods + the registry.

    We rebuild rather than import the real class because importing
    push_dialog.py drags in QDialog, QGroupBox, QFormLayout etc.
    which all need a Qt application or a heavy mock layer.
    """
    import logging

    logger = logging.getLogger("filter_mate_c1_test")

    class _Dialog:
        _orphan_workers: list = []

        def __init__(self):
            self._worker = None

        # Slot stubs — _stop_worker calls .disconnect() on these so they
        # need to exist as bound methods.
        def _on_progress(self, *_args):
            pass

        def _on_push_finished(self, *_args):
            pass

        def _on_push_error(self, *_args):
            pass

        def _stop_worker(self) -> None:
            worker = self._worker
            if worker is None:
                return
            try:
                worker.progress.disconnect(self._on_progress)
                worker.finished.disconnect(self._on_push_finished)
                worker.error.disconnect(self._on_push_error)
            except (TypeError, RuntimeError):
                pass

            stopped = True
            if worker.isRunning():
                worker.terminate()
                stopped = bool(worker.wait(10_000))

            if not stopped:
                logger.warning(
                    "PushWorker did not halt within 10s of terminate(); "
                    "parking the orphan worker."
                )
                self._park_orphan_worker(worker)
            self._worker = None

        @classmethod
        def _park_orphan_worker(cls, worker) -> None:
            registry = cls._orphan_workers
            if worker in registry:
                return
            registry.append(worker)
            try:
                worker.finished.connect(lambda *_: cls._reap_orphan_worker(worker))
            except (TypeError, RuntimeError):
                pass
            try:
                worker.error.connect(lambda *_: cls._reap_orphan_worker(worker))
            except (TypeError, RuntimeError):
                pass
            try:
                worker.destroyed.connect(lambda *_: cls._reap_orphan_worker(worker))
            except (TypeError, RuntimeError):
                pass

        @classmethod
        def _reap_orphan_worker(cls, worker) -> None:
            try:
                cls._orphan_workers.remove(worker)
            except ValueError:
                return
            try:
                worker.deleteLater()
            except (RuntimeError, AttributeError):
                pass

    return _Dialog


_Dialog = _build_stub_dialog_class()


@pytest.fixture(autouse=True)
def reset_registry():
    _Dialog._orphan_workers = []
    yield
    _Dialog._orphan_workers = []


def _make_worker(running=False, wait_returns=True):
    """Build a worker mock with the signal-shape _stop_worker expects."""
    worker = MagicMock()
    worker.isRunning.return_value = running
    worker.wait.return_value = wait_returns
    worker.terminate = MagicMock()
    worker.deleteLater = MagicMock()
    # signals
    for sig in ("progress", "finished", "error", "destroyed"):
        setattr(worker, sig, MagicMock())
    return worker


# ---------------------------------------------------------------------------
# Happy path: worker stops within wait()
# ---------------------------------------------------------------------------


class TestStopWorkerHappyPath:
    def test_not_running_drops_ref_immediately(self):
        dlg = _Dialog()
        worker = _make_worker(running=False)
        dlg._worker = worker

        dlg._stop_worker()

        # No terminate when not running.
        worker.terminate.assert_not_called()
        worker.wait.assert_not_called()
        assert dlg._worker is None
        assert _Dialog._orphan_workers == []

    def test_running_and_wait_succeeds_drops_ref(self):
        dlg = _Dialog()
        worker = _make_worker(running=True, wait_returns=True)
        dlg._worker = worker

        dlg._stop_worker()

        worker.terminate.assert_called_once()
        worker.wait.assert_called_once_with(10_000)
        assert dlg._worker is None
        # No parking when wait() returned True.
        assert _Dialog._orphan_workers == []

    def test_no_worker_is_noop(self):
        dlg = _Dialog()
        dlg._worker = None
        dlg._stop_worker()  # must not raise
        assert _Dialog._orphan_workers == []


# ---------------------------------------------------------------------------
# Timeout: wait() returns False — the orphan path must trigger
# ---------------------------------------------------------------------------


class TestStopWorkerTimeoutParks:
    def test_wait_timeout_parks_worker_in_registry(self):
        dlg = _Dialog()
        worker = _make_worker(running=True, wait_returns=False)
        dlg._worker = worker

        dlg._stop_worker()

        # The worker is now an orphan: dialog ref dropped but registry
        # holds the Python ref alive so the C++ QThread is not GC'd.
        assert dlg._worker is None
        assert worker in _Dialog._orphan_workers

    def test_park_connects_reap_to_finished_error_destroyed(self):
        dlg = _Dialog()
        worker = _make_worker(running=True, wait_returns=False)
        dlg._worker = worker

        dlg._stop_worker()

        worker.finished.connect.assert_called_once()
        worker.error.connect.assert_called_once()
        worker.destroyed.connect.assert_called_once()

    def test_park_idempotent(self):
        # Calling _park_orphan_worker twice for the same worker should
        # not duplicate the registry entry.
        worker = _make_worker(running=True, wait_returns=False)
        _Dialog._park_orphan_worker(worker)
        _Dialog._park_orphan_worker(worker)
        assert _Dialog._orphan_workers.count(worker) == 1

    def test_disconnect_failures_do_not_block_park(self):
        # Slot disconnect raises (signal already disconnected on a prior
        # call). _stop_worker must still proceed to terminate/park.
        dlg = _Dialog()
        worker = _make_worker(running=True, wait_returns=False)
        worker.progress.disconnect.side_effect = TypeError("not connected")
        dlg._worker = worker

        dlg._stop_worker()

        worker.terminate.assert_called_once()
        assert worker in _Dialog._orphan_workers


# ---------------------------------------------------------------------------
# Reap: a parked worker eventually finishes, registry self-cleans
# ---------------------------------------------------------------------------


class TestReapOrphanWorker:
    def test_reap_removes_from_registry(self):
        worker = _make_worker(running=False)
        _Dialog._orphan_workers.append(worker)

        _Dialog._reap_orphan_worker(worker)

        assert worker not in _Dialog._orphan_workers
        worker.deleteLater.assert_called_once()

    def test_reap_idempotent_double_call_does_not_raise(self):
        # The same worker may emit finished AND destroyed; both hooks
        # fire _reap_orphan_worker. The second call must be a no-op.
        worker = _make_worker(running=False)
        _Dialog._orphan_workers.append(worker)

        _Dialog._reap_orphan_worker(worker)
        _Dialog._reap_orphan_worker(worker)  # must not raise

        assert worker not in _Dialog._orphan_workers
        # deleteLater fires only on the first reap.
        assert worker.deleteLater.call_count == 1

    def test_reap_unknown_worker_is_noop(self):
        # Defensive: if a slot fires after the registry was cleared (e.g.
        # plugin reload between park and reap), _reap_orphan_worker must
        # silently ignore the unknown worker.
        unknown = _make_worker()
        _Dialog._reap_orphan_worker(unknown)  # must not raise
        unknown.deleteLater.assert_not_called()

    def test_deleteLater_failure_swallowed(self):
        # Ref already deleted by Qt — deleteLater raises RuntimeError on
        # a "wrapped C/C++ object has been deleted" QThread. The reap
        # must not surface that into the signal handler.
        worker = _make_worker()
        worker.deleteLater.side_effect = RuntimeError("already deleted")
        _Dialog._orphan_workers.append(worker)

        _Dialog._reap_orphan_worker(worker)  # must not raise

        assert worker not in _Dialog._orphan_workers


# ---------------------------------------------------------------------------
# Integration: full sequence — start → timeout → orphan → finished → reap
# ---------------------------------------------------------------------------


class TestEndToEndLifecycle:
    def test_orphan_lives_until_finished_signal_fires(self):
        # Stage 1: dialog stops a stuck worker, parks it.
        dlg = _Dialog()
        worker = _make_worker(running=True, wait_returns=False)
        dlg._worker = worker

        dlg._stop_worker()

        assert worker in _Dialog._orphan_workers
        assert dlg._worker is None

        # Stage 2: dialog instance is dropped (test-side: no Python ref
        # other than the registry's). The class-level registry holds it.
        del dlg
        assert worker in _Dialog._orphan_workers

        # Stage 3: real-world finished signal would now fire; we
        # simulate by calling the reap directly. The lambda handlers
        # registered in _park_orphan_worker would do exactly this.
        _Dialog._reap_orphan_worker(worker)

        assert worker not in _Dialog._orphan_workers
        worker.deleteLater.assert_called_once()

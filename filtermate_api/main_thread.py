"""Safe Qt main-thread dispatch for FastAPI worker threads — P0-B.

QGIS layer mutations (``setSubsetString`` and the ``PublicAPI.apply_filter``
chain it sits behind) are **not thread-safe** outside the Qt main thread.
``uvicorn`` runs FastAPI request handlers in a worker pool, so calling
``self._public_api.apply_filter(...)`` directly from
:class:`QGISFilterMateAccessor.apply_filter` (the deep-audit 2026-04-29
P0-B finding) lets the worker mutate Qt-owned state from the wrong
thread. Symptoms range from silent state corruption to a hard QGIS
crash under concurrent load.

This module exposes :func:`run_on_main_thread` which:

* runs the call inline when invoked **from** the main thread (cheap
  fast path, e.g. when the API is driven from a unit test that already
  owns the QGIS event loop);
* otherwise marshals the call via ``QMetaObject.invokeMethod`` to a
  hidden ``QObject`` living on the main thread, and waits via a
  :class:`threading.Event` for the result. Exceptions raised on the
  main thread re-raise on the caller's thread.

When QGIS / Qt is not importable (the headless test harness), the
function runs the callable inline and emits a one-time warning so the
lack of true main-thread enforcement is not invisible.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger("filtermate_api.main_thread")

_DEFAULT_TIMEOUT_SECONDS = 30.0

# One-time guard so the headless-mode warning doesn't spam the log when
# the API is exercised in tests.
_HEADLESS_WARNED = False

try:  # pragma: no cover - exercised in QGIS, not in headless tests
    from qgis.PyQt.QtCore import (
        QCoreApplication,
        QMetaObject,
        QObject,
        Qt,
        QThread,
        Q_ARG,
        pyqtSlot,
    )

    # Headless test conftests install MagicMock objects in place of
    # ``qgis.PyQt.QtCore.*`` — the import succeeds but the symbols are
    # not real classes. Detect that and treat as headless so the
    # ``BlockingQueuedConnection`` path doesn't deadlock on a fake
    # ``QMetaObject.invokeMethod``.
    _HAS_QT = isinstance(QCoreApplication, type) and isinstance(QObject, type)
except Exception:  # pragma: no cover - headless path (no qgis at all)
    _HAS_QT = False


if _HAS_QT:  # pragma: no cover - QGIS-only

    class _MainThreadDispatcher(QObject):
        """QObject living on the main thread; runs invoked callables."""

        @pyqtSlot(object)
        def _run(self, fn: Callable[[], None]) -> None:
            # fn is a zero-arg wrapper (built in run_on_main_thread)
            # that captures the original args/kwargs and stores result
            # / exception in shared holders.
            fn()

    _dispatcher: Optional["_MainThreadDispatcher"] = None
    _dispatcher_lock = threading.Lock()

    def _get_dispatcher() -> "_MainThreadDispatcher":
        global _dispatcher
        with _dispatcher_lock:
            if _dispatcher is None:
                app = QCoreApplication.instance()
                if app is None:
                    raise RuntimeError(
                        "No QCoreApplication — cannot dispatch to main thread"
                    )
                _dispatcher = _MainThreadDispatcher()
                _dispatcher.moveToThread(app.thread())
            return _dispatcher


def run_on_main_thread(
    fn: Callable[..., Any],
    *args: Any,
    timeout: float = _DEFAULT_TIMEOUT_SECONDS,
    **kwargs: Any,
) -> Any:
    """Run ``fn(*args, **kwargs)`` on the Qt main thread.

    When already on the main thread the call runs inline (no Qt event
    queue trip). Otherwise the call is marshalled to a QObject living
    on the main thread and the worker blocks until completion or
    ``timeout`` seconds elapse — whichever comes first.

    Re-raises any exception raised by ``fn`` so the caller sees the
    original traceback (just on its own thread).

    Headless harness: when QGIS is not importable, runs inline and
    emits a one-time warning so production-vs-test divergence is
    visible in logs.
    """
    global _HEADLESS_WARNED

    if not _HAS_QT:
        if not _HEADLESS_WARNED:
            logger.warning(
                "filtermate_api.main_thread: QGIS/Qt not importable — "
                "running callable inline. Production deployments must "
                "run inside QGIS so the dispatcher can enforce main-thread."
            )
            _HEADLESS_WARNED = True
        return fn(*args, **kwargs)

    # QGIS path — exercised at runtime, not under unit tests.
    dispatcher = _get_dispatcher()  # pragma: no cover
    if QThread.currentThread() is dispatcher.thread():  # pragma: no cover
        return fn(*args, **kwargs)

    result_holder: list = []  # pragma: no cover
    error_holder: list = []  # pragma: no cover
    done = threading.Event()  # pragma: no cover

    def _wrapper() -> None:  # pragma: no cover
        try:
            result_holder.append(fn(*args, **kwargs))
        except Exception as exc:  # noqa: BLE001 - re-raised below
            error_holder.append(exc)
        finally:
            done.set()

    QMetaObject.invokeMethod(  # pragma: no cover
        dispatcher, "_run", Qt.QueuedConnection, Q_ARG(object, _wrapper)
    )
    if not done.wait(timeout=timeout):  # pragma: no cover
        raise TimeoutError(
            f"main_thread.run_on_main_thread: invocation timed out after "
            f"{timeout:.0f}s — main thread may be blocked"
        )
    if error_holder:  # pragma: no cover
        raise error_holder[0]
    return result_holder[0] if result_holder else None  # pragma: no cover


def reset_for_tests() -> None:
    """Reset module state — used by tests that monkeypatch ``_HAS_QT``."""
    global _HEADLESS_WARNED
    _HEADLESS_WARNED = False

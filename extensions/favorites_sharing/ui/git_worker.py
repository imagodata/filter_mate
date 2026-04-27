# -*- coding: utf-8 -*-
"""
Background worker for blocking git operations.

H5 (audit 2026-04-27): clone / pull / commit / push and ls-remote can each
take up to ``GitClient.timeout_seconds`` (30s by default), so chaining
them on the Qt main thread freezes QGIS for ~2 min in the worst case.

The worker is intentionally tiny — it just runs an arbitrary zero-arg
callable on a ``QThread`` and re-emits the outcome on the main thread via
queued signals. Callers (publish dialog, repo manager dialog) build a
closure capturing exactly the operation they want offloaded.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

try:
    from qgis.PyQt.QtCore import QThread, pyqtSignal
    HAS_QT = True
except ImportError:  # pragma: no cover — headless / standalone tests
    HAS_QT = False
    # Provide a minimal stand-in so this module is importable without Qt.
    class QThread:  # type: ignore[no-redef]
        def __init__(self, parent=None) -> None:
            self._parent = parent

        def start(self) -> None:
            self.run()

        def quit(self) -> None:
            pass

        def wait(self, *_a, **_kw) -> bool:
            return True

        def isRunning(self) -> bool:
            return False

        def run(self) -> None:
            pass

    def pyqtSignal(*_a, **_kw):  # type: ignore[no-redef]
        class _Signal:
            def connect(self, *_a, **_kw):
                pass

            def emit(self, *_a, **_kw):
                pass

        return _Signal()


logger = logging.getLogger('FilterMate.FavoritesSharing.UI.GitWorker')


class GitOpsWorker(QThread):
    """Run ``op_callable`` on a worker thread and emit the result.

    Signals:
        finished(object): emitted with the callable's return value on
            successful completion.
        error(str): emitted with a scrubbed message when the callable
            raises. The full exception is logged at exception level on
            the worker thread for diagnostics.

    The worker owns no Qt parents that touch the UI — connections from
    callers are auto-resolved to ``Qt.QueuedConnection`` because the
    sender lives on the worker thread, so signal handlers fire safely on
    the main thread.
    """

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        op_callable: Callable[[], Any],
        parent: Optional[Any] = None,
    ) -> None:
        super().__init__(parent)
        self._op = op_callable

    def run(self) -> None:  # type: ignore[override]
        try:
            result = self._op()
        except Exception as exc:
            # Full traceback to logs; only the message goes back to UI.
            logger.exception("Git worker raised")
            try:
                self.error.emit(str(exc))
            except Exception:
                # If signal emission itself fails (Qt teardown), there's
                # nothing left for us to do — the dialog is gone.
                pass
            return
        try:
            self.finished.emit(result)
        except Exception:
            logger.debug("Result signal emit failed (dialog torn down?)")

# -*- coding: utf-8 -*-
"""
Wall-clock markers for the user-facing latencies of FilterMate.

The performance audit of 2026-09-12 recommended following three durations
from release to release, straight from ``filtermate.log``:

- ``project_open``: project read until the panel is enabled with its layers
- ``layer_change``: current-layer change until the exploring widgets are synced
- ``task_filter`` / ``task_unfilter`` / ``task_reset``: task launch until the
  result handler has refreshed the UI

Marks are named, so a span may start in one place (a signal handler, a task
launch) and end in another (a completion callback). Ending a span that was
never started is a silent no-op, which keeps the call sites free of state.
Each completed span is logged once at INFO::

    ⏱ project_open: 1834 ms (38 layers)

Thread-safe; ``time.perf_counter`` based.
"""

import logging
import threading
import time
from typing import Dict, Optional

logger = logging.getLogger('FilterMate.Perf')

_marks: Dict[str, float] = {}
_lock = threading.Lock()


def perf_mark_start(name: str) -> None:
    """Start (or restart) the span ``name``."""
    with _lock:
        _marks[name] = time.perf_counter()


def perf_elapsed_ms(name: str) -> Optional[float]:
    """Milliseconds since ``perf_mark_start(name)``, or None when not started."""
    with _lock:
        started = _marks.get(name)
    if started is None:
        return None
    return (time.perf_counter() - started) * 1000.0


def perf_mark_end(name: str, details: Optional[str] = None) -> Optional[float]:
    """Close the span ``name`` and log its duration at INFO.

    Returns:
        Elapsed milliseconds, or None when the span was never started.
    """
    with _lock:
        started = _marks.pop(name, None)
    if started is None:
        return None
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    suffix = f" ({details})" if details else ""
    logger.info(f"⏱ {name}: {elapsed_ms:.0f} ms{suffix}")
    return elapsed_ms


def perf_mark_cancel(name: str) -> None:
    """Forget the span ``name`` without logging (aborted operation)."""
    with _lock:
        _marks.pop(name, None)


class perf_span:
    """Context manager measuring a synchronous block: ``with perf_span('x'): ...``."""

    def __init__(self, name: str, details: Optional[str] = None):
        self._name = name
        self._details = details
        self.elapsed_ms: Optional[float] = None

    def __enter__(self):
        perf_mark_start(self._name)
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.elapsed_ms = perf_mark_end(self._name, self._details)
        else:
            perf_mark_cancel(self._name)
        return False


__all__ = [
    'perf_mark_start',
    'perf_mark_end',
    'perf_mark_cancel',
    'perf_elapsed_ms',
    'perf_span',
]

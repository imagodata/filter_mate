# -*- coding: utf-8 -*-
"""The Python stack of every thread written in the log folder when a FilterMate task lasts far too long.

2026-11-22: QGIS froze twice after the agent added an elevation raster; the log said where the task began and
nothing more, and QGIS had to be killed. One thread watches for the whole session, started with the plugin: noting a
task (``begin`` / ``end``) starts no thread and waits for none, so the watch itself cannot freeze anything at the
moment a task starts (a thread started then could wait behind the very lock suspected, 2026-11-22 review). Every
``POLL_SECONDS`` it looks at the tasks noted; one that lasts more than ``STALL_SECONDS`` gets the stacks of every
thread written once (``faulthandler.dump_traceback``). Python stacks only: a thread held in native code shows its last
Python line, and the watch needs the GIL, so a main thread that holds it while blocked in C++ leaves it silent.
"""
from __future__ import annotations

import faulthandler
import logging
import os
import threading
import time
from typing import Dict, List, Optional

logger = logging.getLogger('FilterMate.StallWatch')

STALL_SECONDS = 60.0  # an add_layers of a whole project of PostGIS layers stays far under it
POLL_SECONDS = 5.0
FILE_NAME = 'stall_stacks.log'
MAX_BYTES = 1024 * 1024  # started again beyond, at the first stall of a session

_lock = threading.Lock()
_tasks: Dict[int, List] = {}  # token: [label, start (monotonic), written]
_next = [0]
_watcher: List[Optional[threading.Thread]] = [None]
_stop = threading.Event()


def _log_dir() -> str:
    """The folder of filtermate.log (``FILTERMATE_LOG_DIR`` when this module is loaded alone, by the tests)."""
    try:
        from ..logging import _LOG_DIR
        return _LOG_DIR
    except ImportError:
        return os.environ.get('FILTERMATE_LOG_DIR') or os.path.dirname(os.path.abspath(__file__))


def path() -> str:
    return os.path.join(_log_dir(), FILE_NAME)


def start() -> None:
    """Start the watching thread (plugin load): once, at a quiet moment, never when a task starts."""
    with _lock:
        if _watcher[0] is not None and _watcher[0].is_alive():
            return
        _stop.clear()
        watcher = threading.Thread(target=_watch, name='FilterMate stall watch', daemon=True)
        watcher.start()
        _watcher[0] = watcher


def begin(label: str) -> Optional[int]:
    """Note a task that starts now; the token to give to ``end``. Starts no thread, waits for nothing."""
    with _lock:
        _next[0] += 1
        _tasks[_next[0]] = [label, time.monotonic(), False]
        return _next[0]


def end(token: Optional[int]) -> None:
    """The task of ``token`` ended (finished, failed or canceled); an unknown token or None is ignored."""
    if token is None:
        return
    with _lock:
        entry = _tasks.pop(token, None)
    if entry is not None and entry[2]:
        logger.warning(f"'{entry[0]}' lasted {time.monotonic() - entry[1]:.0f} s: the stacks of every thread "
                       f"are in {path()}")


def shutdown() -> None:
    """Plugin unload: the watching thread ends at its next look, the tasks noted are forgotten."""
    _stop.set()
    with _lock:
        _tasks.clear()
        _watcher[0] = None


def _stalled() -> List[List]:
    """The tasks that just passed ``STALL_SECONDS``, marked as written."""
    now = time.monotonic()
    found = []
    with _lock:
        for entry in _tasks.values():
            if not entry[2] and now - entry[1] > STALL_SECONDS:
                entry[2] = True
                found.append(entry)
    return found


def write_stacks(labels: List[str]) -> None:
    """The stacks of every thread, after a line that says which tasks and when, in ``FILE_NAME``."""
    target = path()
    try:
        too_large = os.path.getsize(target) > MAX_BYTES
    except OSError:
        too_large = False
    with (open(target, 'wb') if too_large else open(target, 'ab')) as stream:
        stream.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')}: {', '.join(labels)} running for more than "
                     f"{STALL_SECONDS:.0f} s\n".encode('utf-8'))
        stream.flush()
        faulthandler.dump_traceback(stream, all_threads=True)


def _watch() -> None:
    while not _stop.wait(POLL_SECONDS):
        try:
            stalled = _stalled()
            if stalled:
                write_stacks([entry[0] for entry in stalled])
        except Exception:  # noqa: BLE001 - a diagnostic: it must never take anything down
            logger.debug("stall watch: stacks not written", exc_info=True)

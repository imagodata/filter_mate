# -*- coding: utf-8 -*-
"""
Folder of derived files produced by cross filters.

Clipped VRT and clipped point clouds live in
``<QGIS profile>/filtermate/cache/<session>/`` (or under
``APP.OPTIONS.CROSS_FILTER.cache_dir`` when set, or under a per-user folder of
the system temp folder when neither can be written). The session folder is
removed when the plugin unloads, once every layer has been put back on its
original source; the cache is then closed.

A live session holds an OS lock on its ``.session.lock`` file, which also
names its host and process, so another QGIS instance never removes it; the
folders of crashed sessions of this computer are not locked and are removed
by the next session. A folder without that file was not made by FilterMate
and is never removed. Files that no layer and no undo step refer to any more
are removed by :func:`collect_garbage`, except the files a running task is
still writing (:func:`new_path` until :func:`settle`).
"""
import errno
import logging
import os
import re
import shutil
import socket
import stat
import tempfile
import threading
import time
import uuid
from typing import Dict, Iterable, Optional, Tuple

logger = logging.getLogger(__name__)

LOCK_NAME = '.session.lock'
_SESSION_NAME = re.compile(r'session_[0-9a-f]{10}$')
# A folder unlocked for less than this may be a session being created.
_UNLOCKED_GRACE_SECONDS = 60.0
# Folders whose liveness cannot be told (another computer, file systems
# without locks) are removed after this age.
_UNKNOWN_MAX_AGE_HOURS = 24.0
_LOCK_ATTEMPTS = 20
# Lock errors meaning "another process holds it"; any other error means the
# file system cannot lock (NFS without lockd, some SMB shares).
_HELD_ERRNOS = {errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES, getattr(errno, 'EDEADLK', -1),
                getattr(errno, 'EDEADLOCK', -1)}

_lock = threading.Lock()
_session_dir: Optional[str] = None
_session_lock_handle = None
_override_root: Optional[str] = None
_fallback_root: Optional[str] = None
_own_temp_folder: Optional[str] = None  # tempfile.mkdtemp folder of the fallback root
_closed = False
_in_flight: set = set()


def _config_value(key: str, default):
    try:
        from ....config.config import ENV_VARS, _get_option_value
        section = ENV_VARS.get('CONFIG_DATA', {}).get('APP', {}).get('OPTIONS', {}).get('CROSS_FILTER', {})
        return _get_option_value(section.get(key), default)
    except Exception:
        return default


def set_cache_root(path: Optional[str]) -> None:
    """Force the cache root (tests and scenario scripts); None restores the default.

    The current session, if any, is removed first and the cache reopened.
    """
    global _override_root, _fallback_root, _closed
    purge_session()
    with _lock:
        _override_root = path
        _fallback_root = None
        _closed = False
        _in_flight.clear()


def cache_root() -> str:
    """Root folder of the cache (not session specific)."""
    if _fallback_root:
        return _fallback_root
    return _preferred_root()


def _preferred_root() -> str:
    if _override_root:
        return _override_root
    configured = _config_value('cache_dir', '') or ''
    if configured:
        return configured
    try:
        from qgis.core import QgsApplication
        base = QgsApplication.qgisSettingsDirPath()
    except Exception:
        base = os.path.expanduser('~')
    return os.path.join(base, 'filtermate', 'cache')


def temp_root() -> str:
    """Per-user cache root in the system temp folder, used when the preferred one cannot be written."""
    try:
        import getpass
        user = getpass.getuser()
    except Exception:
        user = str(getattr(os, 'getuid', lambda: 'user')())
    user = "".join(c if c.isascii() and c.isalnum() else "_" for c in user) or "user"
    return os.path.join(tempfile.gettempdir(), f'filtermate-{user}', 'cache')


def _private_temp_root() -> str:
    """:func:`temp_root` when its folder belongs to this user alone, else a new private folder.

    That folder has a predictable name in a folder every user can write to:
    one made by another user, or a link, is never used (the derived files
    written there could be read or replaced, a link could send them anywhere).
    """
    global _own_temp_folder
    root = temp_root()
    folder = os.path.dirname(root)
    try:
        os.makedirs(folder, mode=0o700, exist_ok=True)
        if _owned_privately(folder):
            return root
    except OSError:
        pass
    _own_temp_folder = tempfile.mkdtemp(prefix='filtermate-')  # removed with the session
    return os.path.join(_own_temp_folder, 'cache')


def _owned_privately(folder: str) -> bool:
    info = os.lstat(folder)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        return False
    # A Windows junction is no link for lstat; realpath resolves it.
    resolved = os.path.join(os.path.realpath(os.path.dirname(folder)), os.path.basename(folder))
    if os.path.normcase(os.path.realpath(folder)) != os.path.normcase(resolved):
        return False
    if hasattr(os, 'getuid'):  # POSIX: the system temp folder is shared by every user
        if info.st_uid != os.getuid():
            return False
        if info.st_mode & 0o077:
            os.chmod(folder, 0o700)
    return True


def is_closed() -> bool:
    """True once the plugin unloaded: nothing may be written or applied any more."""
    return _closed


# --- session lock -------------------------------------------------------------

def _try_lock(handle) -> Optional[bool]:
    """Take a non blocking exclusive lock on ``handle``.

    Returns:
        True when taken, False when another holder has it, None when the
        file system cannot lock.
    """
    try:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as exc:
        return False if exc.errno in _HELD_ERRNOS else None


def _unlock(handle) -> None:
    try:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


def _release_session_lock() -> None:
    global _session_lock_handle
    handle, _session_lock_handle = _session_lock_handle, None
    if handle is not None:
        _unlock(handle)
        try:
            handle.close()
        except OSError:
            pass


def _create_session(root: str) -> str:
    """Create a locked session folder under ``root`` (raises OSError when not writable)."""
    global _session_lock_handle
    folder = os.path.join(root, f"session_{uuid.uuid4().hex[:10]}")
    os.makedirs(folder, exist_ok=True)
    try:
        handle = open(os.path.join(folder, LOCK_NAME), 'a+')
    except OSError:
        try:
            os.rmdir(folder)  # never a session folder without its lock file
        except OSError:
            pass
        raise
    locked = None
    for _attempt in range(_LOCK_ATTEMPTS):
        locked = _try_lock(handle)
        if locked is not False:
            break
        time.sleep(0.05)  # another instance is probing this brand new folder
    if locked:
        handle.seek(0)
        handle.truncate()
        handle.write(f"{socket.gethostname()}\n{os.getpid()}\n")
        handle.flush()
    else:
        logger.warning(f"[FM5] cache session {folder} could not be locked: other QGIS instances "
                       f"keep it for {_UNKNOWN_MAX_AGE_HOURS:.0f} h after it is left")
    _session_lock_handle = handle
    return folder


def session_state(folder: str) -> Tuple[Optional[bool], str]:
    """Liveness of a session folder.

    Returns:
        ``(locked, host)``: locked is True when a live session holds it,
        False when its lock is free, None when it cannot be told (no lock
        file, unreadable, file system without locks); host is the computer
        that created it ('' when unknown, read only when the lock is free).
    """
    lock_path = os.path.join(folder, LOCK_NAME)
    if not os.path.exists(lock_path):
        return None, ''
    try:
        with open(lock_path, 'r') as handle:
            locked = _try_lock(handle)
            if locked is not True:
                return (None if locked is None else True), ''
            try:
                handle.seek(0)
                host = handle.readline().strip()
            finally:
                _unlock(handle)
            return False, host
    except OSError:
        return None, ''


def session_dir() -> str:
    """Folder of the current session, created on first use (stale sessions are removed then).

    Raises:
        RuntimeError: The cache was closed (plugin unloaded).
        OSError: Neither the preferred root nor the temp root can be written.
    """
    global _session_dir, _fallback_root
    created = False
    with _lock:
        if _closed:
            raise RuntimeError("the FilterMate cache is closed (plugin unloaded)")
        if _session_dir is None:
            try:
                _session_dir = _create_session(cache_root())
            except OSError as exc:
                if _fallback_root:
                    raise
                _fallback_root = _private_temp_root()
                logger.warning(f"[FM5] the FilterMate cache cannot be written ({exc}): "
                               f"derived files go to {_fallback_root}")
                _session_dir = _create_session(_fallback_root)
            created = True
        os.makedirs(_session_dir, exist_ok=True)
        folder = _session_dir
    if created:
        cleanup_stale_sessions(keep=folder)
    return folder


def cleanup_stale_sessions(keep: str = '', root: Optional[str] = None) -> int:
    """Remove the session folders left by crashed or closed QGIS sessions.

    A folder of this computer whose lock is free belongs to no live session
    and is removed; a folder whose liveness cannot be told (another computer
    sharing the folder, file system without locks) is removed once it is
    older than a day. Locked folders are kept, and so are the folders without
    the lock file of FilterMate: ``cache_dir`` may be a folder holding other
    data, where a ``session_*`` folder is not necessarily FilterMate's (only
    an empty ``session_<10 hex>`` folder a day old goes: QGIS stopped before
    its lock file was written). The lock file is removed last, so a folder
    that cannot be emptied yet stays recognizable.

    Args:
        keep: Folder never removed (the current session).
        root: Cache root to clean; :func:`cache_root` by default.
    """
    root = root or cache_root()
    removed = 0
    try:
        entries = os.listdir(root)
    except OSError:
        return 0
    now = time.time()
    this_host = socket.gethostname()
    for name in entries:
        path = os.path.join(root, name)
        if not name.startswith('session_') or os.path.normcase(path) == os.path.normcase(keep or ''):
            continue
        try:
            if not os.path.isdir(path):
                continue
            age = now - os.path.getmtime(path)
            if not os.path.isfile(os.path.join(path, LOCK_NAME)):
                if _SESSION_NAME.match(name) and age >= _UNKNOWN_MAX_AGE_HOURS * 3600.0:
                    os.rmdir(path)  # fails, and keeps it, unless it is empty
                    removed += 1
                continue
            locked, host = session_state(path)
            if locked is True:
                continue
            if locked is False and host == this_host:
                if age < _UNLOCKED_GRACE_SECONDS:
                    continue
            elif age < _UNKNOWN_MAX_AGE_HOURS * 3600.0:
                continue
            if _empty_session(path) and _remove_emptied_session(path):
                removed += 1
        except OSError:
            continue
    if removed:
        logger.info(f"[FM5] {removed} stale cache session(s) removed from {root}")
    return removed


# --- files ----------------------------------------------------------------------

def folder_size(path: str) -> int:
    total = 0
    for base, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(base, name))
            except OSError:
                pass
    return total


def max_bytes() -> float:
    """``CROSS_FILTER.cache_max_gb`` in bytes; 0 means no limit."""
    try:
        return max(0.0, float(_config_value('cache_max_gb', 5)) * 1024 ** 3)
    except (TypeError, ValueError):
        return 0.0


def new_path(prefix: str, suffix: str) -> str:
    """Return a fresh file path in the session folder, protected until :func:`settle`.

    Args:
        prefix: Readable prefix (layer name), reduced to ASCII letters and
            digits so the file key survives any URI encoding.
        suffix: Extension including the dot (``.vrt``, ``.copc.laz``).
    """
    safe = "".join(c if (c.isascii() and c.isalnum()) or c in "-_" else "_" for c in (prefix or "layer"))[:40]
    path = os.path.join(session_dir(), f"{safe or 'layer'}_{uuid.uuid4().hex[:8]}{suffix}")
    with _lock:
        _in_flight.add(file_key(os.path.basename(path)))
    return path


def settle(paths: Iterable[str]) -> None:
    """The task that wrote ``paths`` is over: they follow the references from now on."""
    with _lock:
        for path in paths:
            if path:
                _in_flight.discard(file_key(os.path.basename(path)))


def file_key(name: str) -> str:
    """``<prefix>_<id>`` of a cache file name: a derived file and its side files share it.

    :func:`new_path` names have no dot before the extension, so ``a_1f2e.vrt``,
    ``a_1f2e.vrt.aux.xml`` and the ``a_1f2e.copc.laz`` index QGIS builds next
    to ``a_1f2e.laz`` all have the key ``a_1f2e``.
    """
    return name.split('.', 1)[0]


def in_session(source: str) -> bool:
    """True when ``source`` refers to a file of the current session (plain path or URI).

    Session folder names (``session_<hex>``) survive any URI encoding.
    """
    folder = _session_dir
    return bool(folder and source and os.path.basename(folder) in source)


def _entries(folder: str):
    with os.scandir(folder) as scan:
        return [entry for entry in scan if entry.name != LOCK_NAME]


def _kept_keys(entries, sources) -> set:
    """Keys of the entries in use: referenced anywhere in ``sources`` or still being written."""
    with _lock:
        kept = set(_in_flight)
    for entry in entries:
        key = file_key(entry.name)
        if key not in kept and any(key in source for source in sources):
            kept.add(key)
    return kept


def _is_kept(name: str, kept: set) -> bool:
    # A side file or folder named after a kept file (``<key>_tmp`` of an
    # indexing job) is kept with it.
    return any(name.startswith(key) for key in kept)


def entry_sizes() -> Dict[str, int]:
    """Bytes per top-level entry of the session folder (empty before the first derived file)."""
    folder = _session_dir
    if not folder or not os.path.isdir(folder):
        return {}
    sizes = {}
    for entry in _entries(folder):
        try:
            sizes[entry.name] = folder_size(entry.path) if entry.is_dir(follow_symlinks=False) else entry.stat().st_size
        except OSError:
            continue
    return sizes


def unused_entries(referenced: Iterable[str], names: Optional[Iterable[str]] = None) -> set:
    """Names of the session entries nothing refers to (see :func:`collect_garbage`).

    Args:
        referenced: Sources still in use.
        names: Only consider these entries (all of them by default).
    """
    folder = _session_dir
    if not folder or not os.path.isdir(folder):
        return set()
    sources = [str(source) for source in referenced if source]
    entries = _entries(folder)
    kept = _kept_keys(entries, sources)
    wanted = set(names) if names is not None else None
    return {entry.name for entry in entries
            if (wanted is None or entry.name in wanted) and not _is_kept(entry.name, kept)}


def collect_garbage(referenced: Iterable[str]) -> int:
    """Delete the entries of the session folder that nothing refers to any more.

    Args:
        referenced: Sources still in use (layers, undo / redo snapshots). A
            file is kept when its :func:`file_key` appears anywhere in one
            of them: plain paths, ``path|option`` URIs and virtual raster
            URIs embedding a path in their query (keys are ASCII letters,
            digits, ``-`` and ``_``, which URL encoding leaves as they are).
            A false match only keeps a file. Files of running tasks are kept.

    Returns:
        Number of entries removed.
    """
    folder = _session_dir
    if not folder or not os.path.isdir(folder):
        return 0
    removed = 0
    for name in sorted(unused_entries(referenced)):
        path = os.path.join(folder, name)
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            removed += 1
        except OSError as exc:
            logger.debug(f"[FM5] cache file {path} not removed: {exc}")
    if removed:
        logger.info(f"[FM5] {removed} unused derived file(s) removed from the cache")
    return removed


def _empty_session(folder: str) -> bool:
    """Remove everything in a session folder but its lock file; True when nothing else is left."""
    try:
        entries = _entries(folder)
    except OSError:
        return False
    for entry in entries:
        try:
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path)
            else:
                os.remove(entry.path)
        except OSError:
            pass  # still open (Windows): the folder and its lock file stay
    try:
        return not _entries(folder)
    except OSError:
        return False


def _remove_emptied_session(folder: str) -> bool:
    """Remove the lock file, then the folder, of a session :func:`_empty_session` emptied."""
    try:
        lock = os.path.join(folder, LOCK_NAME)
        if os.path.exists(lock):
            os.remove(lock)
        os.rmdir(folder)
        return True
    except OSError:
        return False


def purge_session() -> None:
    """Delete the session folder and close the cache (call once no layer uses its files).

    The lock file goes last: a file that cannot be removed yet (Windows:
    still open) leaves the folder with its lock file, released, which the
    next session of this computer removes.
    """
    global _session_dir, _closed, _fallback_root, _own_temp_folder
    with _lock:
        folder, _session_dir = _session_dir, None
        _closed = True
        _in_flight.clear()
    emptied = bool(folder) and os.path.isdir(folder) and _empty_session(folder)
    with _lock:
        _release_session_lock()
    if emptied and _remove_emptied_session(folder):
        logger.debug(f"[FM5] cache session removed: {folder}")
    if _own_temp_folder:
        try:
            os.rmdir(os.path.join(_own_temp_folder, 'cache'))
            os.rmdir(_own_temp_folder)
            _fallback_root = None
        except OSError:
            pass
        _own_temp_folder = None

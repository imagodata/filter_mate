# -*- coding: utf-8 -*-
"""
Folder of derived files produced by cross filters.

Clipped VRT and clipped point clouds live in
``<QGIS profile>/filtermate/cache/<session>/`` (or under
``APP.OPTIONS.CROSS_FILTER.cache_dir`` when set). The session folder is
removed when the plugin unloads, once every layer has been put back on its
original source.
"""
import logging
import os
import shutil
import threading
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_session_dir: Optional[str] = None
_override_root: Optional[str] = None


def _config_value(key: str, default):
    try:
        from ....config.config import ENV_VARS, _get_option_value
        section = ENV_VARS.get('CONFIG_DATA', {}).get('APP', {}).get('OPTIONS', {}).get('CROSS_FILTER', {})
        return _get_option_value(section.get(key), default)
    except Exception:
        return default


def set_cache_root(path: Optional[str]) -> None:
    """Force the cache root (tests and scenario scripts); None restores the default."""
    global _override_root, _session_dir
    with _lock:
        _override_root = path
        _session_dir = None


def cache_root() -> str:
    """Root folder of the cache (not session specific)."""
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


def session_dir() -> str:
    """Folder of the current session, created on first use."""
    global _session_dir
    with _lock:
        if _session_dir is None:
            _session_dir = os.path.join(cache_root(), f"session_{uuid.uuid4().hex[:10]}")
        os.makedirs(_session_dir, exist_ok=True)
        return _session_dir


def new_path(prefix: str, suffix: str) -> str:
    """Return a fresh file path in the session folder.

    Args:
        prefix: Readable prefix (layer name), sanitized.
        suffix: Extension including the dot (``.vrt``, ``.copc.laz``).
    """
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (prefix or "layer"))[:40] or "layer"
    return os.path.join(session_dir(), f"{safe}_{uuid.uuid4().hex[:8]}{suffix}")


def is_cache_path(path: str) -> bool:
    """True when ``path`` lives under the cache root."""
    if not path:
        return False
    try:
        root = os.path.normcase(os.path.abspath(cache_root()))
        target = os.path.normcase(os.path.abspath(path.split('|')[0]))
        return target.startswith(root)
    except Exception:
        return False


def purge_session() -> None:
    """Delete the session folder (call once no layer uses its files)."""
    global _session_dir
    with _lock:
        folder, _session_dir = _session_dir, None
    if folder and os.path.isdir(folder):
        shutil.rmtree(folder, ignore_errors=True)
        logger.debug(f"[FM5] cache session removed: {folder}")

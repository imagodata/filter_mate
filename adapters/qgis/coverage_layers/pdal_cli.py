# -*- coding: utf-8 -*-
"""
The ``pdal`` command line tool, shipped next to QGIS on Windows (OSGeo4W)
and usually on PATH on Linux and macOS.

Used for the point cloud operations QGIS does not expose to Python: clipping
straight to COPC, height above a DTM (``filters.hag_dem``).
"""
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CREATE_NO_WINDOW = 0x08000000


def _configured_path() -> str:
    try:
        from ....config.config import ENV_VARS, _get_option_value
        section = ENV_VARS.get('CONFIG_DATA', {}).get('APP', {}).get('OPTIONS', {}).get('CROSS_FILTER', {})
        return _get_option_value(section.get('pdal_path'), '') or ''
    except Exception:
        return ''


def _candidates() -> List[str]:
    names = ['pdal.exe', 'pdal'] if sys.platform.startswith('win') else ['pdal']
    folders: List[str] = []
    try:
        from qgis.core import QgsApplication
        prefix = QgsApplication.prefixPath()
        if isinstance(prefix, str) and prefix:
            folders += [
                os.path.normpath(os.path.join(prefix, '..', '..', 'bin')),  # OSGeo4W: apps/qgis -> bin
                os.path.normpath(os.path.join(prefix, 'bin')),
                os.path.normpath(prefix),  # macOS bundle: Contents/MacOS
            ]
    except Exception:
        pass
    found = []
    for folder in folders:
        for name in names:
            found.append(os.path.join(folder, name))
    return found


_cached: Optional[Tuple[str, str]] = None


def find_pdal() -> Optional[str]:
    """Return the pdal executable path, or None when it cannot be found."""
    global _cached
    configured = _configured_path()
    if _cached is not None and _cached[0] == configured:
        return _cached[1] or None
    path = ''
    if configured and os.path.isfile(configured):
        path = configured
    else:
        for candidate in _candidates():
            if os.path.isfile(candidate):
                path = candidate
                break
        if not path:
            path = shutil.which('pdal') or ''
    _cached = (configured, path)
    logger.debug(f"[FM5] pdal executable: {path or 'not found'}")
    return path or None


def reset_cache() -> None:
    global _cached
    _cached = None


def is_available() -> bool:
    return find_pdal() is not None


def reader_for(path: str) -> str:
    """PDAL reader type for a point cloud file."""
    lower = (path or '').lower()
    if lower.endswith('.copc.laz'):
        return 'readers.copc'
    if lower.endswith('ept.json'):
        return 'readers.ept'
    if lower.endswith(('.las', '.laz')):
        return 'readers.las'
    raise ValueError(f"no PDAL reader for {path}")


def run_pipeline(stages: list, timeout: float = 3600.0, is_canceled: Optional[Callable[[], bool]] = None) -> Tuple[bool, str]:
    """Run a PDAL pipeline given as a list of stages.

    Args:
        stages: Pipeline stages (dicts), first the reader, last the writer.
        timeout: Seconds before the process is killed.
        is_canceled: Polled every half second; True kills the process.

    Returns:
        ``(success, message)``.
    """
    exe = find_pdal()
    if not exe:
        return False, "pdal executable not found"
    fd, pipeline_path = tempfile.mkstemp(suffix='.json', prefix='fm5_pdal_')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump({"pipeline": stages}, handle)
        kwargs = {}
        if sys.platform.startswith('win'):
            kwargs['creationflags'] = _CREATE_NO_WINDOW
        process = subprocess.Popen(  # nosec B603 - fixed argv, no shell
            [exe, 'pipeline', pipeline_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs)
        elapsed = 0.0
        while True:
            try:
                out, err = process.communicate(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                elapsed += 0.5
                if (is_canceled is not None and is_canceled()) or elapsed > timeout:
                    process.kill()
                    process.communicate()
                    return False, "canceled" if elapsed <= timeout else "timeout"
        if process.returncode != 0:
            return False, (err or out or f"pdal exit code {process.returncode}").strip()[:2000]
        return True, ""
    finally:
        try:
            os.remove(pipeline_path)
        except OSError:
            pass

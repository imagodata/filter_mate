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
import re
import shutil
import subprocess  # nosec B404 - argument lists, never a shell
import sys
import tempfile
import threading
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
    except Exception as exc:
        logger.debug(f"[FM5] QGIS prefix folders not added to the PDAL search: {exc}")
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
    global _cached, _version_cached
    _cached = None
    _version_cached = None


def is_available() -> bool:
    return find_pdal() is not None


# writers.copc, used by every FilterMate pipeline, came with PDAL 2.4
# (Ubuntu 22.04 and the QGIS 3.22-3.34 Docker images ship 2.3).
COPC_MIN_VERSION = (2, 4)
# The version may be read on the main thread (first point cloud panel): warm_up() reads it earlier.
VERSION_TIMEOUT = 5.0

# (executable, version or None, error when it could not be run)
_version_cached: Optional[Tuple[str, Optional[Tuple[int, int, int]], str]] = None


def _subprocess_kwargs() -> dict:
    return {'creationflags': _CREATE_NO_WINDOW} if sys.platform.startswith('win') else {}


def _probe() -> Tuple[Optional[Tuple[int, int, int]], str]:
    """``(version, error)`` of the pdal executable, read once per executable."""
    global _version_cached
    exe = find_pdal()
    if not exe:
        return None, ''
    cached = _version_cached
    if cached is not None and cached[0] == exe:
        return cached[1], cached[2]
    parsed, error = None, ''
    try:
        out = subprocess.run(  # nosec B603 - fixed argv, no shell
            [exe, '--version'], capture_output=True, text=True, errors='replace', timeout=VERSION_TIMEOUT,
            **_subprocess_kwargs()).stdout or ''
        match = re.search(r'pdal\s+(\d+)\.(\d+)(?:\.(\d+))?', out, re.IGNORECASE)
        if match:
            parsed = (int(match.group(1)), int(match.group(2)), int(match.group(3) or 0))
    except (OSError, subprocess.SubprocessError) as exc:  # cannot be launched, or hangs
        error = str(exc) or type(exc).__name__
    _version_cached = (exe, parsed, error)
    logger.debug(f"[FM5] pdal version: {parsed} {error}")
    return parsed, error


def version() -> Optional[Tuple[int, int, int]]:
    """Version of the pdal executable, or None when there is none or it cannot be read."""
    return _probe()[0]


def warm_up() -> Optional[threading.Thread]:
    """Read the version in a background thread, so that the panel never waits for pdal; None when known."""
    exe = find_pdal()
    cached = _version_cached
    if not exe or (cached is not None and cached[0] == exe):
        return None
    thread = threading.Thread(target=_probe, name='filtermate-pdal-version', daemon=True)
    thread.start()
    return thread


def copc_unavailable_reason() -> str:
    """Why pdal cannot write COPC ('' when it can). A version that cannot be parsed is trusted."""
    if not is_available():
        return 'pdal not found'
    found, error = _probe()
    if error:
        return f"pdal could not be run: {error}"
    if found is not None and found[:2] < COPC_MIN_VERSION:
        return f"pdal {'.'.join(map(str, found))} has no writers.copc (PDAL 2.4 or later needed)"
    return ''


def supports_copc() -> bool:
    """True when the pdal executable can run FilterMate pipelines (they all end with writers.copc)."""
    return copc_unavailable_reason() == ''


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


# Authorities PROJ resolves by code; any other CRS (USER:..., none) is written as WKT.
_PDAL_AUTHORITIES = ('EPSG:', 'IGNF:', 'ESRI:')


def srs_for(crs) -> str:
    """``a_srs`` of a writer for a QgsCoordinateReferenceSystem."""
    authid = crs.authid() or ''
    if authid.upper().startswith(_PDAL_AUTHORITIES):
        return authid
    return crs.toWkt()


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
        process = subprocess.Popen(  # nosec B603 - fixed argv, no shell
            [exe, 'pipeline', pipeline_path],
            # PDAL writes UTF-8 (paths, messages): the Windows locale (cp1252) cannot decode it all.
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
            **_subprocess_kwargs())
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

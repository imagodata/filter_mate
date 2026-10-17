# -*- coding: utf-8 -*-
"""
Atomic JSON writes and corrupt-file backups for FilterMate's own files.

``open(path, 'w')`` truncates the target first: a crash, a full disk or a
serialization error in the middle leaves a half-written config.json, which
the next start then replaced with the default settings. Writing to a
neighbour temp file and swapping it in with ``os.replace`` leaves either the
old file or the new one.

Standard library only, so that it can be loaded from ``config/config.py``
(before the rest of the plugin) and tested on its own.
"""

import hashlib
import json
import os
import shutil
import tempfile
import time
from datetime import datetime
from typing import Any, Optional

# os.replace fails with PermissionError on Windows while another process (antivirus,
# a backup agent, QGIS reading the file) holds the target open for a moment
_REPLACE_ATTEMPTS = 5
_REPLACE_DELAY = 0.05


def atomic_json_write(path: str, data: Any, *, indent: int = 4, ensure_ascii: bool = False) -> None:
    """Write ``data`` to ``path`` as UTF-8 JSON via a temp file + ``os.replace``.

    A reader sees the previous file or the new one, never a truncation. If
    serialization or the swap fails, ``path`` is untouched and the temp file
    is removed.

    The temp file is created in the directory of ``path`` so that the rename
    stays on one filesystem (atomic on POSIX, and Windows refuses cross-device
    moves). The permissions of the file being replaced are kept; if ``path`` is
    a symbolic link, the file it points to is the one replaced (the link stays);
    a ``PermissionError`` from the final swap is retried a few times.

    Args:
        path: Target file.
        data: JSON-serializable object.
        indent: JSON indentation.
        ensure_ascii: Escape non-ASCII characters (False keeps them readable).

    Raises:
        OSError: The file could not be written or replaced.
        TypeError: ``data`` is not JSON-serializable.
        ValueError: ``data`` contains a circular reference.
    """
    if os.path.islink(path):
        path = os.path.realpath(path)  # replace the target of the link, not the link
    target_dir = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(target_dir, exist_ok=True)
    # Serialize first: a bad object must not even create the temp file
    text = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
    fd, tmp_path = tempfile.mkstemp(prefix=".fm_", suffix=".tmp", dir=target_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                # Some filesystems (network mounts) do not implement fsync
                pass
        _keep_permissions(path, tmp_path)
        _replace_with_retries(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _keep_permissions(old_path: str, new_path: str) -> None:
    """Give the new file the mode of the one it replaces (mkstemp makes it 0600)."""
    try:
        if os.path.exists(old_path):
            shutil.copymode(old_path, new_path)
        else:
            os.chmod(new_path, 0o644)
    except OSError:  # nosec B110 - permissions are best effort (some filesystems have none)
        pass


def _replace_with_retries(source: str, target: str) -> None:
    """``os.replace`` retried on PermissionError (a file briefly held open on Windows)."""
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == _REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(_REPLACE_DELAY)


def _digest(path: str) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            sha.update(block)
    return sha.hexdigest()


def backup_corrupt_file(path: str) -> Optional[str]:
    """Copy an unreadable file to ``<path>.corrupt-<YYYYmmdd-HHMMSS>``.

    Called before the settings fall back to the defaults, which the next save
    would otherwise write over the user's file for good. A file whose content
    is already kept in a ``.corrupt-*`` copy is not copied again (a start loop
    on the same broken file would fill the folder).

    Args:
        path: The file that could not be loaded.

    Returns:
        str: Path of the copy (the existing one when the content was already
        kept), or None when there is nothing to copy or the copy failed
        (never raises).
    """
    try:
        if not os.path.isfile(path):
            return None
        digest = _digest(path)
        folder = os.path.dirname(os.path.abspath(path))
        prefix = os.path.basename(path) + ".corrupt-"
        for name in sorted(os.listdir(folder)):
            candidate = os.path.join(folder, name)
            if name.startswith(prefix) and os.path.isfile(candidate) and _digest(candidate) == digest:
                return candidate
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = f"{path}.corrupt-{stamp}"
        counter = 1
        while os.path.exists(backup):
            counter += 1
            backup = f"{path}.corrupt-{stamp}-{counter}"
        shutil.copy2(path, backup)
        return backup
    except OSError:
        return None

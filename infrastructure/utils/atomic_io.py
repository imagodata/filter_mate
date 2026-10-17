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

import json
import os
import shutil
import tempfile
from datetime import datetime
from typing import Any, Optional


def atomic_json_write(path: str, data: Any, *, indent: int = 4, ensure_ascii: bool = False) -> None:
    """Write ``data`` to ``path`` as UTF-8 JSON via a temp file + ``os.replace``.

    A reader sees the previous file or the new one, never a truncation. If
    serialization or the swap fails, ``path`` is untouched and the temp file
    is removed.

    The temp file is created in the directory of ``path`` so that the rename
    stays on one filesystem (atomic on POSIX, and Windows refuses cross-device
    moves).

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
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def backup_corrupt_file(path: str) -> Optional[str]:
    """Copy an unreadable file to ``<path>.corrupt-<YYYYmmdd-HHMMSS>``.

    Called before the settings fall back to the defaults, which the next save
    would otherwise write over the user's file for good.

    Args:
        path: The file that could not be loaded.

    Returns:
        str: Path of the copy, or None when there is nothing to copy or the
        copy failed (never raises).
    """
    try:
        if not os.path.isfile(path):
            return None
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

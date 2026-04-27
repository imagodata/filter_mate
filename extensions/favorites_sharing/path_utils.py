# -*- coding: utf-8 -*-
"""
Path-traversal helpers for the favorites_sharing extension.

Bundles, manifests and target subdirectories all live inside untrusted
trees (Resource Sharing collections, git working copies). Any path that
combines a trusted root with a user/config-supplied component must be
verified to still resolve under the root after symlink resolution.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Optional


def safe_join_under(root: str, *parts: str) -> Optional[str]:
    """Join ``parts`` onto ``root`` and return the result iff it resolves
    under ``root`` after symlink resolution.

    Returns ``None`` when:
      * ``root`` is empty or not an absolute path after normalisation,
      * the joined path escapes ``root`` via ``..`` segments,
      * a symlink anywhere on the resolved path points outside ``root``.

    Use this instead of plain ``os.path.join`` whenever any segment of
    ``parts`` originates from config, user input, or a directory listing
    that may include symlinks.
    """
    if not root:
        return None
    abs_root = os.path.abspath(root)
    candidate = os.path.join(abs_root, *parts)
    real_root = os.path.realpath(abs_root)
    real_candidate = os.path.realpath(candidate)

    try:
        common = os.path.commonpath([real_root, real_candidate])
    except ValueError:
        # Different drives on Windows, or one path is empty.
        return None
    if common != real_root:
        return None
    return real_candidate


def atomic_json_write(path: str, data: Any, *, indent: int = 2) -> None:
    """Write ``data`` to ``path`` as JSON via a temp file + ``os.replace``.

    Guarantees a reader either sees the previous file or the new one, never
    a half-written truncation. Raises ``OSError`` / ``ValueError`` on
    failure — callers decide whether to swallow or propagate.

    The temp file is created in the same directory as ``path`` so the
    rename stays on the same filesystem (``os.replace`` requires this on
    POSIX for atomicity, and Windows refuses cross-device moves).
    """
    target_dir = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(target_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".fmfav_", suffix=".tmp", dir=target_dir,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                # Some filesystems (network mounts) don't implement fsync;
                # skip it rather than fail the write.
                pass
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

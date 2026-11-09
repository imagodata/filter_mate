"""Where exports may be written: below one private root, in a sub-folder named by the client.

No FastAPI here: the chat of the dock runs in the Python of QGIS, without it.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

_SUBFOLDER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}(/[A-Za-z0-9][A-Za-z0-9_.-]{0,63}){0,3}$")


class ExportRootError(RuntimeError):
    """The export root cannot be written safely (link, not a folder, another owner)."""


def prepare_export_root(root: Path) -> Path:
    """Create ``root`` when missing (mode 0700) and check it is safe to write below.

    Refused: a symbolic link or, on Windows, a junction / reparse point
    (whoever made it chose where the files go), a file, or on POSIX a folder
    owned by another user (who could swap its content between the check and
    the write). A root of the user readable by others is made private.
    """
    root = Path(root).expanduser()
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = os.lstat(root)
    except OSError as exc:
        raise ExportRootError(f"export root unavailable: {exc}") from exc
    reparse = getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if stat.S_ISLNK(info.st_mode) or reparse or not stat.S_ISDIR(info.st_mode):
        raise ExportRootError("export root is not a real folder")
    if hasattr(os, "getuid"):
        if info.st_uid != os.getuid():
            raise ExportRootError("export root belongs to another user")
        if info.st_mode & 0o077:
            try:
                os.chmod(root, 0o700)
            except OSError as exc:
                raise ExportRootError(f"export root cannot be made private: {exc}") from exc
    return root


def resolve_export_folder(root: Path, subfolder: str) -> Path:
    """Folder below ``root`` for ``subfolder``; ValueError when it would escape it."""
    # fullmatch: ``$`` alone would let a trailing newline through ("a\n").
    if not _SUBFOLDER.fullmatch(subfolder or "") or ".." in subfolder.split("/"):
        raise ValueError("invalid subfolder")
    root = Path(root).resolve()
    folder = (root / subfolder).resolve()
    if folder != root and root not in folder.parents:
        raise ValueError("invalid subfolder")
    return folder

"""Where exports may be written: below one private root, in a sub-folder named by the client.

No FastAPI here: the chat of the dock runs in the Python of QGIS, without it.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import Tuple

_SUBFOLDER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}(/[A-Za-z0-9][A-Za-z0-9_.-]{0,63}){0,3}$")


class ExportRootError(RuntimeError):
    """The export root cannot be written safely (link, not a folder, another owner)."""


def assert_export_destination(path):
    """Refuse the active QGIS profile and its sibling profiles, including resolved links."""
    from .config import _qgis_profile_dir
    profile = _qgis_profile_dir()
    if not profile:
        return
    profile = Path(profile).expanduser().resolve()
    profiles = profile.parent if profile.parent.name.lower() == 'profiles' else profile
    destination = Path(path).expanduser().resolve()
    if destination == profiles or profiles in destination.parents:
        raise ExportRootError('Exports cannot be written inside a QGIS profile. Choose another export folder.')


def prepare_export_root(root: Path) -> Path:
    """Create ``root`` when missing (mode 0700) and check it is safe to write below.

    Refused: a symbolic link or, on Windows, a junction / reparse point
    (whoever made it chose where the files go), a file, or on POSIX a folder
    owned by another user (who could swap its content between the check and
    the write). A root of the user readable by others is made private.
    """
    root = Path(root() if callable(root) else root).expanduser()
    assert_export_destination(root)
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
            # An explicitly selected existing folder may be a user's shared document folder. Do not chmod it.
            from .config import configured_export_root
            chosen = configured_export_root()
            if chosen is not None and chosen.resolve() == root.resolve():
                return root
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
    assert_export_destination(folder)
    return folder


EXPORTED_FILE = "a relative source is a file export_layers wrote, given as <subfolder>/<its file in outputs>"
MAX_DEPTH = 4  # the sub-folders a client may name: a/b/c/d


def _relative(path: str) -> bool:
    """Neither a URL, a provider or GDAL string (``PG:``, ``C:``), nor a path from a root (``/x``, ``\\x``): those
    are left to the checks of add_layer, which say what they are."""
    return not (os.path.isabs(path) or path.startswith(("/", "\\")) or "://" in path
                or re.match(r"^[A-Za-z0-9_]+:", path))


def _found_below(root: Path, name: str) -> Path:
    """The one file named ``name`` below ``root`` (sub-folders a client may name); ValueError with none or several."""
    found = []
    for folder, children, files in os.walk(root, followlinks=False):
        depth = len(Path(folder).relative_to(root).parts)
        children[:] = [] if depth >= MAX_DEPTH else [child for child in children if not child.startswith(".")]
        if name in files:
            found.append(Path(folder) / name)
    if len(found) == 1:
        return found[0]
    if found:
        raise ValueError(f"several files {name} below the export root: {EXPORTED_FILE}")
    raise ValueError(f"no file {name} below the export root: {EXPORTED_FILE}")


def resolve_exported_file(root: Path, source: str) -> Tuple[str, str]:
    """``(source as it opens, default layer name)``: a relative path is a file export_layers wrote, below ``root``.

    2026-11-24: the chat gets the files of export_layers below its sub-folder (the paths of this machine are not sent
    to the provider), and add_layer took only absolute paths: a model exported a filtered WFS layer to read it
    locally, then got "this file does not exist" for its own "Pays du monde.gpkg". A bare file name is the one file
    of that name below ``root``. Any other source is returned unchanged, with no name. The name is the table or the
    file stem: the title QGIS would draw from a Windows path is that path, which the provider must not read.

    Raises:
        ValueError: The path leaves ``root``, or no file is there (the message says how to name one).
        ExportRootError: ``root`` cannot be used.
    """
    path, bar, table = source.partition("|")
    if not _relative(path):
        return source, ""
    folder, _, name = path.replace("\\", "/").rpartition("/")
    root = prepare_export_root(root).resolve()
    if folder:
        try:
            directory = resolve_export_folder(root, folder)
        except ValueError:
            raise ValueError(EXPORTED_FILE) from None
        full = (directory / name).resolve()
        if not name or full.parent != directory or not full.is_file():
            raise ValueError(f"no file {path} below the export root: {EXPORTED_FILE}")
    else:
        if not name or name in (".", ".."):
            raise ValueError(EXPORTED_FILE)
        full = _found_below(root, name).resolve()
        if root not in full.parents:
            raise ValueError(EXPORTED_FILE)
    title = table.partition("=")[2] if table.startswith("layername=") else full.stem
    return str(full) + bar + table, title

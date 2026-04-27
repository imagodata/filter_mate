# -*- coding: utf-8 -*-
"""
Git binary resolver for the favorites_sharing extension.

Resolution chain (first hit wins):
    1. Explicit user config: ``EXTENSIONS.favorites_sharing.git_binary_path``
    2. Bundled portable Git under the QGIS profile dir
    3. System PATH (``shutil.which("git")``)
    4. ``None`` — caller must surface a "git not found" error

Pure logic — no Qt imports — so it can be unit-tested headless and reused
from both the runtime publish path and the configuration UI.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("FilterMate.FavoritesSharing.GitResolver")


PORTABLE_DIR_NAME = "PortableGit"


class GitSource(Enum):
    """Where the resolved git binary came from."""

    CONFIGURED = "configured"   # user-set EXTENSIONS.favorites_sharing.git_binary_path
    PORTABLE = "portable"       # bundled under [profile]/FilterMate/tools/PortableGit
    SYSTEM = "system"           # shutil.which("git")
    MISSING = "missing"          # nothing found


@dataclass(frozen=True)
class GitResolution:
    """Outcome of a resolver pass."""

    binary_path: Optional[str]
    source: GitSource
    detail: str = ""

    @property
    def found(self) -> bool:
        return self.binary_path is not None and self.source is not GitSource.MISSING


def _is_runnable_file(path: str) -> bool:
    """True if ``path`` exists and is plausibly executable.

    On Windows we accept any existing regular file (the OS handles the
    .exe/.bat resolution); on POSIX we additionally require the +x bit.
    """
    if not path:
        return False
    if not os.path.isfile(path):
        return False
    if os.name == "nt":
        return True
    return os.access(path, os.X_OK)


def get_portable_git_install_dir(profile_tools_dir: str) -> str:
    """Canonical install dir for the bundled portable Git.

    Args:
        profile_tools_dir: ``[QGIS profile]/FilterMate/tools`` — the parent
            under which we drop the PortableGit tree. Caller resolves it
            (the resolver itself stays free of PyQGIS imports so headless
            tests don't need a profile).
    """
    return os.path.join(profile_tools_dir or "", PORTABLE_DIR_NAME)


def get_portable_git_executable(install_dir: str) -> str:
    """Expected path to the git binary inside a PortableGit install.

    Mirrors the upstream PortableGit layout: ``cmd/git.exe`` on Windows
    and ``bin/git`` on POSIX (PortableGit is Windows-only in practice but
    keeping the POSIX shape lets the macOS/Linux resolver still answer
    consistently when admins drop a manual install there).
    """
    if not install_dir:
        return ""
    if os.name == "nt":
        return os.path.join(install_dir, "cmd", "git.exe")
    return os.path.join(install_dir, "bin", "git")


def is_portable_git_installed(install_dir: str) -> bool:
    """True when a usable portable git is present at ``install_dir``."""
    return _is_runnable_file(get_portable_git_executable(install_dir))


def resolve_git_binary(
    *,
    configured_path: str = "",
    profile_tools_dir: str = "",
) -> GitResolution:
    """Walk the resolution chain and return the first hit.

    Args:
        configured_path: Value of
            ``EXTENSIONS.favorites_sharing.git_binary_path`` (may be
            empty).
        profile_tools_dir: ``[QGIS profile]/FilterMate/tools`` — used to
            check for a bundled portable install. May be empty in
            headless contexts.

    Returns:
        A :class:`GitResolution` describing the chosen binary and its
        provenance. ``binary_path`` is ``None`` when nothing was found.
    """
    cfg = (configured_path or "").strip()
    if cfg:
        if _is_runnable_file(cfg):
            return GitResolution(
                binary_path=cfg,
                source=GitSource.CONFIGURED,
                detail=f"configured: {cfg}",
            )
        logger.warning(
            "git_binary_path %r is set but file is missing or not "
            "executable — falling through to portable / PATH.", cfg,
        )

    portable_dir = get_portable_git_install_dir(profile_tools_dir or "")
    portable_exe = get_portable_git_executable(portable_dir)
    if portable_exe and _is_runnable_file(portable_exe):
        return GitResolution(
            binary_path=portable_exe,
            source=GitSource.PORTABLE,
            detail=f"portable: {portable_exe}",
        )

    on_path = shutil.which("git")
    if on_path:
        return GitResolution(
            binary_path=on_path,
            source=GitSource.SYSTEM,
            detail=f"system PATH: {on_path}",
        )

    return GitResolution(
        binary_path=None,
        source=GitSource.MISSING,
        detail=(
            "no git binary found — set EXTENSIONS.favorites_sharing."
            "git_binary_path, install Git for Windows, or download "
            "Portable Git from the Manage Repos dialog."
        ),
    )


def resolve_for_extension(extension) -> GitResolution:
    """Convenience: pull both inputs from a live extension instance.

    Reads ``git_binary_path`` from the extension config and derives
    ``profile_tools_dir`` from FilterMate's ``ENV_VARS`` lookup
    (``PLUGIN_CONFIG_DIRECTORY/tools``). When the env is not set up yet
    (early init, tests), falls through to the path-only resolution.
    """
    configured = ""
    try:
        configured = extension.get_git_binary_path()
    except Exception as exc:
        logger.debug("Cannot read git_binary_path from extension: %s", exc)

    tools_dir = ""
    try:
        from filter_mate.config.config import ENV_VARS  # type: ignore
        base = ENV_VARS.get("PLUGIN_CONFIG_DIRECTORY") or ""
        if base:
            tools_dir = os.path.join(base, "tools")
    except Exception:
        # Standalone import paths (tests, headless harness): no env.
        tools_dir = ""

    return resolve_git_binary(
        configured_path=configured,
        profile_tools_dir=tools_dir,
    )

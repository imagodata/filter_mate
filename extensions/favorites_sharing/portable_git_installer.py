# -*- coding: utf-8 -*-
"""
Portable Git downloader/installer for Windows.

Pulls the official ``PortableGit-<ver>-64-bit.7z.exe`` self-extracting
archive from the Git for Windows GitHub releases, verifies its SHA-256,
and runs it silently to populate ``[QGIS profile]/FilterMate/tools/
PortableGit/``. After that the resolver picks it up automatically.

Why not bundle the .7z inside the plugin? Because that would balloon the
plugin .zip by ~50 MB and tie the FilterMate release cycle to upstream
Git updates. Download-on-demand keeps the plugin lean and lets users
opt-in only when they actually need it.

This module is safe to import on any platform — the heavy lifting only
runs when the caller invokes :func:`download_and_install`. POSIX users
should install ``git`` via their package manager; this installer raises
``UnsupportedPlatformError`` if invoked outside Windows.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .git_resolver import (
    GitSource,
    get_portable_git_executable,
    get_portable_git_install_dir,
    is_portable_git_installed,
    resolve_git_binary,
)

logger = logging.getLogger("FilterMate.FavoritesSharing.PortableGit")


# ---------------------------------------------------------------------------
# Pinned release metadata
# ---------------------------------------------------------------------------
# The default points at a well-known Git for Windows release. Bump the
# version + URL + SHA-256 in lockstep when refreshing — the installer
# refuses to write the tree if the digest doesn't match. Users can also
# override these via the ``override`` argument (e.g. private mirror).

DEFAULT_VERSION = "2.45.1"
DEFAULT_FILENAME = f"PortableGit-{DEFAULT_VERSION}-64-bit.7z.exe"
DEFAULT_URL = (
    f"https://github.com/git-for-windows/git/releases/download/"
    f"v{DEFAULT_VERSION}.windows.1/{DEFAULT_FILENAME}"
)
# Official SHA-256 published on the release notes. Pinned so a hijacked
# CDN can't slip in a tampered archive — we fail fast if the digest
# diverges.
DEFAULT_SHA256 = (
    "f4be1f923e9cc1ee0cb09e99f0e90cf254b530bb622d12064361563307e2f505"
)

DOWNLOAD_TIMEOUT_SECONDS = 180
EXTRACT_TIMEOUT_SECONDS = 300
DEFAULT_CHUNK_SIZE = 256 * 1024  # 256 KiB — friendly for progress callbacks


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PortableGitError(Exception):
    """Generic installer failure (download / verify / extract)."""


class UnsupportedPlatformError(PortableGitError):
    """Raised when invoking the Windows-only installer elsewhere."""


class ChecksumMismatchError(PortableGitError):
    """Raised when the downloaded archive's SHA-256 doesn't match."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class InstallResult:
    """Outcome of an installation attempt."""

    success: bool = False
    install_dir: str = ""
    git_executable: str = ""
    bytes_downloaded: int = 0
    error_message: str = ""
    skipped_reason: str = ""  # "already_installed", "platform_unsupported", …


@dataclass
class DownloadOverride:
    """Optional override of the pinned release metadata.

    Useful for:
    - Pointing at an internal Constructel mirror (intranet-only postes)
    - Pinning a different upstream version per deployment
    - Bypassing GitHub when blocked by corporate firewall
    """

    url: str = ""
    sha256: str = ""
    filename: str = ""

    def merged_url(self) -> str:
        return self.url.strip() or DEFAULT_URL

    def merged_sha256(self) -> str:
        return self.sha256.strip().lower() or DEFAULT_SHA256

    def merged_filename(self) -> str:
        return self.filename.strip() or DEFAULT_FILENAME


def is_supported_platform() -> bool:
    """Portable Git is shipped for Windows only — POSIX users have apt."""
    return os.name == "nt"


def is_already_installed(profile_tools_dir: str) -> bool:
    """True when a runnable PortableGit is present under the profile."""
    return is_portable_git_installed(
        get_portable_git_install_dir(profile_tools_dir or "")
    )


def download_and_install(
    profile_tools_dir: str,
    *,
    override: Optional[DownloadOverride] = None,
    progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
    force: bool = False,
) -> InstallResult:
    """Download, verify and extract Portable Git.

    Args:
        profile_tools_dir: ``[QGIS profile]/FilterMate/tools`` — parent of
            the eventual ``PortableGit/`` directory. Created if missing.
        override: Optional URL / SHA / filename overrides (mirrors).
        progress_callback: ``(bytes_so_far, total_bytes_or_None)`` invoked
            during download. ``total_bytes`` may be ``None`` when the
            server omits ``Content-Length``.
        force: When True, reinstall even if a tree is already present.

    Returns:
        An :class:`InstallResult`. On failure, ``error_message`` carries
        the human-readable cause and any partially-downloaded archive is
        deleted automatically.
    """
    install_dir = get_portable_git_install_dir(profile_tools_dir or "")
    result = InstallResult(install_dir=install_dir)

    if not is_supported_platform():
        result.skipped_reason = "platform_unsupported"
        result.error_message = (
            "Portable Git installer is Windows-only. "
            "Install git via your platform's package manager instead."
        )
        return result

    if not profile_tools_dir:
        result.error_message = (
            "profile_tools_dir is empty — cannot place Portable Git "
            "without a target directory."
        )
        return result

    if not force and is_already_installed(profile_tools_dir):
        result.success = True
        result.git_executable = get_portable_git_executable(install_dir)
        result.skipped_reason = "already_installed"
        return result

    override = override or DownloadOverride()
    url = override.merged_url()
    expected_sha = override.merged_sha256()
    filename = override.merged_filename()

    try:
        os.makedirs(profile_tools_dir, exist_ok=True)
    except OSError as exc:
        result.error_message = (
            f"cannot create tools dir {profile_tools_dir}: {exc}"
        )
        return result

    # Stage the download in a sibling temp dir so we never leave a
    # half-extracted PortableGit tree on disk if extraction fails.
    with tempfile.TemporaryDirectory(prefix="fm-portable-git-") as staging:
        archive_path = os.path.join(staging, filename)
        try:
            bytes_dl = _download(url, archive_path, progress_callback)
        except (URLError, OSError, TimeoutError) as exc:
            result.error_message = f"download failed: {exc}"
            return result
        result.bytes_downloaded = bytes_dl

        try:
            _verify_sha256(archive_path, expected_sha)
        except ChecksumMismatchError as exc:
            result.error_message = (
                f"checksum mismatch — refusing to install. {exc}"
            )
            return result

        if force and os.path.isdir(install_dir):
            try:
                shutil.rmtree(install_dir)
            except OSError as exc:
                result.error_message = (
                    f"cannot remove old install_dir {install_dir}: {exc}"
                )
                return result

        try:
            _extract_self_extracting_7z(archive_path, install_dir)
        except PortableGitError as exc:
            result.error_message = f"extraction failed: {exc}"
            return result

    if not is_portable_git_installed(install_dir):
        result.error_message = (
            f"extracted but git executable not found at "
            f"{get_portable_git_executable(install_dir)}"
        )
        return result

    result.success = True
    result.git_executable = get_portable_git_executable(install_dir)
    return result


def remove_install(profile_tools_dir: str) -> bool:
    """Delete an existing PortableGit install. Returns True on success.

    Best-effort: missing tree returns True (already gone).
    """
    install_dir = get_portable_git_install_dir(profile_tools_dir or "")
    if not os.path.isdir(install_dir):
        return True
    try:
        shutil.rmtree(install_dir)
    except OSError as exc:
        logger.warning("rmtree %s failed: %s", install_dir, exc)
        return False
    return True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _download(
    url: str,
    dest_path: str,
    progress_callback: Optional[Callable[[int, Optional[int]], None]],
) -> int:
    """Stream a URL to disk and return the total bytes written."""
    # Reject non-web schemes — `DownloadOverride.url` is user-supplied, so
    # a misconfigured mirror could otherwise smuggle in `file://`, `ftp://`
    # or custom URL handlers and read arbitrary local files.
    scheme = urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise URLError(
            f"unsupported URL scheme {scheme!r} (only http/https allowed)"
        )
    req = Request(url, headers={"User-Agent": "FilterMate-PortableGit/1.0"})
    bytes_so_far = 0
    with urlopen(req, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:  # nosec B310 - scheme validated above
        total: Optional[int] = None
        cl = response.headers.get("Content-Length")
        if cl and cl.isdigit():
            total = int(cl)
        with open(dest_path, "wb") as fh:
            while True:
                chunk = response.read(DEFAULT_CHUNK_SIZE)
                if not chunk:
                    break
                fh.write(chunk)
                bytes_so_far += len(chunk)
                if progress_callback is not None:
                    try:
                        progress_callback(bytes_so_far, total)
                    except Exception:
                        # A misbehaving callback must not abort a 50 MB
                        # download — log and keep going.
                        logger.debug("progress callback raised", exc_info=True)
    return bytes_so_far


def _verify_sha256(path: str, expected_hex: str) -> None:
    """Raise :class:`ChecksumMismatchError` when digest != ``expected_hex``.

    S6 hardening (audit 2026-04-29): an empty ``expected_hex`` previously
    logged a warning and continued — fine for read-only blobs, dangerous
    for the PortableGit ``.exe`` we are about to execute. The installer
    must refuse to run an unverified self-extractor; tests that legitimately
    need the skip path monkey-patch the function instead.
    """
    expected = (expected_hex or "").strip().lower()
    if not expected:
        raise ChecksumMismatchError(
            f"refusing to install {path}: no SHA-256 digest configured "
            "for this download. Set DownloadOverride.sha256 (or the upstream "
            "DEFAULT_SHA256 constant) to an explicit hex digest before "
            "retrying."
        )
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    actual = h.hexdigest().lower()
    if actual != expected:
        raise ChecksumMismatchError(
            f"expected {expected}, got {actual}"
        )


def _extract_self_extracting_7z(archive_path: str, dest_dir: str) -> None:
    """Run the PortableGit self-extractor silently into ``dest_dir``.

    The PortableGit-x.y.z-64-bit.7z.exe binary is a 7-Zip SFX. The
    documented silent flags are:
        -y         assume yes for prompts
        -o<dir>    output directory (no space between -o and path)

    The extractor returns 0 on success. We surface non-zero codes as
    :class:`PortableGitError` so the UI can show a clear message.
    """
    if not os.path.isfile(archive_path):
        raise PortableGitError(f"archive missing: {archive_path}")

    os.makedirs(dest_dir, exist_ok=True)
    cmd = [archive_path, "-y", f"-o{dest_dir}"]
    logger.debug("Extracting Portable Git: %s", cmd)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=EXTRACT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PortableGitError(
            f"7z self-extractor timed out after {exc.timeout}s"
        ) from exc
    except FileNotFoundError as exc:
        raise PortableGitError(f"cannot run extractor: {exc}") from exc

    if proc.returncode != 0:
        raise PortableGitError(
            f"7z extractor returned {proc.returncode}: "
            f"{(proc.stderr or proc.stdout or '').strip()[:300]}"
        )


def get_default_release_metadata() -> dict:
    """Surface the pinned release info — used by the UI to show the user
    which version will be downloaded before they hit the button."""
    return {
        "version": DEFAULT_VERSION,
        "filename": DEFAULT_FILENAME,
        "url": DEFAULT_URL,
        "sha256": DEFAULT_SHA256,
    }


def current_resolution_after_install(
    profile_tools_dir: str,
    configured_path: str = "",
) -> "tuple[bool, str]":
    """Re-resolve git after a fresh install. Convenience for the UI.

    Returns ``(found, summary)``: ``found`` is True when any git binary
    is now reachable; ``summary`` is a one-line human label including
    the source (system / portable / configured / missing).
    """
    res = resolve_git_binary(
        configured_path=configured_path,
        profile_tools_dir=profile_tools_dir,
    )
    if not res.found:
        return False, "git not found"
    label = {
        GitSource.CONFIGURED: "configured path",
        GitSource.PORTABLE: "portable (downloaded)",
        GitSource.SYSTEM: "system PATH",
    }.get(res.source, res.source.value)
    return True, f"{label} → {res.binary_path}"

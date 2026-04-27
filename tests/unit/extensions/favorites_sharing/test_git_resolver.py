# -*- coding: utf-8 -*-
"""Tests for the git binary resolver chain.

The resolver is pure stdlib + filesystem checks, so we exercise it
without QGIS or git installed. Each test pins one stage of the chain
(configured / portable / system / missing) and asserts the resolution
order — the contract matters more than the absolute paths.
"""

from __future__ import annotations

import os
import stat

import pytest

from extensions.favorites_sharing.git_resolver import (
    GitSource,
    get_portable_git_executable,
    get_portable_git_install_dir,
    is_portable_git_installed,
    resolve_for_extension,
    resolve_git_binary,
)


# ---------------------------------------------------------------------------
# Helpers — fabricate fake "executable" files in tmp paths
# ---------------------------------------------------------------------------


def _make_fake_git(path: str) -> None:
    """Create a file at ``path`` and mark it executable on POSIX."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/sh\necho 2.0.0\n")
    if os.name != "nt":
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


def _portable_path(tools_dir: str) -> str:
    return get_portable_git_executable(get_portable_git_install_dir(tools_dir))


# ---------------------------------------------------------------------------
# Path / install-dir helpers
# ---------------------------------------------------------------------------


class TestPortableLayout:
    def test_install_dir_appends_PortableGit(self, tmp_path):
        tools = str(tmp_path / "tools")
        assert get_portable_git_install_dir(tools).endswith("PortableGit")

    def test_install_dir_handles_empty(self):
        assert get_portable_git_install_dir("") == "PortableGit"

    def test_executable_path_matches_platform(self, tmp_path):
        install = str(tmp_path / "PortableGit")
        exe = get_portable_git_executable(install)
        if os.name == "nt":
            assert exe.endswith(os.path.join("cmd", "git.exe"))
        else:
            assert exe.endswith(os.path.join("bin", "git"))

    def test_executable_path_empty_install_dir(self):
        assert get_portable_git_executable("") == ""

    def test_is_installed_false_when_missing(self, tmp_path):
        assert not is_portable_git_installed(str(tmp_path / "PortableGit"))

    def test_is_installed_true_when_executable_present(self, tmp_path):
        install = str(tmp_path / "PortableGit")
        _make_fake_git(get_portable_git_executable(install))
        assert is_portable_git_installed(install)


# ---------------------------------------------------------------------------
# Resolution chain — order of precedence
# ---------------------------------------------------------------------------


class TestResolveChain:
    def test_missing_when_nothing_provided_and_no_path_git(
        self, tmp_path, monkeypatch
    ):
        # Strip git off PATH so shutil.which returns None
        monkeypatch.setenv("PATH", str(tmp_path))
        res = resolve_git_binary(
            configured_path="",
            profile_tools_dir=str(tmp_path / "tools"),
        )
        assert not res.found
        assert res.source is GitSource.MISSING
        assert "no git" in res.detail.lower()

    def test_configured_path_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PATH", str(tmp_path))
        # Place a portable tree AND a configured path — configured must win
        _make_fake_git(_portable_path(str(tmp_path / "tools")))
        configured = str(tmp_path / "custom-git")
        _make_fake_git(configured)

        res = resolve_git_binary(
            configured_path=configured,
            profile_tools_dir=str(tmp_path / "tools"),
        )
        assert res.found
        assert res.source is GitSource.CONFIGURED
        assert res.binary_path == configured

    def test_configured_path_falls_through_when_missing(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("PATH", str(tmp_path))
        # Configured points at a nonexistent file → resolver should fall
        # through to portable, NOT raise.
        _make_fake_git(_portable_path(str(tmp_path / "tools")))

        res = resolve_git_binary(
            configured_path=str(tmp_path / "does-not-exist"),
            profile_tools_dir=str(tmp_path / "tools"),
        )
        assert res.found
        assert res.source is GitSource.PORTABLE

    def test_portable_used_when_configured_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PATH", str(tmp_path))
        _make_fake_git(_portable_path(str(tmp_path / "tools")))

        res = resolve_git_binary(
            configured_path="",
            profile_tools_dir=str(tmp_path / "tools"),
        )
        assert res.found
        assert res.source is GitSource.PORTABLE

    def test_system_path_used_when_no_configured_no_portable(
        self, tmp_path, monkeypatch
    ):
        # Drop a fake "git" into a directory we put on PATH
        path_dir = tmp_path / "fake-bin"
        path_dir.mkdir()
        if os.name == "nt":
            fake_git = path_dir / "git.exe"
            fake_git.write_text("")
        else:
            fake_git = path_dir / "git"
            _make_fake_git(str(fake_git))
        monkeypatch.setenv("PATH", str(path_dir))

        res = resolve_git_binary(
            configured_path="",
            profile_tools_dir=str(tmp_path / "no-portable"),
        )
        assert res.found
        assert res.source is GitSource.SYSTEM
        assert res.binary_path == str(fake_git)

    def test_whitespace_only_configured_path_treated_as_empty(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("PATH", str(tmp_path))
        _make_fake_git(_portable_path(str(tmp_path / "tools")))

        res = resolve_git_binary(
            configured_path="   ",
            profile_tools_dir=str(tmp_path / "tools"),
        )
        assert res.source is GitSource.PORTABLE


# ---------------------------------------------------------------------------
# Extension shim — convenience entry point
# ---------------------------------------------------------------------------


class _FakeExtension:
    def __init__(self, configured: str = ""):
        self._configured = configured

    def get_git_binary_path(self) -> str:
        return self._configured


class TestResolveForExtension:
    def test_falls_through_to_path_only_when_env_unset(
        self, tmp_path, monkeypatch
    ):
        # No FilterMate env → tools_dir is "" → resolver only sees PATH.
        path_dir = tmp_path / "bin"
        path_dir.mkdir()
        if os.name == "nt":
            (path_dir / "git.exe").write_text("")
        else:
            _make_fake_git(str(path_dir / "git"))
        monkeypatch.setenv("PATH", str(path_dir))

        res = resolve_for_extension(_FakeExtension(""))
        # Either found via SYSTEM (most likely) or MISSING — the contract
        # is that the call doesn't raise even when the env is missing.
        assert res.source in (GitSource.SYSTEM, GitSource.MISSING)

    def test_handles_extension_without_getter(self, tmp_path, monkeypatch):
        # Pass an object that lacks get_git_binary_path — must not crash
        monkeypatch.setenv("PATH", str(tmp_path))
        res = resolve_for_extension(object())
        assert res is not None
        # Either MISSING or SYSTEM depending on host; both are fine
        assert res.source in (GitSource.MISSING, GitSource.SYSTEM)

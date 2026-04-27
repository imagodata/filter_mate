# -*- coding: utf-8 -*-
"""Tests for the Portable Git installer.

We don't actually hit GitHub or run the 7z self-extractor in CI — those
side effects are mocked out. The goal is to exercise the resolver
contract (URL/SHA pinning, idempotence, error envelopes) so a future
refactor can't silently regress download behavior.
"""

from __future__ import annotations

import hashlib
import os

import pytest

from extensions.favorites_sharing import portable_git_installer as installer
from extensions.favorites_sharing.git_resolver import (
    get_portable_git_executable,
    get_portable_git_install_dir,
)


# ---------------------------------------------------------------------------
# Pinned metadata sanity
# ---------------------------------------------------------------------------


class TestReleaseMetadata:
    def test_url_includes_pinned_version(self):
        meta = installer.get_default_release_metadata()
        assert meta["version"] in meta["url"]
        assert meta["version"] in meta["filename"]
        assert meta["url"].startswith(
            "https://github.com/git-for-windows/git/releases/download/"
        )

    def test_sha256_is_64_hex(self):
        meta = installer.get_default_release_metadata()
        sha = meta["sha256"]
        assert len(sha) == 64
        # Validate hex
        int(sha, 16)


# ---------------------------------------------------------------------------
# DownloadOverride merging
# ---------------------------------------------------------------------------


class TestDownloadOverride:
    def test_empty_override_uses_defaults(self):
        ovr = installer.DownloadOverride()
        assert ovr.merged_url() == installer.DEFAULT_URL
        assert ovr.merged_sha256() == installer.DEFAULT_SHA256
        assert ovr.merged_filename() == installer.DEFAULT_FILENAME

    def test_url_override(self):
        ovr = installer.DownloadOverride(url="https://mirror.example.org/pg.exe")
        assert ovr.merged_url() == "https://mirror.example.org/pg.exe"

    def test_sha_override_lowercased(self):
        ovr = installer.DownloadOverride(sha256="ABC123" * 10 + "ABCD")
        assert ovr.merged_sha256() == ("abc123" * 10 + "abcd")

    def test_whitespace_only_override_falls_back_to_default(self):
        ovr = installer.DownloadOverride(url="   ", sha256="\t\n", filename="")
        assert ovr.merged_url() == installer.DEFAULT_URL
        assert ovr.merged_sha256() == installer.DEFAULT_SHA256
        assert ovr.merged_filename() == installer.DEFAULT_FILENAME


# ---------------------------------------------------------------------------
# Platform gating
# ---------------------------------------------------------------------------


class TestPlatformGate:
    def test_unsupported_platform_returns_skip(self, tmp_path, monkeypatch):
        # Force POSIX semantics on every host
        monkeypatch.setattr(installer, "is_supported_platform", lambda: False)
        result = installer.download_and_install(str(tmp_path))
        assert not result.success
        assert result.skipped_reason == "platform_unsupported"

    def test_empty_tools_dir_rejected(self, monkeypatch):
        monkeypatch.setattr(installer, "is_supported_platform", lambda: True)
        result = installer.download_and_install("")
        assert not result.success
        assert "profile_tools_dir" in result.error_message


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------


class TestIdempotence:
    def test_already_installed_short_circuits_when_not_force(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(installer, "is_supported_platform", lambda: True)
        # Simulate an existing portable install
        install_dir = get_portable_git_install_dir(str(tmp_path))
        exe = get_portable_git_executable(install_dir)
        os.makedirs(os.path.dirname(exe), exist_ok=True)
        with open(exe, "w") as fh:
            fh.write("")
        if os.name != "nt":
            os.chmod(exe, 0o755)

        result = installer.download_and_install(
            str(tmp_path), force=False,
        )
        assert result.success
        assert result.skipped_reason == "already_installed"
        assert result.git_executable == exe


# ---------------------------------------------------------------------------
# Checksum verification
# ---------------------------------------------------------------------------


class TestVerifyChecksum:
    def test_matching_digest_does_not_raise(self, tmp_path):
        path = tmp_path / "blob"
        path.write_bytes(b"hello world")
        digest = hashlib.sha256(b"hello world").hexdigest()
        # Public function via the module-private name to keep behavior
        # locked: a future API rename should also update the test.
        installer._verify_sha256(str(path), digest)

    def test_mismatch_raises(self, tmp_path):
        path = tmp_path / "blob"
        path.write_bytes(b"hello world")
        with pytest.raises(installer.ChecksumMismatchError):
            installer._verify_sha256(str(path), "0" * 64)

    def test_empty_expected_logs_and_passes(self, tmp_path):
        path = tmp_path / "blob"
        path.write_bytes(b"x")
        # Should not raise — opt-out path used by tests / dev mirrors
        installer._verify_sha256(str(path), "")


# ---------------------------------------------------------------------------
# Scheme guard: reject file:// / ftp:// / custom handlers before urlopen
# ---------------------------------------------------------------------------


class TestDownloadSchemeGuard:
    @pytest.mark.parametrize("bad_url", [
        "file:///etc/passwd",
        "ftp://mirror.example.com/PortableGit.7z.exe",
        "javascript:alert(1)",
        "data:text/plain;base64,aGVsbG8=",
        "/local/path/no/scheme",
    ])
    def test_non_http_scheme_rejected(self, tmp_path, bad_url):
        from urllib.error import URLError
        with pytest.raises(URLError, match="unsupported URL scheme"):
            installer._download(
                bad_url, str(tmp_path / "out.bin"), progress_callback=None,
            )


# ---------------------------------------------------------------------------
# Mocked end-to-end: download → verify → extract → resolver picks up
# ---------------------------------------------------------------------------


class TestMockedDownloadFlow:
    def test_full_flow_with_monkeypatched_internals(
        self, tmp_path, monkeypatch
    ):
        """Exercise download_and_install with the network and 7z stubbed.

        We replace ``_download`` with a function that writes deterministic
        bytes, ``_verify_sha256`` with a no-op (so the test doesn't have
        to compute the expected digest), and ``_extract_self_extracting_7z``
        with a function that materializes a fake git binary at the
        expected layout. The test then asserts the success envelope and
        that the resolver would now find the new install.
        """
        monkeypatch.setattr(installer, "is_supported_platform", lambda: True)

        def fake_download(url, dest_path, progress_callback):
            with open(dest_path, "wb") as fh:
                fh.write(b"FAKE-7Z")
            if progress_callback:
                progress_callback(7, 7)
            return 7

        def fake_verify(path, expected):
            # Pretend the digest matched — we already test the real
            # verifier elsewhere.
            return

        def fake_extract(archive, dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
            exe = get_portable_git_executable(dest_dir)
            os.makedirs(os.path.dirname(exe), exist_ok=True)
            with open(exe, "w") as fh:
                fh.write("#!/bin/sh\necho 2.0.0\n")
            if os.name != "nt":
                os.chmod(exe, 0o755)

        monkeypatch.setattr(installer, "_download", fake_download)
        monkeypatch.setattr(installer, "_verify_sha256", fake_verify)
        monkeypatch.setattr(
            installer, "_extract_self_extracting_7z", fake_extract,
        )

        result = installer.download_and_install(str(tmp_path))

        assert result.success, result.error_message
        assert result.bytes_downloaded == 7
        assert os.path.isfile(result.git_executable)
        # And the resolver agrees that something is now installed
        assert installer.is_already_installed(str(tmp_path))

    def test_extraction_failure_leaves_no_partial_install(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(installer, "is_supported_platform", lambda: True)

        monkeypatch.setattr(
            installer, "_download",
            lambda url, dest, cb: (open(dest, "wb").close() or 0),
        )
        monkeypatch.setattr(installer, "_verify_sha256", lambda *a, **kw: None)
        monkeypatch.setattr(
            installer, "_extract_self_extracting_7z",
            lambda *a, **kw: (_ for _ in ()).throw(
                installer.PortableGitError("boom"),
            ),
        )

        result = installer.download_and_install(str(tmp_path))
        assert not result.success
        assert "boom" in result.error_message
        # No git binary was materialized
        assert not installer.is_already_installed(str(tmp_path))


# ---------------------------------------------------------------------------
# Removal helper
# ---------------------------------------------------------------------------


class TestRemoveInstall:
    def test_removes_existing_tree(self, tmp_path):
        install_dir = get_portable_git_install_dir(str(tmp_path))
        os.makedirs(install_dir, exist_ok=True)
        with open(os.path.join(install_dir, "marker"), "w") as fh:
            fh.write("x")

        assert installer.remove_install(str(tmp_path)) is True
        assert not os.path.isdir(install_dir)

    def test_missing_tree_returns_true(self, tmp_path):
        # idempotent — removing a non-existent install is success
        assert installer.remove_install(str(tmp_path / "nope")) is True

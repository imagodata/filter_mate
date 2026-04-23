# -*- coding: utf-8 -*-
"""
Tests for the GitClient subprocess wrapper.

The tests run real ``git`` commands against a local bare repo built in
``tmp_path`` — no network, no auth. The goal is to exercise the wrapper
surface (clone, pull --ff-only, add/commit/push, error envelopes) end to
end without mocking subprocess.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from extensions.favorites_sharing.git_client import (
    GitClient,
    GitError,
)


pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git binary not available",
)


# ---------------------------------------------------------------------------
# Fixtures: a tiny bare remote + helper to build clones
# ---------------------------------------------------------------------------


def _run(args, cwd=None):
    """Fire a git command inline; used by fixtures only."""
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def bare_remote(tmp_path):
    """Empty bare repo acting as the remote origin."""
    remote = tmp_path / "origin.git"
    remote.mkdir()
    _run(["git", "init", "--bare", "-b", "main", str(remote)])
    return remote


@pytest.fixture
def seeded_remote(tmp_path, bare_remote):
    """Bare remote pre-seeded with one initial commit on ``main``."""
    seed = tmp_path / "_seed"
    seed.mkdir()
    _run(["git", "init", "-b", "main", str(seed)])
    _run(["git", "config", "user.email", "seed@example.com"], cwd=seed)
    _run(["git", "config", "user.name", "Seed"], cwd=seed)
    (seed / "README.md").write_text("init\n")
    _run(["git", "add", "README.md"], cwd=seed)
    _run(["git", "commit", "-m", "seed"], cwd=seed)
    _run(["git", "remote", "add", "origin", str(bare_remote)], cwd=seed)
    _run(["git", "push", "origin", "main"], cwd=seed)
    return bare_remote


def _configure_identity(path):
    """Give the test clone a local git identity so commits don't fail."""
    _run(["git", "config", "user.email", "test@example.com"], cwd=path)
    _run(["git", "config", "user.name", "Test"], cwd=path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGitClient:
    """Exercises the wrapper end-to-end against real git."""

    def test_is_cloned_false_when_dir_missing(self, tmp_path):
        client = GitClient(cwd=str(tmp_path / "nope"))
        assert client.is_cloned() is False

    def test_clone_creates_working_tree(self, tmp_path, seeded_remote):
        dest = tmp_path / "clone"
        client = GitClient(cwd=str(dest))
        result = client.clone(str(seeded_remote), branch="main")
        assert result.ok
        assert client.is_cloned()
        assert (dest / "README.md").read_text() == "init\n"

    def test_clone_is_idempotent(self, tmp_path, seeded_remote):
        dest = tmp_path / "clone"
        client = GitClient(cwd=str(dest))
        client.clone(str(seeded_remote), branch="main")
        result = client.clone(str(seeded_remote), branch="main")
        assert result.ok
        assert "already cloned" in result.stdout

    def test_pull_ff_only_on_diverged_history_raises(self, tmp_path, seeded_remote):
        """A fast-forward refusal must surface as GitError (no auto-merge)."""
        # Clone A, make a local divergent commit
        clone_a = tmp_path / "a"
        a = GitClient(cwd=str(clone_a))
        a.clone(str(seeded_remote), branch="main")
        _configure_identity(clone_a)

        # Second clone B, push a commit — now origin diverges from A.
        clone_b = tmp_path / "b"
        b = GitClient(cwd=str(clone_b))
        b.clone(str(seeded_remote), branch="main")
        _configure_identity(clone_b)
        (clone_b / "from_b.txt").write_text("b\n")
        b.add(["from_b.txt"])
        b.commit("from b")
        b.push("origin", "main")

        # Local divergent change on A
        (clone_a / "local.txt").write_text("a\n")
        a.add(["local.txt"])
        a.commit("local a")

        with pytest.raises(GitError) as excinfo:
            a.pull_fast_forward()
        # The error message carries the exit code + stderr for diagnostics.
        assert excinfo.value.returncode != 0

    def test_has_staged_changes_detects_index_delta(self, tmp_path, seeded_remote):
        clone = tmp_path / "c"
        client = GitClient(cwd=str(clone))
        client.clone(str(seeded_remote), branch="main")
        _configure_identity(clone)

        assert client.has_staged_changes() is False
        (clone / "new.txt").write_text("x\n")
        client.add(["new.txt"])
        assert client.has_staged_changes() is True

    def test_commit_and_push_round_trip(self, tmp_path, seeded_remote):
        clone = tmp_path / "c"
        client = GitClient(cwd=str(clone))
        client.clone(str(seeded_remote), branch="main")
        _configure_identity(clone)

        bundle = clone / "bundle.json"
        bundle.write_text('{"a": 1}\n')
        client.add([str(bundle)])
        client.commit("add bundle", author="Alice <alice@example.com>")

        head = client.head_sha()
        assert head and len(head) >= 4

        res = client.push("origin", "main")
        assert res.ok

        # Verify remote received it
        verify_dir = tmp_path / "verify"
        verify = GitClient(cwd=str(verify_dir))
        verify.clone(str(seeded_remote), branch="main")
        assert (verify_dir / "bundle.json").exists()

    def test_timeout_surfaces_as_giterror(self, tmp_path, seeded_remote):
        """Clamping the timeout to 0s forces an instant timeout."""
        clone = tmp_path / "c"
        client = GitClient(
            cwd=str(clone),
            timeout_seconds=0,  # immediate timeout
        )
        with pytest.raises(GitError) as excinfo:
            client.clone(str(seeded_remote), branch="main")
        assert "timeout" in excinfo.value.stderr.lower()

    def test_missing_git_binary(self, tmp_path):
        client = GitClient(cwd=str(tmp_path), git_binary="git-does-not-exist-xyz")
        with pytest.raises(GitError) as excinfo:
            client._run(["status"])
        assert "not found" in excinfo.value.stderr.lower()

    def test_auth_header_passed_via_config_not_argv(self, tmp_path, seeded_remote, monkeypatch):
        """Tokens must travel via git's --config, never as bare argv."""
        captured = {}

        orig_run = subprocess.run

        def spy(cmd, **kwargs):
            captured.setdefault("invocations", []).append(list(cmd))
            return orig_run(cmd, **kwargs)

        monkeypatch.setattr(subprocess, "run", spy)

        dest = tmp_path / "clone"
        client = GitClient(
            cwd=str(dest),
            auth_header="Bearer SECRET-TOKEN-123",
        )
        client.clone(str(seeded_remote), branch="main")

        # The token should appear in the -c http.extraHeader= slot, not
        # anywhere else in the argv list.
        for argv in captured["invocations"]:
            joined = " ".join(argv)
            assert "SECRET-TOKEN-123" in joined
            # Hard assertion: token is always associated with the config flag
            idx = argv.index("-c")
            assert "http.extraHeader" in argv[idx + 1]
            assert "SECRET-TOKEN-123" in argv[idx + 1]

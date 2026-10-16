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
    _scrub_command,
    _scrub_text,
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

    @staticmethod
    def _spy_clone(tmp_path, seeded_remote, monkeypatch, git_version=None, extra_env=None):
        """Clone with a stored token; every (argv, env) handed to subprocess.run."""
        invocations = []
        orig_run = subprocess.run

        def spy(cmd, **kwargs):
            invocations.append((list(cmd), dict(kwargs.get("env") or {})))
            return orig_run(cmd, **kwargs)

        monkeypatch.setattr(subprocess, "run", spy)
        # The credential comes from the QGIS Auth Manager (authcfg_id), resolved at exec time.
        import extensions.favorites_sharing.git_client as git_client_module
        monkeypatch.setattr(git_client_module, "_resolve_authcfg_header",
                            lambda authcfg_id: "Bearer SECRET-TOKEN-123")
        if git_version is not None:
            monkeypatch.setattr(git_client_module, "_git_version", lambda binary: git_version)

        client = GitClient(cwd=str(tmp_path / "clone"), authcfg_id="qg1xy7w", extra_env=extra_env or {})
        client.clone(str(seeded_remote), branch="main")
        return [(argv, env) for argv, env in invocations if "clone" in argv]

    def test_auth_header_passed_via_environment_not_argv(self, tmp_path, seeded_remote, monkeypatch):
        """Audit 2026-10: argv is world-readable (/proc/<pid>/cmdline): the token travels in the environment."""
        (argv, env), = self._spy_clone(tmp_path, seeded_remote, monkeypatch)
        assert "SECRET-TOKEN-123" not in " ".join(argv)
        index = int(env["GIT_CONFIG_COUNT"]) - 1
        assert env[f"GIT_CONFIG_KEY_{index}"] == "http.extraHeader"
        assert env[f"GIT_CONFIG_VALUE_{index}"] == "Authorization: Bearer SECRET-TOKEN-123"

    def test_existing_git_config_count_is_kept(self, tmp_path, seeded_remote, monkeypatch):
        (argv, env), = self._spy_clone(tmp_path, seeded_remote, monkeypatch, git_version=(2, 43),
                                        extra_env={"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.autocrlf",
                                                   "GIT_CONFIG_VALUE_0": "false"})
        assert env["GIT_CONFIG_COUNT"] == "2"
        assert env["GIT_CONFIG_KEY_0"] == "core.autocrlf"
        assert env["GIT_CONFIG_KEY_1"] == "http.extraHeader"

    def test_old_git_falls_back_to_the_command_line(self, tmp_path, seeded_remote, monkeypatch):
        """git < 2.31 has no GIT_CONFIG_COUNT: the -c option is the only way left."""
        (argv, env), = self._spy_clone(tmp_path, seeded_remote, monkeypatch, git_version=(2, 30))
        index = argv.index("-c")
        assert argv[index + 1] == "http.extraHeader=Authorization: Bearer SECRET-TOKEN-123"
        assert "GIT_CONFIG_COUNT" not in env or "SECRET" not in str(env)

    def test_git_version_parsing(self, monkeypatch):
        import extensions.favorites_sharing.git_client as git_client_module

        class _Proc:
            returncode = 0
            stdout = ""

        for text, expected in (("git version 2.43.0\n", (2, 43)), ("git version 2.39.2.windows.1", (2, 39)),
                               ("git version 2.30.1 (Apple Git-130)", (2, 30)), ("nonsense", None)):
            proc = _Proc()
            proc.stdout = text
            monkeypatch.setattr(git_client_module, "_GIT_VERSIONS", {})
            monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: proc)
            assert git_client_module._git_version("git") == expected

    def test_missing_binary_has_no_version(self):
        from extensions.favorites_sharing.git_client import _git_version
        assert _git_version("git-does-not-exist-xyz") is None


class TestTransportsAndIdentity:
    """Audit 2026-10: only https / ssh, and a commit works on a fresh install."""

    def test_local_path_refused_in_production(self, tmp_path, seeded_remote, monkeypatch):
        import extensions.favorites_sharing.git_client as git_client_module
        monkeypatch.setattr(git_client_module, "ALLOWED_PROTOCOLS", "https:ssh")  # undo the conftest opening
        with pytest.raises(GitError) as excinfo:
            GitClient(cwd=str(tmp_path / "clone")).clone(str(seeded_remote), branch="main")
        assert "not allowed" in excinfo.value.stderr

    @pytest.mark.parametrize("url", ["http://127.0.0.1:9/team/repo.git", "git://127.0.0.1:9/repo.git",
                                     "ext::sh -c touch% /tmp/pwned"])
    def test_plaintext_and_command_transports_refused(self, tmp_path, url):
        with pytest.raises(GitError) as excinfo:
            GitClient(cwd=str(tmp_path / "clone"), timeout_seconds=10).clone(url)
        assert "not allowed" in excinfo.value.stderr

    def test_commit_on_a_fresh_install_uses_the_author_as_committer(self, tmp_path, seeded_remote, monkeypatch):
        # No global / system identity at all, like a new Windows workstation.
        for name in ("EMAIL", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
            monkeypatch.delenv(name, raising=False)
        home = tmp_path / "home"
        home.mkdir()
        fresh = {"HOME": str(home), "XDG_CONFIG_HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1",
                 "GIT_CONFIG_GLOBAL": str(home / "none")}
        client = GitClient(cwd=str(tmp_path / "clone"), extra_env=fresh)
        client.clone(str(seeded_remote), branch="main")
        (tmp_path / "clone" / "bundle.json").write_text("{}")
        client.add(["bundle.json"])
        client.commit("publish", author="Acme team <team@acme.example>")
        res = client._run(["log", "-1", "--format=%cn <%ce>|%an <%ae>"])
        assert res.stdout.strip() == "Acme team <team@acme.example>|Acme team <team@acme.example>"

    def test_configured_identity_stays_the_committer(self, tmp_path, seeded_remote):
        client = GitClient(cwd=str(tmp_path / "clone"))
        client.clone(str(seeded_remote), branch="main")
        client._run(["config", "user.name", "Local User"])
        client._run(["config", "user.email", "local@example.com"])
        (tmp_path / "clone" / "bundle.json").write_text("{}")
        client.add(["bundle.json"])
        client.commit("publish", author="Acme team <team@acme.example>")
        res = client._run(["log", "-1", "--format=%cn <%ce>|%an <%ae>"])
        assert res.stdout.strip() == "Local User <local@example.com>|Acme team <team@acme.example>"


# ---------------------------------------------------------------------------
# M7: secret scrubbing on the leak path (audit 2026-04-23)
# ---------------------------------------------------------------------------


class TestSecretScrubbing:
    """The auth header / URL-embedded creds must never leave the process via
    GitError messages, the .stderr field, or debug logs."""

    def test_scrub_command_redacts_auth_header_arg(self):
        cmd = [
            "git", "-c",
            "http.extraHeader=Authorization: Bearer SECRET-TOKEN-123",
            "fetch",
        ]
        scrubbed = _scrub_command(cmd)
        joined = " ".join(scrubbed)
        assert "SECRET-TOKEN-123" not in joined
        assert "[REDACTED]" in joined
        # Original list untouched (function returns a copy).
        assert "SECRET-TOKEN-123" in " ".join(cmd)

    def test_scrub_command_no_auth_arg_is_passthrough(self):
        cmd = ["git", "status"]
        assert _scrub_command(cmd) == cmd

    def test_scrub_text_redacts_url_embedded_creds(self):
        text = "fatal: unable to access 'https://user:hunter2@host/repo.git/'"
        scrubbed = _scrub_text(text)
        assert "hunter2" not in scrubbed
        assert "user" not in scrubbed
        assert "[REDACTED]" in scrubbed

    def test_scrub_text_redacts_authorization_header_in_log(self):
        text = "request: http.extraHeader=Authorization: Bearer SECRET-XYZ"
        scrubbed = _scrub_text(text)
        assert "SECRET-XYZ" not in scrubbed
        assert "[REDACTED]" in scrubbed

    def test_scrub_text_empty_string_is_safe(self):
        assert _scrub_text("") == ""
        assert _scrub_text(None) is None  # type: ignore[arg-type]

    def test_scrub_command_redacts_url_credentials(self):
        # Audit 2026-10: a GitLab token in the clone URL reached the message bar and the log.
        cmd = ["git", "clone", "--", "https://oauth2:glpat-SECRET@gitlab.example/team/repo.git", "/tmp/c"]
        joined = " ".join(_scrub_command(cmd))
        assert "glpat-SECRET" not in joined and "oauth2" not in joined
        assert "https://[REDACTED]@gitlab.example/team/repo.git" in joined

    def test_password_holding_an_at_sign_is_masked_whole(self):
        scrubbed = _scrub_text("https://user:p@ss@word@host/repo.git")
        assert "ss" not in scrubbed.split("@host")[0].replace("[REDACTED]", "")
        assert scrubbed == "https://[REDACTED]@host/repo.git"

    def test_giterror_message_hides_url_token(self):
        err = GitError(["git", "clone", "--", "https://oauth2:glpat-SECRET@gitlab.example/r.git", "/tmp/c"],
                       128, "https://oauth2:glpat-SECRET@gitlab.example", "fatal: repository not found")
        assert "glpat-SECRET" not in str(err)
        assert "glpat-SECRET" not in " ".join(err.command)
        assert "glpat-SECRET" not in err.stdout

    def test_giterror_message_does_not_leak_token(self):
        cmd = [
            "git", "-c",
            "http.extraHeader=Authorization: Bearer SECRET-TOKEN-123",
            "push",
        ]
        err = GitError(
            command=cmd,
            returncode=128,
            stdout="",
            stderr="fatal: unable to access 'https://u:tok@h/r.git/'",
            cwd="/tmp/clone",
        )
        msg = str(err)
        assert "SECRET-TOKEN-123" not in msg
        assert "tok" not in msg  # URL-embedded token also scrubbed
        # Stored fields are scrubbed too.
        assert "SECRET-TOKEN-123" not in " ".join(err.command)
        assert "tok" not in err.stderr


# ---------------------------------------------------------------------------
# authcfg_id resolution — the only credential source since FilterMate 5.0
# ---------------------------------------------------------------------------


class TestAuthcfgResolution:
    """``authcfg_id`` is the only credential source (the plaintext auth_header
    was removed in 5.0, audit EXT-6); without QgsAuthManager git runs anonymous."""

    def test_resolve_returns_none_without_qgis(self, monkeypatch):
        """Standalone tests have no qgis.core importable — must not crash."""
        # Force the import in _resolve_authcfg_header to fail
        import builtins
        real_import = builtins.__import__

        def raising(name, *a, **kw):
            if name == "qgis.core":
                raise ImportError("simulated standalone env")
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", raising)

        from extensions.favorites_sharing.git_client import _resolve_authcfg_header
        assert _resolve_authcfg_header("anything") is None

    def test_unresolvable_authcfg_runs_unauthenticated(self, tmp_path):
        """No QGIS in the test harness: authcfg returns None and nothing else is used."""
        from extensions.favorites_sharing.git_client import GitClient

        client = GitClient(cwd=str(tmp_path), authcfg_id="qg1xy7w")
        assert client._resolve_auth_header() is None

    def test_plaintext_auth_header_is_gone(self, tmp_path):
        from extensions.favorites_sharing.git_client import GitClient

        with pytest.raises(TypeError):
            GitClient(cwd=str(tmp_path), auth_header="Bearer LEGACY")

    def test_no_credentials_at_all_returns_none(self, tmp_path):
        """No authcfg_id → None (anonymous git)."""
        from extensions.favorites_sharing.git_client import GitClient

        client = GitClient(cwd=str(tmp_path))
        assert client._resolve_auth_header() is None

    def test_authcfg_resolution_is_called_lazily(
        self, tmp_path, seeded_remote, monkeypatch,
    ):
        """Resolver fires at exec time, not at __init__ — so the QGIS
        master-password prompt only happens when a publish actually runs."""
        from extensions.favorites_sharing import git_client as gc_mod

        calls = {"count": 0}

        def spy_resolver(authcfg_id):
            calls["count"] += 1
            return None

        monkeypatch.setattr(gc_mod, "_resolve_authcfg_header", spy_resolver)

        # Constructing the client must not call the resolver
        client = gc_mod.GitClient(cwd=str(tmp_path / "x"), authcfg_id="qg1xy7w")
        assert calls["count"] == 0

        # Running a command does
        try:
            client.clone(str(seeded_remote), branch="main")
        except gc_mod.GitError:
            pass
        assert calls["count"] >= 1

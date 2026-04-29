# -*- coding: utf-8 -*-
"""
Tests for RemoteRepoManager — config parsing, selection logic, and the
publish orchestration against a real local git remote.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import types

import pytest

from extensions.favorites_sharing.remote_repo_manager import (
    LEGACY_AUTH_HEADER_DEADLINE,
    RemoteRepo,
    RemoteRepoManager,
    RepoStatus,
)

GIT_AVAILABLE = shutil.which("git") is not None


# ---------------------------------------------------------------------------
# Fake extension: only needs get_remote_repos() for the manager
# ---------------------------------------------------------------------------


class FakeExtension:
    def __init__(self, repos, git_binary_path: str = ""):
        self._repos = list(repos)
        self._git_binary_path = git_binary_path
        self.last_set_call = None

    def get_remote_repos(self):
        return list(self._repos)

    def get_git_binary_path(self) -> str:
        return self._git_binary_path

    def set_config(self, key, value, *, persist=True):
        self.last_set_call = (key, value, persist)
        if key == "remote_repos" and isinstance(value, list):
            self._repos = list(value)
        elif key == "git_binary_path":
            self._git_binary_path = value
        return True


# ---------------------------------------------------------------------------
# from_config_entry — validation surface
# ---------------------------------------------------------------------------


class TestRemoteRepoFromConfig:
    def test_drops_entries_with_no_name(self):
        assert RemoteRepo.from_config_entry({}) is None
        assert RemoteRepo.from_config_entry({"name": ""}) is None
        assert RemoteRepo.from_config_entry({"name": "   "}) is None

    def test_drops_non_dict_entries(self):
        assert RemoteRepo.from_config_entry("not-a-dict") is None
        assert RemoteRepo.from_config_entry(None) is None
        assert RemoteRepo.from_config_entry(42) is None

    def test_parses_full_entry(self):
        repo = RemoteRepo.from_config_entry({
            "name": "Constructel",
            "git_url": "http://192.168.160.31:9082/",
            "branch": "master",
            "local_clone": "~/.cache/filter_mate/repos/constructel",
            "target_collection": "constructel_sketches",
            "is_default": True,
            "auth_header": "Bearer tok",
        })
        assert repo is not None
        assert repo.name == "Constructel"
        assert repo.is_default is True
        assert repo.has_remote
        assert repo.expanded_local_clone.endswith(
            os.path.join(".cache", "filter_mate", "repos", "constructel")
        )

    def test_preserves_unknown_fields_in_extra(self):
        repo = RemoteRepo.from_config_entry({
            "name": "X", "future_field": {"nested": 1},
        })
        assert repo is not None
        assert repo.extra == {"future_field": {"nested": 1}}

    def test_parses_authcfg_id(self):
        repo = RemoteRepo.from_config_entry({
            "name": "Acme", "authcfg_id": "qg1xy7w",
        })
        assert repo is not None
        assert repo.authcfg_id == "qg1xy7w"
        assert repo.auth_header == ""

    def test_legacy_auth_header_logs_deprecation(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING,
                             logger="FilterMate.FavoritesSharing.RemoteRepo"):
            repo = RemoteRepo.from_config_entry({
                "name": "Legacy", "auth_header": "Bearer tok",
            })
        assert repo is not None
        assert repo.auth_header == "Bearer tok"
        assert any("legacy plaintext auth_header" in rec.message
                   for rec in caplog.records)

    def test_authcfg_id_does_not_warn(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING,
                             logger="FilterMate.FavoritesSharing.RemoteRepo"):
            RemoteRepo.from_config_entry({
                "name": "Encrypted", "authcfg_id": "qg1xy7w",
            })
        assert not any("legacy plaintext auth_header" in rec.message
                       for rec in caplog.records)

    def test_legacy_auth_header_purge_tripwire(self):
        """Tripwire for the EXT-6 audit promise.

        ``LEGACY_AUTH_HEADER_DEADLINE`` is currently enforced only via a
        ``logger.warning`` — there is no runtime guard that rejects entries
        carrying a plaintext ``auth_header`` once FilterMate is at or past
        the declared deadline. This test fails the moment the plugin
        version reaches ``LEGACY_AUTH_HEADER_DEADLINE`` (currently
        ``"5.0.0"``) so the dev cannot ship a major bump without:

        1. dropping the ``auth_header`` field from ``RemoteRepo``,
        2. removing the warning path in ``from_config_entry``,
        3. raising on / refusing entries that still carry it,
        4. deleting this tripwire.

        See `project_audit_general_deep_2026_04_29.md` (P1-EXT6).
        """
        import os
        import re

        plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )))
        metadata_path = os.path.join(plugin_root, "metadata.txt")
        assert os.path.exists(metadata_path), \
            f"metadata.txt not found at {metadata_path}"

        with open(metadata_path, encoding="utf-8") as fh:
            match = re.search(r"^version=(\S+)\s*$", fh.read(), re.MULTILINE)
        assert match, "metadata.txt is missing a version= line"
        current = match.group(1)

        def _version_tuple(v: str) -> tuple:
            # Strip any trailing pre-release tag (e.g. "5.0.0-rc1").
            head = v.split("-", 1)[0]
            return tuple(int(p) for p in head.split(".") if p.isdigit())

        current_t = _version_tuple(current)
        deadline_t = _version_tuple(LEGACY_AUTH_HEADER_DEADLINE)

        if current_t >= deadline_t:
            pytest.fail(
                f"FilterMate is at v{current} (>= deadline "
                f"{LEGACY_AUTH_HEADER_DEADLINE}). Time to drop legacy "
                "plaintext auth_header support per the EXT-6 audit "
                "promise: remove the field on RemoteRepo, drop the "
                "warning branch in from_config_entry, raise on entries "
                "that still carry it (or skip them), and delete this "
                "tripwire test."
            )

    def test_collection_dir_uses_collections_subdir(self, tmp_path):
        repo = RemoteRepo.from_config_entry({
            "name": "X",
            "local_clone": str(tmp_path / "clone"),
            "target_collection": "mycoll",
        })
        assert repo.collection_dir == str(
            tmp_path / "clone" / "collections" / "mycoll"
        )

    def test_collection_dir_falls_back_to_clone_root(self, tmp_path):
        repo = RemoteRepo.from_config_entry({
            "name": "X",
            "local_clone": str(tmp_path / "clone"),
            # no target_collection — single-collection repo
        })
        assert repo.collection_dir == str(tmp_path / "clone")


# ---------------------------------------------------------------------------
# Status badges reflect disk state
# ---------------------------------------------------------------------------


class TestRepoStatus:
    def test_not_cloned_when_dir_missing(self, tmp_path):
        repo = RemoteRepo(
            name="X", git_url="http://example/x.git",
            local_clone=str(tmp_path / "absent"),
        )
        assert repo.status() == RepoStatus.NOT_CLONED

    def test_cloned_when_git_dir_present(self, tmp_path):
        clone = tmp_path / "clone"
        clone.mkdir()
        (clone / ".git").mkdir()
        repo = RemoteRepo(
            name="X", git_url="http://example/x.git",
            local_clone=str(clone),
        )
        assert repo.status() == RepoStatus.CLONED

    def test_local_only_when_no_remote_and_dir_exists(self, tmp_path):
        clone = tmp_path / "c"
        clone.mkdir()
        repo = RemoteRepo(name="X", local_clone=str(clone))
        assert repo.status() == RepoStatus.LOCAL_ONLY


# ---------------------------------------------------------------------------
# Manager selection logic
# ---------------------------------------------------------------------------


class TestManagerSelection:
    def test_list_repos_drops_invalid(self):
        ext = FakeExtension([
            {"name": "A"},
            {"name": ""},  # dropped
            "not-a-dict",  # dropped
            {"name": "B"},
        ])
        mgr = RemoteRepoManager(ext)
        names = [r.name for r in mgr.list_repos()]
        assert names == ["A", "B"]

    def test_default_respects_is_default_flag(self):
        ext = FakeExtension([
            {"name": "A"},
            {"name": "B", "is_default": True},
            {"name": "C"},
        ])
        mgr = RemoteRepoManager(ext)
        assert mgr.get_default().name == "B"

    def test_default_falls_back_to_first_entry(self):
        ext = FakeExtension([{"name": "A"}, {"name": "B"}])
        mgr = RemoteRepoManager(ext)
        assert mgr.get_default().name == "A"

    def test_default_returns_none_on_empty_config(self):
        mgr = RemoteRepoManager(FakeExtension([]))
        assert mgr.get_default() is None

    def test_get_by_name_is_case_sensitive(self):
        mgr = RemoteRepoManager(FakeExtension([{"name": "Constructel"}]))
        assert mgr.get_by_name("Constructel") is not None
        assert mgr.get_by_name("constructel") is None


# ---------------------------------------------------------------------------
# End-to-end publish — real git against a local bare remote
# ---------------------------------------------------------------------------


pytestmark_needs_git = pytest.mark.skipif(
    not GIT_AVAILABLE, reason="git binary not available",
)


def _run(args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def seeded_bare(tmp_path):
    """Bare remote pre-seeded with an initial commit on ``main``."""
    bare = tmp_path / "origin.git"
    bare.mkdir()
    _run(["git", "init", "--bare", "-b", "main", str(bare)])

    seed = tmp_path / "_seed"
    seed.mkdir()
    _run(["git", "init", "-b", "main", str(seed)])
    _run(["git", "config", "user.email", "seed@example.com"], cwd=seed)
    _run(["git", "config", "user.name", "Seed"], cwd=seed)
    (seed / "README.md").write_text("seed\n")
    _run(["git", "add", "README.md"], cwd=seed)
    _run(["git", "commit", "-m", "seed"], cwd=seed)
    _run(["git", "remote", "add", "origin", str(bare)], cwd=seed)
    _run(["git", "push", "origin", "main"], cwd=seed)
    return bare


@pytest.mark.skipif(not GIT_AVAILABLE, reason="git binary not available")
class TestPublishBundleE2E:
    def _write_bundle_fn(self, content="{}\n"):
        def _write(collection_dir):
            os.makedirs(collection_dir, exist_ok=True)
            path = os.path.join(collection_dir, "favorites.fmfav-pack.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return path
        return _write

    def _make_manager(self, tmp_path, seeded_bare, *, is_default=True,
                       target_collection="acme"):
        entry = {
            "name": "Acme",
            "git_url": str(seeded_bare),
            "branch": "main",
            "local_clone": str(tmp_path / "clone"),
            "target_collection": target_collection,
            "is_default": is_default,
        }
        return RemoteRepoManager(FakeExtension([entry]))

    def test_publish_clones_then_commits_and_pushes(self, tmp_path, seeded_bare):
        mgr = self._make_manager(tmp_path, seeded_bare)
        repo = mgr.get_default()

        # Configure local identity so commit doesn't fail on fresh clone
        # (prepare_clone runs first, so we post-configure right after)
        sync = mgr.prepare_clone(repo)
        assert sync.success
        _run(["git", "config", "user.email", "t@example.com"], cwd=repo.expanded_local_clone)
        _run(["git", "config", "user.name", "T"], cwd=repo.expanded_local_clone)

        sync = mgr.publish_to_remote(
            repo, self._write_bundle_fn(content='{"v": 1}\n'),
        )
        assert sync.success, sync.error_message
        assert sync.pushed is True
        assert sync.commit_sha
        assert os.path.basename(sync.bundle_written_at) == "favorites.fmfav-pack.json"
        assert "collections/acme" in sync.bundle_written_at.replace("\\", "/")

        # Verify remote actually received the bundle
        verify_dir = tmp_path / "verify"
        _run(["git", "clone", str(seeded_bare), str(verify_dir)])
        assert (verify_dir / "collections" / "acme" / "favorites.fmfav-pack.json").exists()

    def test_publish_no_changes_is_a_success_but_skips_push(
        self, tmp_path, seeded_bare,
    ):
        """Re-running publish with identical content must not force-create an empty commit."""
        mgr = self._make_manager(tmp_path, seeded_bare)
        repo = mgr.get_default()

        mgr.prepare_clone(repo)
        _run(["git", "config", "user.email", "t@example.com"], cwd=repo.expanded_local_clone)
        _run(["git", "config", "user.name", "T"], cwd=repo.expanded_local_clone)

        # First publish lands a commit
        first = mgr.publish_to_remote(repo, self._write_bundle_fn('{"v": 1}\n'))
        assert first.pushed is True

        # Second publish with identical content → no-op
        second = mgr.publish_to_remote(repo, self._write_bundle_fn('{"v": 1}\n'))
        assert second.success is True
        assert second.pushed is False
        assert second.skipped_push_reason == "no_changes"

    def test_fallback_a_no_git_url_writes_locally_without_push(self, tmp_path):
        """Repo with empty git_url: write only, don't try to clone/push."""
        clone = tmp_path / "local_only"
        mgr = RemoteRepoManager(FakeExtension([{
            "name": "LocalOnly",
            "local_clone": str(clone),
            "target_collection": "coll",
        }]))
        repo = mgr.get_default()

        sync = mgr.publish_to_remote(repo, self._write_bundle_fn())
        assert sync.success is True
        assert sync.pushed is False
        assert sync.skipped_push_reason == "no_remote"
        assert os.path.isfile(sync.bundle_written_at)

    def test_bundle_write_exception_surfaces_as_error(self, tmp_path, seeded_bare):
        mgr = self._make_manager(tmp_path, seeded_bare)
        repo = mgr.get_default()
        mgr.prepare_clone(repo)

        def _boom(_collection_dir):
            raise IOError("disk full")

        sync = mgr.publish_to_remote(repo, _boom)
        assert sync.success is False
        assert "disk full" in sync.error_message
        # clone_path is surfaced so the UI can offer "Open clone"
        assert sync.clone_path


# ---------------------------------------------------------------------------
# CRUD: save_repos round-trip + serialization invariants
# ---------------------------------------------------------------------------


class TestSaveRepos:
    def test_save_repos_serializes_and_persists(self):
        ext = FakeExtension([])
        mgr = RemoteRepoManager(ext)

        repos = [
            RemoteRepo(name="A", git_url="https://x/a.git", authcfg_id="cfg1"),
            RemoteRepo(name="B", local_clone="/tmp/b", target_collection="coll"),
        ]
        assert mgr.save_repos(repos) is True
        assert ext.last_set_call[0] == "remote_repos"
        saved = ext.last_set_call[1]
        assert saved == [
            {"name": "A", "git_url": "https://x/a.git", "authcfg_id": "cfg1"},
            {"name": "B", "local_clone": "/tmp/b", "target_collection": "coll"},
        ]

    def test_save_repos_drops_legacy_auth_header_when_authcfg_set(self):
        """Migration path: when both fields exist, drop the plaintext one."""
        mgr = RemoteRepoManager(FakeExtension([]))
        repo = RemoteRepo(
            name="Migrated",
            git_url="https://x/a.git",
            auth_header="Bearer LEGACY",
            authcfg_id="cfg-new",
        )
        ext = FakeExtension([])
        mgr = RemoteRepoManager(ext)
        mgr.save_repos([repo])
        saved_entry = ext.last_set_call[1][0]
        assert saved_entry.get("authcfg_id") == "cfg-new"
        assert "auth_header" not in saved_entry

    def test_save_repos_keeps_legacy_auth_header_alone(self):
        """Without authcfg_id, the legacy header survives the round-trip."""
        ext = FakeExtension([])
        mgr = RemoteRepoManager(ext)
        repo = RemoteRepo(
            name="Old", git_url="https://x/a.git", auth_header="Bearer KEEP",
        )
        mgr.save_repos([repo])
        saved_entry = ext.last_set_call[1][0]
        assert saved_entry["auth_header"] == "Bearer KEEP"

    def test_save_repos_enforces_single_default(self):
        """Two is_default=True entries → only the first survives as default."""
        ext = FakeExtension([])
        mgr = RemoteRepoManager(ext)
        repos = [
            RemoteRepo(name="A", is_default=True),
            RemoteRepo(name="B", is_default=True),
        ]
        mgr.save_repos(repos)
        saved = ext.last_set_call[1]
        assert saved[0].get("is_default") is True
        # Second entry's is_default is dropped (falsy → omitted from dict)
        assert "is_default" not in saved[1]

    def test_save_repos_round_trip_via_list_repos(self):
        """save → list must yield the same set of repos."""
        ext = FakeExtension([])
        mgr = RemoteRepoManager(ext)
        original = [
            RemoteRepo(name="X", authcfg_id="cfg1"),
            RemoteRepo(name="Y", git_url="https://y.git", branch="main"),
        ]
        mgr.save_repos(original)
        round_tripped = mgr.list_repos()
        assert [r.name for r in round_tripped] == ["X", "Y"]
        assert round_tripped[0].authcfg_id == "cfg1"
        assert round_tripped[1].git_url == "https://y.git"

    def test_save_repos_returns_false_without_extension(self):
        """No extension → cannot persist, must report failure."""
        mgr = RemoteRepoManager(extension=None)
        assert mgr.save_repos([RemoteRepo(name="X")]) is False


# ---------------------------------------------------------------------------
# test_connection — used by the editor dialog's "Test connection" button
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not GIT_AVAILABLE, reason="git binary not available")
class TestTestConnection:
    def test_local_only_repo_is_considered_ready(self, tmp_path):
        """No git_url + writable path → success, skipped reason 'no_remote'."""
        clone = tmp_path / "local_only"
        mgr = RemoteRepoManager(FakeExtension([{
            "name": "Local",
            "local_clone": str(clone),
        }]))
        result = mgr.test_connection(mgr.get_default())
        assert result.success is True
        assert result.skipped_push_reason == "no_remote"

    def test_unreachable_remote_returns_error(self, tmp_path):
        """Bogus git URL must surface as a non-success with a stderr message."""
        mgr = RemoteRepoManager(FakeExtension([{
            "name": "Bogus",
            "git_url": "https://127.0.0.1:1/no-such-repo.git",
            "local_clone": str(tmp_path / "x"),
        }]))
        result = mgr.test_connection(mgr.get_default(), timeout=5)
        assert result.success is False
        assert result.error_message  # whatever git says, just non-empty


# ---------------------------------------------------------------------------
# Git binary plumbing — every GitClient must receive the resolved binary
# ---------------------------------------------------------------------------


class TestGitBinaryPlumbing:
    def test_default_uses_literal_git_when_unresolved(self, monkeypatch):
        """No configured path, no portable, no PATH → fallback "git" string.

        Preserves the legacy GitError envelope (returncode -2 with
        "git binary not found") so callers that match on it still work.
        """
        # Drop git off PATH for the duration of the test
        monkeypatch.setenv("PATH", "")
        mgr = RemoteRepoManager(FakeExtension([], git_binary_path=""))
        assert mgr._git_binary_or_default() == "git"

    def test_configured_path_propagated(self, tmp_path, monkeypatch):
        """A user-set git_binary_path must surface from the resolver."""
        # Make a fake executable file so the resolver accepts it
        fake = tmp_path / "custom-git"
        fake.write_text("#!/bin/sh\nexit 0\n")
        if os.name != "nt":
            os.chmod(fake, 0o755)

        mgr = RemoteRepoManager(
            FakeExtension([], git_binary_path=str(fake))
        )
        # The resolver should pick this up because configured wins over
        # portable / PATH whenever the file exists and is runnable.
        assert mgr._git_binary_or_default() == str(fake)

    def test_resolution_includes_source(self, tmp_path):
        """resolve_git_binary() exposes provenance for UI display."""
        fake = tmp_path / "g"
        fake.write_text("")
        if os.name != "nt":
            os.chmod(fake, 0o755)
        mgr = RemoteRepoManager(
            FakeExtension([], git_binary_path=str(fake))
        )
        res = mgr.resolve_git_binary()
        assert res.found
        assert res.binary_path == str(fake)

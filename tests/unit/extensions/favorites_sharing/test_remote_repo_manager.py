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
    RemoteRepo,
    RemoteRepoManager,
    RepoStatus,
)

GIT_AVAILABLE = shutil.which("git") is not None


# ---------------------------------------------------------------------------
# Fake extension: only needs get_remote_repos() for the manager
# ---------------------------------------------------------------------------


class FakeExtension:
    def __init__(self, repos):
        self._repos = list(repos)

    def get_remote_repos(self):
        return list(self._repos)


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

        sync = mgr.publish_bundle(
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
        first = mgr.publish_bundle(repo, self._write_bundle_fn('{"v": 1}\n'))
        assert first.pushed is True

        # Second publish with identical content → no-op
        second = mgr.publish_bundle(repo, self._write_bundle_fn('{"v": 1}\n'))
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

        sync = mgr.publish_bundle(repo, self._write_bundle_fn())
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

        sync = mgr.publish_bundle(repo, _boom)
        assert sync.success is False
        assert "disk full" in sync.error_message
        # clone_path is surfaced so the UI can offer "Open clone"
        assert sync.clone_path

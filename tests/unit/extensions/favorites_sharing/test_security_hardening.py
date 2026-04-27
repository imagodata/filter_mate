# -*- coding: utf-8 -*-
"""
Regression tests for the 2026-04-27 security audit hardening.

Covers:
- C1 — fork sanitizes the favorite expression before insertion.
- C2 — git argv carries an explicit ``--`` separator before positional URLs.
- C3 — scanner runs the validator on envelope bundles before yielding.
- H1 — symlinks that escape the collections root are rejected.
- H2 — ``target_collection`` with ``..`` traversal is refused.
- H3/H4 — atomic JSON write helper writes via temp + rename.
- M1/M2 — control characters are stripped from commit author and auth header.
"""

import json
import os
import sys
import types
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from extensions.favorites_sharing import path_utils
from extensions.favorites_sharing.git_client import (
    GitClient,
    _strip_control_chars,
)
from extensions.favorites_sharing.remote_repo_manager import RemoteRepo
from extensions.favorites_sharing.scanner import (
    ResourceSharingScanner,
    SharedFavorite,
    SharedFavoriteSource,
)
from extensions.favorites_sharing.service import FavoritesSharingService


# ─── C2: -- separator before positional URLs ─────────────────────────────


class _CapturingClient(GitClient):
    """GitClient subclass that records argv passed to ``_run`` instead of
    actually invoking subprocess. Lets us assert the exact argv shape."""

    last_args: List[str] = []

    def _run(self, args, *, cwd=None, timeout=None, check=True):  # type: ignore[override]
        type(self).last_args = list(args)
        from extensions.favorites_sharing.git_client import GitResult
        return GitResult(ok=True)


def test_clone_inserts_double_dash_before_url(tmp_path):
    client = _CapturingClient(cwd=str(tmp_path / "repo"))
    client.clone("https://example.com/x.git", branch="main")
    args = _CapturingClient.last_args
    assert "--" in args
    sep_idx = args.index("--")
    # After the separator: url, then destination
    assert args[sep_idx + 1] == "https://example.com/x.git"
    assert args[sep_idx + 2] == str(tmp_path / "repo")


def test_push_inserts_double_dash_before_remote(tmp_path):
    (tmp_path / ".git").mkdir()  # cwd validity not strictly required for capture
    client = _CapturingClient(cwd=str(tmp_path))
    client.push(remote="origin", branch="main")
    args = _CapturingClient.last_args
    assert args[:2] == ["push", "--"]
    assert "origin" in args
    assert "main" in args


def test_ls_remote_inserts_double_dash_before_url(tmp_path):
    client = _CapturingClient(cwd=str(tmp_path))
    client.ls_remote("https://example.com/x.git")
    args = _CapturingClient.last_args
    assert args[0] == "ls-remote"
    assert args[-2] == "--"
    assert args[-1] == "https://example.com/x.git"


# ─── M1/M2: control-char stripping ───────────────────────────────────────


def test_strip_control_chars_drops_newlines():
    raw = "Bearer foo\n[remote \"x\"]\nurl=evil"
    cleaned = _strip_control_chars(raw)
    assert "\n" not in cleaned
    assert "[remote" in cleaned  # content preserved, just no newlines


def test_strip_control_chars_keeps_tabs_and_printable():
    assert _strip_control_chars("hello\tworld") == "hello\tworld"
    assert _strip_control_chars("simple") == "simple"


def test_strip_control_chars_handles_empty():
    assert _strip_control_chars("") == ""


def test_commit_author_newline_is_stripped(tmp_path):
    client = _CapturingClient(cwd=str(tmp_path))
    poisoned = "Alice <a@x>\nGPG-SIG: forged"
    client.commit("msg", author=poisoned)
    args = _CapturingClient.last_args
    # --author value comes right after the flag
    author_idx = args.index("--author")
    assert "\n" not in args[author_idx + 1]


def test_auth_header_newline_is_stripped(tmp_path):
    """``_run`` injects the auth header — patch ``subprocess.run`` so we
    can observe the final argv that would have hit git."""
    captured: Dict[str, Any] = {}

    class _FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return _FakeProc()

    client = GitClient(
        cwd=str(tmp_path),
        auth_header="Bearer token\n[remote \"x\"]\nurl=evil",
    )
    with patch("extensions.favorites_sharing.git_client.subprocess.run", _fake_run):
        client.commit("msg")

    cmd = captured["cmd"]
    ec_args = [a for a in cmd if a.startswith("http.extraHeader=")]
    assert ec_args, "expected http.extraHeader injection"
    assert "\n" not in ec_args[0]
    assert "[remote" in ec_args[0]  # other content survives, just no newline


# ─── C3: validator runs on scanner load ──────────────────────────────────


def test_scanner_rejects_envelope_with_missing_favorites(tmp_path):
    root = tmp_path / "collections"
    favdir = root / "x" / "filter_mate" / "favorites"
    favdir.mkdir(parents=True)
    # Envelope without 'favorites' key — but we declare schema-shape so the
    # scanner enters the envelope branch and the validator should reject it.
    (favdir / "bad.fmfav.json").write_text(json.dumps({
        "schema": "filter_mate.favorites",
        "favorites": "not a list",
    }))
    (favdir / "good.fmfav-pack.json").write_text(json.dumps({
        "schema": "filter_mate.favorites",
        "favorites": [{"name": "OK", "expression": "TRUE"}],
    }))
    scanner = ResourceSharingScanner(collections_root=str(root))
    items = scanner.scan()
    names = {f.name for f in items}
    assert names == {"OK"}


def test_scanner_rejects_envelope_with_invalid_favorite(tmp_path):
    root = tmp_path / "collections"
    favdir = root / "x" / "filter_mate" / "favorites"
    favdir.mkdir(parents=True)
    (favdir / "bad.fmfav-pack.json").write_text(json.dumps({
        "schema": "filter_mate.favorites",
        "favorites": [{"name": "", "expression": "TRUE"}],  # empty name → invalid
    }))
    scanner = ResourceSharingScanner(collections_root=str(root))
    assert scanner.scan() == []


# ─── H1: symlink escape rejected ─────────────────────────────────────────


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="symlinks need elevated privileges on Windows CI",
)
def test_scanner_rejects_symlink_escaping_root(tmp_path):
    outside = tmp_path / "outside" / "filter_mate" / "favorites"
    outside.mkdir(parents=True)
    (outside / "leak.fmfav.json").write_text(json.dumps({
        "name": "Leak", "expression": "TRUE",
    }))

    root = tmp_path / "collections"
    root.mkdir()
    # A symlink with a benign name pointing to an attacker-controlled tree
    (root / "innocent").symlink_to(tmp_path / "outside", target_is_directory=True)

    scanner = ResourceSharingScanner(collections_root=str(root))
    items = scanner.scan()
    assert items == []  # symlink resolution drops the escape


# ─── H2: target_collection traversal rejected ────────────────────────────


def test_remote_repo_collection_dir_refuses_traversal(tmp_path):
    repo = RemoteRepo(
        name="acme",
        local_clone=str(tmp_path / "clone"),
        target_collection="../../../etc",
    )
    # Even though local_clone doesn't exist yet, the safe-join check on
    # the abstract path must refuse the escape.
    assert repo.collection_dir == ""


def test_remote_repo_collection_dir_accepts_clean_subdir(tmp_path):
    repo = RemoteRepo(
        name="acme",
        local_clone=str(tmp_path / "clone"),
        target_collection="my-collection",
    )
    cd = repo.collection_dir
    assert cd
    assert cd.endswith(os.path.join("collections", "my-collection"))


# ─── H3/H4: atomic JSON write ────────────────────────────────────────────


def test_atomic_json_write_creates_target(tmp_path):
    target = tmp_path / "out.json"
    path_utils.atomic_json_write(str(target), {"k": 1})
    assert target.exists()
    assert json.loads(target.read_text()) == {"k": 1}


def test_atomic_json_write_no_temp_left_on_success(tmp_path):
    target = tmp_path / "out.json"
    path_utils.atomic_json_write(str(target), {"k": 1})
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".fmfav_")]
    assert leftovers == []


def test_atomic_json_write_overwrites_existing(tmp_path):
    target = tmp_path / "out.json"
    target.write_text('{"old": true}')
    path_utils.atomic_json_write(str(target), {"new": True})
    assert json.loads(target.read_text()) == {"new": True}


# ─── safe_join_under primitive ───────────────────────────────────────────


def test_safe_join_under_blocks_dotdot(tmp_path):
    assert path_utils.safe_join_under(str(tmp_path), "..", "etc") is None


def test_safe_join_under_returns_inside_path(tmp_path):
    out = path_utils.safe_join_under(str(tmp_path), "sub", "child")
    assert out is not None
    assert out.startswith(str(tmp_path))


# ─── C1: fork sanitizes expression ───────────────────────────────────────


@pytest.fixture
def _fake_filter_mate_modules(monkeypatch):
    """Stub the ``filter_mate.core.*`` namespace so service.fork can import
    without a running QGIS. Forces a clean slate on every entry: any prior
    test that loaded the real modules under that namespace would otherwise
    leak through and break our assertions.

    Returns ``(FilterFavorite_cls, captured_kwargs)``.
    """
    # Wipe any previously-cached filter_mate.* entries — pytest collects
    # tests across packages and earlier ones may have imported the real
    # implementation, leaving live references in sys.modules.
    for cached in [k for k in list(sys.modules) if k == "filter_mate" or k.startswith("filter_mate.")]:
        monkeypatch.delitem(sys.modules, cached, raising=False)

    fm_pkg = types.ModuleType("filter_mate")
    core_pkg = types.ModuleType("filter_mate.core")
    services_pkg = types.ModuleType("filter_mate.core.services")
    domain_pkg = types.ModuleType("filter_mate.core.domain")
    filter_pkg = types.ModuleType("filter_mate.core.filter")
    fav_svc_mod = types.ModuleType("filter_mate.core.services.favorites_service")
    fav_mgr_mod = types.ModuleType("filter_mate.core.domain.favorites_manager")

    # Re-export the REAL sanitizer so fork's sanitization step runs end-to-end.
    from core.filter import sanitize_subset_string as _real_sanitize  # noqa: WPS433
    filter_pkg.sanitize_subset_string = _real_sanitize  # type: ignore[attr-defined]

    class _FavoritesService:
        @staticmethod
        def _rebind_imported_favorite(payload, schema_version):
            # Pass-through for the test — keeps the expression intact.
            return dict(payload)

    captured: Dict[str, Any] = {}

    class _FilterFavorite:
        id: Any = None
        name: str = ""

        def __init__(self) -> None:
            self.id = None
            self.name = ""

        @classmethod
        def from_dict(cls, payload):
            inst = cls()
            inst.name = payload.get("name") or ""
            captured["expression"] = payload.get("expression")
            captured["payload"] = payload
            return inst

    fav_svc_mod.FavoritesService = _FavoritesService  # type: ignore[attr-defined]
    fav_mgr_mod.FilterFavorite = _FilterFavorite  # type: ignore[attr-defined]
    fm_pkg.core = core_pkg  # type: ignore[attr-defined]
    core_pkg.services = services_pkg  # type: ignore[attr-defined]
    core_pkg.domain = domain_pkg  # type: ignore[attr-defined]
    core_pkg.filter = filter_pkg  # type: ignore[attr-defined]
    services_pkg.favorites_service = fav_svc_mod  # type: ignore[attr-defined]
    domain_pkg.favorites_manager = fav_mgr_mod  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "filter_mate", fm_pkg)
    monkeypatch.setitem(sys.modules, "filter_mate.core", core_pkg)
    monkeypatch.setitem(sys.modules, "filter_mate.core.services", services_pkg)
    monkeypatch.setitem(sys.modules, "filter_mate.core.domain", domain_pkg)
    monkeypatch.setitem(sys.modules, "filter_mate.core.filter", filter_pkg)
    monkeypatch.setitem(
        sys.modules, "filter_mate.core.services.favorites_service", fav_svc_mod
    )
    monkeypatch.setitem(
        sys.modules, "filter_mate.core.domain.favorites_manager", fav_mgr_mod
    )
    return _FilterFavorite, captured


def _make_shared(payload):
    src = SharedFavoriteSource(
        file_path="/tmp/fake.fmfav.json",
        collection_name="acme",
        collection_metadata={},
    )
    return SharedFavorite(payload=dict(payload), source=src)


def test_fork_refuses_standalone_display_expression(_fake_filter_mate_modules):
    _, captured = _fake_filter_mate_modules
    # A standalone COALESCE display expression — sanitizer returns ''
    shared = _make_shared({
        "name": "Bad",
        "expression": "COALESCE(\"identifier\", '<NULL>')",
    })
    svc = FavoritesSharingService(scanner=MagicMock())
    fav_service = MagicMock()
    fav_service.favorites_manager = MagicMock()
    fav_service.favorites_manager.add_favorite = MagicMock(return_value=True)

    result = svc.fork(shared, fav_service)
    assert result is None
    # add_favorite must not have been called — fork should refuse before insert
    fav_service.favorites_manager.add_favorite.assert_not_called()


def test_fork_passes_clean_expression_through(_fake_filter_mate_modules):
    _, captured = _fake_filter_mate_modules
    shared = _make_shared({
        "name": "Good",
        "expression": "\"x\" = 1",
    })
    svc = FavoritesSharingService(scanner=MagicMock())
    fav_service = MagicMock()
    fav_service.favorites_manager = MagicMock()
    fav_service.favorites_manager.add_favorite = MagicMock(return_value=True)

    result = svc.fork(shared, fav_service)
    # The captured expression must have reached from_dict (sanitizer kept it).
    assert captured["expression"] == "\"x\" = 1"
    fav_service.favorites_manager.add_favorite.assert_called_once()

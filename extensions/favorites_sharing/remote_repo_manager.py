# -*- coding: utf-8 -*-
"""
Remote repo manager — git-backed publish targets for favorite collections.

Turns raw ``remote_repos`` config entries into typed ``RemoteRepo``
objects, exposes helpers for the publish UI (default pick, status badge)
and orchestrates the end-to-end git flow on publish:

    clone if missing → pull --ff-only → (caller writes bundle) → add →
    commit → push

The manager never auto-rebases or force-pushes. Conflicts are surfaced
to the UI so the user can resolve in their own tooling.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .git_client import GitClient, GitError, GitResult

logger = logging.getLogger('FilterMate.FavoritesSharing.RemoteRepo')


def _profile_repos_root() -> str:
    """Return the standard parent directory for FilterMate-managed clones.

    Convention (v5.1): clones live under the QGIS roaming profile dir —
    specifically ``PLUGIN_CONFIG_DIRECTORY/repos``. This keeps them
    co-located with ``config.json`` and ``filterMate_db.sqlite`` and
    survives a plugin reinstall (the plugin folder itself may be wiped
    when QGIS updates the plugin).

    Returns an empty string when the plugin env has not been initialised
    yet (tests, standalone imports). Callers must handle the empty case.
    """
    try:
        from filter_mate.config.config import ENV_VARS
    except Exception:
        return ""
    base = ENV_VARS.get("PLUGIN_CONFIG_DIRECTORY") or ""
    if not base:
        return ""
    return os.path.join(base, "repos")


def _slugify_repo_name(name: str) -> str:
    """Make a repo name safe for use as a filesystem directory.

    Only ``[A-Za-z0-9._-]`` survive; everything else becomes ``_``.
    Empty input yields ``repo`` to guarantee a non-empty path segment.
    """
    if not name:
        return "repo"
    safe = []
    for ch in name:
        if ch.isalnum() or ch in "._-":
            safe.append(ch)
        else:
            safe.append("_")
    slug = "".join(safe).strip("._-") or "repo"
    return slug.lower()


class RepoStatus(Enum):
    """Disk-level status of a configured repo."""

    NOT_CLONED = "not_cloned"   # local_clone directory is absent
    CLONED = "cloned"            # local_clone exists + is a git tree
    LOCAL_ONLY = "local_only"    # no git_url → fallback A (write only)
    UNKNOWN = "unknown"          # config entry cannot be resolved


@dataclass
class RemoteRepo:
    """One configured publish target (validated entry)."""

    name: str
    git_url: str = ""
    branch: str = ""
    local_clone: str = ""
    target_collection: str = ""
    is_default: bool = False
    auth_header: str = ""
    # Forward-compatible catch-all for unknown fields
    extra: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def expanded_local_clone(self) -> str:
        """Resolve ``local_clone`` to an absolute path.

        Resolution rules (v5.1, user-locked 2026-04-23):

        - Empty → default to ``[profile]/FilterMate/repos/<name>`` so new
          installs don't need to pick a path. This keeps all FilterMate
          state (config, SQLite, repos) under the QGIS roaming profile
          dir, never inside the plugin folder itself (which gets wiped
          on plugin updates).
        - Relative (no leading ``/``, ``\\``, drive letter, or ``~``) →
          resolved relative to the same profile dir (``repos/acme`` →
          ``[profile]/FilterMate/repos/acme``).
        - Absolute or ``~``-prefixed → kept as-is, expanded. Use this
          for shared network mounts or explicit overrides.
        """
        raw = (self.local_clone or "").strip()

        # Empty → derive from the repo name under the profile's repos dir
        if not raw:
            root = _profile_repos_root()
            if not root:
                return ""
            return os.path.join(root, _slugify_repo_name(self.name))

        # Expand ~ and env vars first — user-provided absolute paths win
        expanded = os.path.expandvars(os.path.expanduser(raw))

        # Relative paths are anchored at the profile's repos dir rather
        # than the current working dir (which is QGIS' runtime cwd, a
        # terrible anchor). Users who truly want cwd-relative should
        # pass an absolute path.
        if not os.path.isabs(expanded):
            root = _profile_repos_root()
            if root:
                expanded = os.path.join(root, expanded)

        return os.path.abspath(expanded)

    @property
    def collection_dir(self) -> str:
        """Absolute path to the collection sub-directory inside the clone."""
        root = self.expanded_local_clone
        if not root:
            return ""
        if self.target_collection:
            return os.path.join(root, "collections", self.target_collection)
        # When target_collection is omitted, assume the repo *is* the
        # collection root (rare, but supported for single-collection repos).
        return root

    @property
    def has_remote(self) -> bool:
        return bool(self.git_url)

    def status(self) -> RepoStatus:
        local = self.expanded_local_clone
        if not local:
            return RepoStatus.UNKNOWN
        has_git_dir = os.path.isdir(os.path.join(local, ".git"))
        if has_git_dir:
            return RepoStatus.CLONED
        if not self.has_remote and os.path.isdir(local):
            return RepoStatus.LOCAL_ONLY
        return RepoStatus.NOT_CLONED

    def status_badge(self) -> str:
        """UI-friendly short label for the repo's current state."""
        s = self.status()
        return {
            RepoStatus.CLONED: "🟢 ready",
            RepoStatus.NOT_CLONED: "⚪ not cloned",
            RepoStatus.LOCAL_ONLY: "📁 local only",
            RepoStatus.UNKNOWN: "⚠ invalid",
        }[s]

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config_entry(cls, entry: Dict[str, Any]) -> Optional["RemoteRepo"]:
        """Parse a raw config dict into a validated repo.

        Returns None when the entry is missing the required ``name`` or
        when ``local_clone`` is unresolvable (all other fields are
        optional — absent ``git_url`` switches to fallback A).
        """
        if not isinstance(entry, dict):
            return None
        name = str(entry.get("name") or "").strip()
        if not name:
            return None

        known = {
            "name", "git_url", "branch", "local_clone",
            "target_collection", "is_default", "auth_header",
        }
        extra = {k: v for k, v in entry.items() if k not in known}

        return cls(
            name=name,
            git_url=str(entry.get("git_url") or "").strip(),
            branch=str(entry.get("branch") or "").strip(),
            local_clone=str(entry.get("local_clone") or "").strip(),
            target_collection=str(entry.get("target_collection") or "").strip(),
            is_default=bool(entry.get("is_default") or False),
            auth_header=str(entry.get("auth_header") or "").strip(),
            extra=extra,
        )


@dataclass
class RepoSyncResult:
    """Outcome of a publish to a RemoteRepo."""
    success: bool = False
    repo_name: str = ""
    bundle_written_at: str = ""
    commit_sha: str = ""
    pushed: bool = False
    skipped_push_reason: str = ""  # "no_remote" (fallback A), "no_changes", …
    error_message: str = ""
    clone_path: str = ""            # surfaced so UI can offer "Open clone"


class RemoteRepoManager:
    """
    Resolve configured repos + orchestrate the publish git flow.

    The manager does not write bundle files itself — it delegates to a
    caller-provided callable (``write_bundle``) that takes the
    destination collection dir and returns the absolute bundle path.
    Keeping the write step outside means we never accidentally wrap a
    non-git concern in the git-failure envelope.
    """

    DEFAULT_COMMIT_AUTHOR = "FilterMate <filter_mate@imagodata.local>"

    def __init__(self, extension):
        """
        Args:
            extension: Owning ``FavoritesSharingExtension`` — used to
                read ``remote_repos`` from config.
        """
        self._extension = extension

    # ------------------------------------------------------------------
    # Config lookup
    # ------------------------------------------------------------------

    def list_repos(self) -> List[RemoteRepo]:
        """Return the configured repos (validated, order preserved)."""
        entries = []
        try:
            entries = self._extension.get_remote_repos()
        except Exception as exc:
            logger.debug("Cannot read remote_repos from config: %s", exc)
            return []

        repos: List[RemoteRepo] = []
        for entry in entries:
            repo = RemoteRepo.from_config_entry(entry)
            if repo is not None:
                repos.append(repo)
        return repos

    def get_default(self) -> Optional[RemoteRepo]:
        """Pick the default repo.

        Priority:
            1. The first entry with ``is_default: true``.
            2. The first entry (any).
        """
        repos = self.list_repos()
        if not repos:
            return None
        for r in repos:
            if r.is_default:
                return r
        return repos[0]

    def get_by_name(self, name: str) -> Optional[RemoteRepo]:
        """Case-sensitive lookup by ``name``."""
        for r in self.list_repos():
            if r.name == name:
                return r
        return None

    # ------------------------------------------------------------------
    # Publish orchestration
    # ------------------------------------------------------------------

    def prepare_clone(self, repo: RemoteRepo) -> RepoSyncResult:
        """Clone or fast-forward pull the repo's local clone.

        Fallback A: when ``git_url`` is empty and ``local_clone`` exists,
        return success immediately (caller will write locally, user pushes
        manually). When ``git_url`` is empty AND the clone is missing,
        we create the directory so the bundle has somewhere to land.
        """
        result = RepoSyncResult(
            repo_name=repo.name,
            clone_path=repo.expanded_local_clone,
        )

        if not repo.expanded_local_clone:
            result.error_message = "local_clone is empty in config"
            return result

        # Fallback A — no remote
        if not repo.has_remote:
            try:
                os.makedirs(repo.expanded_local_clone, exist_ok=True)
            except OSError as exc:
                result.error_message = f"cannot create local_clone: {exc}"
                return result
            result.success = True
            result.skipped_push_reason = "no_remote"
            return result

        client = GitClient(
            cwd=repo.expanded_local_clone,
            auth_header=repo.auth_header or None,
        )

        try:
            if not client.is_cloned():
                logger.info(
                    "Cloning %s → %s (branch=%s)",
                    repo.git_url, repo.expanded_local_clone, repo.branch or "<default>",
                )
                client.clone(repo.git_url, branch=repo.branch or None)
            else:
                logger.info("Fast-forward pull on %s", repo.expanded_local_clone)
                client.pull_fast_forward()
        except GitError as exc:
            result.error_message = str(exc)
            return result

        result.success = True
        return result

    def publish_bundle(
        self,
        repo: RemoteRepo,
        write_bundle,
        commit_author: Optional[str] = None,
    ) -> RepoSyncResult:
        """
        Run the full publish flow for a single repo.

        Args:
            repo: Target repo (validated via ``from_config_entry``).
            write_bundle: Callable ``(collection_dir: str) -> str`` that
                writes the bundle file and returns its absolute path.
                Any exception it raises is captured into the result.
            commit_author: Override for git author, e.g. "Team <email>".
                When None, falls back to ``DEFAULT_COMMIT_AUTHOR``.

        Returns:
            RepoSyncResult — on failure ``error_message`` is set and
            ``clone_path`` points at the local clone for manual recovery.
        """
        # Step 1 — clone or ff-pull
        sync = self.prepare_clone(repo)
        if not sync.success:
            return sync
        sync.success = False  # reset; only final success flips it back

        # Step 2 — caller writes bundle into the collection dir
        collection_dir = repo.collection_dir
        if not collection_dir:
            sync.error_message = "resolved collection_dir is empty"
            return sync
        try:
            os.makedirs(collection_dir, exist_ok=True)
        except OSError as exc:
            sync.error_message = f"cannot create collection_dir: {exc}"
            return sync

        try:
            bundle_path = write_bundle(collection_dir)
        except Exception as exc:
            sync.error_message = f"bundle write failed: {exc}"
            return sync
        sync.bundle_written_at = bundle_path or ""

        # Fallback A — no remote, we're done after writing
        if not repo.has_remote:
            sync.success = True
            sync.skipped_push_reason = "no_remote"
            return sync

        # Step 3 — git add / commit / push
        client = GitClient(
            cwd=repo.expanded_local_clone,
            auth_header=repo.auth_header or None,
        )

        try:
            client.add([bundle_path])
            if not client.has_staged_changes():
                sync.success = True
                sync.skipped_push_reason = "no_changes"
                return sync

            # Commit message includes bundle basename + collection slug
            msg = (
                f"filter_mate: publish "
                f"{os.path.basename(bundle_path)} to "
                f"{repo.target_collection or 'root'}"
            )
            client.commit(
                msg,
                author=commit_author or self.DEFAULT_COMMIT_AUTHOR,
            )
            sync.commit_sha = client.head_sha() or ""

            branch = repo.branch or client.current_branch() or ""
            client.push(remote="origin", branch=branch or None)
            sync.pushed = True

        except GitError as exc:
            sync.error_message = str(exc)
            return sync

        sync.success = True
        return sync

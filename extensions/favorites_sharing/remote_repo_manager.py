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
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .git_client import GitClient, GitError, _scrub_text
from .git_resolver import GitResolution, resolve_for_extension


def _repo_path(url: str) -> str:
    """The repository path of a git URL, without scheme, host, port, user or ``.git``: same path, same
    repository under another address. Pure (unit tests read it)."""
    from urllib.parse import urlsplit
    text = (url or "").strip()
    if not text:
        return ""
    path = text
    if "://" not in text and ":" in text and "/" not in text.split(":")[0]:
        path = text.split(":", 1)[1]  # scp-like user@host:path first: urlsplit reads it as scheme://host/path
    else:
        parsed = urlsplit(text if "://" in text else f"scheme://{text}")
        if parsed.hostname:
            path = parsed.path or ""
    path = path.strip().rstrip("/")
    if path.lower().endswith(".git"):
        path = path[:-4]
    return path.strip("/") or text.strip()


logger = logging.getLogger('FilterMate.FavoritesSharing.RemoteRepo')

# The plaintext ``auth_header`` of FilterMate 4.x repo entries is refused
# since 5.0.0 (audit EXT-6): the token is never used, an error tells the user
# to move it to the QGIS Authentication Manager (``authcfg_id``), and the
# next save removes it from config.json. The repo entry itself is kept.
PLAINTEXT_AUTH_REMOVED_IN = "5.0.0"

# Repos already reported. Re-parsing the same config (e.g. on every
# save_repos round-trip) would otherwise log one error per read.
_PLAINTEXT_AUTH_REPORTED: set = set()

# Fallbacks used only when a repo entry leaves ``bundle_name`` or
# ``commit_email`` empty: everything else comes from the entry itself.
DEFAULT_BUNDLE_NAME = "favorites"
DEFAULT_COMMIT_NAME = "FilterMate"
DEFAULT_COMMIT_EMAIL = "filter_mate@imagodata.local"

# ASCII ``local@domain``: the local part with the usual unquoted characters
# (not starting with ``-``), the domain as dot-separated labels.
_COMMIT_EMAIL_RE = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~][A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]*"
    r"@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*"
)


def _text_field(entry: Dict[str, Any], key: str, repo_name: str) -> str:
    """String value of ``key`` in a repo entry; another type is ignored (logged)."""
    value = entry.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        logger.warning("Repo %r: %s must be text, got %r; ignored", repo_name, key, value)
        return ""
    return value.strip()


def is_valid_commit_email(value: str) -> bool:
    """True for a single ASCII ``local@domain`` address, as git records it."""
    return bool(_COMMIT_EMAIL_RE.fullmatch((value or "").strip()))


def is_valid_bundle_name(value: str) -> bool:
    """True when the bundle file name is written as typed: letters, digits, ``_`` and ``-``.

    Same rule as ``BundlePublisher.sanitize_bundle_filename``, which replaces
    any other character with ``_``.
    """
    value = (value or "").strip()
    return bool(value) and all(c.isalnum() or c in "_-" for c in value)


def _commit_name(author_name: str) -> str:
    """Author name for git: an ``<email>`` typed in the Author field is dropped.

    The e-mail of the commit is the repo's; git would otherwise record the
    first ``<…>`` of the string. Control characters are removed, and a name
    left empty (or only ``<``) falls back to ``DEFAULT_COMMIT_NAME``.
    """
    name = (author_name or "").split("<", 1)[0]
    name = "".join(c for c in name if c.isprintable()).strip()
    return name or DEFAULT_COMMIT_NAME


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
        from ...config.config import ENV_VARS
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
    """One configured publish target (validated entry).

    Authentication is stored as ``authcfg_id`` only — a reference to a
    QGIS Auth Manager entry that ships an encrypted PAT/Basic credential.
    The plaintext ``auth_header`` of 4.x entries is refused since
    FilterMate 5.0.0 (see ``from_config_entry``).
    """

    name: str
    git_url: str = ""
    branch: str = ""
    local_clone: str = ""
    target_collection: str = ""
    is_default: bool = False
    # References an entry in QgsAuthManager. Encrypted at rest.
    authcfg_id: str = ""
    # File name of the published bundle (empty = DEFAULT_BUNDLE_NAME)
    bundle_name: str = ""
    # E-mail of the publish commits (empty = DEFAULT_COMMIT_EMAIL)
    commit_email: str = ""
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
        """Absolute path to the collection sub-directory inside the clone.

        ``target_collection`` originates from config and may be edited by
        users — guard against ``..`` traversal that would land bundles
        outside the working clone (and outside the git index, breaking
        ``git add`` while still creating attacker-controlled directories).
        """
        root = self.expanded_local_clone
        if not root:
            return ""
        if self.target_collection:
            from .path_utils import safe_join_under
            safe = safe_join_under(root, "collections", self.target_collection)
            if safe is None:
                logger.warning(
                    "target_collection %r escapes local_clone %r — refusing",
                    self.target_collection, root,
                )
                return ""
            return safe
        # When target_collection is omitted, assume the repo *is* the
        # collection root (rare, but supported for single-collection repos).
        return root

    @property
    def has_remote(self) -> bool:
        return bool(self.git_url)

    @property
    def effective_bundle_name(self) -> str:
        """Bundle file name of this repo, ``DEFAULT_BUNDLE_NAME`` when unset."""
        return self.bundle_name or DEFAULT_BUNDLE_NAME

    def commit_author(self, author_name: str = "") -> str:
        """``"Name <email>"`` for the publish commits to this repo.

        The e-mail is the repo's ``commit_email``; an invalid one (edited
        by hand in config.json) is ignored for ``DEFAULT_COMMIT_EMAIL``.
        """
        email = self.commit_email
        if email and not is_valid_commit_email(email):
            logger.warning(
                "Repo %r: commit_email %r is not an e-mail address, using %s",
                self.name, email, DEFAULT_COMMIT_EMAIL,
            )
            email = ""
        return f"{_commit_name(author_name)} <{email or DEFAULT_COMMIT_EMAIL}>"

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
            "target_collection", "is_default", "authcfg_id", "auth_header",
            "bundle_name", "commit_email",
        }
        extra = {k: v for k, v in entry.items() if k not in known}

        # "auth_header" is a known key: never kept in ``extra``, so the next
        # save drops the plaintext token from config.json.
        if str(entry.get("auth_header") or "").strip() and name not in _PLAINTEXT_AUTH_REPORTED:
            logger.error(
                "Repo %r: the plaintext auth_header in config.json is refused since "
                "FilterMate %s and is not used. Store the token in the QGIS "
                "Authentication Manager and select it in Manage Repos → Edit → "
                "Authentication; the next save removes it from config.json.",
                name, PLAINTEXT_AUTH_REMOVED_IN,
            )
            _PLAINTEXT_AUTH_REPORTED.add(name)

        return cls(
            name=name,
            git_url=str(entry.get("git_url") or "").strip(),
            branch=str(entry.get("branch") or "").strip(),
            local_clone=str(entry.get("local_clone") or "").strip(),
            target_collection=str(entry.get("target_collection") or "").strip(),
            is_default=bool(entry.get("is_default") or False),
            authcfg_id=str(entry.get("authcfg_id") or "").strip(),
            bundle_name=_text_field(entry, "bundle_name", name),
            commit_email=_text_field(entry, "commit_email", name),
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

    DEFAULT_COMMIT_AUTHOR = f"{DEFAULT_COMMIT_NAME} <{DEFAULT_COMMIT_EMAIL}>"

    def __init__(self, extension):
        """
        Args:
            extension: Owning ``FavoritesSharingExtension`` — used to
                read ``remote_repos`` from config.
        """
        self._extension = extension

    # ------------------------------------------------------------------
    # Git binary resolution — feeds every GitClient we spawn so a user
    # who set EXTENSIONS.favorites_sharing.git_binary_path or installed
    # Portable Git via the UI is honored without restarting QGIS.
    # ------------------------------------------------------------------

    def resolve_git_binary(self) -> GitResolution:
        """Re-resolve the git binary on every call.

        We don't memoize because the user may install Portable Git or
        flip ``git_binary_path`` mid-session via the dialog and expect
        the next publish to honor it. Resolution is cheap (a few stat
        calls + a PATH lookup).
        """
        if self._extension is None:
            return resolve_for_extension(None)  # falls through to MISSING
        return resolve_for_extension(self._extension)

    def _git_binary_or_default(self) -> str:
        """Best-effort binary string for ``GitClient.git_binary``.

        Returns the resolved path when found, or the literal ``"git"``
        when nothing matched — so existing call sites keep their old
        behavior (subprocess fails with the same FileNotFoundError that
        ``GitClient._run`` already wraps as ``GitError`` returncode -2).
        That preserves the legacy error envelope for callers that still
        match on ``"git binary not found"``.
        """
        res = self.resolve_git_binary()
        return res.binary_path or "git"

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
    # CRUD — persist back into EXTENSIONS.favorites_sharing.remote_repos
    # ------------------------------------------------------------------

    def purge_plaintext_auth(self, persist: bool = True) -> bool:
        """Remove the refused plaintext ``auth_header`` of 4.x entries from the config.

        Refused (never used) since 5.0.0, it stayed on disk until the user
        saved the repo list. Only that key goes; every entry is kept as is.
        ``persist=False``: the live config only (the caller writes it).
        Returns True when the config changed.
        """
        if self._extension is None or not hasattr(self._extension, "set_config"):
            return False
        try:
            raw = self._extension.get_config("remote_repos", default=[])
        except Exception as exc:
            logger.debug("Cannot read remote_repos from config: %s", exc)
            return False
        if not isinstance(raw, list):
            return False
        legacy = [entry for entry in raw if isinstance(entry, dict) and "auth_header" in entry]
        if not legacy:
            return False
        names = [str(entry.get("name") or "?") for entry in legacy if str(entry.get("auth_header") or "").strip()]
        if names:
            logger.error(
                "Repos %s: the plaintext auth_header in config.json is refused since FilterMate %s "
                "and has been removed from config.json. Store the token in the QGIS Authentication "
                "Manager and select it in Manage Repos → Edit → Authentication.",
                ", ".join(repr(name) for name in names), PLAINTEXT_AUTH_REMOVED_IN,
            )
            _PLAINTEXT_AUTH_REPORTED.update(names)
        cleaned = [{k: v for k, v in entry.items() if k != "auth_header"} if isinstance(entry, dict) else entry
                   for entry in raw]
        return bool(self._extension.set_config("remote_repos", cleaned, persist=persist))

    def save_repos(self, repos: List[RemoteRepo]) -> bool:
        """Persist the given list of repos to FilterMate config.

        Replaces the entire ``remote_repos`` list with the provided one
        (intentional — the dialog edits the full set in one shot, and
        we don't want orphan keys lingering on disk when a repo is
        removed). Empty fields are dropped to keep config.json compact.

        Returns True when the underlying ``set_config`` call succeeded.
        """
        if self._extension is None or not hasattr(self._extension, "set_config"):
            logger.warning("Cannot persist repos: no extension wired")
            return False

        # Enforce: at most one default. If multiple are flagged, keep the
        # first; this matches the get_default() pick-order so the UI is
        # consistent across the round-trip.
        seen_default = False
        normalized: List[Dict[str, Any]] = []
        for repo in repos:
            entry = self._serialize_repo(repo)
            if entry.get("is_default"):
                if seen_default:
                    # Demote duplicates by *removing* the key — keeps the
                    # serialized JSON minimal (omit-when-false is our
                    # convention) and matches what list_repos sees on
                    # the way back in.
                    entry.pop("is_default", None)
                else:
                    seen_default = True
            normalized.append(entry)

        return bool(self._extension.set_config("remote_repos", normalized))

    @staticmethod
    def _serialize_repo(repo: RemoteRepo) -> Dict[str, Any]:
        """Turn a RemoteRepo back into a config-shaped dict.

        Drops empty fields; a plaintext ``auth_header`` is never written
        (refused since FilterMate 5.0.0).
        """
        entry: Dict[str, Any] = {"name": repo.name}
        for key in ("git_url", "branch", "local_clone",
                    "target_collection", "authcfg_id",
                    "bundle_name", "commit_email"):
            val = getattr(repo, key, "")
            if val:
                entry[key] = val
        if repo.is_default:
            entry["is_default"] = True
        # Round-trip unknown forward-compatibility fields
        if repo.extra:
            for k, v in repo.extra.items():
                entry.setdefault(k, v)
        return entry

    # ------------------------------------------------------------------
    # Connection diagnostic — used by 'Test connection' in the editor
    # ------------------------------------------------------------------

    def test_connection(self, repo: RemoteRepo, timeout: int = 15) -> RepoSyncResult:
        """Probe a remote repo without mutating local state.

        Runs ``git ls-remote <url>`` (no clone, no working tree) so the
        user gets fast feedback on URL/auth correctness from the editor
        dialog. For Fallback A repos (no git_url) we just check the
        local_clone path is writable.
        """
        result = RepoSyncResult(
            repo_name=repo.name,
            clone_path=repo.expanded_local_clone,
        )
        if not repo.has_remote:
            target = repo.expanded_local_clone
            if not target:
                result.error_message = "local_clone is empty"
                return result
            try:
                os.makedirs(target, exist_ok=True)
            except OSError as exc:
                result.error_message = f"cannot write local_clone: {exc}"
                return result
            result.success = True
            result.skipped_push_reason = "no_remote"
            return result

        client = GitClient(
            cwd=repo.expanded_local_clone or os.getcwd(),
            authcfg_id=repo.authcfg_id or None,
            git_binary=self._git_binary_or_default(),
            timeout_seconds=timeout,
        )
        try:
            client.ls_remote(repo.git_url, cwd=os.getcwd())
        except GitError as exc:
            result.error_message = str(exc)
            return result
        result.success = True
        return result

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
            authcfg_id=repo.authcfg_id or None,
            git_binary=self._git_binary_or_default(),
        )

        try:
            if not client.is_cloned():
                logger.info(
                    "Cloning %s → %s (branch=%s)",
                    _scrub_text(repo.git_url), repo.expanded_local_clone, repo.branch or "<default>",
                )
                client.clone(repo.git_url, branch=repo.branch or None)
            else:
                # The clone keeps the origin it was cloned from: follow the
                # git_url of the config (a new port or host) before talking
                # to the remote, so pull and push reach the configured server.
                current = client.get_remote_url("origin")
                if not current:
                    # set-url fails with no origin: every publish failed (audit of 2026-11-24, git 2.43).
                    logger.info(
                        "Remote origin of %s set to the configured URL %s",
                        repo.expanded_local_clone,
                        _scrub_text(repo.git_url),
                    )
                    client.add_remote_url(repo.git_url, "origin")
                elif current != repo.git_url:
                    if _repo_path(current) != _repo_path(repo.git_url):
                        # Another repository, not a new address of this one (a move keeps the path): said
                        # loudly, not silently (audit of 2026-11-24). The configured URL still wins (a moved
                        # server must be followed); check it is yours when this warns.
                        logger.warning(
                            "Remote origin of %s points to another repository (%s): set to the configured "
                            "URL %s; fix the address or move the folder if that other repository is not a "
                            "move of this one",
                            repo.expanded_local_clone,
                            _scrub_text(current), _scrub_text(repo.git_url),
                        )
                    else:
                        logger.info(
                            "Remote origin of %s set to the configured URL %s (was %s)",
                            repo.expanded_local_clone,
                            _scrub_text(repo.git_url), _scrub_text(current),
                        )
                    client.set_remote_url(repo.git_url, "origin")
                # Same for the branch: pulling the configured branch into
                # another one would merge them, so switch to it first.
                checked_out = client.current_branch()
                if repo.branch and checked_out != repo.branch:
                    logger.info(
                        "Clone %s switched to the configured branch %s (was %s)",
                        repo.expanded_local_clone, repo.branch, checked_out or "<detached>",
                    )
                    client.switch_branch(repo.branch, "origin")
                logger.info("Fast-forward pull on %s", repo.expanded_local_clone)
                client.pull_fast_forward()
        except GitError as exc:
            result.error_message = str(exc)
            return result

        result.success = True
        return result

    def publish_to_remote(
        self,
        repo: RemoteRepo,
        write_bundle,
        commit_author: Optional[str] = None,
    ) -> RepoSyncResult:
        """
        Run the full publish flow for a single repo.

        Renamed from ``publish_bundle`` (P1, 2026-04-28) to disambiguate
        from :meth:`FavoritesSharingService.publish_bundle` — which
        writes a single bundle into a local Resource Sharing collection
        directory. ``publish_to_remote`` is the *outer* layer: it clones
        the repo, runs ``write_bundle`` to produce the file in-tree,
        commits, and pushes.

        Args:
            repo: Target repo (validated via ``from_config_entry``).
            write_bundle: Callable ``(collection_dir: str) -> str`` that
                writes the bundle file and returns its absolute path.
                Any exception it raises is captured into the result.
            commit_author: Override for git author, e.g. "Team <email>".
                When None, falls back to ``repo.commit_author()`` (the
                repo's ``commit_email``, else ``DEFAULT_COMMIT_AUTHOR``).

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
            authcfg_id=repo.authcfg_id or None,
            git_binary=self._git_binary_or_default(),
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
                author=commit_author or repo.commit_author(),
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

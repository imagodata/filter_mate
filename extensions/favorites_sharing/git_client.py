# -*- coding: utf-8 -*-
"""
Thin ``subprocess`` wrapper around the system ``git`` binary.

FilterMate uses git to keep remote-backed favorite collections in sync:
clone on first publish, fast-forward pull before each publish, commit +
push the bundle afterwards. We deliberately avoid the ``gitpython``
dependency — ``git`` is already on every QGIS-capable host and a shell
call is trivial to audit.

Design rules:
- All commands run with an explicit timeout (default 30s) — a slow remote
  must never freeze QGIS.
- No auto-rebase, no auto-merge. Conflicts surface as ``GitError`` with
  the clone path attached so the UI can offer "Open clone" rather than
  risking history rewrites.
- stderr is captured and returned verbatim — operators paste it into bug
  reports.
- Credentials are injected via ``http.extraHeader`` so they never land
  in process argv. Two sources are supported, the first one wins:
  * ``authcfg_id`` — resolved at exec time through ``QgsAuthManager``,
    which decrypts the stored Basic/PAT credential into an
    ``Authorization:`` header. The plaintext never touches config.json.
  * ``auth_header`` — legacy plaintext fallback for pre-migration
    configs (deprecated).
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger('FilterMate.FavoritesSharing.Git')

DEFAULT_TIMEOUT_SECONDS = 30

# Patterns used to scrub secrets out of command lists, stderr text, and log
# lines before they leave the process (M7 hardening, audit 2026-04-23).
_AUTH_HEADER_RE = re.compile(
    r"(http\.extraHeader=Authorization:\s*)[^\n]+", re.IGNORECASE
)
_URL_CREDS_RE = re.compile(r"(\w+://)([^/@\s]+)@")
_REDACTED = "[REDACTED]"


def _scrub_command(cmd: List[str]) -> List[str]:
    """Return a copy of ``cmd`` with any embedded auth header redacted."""
    return [_AUTH_HEADER_RE.sub(rf"\1{_REDACTED}", arg) for arg in cmd]


def _strip_control_chars(value: str) -> str:
    """Remove CR/LF and other low-ASCII control chars from a single-line value.

    Used on credentials, commit authors and other strings injected into
    git's ``-c key=value`` flag or single-line argv slots: a stray
    newline would otherwise terminate the config line and let attacker
    content be parsed as additional git config.
    """
    if not value:
        return value
    return "".join(c for c in value if c == "\t" or (c >= " " and c != "\x7f"))


def _scrub_text(text: str) -> str:
    """Strip Authorization headers and URL-embedded credentials from text.

    Designed for stderr coming back from ``git`` — server messages may echo
    the request line (``Authorization: Basic ...``) or the full URL
    (``https://user:token@host/repo``). Either would leak credentials into
    log files, bug-report attachments, or the GitError message.
    """
    if not text:
        return text
    scrubbed = _AUTH_HEADER_RE.sub(rf"\1{_REDACTED}", text)
    scrubbed = _URL_CREDS_RE.sub(rf"\1{_REDACTED}@", scrubbed)
    return scrubbed


def _resolve_authcfg_header(authcfg_id: str) -> Optional[str]:
    """Decrypt a QGIS auth config entry into an HTTP Authorization value.

    Supports the two QgsAuthMethodConfig variants that map cleanly onto
    HTTP credentials: ``Basic`` (username + password → ``Basic <b64>``)
    and ``APIHeader``/PAT-style configs that store a raw header value
    under a ``token`` / ``Authorization`` config key.

    Returns ``None`` when:
      * the ``qgis.core`` module is not importable (standalone tests);
      * the ``authcfg_id`` is not registered in QgsAuthManager;
      * the entry exists but doesn't carry credentials we can map to an
        ``Authorization:`` header (e.g. SSH key configs — out of scope
        for HTTPS git over subprocess).

    The first call may trigger the master-password prompt — that's the
    user-facing tradeoff for storing credentials encrypted at rest.
    """
    if not authcfg_id:
        return None
    try:
        from qgis.core import QgsApplication, QgsAuthMethodConfig  # type: ignore
    except ImportError:
        return None

    auth_manager = QgsApplication.authManager()
    if auth_manager is None or authcfg_id not in auth_manager.configIds():
        return None

    cfg = QgsAuthMethodConfig()
    if not auth_manager.loadAuthenticationConfig(authcfg_id, cfg, True):
        return None

    method = (cfg.method() or "").lower()
    config_map = {k: cfg.config(k) for k in cfg.configMap().keys()}

    # Basic auth: build Basic <base64(user:pass)>
    if method in ("basic", "httpbasic"):
        import base64
        user = config_map.get("username") or ""
        pwd = config_map.get("password") or ""
        if not user and not pwd:
            return None
        token = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    # APIHeader / PAT — providers store either the full "Bearer X" string
    # or just the raw token. Accept both common keys.
    for key in ("Authorization", "authorization", "token", "header"):
        value = (config_map.get(key) or "").strip()
        if value:
            # Prepend "Bearer " when the value looks like a bare PAT
            # (no scheme word at the start).
            if " " not in value:
                return f"Bearer {value}"
            return value

    return None


class GitError(RuntimeError):
    """A git subprocess returned non-zero."""

    def __init__(self, command: List[str], returncode: int,
                 stdout: str, stderr: str, cwd: Optional[str] = None):
        # M7 (2026-04-23): scrub auth headers from cmd & stderr so the
        # exception (often surfaced in log files / bug reports) doesn't
        # leak credentials.
        self.command = _scrub_command(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = _scrub_text(stderr)
        self.cwd = cwd
        cmd_str = " ".join(self.command)
        super().__init__(
            f"git command failed (exit {returncode}): {cmd_str}\n{self.stderr.strip()}"
        )


@dataclass
class GitResult:
    """Outcome of a single git invocation."""
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


@dataclass
class GitClient:
    """
    Stateless git client bound to a working directory + optional auth.

    The client can run commands in repos that don't exist yet (clone) or
    that already exist (everything else). Construct one per repo.
    """
    cwd: str
    auth_header: Optional[str] = None
    # Preferred over auth_header when both are set. Resolved lazily via
    # QgsAuthManager — keeps credentials encrypted at rest in QGIS' keystore.
    authcfg_id: Optional[str] = None
    git_binary: str = "git"
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    # Extra env overrides (tests inject GIT_TERMINAL_PROMPT=0 etc.)
    extra_env: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Auth resolution
    # ------------------------------------------------------------------

    def _resolve_auth_header(self) -> Optional[str]:
        """Return the Authorization header value to inject, or None.

        Priority: ``authcfg_id`` (decrypted via QgsAuthManager) wins over
        the legacy ``auth_header`` field. If the QGIS auth manager is not
        importable (standalone tests, headless harness without QGIS) the
        method silently falls back to ``auth_header``.
        """
        if self.authcfg_id:
            header = _resolve_authcfg_header(self.authcfg_id)
            if header:
                return header
            logger.warning(
                "authcfg_id %r could not be resolved to a credential — "
                "falling back to auth_header (if any).", self.authcfg_id,
            )
        return self.auth_header or None

    # ------------------------------------------------------------------
    # Low-level run
    # ------------------------------------------------------------------

    def _run(
        self,
        args: List[str],
        *,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        check: bool = True,
    ) -> GitResult:
        """Run ``git <args>`` and return the captured result.

        Raises ``GitError`` when ``check=True`` and exit code != 0. On
        ``subprocess.TimeoutExpired`` we also raise ``GitError`` with a
        synthetic exit code (-1) so callers need to handle only one
        exception type.
        """
        cmd: List[str] = [self.git_binary]
        # Inject auth header as a --config override so it is not logged
        # as part of the URL. Only set for operations that touch the net.
        # Resolved here (not at __init__) so QgsAuthManager prompts for
        # the master password at the moment of use, not at config load.
        header = self._resolve_auth_header()
        if header:
            # Strip CR/LF: a header containing "\n[remote \"x\"]..." would
            # otherwise inject extra git config through the ``-c`` flag.
            safe_header = _strip_control_chars(header)
            cmd += [
                "-c",
                f"http.extraHeader=Authorization: {safe_header}",
            ]
        cmd += list(args)

        run_cwd = cwd or self.cwd
        env = os.environ.copy()
        # Never prompt for credentials — fail fast on auth issues.
        env.setdefault("GIT_TERMINAL_PROMPT", "0")
        env.setdefault("GIT_ASKPASS", "echo")
        env.update(self.extra_env)

        logger.debug("git run: cwd=%s cmd=%s", run_cwd, _scrub_command(cmd))
        try:
            proc = subprocess.run(
                cmd,
                cwd=run_cwd if run_cwd and os.path.isdir(run_cwd) else None,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout_seconds,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitError(
                cmd, returncode=-1, stdout="",
                stderr=f"timeout after {exc.timeout}s",
                cwd=run_cwd,
            ) from exc
        except FileNotFoundError as exc:
            # git binary not on PATH
            raise GitError(
                cmd, returncode=-2, stdout="",
                stderr=f"git binary not found: {exc}",
                cwd=run_cwd,
            ) from exc

        result = GitResult(
            ok=proc.returncode == 0,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            returncode=proc.returncode,
        )
        if check and not result.ok:
            raise GitError(
                cmd, returncode=proc.returncode,
                stdout=result.stdout, stderr=result.stderr,
                cwd=run_cwd,
            )
        return result

    # ------------------------------------------------------------------
    # High-level operations
    # ------------------------------------------------------------------

    def is_cloned(self) -> bool:
        """True when ``cwd`` looks like a git working tree."""
        git_dir = os.path.join(self.cwd, ".git")
        return os.path.isdir(git_dir) or os.path.isfile(git_dir)

    def clone(self, git_url: str, branch: Optional[str] = None) -> GitResult:
        """Clone ``git_url`` into ``self.cwd``.

        Creates parent directories if needed. ``--depth 1`` would be
        tempting for speed but breaks subsequent ``pull --ff-only`` on
        diverged histories — keep a full clone.

        Defense-in-depth: an explicit ``--`` separator precedes the URL
        and destination so a URL like ``--upload-pack=evil`` cannot be
        re-interpreted as an option even on older git releases.
        """
        parent = os.path.dirname(os.path.abspath(self.cwd))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)

        if self.is_cloned():
            logger.debug("Repo already cloned at %s — skipping clone", self.cwd)
            return GitResult(ok=True, stdout="already cloned")

        args = ["clone"]
        if branch:
            args += ["--branch", branch]
        args += ["--", git_url, self.cwd]
        # Run from parent so we can target cwd that doesn't exist yet.
        return self._run(args, cwd=parent or None)

    def pull_fast_forward(self) -> GitResult:
        """``git pull --ff-only`` — refuses to merge on divergence.

        A non-fast-forward refusal surfaces as ``GitError``; the caller
        should present the clone path and let the user resolve manually.
        """
        return self._run(["pull", "--ff-only"])

    def add(self, paths: List[str]) -> GitResult:
        """``git add`` one or more paths (relative to cwd or absolute)."""
        if not paths:
            return GitResult(ok=True, stdout="no paths to add")
        return self._run(["add", "--"] + list(paths))

    def has_staged_changes(self) -> bool:
        """True when the index differs from HEAD (something to commit)."""
        res = self._run(
            ["diff", "--cached", "--quiet"],
            check=False,
        )
        # Exit code 1 = diff present (i.e., changes staged).
        return res.returncode == 1

    def commit(self, message: str, author: Optional[str] = None) -> GitResult:
        """Create a commit with ``message``.

        When ``author`` is provided ("Name <email>"), it overrides the
        repo's configured identity for this single commit. Useful so
        bundles carry the publishing team's identity rather than the
        machine's default git config. Newlines in ``author`` are
        stripped — the field must stay single-line so a malicious
        identity cannot inject extra commit trailers.
        """
        args = ["commit", "-m", message]
        if author:
            args += ["--author", _strip_control_chars(author)]
        return self._run(args)

    def push(self, remote: str = "origin", branch: Optional[str] = None) -> GitResult:
        """``git push <remote> [branch]``.

        The ``--`` separator pins ``remote`` and ``branch`` as positional
        even if they accidentally start with a dash.
        """
        args = ["push", "--", remote]
        if branch:
            args.append(branch)
        return self._run(args)

    def current_branch(self) -> Optional[str]:
        """Return the checked-out branch name, or None when detached."""
        res = self._run(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            check=False,
        )
        if not res.ok:
            return None
        name = (res.stdout or "").strip()
        return name if name and name != "HEAD" else None

    def head_sha(self) -> Optional[str]:
        """Short SHA of HEAD, or None when the repo has no commits."""
        res = self._run(["rev-parse", "--short", "HEAD"], check=False)
        if not res.ok:
            return None
        return (res.stdout or "").strip() or None

    def ls_remote(self, git_url: str, *, heads_only: bool = True,
                  cwd: Optional[str] = None,
                  timeout: Optional[int] = None) -> GitResult:
        """``git ls-remote [--heads] -- <url>`` — probe a remote without cloning.

        Used by ``test_connection`` to validate URL/auth from the editor
        dialog. The ``--`` separator ensures a URL beginning with ``-``
        is treated as positional, not as a flag.
        """
        args = ["ls-remote"]
        if heads_only:
            args.append("--heads")
        args += ["--", git_url]
        return self._run(args, cwd=cwd, timeout=timeout)

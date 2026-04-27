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
- ``auth_header`` (HTTP Basic / PAT) is injected via
  ``http.extraHeader`` so credentials never land in process argv.
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
    git_binary: str = "git"
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    # Extra env overrides (tests inject GIT_TERMINAL_PROMPT=0 etc.)
    extra_env: dict = field(default_factory=dict)

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
        # Inject auth header as an --config override so it is not logged
        # as part of the URL. Only set for operations that touch the net.
        if self.auth_header:
            cmd += [
                "-c",
                f"http.extraHeader=Authorization: {self.auth_header}",
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
        args += [git_url, self.cwd]
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
        machine's default git config.
        """
        args = ["commit", "-m", message]
        if author:
            args += ["--author", author]
        return self._run(args)

    def push(self, remote: str = "origin", branch: Optional[str] = None) -> GitResult:
        """``git push <remote> [branch]``."""
        args = ["push", remote]
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

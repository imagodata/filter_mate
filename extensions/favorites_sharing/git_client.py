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
- stderr is captured and returned with credentials scrubbed — operators
  paste it into bug reports.
- Credentials are injected as an ``http.extraHeader`` passed through the
  environment (``GIT_CONFIG_COUNT`` / ``GIT_CONFIG_KEY_n`` /
  ``GIT_CONFIG_VALUE_n``, git >= 2.31), never in the process argv, which
  any local user can read (``/proc/<pid>/cmdline``, process lists). Older
  git only takes it as a ``-c`` option on the command line. It is given
  only to the commands that reach the remote (clone, fetch, pull, push,
  ls-remote), and only when that remote is an ``https://`` URL: never sent
  in clear over ``http://``, never to an ssh or local remote. The credential
  comes from ``authcfg_id`` only, resolved at exec time through
  ``QgsAuthManager``, which decrypts the stored Basic/PAT credential into an
  ``Authorization:`` header. The plaintext never touches config.json (the
  legacy plaintext ``auth_header`` was removed in FilterMate 5.0, audit EXT-6).
- Transports: git's own default list minus ``ext::`` (which runs a
  command), through ``GIT_ALLOW_PROTOCOL``: team repos on a local / UNC
  path or an intranet ``http://`` server keep working.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('FilterMate.FavoritesSharing.Git')

DEFAULT_TIMEOUT_SECONDS = 30

# Patterns used to scrub secrets out of command lists, stderr text, and log
# lines before they leave the process (M7 hardening, audit 2026-04-23).
_AUTH_HEADER_RE = re.compile(
    r"(http\.extraHeader=Authorization:\s*)[^\n]+", re.IGNORECASE
)
# A bare header line echoed by a server or a verbose trace (``Authorization: Basic ...``).
_RAW_AUTH_RE = re.compile(r"(Authorization:\s*)(?!\[REDACTED\])[^\n]+", re.IGNORECASE)
# userinfo of a URL (``https://user:token@host``), greedy up to the last "@"
# of the authority so a password holding "@" is masked whole.
_URL_CREDS_RE = re.compile(r"(\w+://)([^/\s]+)@")
_REDACTED = "[REDACTED]"

# Transports git may use (GIT_ALLOW_PROTOCOL): git's default policy without
# ``ext::``, which runs a command. Local / UNC paths (file) and intranet
# http:// remotes are real team setups; the token only ever goes to https.
ALLOWED_PROTOCOLS = "file:git:http:https:ssh"

# Commands that talk to the remote: the only ones given the auth header.
_NETWORK_COMMANDS = frozenset({"clone", "fetch", "pull", "push", "ls-remote"})

# ``GIT_CONFIG_COUNT`` / ``GIT_CONFIG_KEY_n`` / ``GIT_CONFIG_VALUE_n``: git 2.31+.
_CONFIG_ENV_MIN_VERSION = (2, 31)
_GIT_VERSIONS: Dict[str, Optional[Tuple[int, int]]] = {}


def _scrub_command(cmd: List[str]) -> List[str]:
    """Return a copy of ``cmd`` with auth headers and URL credentials redacted."""
    return [_scrub_text(arg) for arg in cmd]


def _git_version(git_binary: str) -> Optional[Tuple[int, int]]:
    """``(major, minor)`` of ``git_binary``, None when it cannot be read.

    Read once per binary, failure included (``git --version``:
    ``git version 2.43.0``, ``2.39.2.windows.1``, ``2.30.1 (Apple Git-130)``).
    """
    if git_binary not in _GIT_VERSIONS:
        version = None
        try:
            proc = subprocess.run(  # nosec B603 - fixed argv, no shell, timeout enforced
                [git_binary, "--version"], capture_output=True, text=True, timeout=10, check=False,
            )
            match = re.search(r"(\d+)\.(\d+)", proc.stdout or "")
            if proc.returncode == 0 and match is not None:
                version = (int(match.group(1)), int(match.group(2)))
        except (OSError, subprocess.SubprocessError):
            pass
        _GIT_VERSIONS[git_binary] = version
    return _GIT_VERSIONS[git_binary]


def _subcommand(args: List[str]) -> Tuple[str, List[str]]:
    """``(git command, its arguments)`` of ``args``, past leading ``-c key=value`` options."""
    index = 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] == "-c" else 1
    if index >= len(args):
        return "", []
    return args[index], list(args[index + 1:])


def _split_identity(author: str) -> Optional[Tuple[str, str]]:
    """``("Name", "email")`` of ``"Name <email>"``, None when there is no email."""
    match = re.fullmatch(r"\s*(.*?)\s*<([^<>]+)>\s*", author or "")
    if match is None:
        return None
    return match.group(1) or match.group(2), match.group(2)


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
    (``https://user:token@host/repo``).  # pragma: allowlist secret
    Either would leak credentials into log files, bug-report attachments,
    or the GitError message.
    """
    if not text:
        return text
    scrubbed = _AUTH_HEADER_RE.sub(rf"\1{_REDACTED}", text)
    scrubbed = _RAW_AUTH_RE.sub(rf"\1{_REDACTED}", scrubbed)
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
        # M7 (2026-04-23): scrub auth headers and URL credentials
        # (``git clone -- https://oauth2:TOKEN@host/...``) from cmd & output
        # so the exception (message bar, log files, bug reports) doesn't
        # leak credentials.
        self.command = _scrub_command(command)
        self.returncode = returncode
        self.stdout = _scrub_text(stdout)
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
    # Resolved lazily via QgsAuthManager — keeps credentials encrypted at
    # rest in QGIS' keystore.
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

        The header comes from ``authcfg_id`` (decrypted via QgsAuthManager).
        Without it, or when it cannot be resolved (QGIS auth manager not
        importable, entry missing, master password refused), git runs
        unauthenticated.
        """
        if not self.authcfg_id:
            return None
        header = _resolve_authcfg_header(self.authcfg_id)
        if not header:
            logger.warning(
                "authcfg_id %r could not be resolved to a credential — "
                "running git unauthenticated.", self.authcfg_id,
            )
        return header or None

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
        run_cwd = cwd or self.cwd
        env = os.environ.copy()
        # Never prompt for credentials — fail fast on auth issues.
        env.setdefault("GIT_TERMINAL_PROMPT", "0")
        env.setdefault("GIT_ASKPASS", "echo")
        env["GIT_ALLOW_PROTOCOL"] = ALLOWED_PROTOCOLS
        env.update(self.extra_env)

        # Inject the auth header as an http.extraHeader config override, out
        # of the URL, for a command reaching an https remote only. Resolved
        # here (not at __init__) so QgsAuthManager prompts for the master
        # password at the moment of use, not at config load.
        command, rest = _subcommand(list(args))
        header = None
        if command in _NETWORK_COMMANDS and self._remote_url(command, rest, cwd).lower().startswith("https://"):
            header = self._resolve_auth_header()
        if header:
            # Strip CR/LF: a header containing "\n[remote \"x\"]..." would
            # otherwise inject extra git config through the ``-c`` flag.
            value = f"Authorization: {_strip_control_chars(header)}"
            if (_git_version(self.git_binary) or (0, 0)) >= _CONFIG_ENV_MIN_VERSION:
                # Through the environment: argv is readable by any local user.
                try:
                    index = max(0, int(env.get("GIT_CONFIG_COUNT") or 0))
                except ValueError:
                    index = 0
                env[f"GIT_CONFIG_KEY_{index}"] = "http.extraHeader"
                env[f"GIT_CONFIG_VALUE_{index}"] = value
                env["GIT_CONFIG_COUNT"] = str(index + 1)
            else:
                cmd += ["-c", f"http.extraHeader={value}"]
        cmd += list(args)

        logger.debug("git run: cwd=%s cmd=%s", run_cwd, _scrub_command(cmd))
        try:
            proc = subprocess.run(  # nosec B603 - cmd is a list built from self.git_binary + fixed flags, no shell, timeout enforced
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

    def _remote_url(self, command: str, rest: List[str], cwd: Optional[str] = None) -> str:
        """URL a network command talks to ("" when unknown).

        clone / ls-remote name it after ``--``; push names a remote after
        ``--``, pull / fetch use ``origin`` (our flow): read from the clone's
        config, without any header.
        """
        positional = rest[rest.index("--") + 1:] if "--" in rest else [a for a in rest if not a.startswith("-")]
        if command in ("clone", "ls-remote"):
            return positional[0] if positional else ""
        remote = positional[0] if command == "push" and positional else "origin"
        if "://" in remote:
            return remote
        res = self._run(["config", "--get", f"remote.{remote}.url"], cwd=cwd, check=False)
        return (res.stdout or "").strip() if res.ok else ""

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
        identity cannot inject extra commit trailers. On a fresh install
        with no git identity at all, the author is also the committer
        (git refuses to commit without one).
        """
        author = _strip_control_chars(author or "")
        args = ["commit", "-m", message]
        if author:
            args += ["--author", author]
            identity = _split_identity(author)
            if identity is not None:
                for key, value in zip(("user.name", "user.email"), identity):
                    if not self._has_config(key):
                        args = ["-c", f"{key}={value}"] + args
        return self._run(args)

    def _has_config(self, key: str) -> bool:
        """True when git has a value for ``key`` here (repo, global or system config)."""
        res = self._run(["config", "--get", key], check=False)
        return res.ok and bool((res.stdout or "").strip())

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

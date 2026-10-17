"""Command line and environment settings of the FilterMate MCP server.

The API key is read from an environment variable, never from the command
line (a command line is visible to every process of the machine and ends up
in shell history and client configuration files shown on screen).
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence
from urllib.parse import urlsplit

DEFAULT_URL = "http://127.0.0.1:8000"
DEFAULT_KEY_ENV = "FILTERMATE_API_KEY"
# REST API calls wait up to 30 s for the QGIS main thread (main_thread.py);
# the MCP side must outlast that to read the 503 instead of timing out first.
DEFAULT_TIMEOUT_SECONDS = 45.0

_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ConfigError(ValueError):
    """The server cannot start with these settings (the message is for the user)."""


@dataclass(frozen=True)
class MCPSettings:
    """Validated settings of one MCP server run."""

    base_url: str
    api_key: str = field(repr=False)
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    allow_remote: bool = False

    @property
    def is_loopback(self) -> bool:
        """True when the API URL points at this machine."""
        return is_loopback_host(urlsplit(self.base_url).hostname)


def is_loopback_host(host: Optional[str]) -> bool:
    """True for ``localhost`` and loopback IP literals (127.0.0.0/8, ::1)."""
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def build_parser() -> argparse.ArgumentParser:
    """Argument parser of ``python -m filtermate_api.mcp``."""
    parser = argparse.ArgumentParser(
        prog="python -m filtermate_api.mcp",
        # No abbreviations: "--api-key SECRET" would otherwise be read as "--api-key-env SECRET".
        allow_abbrev=False,
        description=(
            "MCP server (stdio) for FilterMate: relays tool calls to the FilterMate REST API "
            "running inside QGIS. The API key comes from an environment variable."
        ),
    )
    parser.add_argument(
        "--url", default=DEFAULT_URL,
        help="base URL of the FilterMate REST API (default: %(default)s)")
    parser.add_argument(
        "--api-key-env", default=DEFAULT_KEY_ENV, metavar="NAME",
        help="NAME of the environment variable holding the API key (default: %(default)s); "
             "the key itself is never accepted on the command line")
    parser.add_argument(
        "--allow-remote", action="store_true",
        help="accept an API URL that is not on this machine (the key then travels over the network)")
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, metavar="SECONDS",
        help="HTTP timeout per call (default: %(default).0f, above the 30 s wait of the API for QGIS)")
    return parser


def parse_settings(argv: Optional[Sequence[str]], environ: Mapping[str, str]) -> MCPSettings:
    """Settings from the command line ``argv`` and ``environ``.

    Raises:
        ConfigError: the settings are unusable (no key, remote URL not allowed...).
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    for arg in argv:
        name = arg.split("=", 1)[0]
        if name.startswith("--api-key") and name != "--api-key-env":
            # Say it without echoing the value argparse would print back.
            raise ConfigError(
                "The API key is never accepted on the command line: put it in the environment variable "
                f"{DEFAULT_KEY_ENV} (or name another variable with --api-key-env NAME).")
    args = build_parser().parse_args(argv)

    env_name = args.api_key_env
    if not _ENV_NAME.match(env_name):
        raise ConfigError(
            "--api-key-env takes the NAME of an environment variable (e.g. FILTERMATE_API_KEY), "
            "never the key itself.")
    api_key = (environ.get(env_name) or "").strip()
    if not api_key:
        raise ConfigError(
            f"No API key: set the environment variable {env_name} to the FilterMate API key "
            "(the key configured in QGIS for the REST API). An AI assistant able to change your "
            "layer filters must authenticate, so the server refuses to start without one.")
    if not api_key.isascii() or not api_key.isprintable():
        raise ConfigError(f"The API key in {env_name} must be printable ASCII.")

    base_url = _check_url(args.url, args.allow_remote)
    if not args.timeout > 0:
        raise ConfigError("--timeout must be a positive number of seconds.")
    return MCPSettings(base_url=base_url, api_key=api_key, timeout=args.timeout,
                       allow_remote=args.allow_remote)


def _check_url(url: str, allow_remote: bool) -> str:
    try:
        parts = urlsplit(url)
        host = parts.hostname
        _ = parts.port  # raises ValueError on a bad port
    except ValueError as exc:
        raise ConfigError(f"Invalid --url {url!r}: {exc}") from exc
    if parts.scheme not in ("http", "https") or not host:
        raise ConfigError(f"Invalid --url {url!r}: expected http://host:port.")
    if parts.username or parts.password:
        raise ConfigError("Invalid --url: credentials do not belong in the URL (use the API key variable).")
    if parts.query or parts.fragment:
        raise ConfigError("Invalid --url: no query string or fragment.")
    if not is_loopback_host(host):
        if not allow_remote:
            raise ConfigError(
                f"Refusing --url {url!r}: it is not on this machine. The FilterMate API is meant to be "
                "reached on 127.0.0.1; pass --allow-remote if you really expose it (use https then).")
        if parts.scheme == "http":
            print("filtermate-mcp: warning: the API key is sent in clear text to a remote http URL.",
                  file=sys.stderr)
    return url.rstrip("/")

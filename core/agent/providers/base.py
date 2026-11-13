# -*- coding: utf-8 -*-
"""What a provider adapter is, and what all of them share (SSE, errors, base URL rule)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence
from urllib.parse import urlsplit

from ..messages import (
    ERROR_AUTH, ERROR_BAD_REQUEST, ERROR_NETWORK, ERROR_QUOTA, ERROR_RATE_LIMIT, ERROR_SERVER, Message, ProviderError,
    StreamEvent,
)
from ..tool_catalog import ToolSpec

_LOOPBACK = ("localhost", "127.0.0.1", "::1")
_QUOTA_WORDS = ("credit balance", "insufficient_quota", "quota exceeded", "exceeded your current quota")
_MAX_ERROR_CHARS = 500


@dataclass(frozen=True)
class ProviderConfig:
    """Which model answers, and how to reach it. ``api_key`` never appears in a repr."""

    kind: str
    model: str
    base_url: str = ""
    api_key: str = field(default="", repr=False)
    max_tokens: int = 16000
    effort: Optional[str] = None
    # A relay's own token, for instance.
    extra_headers: Mapping[str, str] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class HttpRequest:
    """A POST to send; the headers hold the key, so they stay out of a repr."""

    url: str
    headers: Mapping[str, str] = field(default_factory=dict, repr=False)
    body: bytes = field(default=b"", repr=False)


class StreamParser(Protocol):
    """Turns the bytes of one response into events."""

    def feed(self, data: bytes) -> List[StreamEvent]:
        """Events completed by ``data``."""

    def close(self) -> List[StreamEvent]:
        """The response is over: a failure when the turn never finished."""


class Provider(Protocol):
    """Translates the conversation for one API."""

    def build_request(self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> HttpRequest:
        """The request for the next model turn."""

    def new_parser(self) -> StreamParser:
        """A parser for one streamed response."""


def check_base_url(url: str, secret: Any) -> None:
    """Refuse a URL that is not http(s), or that would send ``secret`` (key, token) in clear over a network.

    Raises:
        ValueError: With the reason.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError(f"not an http(s) URL: {without_credentials(url)!r}")
    if parts.scheme == "http" and secret and parts.hostname not in _LOOPBACK:
        raise ValueError("an API key is only sent over https, or to this machine")


# A URL up to its last "@" before the query: a user:password typed in the address, which may hold "/" (a generated
# password), with or without "http://". A pattern, not urlsplit, which refuses an address it cannot parse (an IPv6
# left open) and would then have shown it whole. A path holding "@" loses what comes before it: shown, not used.
_CREDENTIALS = re.compile(r"^(?:([A-Za-z][A-Za-z0-9+.-]*:)?//)?[^?#]*@")


def without_credentials(url: str) -> str:
    """``url`` as shown to the user (a tooltip, a message): a ``user:password@`` typed in the address is left out."""
    return _CREDENTIALS.sub(lambda match: (match.group(1) or "") + "//" if "//" in match.group(0) else "", url,
                            count=1)


MIN_MASKED_KEY = 8  # a shorter "key" (one letter) would be found in any word: the message would be torn


def without_key(text: str, key: str) -> str:
    """``text`` with ``key`` replaced by an ellipsis, for a message a provider worded and may have sent the key in."""
    return text.replace(key, "…") if len(key) >= MIN_MASKED_KEY else text


def encode_json(body: Dict[str, Any]) -> bytes:
    """Compact and in insertion order: the same conversation gives the same bytes."""
    # "replace": a model can stream a lone surrogate, which must not make every later request fail.
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8", "replace")


class SseDecoder:
    """Server-sent events from chunks of bytes, which may cut a line or a character anywhere."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._event = ""
        self._data: List[str] = []

    def feed(self, chunk: bytes) -> List[tuple]:
        """Complete ``(event name, data)`` pairs."""
        self._buffer.extend(chunk)
        events: List[tuple] = []
        while True:
            end = self._buffer.find(b"\n")
            if end < 0:
                return events
            line = bytes(self._buffer[:end]).rstrip(b"\r").decode("utf-8", "replace")
            del self._buffer[:end + 1]
            if not line:
                if any(self._data):
                    events.append((self._event, "\n".join(self._data)))
                self._event, self._data = "", []
            elif line.startswith("event:"):
                self._event = line[6:].strip()
            elif line.startswith("data:"):
                self._data.append(line[5:].lstrip(" "))

    def flush(self) -> List[tuple]:
        """What is left at the end of the response (a server may omit the last blank line)."""
        events = self.feed(b"\n\n") if self._buffer or self._data else []
        return events


def parse_tool_arguments(text: str):
    """``(arguments, error)`` from the JSON a model streamed; an object, or the reason it is not one."""
    if not text.strip():
        return {}, None
    try:
        value = json.loads(text)
    except (ValueError, RecursionError) as exc:
        return {}, str(exc)
    if not isinstance(value, dict):
        return {}, "expected a JSON object"
    return value, None


def _error_text(body: bytes) -> str:
    text = body.decode("utf-8", "replace")
    try:
        data = json.loads(text)
    except ValueError:
        return text[:_MAX_ERROR_CHARS]
    if isinstance(data, dict):
        for candidate in (data.get("error"), data.get("detail"), data.get("message")):
            if isinstance(candidate, dict):
                candidate = candidate.get("message") or candidate.get("type")
            if isinstance(candidate, str) and candidate:
                return candidate[:_MAX_ERROR_CHARS]
    return text[:_MAX_ERROR_CHARS]


def error_from_response(status: int, body: bytes = b"", headers: Optional[Mapping[str, str]] = None) -> ProviderError:
    """Classify an HTTP failure, so the panel can offer the right way out (own key, wait, settings)."""
    message = _error_text(body) or f"HTTP {status}"
    lowered = message.lower()
    retry_after = None
    for name, value in (headers or {}).items():
        if name.lower() == "retry-after":
            try:
                retry_after = float(value)
            except (TypeError, ValueError):
                retry_after = None
    if status == 402 or any(word in lowered for word in _QUOTA_WORDS):
        kind = ERROR_QUOTA
    elif status in (401, 403):
        kind = ERROR_AUTH
    elif status == 429:
        kind = ERROR_RATE_LIMIT
    elif status >= 500:
        kind = ERROR_SERVER
    elif status >= 400:
        kind = ERROR_BAD_REQUEST
    else:
        kind = ERROR_NETWORK
    return ProviderError(kind, message, status=status, retry_after=retry_after)

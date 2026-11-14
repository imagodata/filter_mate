# -*- coding: utf-8 -*-
"""A request whose cost is bounded, for answers that come from servers nobody here controls.

``QgsBlockingNetworkRequest`` follows redirects, restarts its timeout at every byte and holds the whole answer before
its size can be checked, so a server could send the request elsewhere, freeze QGIS or fill its memory. Here a redirect
is an answer like another, the total time and the size are capped, and the user can stop it. The manager is a private
one: a 401 or a TLS error is a failure, not a dialog that a remote server gets to word.
"""
from __future__ import annotations

import re

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QByteArray, QEventLoop, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

DEFAULT_MAX_BYTES = 8 * 1024 * 1024
DEFAULT_TIMEOUT_MS = 60_000
TOO_LARGE = "the server answered with too much data"
TOO_LONG = "the server took too long to answer"
STOPPED = "stopped"
_USER_AGENT = b"FilterMate-QGIS-plugin"
CHAT = "chat"
_ACTIVE = []  # (whose, stop) of each wait Stop can end
_OWNER = [""]  # whose waits start now: CHAT inside owned_by(CHAT), "" for another application


# The blank line that ends a server-sent event: two ends of line, each CRLF, LF or CR, in any mix. A CR before an
# LF is the start of one CRLF, never an end of line of its own: "\r\n" alone is no blank line.
_BLANK_LINE = re.compile(rb"(?:\r\n|\r(?!\n)|\n)(?:\r\n|\r|\n)")
_SEPARATOR_TAIL = 3  # what of a separator may end a chunk: "\r\n\r" before its last "\n"


def ends_an_event(tail: bytes, chunk: bytes) -> Tuple[bool, bytes]:
    """Whether ``chunk`` completes a blank line, the end of a server-sent event, with the end of the chunk before it.

    2026-11-13: only the chunk itself was looked at, so a separator cut between two chunks ("...\n" then "\n...")
    ended no event, and the request waited for another event or for its timeout.

    Args:
        tail: What ``ends_an_event`` returned for the chunk before (b"" for the first one).
        chunk: The bytes just received.

    Returns:
        (whether a separator is there, the tail to give with the next chunk).
    """
    window = tail + chunk
    return _BLANK_LINE.search(window) is not None, window[-_SEPARATOR_TAIL:]


class HttpFailure(Exception):
    """The request did not get an answer; the message can be shown."""


@dataclass(frozen=True)
class BoundedReply:
    status: int
    headers: Mapping[str, str]  # names in lower case: servers disagree on their case
    content: bytes


@contextmanager
def owned_by(owner: str) -> Iterator[None]:
    """The waits started inside belong to ``owner``: its Stop ends them, never those of another application."""
    previous, _OWNER[0] = _OWNER[0], owner
    try:
        yield
    finally:
        _OWNER[0] = previous


def abort_active(owner: Optional[str] = None) -> None:
    """The user pressed Stop: end the waits of ``owner`` (see owned_by), every wait when None.

    The Stop of the chat must not cut the call of an MCP client being answered meanwhile.
    """
    for whose, stop in list(_ACTIVE):
        if owner is None or whose == owner:
            stop()


def on_abort(stop: Callable[[], object]) -> Callable[[], None]:
    """Call ``stop`` when the user presses Stop, until the returned function is called.

    For another wait of the agent that lets the event loop run (a Processing algorithm).
    """
    entry = (_OWNER[0], stop)
    _ACTIVE.append(entry)

    def forget() -> None:
        if entry in _ACTIVE:
            _ACTIVE.remove(entry)
    return forget


class _Wait:
    """One request being waited for: bounded in size and in time, ended by Stop. ``settled`` is called once."""

    def __init__(self, settled: Callable[[], object], url: str, body: Optional[bytes] = None,
                 headers: Optional[Mapping[str, str]] = None, max_bytes: int = DEFAULT_MAX_BYTES,
                 timeout_ms: int = DEFAULT_TIMEOUT_MS, done: Optional[Callable[[bytes], bool]] = None,
                 headers_only: bool = False, sink: Optional[Callable[[bytes], object]] = None,
                 decompress_freely: bool = False) -> None:
        self._settled, self._max_bytes, self._done = settled, max_bytes, done
        self._headers_only, self._sink = headers_only, sink
        self._manager = QNetworkAccessManager()
        self._manager.setProxy(QgsNetworkAccessManager.instance().fallbackProxy())
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"User-Agent", _USER_AGENT)
        for name, value in (headers or {}).items():
            request.setRawHeader(name.encode("ascii"), value.encode("utf-8"))
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        if decompress_freely and hasattr(request, "setDecompressedSafetyCheckThreshold"):  # Qt 6.2 and later
            request.setDecompressedSafetyCheckThreshold(-1)
        self._reply = self._manager.post(request, QByteArray(body)) if body is not None else self._manager.get(request)
        self._buffer = bytearray()
        self._received = 0
        self._failure: Optional[str] = None
        self._tail = b""  # the end of the chunk before, where a separator may begin
        self._outcome: Union[BoundedReply, HttpFailure, None] = None
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._reply.readyRead.connect(self._on_data)
        self._reply.metaDataChanged.connect(self._on_headers)
        self._reply.finished.connect(self._settle)
        self._entry = (_OWNER[0], self._on_stop)
        _ACTIVE.append(self._entry)
        self._timer.start(timeout_ms)
        if self._reply.isFinished():
            self._settle()

    @property
    def settled(self) -> bool:
        return self._outcome is not None

    def _status(self) -> int:
        status = self._reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        return int(status) if isinstance(status, int) else 0

    def _fail(self, message: str) -> None:
        if not self.settled:
            self._failure = self._failure or message
            self._settle()

    def _on_timeout(self) -> None:
        self._fail(TOO_LONG)

    def _on_stop(self) -> None:
        self._fail(STOPPED)

    def _keep(self, chunk: bytes) -> None:
        """Count and keep ``chunk``; what goes wrong is left in ``_failure`` for the caller to settle on."""
        self._received += len(chunk)
        if self._received > self._max_bytes:
            self._failure = self._failure or TOO_LARGE
        elif self._sink is None:
            self._buffer.extend(chunk)
        else:
            try:
                self._sink(chunk)
            except OSError:  # raised from a Qt slot it would end QGIS
                self._failure = self._failure or "what the server sent could not be written to disk"

    def _on_data(self) -> None:
        chunk = bytes(self._reply.readAll())
        if self.settled:  # another request is still waited for: what keeps coming here is read and dropped
            return
        self._keep(chunk)
        if self._failure:
            self._settle()
        if self.settled or self._done is None:
            return
        ended, self._tail = ends_an_event(self._tail, chunk)
        if ended and self._done(bytes(self._buffer)):
            self._settle()

    def _on_headers(self) -> None:
        if self._headers_only and self._status():
            self._settle()

    def _settle(self) -> None:
        """What the request came to, read once: the reply is only aborted in ``close``, outside its own signals."""
        if self.settled:
            return
        self._timer.stop()
        try:
            self._outcome = self._read_outcome()
        except Exception as exc:  # a sink that raised: left unsettled, the wait would only end with Stop
            self._outcome = HttpFailure(f"what the server sent could not be kept ({exc})")
        self._settled()

    def _read_outcome(self) -> Union[BoundedReply, HttpFailure]:
        reply = self._reply
        if self._failure:
            return HttpFailure(self._failure)
        if reply.isOpen():
            self._keep(bytes(reply.readAll()))
            if self._failure:
                return HttpFailure(self._failure)
        status = self._status()
        pairs = {bytes(name).decode("latin-1").lower(): bytes(value).decode("latin-1")
                 for name, value in reply.rawHeaderPairs()}
        message = reply.errorString()
        broken = reply.isFinished() and reply.error() != QNetworkReply.NetworkError.NoError
        if not status and broken:
            if reply.error() == QNetworkReply.NetworkError.SslHandshakeFailedError:
                return HttpFailure("its security certificate is not valid for this address, so the connection was "
                                   "refused (" + (message or "TLS error") + ")")
            return HttpFailure(message or "network error")
        if self._sink is not None and 200 <= status < 300 and (broken or not reply.isFinished()):
            return HttpFailure("the connection was lost before the end of the file")
        return BoundedReply(status, pairs, bytes(self._buffer))

    def close(self) -> Union[BoundedReply, HttpFailure]:
        """End the request, whatever its state, and give what it came to."""
        if self._entry in _ACTIVE:
            _ACTIVE.remove(self._entry)
        self._entry = self._settled = None  # each held this wait in a cycle only the garbage collector would free
        self._timer.stop()
        outcome = self._outcome or HttpFailure(STOPPED)
        self._outcome = outcome
        self._reply.readyRead.disconnect(self._on_data)
        self._reply.metaDataChanged.disconnect(self._on_headers)
        self._reply.finished.disconnect(self._settle)
        self._reply.abort()
        self._reply.deleteLater()
        self._manager.deleteLater()
        return outcome


def fetch_together(requests: Sequence[Mapping[str, Any]]) -> List[Union[BoundedReply, HttpFailure]]:
    """Several requests waited for at once, each with the arguments of ``fetch`` and its own bounds.

    The wait lasts as long as the slowest of them, not their sum: connectors asked one after the other made the user
    wait for each one that did not answer.

    Returns:
        For each request, in order, its reply or the ``HttpFailure`` it ended with (returned, not raised).
    """
    loop = QEventLoop()
    waits: List[_Wait] = []

    def settled() -> None:
        if all(wait.settled for wait in waits):
            loop.quit()

    try:
        for request in requests:
            waits.append(_Wait(settled, **request))
        if not all(wait.settled for wait in waits):
            loop.exec()
    finally:
        outcomes = [wait.close() for wait in waits]
    return outcomes


def fetch(url: str, body: Optional[bytes] = None, headers: Optional[Mapping[str, str]] = None,
          max_bytes: int = DEFAULT_MAX_BYTES, timeout_ms: int = DEFAULT_TIMEOUT_MS,
          done: Optional[Callable[[bytes], bool]] = None, headers_only: bool = False,
          sink: Optional[Callable[[bytes], object]] = None, decompress_freely: bool = False) -> BoundedReply:
    """GET, or POST with ``body``. ``done`` ends the wait early, for a stream a server does not close.

    ``sink`` receives the answer piece by piece (a file being written) instead of the reply holding it: the
    content of the reply is then empty, and an answer cut before its end is a failure, never a shorter file.
    ``decompress_freely`` lifts the ratio check of Qt 6 on a compressed answer (a repetitive CSV sent gzipped would
    end as an error, read as a cut): ``max_bytes`` bounds what is decompressed anyway.

    Raises:
        HttpFailure: No answer, too long, too large, cut, or stopped.
    """
    outcome = fetch_together([{
        "url": url, "body": body, "headers": headers, "max_bytes": max_bytes, "timeout_ms": timeout_ms, "done": done,
        "headers_only": headers_only, "sink": sink, "decompress_freely": decompress_freely}])[0]
    if isinstance(outcome, HttpFailure):
        raise outcome
    return outcome

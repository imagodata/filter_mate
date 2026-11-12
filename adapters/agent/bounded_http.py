# -*- coding: utf-8 -*-
"""A request whose cost is bounded, for answers that come from servers nobody here controls.

``QgsBlockingNetworkRequest`` follows redirects, restarts its timeout at every byte and holds the whole answer before
its size can be checked, so a server could send the request elsewhere, freeze QGIS or fill its memory. Here a redirect
is an answer like another, the total time and the size are capped, and the user can stop it. The manager is a private
one: a 401 or a TLS error is a failure, not a dialog that a remote server gets to word.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Dict, Iterator, Mapping, Optional

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
    manager = QNetworkAccessManager()
    manager.setProxy(QgsNetworkAccessManager.instance().fallbackProxy())
    request = QNetworkRequest(QUrl(url))
    request.setRawHeader(b"User-Agent", _USER_AGENT)
    for name, value in (headers or {}).items():
        request.setRawHeader(name.encode("ascii"), value.encode("utf-8"))
    request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
    if decompress_freely and hasattr(request, "setDecompressedSafetyCheckThreshold"):  # Qt 6.2 and later
        request.setDecompressedSafetyCheckThreshold(-1)
    reply = manager.post(request, QByteArray(body)) if body is not None else manager.get(request)
    buffer = bytearray()
    received = [0]
    state: Dict[str, Optional[str]] = {"failure": None}
    loop = QEventLoop()

    def status_code() -> int:
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        return int(status) if isinstance(status, int) else 0

    def fail(message: str) -> None:
        state["failure"] = state["failure"] or message
        loop.quit()

    def keep(chunk: bytes) -> None:
        received[0] += len(chunk)
        if received[0] > max_bytes:
            fail(TOO_LARGE)
        elif sink is None:
            buffer.extend(chunk)
        else:
            try:
                sink(chunk)
            except OSError:  # raised from a Qt slot it would end QGIS
                fail("what the server sent could not be written to disk")

    def on_data() -> None:
        if state["failure"]:
            return
        chunk = bytes(reply.readAll())
        keep(chunk)
        if not state["failure"] and done is not None and (b"\n\n" in chunk or b"\r\n\r\n" in chunk) \
                and done(bytes(buffer)):
            loop.quit()

    def on_headers() -> None:
        if headers_only and status_code():
            loop.quit()

    def on_stop() -> None:
        fail(STOPPED)

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: fail(TOO_LONG))
    reply.readyRead.connect(on_data)
    reply.metaDataChanged.connect(on_headers)
    reply.finished.connect(loop.quit)
    entry = (_OWNER[0], on_stop)
    _ACTIVE.append(entry)
    try:
        timer.start(timeout_ms)
        if not reply.isFinished():
            loop.exec()
        timer.stop()
        if reply.isOpen() and not state["failure"]:
            keep(bytes(reply.readAll()))
        status = status_code()
        pairs = {bytes(name).decode("latin-1").lower(): bytes(value).decode("latin-1")
                 for name, value in reply.rawHeaderPairs()}
        message = reply.errorString()
        broken = reply.isFinished() and reply.error() != QNetworkReply.NetworkError.NoError
        no_answer = not status and broken
        tls_refused = no_answer and reply.error() == QNetworkReply.NetworkError.SslHandshakeFailedError
        cut = sink is not None and 200 <= status < 300 and (broken or not reply.isFinished())
    finally:
        _ACTIVE.remove(entry)
        reply.readyRead.disconnect(on_data)
        reply.metaDataChanged.disconnect(on_headers)
        reply.abort()
        reply.deleteLater()
        manager.deleteLater()
    if state["failure"]:
        raise HttpFailure(str(state["failure"]))
    if no_answer:
        if tls_refused:
            raise HttpFailure("its security certificate is not valid for this address, so the connection was refused "
                              "(" + (message or "TLS error") + ")")
        raise HttpFailure(message or "network error")
    if cut:
        raise HttpFailure("the connection was lost before the end of the file")
    return BoundedReply(status, pairs, bytes(buffer))

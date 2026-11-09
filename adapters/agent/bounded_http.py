# -*- coding: utf-8 -*-
"""A request whose cost is bounded, for answers that come from servers nobody here controls.

``QgsBlockingNetworkRequest`` follows redirects, restarts its timeout at every byte and holds the whole answer before
its size can be checked, so a server could send the request elsewhere, freeze QGIS or fill its memory. Here a redirect
is an answer like another, the total time and the size are capped, and the user can stop it. The manager is a private
one: a 401 or a TLS error is a failure, not a dialog that a remote server gets to word.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Mapping, Optional

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QByteArray, QEventLoop, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

DEFAULT_MAX_BYTES = 8 * 1024 * 1024
DEFAULT_TIMEOUT_MS = 60_000
_USER_AGENT = b"FilterMate-QGIS-plugin"
_ACTIVE = []


class HttpFailure(Exception):
    """The request did not get an answer; the message can be shown."""


@dataclass(frozen=True)
class BoundedReply:
    status: int
    headers: Mapping[str, str]  # names in lower case: servers disagree on their case
    content: bytes


def abort_active() -> None:
    """The user pressed Stop."""
    for stop in list(_ACTIVE):
        stop()


def fetch(url: str, body: Optional[bytes] = None, headers: Optional[Mapping[str, str]] = None,
          max_bytes: int = DEFAULT_MAX_BYTES, timeout_ms: int = DEFAULT_TIMEOUT_MS,
          done: Optional[Callable[[bytes], bool]] = None, headers_only: bool = False) -> BoundedReply:
    """GET, or POST with ``body``. ``done`` ends the wait early, for a stream a server does not close.

    Raises:
        HttpFailure: No answer, too long, too large, or stopped.
    """
    manager = QNetworkAccessManager()
    manager.setProxy(QgsNetworkAccessManager.instance().fallbackProxy())
    request = QNetworkRequest(QUrl(url))
    request.setRawHeader(b"User-Agent", _USER_AGENT)
    for name, value in (headers or {}).items():
        request.setRawHeader(name.encode("ascii"), value.encode("utf-8"))
    request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
    reply = manager.post(request, QByteArray(body)) if body is not None else manager.get(request)
    buffer = bytearray()
    state: Dict[str, Optional[str]] = {"failure": None}
    loop = QEventLoop()

    def status_code() -> int:
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        return int(status) if isinstance(status, int) else 0

    def fail(message: str) -> None:
        state["failure"] = state["failure"] or message
        loop.quit()

    def on_data() -> None:
        chunk = bytes(reply.readAll())
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            fail("the server answered with too much data")
        elif done is not None and (b"\n\n" in chunk or b"\r\n\r\n" in chunk) and done(bytes(buffer)):
            loop.quit()

    def on_headers() -> None:
        if headers_only and status_code():
            loop.quit()

    def on_stop() -> None:
        fail("stopped")

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: fail("the server took too long to answer"))
    reply.readyRead.connect(on_data)
    reply.metaDataChanged.connect(on_headers)
    reply.finished.connect(loop.quit)
    _ACTIVE.append(on_stop)
    try:
        timer.start(timeout_ms)
        if not reply.isFinished():
            loop.exec()
        timer.stop()
        on_finished_data = bytes(reply.readAll()) if reply.isOpen() else b""
        buffer.extend(on_finished_data)
        status = status_code()
        pairs = {bytes(name).decode("latin-1").lower(): bytes(value).decode("latin-1")
                 for name, value in reply.rawHeaderPairs()}
        message = reply.errorString()
        no_answer = not status and reply.isFinished() and reply.error() != QNetworkReply.NetworkError.NoError
    finally:
        _ACTIVE.remove(on_stop)
        reply.readyRead.disconnect(on_data)
        reply.metaDataChanged.disconnect(on_headers)
        reply.abort()
        reply.deleteLater()
        manager.deleteLater()
    if state["failure"]:
        raise HttpFailure(str(state["failure"]))
    if len(buffer) > max_bytes:
        raise HttpFailure("the server answered with too much data")
    if no_answer:
        raise HttpFailure(message or "network error")
    return BoundedReply(status, pairs, bytes(buffer))

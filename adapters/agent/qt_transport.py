# -*- coding: utf-8 -*-
"""Streams a provider response through ``QgsNetworkAccessManager``.

It follows the proxy and SSL settings of QGIS, and never blocks the interface.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QByteArray, QObject, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from ...core.agent.messages import (
    ERROR_NETWORK, ERROR_STREAM, ProviderError, StreamEvent, StreamFailure, TurnComplete,
)
from ...core.agent.providers.base import HttpRequest, error_from_response

logger = logging.getLogger("FilterMate.agent")
MAX_ERROR_BODY = 64 * 1024
IDLE_TIMEOUT_MS = 180_000


class QtStreamingRequest(QObject):
    """One POST; ``on_event`` gets the events and exactly one final event, then this object goes away."""

    def __init__(self, request: HttpRequest, parser, on_event: Callable[[StreamEvent], None],
                 idle_timeout_ms: int = IDLE_TIMEOUT_MS, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._parser = parser
        self._on_event = on_event
        self._over = False
        self._disposed = False
        self._error_body = bytearray()
        self._idle = QTimer(self)
        self._idle.setSingleShot(True)
        self._idle.setInterval(idle_timeout_ms)
        self._idle.timeout.connect(self._on_idle)

        network_request = QNetworkRequest(QUrl(request.url))
        for name, value in request.headers.items():
            network_request.setRawHeader(name.encode("ascii"), value.encode("utf-8"))
        # The key is in the headers: it never follows a redirection.
        network_request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                                     QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        self._reply = QgsNetworkAccessManager.instance().post(network_request, QByteArray(request.body))
        self._reply.readyRead.connect(self._on_ready_read)
        self._reply.finished.connect(self._on_finished)
        self._idle.start()

    def abort(self) -> None:
        """Stop now; no event comes afterwards."""
        if self._disposed:
            return
        self._over = True
        self._idle.stop()
        self._reply.abort()
        self._dispose()

    def _dispose(self) -> None:
        """Nothing keeps the engine, the session or the key alive once the response is over."""
        if self._disposed:
            return
        self._disposed = True
        self._idle.stop()
        self._on_event = lambda event: None
        self._parser = None
        self._reply.deleteLater()
        self.deleteLater()

    def _status(self) -> Optional[int]:
        status = self._reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        return int(status) if isinstance(status, int) else None

    def _deliver(self, events) -> None:
        for event in events:
            if self._over:
                return
            if isinstance(event, (StreamFailure, TurnComplete)):
                self._over = True
                self._idle.stop()
            self._on_event(event)

    def _feed(self, data: bytes, closing: bool = False) -> None:
        try:
            events = self._parser.feed(data)
            if closing:
                events = events + self._parser.close()
        except Exception:  # a response no parser expected
            logger.exception("Agent response could not be read")
            self._fail(ProviderError(ERROR_STREAM, "The response could not be read."))
            return
        self._deliver(events)

    def _on_ready_read(self) -> None:
        if self._over:
            return
        self._idle.start()
        data = bytes(self._reply.readAll())
        status = self._status()
        if status is not None and status >= 300:
            self._error_body.extend(data[:MAX_ERROR_BODY - len(self._error_body)])
            return
        self._feed(data)

    def _on_idle(self) -> None:
        if not self._over:
            self._fail(ProviderError(ERROR_NETWORK, "The provider stopped answering."))
            self._reply.abort()

    def _fail(self, error: ProviderError) -> None:
        if self._over:
            return
        self._over = True
        self._idle.stop()
        self._on_event(StreamFailure(error))

    def _on_finished(self) -> None:
        if not self._over:
            self._conclude()
        self._dispose()

    def _conclude(self) -> None:
        status = self._status()
        if status is not None and 300 <= status < 400:
            self._fail(ProviderError(ERROR_NETWORK, "The provider answered with a redirection, which is not followed."))
        elif status is not None and status >= 400:
            self._error_body.extend(bytes(self._reply.readAll())[:MAX_ERROR_BODY - len(self._error_body)])
            headers = {bytes(name).decode("latin-1"): bytes(value).decode("latin-1")
                       for name, value in self._reply.rawHeaderPairs()}
            self._fail(error_from_response(status, bytes(self._error_body), headers))
        elif self._reply.error() == QNetworkReply.NetworkError.OperationCanceledError:
            # Nobody here aborted: QGIS gave up, after the network timeout of its options.
            self._fail(ProviderError(ERROR_NETWORK, "QGIS stopped waiting for the provider. A slow model may need a "
                                                    "longer network timeout in the options of QGIS."))
        elif self._reply.error() != QNetworkReply.NetworkError.NoError and status is None:
            self._fail(ProviderError(ERROR_NETWORK, self._reply.errorString()))
        else:
            self._feed(bytes(self._reply.readAll()), closing=True)
            self._fail(ProviderError(ERROR_STREAM, "The response ended without a complete turn."))


class QtTransport:
    """Starts one :class:`QtStreamingRequest` per model turn."""

    def __init__(self, parent: Optional[QObject] = None, idle_timeout_ms: int = IDLE_TIMEOUT_MS) -> None:
        self._parent = parent
        self._idle_timeout_ms = idle_timeout_ms

    def start(self, request: HttpRequest, parser, on_event: Callable[[StreamEvent], None]) -> QtStreamingRequest:
        return QtStreamingRequest(request, parser, on_event, self._idle_timeout_ms, self._parent)

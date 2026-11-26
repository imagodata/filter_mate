# -*- coding: utf-8 -*-
"""One bounded, cancellable transcription POST. Loopback audio never goes through a network proxy."""
import ipaddress

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QByteArray, QObject, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkReply, QNetworkRequest

from ...core.agent.providers.base import error_from_response
from ...core.agent.speech import MAX_RESPONSE_BYTES, transcription_text


class SpeechRequest(QObject):
    def __init__(self, request, callback, parent=None, timeout_ms=120000):
        super().__init__(parent)
        self._callback, self._body, self._over = callback, bytearray(), False
        self._key = request.headers.get('Authorization', '').removeprefix('Bearer ')
        query = QNetworkRequest(QUrl(request.url))
        for name, value in request.headers.items():
            query.setRawHeader(name.encode('ascii'), value.encode('utf-8'))
        query.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                           QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        query.setAttribute(QNetworkRequest.Attribute.CacheSaveControlAttribute, False)
        host = QUrl(request.url).host()
        try:
            local = host == 'localhost' or ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = host == 'localhost'
        if local:
            self._manager = QNetworkAccessManager(self)
            self._manager.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        else:
            self._manager = QgsNetworkAccessManager.instance()
        self._reply = self._manager.post(query, QByteArray(request.body))
        self._reply.setReadBufferSize(MAX_RESPONSE_BYTES + 1)
        self._reply.readyRead.connect(self._read)
        self._reply.finished.connect(self._finished)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda: self._finish('', 'The transcription service took too long to answer.'))
        self._timer.start(timeout_ms)

    def _read(self):
        if self._over:
            return
        chunk = self._reply.read(MAX_RESPONSE_BYTES - len(self._body) + 1)
        if chunk:
            self._body.extend(bytes(chunk))
        if len(self._body) > MAX_RESPONSE_BYTES:
            self._finish('', 'The transcription response is too large.')

    def _finished(self):
        if self._over:
            return
        self._read()
        if self._over:
            return
        status = self._reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if isinstance(status, int) and 300 <= status < 400:
            self._finish('', 'The transcription service redirected the request. Check its address in Microphone settings.')
        elif isinstance(status, int) and status >= 400:
            self._finish('', f'HTTP {status}: ' + error_from_response(status, bytes(self._body)).message)
        elif self._reply.error() != QNetworkReply.NetworkError.NoError:
            self._finish('', 'The transcription service could not be reached. Check its address and connection.')
        else:
            try:
                text = transcription_text(bytes(self._body))
            except ValueError as exc:
                self._finish('', str(exc))
            else:
                self._finish(text, '')

    def _finish(self, text, error):
        if self._over:
            return
        self._over = True
        callback, self._callback = self._callback, None
        if self._key:
            error = error.replace(self._key, '…')
        self._key = ''
        self._timer.stop()
        self._body.clear()
        self._reply.abort()
        self._reply.deleteLater()
        self.deleteLater()
        if callback is not None:
            callback(text, error)

    def abort(self):
        self._callback = None
        self._finish('', '')

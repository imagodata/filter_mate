# -*- coding: utf-8 -*-
"""Listens on the loopback interface, on the Qt main thread: the tools of the plugin have to run there anyway."""
from __future__ import annotations

import logging
from collections import deque
from typing import Callable, Deque, Dict, Optional

from qgis.PyQt.QtCore import QObject, QTimer
from qgis.PyQt.QtNetwork import QAbstractSocket, QHostAddress, QNetworkProxy, QTcpServer

from ...core.agent.mcp_server import (
    MAX_BODY, MAX_HEAD, HttpReject, HttpResponse, RequestHead, check_access, read_head, render,
)

logger = logging.getLogger("FilterMate.agent")

MAX_CONNECTIONS = 16
RECEIVE_TIMEOUT_MS = 5_000  # to send a request; the time a tool takes does not count

Respond = Callable[[RequestHead, bytes], HttpResponse]
Quick = Callable[[RequestHead, bytes], bool]


class _Connection:
    """One socket until its one request is answered."""

    def __init__(self, socket, timer) -> None:
        self.socket = socket
        self.timer = timer
        self.buffer = b""
        self.head = None
        self.waiting = False


class NativeMcpServer(QObject):
    """One request per connection. Tools run one at a time and in order; what runs no tool does not wait for them."""

    def __init__(self, respond: Respond, runs_no_tool: Quick, parent=None) -> None:
        super().__init__(parent)
        self._respond = respond
        self._runs_no_tool = runs_no_tool
        self._server = QTcpServer(self)
        self._server.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        self._server.newConnection.connect(self._on_new_connection)
        self._connections: Dict[int, _Connection] = {}
        self._queue: Deque[_Connection] = deque()
        self._port = 0
        self._token: Optional[str] = None
        self._current: Optional[_Connection] = None
        self._scheduled = False
        self._running = False

    @property
    def listening(self) -> bool:
        return self._server.isListening()

    def serves(self, port: int, token: str) -> bool:
        return self.listening and self._port == port and bool(token) and self._token == token

    def listen(self, port: int, token: str) -> str:
        """Start; "" when it listens, otherwise why it does not."""
        self.close()
        if not token:
            return "no token"
        if not self._server.listen(QHostAddress("127.0.0.1"), port):
            return self._server.errorString()
        self._port, self._token = port, token
        return ""

    def close(self) -> None:
        self._server.close()
        self._queue.clear()
        for connection in list(self._connections.values()):
            connection.socket.abort()
            self._forget(connection)
        self._token = None

    def client_still_there(self) -> bool:
        """Is the client of the tool being run still waiting for its answer?"""
        return self._alive(self._current)

    def _alive(self, connection: Optional[_Connection]) -> bool:
        return (connection is not None and id(connection) in self._connections
                and connection.socket.state() == QAbstractSocket.SocketState.ConnectedState)

    def _make_room(self) -> bool:
        """A connection that has not yet said who it is gives way: idle sockets must not lock real clients out."""
        if len(self._connections) < MAX_CONNECTIONS:
            return True
        unknown = next((item for item in self._connections.values() if item.head is None and not item.waiting), None)
        if unknown is None:
            return False
        unknown.socket.abort()
        self._forget(unknown)
        return True

    def _on_new_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if not self._make_room():
                socket.write(render(HttpResponse(503)))
                socket.disconnectFromHost()
                socket.disconnected.connect(socket.deleteLater)
                continue
            socket.setReadBufferSize(MAX_HEAD + MAX_BODY + 4)
            timer = QTimer(self)
            timer.setSingleShot(True)
            connection = _Connection(socket, timer)
            self._connections[id(connection)] = connection
            timer.timeout.connect(lambda item=connection: self._send(item, HttpResponse(408)))
            socket.readyRead.connect(lambda item=connection: self._on_ready_read(item))
            socket.disconnected.connect(lambda item=connection: self._forget(item))
            timer.start(RECEIVE_TIMEOUT_MS)
            self._on_ready_read(connection)  # it may have arrived already

    def _forget(self, connection: _Connection) -> None:
        if self._connections.pop(id(connection), None) is None:
            return
        connection.timer.stop()
        connection.timer.deleteLater()
        connection.socket.deleteLater()

    def _send(self, connection: _Connection, response: HttpResponse) -> None:
        if id(connection) not in self._connections:  # the client left, or the server closed, while a tool ran
            return
        connection.timer.stop()
        connection.waiting = True  # whatever else it sends is not read
        connection.socket.write(render(response))
        connection.socket.disconnectFromHost()

    def _on_ready_read(self, connection: _Connection) -> None:
        if id(connection) not in self._connections or connection.waiting:
            return
        connection.buffer += bytes(connection.socket.readAll())
        try:
            if connection.head is None:
                connection.head = read_head(connection.buffer)
                if connection.head is None:
                    return
                refusal = check_access(connection.head, self._port, self._token or "")
                if refusal is not None:
                    self._send(connection, refusal)
                    return
        except HttpReject as exc:
            self._send(connection, HttpResponse(exc.status))
            return
        except Exception:  # a slot must not raise: what a stranger sends cannot be allowed to show a QGIS error
            logger.exception("MCP request unreadable")
            self._send(connection, HttpResponse(400))
            return
        end = connection.head.body_start + connection.head.content_length
        if len(connection.buffer) < end:
            return
        connection.buffer = connection.buffer[connection.head.body_start:end]
        connection.waiting = True
        connection.timer.stop()
        if self._runs_no_tool(connection.head, connection.buffer):
            QTimer.singleShot(0, lambda item=connection: self._answer(item))
            return
        self._queue.append(connection)
        self._schedule()

    def _answer(self, connection: _Connection) -> None:
        if not self._alive(connection):
            return
        try:
            response = self._respond(connection.head, connection.buffer)
        except Exception:
            logger.exception("MCP request failed")
            response = HttpResponse(500)
        self._send(connection, response)

    def _schedule(self) -> None:
        if not self._scheduled:
            self._scheduled = True
            QTimer.singleShot(0, self._next)

    def _next(self) -> None:
        self._scheduled = False
        if self._running or not self._queue:  # a tool can spin the event loop: the next one waits for it
            return
        connection = self._queue.popleft()
        self._running, self._current = True, connection
        try:
            self._answer(connection)
        finally:
            self._running, self._current = False, None
        if self._queue:
            self._schedule()

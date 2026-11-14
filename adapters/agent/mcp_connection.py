# -*- coding: utf-8 -*-
"""A connection to one MCP server over Streamable HTTP. Every request goes through ``bounded_http``."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ...core.agent.mcp_client import (
    PROTOCOL_VERSION, McpError, McpSessionLost, McpTimeout, RemoteTool, has_response, initialize_params,
    notification_body, parse_response, request_body, result_text, server_url_problem, tools_from_listing,
)
from ...core.agent.sources import Source
from .bounded_http import STOPPED, TOO_LONG, BoundedReply, HttpFailure, fetch_together, on_abort

CONNECT_TIMEOUT_MS = 20_000
# 2026-11-14: mcp.data.gouv.fr answered initialize in 0.3 s or in 13 s from one try to the next, and one try of 20 s
# left it out of the whole conversation. A short try first, then a long one: a server that only stalled is back in 8 s.
CONNECT_TIMEOUTS_MS = (8_000, CONNECT_TIMEOUT_MS)
CALL_TIMEOUT_MS = 60_000
_SESSION_HEADER = "mcp-session-id"


class McpConnection:
    """On the main thread between two model turns: a tool has to answer before the next one."""

    def __init__(self, source: Source) -> None:
        problem = server_url_problem(source.address)
        if problem:
            raise McpError(problem)
        self.source = source
        self.timeout_ms = CALL_TIMEOUT_MS
        self._next_id = 0
        self._session: Optional[str] = None
        self._connected = False

    def _request(self, method: str, params: Optional[Dict[str, Any]], timeout_ms: int,
                 notification: bool = False) -> Tuple[Optional[int], Dict[str, Any]]:
        """The id of a request (None for a notification) and the arguments ``bounded_http`` sends it with."""
        request_id = None
        if not notification:
            self._next_id += 1
            request_id = self._next_id
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "MCP-Protocol-Version": PROTOCOL_VERSION}
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        body = notification_body(method) if notification else request_body(request_id, method, params)
        done = None if request_id is None else (lambda data: has_response(data, request_id))
        return request_id, {"url": self.source.address, "body": body, "headers": headers, "timeout_ms": timeout_ms,
                            "done": done}

    def _answer(self, request_id: Optional[int], outcome: Union[BoundedReply, HttpFailure]) -> Dict[str, Any]:
        """The result of a request from what ``bounded_http`` got for it; {} for a notification.

        Raises:
            McpError: No answer (McpTimeout when it only took too long), a redirect, a refusal or an error.
        """
        if isinstance(outcome, HttpFailure):
            kind = McpTimeout if str(outcome) == TOO_LONG else McpError
            raise kind(f"{self.source.title}: {outcome}")
        if 300 <= outcome.status < 400:  # a redirect could lead anywhere: this address is the one the user chose
            raise McpError(f"{self.source.title} redirects elsewhere, which is not followed")
        if outcome.headers.get(_SESSION_HEADER):
            self._session = outcome.headers[_SESSION_HEADER]
        if request_id is None:
            return {}
        if outcome.status == 404 and self._session:
            raise McpSessionLost(f"{self.source.title} forgot the session")
        if outcome.status in (401, 403):
            raise McpError(f"{self.source.title} needs an account or a key")
        if outcome.status >= 300:
            raise McpError(f"{self.source.title} answered with an error ({outcome.status})")
        return parse_response(outcome.content, request_id)

    def _call(self, method: str, params: Optional[Dict[str, Any]] = None, timeout_ms: Optional[int] = None,
              notification: bool = False) -> Dict[str, Any]:
        request_id, request = self._request(method, params, timeout_ms or self.timeout_ms, notification)
        return self._answer(request_id, fetch_together([request])[0])

    def connect(self) -> None:
        self._session = None
        self._call("initialize", initialize_params(), min(self.timeout_ms, CONNECT_TIMEOUT_MS))
        self._call("notifications/initialized", None, min(self.timeout_ms, CONNECT_TIMEOUT_MS), notification=True)
        self._connected = True

    def list_tools(self) -> Tuple[RemoteTool, ...]:
        """The tools of the server, connecting first; a server that took too long is tried once more.

        Raises:
            McpError: The server did not answer, refused or failed.
        """
        if self._connected:  # the session is kept: only the listing is asked again
            return tools_from_listing(self.source.id, self.source.title,
                                      self._call("tools/list", None, min(self.timeout_ms, CONNECT_TIMEOUT_MS)))
        outcome = list_tools_together([self])[0]
        if isinstance(outcome, McpError):
            raise outcome
        return outcome

    def call_tool(self, remote_name: str, arguments: Dict[str, Any]) -> str:
        """The text of the answer. A call is sent once: it is only sent again when the session was lost.

        Raises:
            McpError: The server refused, failed or reported an error.
        """
        if not self._connected:
            self.connect()
        params = {"name": remote_name, "arguments": arguments}
        try:
            result = self._call("tools/call", params)
        except McpSessionLost:
            self.connect()
            result = self._call("tools/call", params)
        text, is_error = result_text(result)
        if is_error:
            raise McpError(text[:500] or f"{self.source.title} reported an error")
        return text


def _ask_together(connections: Sequence[McpConnection], method: str, params: Optional[Dict[str, Any]], timeout_ms: int,
                  failed: Dict[McpConnection, McpError], notification: bool = False) -> Dict[McpConnection, Dict[str, Any]]:
    """One request to each connection, all waited for at once: the result of those that answered, in order."""
    if not connections:
        return {}
    sent = [(connection, *connection._request(method, params, min(connection.timeout_ms, timeout_ms), notification))
            for connection in connections]
    answers: Dict[McpConnection, Dict[str, Any]] = {}
    for (connection, request_id, _), outcome in zip(sent, fetch_together([request for _, _, request in sent])):
        try:
            answers[connection] = connection._answer(request_id, outcome)
        except McpError as exc:
            failed[connection] = exc
    return answers


def list_tools_together(connections: Sequence[McpConnection],
                        timeouts_ms: Sequence[int] = CONNECT_TIMEOUTS_MS) -> List[Union[Tuple[RemoteTool, ...], McpError]]:
    """Connect every connection and list its tools, all of them at once.

    2026-11-14: asked one after the other, a connector that stalled (20 s) and one that was not started made the user
    wait for both before the first word of the model. Here each step (initialize, initialized, tools/list) is sent to
    all at once, so the wait is the one of the slowest. Those that took too long, and only those, get a second try
    with the next timeout of ``timeouts_ms``. Stop ends it all: nothing is sent after it, no step and no second try.

    Returns:
        For each connection, in order, its tools or the ``McpError`` it ended with (returned, not raised).
    """
    found: Dict[McpConnection, Tuple[RemoteTool, ...]] = {}
    failed: Dict[McpConnection, McpError] = {}
    pending = list(connections)
    stopped: List[bool] = []
    forget = on_abort(lambda: stopped.append(True))
    try:
        for timeout_ms in timeouts_ms:
            if not pending or stopped:
                break
            for connection in pending:
                failed.pop(connection, None)
                connection._session = None
                connection._connected = False
            alive = list(_ask_together(pending, "initialize", initialize_params(), timeout_ms, failed))
            if not stopped:
                alive = list(_ask_together(alive, "notifications/initialized", None, timeout_ms, failed, notification=True))
            listed = {} if stopped else _ask_together(alive, "tools/list", None, timeout_ms, failed)
            for connection, result in listed.items():
                try:
                    found[connection] = tools_from_listing(connection.source.id, connection.source.title, result)
                    connection._connected = True
                except McpError as exc:
                    failed[connection] = exc
            pending = [connection for connection in pending if isinstance(failed.get(connection), McpTimeout)]
    finally:
        forget()

    def outcome(connection: McpConnection) -> Union[Tuple[RemoteTool, ...], McpError]:
        if connection in found:
            return found[connection]
        if stopped or connection not in failed:  # Stop came between two steps, or no try was allowed
            return McpError(f"{connection.source.title}: {STOPPED}")
        return failed[connection]
    return [outcome(connection) for connection in connections]

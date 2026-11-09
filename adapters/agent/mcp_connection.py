# -*- coding: utf-8 -*-
"""A connection to one MCP server over Streamable HTTP. Every request goes through ``bounded_http``."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ...core.agent.mcp_client import (
    PROTOCOL_VERSION, McpError, McpSessionLost, RemoteTool, has_response, initialize_params, notification_body,
    parse_response, request_body, result_text, server_url_problem, tools_from_listing,
)
from ...core.agent.sources import Source
from .bounded_http import BoundedReply, HttpFailure, fetch

CONNECT_TIMEOUT_MS = 20_000
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

    def _post(self, body: bytes, request_id: Optional[int], timeout_ms: int) -> BoundedReply:
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "MCP-Protocol-Version": PROTOCOL_VERSION}
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        done = None if request_id is None else (lambda data: has_response(data, request_id))
        try:
            reply = fetch(self.source.address, body=body, headers=headers, timeout_ms=timeout_ms, done=done)
        except HttpFailure as exc:
            raise McpError(f"{self.source.title}: {exc}") from None
        if 300 <= reply.status < 400:  # a redirect could lead anywhere: this address is the one the user chose
            raise McpError(f"{self.source.title} redirects elsewhere, which is not followed")
        if reply.headers.get(_SESSION_HEADER):
            self._session = reply.headers[_SESSION_HEADER]
        return reply

    def _call(self, method: str, params: Optional[Dict[str, Any]] = None, timeout_ms: Optional[int] = None) -> Dict[str, Any]:
        self._next_id += 1
        reply = self._post(request_body(self._next_id, method, params), self._next_id, timeout_ms or self.timeout_ms)
        if reply.status == 404 and self._session:
            raise McpSessionLost(f"{self.source.title} forgot the session")
        if reply.status in (401, 403):
            raise McpError(f"{self.source.title} needs an account or a key")
        if reply.status >= 300:
            raise McpError(f"{self.source.title} answered with an error ({reply.status})")
        return parse_response(reply.content, self._next_id)

    def connect(self) -> None:
        self._session = None
        self._call("initialize", initialize_params(), min(self.timeout_ms, CONNECT_TIMEOUT_MS))
        self._post(notification_body("notifications/initialized"), None, min(self.timeout_ms, CONNECT_TIMEOUT_MS))
        self._connected = True

    def list_tools(self) -> Tuple[RemoteTool, ...]:
        if not self._connected:
            self.connect()
        return tools_from_listing(self.source.id, self.source.title,
                                  self._call("tools/list", None, min(self.timeout_ms, CONNECT_TIMEOUT_MS)))

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

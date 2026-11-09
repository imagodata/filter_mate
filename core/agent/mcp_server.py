# -*- coding: utf-8 -*-
"""What the MCP server built into the plugin says: HTTP reading, access rules, JSON-RPC. No Qt here.

QGIS gives no HTTP server and the plugin takes no dependency. This is the small part of Streamable HTTP a client needs:
one POST, one JSON answer, on the loopback interface, with a token. A page in a browser must not be able to reach it.
"""
from __future__ import annotations

import hmac
import json
import re
import secrets
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from .messages import ToolResultPart
from .tool_catalog import ToolSpec

PATH = "/mcp"
DEFAULT_PORT = 17823
MAX_HEAD = 16 * 1024
MAX_BODY = 4 * 1024 * 1024
MAX_SESSIONS = 32
MAX_CLIENT_NAME = 40
UNKNOWN_CLIENT = "MCP client"
EXTERNAL_MARK = "[MCP] "  # opens a step of the history made by another application: it cannot be sent again to the chat
SUPPORTED_VERSIONS = ("2025-06-18", "2025-11-25", "2025-03-26")
_LOCAL_HOSTS = ("127.0.0.1", "localhost")
_HEADER_NAME = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
_DIGITS = re.compile(r"[0-9]{1,10}")
_REASONS = {200: "OK", 202: "Accepted", 204: "No Content", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
            404: "Not Found", 405: "Method Not Allowed", 408: "Request Timeout", 411: "Length Required",
            413: "Content Too Large", 415: "Unsupported Media Type", 431: "Request Header Fields Too Large",
            500: "Internal Server Error", 501: "Not Implemented", 503: "Service Unavailable"}
_PARSE_ERROR, _INVALID_REQUEST, _METHOD_NOT_FOUND, _INVALID_PARAMS = -32700, -32600, -32601, -32602


class HttpReject(Exception):
    """The request cannot be read: answer ``status`` and close."""

    def __init__(self, status: int) -> None:
        super().__init__(str(status))
        self.status = status


@dataclass(frozen=True)
class RequestHead:
    """A request line and its headers; ``headers`` keys are in lower case."""

    method: str
    target: str
    headers: Mapping[str, str] = field(repr=False)  # the token is in there
    body_start: int
    content_length: int


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes = b""
    headers: Tuple[Tuple[str, str], ...] = ()


def read_head(buffer: bytes) -> Optional[RequestHead]:
    """The head of the request in ``buffer``, None until it is complete.

    Raises:
        HttpReject: Malformed, too large, or using what could make two readers disagree on where it ends.
    """
    end = buffer.find(b"\r\n\r\n")
    if end < 0:
        if len(buffer) > MAX_HEAD:
            raise HttpReject(431)
        return None
    if end > MAX_HEAD:
        raise HttpReject(431)
    lines = buffer[:end].decode("latin-1").split("\r\n")
    parts = lines[0].split(" ")
    if len(parts) != 3 or parts[2] not in ("HTTP/1.1", "HTTP/1.0"):
        raise HttpReject(400)
    headers: Dict[str, str] = {}
    for line in lines[1:]:
        name, separator, value = line.partition(":")
        name = name.lower()
        if not separator or not _HEADER_NAME.fullmatch(name) or "\n" in value or "\r" in value or name in headers:
            raise HttpReject(400)  # a repeated header is never needed here, and can hide a second Host or token
        headers[name] = value.strip()
    if "transfer-encoding" in headers:
        raise HttpReject(501)
    raw_length = headers.get("content-length", "")
    if raw_length and not _DIGITS.fullmatch(raw_length):
        raise HttpReject(400)
    length = int(raw_length or 0)
    if length > MAX_BODY:
        raise HttpReject(413)
    if parts[0] == "POST" and not raw_length:
        raise HttpReject(411)
    return RequestHead(parts[0], parts[1], headers, end + 4, length)


def check_access(head: RequestHead, port: int, token: str) -> Optional[HttpResponse]:
    """Why this request may not go further, None when it may. Read before its body arrives."""
    if head.headers.get("host", "").lower() not in tuple(f"{host}:{port}" for host in _LOCAL_HOSTS):
        return HttpResponse(403)  # DNS rebinding: a remote page resolving its own name to this machine
    origin = head.headers.get("origin")
    if origin is not None:
        try:
            origin_host = urlsplit(origin).hostname
        except ValueError:
            origin_host = None
        if origin_host not in _LOCAL_HOSTS:
            return HttpResponse(403)
    scheme, _, value = head.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(value.strip().encode("utf-8"), token.encode("utf-8")):
        return HttpResponse(401, headers=(("WWW-Authenticate", "Bearer"),))
    try:
        path = urlsplit(head.target).path
    except ValueError:
        return HttpResponse(404)
    if path != PATH:
        return HttpResponse(404)
    if head.method == "POST" and head.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        return HttpResponse(415)
    return None


def render(response: HttpResponse) -> bytes:
    """The bytes to send; the connection closes afterwards."""
    lines = [f"HTTP/1.1 {response.status} {_REASONS.get(response.status, 'Error')}",
             f"Content-Length: {len(response.body)}", "Connection: close"]
    if response.body:
        lines.append("Content-Type: application/json")
    lines.extend(f"{name}: {value}" for name, value in response.headers)
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + response.body


def new_token() -> str:
    return secrets.token_urlsafe(32)


def server_url(port: int) -> str:
    return f"http://127.0.0.1:{port}{PATH}"


def client_config(port: int, token: str) -> str:
    """What most MCP clients read in their configuration file."""
    return json.dumps({"mcpServers": {"filtermate": {"type": "http", "url": server_url(port),
                                                     "headers": {"Authorization": "Bearer " + token}}}}, indent=2)


def claude_code_command(port: int, token: str) -> str:
    return f'claude mcp add --transport http filtermate {server_url(port)} --header "Authorization: Bearer {token}"'


def one_line(text: str, limit: int = 400) -> str:
    """``text`` safe to show: one line, short, nothing that reorders the text around it."""
    return " ".join("".join(char if char.isprintable() else " " for char in str(text)).split())[:limit]


def client_name(info: Any) -> str:
    """What a client calls itself."""
    name = info.get("name") if isinstance(info, dict) else None
    if not isinstance(name, str):
        return UNKNOWN_CLIENT
    return one_line(name, MAX_CLIENT_NAME) or UNKNOWN_CLIENT


def _tool_listing(tool: ToolSpec) -> Dict[str, Any]:
    return {"name": tool.name, "title": tool.title or tool.name, "description": tool.description,
            "inputSchema": tool.input_schema or {"type": "object", "properties": {}},
            "annotations": {"title": tool.title or tool.name, "readOnlyHint": tool.read_only, "destructiveHint": tool.destructive,
                            "idempotentHint": tool.idempotent, "openWorldHint": tool.open_world}}


def _json(value: Any) -> bytes:
    return json.dumps(value, default=str).encode("ascii")  # escaped: a lone surrogate in a result stays sendable


def _failure(request_id: Any, code: int, message: str, status: int = 200) -> HttpResponse:
    return HttpResponse(status, _json({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}))


def _success(request_id: Any, result: Any, headers: Tuple[Tuple[str, str], ...] = ()) -> HttpResponse:
    return HttpResponse(200, _json({"jsonrpc": "2.0", "id": request_id, "result": result}), headers)


RunTool = Callable[[ToolSpec, Dict[str, Any], str], ToolResultPart]


class McpProtocol:
    """Answers one request at a time. Tools run on the caller's thread."""

    def __init__(self, list_tools: Callable[[], Sequence[ToolSpec]], run_tool: RunTool, instructions: str = "",
                 version: str = "1") -> None:
        self._list_tools = list_tools
        self._run_tool = run_tool
        self._instructions = instructions
        self._version = version
        self._sessions: "OrderedDict[str, str]" = OrderedDict()

    @staticmethod
    def runs_no_tool(head: RequestHead, body: bytes) -> bool:
        """Can it be answered while a tool works, or while the user reads a confirmation? Most can."""
        if head.method != "POST":
            return True
        try:
            message = json.loads(body.decode("utf-8"))
        except (ValueError, RecursionError):
            return True
        return not (isinstance(message, dict) and message.get("method") == "tools/call")

    def handle(self, head: RequestHead, body: bytes) -> HttpResponse:
        """The answer to a request that passed :func:`check_access`."""
        session = head.headers.get("mcp-session-id")
        if head.method == "DELETE":
            if session is None or self._sessions.pop(session, None) is None:
                return HttpResponse(404)
            return HttpResponse(204)
        if head.method != "POST":  # no stream to open: nothing is ever pushed to a client
            return HttpResponse(405, headers=(("Allow", "POST, DELETE"),))
        try:
            message = json.loads(body.decode("utf-8"))
        except (ValueError, RecursionError):
            return _failure(None, _PARSE_ERROR, "The body is not JSON.", 400)
        if isinstance(message, list):
            return _failure(None, _INVALID_REQUEST, "Batches are not supported.", 400)
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _failure(None, _INVALID_REQUEST, "Not a JSON-RPC 2.0 message.", 400)
        if "method" not in message and "result" not in message and "error" not in message:
            return _failure(None, _INVALID_REQUEST, "Not a request, a notification or a response.", 400)
        if "method" not in message or "id" not in message:  # a notification or a response: nothing to say
            return HttpResponse(202)
        request_id = message["id"]
        if isinstance(request_id, bool) or not isinstance(request_id, (str, int)):
            return _failure(None, _INVALID_REQUEST, "An id is a string or an integer.", 400)
        method, params = message["method"], message.get("params")
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return _failure(request_id, _INVALID_PARAMS, "params must be an object.")
        if method == "initialize":  # the version is negotiated here: the header comes afterwards
            return self._initialize(request_id, params)
        version = head.headers.get("mcp-protocol-version")
        if version is not None and version not in SUPPORTED_VERSIONS:
            return HttpResponse(400)
        if session is not None and session not in self._sessions:
            return HttpResponse(404)  # the client starts again with initialize, as the protocol says
        if method == "ping":
            return _success(request_id, {})
        if method == "tools/list":
            return _success(request_id, {"tools": [_tool_listing(tool) for tool in self._list_tools()]})
        if method == "tools/call":
            return self._call(request_id, params, self._sessions.get(session or "", UNKNOWN_CLIENT))
        return _failure(request_id, _METHOD_NOT_FOUND, "Method not found.")

    def _initialize(self, request_id: Any, params: Dict[str, Any]) -> HttpResponse:
        wanted = params.get("protocolVersion")
        session = secrets.token_hex(16)
        self._sessions[session] = client_name(params.get("clientInfo"))
        while len(self._sessions) > MAX_SESSIONS:
            self._sessions.popitem(last=False)
        return _success(request_id, {
            "protocolVersion": wanted if wanted in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "filtermate", "title": "FilterMate", "version": self._version},
            "instructions": self._instructions,
        }, (("Mcp-Session-Id", session),))

    def _call(self, request_id: Any, params: Dict[str, Any], client: str) -> HttpResponse:
        name, arguments = params.get("name"), params.get("arguments")
        if arguments is None:
            arguments = {}
        tool = next((item for item in self._list_tools() if item.name == name), None)
        if tool is None:
            return _failure(request_id, _INVALID_PARAMS, "Unknown tool.")
        if not isinstance(arguments, dict):
            return _failure(request_id, _INVALID_PARAMS, "arguments must be an object.")
        result = self._run_tool(tool, arguments, client)
        return _success(request_id, {"content": [{"type": "text", "text": result.content}], "isError": result.is_error})

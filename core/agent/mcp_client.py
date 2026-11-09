# -*- coding: utf-8 -*-
"""The MCP protocol as far as the chat needs it: JSON-RPC bodies, answers, tools. Pure, no network.

Remote servers are outside our trust: what they list reaches a model, so names, descriptions and
counts are bounded, and only the Streamable HTTP transport exists here (a plugin starts no process).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from .open_data import _url_problem
from .tool_catalog import ToolSpec

PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "FilterMate", "version": "5"}
MAX_TOOLS_PER_SERVER = 30
MAX_DESCRIPTION = 1000
MAX_PARAMETER_DESCRIPTION = 300
MAX_SCHEMA_CHARS = 4000
MAX_SERVER_CHARS = 40_000  # sent with every request of the conversation
_MAX_SCHEMA_DEPTH = 6
_SCHEMA_NUMBERS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "minItems", "maxItems")
_SCHEMA_TYPES = ("object", "array", "string", "number", "integer", "boolean", "null")
_LINES = re.compile(r"\r\n|\n|\r")
MAX_NAME = 64
MAX_RESULT_TEXT = 40_000
PREFIX = "mcp_"
_SEPARATOR = "__"
_LOOPBACK = ("localhost", "127.0.0.1", "::1")
_NOT_NAME = re.compile(r"[^a-zA-Z0-9_-]")


class McpError(Exception):
    """A server that failed or refused; the message can be shown."""


class McpSessionLost(McpError):
    """The server no longer knows the session: the only failure after which a call may be sent again."""


def server_url_problem(url: str) -> str:
    """Why a connector cannot be added; "" when it can: public https, or http on this machine."""
    url = (url or "").strip()
    if any(ord(char) < 33 for char in url):
        return "this address cannot be read"
    if url.lower().startswith("http://"):
        try:
            host = urlsplit(url).hostname
        except ValueError:
            return "this address cannot be read"
        return "" if host in _LOOPBACK else "a connector is reached over https, or on this machine"
    if not url.lower().startswith("https://"):
        return "a connector is reached over https, or on this machine"
    return _url_problem(url)


def request_body(request_id: int, method: str, params: Optional[Dict[str, Any]] = None) -> bytes:
    body: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        body["params"] = params
    return json.dumps(body, ensure_ascii=False).encode("utf-8", "replace")


def notification_body(method: str) -> bytes:
    return json.dumps({"jsonrpc": "2.0", "method": method}).encode("utf-8")


def initialize_params() -> Dict[str, Any]:
    return {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": CLIENT_INFO}


def _messages(data: bytes) -> List[Any]:
    """The JSON-RPC messages of an answer, plain JSON or server-sent events."""
    text = data.decode("utf-8", "replace").strip()
    if text.startswith(("{", "[")):
        try:
            value = json.loads(text)
        except (ValueError, RecursionError):
            raise McpError("the connector answered with something unreadable") from None
        return value if isinstance(value, list) else [value]
    messages = []
    for block in re.split(r"\r?\n\r?\n", text):
        # Not splitlines(): U+2028 and its kin are valid inside a JSON string.
        lines = [line[5:].lstrip() for line in _LINES.split(block) if line.startswith("data:")]
        if lines:
            try:
                messages.append(json.loads("\n".join(lines)))
            except (ValueError, RecursionError):
                continue
    return messages


def has_response(data: bytes, request_id: int) -> bool:
    """The answer to ``request_id`` has arrived, whether or not the server closes its stream."""
    try:
        return any(isinstance(message, dict) and message.get("id") == request_id for message in _messages(data))
    except McpError:
        return False


def parse_response(data: bytes, request_id: int) -> Dict[str, Any]:
    """The ``result`` answering ``request_id``.

    Raises:
        McpError: An error from the server, or an answer without that result.
    """
    for message in _messages(data):
        if not isinstance(message, dict) or message.get("id") != request_id:
            continue
        error = message.get("error")
        if error:
            detail = error.get("message") if isinstance(error, dict) else error
            raise McpError(f"the connector refused: {str(detail)[:300]}")
        result = message.get("result")
        if isinstance(result, dict):
            return result
    raise McpError("the connector did not answer the request")


@dataclass(frozen=True)
class RemoteTool:
    """A tool of a connector: how the model knows it, how the server does."""

    spec: ToolSpec
    server_id: str
    remote_name: str


def _safe_name(text: str) -> str:
    return _NOT_NAME.sub("_", text)


def tool_name(server_id: str, remote_name: str) -> str:
    """Unique in the conversation, and within the limits every provider sets on a tool name."""
    return f"{PREFIX}{_safe_name(server_id)}{_SEPARATOR}{_safe_name(remote_name)}"[:MAX_NAME]


def tools_from_listing(server_id: str, server_title: str, result: Dict[str, Any]) -> Tuple[RemoteTool, ...]:
    """The usable tools of a ``tools/list`` result, in a fixed order, bounded in number and size."""
    tools = result.get("tools")
    found: Dict[str, RemoteTool] = {}
    budget = MAX_SERVER_CHARS
    for item in sorted((tool for tool in tools or () if isinstance(tool, dict)) if isinstance(tools, list) else (),
                       key=lambda tool: str(tool.get("name"))):
        remote = item.get("name")
        schema = item.get("inputSchema")
        if not isinstance(remote, str) or not remote or not isinstance(schema, dict):
            continue
        name = tool_name(server_id, remote)
        if name in found or len(found) >= MAX_TOOLS_PER_SERVER:
            continue
        hints = item.get("annotations") if isinstance(item.get("annotations"), dict) else {}
        description = " ".join(str(item.get("description") or "").split())[:MAX_DESCRIPTION]
        bounded = _bounded_schema(schema)
        cost = len(description) + len(json.dumps(bounded))
        if cost > budget:
            continue
        budget -= cost
        found[name] = RemoteTool(ToolSpec(
            name=name, description=f"[External connector {server_title}] {description}", input_schema=bounded,
            title=_safe_name(remote)[:80], read_only=hints.get("readOnlyHint") is True,
            destructive=hints.get("destructiveHint") is True, open_world=True), server_id, remote)
    return tuple(found.values())


def _clean_schema(schema: Any, depth: int = 0) -> Dict[str, Any]:
    """Only well-formed keywords: a provider refuses a whole request over one malformed tool."""
    if not isinstance(schema, dict) or depth > _MAX_SCHEMA_DEPTH:
        return {}
    clean: Dict[str, Any] = {}
    kind = schema.get("type")
    if isinstance(kind, str) and kind in _SCHEMA_TYPES:
        clean["type"] = kind
    elif isinstance(kind, list) and kind and all(item in _SCHEMA_TYPES for item in kind if isinstance(item, str)) \
            and all(isinstance(item, str) for item in kind):
        clean["type"] = kind
    if isinstance(schema.get("description"), str):
        clean["description"] = " ".join(schema["description"].split())[:MAX_PARAMETER_DESCRIPTION]
    for key in _SCHEMA_NUMBERS:
        value = schema.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            clean[key] = value
    if isinstance(schema.get("enum"), list) and schema["enum"]:
        clean["enum"] = [item for item in schema["enum"][:100] if isinstance(item, (str, int, float, bool)) or item is None]
    if isinstance(schema.get("properties"), dict):
        clean["properties"] = {name[:MAX_NAME]: _clean_schema(item, depth + 1)
                               for name, item in schema["properties"].items() if isinstance(name, str)}
    if isinstance(schema.get("required"), list):
        known = clean.get("properties", {})
        clean["required"] = [name for name in schema["required"] if isinstance(name, str) and name in known]
    if isinstance(schema.get("items"), dict):
        clean["items"] = _clean_schema(schema["items"], depth + 1)
    if isinstance(schema.get("anyOf"), list):
        options = [_clean_schema(item, depth + 1) for item in schema["anyOf"] if isinstance(item, dict)]
        if options:
            clean["anyOf"] = options
    if isinstance(schema.get("additionalProperties"), bool):
        clean["additionalProperties"] = schema["additionalProperties"]
    if "default" in schema and isinstance(schema["default"], (str, int, float, bool, type(None))):
        clean["default"] = schema["default"]
    return clean


def _bounded_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Always an object schema, well-formed; one still unreasonably large accepts any object."""
    try:
        bounded = _clean_schema(schema)
        if len(json.dumps(bounded)) > MAX_SCHEMA_CHARS:
            return {"type": "object", "properties": {}}
    except (TypeError, ValueError, RecursionError):
        return {"type": "object", "properties": {}}
    bounded["type"] = "object"
    bounded.setdefault("properties", {})
    return bounded


def result_text(result: Dict[str, Any]) -> Tuple[str, bool]:
    """``(text, is_error)`` of a ``tools/call`` result: its text blocks, or its structured content."""
    is_error = result.get("isError") is True
    content = result.get("content")
    parts: Sequence[str] = [item["text"] for item in content if isinstance(item, dict) and isinstance(item.get("text"), str)] \
        if isinstance(content, list) else []
    text = "\n".join(parts)
    if not text and "structuredContent" in result:
        text = json.dumps(result["structuredContent"], ensure_ascii=False, default=str)
    return text[:MAX_RESULT_TEXT], is_error

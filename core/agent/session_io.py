# -*- coding: utf-8 -*-
"""Keep a conversation from one project session to the next, and take it up again. Pure: storage is the caller's.

Only the display (``core/agent/transcript.py``) was kept until now: reopening the project, restarting QGIS or
changing the settings started the model afresh, with a recap of a few lines. What is dumped here is the real
conversation (``AgentSession.messages``: requests, tool calls and their results), so the model truly remembers.

The images of tool results are left out: they go with the request they were taken in only (``session._without_images``).
Anything odd is dropped, never interpreted, and nothing is ever raised: a stored conversation that cannot be read is
simply not resumed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .messages import (
    ROLE_ASSISTANT, ROLE_USER, Message, OpaquePart, TextPart, ToolCallPart, ToolResultPart, Usage,
)

VERSION = 1
# The stored JSON is trimmed to the newest messages that fit, whole, so a long conversation cannot fill the settings.
MAX_STORED_CHARS = 250_000


@dataclass(frozen=True)
class SavedSession:
    """A conversation kept earlier: who it talked to, and what was said."""

    preset: str
    model: str
    messages: Tuple[Message, ...] = ()
    usage: Usage = Usage()
    summarized: int = 0
    context: str = ""


def _part_to_dict(part: Any) -> Optional[Dict[str, Any]]:
    if isinstance(part, TextPart):
        return {"type": "text", "text": part.text}
    if isinstance(part, ToolCallPart):
        return {"type": "call", "call_id": part.call_id, "name": part.name,
                "arguments": part.arguments, "parse_error": part.parse_error}
    if isinstance(part, ToolResultPart):
        # Images belong to the request they were taken in: never stored.
        return {"type": "result", "call_id": part.call_id, "content": part.content, "is_error": part.is_error}
    if isinstance(part, OpaquePart):
        return {"type": "opaque", "provider": part.provider, "data": part.data}
    return None


def _part_from_dict(item: Any) -> Optional[Any]:
    if not isinstance(item, dict):
        return None
    kind = item.get("type")
    try:
        if kind == "text" and isinstance(item.get("text"), str):
            return TextPart(item["text"])
        if kind == "call" and isinstance(item.get("call_id"), str) and isinstance(item.get("name"), str):
            arguments = item.get("arguments")
            error = item.get("parse_error")
            return ToolCallPart(item["call_id"], item["name"],
                                arguments if isinstance(arguments, dict) else {},
                                error if isinstance(error, str) or error is None else None)
        if kind == "result" and isinstance(item.get("call_id"), str) and isinstance(item.get("content"), str):
            return ToolResultPart(item["call_id"], item["content"], bool(item.get("is_error", False)))
        if kind == "opaque" and isinstance(item.get("provider"), str):
            data = item.get("data")
            return OpaquePart(item["provider"], data if isinstance(data, dict) else {})
    except (TypeError, ValueError):
        return None
    return None


def _message_to_dict(message: Message) -> Optional[Dict[str, Any]]:
    if not isinstance(message, Message) or message.role not in (ROLE_USER, ROLE_ASSISTANT):
        return None
    parts = []
    for part in message.parts:
        item = _part_to_dict(part)
        if item is not None:
            parts.append(item)
    if not parts:
        return None
    return {"role": message.role, "parts": parts}


def _message_from_dict(item: Any) -> Optional[Message]:
    if not isinstance(item, dict) or item.get("role") not in (ROLE_USER, ROLE_ASSISTANT):
        return None
    raw = item.get("parts")
    if not isinstance(raw, list):
        return None
    parts = [part for part in (_part_from_dict(entry) for entry in raw) if part is not None]
    if not parts:
        return None
    return Message(item["role"], tuple(parts))


def _usage_to_dict(usage: Usage) -> Dict[str, int]:
    return {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
            "cache_read_tokens": usage.cache_read_tokens, "cache_write_tokens": usage.cache_write_tokens}


def _usage_from_dict(item: Any) -> Usage:
    if not isinstance(item, dict):
        return Usage()
    values = [item.get(name) for name in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")]
    if not all(isinstance(value, int) and value >= 0 for value in values):
        return Usage()
    return Usage(*values)


def _trim(messages: List[Message], usage: Usage, summarized: int, preset: str, model: str,
          context: str) -> List[Message]:
    """The newest messages whose JSON fits, whole; the oldest go first (never half a request: cuts fall where the
    in-memory compaction cuts them, before a request of the user)."""
    from .compaction import is_request
    size = len(json.dumps({"version": VERSION, "preset": preset, "model": model, "messages": [],
                           "usage": _usage_to_dict(usage), "summarized": summarized,
                           "context": context}, ensure_ascii=False))
    start = len(messages)
    for message in reversed(messages):
        # Serialize each message once for sizing. Re-encoding the growing suffix at every step froze the
        # main thread for over a second on a conversation of 2,000 short messages (quadratic work).
        extra = len(json.dumps(_message_to_dict(message), ensure_ascii=False)) + (2 if start < len(messages) else 0)
        if size + extra > MAX_STORED_CHARS:
            break
        size += extra
        start -= 1
    while start < len(messages) and not is_request(messages[start]):
        start += 1
    return messages[start:]


def dump(messages: Sequence[Message], usage: Optional[Usage] = None, summarized: int = 0,
         preset: str = "", model: str = "", context: str = "") -> str:
    """The conversation as JSON to keep; "" when it holds nothing to resume."""
    kept = [item for item in (_message_to_dict(message) for message in messages) if item is not None]
    if not kept:
        return ""
    live = [_message_from_dict(item) for item in kept]
    messages = tuple(item for item in live if item is not None)
    usage = usage or Usage()
    summarized = summarized if isinstance(summarized, int) and summarized >= 0 else 0
    preset, model, context = str(preset), str(model), str(context)
    trimmed = _trim(list(messages), usage, summarized, preset, model, context)
    if not trimmed:
        return ""
    return json.dumps({"version": VERSION, "preset": str(preset), "model": str(model),
                       "messages": [_message_to_dict(message) for message in trimmed],
                       "usage": _usage_to_dict(usage), "summarized": summarized,
                       "context": context}, ensure_ascii=False)


def parse(text: str) -> Optional[SavedSession]:
    """The conversation kept earlier; None when absent or odd (never raised, never interpreted)."""
    try:
        data = json.loads(text or "")
    except ValueError:
        return None
    if not isinstance(data, dict) or data.get("version") != VERSION:
        return None
    raw = data.get("messages")
    if not isinstance(raw, list):
        return None
    messages = tuple(item for item in (_message_from_dict(entry) for entry in raw) if item is not None)
    if not messages:
        return None
    summarized = data.get("summarized")
    preset, model, context = data.get("preset"), data.get("model"), data.get("context")
    return SavedSession(preset if isinstance(preset, str) else "", model if isinstance(model, str) else "",
                        messages, _usage_from_dict(data.get("usage")),
                        summarized if isinstance(summarized, int) and summarized >= 0 else 0,
                        context if isinstance(context, str) else "")


def resumable(text: str, preset: str = "", model: str = "", context: Optional[str] = None) -> bool:
    """Whether ``text`` holds a conversation worth resuming for this provider and model.

    Only for the same destination the data already went to: opaque blocks only their provider understands, and tool
    calls only make sense under the settings that offered them. ``context`` identifies the server, account and
    value-sharing choice; a legacy session without it cannot prove it belongs to that destination. Anything else
    falls back to the recap of the thread.
    """
    saved = parse(text)
    return saved is not None and bool(saved.messages) and (not preset or saved.preset in ("", preset)) \
        and (not model or saved.model in ("", model)) and (context is None or saved.context == context)

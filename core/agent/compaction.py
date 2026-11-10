# -*- coding: utf-8 -*-
"""A long conversation made shorter: its oldest requests become a few lines of text.

Each request of the user sends the whole conversation again. Past a budget, the oldest exchanges (a request of the
user and every turn and tool result after it) are dropped, whole, and replaced by a summary written here, without
asking a model: what was asked, what changed the project, how the answer ended. A cut falls only before a request of
the user, so no tool call is ever left without its result. The summary goes at the start of the first request kept:
roles keep alternating, as every provider wants.
"""
from __future__ import annotations

import json
from typing import List, Sequence, Tuple

from .messages import ROLE_ASSISTANT, ROLE_USER, Message, TextPart, ToolCallPart, ToolResultPart

SUMMARY_HEADER = ("Earlier in this conversation, shortened to keep it short (the project state sent with the "
                  "request below is what holds now):")
MAX_SUMMARY_LINES = 30
MAX_REQUEST_CHARS = 200
MAX_ANSWER_CHARS = 300
MAX_CHANGES = 6


def _size(message: Message) -> int:
    total = 0
    for part in message.parts:
        if isinstance(part, TextPart):
            total += len(part.text)
        elif isinstance(part, ToolResultPart):
            total += len(part.content)
        elif isinstance(part, ToolCallPart):
            total += len(part.name) + len(json.dumps(part.arguments, ensure_ascii=False, default=str))
        else:
            total += len(json.dumps(getattr(part, "data", {}), default=str))
    return total


def is_request(message: Message) -> bool:
    """A request of the user, not the results of tools."""
    return message.role == ROLE_USER and bool(message.parts) and isinstance(message.parts[0], TextPart) \
        and not any(isinstance(part, ToolResultPart) for part in message.parts)


def _cut(text: str, size: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= size else text[:size] + "…"


def _earlier_lines(message: Message) -> List[str]:
    """The lines of a summary this request already starts with."""
    first = message.parts[0]
    if isinstance(first, TextPart) and first.text.startswith(SUMMARY_HEADER):
        return [line for line in first.text.splitlines()[1:] if line.strip()]
    return []


def _own_text(message: Message) -> str:
    """The words of the user: neither an earlier summary nor the project state that follows them."""
    texts = [part.text for part in message.parts if isinstance(part, TextPart)]
    if texts and texts[0].startswith(SUMMARY_HEADER):
        texts = texts[1:]
    return texts[0] if texts else ""


def _line(exchange: Sequence[Message], writes: Sequence[str]) -> str:
    request = _cut(_own_text(exchange[0]), MAX_REQUEST_CHARS)
    changes: List[str] = []
    answer = ""
    for message in exchange[1:]:
        if message.role == ROLE_ASSISTANT:
            for call in message.tool_calls:
                if call.name in writes:
                    target = call.arguments.get("layer_name") or call.arguments.get("layer") or \
                        call.arguments.get("algorithm_id") or ", ".join(map(str, call.arguments.get("layers") or ()))
                    changes.append(f"{call.name} {target}".strip())
            if message.text.strip():
                answer = message.text
    line = f"- asked: {request}"
    if changes:
        shown = changes[:MAX_CHANGES] + ([f"and {len(changes) - MAX_CHANGES} more"] if len(changes) > MAX_CHANGES else [])
        line += f" | changed: {'; '.join(shown)}"
    if answer:
        line += f" | answered: {_cut(answer, MAX_ANSWER_CHARS)}"
    return line


def compact(messages: Sequence[Message], budget: int, writes: Sequence[str] = ()) -> Tuple[List[Message], int]:
    """``messages`` within ``budget`` characters when it can be done, and how many requests were summed up.

    The most recent requests are kept whole, as many as fit; at least the last one always is. ``writes`` are the
    names of the tools that change the project: the summary names what they changed.
    """
    messages = list(messages)
    if sum(_size(message) for message in messages) <= budget:
        return messages, 0
    starts = [index for index, message in enumerate(messages) if is_request(message)]
    if len(starts) < 2:
        return messages, 0
    keep_from = starts[-1]
    kept_size = sum(_size(message) for message in messages[keep_from:])
    for start in reversed(starts[:-1]):
        size = sum(_size(message) for message in messages[start:keep_from])
        if kept_size + size + 2000 > budget:  # room for the summary
            break
        keep_from, kept_size = start, kept_size + size
    if keep_from == starts[0]:
        return messages, 0
    lines: List[str] = []
    dropped = [start for start in starts if start < keep_from]
    for position, start in enumerate(dropped):
        end = dropped[position + 1] if position + 1 < len(dropped) else keep_from
        lines.extend(_earlier_lines(messages[start]))
        lines.append(_line(messages[start:end], writes))
    lines = lines[-MAX_SUMMARY_LINES:]
    summary = TextPart("\n".join([SUMMARY_HEADER] + lines))
    # Only the first request can hold a summary, and it is among the dropped ones: the request kept has none.
    return [Message(ROLE_USER, (summary,) + messages[keep_from].parts)] + messages[keep_from + 1:], len(dropped)

# -*- coding: utf-8 -*-
"""Ollama's own ``/api/chat`` format: the one that lets the request say how much context the model needs.

Ollama loads a model with 4096 tokens of context unless told otherwise, and its OpenAI-compatible endpoint ignores
any attempt to say more (measured with Ollama 0.30.10, 2026-11-11). A request of the agent carries about 18,000 tokens
of system prompt and tool definitions before the conversation: through ``/v1`` the model never saw the tools nor the
request, and answered nothing useful. Here ``options.num_ctx`` grows with the request, in three steps only: each
new size makes Ollama load the model again, which takes seconds.

The response is newline-delimited JSON, one object per line, the last one with ``done``. A model that thinks
(``message.thinking``) keeps its thoughts: only ``message.content`` is the answer, and a turn that only thought (a
small model, after its tools, may have nothing to add) ends the request without an error.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from ..messages import (
    ERROR_STREAM, ROLE_ASSISTANT, ROLE_USER, STOP_END, STOP_MAX_TOKENS, STOP_OTHER, STOP_TOOL_USE, Message,
    ProviderError, StreamEvent, StreamFailure, TextDelta, TextPart, ToolCallPart, ToolResultPart, TurnComplete, Usage,
)
from ..tool_catalog import ToolSpec
from .base import HttpRequest, ProviderConfig, check_base_url, encode_json

# Context sizes asked of Ollama, the smallest that holds the request and an answer: 16k for the filtering tools of a
# local model (core/agent/tool_catalog.FILTERING_TOOLS) and a short conversation, 32k with every tool, then 64k;
# beyond, the compaction of the history keeps it short. The KV cache of an 8-billion model takes about 4.5 GB at 32k.
CONTEXT_STEPS = (16_384, 32_768, 65_536)
CHARS_PER_TOKEN = 3.5  # measured 4.15 to 4.8 with qwen3.5 and qwen3 (2026-11-11): a margin of 15 %
ANSWER_ROOM = 4_096  # tokens left for the answer of the model
_STOP_REASONS = {"stop": STOP_END, "length": STOP_MAX_TOKENS}
_MAX_LINE = 4_000_000  # a line longer than this is not a chunk of a chat answer


def context_for(body_chars: int) -> int:
    """The ``num_ctx`` a request of ``body_chars`` characters asks for."""
    needed = int(body_chars / CHARS_PER_TOKEN) + ANSWER_ROOM
    for size in CONTEXT_STEPS:
        if needed <= size:
            return size
    return CONTEXT_STEPS[-1]


def native_base(url: str) -> str:
    """The address of the server, without the ``/v1`` of its OpenAI-compatible endpoint that settings may hold."""
    base = url.rstrip("/")
    return base[:-3] if base.endswith("/v1") else base


def _wire_messages(system: str, messages: Sequence[Message]) -> List[Dict[str, Any]]:
    wire: List[Dict[str, Any]] = [{"role": "system", "content": system}]
    names: Dict[str, str] = {}  # call id -> tool name: a tool message names its tool, it has no id here
    for message in messages:
        if message.role == ROLE_USER:
            images = []
            for part in message.parts:
                if isinstance(part, ToolResultPart):
                    wire.append({"role": "tool", "tool_name": names.get(part.call_id, ""), "content": part.content})
                    images.extend(data for _mime, data in part.images)
            text = message.text
            if images:  # a tool message holds text only: its images follow, in a message of the user
                wire.append({"role": "user", "content": "Images answered by the tool calls above.", "images": images})
            if text:
                wire.append({"role": "user", "content": text})
            continue
        entry: Dict[str, Any] = {"role": "assistant", "content": message.text}
        calls = []
        for call in message.tool_calls:
            names[call.call_id] = call.name
            calls.append({"function": {"name": call.name, "arguments": call.arguments}})
        if calls:
            entry["tool_calls"] = calls
        wire.append(entry)
    return wire


class OllamaChatProvider:
    """Requests and streamed responses of a local Ollama server."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.base_url:
            raise ValueError("Ollama needs the address of its server")
        self._config = config
        self._base_url = native_base(config.base_url)
        check_base_url(self._base_url, config.api_key or config.extra_headers)

    def build_request(self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> HttpRequest:
        config = self._config
        body: Dict[str, Any] = {
            "model": config.model,
            "stream": True,
            "messages": _wire_messages(system, messages),
            "tools": [{"type": "function", "function": {
                "name": tool.name, "description": tool.description, "parameters": tool.input_schema}}
                for tool in tools],
        }
        size = len(encode_json(body))
        body["options"] = {"num_ctx": context_for(size)}
        headers = {"content-type": "application/json", "accept": "application/x-ndjson"}
        if config.api_key:  # a server behind a proxy that asks for one
            headers["authorization"] = f"Bearer {config.api_key}"
        headers.update(config.extra_headers)
        return HttpRequest(f"{self._base_url}/api/chat", headers, encode_json(body))

    def new_parser(self) -> "OllamaStreamParser":
        return OllamaStreamParser()


class OllamaStreamParser:
    """Rebuilds the assistant turn from the lines of JSON Ollama streams."""

    def __init__(self) -> None:
        self._buffer = b""
        self._text: List[str] = []
        self._calls: List[ToolCallPart] = []
        self._done_reason: Optional[str] = None
        self._usage = Usage()
        self._finished = False
        self._thought = False  # the model thought, even if it then said nothing

    def feed(self, data: bytes) -> List[StreamEvent]:
        if self._finished:
            return []
        self._buffer += data
        lines = self._buffer.split(b"\n")
        self._buffer = lines.pop()
        if len(self._buffer) > _MAX_LINE:
            self._finished = True
            return [StreamFailure(ProviderError(ERROR_STREAM, "The response could not be read."))]
        return self._handle(lines)

    def close(self) -> List[StreamEvent]:
        events = self._handle([self._buffer]) if self._buffer.strip() else []
        self._buffer = b""
        if self._finished:
            return events
        self._finished = True
        events.append(StreamFailure(ProviderError(ERROR_STREAM, "The response was cut before its end.")))
        return events

    def _handle(self, lines: Sequence[bytes]) -> List[StreamEvent]:
        events: List[StreamEvent] = []
        for line in lines:
            if self._finished:
                break
            if not line.strip():
                continue
            try:
                payload = json.loads(line.decode("utf-8", "replace"))
            except (ValueError, RecursionError):
                payload = None
            if not isinstance(payload, dict):
                self._finished = True
                events.append(StreamFailure(ProviderError(ERROR_STREAM, "The response could not be read.")))
                break
            events.extend(self._on_chunk(payload))
        return events

    def _on_chunk(self, payload: Dict[str, Any]) -> List[StreamEvent]:
        if payload.get("error"):
            self._finished = True
            return [StreamFailure(ProviderError(ERROR_STREAM, str(payload["error"])[:500]))]
        events: List[StreamEvent] = []
        message = payload.get("message") or {}
        if isinstance(message, dict):
            text = message.get("content")
            if isinstance(text, str) and text:
                self._text.append(text)
                events.append(TextDelta(text))
            if message.get("thinking"):
                self._thought = True
            for call in message.get("tool_calls") or ():
                self._on_tool_call(call)
        if payload.get("done"):
            self._finished = True
            self._done_reason = str(payload.get("done_reason") or "stop")
            self._usage = Usage(int(payload.get("prompt_eval_count") or 0), int(payload.get("eval_count") or 0))
            if not self._text and not self._calls and not self._thought:
                events.append(StreamFailure(ProviderError(ERROR_STREAM, "The response was empty.")))
            else:
                events.append(self._turn())
        return events

    def _on_tool_call(self, call: Any) -> None:
        function = call.get("function") if isinstance(call, dict) else None
        if not isinstance(function, dict) or not isinstance(function.get("name"), str) or not function["name"]:
            return  # sent back as is, it would make the next request invalid
        arguments = function.get("arguments")
        error = None
        if isinstance(arguments, str):  # some models write the arguments as a JSON text
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except (ValueError, RecursionError) as exc:
                arguments, error = {}, str(exc)
        if not isinstance(arguments, dict):
            arguments, error = {}, error or "the arguments are not a JSON object"
        call_id = f"call_{len(self._calls)}"
        self._calls.append(ToolCallPart(call_id, function["name"], arguments, error))

    def _turn(self) -> TurnComplete:
        parts: List[Any] = []
        text = "".join(self._text)
        if text:
            parts.append(TextPart(text))
        parts.extend(self._calls)
        reason = _STOP_REASONS.get(self._done_reason or "stop", STOP_OTHER)
        if self._calls and reason in (STOP_END, STOP_OTHER):
            reason = STOP_TOOL_USE  # Ollama says "stop" after complete calls
        return TurnComplete(Message(ROLE_ASSISTANT, tuple(parts)), reason, self._usage)

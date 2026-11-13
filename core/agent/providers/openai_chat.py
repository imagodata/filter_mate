# -*- coding: utf-8 -*-
"""The ``/chat/completions`` format that OpenAI, Mistral, Ollama and many others speak."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from ..messages import (
    ERROR_STREAM, ROLE_ASSISTANT, ROLE_USER, STOP_END, STOP_MAX_TOKENS, STOP_OTHER, STOP_REFUSAL, STOP_TOOL_USE, Message,
    ProviderError, StreamEvent, StreamFailure, TextDelta, TextPart, ToolCallPart, ToolResultPart, TurnComplete, Usage,
)
from ..tool_catalog import ToolSpec
from .base import HttpRequest, ProviderConfig, SseDecoder, check_base_url, encode_json, parse_tool_arguments

_STOP_REASONS = {"stop": STOP_END, "tool_calls": STOP_TOOL_USE, "function_call": STOP_TOOL_USE,
                 "length": STOP_MAX_TOKENS, "content_filter": STOP_REFUSAL}


def _wire_messages(system: str, messages: Sequence[Message]) -> List[Dict[str, Any]]:
    wire: List[Dict[str, Any]] = [{"role": "system", "content": system}]
    for message in messages:
        if message.role == ROLE_USER:
            images = []
            for part in message.parts:
                if isinstance(part, ToolResultPart):
                    wire.append({"role": "tool", "tool_call_id": part.call_id, "content": part.content})
                    images.extend((part.call_id, mime, data) for mime, data in part.images)
            if images:  # a tool message holds text only: its images follow, in a message of the user
                content: List[Dict[str, Any]] = []
                for call_id, mime, data in images:
                    content.append({"type": "text", "text": f"Image answered by the tool call {call_id}:"})
                    content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}})
                wire.append({"role": "user", "content": content})
            text = message.text
            if text:
                wire.append({"role": "user", "content": text})
            continue
        entry: Dict[str, Any] = {"role": "assistant", "content": message.text}
        calls = [{"id": call.call_id, "type": "function",
                  "function": {"name": call.name, "arguments": json.dumps(call.arguments, ensure_ascii=False)}}
                 for call in message.tool_calls]
        if calls:
            entry["tool_calls"] = calls
        wire.append(entry)
    return wire


class OpenAIChatProvider:
    """Requests and streamed responses of an OpenAI-compatible endpoint."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.base_url:
            raise ValueError("an OpenAI-compatible provider needs a base URL")
        self._config = config
        self._base_url = config.base_url.rstrip("/")
        check_base_url(self._base_url, config.api_key or config.extra_headers)

    def build_request(self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> HttpRequest:
        config = self._config
        # No max_tokens: the servers disagree on its name (recent OpenAI models refuse it).
        body: Dict[str, Any] = {
            "model": config.model,
            "stream": True,
            "messages": _wire_messages(system, messages),
        }
        if tools:  # OpenAI answers 400 (empty_array) to an empty list
            body["tools"] = [{"type": "function", "function": {
                "name": tool.name, "description": tool.description, "parameters": tool.input_schema}}
                for tool in tools]
        headers = {"content-type": "application/json", "accept": "text/event-stream"}
        if config.api_key:
            headers["authorization"] = f"Bearer {config.api_key}"
        headers.update(config.extra_headers)
        return HttpRequest(f"{self._base_url}/chat/completions", headers, encode_json(body))

    def new_parser(self) -> "OpenAIStreamParser":
        return OpenAIStreamParser()


class OpenAIStreamParser:
    """Rebuilds the assistant turn, whatever liberties the server takes with the format."""

    def __init__(self) -> None:
        self._sse = SseDecoder()
        self._text: List[str] = []
        self._calls: Dict[int, Dict[str, str]] = {}
        self._finish_reason: Optional[str] = None
        self._usage = Usage()
        self._finished = False

    def feed(self, data: bytes) -> List[StreamEvent]:
        return self._handle(self._sse.feed(data))

    def close(self) -> List[StreamEvent]:
        events = self._handle(self._sse.flush())
        if self._finished:
            return events
        self._finished = True
        if self._finish_reason is not None:  # some servers never send [DONE]
            events.append(self._turn())
        else:
            events.append(StreamFailure(ProviderError(ERROR_STREAM, "The response was cut before its end.")))
        return events

    def _handle(self, raw_events: Sequence[tuple]) -> List[StreamEvent]:
        events: List[StreamEvent] = []
        for _, data in raw_events:
            if self._finished:
                break
            if data.strip() == "[DONE]":
                self._finished = True
                if self._finish_reason is None and not self._text and not self._calls:
                    events.append(StreamFailure(ProviderError(ERROR_STREAM, "The response was empty.")))
                else:
                    events.append(self._turn())
                break
            try:
                payload = json.loads(data)
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
            error = payload["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            return [StreamFailure(ProviderError(ERROR_STREAM, message or "The provider reported an error."))]
        usage = payload.get("usage")
        if isinstance(usage, dict):
            details = usage.get("prompt_tokens_details") or {}
            cached = details.get("cached_tokens") or 0
            self._usage = Usage(int(usage.get("prompt_tokens") or 0) - cached, int(usage.get("completion_tokens") or 0),
                                cached)
        events: List[StreamEvent] = []
        for choice in (payload.get("choices") or [])[:1]:
            delta = choice.get("delta") or {}
            text = delta.get("content")
            if isinstance(text, str) and text:
                self._text.append(text)
                events.append(TextDelta(text))
            for position, call in enumerate(delta.get("tool_calls") or ()):
                if isinstance(call, dict):
                    self._on_tool_call(position, call)
            if choice.get("finish_reason"):
                self._finish_reason = choice["finish_reason"]
        return events

    def _on_tool_call(self, position: int, call: Dict[str, Any]) -> None:
        # Mistral and Ollama can send a whole call per chunk, with no index or the same one.
        function = call.get("function") or {}
        index = call.get("index")
        entry_id = call.get("id")
        if not isinstance(index, int):
            index = len(self._calls) if entry_id or function.get("name") else max(self._calls, default=position)
        elif index in self._calls and entry_id and self._calls[index]["id"] and entry_id != self._calls[index]["id"]:
            index = max(self._calls) + 1
        entry = self._calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
        entry["id"] = entry_id or entry["id"]
        entry["name"] = entry["name"] or function.get("name") or ""
        arguments = function.get("arguments")
        if isinstance(arguments, dict):  # already decoded, on some servers
            arguments = json.dumps(arguments, ensure_ascii=False)
        entry["arguments"] += arguments if isinstance(arguments, str) else ""

    def _turn(self) -> TurnComplete:
        parts: List[Any] = []
        text = "".join(self._text)
        if text:
            parts.append(TextPart(text))
        for index in sorted(self._calls):
            entry = self._calls[index]
            if not entry["name"]:  # sent back as is, it would make the next request invalid
                continue
            arguments, error = parse_tool_arguments(entry["arguments"])
            parts.append(ToolCallPart(entry["id"] or f"call_{index}", entry["name"], arguments, error))
        reason = _STOP_REASONS.get(self._finish_reason or "stop", STOP_OTHER)
        if any(isinstance(part, ToolCallPart) for part in parts) and reason in (STOP_END, STOP_OTHER):
            reason = STOP_TOOL_USE  # servers say "stop", "tool_call", "eos"... after complete calls
        return TurnComplete(Message(ROLE_ASSISTANT, tuple(parts)), reason, self._usage)

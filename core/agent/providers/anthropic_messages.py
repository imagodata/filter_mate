# -*- coding: utf-8 -*-
"""Claude, through the Messages API.

Plain HTTP on purpose: the official SDK needs Python 3.10 and third-party packages, and
the plugin runs in the Python of QGIS 3.22 and later, without installing anything.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from ..messages import (
    ERROR_RATE_LIMIT, ERROR_SERVER, ERROR_STREAM, ROLE_ASSISTANT, STOP_END, STOP_MAX_TOKENS, STOP_OTHER, STOP_REFUSAL,
    STOP_TOOL_USE, Message, OpaquePart, ProviderError, StreamEvent, StreamFailure, TextDelta, TextPart, ToolCallPart,
    ToolResultPart, TurnComplete, Usage,
)
from ..tool_catalog import ToolSpec
from .base import HttpRequest, ProviderConfig, SseDecoder, check_base_url, encode_json, parse_tool_arguments

PROVIDER = "anthropic"
DEFAULT_BASE_URL = "https://api.anthropic.com"
API_VERSION = "2026-10-21"
_FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Models with a server-side fallback when a request is declined (official API only).
_FALLBACK_MODELS = frozenset({"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"})

_STOP_REASONS = {"end_turn": STOP_END, "stop_sequence": STOP_END, "tool_use": STOP_TOOL_USE,
                 "max_tokens": STOP_MAX_TOKENS, "refusal": STOP_REFUSAL}
_STREAM_ERRORS = {"rate_limit_error": ERROR_RATE_LIMIT, "overloaded_error": ERROR_SERVER, "api_error": ERROR_SERVER}


def _content(message: Message) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    for part in message.parts:
        if isinstance(part, TextPart):
            if part.text:  # the API refuses an empty text block
                blocks.append({"type": "text", "text": part.text})
        elif isinstance(part, ToolCallPart):
            blocks.append({"type": "tool_use", "id": part.call_id, "name": part.name, "input": part.arguments})
        elif isinstance(part, ToolResultPart):
            block: Dict[str, Any] = {"type": "tool_result", "tool_use_id": part.call_id, "content": part.content}
            if part.images:
                block["content"] = [{"type": "text", "text": part.content}] + [
                    {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}
                    for mime, data in part.images]
            if part.is_error:
                block["is_error"] = True
            blocks.append(block)
        elif isinstance(part, OpaquePart) and part.provider == PROVIDER:
            blocks.append(part.data)
    return blocks


class AnthropicProvider:
    """Requests and streamed responses of ``POST /v1/messages``."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._base_url = (config.base_url or DEFAULT_BASE_URL).rstrip("/")
        check_base_url(self._base_url, config.api_key or config.extra_headers)

    def _uses_fallback(self) -> bool:
        return self._base_url == DEFAULT_BASE_URL and self._config.model in _FALLBACK_MODELS

    def build_request(self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> HttpRequest:
        config = self._config
        body: Dict[str, Any] = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "stream": True,
            # Caches everything up to the last block, and follows the conversation as it grows.
            "cache_control": {"type": "ephemeral"},
            "system": [{"type": "text", "text": system}],
            **({"tools": [{"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}
                          for tool in tools]} if tools else {}),  # an empty list is refused by some servers
            "messages": [{"role": message.role, "content": _content(message)} for message in messages],
        }
        if config.effort:
            body["output_config"] = {"effort": config.effort}
        headers = {"content-type": "application/json", "accept": "text/event-stream", "anthropic-version": API_VERSION}
        if self._uses_fallback():
            body["fallbacks"] = "default"
            headers["anthropic-beta"] = _FALLBACK_BETA
        if config.api_key:
            headers["x-api-key"] = config.api_key
        headers.update(config.extra_headers)
        return HttpRequest(f"{self._base_url}/v1/messages", headers, encode_json(body))

    def new_parser(self) -> "AnthropicStreamParser":
        return AnthropicStreamParser()


class AnthropicStreamParser:
    """Rebuilds the assistant turn from the events of the stream, every block kept for the next request."""

    def __init__(self) -> None:
        self._sse = SseDecoder()
        self._blocks: Dict[int, Dict[str, Any]] = {}
        self._stop_reason: Optional[str] = None
        self._usage: Dict[str, int] = {}
        self._finished = False

    def feed(self, data: bytes) -> List[StreamEvent]:
        return self._handle(self._sse.feed(data))

    def close(self) -> List[StreamEvent]:
        events = self._handle(self._sse.flush())
        if not self._finished:
            self._finished = True
            events.append(StreamFailure(ProviderError(ERROR_STREAM, "The response was cut before its end.")))
        return events

    def _handle(self, raw_events: Sequence[tuple]) -> List[StreamEvent]:
        events: List[StreamEvent] = []
        for _, data in raw_events:
            if self._finished:
                break
            try:
                payload = json.loads(data)
            except (ValueError, RecursionError):
                payload = None
            if not isinstance(payload, dict):
                self._finished = True
                events.append(StreamFailure(ProviderError(ERROR_STREAM, "The response could not be read.")))
                break
            events.extend(self._on_event(payload))
        return events

    def _on_event(self, payload: Dict[str, Any]) -> List[StreamEvent]:
        kind = payload.get("type")
        if kind == "message_start":
            self._read_usage(payload.get("message", {}).get("usage") or {})
        elif kind == "content_block_start":
            self._start_block(payload.get("index", 0), payload.get("content_block") or {})
        elif kind == "content_block_delta":
            return self._on_delta(payload.get("index", 0), payload.get("delta") or {})
        elif kind == "message_delta":
            self._stop_reason = (payload.get("delta") or {}).get("stop_reason") or self._stop_reason
            self._read_usage(payload.get("usage") or {})
        elif kind == "message_stop":
            self._finished = True
            return [self._turn()]
        elif kind == "error":
            self._finished = True
            error = payload.get("error") or {}
            return [StreamFailure(ProviderError(_STREAM_ERRORS.get(error.get("type"), ERROR_STREAM),
                                                str(error.get("message") or "The provider reported an error.")))]
        return []

    def _read_usage(self, usage: Dict[str, Any]) -> None:
        for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            if isinstance(usage.get(key), int):
                self._usage[key] = usage[key]

    def _start_block(self, index: int, block: Dict[str, Any]) -> None:
        self._blocks[index] = {"block": dict(block), "json": ""}

    def _on_delta(self, index: int, delta: Dict[str, Any]) -> List[StreamEvent]:
        entry = self._blocks.get(index)
        if entry is None:
            return []
        kind = delta.get("type")
        block = entry["block"]
        if kind == "text_delta":
            text = delta.get("text", "")
            block["text"] = block.get("text", "") + text
            return [TextDelta(text)] if text else []
        if kind == "input_json_delta":
            entry["json"] += delta.get("partial_json", "")
        elif kind == "thinking_delta":
            block["thinking"] = block.get("thinking", "") + delta.get("thinking", "")
        elif kind == "signature_delta":  # losing it makes the block invalid on the next request
            block["signature"] = block.get("signature", "") + delta.get("signature", "")
        return []

    def _turn(self) -> TurnComplete:
        ordered = [self._blocks[index] for index in sorted(self._blocks)]
        # After a fallback in the middle of a turn, only the text of the declined model is sent back.
        last_fallback = max((i for i, entry in enumerate(ordered) if entry["block"].get("type") == "fallback"),
                            default=-1)
        parts = []
        for position, entry in enumerate(ordered):
            block = entry["block"]
            kind = block.get("type")
            if kind == "text":
                if block.get("text"):
                    parts.append(TextPart(block["text"]))
            elif position < last_fallback:
                continue
            elif kind == "thinking" and not block.get("signature"):  # cut before its end: invalid if sent back
                continue
            elif kind == "tool_use":
                arguments, error = parse_tool_arguments(entry["json"])
                if not entry["json"] and isinstance(block.get("input"), dict):
                    arguments = block["input"]
                parts.append(ToolCallPart(block.get("id", ""), block.get("name", ""), arguments, error))
            elif kind != "fallback":
                parts.append(OpaquePart(PROVIDER, block))
        usage = Usage(self._usage.get("input_tokens", 0), self._usage.get("output_tokens", 0),
                      self._usage.get("cache_read_input_tokens", 0), self._usage.get("cache_creation_input_tokens", 0))
        return TurnComplete(Message(ROLE_ASSISTANT, tuple(parts)),
                            _STOP_REASONS.get(self._stop_reason or "", STOP_OTHER), usage)

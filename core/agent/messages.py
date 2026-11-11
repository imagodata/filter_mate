# -*- coding: utf-8 -*-
"""Provider-neutral conversation model and stream events of the agent."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Union

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

STOP_END = "end"
STOP_TOOL_USE = "tool_use"
STOP_MAX_TOKENS = "max_tokens"
STOP_REFUSAL = "refusal"
STOP_OTHER = "other"

ERROR_AUTH = "auth"
ERROR_QUOTA = "quota"
ERROR_RATE_LIMIT = "rate_limit"
ERROR_BAD_REQUEST = "bad_request"
ERROR_SERVER = "server"
ERROR_NETWORK = "network"
ERROR_STREAM = "stream"


@dataclass(frozen=True)
class TextPart:
    """Text written by the user or the model."""

    text: str


@dataclass(frozen=True)
class ToolCallPart:
    """A tool the model asks to run. ``parse_error`` is set when its arguments were not valid JSON."""

    call_id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    parse_error: Optional[str] = None


@dataclass(frozen=True)
class ImageData:
    """An image a tool answers with (a render of the map), base64 encoded."""

    media_type: str
    data: str


@dataclass(frozen=True)
class ToolResultPart:
    """What a tool answered, in a user message; ``images`` only for the request it was taken in."""

    call_id: str
    content: str
    is_error: bool = False
    images: Tuple[ImageData, ...] = ()


@dataclass(frozen=True)
class OpaquePart:
    """A block only its provider understands (reasoning...), sent back unchanged to that provider."""

    provider: str
    data: Dict[str, Any] = field(default_factory=dict)


Part = Union[TextPart, ToolCallPart, ToolResultPart, OpaquePart]


@dataclass(frozen=True)
class Message:
    """One turn of the conversation."""

    role: str
    parts: Tuple[Part, ...] = ()

    @property
    def text(self) -> str:
        return "".join(part.text for part in self.parts if isinstance(part, TextPart))

    @property
    def tool_calls(self) -> Tuple[ToolCallPart, ...]:
        return tuple(part for part in self.parts if isinstance(part, ToolCallPart))


@dataclass(frozen=True)
class Usage:
    """Tokens of a model turn, or of a whole conversation once added up."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens,
                     self.cache_read_tokens + other.cache_read_tokens,
                     self.cache_write_tokens + other.cache_write_tokens)


@dataclass(frozen=True)
class ProviderError:
    """A failure a user can act on: ``kind`` is one of the ``ERROR_*`` constants."""

    kind: str
    message: str
    status: Optional[int] = None
    retry_after: Optional[float] = None


@dataclass(frozen=True)
class TextDelta:
    """More text of the answer being written."""

    text: str


@dataclass(frozen=True)
class TurnComplete:
    """The model finished a turn."""

    message: Message
    stop_reason: str
    usage: Usage = Usage()


@dataclass(frozen=True)
class StreamFailure:
    """The turn failed; nothing of it may be kept."""

    error: ProviderError


StreamEvent = Union[TextDelta, TurnComplete, StreamFailure]

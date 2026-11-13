# -*- coding: utf-8 -*-
"""One conversation with a model: what to send next, what to do with what came back.

:class:`AgentSession` holds no thread and waits for nothing, so a Qt transport can
drive it from signals. :func:`run_exchange` is the blocking way, for the evaluation bench.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Protocol, Sequence, Tuple

from .compaction import compact
from .messages import (
    ROLE_ASSISTANT, ROLE_USER, STOP_MAX_TOKENS, STOP_REFUSAL, STOP_TOOL_USE, Message, ProviderError, StreamFailure,
    TextPart, ToolCallPart, ToolResultPart, TurnComplete, Usage,
)
from .providers.base import HttpRequest, Provider
from .tool_catalog import ToolSpec
from .tool_executor import ToolExecutor

STATUS_DONE = "done"
STATUS_RUN_TOOLS = "run_tools"
STATUS_STOPPED = "stopped"

REASON_TURN_LIMIT = "turn_limit"
REASON_TRUNCATED = "truncated"
REASON_REFUSED = "refused"


@dataclass(frozen=True)
class AgentLimits:
    """Bounds of one user request."""

    max_model_turns: int = 16
    # This many model turns before the end, the tool results say so: the model finishes instead of being cut.
    warn_turns_left: int = 2
    # Past this many characters (about a quarter as many tokens), the oldest requests are summed up in a few lines
    # (core/agent/compaction.py) before a new one is sent.
    max_history_chars: int = 120_000


TURNS_LEFT_NOTE = ("{} model turns left for this request: finish what is under way and answer now. If something "
                   "cannot be done in time, say what is left.")


@dataclass(frozen=True)
class TurnDecision:
    """What the caller does after a model turn."""

    status: str
    text: str = ""
    calls: Tuple[ToolCallPart, ...] = ()
    reason: str = ""


IMAGE_GONE = " (An image of the map came with this answer; it is no longer sent: call the tool again to see it.)"


def _without_images(message: Message) -> Message:
    """An image goes with the request it was taken in only: sent again with each later one, it would weigh on all."""
    if not any(isinstance(part, ToolResultPart) and part.images for part in message.parts):
        return message
    return Message(message.role, tuple(
        ToolResultPart(part.call_id, part.content + IMAGE_GONE, part.is_error)
        if isinstance(part, ToolResultPart) and part.images else part for part in message.parts))


class AgentSession:
    """The conversation and its rules, without any transport."""

    def __init__(self, provider: Provider, tools: Sequence[ToolSpec], system: str,
                 limits: AgentLimits = AgentLimits()) -> None:
        self._provider = provider
        self._tools = tuple(tools)
        self._system = system
        self._limits = limits
        self._messages: List[Message] = []
        self._turns = 0
        self._request_start = 0
        self.usage = Usage()
        # Requests summed up so far, to say so in the interface.
        self.summarized = 0

    @property
    def messages(self) -> Tuple[Message, ...]:
        return tuple(self._messages)

    def add_user_text(self, text: str, context: str = "") -> None:
        """Start a new request of the user; ``context`` (the state of the project) follows it in the same message.

        A conversation past ``max_history_chars`` first loses its oldest requests, summed up in their place.
        """
        self._messages = [_without_images(message) for message in self._messages]
        writes = [tool.name for tool in self._tools if not tool.read_only]
        self._messages, summarized = compact(self._messages, self._limits.max_history_chars, writes)
        self.summarized += summarized
        self._request_start = len(self._messages)
        parts = (TextPart(text),) + ((TextPart(context),) if context else ())
        self._messages.append(Message(ROLE_USER, parts))
        self._turns = 0

    def offer(self, tools: Sequence[ToolSpec]) -> None:
        """More tools from the next request on (a family of tools, once its skill is loaded), after those offered:
        the start of the list stays the same for the prompt cache."""
        known = {tool.name for tool in self._tools}
        self._tools = self._tools + tuple(tool for tool in tools if tool.name not in known)

    @property
    def tool_names(self) -> Tuple[str, ...]:
        return tuple(tool.name for tool in self._tools)

    def abandon_request(self) -> None:
        """Forget the current request, after a failure or a refusal: it would be replayed with every later one."""
        del self._messages[self._request_start:]

    def next_request(self) -> HttpRequest:
        return self._provider.build_request(self._system, self._messages, self._tools)

    def new_parser(self):
        return self._provider.new_parser()

    def accept_turn(self, turn: TurnComplete) -> TurnDecision:
        """Record a finished model turn and say what comes next.

        Only a turn that says it stopped to use its tools gets them run. Any other turn
        holding tool calls stays out of the history, like a refused one: a tool call with
        no result would make every later request invalid. So does an empty turn.
        """
        self.usage = self.usage + turn.usage
        self._turns += 1
        calls = turn.message.tool_calls
        if turn.stop_reason == STOP_REFUSAL:
            self.abandon_request()
            return TurnDecision(STATUS_STOPPED, reason=REASON_REFUSED)
        if calls and turn.stop_reason != STOP_TOOL_USE:
            return TurnDecision(STATUS_STOPPED, text=turn.message.text, reason=REASON_TRUNCATED)
        if calls:
            if self._turns >= self._limits.max_model_turns:
                return TurnDecision(STATUS_STOPPED, text=turn.message.text, reason=REASON_TURN_LIMIT)
            self._messages.append(turn.message)
            return TurnDecision(STATUS_RUN_TOOLS, text=turn.message.text, calls=calls)
        if turn.message.parts:
            self._messages.append(turn.message)
        reason = REASON_TRUNCATED if turn.stop_reason == STOP_MAX_TOKENS else ""
        return TurnDecision(STATUS_STOPPED if reason else STATUS_DONE, text=turn.message.text, reason=reason)

    def add_tool_results(self, results: Sequence[ToolResultPart]) -> None:
        """Answer every call of the last turn, in one message; near the limit, with a note saying so."""
        parts = tuple(results)
        left = self._limits.max_model_turns - self._turns
        if 0 < left <= self._limits.warn_turns_left:
            parts += (TextPart(TURNS_LEFT_NOTE.format(left)),)
        self._messages.append(Message(ROLE_USER, parts))

    def assistant_text(self) -> str:
        """Text of the last answer of the model."""
        for message in reversed(self._messages):
            if message.role == ROLE_ASSISTANT:
                return message.text
        return ""


class Transport(Protocol):
    """Sends a request and blocks until the response is over, for :func:`run_exchange`."""

    def send(self, request: HttpRequest, session: AgentSession):
        """The events of the response, read with ``session.new_parser()``."""


@dataclass
class ExchangeResult:
    """How one user request ended."""

    decision: Optional[TurnDecision] = None
    error: Optional[ProviderError] = None
    calls: List[ToolCallPart] = field(default_factory=list)
    confirmations: List[ToolCallPart] = field(default_factory=list)


def run_exchange(session: AgentSession, text: str, transport: Transport, executor: ToolExecutor,
                 confirm: Callable[[ToolCallPart], bool] = lambda call: False, context: str = "") -> ExchangeResult:
    """Run one user request to its end, tools included, blocking; ``context`` goes with the request."""
    result = ExchangeResult()
    session.add_user_text(text, context)
    while True:
        turn = None
        for event in transport.send(session.next_request(), session):
            if isinstance(event, StreamFailure):
                result.error = event.error
                session.abandon_request()
                return result
            if isinstance(event, TurnComplete):
                turn = event
        if turn is None:
            result.error = ProviderError("stream", "The response ended without a complete turn.")
            session.abandon_request()
            return result
        decision = session.accept_turn(turn)
        result.decision = decision
        if decision.status != STATUS_RUN_TOOLS:
            return result
        answers = []
        for call in decision.calls:
            result.calls.append(call)
            if executor.needs_confirmation(call):
                result.confirmations.append(call)
                if not confirm(call):
                    answers.append(executor.declined(call))
                    continue
            answers.append(executor.execute(call))
        session.add_tool_results(answers)

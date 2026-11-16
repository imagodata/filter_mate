# -*- coding: utf-8 -*-
"""One conversation with a model: what to send next, what to do with what came back.

:class:`AgentSession` holds no thread and waits for nothing, so a Qt transport can
drive it from signals. :func:`run_exchange` is the blocking way, for the evaluation bench.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Collection, Dict, List, Optional, Protocol, Sequence, Tuple, Union

from .compaction import _size, compact, trim_results
from .mcp_client import PREFIX as CONNECTOR_TOOL_PREFIX
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

# Why a request broke off before its end, as the note left in the conversation says it.
CAUSE_FAILED = "failed"
CAUSE_STOPPED = "stopped"
CAUSE_REFUSED = "refused"


@dataclass(frozen=True)
class AgentLimits:
    """Bounds of one user request."""

    max_model_turns: int = 16
    # This many model turns before the end, the tool results say so: the model finishes instead of being cut.
    warn_turns_left: int = 2
    # Past this many characters (about a quarter as many tokens), the oldest requests are summed up in a few lines
    # (core/agent/compaction.py) before a new one is sent.
    max_history_chars: int = 120_000


# Token diet, lot 1: a tool added and not called during this many requests leaves the request at a compaction.
MAX_IDLE_REQUESTS = 3

TURNS_LEFT_NOTE = ("{} model turns left for this request: finish what is under way and answer now. If something "
                   "cannot be done in time, say what is left.")


@dataclass(frozen=True)
class TurnDecision:
    """What the caller does after a model turn."""

    status: str
    text: str = ""
    calls: Tuple[ToolCallPart, ...] = ()
    reason: str = ""
    # A refused request: the steps it had done that stay in the conversation (``AgentSession.interrupt_request``).
    kept: int = 0


INTERRUPTED_NOTE = ("This request broke off here: {}. The tool calls above ran, and what they changed is in place in "
                    "QGIS (the user can undo it). Do not run them again without checking the project first: when the "
                    "user asks to go on, continue from this point.")
_CAUSES = {CAUSE_FAILED: "the request to the model failed", CAUSE_STOPPED: "the user clicked Stop",
           CAUSE_REFUSED: "the model declined to go on"}
NOT_RUN = "Not run: the request was stopped before this call."

IMAGE_GONE = " (An image of the map came with this answer; it is no longer sent: call the tool again to see it.)"


def _without_images(message: Message) -> Message:
    """An image goes with the request it was taken in only: sent again with each later one, it would weigh on all."""
    if not any(isinstance(part, ToolResultPart) and part.images for part in message.parts):
        return message
    return Message(message.role, tuple(
        ToolResultPart(part.call_id, part.content + IMAGE_GONE, part.is_error)
        if isinstance(part, ToolResultPart) and part.images else part for part in message.parts))


def _holds_results(message: Message) -> bool:
    return message.role == ROLE_USER and any(isinstance(part, ToolResultPart) for part in message.parts)


class AgentSession:
    """The conversation and its rules, without any transport."""

    def __init__(self, provider: Provider, tools: Sequence[ToolSpec], system: str,
                 limits: AgentLimits = AgentLimits(), core: Collection[str] = ()) -> None:
        self._provider = provider
        self._tools = tuple(tools)
        # Token diet, lot 1: the tools offered at once (never taken out), and for each tool added since, the request
        # it was added in and the last one that called it. None of this without a core (the option off).
        self._core = frozenset(core)
        self._requests = 0
        self._added_at: Dict[str, int] = {}
        self._used_at: Dict[str, int] = {}
        # The tools the last compaction took out of the request, for the executor and use_tools to hold again.
        self.dropped: Tuple[str, ...] = ()
        self._system = system
        self._limits = limits
        self._messages: List[Message] = []
        self._turns = 0
        self._request_start = 0
        self.usage = Usage()
        # Requests summed up so far, to say so in the interface.
        self.summarized = 0
        self.rewritten = False

    @property
    def messages(self) -> Tuple[Message, ...]:
        return tuple(self._messages)

    @property
    def system(self) -> str:
        """The instructions ``next_request`` sends."""
        return self._system

    @property
    def tools(self) -> Tuple[ToolSpec, ...]:
        """The tools ``next_request`` offers, in their order."""
        return self._tools

    def add_user_text(self, text: str, context: Union[str, Callable[[bool], str]] = "") -> None:
        """Start a new request of the user; ``context`` (the state of the project) follows it in the same message.

        A conversation past ``max_history_chars`` first loses its oldest requests, summed up in their place.
        """
        first = not self._messages
        self._messages = [_without_images(message) for message in self._messages]
        writes = [tool.name for tool in self._tools if not tool.read_only]
        trimmed = 0
        if sum(_size(message) for message in self._messages) > self._limits.max_history_chars:
            # Lot 3: the results of old requests go first; requests are summed up only if that is not enough.
            self._messages, trimmed = trim_results(self._messages)
        self._messages, summarized = compact(self._messages, self._limits.max_history_chars, writes)
        self.summarized += summarized
        # Lot 3: the history was rewritten; the next context carries the whole state again.
        self.rewritten = bool(summarized or trimmed)
        if callable(context):  # the whole state at the first request and after a rewrite, what changed otherwise
            context = context(first or self.rewritten)
        self._requests += 1
        self.dropped = self._drop_idle() if self.rewritten else ()
        self._request_start = len(self._messages)
        parts = (TextPart(text),) + ((TextPart(context),) if context else ())
        self._messages.append(Message(ROLE_USER, parts))
        self._turns = 0

    def offer(self, tools: Sequence[ToolSpec]) -> None:
        """More tools from the next request on (a family of tools, once its skill is loaded), after those offered:
        the start of the list stays the same for the prompt cache."""
        known = {tool.name for tool in self._tools}
        added = tuple(tool for tool in tools if tool.name not in known)
        self._tools = self._tools + added
        if self._core:
            for tool in added:
                if tool.name not in self._core and not tool.name.startswith(CONNECTOR_TOOL_PREFIX):
                    self._added_at[tool.name] = self._requests

    def _drop_idle(self) -> Tuple[str, ...]:
        """Take out of the request the tools added and not called in the last ``MAX_IDLE_REQUESTS`` requests: at a
        compaction only, when the cache is lost anyway (the start of the request changes then)."""
        idle = sorted(name for name, added in self._added_at.items()
                      if max(added, self._used_at.get(name, 0)) < self._requests - MAX_IDLE_REQUESTS)
        for name in idle:
            self._added_at.pop(name, None)
            self._used_at.pop(name, None)
        self._tools = tuple(tool for tool in self._tools if tool.name not in idle)
        return tuple(idle)

    @property
    def tool_names(self) -> Tuple[str, ...]:
        return tuple(tool.name for tool in self._tools)

    def interrupt_request(self, cause: str, ran: Sequence[ToolResultPart] = (), forget: bool = False) -> int:
        """End the current request where it broke off (a failure, Stop, a refusal), keeping the changes it made.

        What its tools changed stays in QGIS: forgotten, the request sent again would do it twice. So when a tool
        that changes something ran, the conversation is cut after the last message of tool results (every call kept
        has its result, no turn of the model is left without its answer) and that message ends with a note saying
        why the request stopped there (``cause``, one of the ``CAUSE_*`` constants). It stays a message of results:
        the next request follows it as a message of its own, as after the turn limit.

        When nothing was changed (nothing ran, only readings, only refused or failed calls), the request is
        forgotten, as if never sent: the user sends it again whole. So it is with ``forget``, whatever ran: a
        request the server refuses for what it holds (too long for the model) would fail again with every later one.

        Args:
            cause: Why the request stopped.
            ran: The results of the first calls of the last turn, run before Stop came in the middle of the turn:
                the other calls are answered as not run. Without any, that turn is dropped.
            forget: Forget the request even when it changed something.

        Returns:
            How many calls of tools that change something ran without an error, kept or not.
        """
        last = self._messages[-1] if len(self._messages) > self._request_start else None
        if ran and last is not None and last.role == ROLE_ASSISTANT and len(ran) <= len(last.tool_calls):
            # By position, like the answers of the engine: a server may give two calls the same id.
            not_run = tuple(ToolResultPart(call.call_id, NOT_RUN, is_error=True)
                            for call in last.tool_calls[len(ran):])
            self._messages.append(Message(ROLE_USER, tuple(ran) + not_run))
        end = self._request_start
        for index in range(len(self._messages) - 1, self._request_start, -1):
            if _holds_results(self._messages[index]):
                end = index + 1
                break
        del self._messages[end:]
        changes = self._changes_done()
        if forget or not changes:
            del self._messages[self._request_start:]
            return changes
        # The note of the turns left, if any, is no longer true.
        results = tuple(part for part in self._messages[-1].parts if not isinstance(part, TextPart))
        self._messages[-1] = Message(ROLE_USER, results + (TextPart(INTERRUPTED_NOTE.format(_CAUSES[cause])),))
        return changes

    def _changes_done(self) -> int:
        """Calls of the current request that ran without an error, of tools that change something."""
        reads = {tool.name for tool in self._tools if tool.read_only}
        changes, calls = 0, ()
        for message in self._messages[self._request_start:]:
            if message.role == ROLE_ASSISTANT:
                calls = message.tool_calls
                continue
            results = [part for part in message.parts if isinstance(part, ToolResultPart)]
            # By position: a result answers the call of the same rank in the turn before it.
            changes += sum(1 for call, result in zip(calls, results) if not result.is_error and call.name not in reads)
            calls = ()
        return changes

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
            return TurnDecision(STATUS_STOPPED, reason=REASON_REFUSED, kept=self.interrupt_request(CAUSE_REFUSED))
        if calls and turn.stop_reason != STOP_TOOL_USE:
            return TurnDecision(STATUS_STOPPED, text=turn.message.text, reason=REASON_TRUNCATED)
        if calls:
            for call in calls:
                if call.name in self._added_at:
                    self._used_at[call.name] = self._requests
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
                session.interrupt_request(CAUSE_FAILED)
                return result
            if isinstance(event, TurnComplete):
                turn = event
        if turn is None:
            result.error = ProviderError("stream", "The response ended without a complete turn.")
            session.interrupt_request(CAUSE_FAILED)
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

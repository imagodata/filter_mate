# -*- coding: utf-8 -*-
"""Runs one user request at a time, without blocking: the event-driven twin of ``run_exchange``.

Transport, undo point and user interface are injected, so this module stays free of Qt.
Everything happens on the caller's thread; ``defer`` lets its event loop breathe between steps.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Protocol, Sequence, Tuple

from .messages import (
    ERROR_STREAM, ProviderError, StreamEvent, StreamFailure, TextDelta, ToolCallPart, ToolResultPart, TurnComplete,
)
from .providers.base import HttpRequest
from .session import STATUS_DONE, STATUS_RUN_TOOLS, AgentSession, TurnDecision
from .permissions import ASK, MAX_ASKED_TOGETHER, PROTECTED, REFUSE, TURNED_OFF, PermissionPolicy, asked_alone
from .tool_executor import Handler, ToolExecutor, connector_gate

logger = logging.getLogger("FilterMate.agent")

OUTCOME_DONE = "done"
OUTCOME_STOPPED = "stopped"
OUTCOME_FAILED = "failed"
OUTCOME_CANCELLED = "cancelled"

_NO_UNDO_POINT = "The undo point could not be made, so nothing was done."


@dataclass(frozen=True)
class ChatOutcome:
    """How a user request ended."""

    status: str
    reason: str = ""
    error: Optional[ProviderError] = None
    changed_layers: Tuple[str, ...] = ()


class StreamHandle(Protocol):
    def abort(self) -> None:
        """Stop the request; no event comes afterwards."""


class AsyncTransport(Protocol):
    def start(self, request: HttpRequest, parser: Any, on_event: Callable[[StreamEvent], None]) -> StreamHandle:
        """Send ``request``; ``on_event`` gets the events, ending with one TurnComplete or StreamFailure."""


class Checkpoint(Protocol):
    def begin(self, call: Optional[ToolCallPart] = None) -> None:
        """Remember the state of the layers before a change: ``call`` names the step."""

    def commit(self) -> Sequence[str]:
        """Close the request; names of the layers it really changed."""


class ChatListener(Protocol):
    def on_text(self, text: str) -> None:
        """More of the answer."""

    def on_tool_start(self, call: ToolCallPart) -> None:
        """A tool is about to run."""

    def on_tool_end(self, call: ToolCallPart, result: ToolResultPart) -> None:
        """A tool has answered."""

    def confirm(self, call: ToolCallPart) -> bool:
        """Does the user accept this call?"""

    # Optional: ``confirm_many(calls) -> bool``, one question for several calls of a turn, all or none.

    def on_finished(self, outcome: ChatOutcome) -> None:
        """The request is over."""


class ChatEngine:
    """The state of one conversation in the dock: idle, or working on a single request."""

    def __init__(self, session: AgentSession, executor: ToolExecutor, transport: AsyncTransport,
                 listener: ChatListener, checkpoint: Checkpoint,
                 defer: Callable[[Callable[[], None]], None] = lambda step: step(),
                 policy: Optional[PermissionPolicy] = None) -> None:
        self._session = session
        # Read at each call: the user may change the level, or allow a tool, while the conversation goes on.
        self._policy = policy if policy is not None else PermissionPolicy()
        self._executor = executor
        self._transport = transport
        self._listener = listener
        self._checkpoint = checkpoint
        self._defer = defer
        self._busy = False
        self._running_tools = False
        self._cancelled = False
        self._generation = 0  # an event of an earlier request is stale
        self._handle: Optional[StreamHandle] = None

    @property
    def busy(self) -> bool:
        return self._busy

    def offer_tools(self, tools, handlers: Optional[Mapping[str, Handler]] = None) -> None:
        """A family of tools, or the tools of a connector with their ``handlers``, offered from the next turn on, to
        the model and to the executor."""
        self._session.offer(tools)
        self._executor.offer(tools, handlers)

    @property
    def usage(self):
        """Tokens of the conversation so far, as the providers counted them."""
        return self._session.usage

    @property
    def summarized(self) -> int:
        """Requests of this conversation summed up so far, to keep what is sent short."""
        return self._session.summarized

    def send(self, text: str, context: str = "") -> bool:
        """Start a request; False when one is running or there is nothing to send. ``context`` goes with it."""
        if self._busy or not text.strip():
            return False
        self._busy, self._cancelled = True, False
        self._generation += 1
        self._session.add_user_text(text, context)
        self._request_model(self._generation)
        return True

    def cancel(self) -> None:
        """Stop the current request. What already changed stays, and can be undone."""
        if not self._busy:
            return
        self._cancelled = True
        if self._running_tools:  # a tool may spin the event loop: it finishes first, see _run_tools
            return
        handle, self._handle = self._handle, None
        if handle is not None:
            handle.abort()
        self._session.abandon_request()
        self._finish(ChatOutcome(OUTCOME_CANCELLED))

    def _notify(self, callback: Callable[..., None], *args: Any) -> None:
        """What the interface does with an event must not stop the request."""
        try:
            callback(*args)
        except Exception:
            logger.exception("Agent listener failed")

    def _request_model(self, generation: int) -> None:
        if not self._busy or generation != self._generation:  # stopped while this step waited for the event loop
            return
        try:
            handle = self._transport.start(self._session.next_request(), self._session.new_parser(),
                                           lambda event: self._on_event(generation, event))
        except Exception:
            logger.exception("Agent request could not be started")
            self._session.abandon_request()
            self._finish(ChatOutcome(OUTCOME_FAILED, error=ProviderError(ERROR_STREAM, "The request could not be sent.")))
            return
        if self._busy and generation == self._generation:
            self._handle = handle

    def _on_event(self, generation: int, event: StreamEvent) -> None:
        if not self._busy or generation != self._generation:
            return
        if isinstance(event, TextDelta):
            self._notify(self._listener.on_text, event.text)
        elif isinstance(event, StreamFailure):
            self._session.abandon_request()
            self._finish(ChatOutcome(OUTCOME_FAILED, error=event.error))
        elif isinstance(event, TurnComplete):
            self._handle = None
            self._after_turn(generation, self._session.accept_turn(event))

    def _after_turn(self, generation: int, decision: TurnDecision) -> None:
        if decision.status == STATUS_RUN_TOOLS:
            self._defer(lambda: self._run_tools(generation, decision.calls))
        elif decision.status == STATUS_DONE:
            self._finish(ChatOutcome(OUTCOME_DONE))
        else:
            self._finish(ChatOutcome(OUTCOME_STOPPED, reason=decision.reason))

    def _run_tools(self, generation: int, calls: Sequence[ToolCallPart]) -> None:
        if not self._busy or generation != self._generation:
            return
        self._running_tools = True
        answers = []
        try:
            answered = self._confirm_together(calls)
            for position, call in enumerate(calls):
                if self._cancelled:
                    break
                answers.append(self._run_one(call, answered.get(position)))
        finally:
            self._running_tools = False
        if self._cancelled:
            self._session.abandon_request()
            self._finish(ChatOutcome(OUTCOME_CANCELLED))
            return
        self._session.add_tool_results(answers)
        self._defer(lambda: self._request_model(generation))

    def _confirm_together(self, calls: Sequence[ToolCallPart]) -> Dict[int, bool]:
        """One question for the calls of a turn the user is asked about, when there are several.

        ``{position in calls: yes}``, by position and not by call id: a server may give two calls the same id, and
        the answer to the listed ones then reached a call that was not listed (code, run without its dialog).
        Code and the other tools asked alone (``asked_alone``) are left out: each is read in a dialog of its own;
        so are the actions past ``MAX_ASKED_TOGETHER``, which the question would not list. Loading a connector is
        judged as the connector (``connector_gate``): it reaches outside, so it is always asked alone.
        A listener without ``confirm_many`` is asked call by call, as before.
        """
        asked = [(position, call) for position, call in enumerate(calls)
                 if self._executor.verdict(call, self._policy) == ASK
                 and not asked_alone(call.name, connector_gate(call) or self._executor.spec(call.name))
                 ][:MAX_ASKED_TOGETHER]
        confirm_many = getattr(self._listener, "confirm_many", None)
        if len(asked) < 2 or confirm_many is None:
            return {}
        try:
            yes = bool(confirm_many([call for _position, call in asked]))
        except Exception:
            logger.exception("Agent confirmation failed")
            yes = False
        return {position: yes for position, _call in asked}

    def _run_one(self, call: ToolCallPart, answered: Optional[bool] = None) -> ToolResultPart:
        verdict = self._executor.verdict(call, self._policy)
        if verdict in (REFUSE, PROTECTED, TURNED_OFF):
            return self._executor.refused(call, self._policy)
        if verdict == ASK and not (answered if answered is not None else self._confirmed(call)):
            return self._executor.declined(call, self._policy)
        spec = self._executor.spec(call.name)
        if spec is not None and not spec.read_only and not spec.manages_history:
            try:
                self._checkpoint.begin(call)
            except Exception:
                logger.exception("Agent undo point failed")
                return ToolResultPart(call.call_id, _NO_UNDO_POINT, is_error=True)
        self._notify(self._listener.on_tool_start, call)
        generation = self._generation
        result = self._executor.execute(call)
        gate = connector_gate(call) if verdict == ASK else None
        if gate is not None and not result.is_error and generation == self._generation and not self._cancelled:
            # Granted once loaded only: a connector that did not answer keeps nothing, and is asked again. Nor when
            # the conversation ended while it loaded: the policy outlives it, and the yes would go to the next one.
            self._policy.grant(gate.name)
        self._notify(self._listener.on_tool_end, call, result)
        return result

    def _confirmed(self, call: ToolCallPart) -> bool:
        try:
            return bool(self._listener.confirm(call))
        except Exception:
            logger.exception("Agent confirmation failed")
            return False

    def _finish(self, outcome: ChatOutcome) -> None:
        self._busy = False
        self._handle = None
        self._generation += 1
        try:
            changed = tuple(self._checkpoint.commit())
        except Exception:
            logger.exception("Agent undo point could not be closed")
            changed = ()
        self._notify(self._listener.on_finished, ChatOutcome(outcome.status, outcome.reason, outcome.error, changed))

# -*- coding: utf-8 -*-
"""Runs one user request at a time, without blocking: the event-driven twin of ``run_exchange``.

Transport, undo point and user interface are injected, so this module stays free of Qt.
Everything happens on the caller's thread; ``defer`` lets its event loop breathe between steps, and ``delay`` waits
without blocking it before a request is sent again to a provider that was busy.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, Mapping, Optional, Protocol, Sequence, Tuple, Union

from .messages import (
    ERROR_BAD_REQUEST, ERROR_NETWORK, ERROR_RATE_LIMIT, ERROR_SERVER, ERROR_STREAM, ProviderError, StreamEvent,
    StreamFailure, TextDelta, ToolCallPart, ToolResultPart, TurnComplete,
)
from .providers.base import HttpRequest
from .session import CAUSE_FAILED, CAUSE_STOPPED, NOT_RUN, STATUS_DONE, STATUS_RUN_TOOLS, AgentSession, TurnDecision
from .permissions import ASK, MAX_ASKED_TOGETHER, PROTECTED, REFUSE, TURNED_OFF, PermissionPolicy, asked_alone
from .tool_executor import Handler, ToolExecutor, connector_gate
from .skill_commands import requested_skill

logger = logging.getLogger("FilterMate.agent")

OUTCOME_DONE = "done"
OUTCOME_STOPPED = "stopped"
OUTCOME_FAILED = "failed"
OUTCOME_CANCELLED = "cancelled"

_NO_UNDO_POINT = "The undo point could not be made, so nothing was done."

# A model turn that failed for a reason that may pass (the provider busy or rate limited, a network failure that may
# pass) is asked again, once after each of these waits in seconds, unless the provider said how long (Retry-After):
# then that long, up to MAX_RETRY_WAIT.
RETRY_WAITS = (2.0, 6.0)
MAX_RETRY_WAIT = 30.0
NO_RETRY_ABOVE = 120.0  # a Retry-After beyond this is not a busy moment: the failure is shown at once
# A tool that took this long writes its time in the log, as the other timings of FilterMate (core/agent/performance.py
# reads them for diagnose_performance). 2026-11-23: a freeze of 15 s in a cross filter of the agent showed only in
# the timing of set_subset; a slow tool elsewhere left nothing.
SLOW_TOOL_MS = 250
PUSH_NOT_RUN = "Not run: a new user message arrived. Reconsider this call using the latest instructions."


def worth_retrying(error: ProviderError) -> bool:
    """A failure that may be over in a few seconds; never a refused key, a bad request or a used-up quota."""
    wait = error.retry_after
    if wait is not None and wait > NO_RETRY_ABOVE:  # asked to come back much later (a quota of the day): not now
        return False
    return error.kind in (ERROR_RATE_LIMIT, ERROR_SERVER) or (error.kind == ERROR_NETWORK and error.transient)


def retry_wait(error: ProviderError, tries: int) -> float:
    """Seconds before the new try that follows ``tries`` earlier ones."""
    wait = error.retry_after
    if wait is None or not wait >= 0:  # NaN as well
        wait = RETRY_WAITS[min(tries, len(RETRY_WAITS) - 1)]
    return min(wait, MAX_RETRY_WAIT)


@dataclass(frozen=True)
class ChatOutcome:
    """How a user request ended."""

    status: str
    reason: str = ""
    error: Optional[ProviderError] = None
    changed_layers: Tuple[str, ...] = ()
    # A request that broke off (failed, stopped, refused): the steps it had done, kept in the conversation. They stay
    # in QGIS and the model knows them, so the request is not to be sent again whole.
    kept_steps: int = 0
    # Accepted while working, but not yet included in a request to the model. Return them if the request stops.
    pending_messages: Tuple[str, ...] = ()


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
    # Optional: ``on_retry(seconds, error)``, the provider failed for a moment: the turn is asked again after this wait.

    def on_finished(self, outcome: ChatOutcome) -> None:
        """The request is over."""


class ChatEngine:
    """The state of one conversation in the dock: idle, or working on a single request."""

    def __init__(self, session: AgentSession, executor: ToolExecutor, transport: AsyncTransport,
                 listener: ChatListener, checkpoint: Checkpoint,
                 defer: Callable[[Callable[[], None]], None] = lambda step: step(),
                 policy: Optional[PermissionPolicy] = None,
                 delay: Callable[[float, Callable[[], None]], None] = lambda seconds, step: step(),
                 released: Callable[[Sequence[str]], None] = lambda names: None,
                 auto_offer: Optional[Callable[[str], bool]] = None) -> None:
        self._session = session
        # Offers a tool the model called before it was offered (held for the token diet), True when offered:
        # the call runs in this turn instead of waiting for the model to load its tools first.
        self._auto_offer = auto_offer
        # Told the tools a compaction took out of the request (token diet, lot 1): use_tools may add them again.
        self._released = released
        # Read at each call: the user may change the level, or allow a tool, while the conversation goes on.
        self._policy = policy if policy is not None else PermissionPolicy()
        self._executor = executor
        self._transport = transport
        self._listener = listener
        self._checkpoint = checkpoint
        self._defer = defer
        self._delay = delay
        self._busy = False
        self._running_tools = False
        self._cancelled = False
        self._generation = 0  # an event of an earlier request, or of a response tried again, is stale
        self._handle: Optional[StreamHandle] = None
        self._tries = 0  # new tries of the current model turn
        self._streamed = False  # text of the current model turn was shown
        self._pushed: list[str] = []
        self._partial_answer: list[str] = []

    @property
    def busy(self) -> bool:
        return self._busy

    def offer_tools(self, tools, handlers: Optional[Mapping[str, Handler]] = None) -> None:
        """A family of tools, or the tools of a connector with their ``handlers``, offered from the next turn on, to
        the model and to the executor."""
        self._session.offer(tools)
        self._executor.offer(tools, handlers)

    @property
    def session(self) -> AgentSession:
        """The conversation, to keep it from one project session to the next (``core/agent/session_io.py``)."""
        return self._session

    @property
    def usage(self):
        """Tokens of the conversation so far, as the providers counted them."""
        return self._session.usage

    @property
    def rewritten(self) -> bool:
        """The history was rewritten (summed up, trimmed) when the last request began."""
        return bool(getattr(self._session, "rewritten", True))

    @property
    def summarized(self) -> int:
        """Requests of this conversation summed up so far, to keep what is sent short."""
        return self._session.summarized

    def send(self, text: str, context: Union[str, Callable[[bool], str]] = "") -> bool:
        """Start a request; False when one is running or there is nothing to send. ``context`` goes with it."""
        if self._busy or not text.strip():
            return False
        self._busy, self._cancelled = True, False
        self._tries = 0
        self._generation += 1
        try:
            self._session.add_user_text(text, context)
        except Exception:
            # The context is computed in there, from the project: an error must not leave the engine busy, which
            # would refuse every later request. Nothing was added to the conversation (the message goes in last), so
            # it ends as a request that could not be sent, and the interface gives it back.
            logger.exception("Agent request could not be prepared")
            self._finish(ChatOutcome(OUTCOME_FAILED, error=ProviderError(ERROR_STREAM, "The request could not be sent.")))
            return True
        dropped = tuple(getattr(self._session, "dropped", ()) or ())
        if dropped:
            self._executor.withdraw(dropped)
            self._released(dropped)
        skill = requested_skill(text)
        if skill is not None:
            call = self._session.request_skill(skill)
            generation = self._generation
            self._defer(lambda: self._run_tools(generation, (call,), requested=True))
        else:
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
        self._interrupt(OUTCOME_CANCELLED, CAUSE_STOPPED)  # a new try that waited is stale once it is over

    def push(self, text: str) -> bool:
        """Steer the running request at its next model turn, after any tool already executing finishes.

        Calls not started yet are answered as not run so the model can reconsider them with the new message.
        A provider still streaming its old answer is aborted and asked again with the text already shown and the
        correction. The undo point stays open; no second exchange is started alongside this one.
        """
        if not self._busy or self._cancelled or not text.strip():
            return False
        self._pushed.append(text.strip())
        if self._handle is not None and not self._running_tools:
            handle, self._handle = self._handle, None
            self._generation += 1  # abort may emit a final event: it belongs to the old answer
            generation = self._generation
            self._tries = 0
            self._session.keep_partial_answer("".join(self._partial_answer))
            self._partial_answer = []
            handle.abort()
            self._defer(lambda: self._request_model(generation))
        return True

    def _notify(self, callback: Callable[..., None], *args: Any) -> None:
        """What the interface does with an event must not stop the request."""
        try:
            callback(*args)
        except Exception:
            logger.exception("Agent listener failed")

    def _request_model(self, generation: int) -> None:
        if not self._busy or generation != self._generation:  # stopped while this step waited for the event loop
            return
        pushed, self._pushed = self._pushed, []
        for text in pushed:
            self._session.add_followup_text(text)
        self._streamed = False
        self._partial_answer = []
        try:
            handle = self._transport.start(self._session.next_request(), self._session.new_parser(),
                                           lambda event: self._on_event(generation, event))
        except Exception:
            logger.exception("Agent request could not be started")
            self._interrupt(OUTCOME_FAILED, CAUSE_FAILED,
                            error=ProviderError(ERROR_STREAM, "The request could not be sent."))
            return
        if self._busy and generation == self._generation:
            self._handle = handle

    def _on_event(self, generation: int, event: StreamEvent) -> None:
        if not self._busy or generation != self._generation:
            return
        if isinstance(event, TextDelta):
            self._streamed = True
            self._partial_answer.append(event.text)
            self._notify(self._listener.on_text, event.text)
        elif isinstance(event, StreamFailure):
            self._handle = None
            if not self._retry(event.error):
                self._interrupt(OUTCOME_FAILED, CAUSE_FAILED, error=event.error)
        elif isinstance(event, TurnComplete):
            self._handle = None
            self._tries = 0
            self._after_turn(generation, self._session.accept_turn(event))

    def _retry(self, error: ProviderError) -> bool:
        """Ask the model again, after a wait, for a failure that may pass; False when it is not worth it.

        Only while nothing of the turn was shown: sent again, its text would show twice. Its tool calls come with the
        end of the turn only, so none was taken yet. A Stop during the wait makes the new try stale.
        """
        if self._streamed or self._tries >= len(RETRY_WAITS) or not worth_retrying(error):
            return False
        wait = retry_wait(error, self._tries)
        self._tries += 1
        self._generation += 1  # an event the failed response would still send is stale
        generation = self._generation
        on_retry = getattr(self._listener, "on_retry", None)
        if on_retry is not None:
            self._notify(on_retry, wait, error)
        logger.info("Agent provider failed (%s), trying again in %.0f s", error.kind, wait)
        self._delay(wait, lambda: self._request_model(generation))
        return True

    def _after_turn(self, generation: int, decision: TurnDecision) -> None:
        if decision.status == STATUS_RUN_TOOLS:
            self._defer(lambda: self._run_tools(generation, decision.calls))
        elif decision.status == STATUS_DONE:
            if self._pushed:
                self._defer(lambda: self._request_model(generation))
            else:
                self._finish(ChatOutcome(OUTCOME_DONE))
        else:
            self._finish(ChatOutcome(OUTCOME_STOPPED, reason=decision.reason, kept_steps=decision.kept))

    def _run_tools(self, generation: int, calls: Sequence[ToolCallPart], *, requested: bool = False) -> None:
        if not self._busy or generation != self._generation:
            return
        self._running_tools = True
        answers = []
        try:
            answered = {} if self._pushed else self._confirm_together(calls)
            for position, call in enumerate(calls):
                if self._cancelled:
                    break
                answers.append(ToolResultPart(call.call_id, PUSH_NOT_RUN, is_error=True) if self._pushed
                               else self._run_one(call, answered.get(position)))
        finally:
            self._running_tools = False
        if self._cancelled:  # the calls that ran stay, with their results; the others are answered as not run
            self._interrupt(OUTCOME_CANCELLED, CAUSE_STOPPED, answers)
            return
        if self._auto_offer is not None and not self._pushed:
            for position, call in enumerate(calls):
                if self._cancelled or self._pushed:
                    break
                if answers[position].is_error and self._executor.is_held(call.name) and self._auto_offer(call.name):
                    # Offered now: run at once, once per call (a call still held afterwards keeps its failure).
                    # The panel shows both steps, the failure then the run, so nothing looks silently fixed.
                    answers[position] = self._run_one(call, answered.get(position))
        self._session.add_tool_results(answers)
        if requested and any(answer.is_error for answer in answers):
            self._interrupt(OUTCOME_FAILED, CAUSE_FAILED,
                            error=ProviderError(ERROR_BAD_REQUEST, 'The requested skill could not be loaded.'))
            return
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
        # One tick per action when the listener offers it (the thread asks Allow or Refuse of each):
        # None means it could not ask, and the grouped question below takes over; {} refuses everything.
        confirm_each = getattr(self._listener, "confirm_each", None)
        if len(asked) >= 2 and confirm_each is not None:
            try:
                each = confirm_each([call for _position, call in asked])
            except Exception:
                logger.exception("Agent confirmation failed")
                each = {}
            if each is not None:
                if not isinstance(each, dict):
                    each = {}
                return {position: each.get(index) is True for index, (position, _call) in enumerate(asked)}
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
        generation = self._generation
        verdict = self._executor.verdict(call, self._policy)
        if verdict in (REFUSE, PROTECTED, TURNED_OFF):
            return self._executor.refused(call, self._policy)
        if verdict == ASK and not (answered if answered is not None else self._confirmed(call)):
            return self._executor.declined(call, self._policy)
        if self._cancelled or generation != self._generation:
            return ToolResultPart(call.call_id, NOT_RUN, is_error=True)
        if self._pushed:
            return ToolResultPart(call.call_id, PUSH_NOT_RUN, is_error=True)
        verdict_now = self._executor.verdict(call, self._policy)
        if verdict_now in (REFUSE, PROTECTED, TURNED_OFF):
            return self._executor.refused(call, self._policy)
        spec = self._executor.spec(call.name)
        began = spec is not None and not spec.read_only and not spec.manages_history
        if began:
            try:
                self._checkpoint.begin(call)
            except Exception:
                logger.exception("Agent undo point failed")
                return ToolResultPart(call.call_id, _NO_UNDO_POINT, is_error=True)
        self._notify(self._listener.on_tool_start, call)
        if self._cancelled or generation != self._generation:
            return ToolResultPart(call.call_id, NOT_RUN, is_error=True)
        if self._pushed:
            return ToolResultPart(call.call_id, PUSH_NOT_RUN, is_error=True)
        started = time.monotonic()
        result = self._executor.execute(call)
        spent = (time.monotonic() - started) * 1000
        if spent >= SLOW_TOOL_MS:
            logger.info(f"⏱ agent {call.name}: {spent:.0f} ms" + (" (failed)" if result.is_error else ""))
        end = getattr(self._checkpoint, "end", None)  # optional: what the user does next is not the turn's
        end_call = getattr(self._checkpoint, 'end_call', None)
        if began and (end_call is not None or end is not None):
            try:
                end_call(call, result) if end_call is not None else end()
            except Exception:
                logger.exception("Agent undo point could not close its step")
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

    def _interrupt(self, status: str, cause: str, ran: Sequence[ToolResultPart] = (),
                   error: Optional[ProviderError] = None) -> None:
        """End a request before its end: what it ran stays in the conversation (``interrupt_request``)."""
        # A request the server refuses for what it holds would be refused again with every later one: forgotten.
        forget = error is not None and error.kind == ERROR_BAD_REQUEST
        kept = self._session.interrupt_request(cause, ran, forget=forget)
        self._finish(ChatOutcome(status, error=error, kept_steps=kept))

    def _finish(self, outcome: ChatOutcome) -> None:
        pending, self._pushed = tuple(self._pushed), []
        self._busy = False
        self._handle = None
        self._generation += 1
        try:
            changed = tuple(self._checkpoint.commit())
        except Exception:
            logger.exception("Agent undo point could not be closed")
            changed = ()
        self._notify(self._listener.on_finished, replace(outcome, changed_layers=changed, pending_messages=pending))

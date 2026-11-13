# -*- coding: utf-8 -*-
"""Runs a tool call of the model: validated first, and always answered."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

from .json_schema import validate
from .messages import ToolCallPart, ToolResultPart
from .permissions import ADVISOR_REFUSAL, ASK, PROTECTED, RUN, TURNED_OFF, PermissionPolicy
from .tool_catalog import ToolSpec

logger = logging.getLogger("FilterMate.agent")

Handler = Callable[[Dict[str, Any]], Any]

MAX_RESULT_CHARS = 20_000
DECLINED = "The user declined this action. Nothing was done; do not try again unless they ask."


class ToolFailure(Exception):
    """A failure whose message is meant for the model (layer not found, rejected filter, QGIS busy)."""


@dataclass(frozen=True)
class WithImages:
    """What a handler answers when images go with it: ``answer`` as JSON, ``images`` as ``(mime type, base64)``."""

    answer: Any
    images: Tuple[Tuple[str, str], ...] = ()


def _with_defaults(arguments: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    filled = dict(arguments)
    for name, definition in schema.get("properties", {}).items():
        if name not in filled and "default" in definition:
            filled[name] = definition["default"]
    return filled


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _fewer_rows(value: Any, limit: int) -> Optional[str]:
    """A long list of a result loses its last rows, whole, and says how many: the rest stays valid JSON."""
    if not isinstance(value, dict):
        return None
    lists = [key for key, item in value.items() if isinstance(item, list) and len(item) > 1]
    if not lists:
        return None
    key = max(lists, key=lambda name: len(_dumps(value[name])))
    rows = value[key]
    low, high = 0, len(rows) - 1  # the most rows that fit, at least none
    best = None
    while low <= high:
        middle = (low + high) // 2
        text = _dumps({**value, key: rows[:middle], f"{key}_omitted": len(rows) - middle,
                       "note": f"{len(rows) - middle} of {len(rows)} {key} left out: ask for fewer (filters, limit)."})
        if len(text) <= limit:
            best, low = text, middle + 1
        else:
            high = middle - 1
    return best


def bounded_json(value: Any, limit: int = MAX_RESULT_CHARS) -> str:
    """``value`` as JSON text; a long answer is cut and says so, it never fills the conversation."""
    text = _dumps(value)
    if len(text) <= limit:
        return text
    fewer = _fewer_rows(value, limit)
    if fewer is not None:
        return fewer
    # Half: the quotes of the JSON text are escaped when it is quoted again.
    return json.dumps({"truncated": True, "total_characters": len(text), "start_of_result": text[:limit // 2]},
                      ensure_ascii=False)


class ToolExecutor:
    """Calls the handler of each tool, whatever the model sent."""

    def __init__(self, tools: Sequence[ToolSpec], handlers: Mapping[str, Handler]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._handlers = dict(handlers)
        self._held: set = set()

    def offer(self, tools: Sequence[ToolSpec]) -> None:
        """Tools run from now on (a family of tools, once its skill is loaded); their handlers were given already."""
        for tool in tools:
            self._tools.setdefault(tool.name, tool)
            self._held.discard(tool.name)

    def hold(self, names) -> None:
        """Tools offered later, with the skill of their task: a call of one says so instead of "unknown"."""
        self._held = set(names)

    def spec(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def needs_confirmation(self, call: ToolCallPart) -> bool:
        """At the usual level (``standard``), without the rules of the Tools tab: what the bench is asked to confirm."""
        return self.verdict(call, PermissionPolicy()) == ASK

    def verdict(self, call: ToolCallPart, policy: PermissionPolicy) -> str:
        """``RUN``, ``ASK`` or ``REFUSE`` under ``policy``. An invalid call runs: it only answers its mistake, and
        nobody is asked to confirm, or told they may not, what would not run anyway."""
        tool = self._tools.get(call.name)
        if tool is None and policy.turned_off(call.name):
            return TURNED_OFF  # left out of the tools offered, and still called: say why, not "unknown"
        if tool is None or call.parse_error or validate(call.arguments, tool.input_schema):
            return RUN
        if policy.protection_refusal(call.name, call.arguments):
            return PROTECTED
        return policy.verdict(tool, call.arguments)

    @staticmethod
    def declined(call: ToolCallPart) -> ToolResultPart:
        return ToolResultPart(call.call_id, DECLINED, is_error=True)

    @staticmethod
    def refused(call: ToolCallPart, policy: Optional[PermissionPolicy] = None) -> ToolResultPart:
        """Not run, because of a layer the user protected, a tool turned off, or the level of autonomy."""
        text = policy.refusal_text(call.name, call.arguments) if policy is not None else ADVISOR_REFUSAL
        return ToolResultPart(call.call_id, text, is_error=True)

    def execute(self, call: ToolCallPart) -> ToolResultPart:
        """Result of ``call``; never raises, a model reads its mistakes and corrects them."""
        def failure(message: str) -> ToolResultPart:
            return ToolResultPart(call.call_id, message, is_error=True)

        tool = self._tools.get(call.name)
        handler = self._handlers.get(call.name)
        if tool is None and call.name in self._held:
            return failure(f"{call.name} comes with the instructions of its task: call load_skill with the skill of "
                           f"that task first (its list says which), then call {call.name} again.")
        if tool is None or handler is None:
            return failure(f"Unknown tool {call.name!r}.")
        if call.parse_error:
            return failure(f"The arguments were not valid JSON: {call.parse_error}")
        problems = validate(call.arguments, tool.input_schema)
        if problems:
            return failure("Invalid arguments: " + "; ".join(problems))
        try:
            value = handler(_with_defaults(call.arguments, tool.input_schema))
            if isinstance(value, WithImages):
                return ToolResultPart(call.call_id, bounded_json(value.answer), images=tuple(value.images))
            return ToolResultPart(call.call_id, bounded_json(value))
        except ToolFailure as exc:
            return failure(str(exc))
        except Exception:  # the text of an unexpected exception may hold paths or SQL: it stays in the log
            logger.exception("Agent tool %s failed", call.name)
            return failure("Unexpected error in QGIS: see the FilterMate log.")

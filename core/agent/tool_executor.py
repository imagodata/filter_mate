# -*- coding: utf-8 -*-
"""Runs a tool call of the model: validated first, and always answered."""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from .json_schema import validate
from .messages import ToolCallPart, ToolResultPart
from .tool_catalog import ToolSpec

logger = logging.getLogger("FilterMate.agent")

Handler = Callable[[Dict[str, Any]], Any]

MAX_RESULT_CHARS = 20_000
DECLINED = "The user declined this action. Nothing was done; do not try again unless they ask."


class ToolFailure(Exception):
    """A failure whose message is meant for the model (layer not found, rejected filter, QGIS busy)."""


def _with_defaults(arguments: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    filled = dict(arguments)
    for name, definition in schema.get("properties", {}).items():
        if name not in filled and "default" in definition:
            filled[name] = definition["default"]
    return filled


def bounded_json(value: Any, limit: int = MAX_RESULT_CHARS) -> str:
    """``value`` as JSON text; a long answer is cut and says so, it never fills the conversation."""
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= limit:
        return text
    # Half: the quotes of the JSON text are escaped when it is quoted again.
    return json.dumps({"truncated": True, "total_characters": len(text), "start_of_result": text[:limit // 2]},
                      ensure_ascii=False)


class ToolExecutor:
    """Calls the handler of each tool, whatever the model sent."""

    def __init__(self, tools: Sequence[ToolSpec], handlers: Mapping[str, Handler]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._handlers = dict(handlers)

    def spec(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def needs_confirmation(self, call: ToolCallPart) -> bool:
        """Only a call that would really run: nobody is asked to confirm an invalid one."""
        tool = self._tools.get(call.name)
        if tool is None or not tool.requires_confirmation or call.parse_error:
            return False
        return not validate(call.arguments, tool.input_schema)

    @staticmethod
    def declined(call: ToolCallPart) -> ToolResultPart:
        return ToolResultPart(call.call_id, DECLINED, is_error=True)

    def execute(self, call: ToolCallPart) -> ToolResultPart:
        """Result of ``call``; never raises, a model reads its mistakes and corrects them."""
        def failure(message: str) -> ToolResultPart:
            return ToolResultPart(call.call_id, message, is_error=True)

        tool = self._tools.get(call.name)
        handler = self._handlers.get(call.name)
        if tool is None or handler is None:
            return failure(f"Unknown tool {call.name!r}.")
        if call.parse_error:
            return failure(f"The arguments were not valid JSON: {call.parse_error}")
        problems = validate(call.arguments, tool.input_schema)
        if problems:
            return failure("Invalid arguments: " + "; ".join(problems))
        try:
            return ToolResultPart(call.call_id, bounded_json(handler(_with_defaults(call.arguments, tool.input_schema))))
        except ToolFailure as exc:
            return failure(str(exc))
        except Exception:  # the text of an unexpected exception may hold paths or SQL: it stays in the log
            logger.exception("Agent tool %s failed", call.name)
            return failure("Unexpected error in QGIS: see the FilterMate log.")

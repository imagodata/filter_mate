# -*- coding: utf-8 -*-
"""The tools of FilterMate, as data: what the chat offers a model and a native MCP server will list.

``tool_catalog.json`` is generated from the declarations of the stdio MCP server
(``scripts/export_agent_tools.py``), the single place where a tool is described. It is
JSON because that server needs pydantic and the MCP SDK, which QGIS does not have.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

CATALOG_PATH = Path(__file__).with_name("tool_catalog.json")

# Left out of the chat. undo_filter / redo_filter only walk the dock's history, not what
# the agent did (a turn is undone as a whole by the dock); filter_status is a vector-only
# subset of filter_state.
NOT_IN_CHAT = frozenset({"undo_filter", "redo_filter", "filter_status"})


@dataclass(frozen=True)
class ToolSpec:
    """One tool: its JSON description and what it may do."""

    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    title: str = ""
    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    # Reaches outside QGIS (the network): a read is logged, a change is confirmed by the user.
    open_world: bool = False
    # Walks the history of the agent itself: no undo point is taken for it, or it would undo itself.
    manages_history: bool = False

    @property
    def requires_confirmation(self) -> bool:
        """Writes outside the project (files), or changes that bring the outside in: the user says yes first."""
        return self.destructive or (self.open_world and not self.read_only)


def tool_from_entry(entry: Dict[str, Any]) -> ToolSpec:
    return ToolSpec(
        name=entry["name"], description=entry["description"], input_schema=entry["input_schema"],
        title=entry.get("title", ""), read_only=bool(entry.get("read_only")),
        destructive=bool(entry.get("destructive")), idempotent=bool(entry.get("idempotent")),
        open_world=bool(entry.get("open_world")))


def load_catalog(path: Optional[Path] = None) -> Tuple[ToolSpec, ...]:
    """Every tool, in a fixed order (a prompt cache needs identical bytes from one request to the next)."""
    with open(path or CATALOG_PATH, encoding="utf-8") as stream:
        return tuple(tool_from_entry(entry) for entry in json.load(stream)["tools"])


UNDO_AGENT_STEP = "undo_agent_step"
# Tools of the chat alone: the history of the agent lives in QGIS, not behind the REST API.
CHAT_ONLY = (
    ToolSpec(
        name=UNDO_AGENT_STEP, title="Undo the last change of the agent",
        description=("Undo the last request the agent carried out in this project, as a whole: its filters, the layers "
                     "it added or removed, its selections and visibility changes. Use it when the user asks to undo or "
                     "cancel what you just did, before any other change. Never for filters the user set by hand. "
                     "Returns undone (that request), restored (layers put back) and left (layers changed since, left "
                     "as they are)."),
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        manages_history=True),
)


def chat_tools(path: Optional[Path] = None) -> Tuple[ToolSpec, ...]:
    """The tools the chat offers."""
    return tuple(tool for tool in load_catalog(path) if tool.name not in NOT_IN_CHAT) + CHAT_ONLY

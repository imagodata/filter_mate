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
    # Belongs to the conversation of the chat (its notes): not served to another application.
    chat_only: bool = False

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
ADD_NOTE = "add_project_note"
REMOVE_NOTE = "remove_project_note"
VIEW_MAP = "view_map"
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
        manages_history=True, chat_only=True),
    ToolSpec(
        name=ADD_NOTE, title="Keep a note for this project",
        description=("Keep a short fact about this project for the next conversations, saved with the project: which "
                     "layer holds what, a key field, a naming rule, what the user calls things. Only when the user "
                     "asks you to remember something, or confirms a fact you should not ask again; never for what a "
                     "tool result or a layer says on its own. One fact per note, 300 characters at most, 20 notes. "
                     "Returns notes, numbered."),
        input_schema={"type": "object", "properties": {"text": {
            "type": "string", "minLength": 1, "maxLength": 300, "description": "The fact, in one sentence"}},
            "required": ["text"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=REMOVE_NOTE, title="Forget a note of this project",
        description=("Forget a note kept for this project, by its number in the notes sent with the request: when "
                     "the user asks, or when it no longer holds. Returns notes, numbered again."),
        input_schema={"type": "object", "properties": {"number": {
            "type": "integer", "minimum": 1, "maximum": 20, "description": "Number of the note"}},
            "required": ["number"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=VIEW_MAP, title="Look at the map",
        description=("See the map as an image: the view of the user by default, or an extent, or the whole of a "
                     "layer. Use it to check what a filter, a style or an analysis looks like, to describe the map, or "
                     "to find what the data does not say (the look of an area). It reads, it changes nothing. Returns "
                     "the image and its width, height, crs, extent [xmin, ymin, xmax, ymax], scale and layers. The "
                     "image is only sent with this request: call it again later to look again."),
        input_schema={"type": "object", "properties": {
            "extent": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4,
                       "description": "[xmin, ymin, xmax, ymax] in the CRS of the map (canvas_crs of map_context)"},
            "layer": {"type": "string", "minLength": 1, "maxLength": 1000,
                      "description": "Show the whole of this layer instead"},
            "width": {"type": "integer", "minimum": 256, "maximum": 1568, "default": 1024,
                      "description": "Width of the image in pixels"}},
            "additionalProperties": False},
        read_only=True, chat_only=True),
)


def chat_tools(path: Optional[Path] = None) -> Tuple[ToolSpec, ...]:
    """The tools the chat offers."""
    return tuple(tool for tool in load_catalog(path) if tool.name not in NOT_IN_CHAT) + CHAT_ONLY

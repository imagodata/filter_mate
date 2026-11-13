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
from typing import Any, Dict, Optional, Sequence, Tuple

from .skills import Approved, names as skill_names, skill_list

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
RUN_PYTHON = "run_pyqgis"
CREATE_WIDGET = "create_widget"
REMOVE_WIDGET = "remove_widget"
SAVE_RECIPE = "save_recipe"
REMOVE_RECIPE = "remove_recipe"
SHOW_SETTINGS_LINK = "show_settings_link"
# The tabs of the settings dialog of the agent a link may open (ui/widgets/agent_panel.AgentSettingsDialog).
SETTINGS_TABS = ("provider", "sources", "autonomy", "tools", "other_applications")
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
        name=RUN_PYTHON, title="Run Python code in QGIS (expert)",
        description=("Run Python code in QGIS (PyQGIS), for what no other tool does. Offered only because the user "
                     "turned on the expert mode: they see the whole code and confirm each run, and it is NOT undone "
                     "with the turn. Prefer the other tools; never use it to get around a refusal of another tool. "
                     "iface and project (QgsProject.instance()) are defined; import what you need. Assign result to "
                     "return a value; print() output is returned too. Returns ok, printed, result, and error (a "
                     "traceback) when it raised."),
        input_schema={"type": "object", "properties": {
            "purpose": {"type": "string", "minLength": 1, "maxLength": 300,
                        "description": "What the code does, in one sentence the user reads before saying yes"},
            "code": {"type": "string", "minLength": 1, "maxLength": 20000, "description": "Python code"}},
            "required": ["purpose", "code"], "additionalProperties": False},
        destructive=True, chat_only=True),
    ToolSpec(
        name=VIEW_MAP, title="Look at the map",
        description=("See the map as an image: the view of the user by default, or an extent, or the whole of a "
                     "layer. Use it to check what a filter, a style or an analysis looks like, to describe the map, or "
                     "to find what the data does not say (the look of an area). It reads, it changes nothing. Returns "
                     "the image and its width, height, extent_wkt, crs and scale. The image is only sent with this "
                     "request: call it again later to look again."),
        input_schema={"type": "object", "properties": {
            "extent_wkt": {"type": "string", "minLength": 1, "maxLength": 10000,
                           "description": "Area to show, as WKT (map_context gives the view as extent_wkt)"},
            "crs": {"type": "string", "maxLength": 200, "description": "CRS of extent_wkt; the CRS of the map by default"},
            "layer": {"type": "string", "minLength": 1, "maxLength": 1000,
                      "description": "Show the whole of this layer instead"},
            "width": {"type": "integer", "minimum": 256, "maximum": 1568, "default": 1024,
                      "description": "Width of the image in pixels"}},
            "additionalProperties": False},
        read_only=True, chat_only=True),
    ToolSpec(
        name=CREATE_WIDGET, title="Make a widget for the user",
        description=("Make a small control that stays in the AGENT panel, saved with the project, for the user to "
                     "explore a vector layer without asking you again: range (two bounds on a numeric field: moving "
                     "them filters the layer), values (the values of a field, each ticked or not: at most 50, "
                     "unticking filters the layer), stat (a number on the layer as filtered now: count, or sum, "
                     "mean, min, max of a numeric field, kept up to date) or chart (bars of the layer as filtered "
                     "now: the features of each value of a field, the 8 most frequent and the others, or a "
                     "histogram of a numeric field; it filters nothing). FilterMate builds the filter of a widget "
                     "itself; the widgets of one layer narrow it together, after the filter it had when its first "
                     "widget was made. Use it when the user asks for a widget, a slider, a control, a dashboard or "
                     "a way to play with the data; several calls make several widgets. Undone with the turn. Returns "
                     "widget (what was made) and widgets (all of them, without their values)."),
        input_schema={"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["range", "values", "stat", "chart"]},
            "layer": {"type": "string", "minLength": 1, "maxLength": 1000, "description": "Vector layer, name or id"},
            "field": {"type": "string", "maxLength": 200,
                      "description": ("Field: numeric for range and for a stat other than count; for chart, the "
                                      "values counted (a histogram when numeric)")},
            "aggregate": {"type": "string", "enum": ["count", "sum", "mean", "min", "max"], "default": "count",
                          "description": "For stat only"},
            "title": {"type": "string", "maxLength": 60, "description": "Short title in the words of the user"}},
            "required": ["kind", "layer"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=REMOVE_WIDGET, title="Remove a widget",
        description=("Remove a widget of the AGENT panel by its widget_id (listed with each request). "
                     "The filter it set stays on its layer until the user or you change it. Returns widgets."),
        input_schema={"type": "object", "properties": {
            "widget_id": {"type": "string", "minLength": 1, "maxLength": 20}},
            "required": ["widget_id"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=SAVE_RECIPE, title="Keep what was just done as a recipe",
        description=("Keep the changes of a request as a recipe of this project, under a name: the user runs it again "
                     "from the panel (More > Recipes), step by step, without you and without sending anything. Only "
                     "when the user asks to keep, save or reuse what was done (a recipe, a routine, a chain to run "
                     "again). It keeps the changes made so far in this request, or, when this request changed nothing "
                     "yet, those of the last request that did; reads, notes, widgets, code and connectors are not "
                     "kept. The same name replaces the recipe. Returns recipe (its name and steps) and recipes."),
        input_schema={"type": "object", "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 60,
                     "description": "Short name in the words of the user"}},
            "required": ["name"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=REMOVE_RECIPE, title="Forget a recipe",
        description=("Forget a recipe of this project by its recipe_id (listed with each request), when the user "
                     "asks. Returns recipes."),
        input_schema={"type": "object", "properties": {
            "recipe_id": {"type": "string", "minLength": 1, "maxLength": 20}},
            "required": ["recipe_id"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=SHOW_SETTINGS_LINK, title="Show the user where a setting is",
        description=("Put a button in the thread that takes the user to a setting they change themselves: a tab of "
                     "the settings of the agent (provider: provider, model, key; sources: open data and connectors; "
                     "autonomy: level, protected layers, expert mode; tools: always ask, always allow or never by "
                     "tool; other_applications: the MCP server), or a setting of FilterMate in the configuration "
                     "tree (target setting, with its path). Use it with your answer when the user should change "
                     "something you may not (the settings of the agent, APP.OPTIONS.AGENT, a name or a path), or "
                     "asks where a setting is. It changes nothing; the user clicks when they want. Returns shown."),
        input_schema={"type": "object", "properties": {
            "target": {"type": "string", "enum": list(SETTINGS_TABS) + ["setting"]},
            "path": {"type": "string", "maxLength": 200,
                     "description": "For target setting: the path of the setting (from describe_settings)"}},
            "required": ["target"], "additionalProperties": False},
        read_only=True, chat_only=True),
)


DESCRIBE_SETTINGS = "describe_settings"
GET_SETTING = "get_setting"
CHANGE_SETTINGS = "change_settings"
DIAGNOSE_PERFORMANCE = "diagnose_performance"
EXPORT_SETTINGS_PROFILE = "export_settings_profile"
APPLY_SETTINGS_PROFILE = "apply_settings_profile"
_PROFILE_NAME = {"type": "string", "minLength": 1, "maxLength": 60,
                 "description": "Name of the profile: letters, digits, spaces, dots, dashes, underscores"}
_SETTING_PATH = {"type": "string", "minLength": 1, "maxLength": 200,
                 "description": "Path of the setting, e.g. APP.OPTIONS.QUERY_CACHE.enabled (or its last parts)"}
# The settings of FilterMate itself (config.json), read in the plugin: served by the chat and by the MCP server of the
# plugin, not by the REST API.
SETTINGS_TOOLS = (
    ToolSpec(
        name=DESCRIBE_SETTINGS, title="Find settings of FilterMate",
        description=("Find the settings of FilterMate itself (its configuration: interface, language, theme, "
                     "performance, timeouts, caches, raster and point cloud options), with their value, default, "
                     "choices or bounds and what they do. Without arguments: the sections. With query (English words "
                     "of the setting: theme, timeout, cache, language...) or section: the settings found. It reads, "
                     "it changes nothing. Use it when the user asks what a setting does, how FilterMate is set up, or "
                     "how to make it faster or look otherwise; never guess a setting. The settings of the agent "
                     "(provider, key, autonomy, tools) are not here: they are in its own settings dialog. Returns "
                     "sections, or settings (path, value, description, default when changed, choices, min, max) and "
                     "matched."),
        input_schema={"type": "object", "properties": {
            "query": {"type": "string", "maxLength": 200, "description": "Words of the setting, in English"},
            "section": {"type": "string", "maxLength": 200,
                        "description": "Section path (APP.OPTIONS.QUERY_CACHE), name (QUERY_CACHE) or title (Interface)"},
            "changed_only": {"type": "boolean", "default": False,
                             "description": "Only the settings whose value differs from the default"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 60, "default": 25}},
            "additionalProperties": False},
        read_only=True, idempotent=True),
    ToolSpec(
        name=GET_SETTING, title="Read one setting of FilterMate",
        description=("Read one setting of FilterMate by its path (from describe_settings): its value, default, "
                     "choices or bounds, what it does, where it is in the configuration tree (where) and whether the "
                     "user changed it. A name, local paths and folders are only said set or empty. Returns path, "
                     "value, description, where, changed, and default, choices, min, max, section when they apply."),
        input_schema={"type": "object", "properties": {"path": _SETTING_PATH},
                      "required": ["path"], "additionalProperties": False},
        read_only=True, idempotent=True),
    ToolSpec(
        name=CHANGE_SETTINGS, title="Change settings of FilterMate",
        description=("Change settings of FilterMate itself (from describe_settings), all or none: each value is "
                     "checked against the choices or bounds of its setting. The user sees each setting before and "
                     "after and says yes first (in the chat, a card in the thread: the answer is then proposed and "
                     "the next request says what they chose), except how the panel looks at the autonomous level. "
                     "Undone with the turn. Only when the user asks to change how FilterMate looks or works; read the setting first "
                     "and say what it changes. The settings of the agent (APP.OPTIONS.AGENT), a name and local paths "
                     "are refused: tell the user where they are. Returns changed (path, before, after, effect: now, "
                     "next use or after restarting QGIS) and unchanged (already set)."),
        input_schema={"type": "object", "properties": {
            "changes": {"type": "array", "minItems": 1, "maxItems": 10, "items": {
                "type": "object", "properties": {
                    "path": _SETTING_PATH,
                    "value": {"type": ["string", "number", "boolean"],
                              "description": "New value, of the type of the setting (one of its choices when it has)"}},
                "required": ["path", "value"], "additionalProperties": False}},
            "reason": {"type": "string", "minLength": 1, "maxLength": 300,
                       "description": "Why, in one sentence the user reads before saying yes"}},
            "required": ["changes", "reason"], "additionalProperties": False}),
    ToolSpec(
        name=DIAGNOSE_PERFORMANCE, title="Read the timings of FilterMate",
        description=("Read the timings FilterMate logged (its log file on this machine): by operation (count, median, "
                     "max, last, in ms) and the slowest ones with their layer, and how many timeouts and errors were "
                     "logged. cascade_filter is a whole filter in the background, layer_filter one layer of it, "
                     "apply_subset_layer and set_subset the main thread (QGIS frozen meanwhile). Use it when the user "
                     "says FilterMate is slow, before proposing a setting. It reads, it changes nothing. Returns "
                     "timings, operations, slowest, timeouts_logged, errors_logged, log_from, log_to."),
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        read_only=True, idempotent=True),
    ToolSpec(
        name=EXPORT_SETTINGS_PROFILE, title="Save the settings of FilterMate as a profile",
        description=("Write the settings of FilterMate the user changed from their default as a profile, a small "
                     "JSON file to share with a team, in the folder profiles of the export folder. Never the settings "
                     "of the agent, a name, a path, a key or an account. Asked like a file (the autonomous level "
                     "writes it alone). An existing profile is replaced only with replace true, once the user agreed. "
                     "Returns file, name and settings (how many)."),
        input_schema={"type": "object", "properties": {
            "name": _PROFILE_NAME,
            "replace": {"type": "boolean", "default": False,
                        "description": "Replace a profile of that name; only once the user agreed"}},
            "required": ["name"], "additionalProperties": False},
        destructive=True),
    ToolSpec(
        name=APPLY_SETTINGS_PROFILE, title="Apply a profile of settings",
        description=("Apply a profile of settings of FilterMate by its name, from the folder profiles of the export "
                     "folder (a profile from a colleague is copied there first). Each setting is checked as with "
                     "change_settings and the user sees each one before and after; 40 changes at most. What the "
                     "profile may not set (the settings of the agent, a name, a path, an unknown setting, a value out "
                     "of bounds) is left out and listed. Returns changed, unchanged and left_out, or proposed when "
                     "the user decides in the thread."),
        input_schema={"type": "object", "properties": {"name": _PROFILE_NAME},
                      "required": ["name"], "additionalProperties": False}),
)

LOAD_SKILL = "load_skill"


# Instructions for one kind of task, sent when the task comes rather than with every request (skills/<name>/, read by
# core/agent/skills.py).
def skill_tool(offered: Optional[set] = None, approved: Optional[Approved] = None, audience: str = "chat",
               connectors: Sequence[Tuple[str, str]] = (), with_skills: bool = True) -> ToolSpec:
    """load_skill, listing the skills of ``audience`` whose required tools are among ``offered`` (the pyqgis skill:
    the expert mode). ``approved`` tells which skills from elsewhere the user allowed: the others are named, and
    none of their words is in the description (core/agent/skills.skill_list).

    ``connectors``: pairs ``(entry name, line)`` of the MCP connectors the user enabled (core/agent/connectors.py),
    listed after the skills. ``with_skills`` False: the connectors alone."""
    names = list(skill_names(offered, audience)) if with_skills else []
    description = ("Load the instructions for one kind of task, before doing it: they say how to work and where to "
                   "look. Call it once per conversation and task, then follow them.")
    if with_skills:
        description += " Skills: " + skill_list(offered, approved, audience) + "."
    if connectors:
        names += [name for name, _ in connectors]
        description += (" Connectors the user enabled, loaded the same way when the request needs their data (the user "
                        "is asked the first time; their tools come from the next turn on): "
                        + "; ".join(f"{name}: {line}" for name, line in connectors) + ".")
    return ToolSpec(
        name=LOAD_SKILL, title="Load the instructions of a task", description=description,
        input_schema={"type": "object", "properties": {"name": {"type": "string", "enum": names}},
                      "required": ["name"], "additionalProperties": False},
        read_only=True, idempotent=True)


SKILL_TOOLS = (skill_tool(),)


def chat_tools(path: Optional[Path] = None) -> Tuple[ToolSpec, ...]:
    """The tools the chat offers."""
    return (tuple(tool for tool in load_catalog(path) if tool.name not in NOT_IN_CHAT) + SETTINGS_TOOLS + SKILL_TOOLS
            + CHAT_ONLY)


# What a local model gets when the user asks for the filtering tools only (a slow computer): reading the project and
# filtering it, the selection and the view, the export of the result, and the agent's own undo and recipes. Every tool
# of the chat weighs 15,000 to 18,000 tokens with the system prompt, these 8,000 to 9,000. Measured on 2026-11-11 with
# qwen3.5:4b on the 48 cases of the bench these tools cover: 33 passed with every tool, 29 with these, for half the
# tokens; so every tool stays the default. The memory of the model and its context, not the tools, decide what fits.
FILTERING_TOOLS = frozenset({
    "list_layers", "filter_state", "list_favorites", "describe_layer", "field_values", "layer_statistics",
    "sample_features", "preview_filter", "map_context", "apply_filter", "cross_filter", "geometry_filter",
    "point_cloud_filter", "clear_filters", "apply_favorite", "zoom_to", "select_features", "set_layers_visibility",
    "export_layers", "undo_agent_step", "save_recipe", "add_project_note",
})
FILTERING_NOTE = ("\n\nOnly the tools for reading and filtering the project are offered with this local model. For "
                  "styles, Processing, editing, layouts, layers to add or remove, widgets: say so, and that the user can "
                  "offer every tool again in the settings of the agent.")


def filtering_only(tools) -> Tuple[ToolSpec, ...]:
    """``tools`` without what a local model is not offered by default."""
    return tuple(tool for tool in tools if tool.name in FILTERING_TOOLS)


MAP_IMAGE = "map_image"
CONTACT_SHEET = "contact_sheet"
_EXTENT = {"type": "string", "maxLength": 100000,
           "description": "Extent as WKT, e.g. extent_wkt of map_context; empty: the visible map"}
_CRS = {"type": "string", "maxLength": 64, "description": "CRS of the WKT, e.g. EPSG:2154; empty: the CRS of the map"}
# Tools of the MCP server of the plugin alone (2026-11-11, decided with the user): an image of the map goes to the
# application that asked for it, never to the provider of the chat. Read-only: they draw, they change nothing; open
# world: the image leaves QGIS (the application may send it to its own provider), so each one shows in the thread.
MCP_ONLY = (
    ToolSpec(
        name=MAP_IMAGE, title="Image of the map",
        description=("An image (JPEG) of the map of QGIS as the user sees it, with the layers shown: the visible map, "
                     "or the extent given. Returns the image with width, height, extent_wkt, crs and scale. The image "
                     "is made on the computer of the user and sent to you, the application that asked; it may show "
                     "private data: ask before sending it further."),
        input_schema={"type": "object", "properties": {
            "extent_wkt": _EXTENT, "crs": _CRS,
            "width": {"type": "integer", "minimum": 128, "maximum": 1600, "default": 1024,
                      "description": "Width in pixels; the height follows the extent"}},
            "additionalProperties": False},
        read_only=True, idempotent=True, open_world=True),
    ToolSpec(
        name=CONTACT_SHEET, title="Contact sheet of objects",
        description=("A contact sheet (JPEG) to judge objects by eye: tile E is the example (the one selected feature of "
                     "example_layer, or none), tiles 1 to n the features of layer (its selected features, or all it "
                     "shows), each cut out of raster around the object and outlined in red. Use it to tell, for "
                     "example, which objects found by similar_objects are really like the example, then "
                     "select_features on the ones meant (fids gives the feature id of each tile). At most 30 tiles. "
                     "Returns the image with tiles [{tile, fid}] and example_fid."),
        input_schema={"type": "object", "properties": {
            "raster": {"type": "string", "minLength": 1, "maxLength": 1000,
                       "description": "Raster the tiles are cut from (an orthophoto): layer id or name"},
            "layer": {"type": "string", "minLength": 1, "maxLength": 1000,
                      "description": "Polygon or point layer of the objects to show: layer id or name"},
            "example_layer": {"type": "string", "maxLength": 1000, "default": "",
                              "description": "Layer whose one selected feature is the example (tile E); empty: none"},
            "tile": {"type": "integer", "minimum": 96, "maximum": 256, "default": 160,
                     "description": "Side of a tile in pixels"}},
            "required": ["raster", "layer"], "additionalProperties": False},
        read_only=True, idempotent=True, open_world=True),
)

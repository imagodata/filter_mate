# -*- coding: utf-8 -*-
"""The tools of FilterMate, as data: what the chat offers a model and a native MCP server will list.

``tool_catalog.json`` is generated from the declarations of the stdio MCP server
(``scripts/export_agent_tools.py``), the single place where a tool is described. It is
JSON because that server needs pydantic and the MCP SDK, which QGIS does not have.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
    # One line for the index of the tools a conversation may add (core/agent/tool_index.py).
    summary: str = ""

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
OPEN_LAYOUT = "open_layout"
OPEN_MODEL = "open_model"
FLASH_FEATURES = "flash_features"
SET_ACTIVE_LAYER = "set_active_layer"
SHOW_MESSAGE = "show_message"
PREVIEW_ATLAS = "preview_atlas"
RUN_PYTHON = "run_pyqgis"
CREATE_WIDGET = "create_widget"
REMOVE_WIDGET = "remove_widget"
SHOW_CHART = "show_chart"
EXPORT_CHART = "export_chart"
CHART_TO_LAYOUT = "add_chart_to_layout"
RUN_CHART_CODE = "run_chart_code"
CHART_TOOLS = (SHOW_CHART, EXPORT_CHART, CHART_TO_LAYOUT, RUN_CHART_CODE)
SHOW_INFOGRAPHIC = "show_infographic"
EXPORT_INFOGRAPHIC = "export_infographic"
INFOGRAPHIC_TOOLS = (SHOW_INFOGRAPHIC, EXPORT_INFOGRAPHIC)
SAVE_RECIPE = "save_recipe"
REMOVE_RECIPE = "remove_recipe"
SHOW_SETTINGS_LINK = "show_settings_link"
AGENT_OPTIONS = "agent_options"
TURN_OFF_OPTIONS = "turn_off_agent_options"
TURN_ON_OPTIONS = "turn_on_agent_options"
ASK_USER = "ask_user"
LIST_TABLES = "list_database_tables"
ADD_TABLE = "add_database_table"
# The tabs of the settings dialog of the agent a link may open (ui/widgets/agent_panel.AgentSettingsDialog).
SETTINGS_TABS = ("provider", "sources", "autonomy", "tools", "memory", "other_applications")
# The forms of the feedback page of the site a link may open (infrastructure/feedback_forms.py).
FEEDBACK_FORMS = ("usage", "feature", "testers", "services")
# Tools of the chat alone: the history of the agent lives in QGIS, not behind the REST API.
CHAT_ONLY = (
    ToolSpec(
        name=OPEN_MODEL, title="Open the Processing model designer",
        description=("Open a registered model by algorithm_id, a new declarative definition, or a blank QGIS model "
                     "designer when both are omitted. Never executes steps or saves a file: the user chooses Save "
                     "or Save in project in the editor. Load processing-models for the definition format."),
        input_schema={"type": "object", "properties": {
            "algorithm_id": {"type": "string", "maxLength": 200, "default": "",
                             "description": "Existing model id from find_algorithms with query model"},
            "definition": {"type": "object", "description": "New draft: name, inputs, steps, outputs; see processing-models"}},
            "additionalProperties": False},
        manages_history=True, chat_only=True),
    # The PostgreSQL connections of QGIS the user ticked. Of the chat alone: another application (REST, MCP) holds
    # a key of FilterMate, not the databases of the user.
    ToolSpec(
        name=LIST_TABLES, title="List the tables of a database",
        description=("List the tables of a PostgreSQL connection of QGIS the user enabled: schema, table, whether it "
                     "has a geometry (and in which column, of which types), whether it is a view, and its comment. "
                     "Names only: no row is read. search keeps the tables whose schema, name or comment hold every "
                     "word; schema reads one schema only, which is faster on a large database. Returns tables "
                     "[{schema, table, kind, geometry, geometry_column, geometry_types, comment}], count and "
                     "truncated (50 at most: search to narrow). Then add_database_table."),
        input_schema={"type": "object", "properties": {
            "connection": {"type": "string", "minLength": 1, "maxLength": 100,
                           "description": "A database the user enabled, by its id (db_...)"},
            "search": {"type": "string", "maxLength": 200, "default": "",
                       "description": "Words of the schema, the name or the comment of the tables wanted"},
            "schema": {"type": "string", "maxLength": 200, "default": "", "description": "Only the tables of this schema"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 50}},
            "required": ["connection"], "additionalProperties": False},
        read_only=True, chat_only=True),
    ToolSpec(
        name=ADD_TABLE, title="Add a table of a database",
        description=("Add a table of a PostgreSQL connection of QGIS the user enabled to the project, as a layer: it "
                     "is then read, filtered and styled like any other layer (filters run in the database). Only a "
                     "table list_database_tables gives. Returns the layer summary. The user is asked first."),
        input_schema={"type": "object", "properties": {
            "connection": {"type": "string", "minLength": 1, "maxLength": 100,
                           "description": "A database the user enabled, by its id (db_...)"},
            "schema": {"type": "string", "minLength": 1, "maxLength": 200},
            "table": {"type": "string", "minLength": 1, "maxLength": 200},
            "geometry_column": {"type": "string", "maxLength": 200, "default": "",
                                "description": "For a table with several geometry columns: the one to draw"},
            "name": {"type": "string", "maxLength": 200, "default": "",
                     "description": "Name of the layer in the project (default: the name of the table)"}},
            "required": ["connection", "schema", "table"], "additionalProperties": False},
        open_world=True, chat_only=True),
    ToolSpec(
        name=UNDO_AGENT_STEP, title="Undo the last change of the agent",
        description=("Undo the last request of the agent as a whole (filters, layers added or removed, selections, "
                     "visibility), when the user asks, before any other change; never for filters set by hand. "
                     "Returns undone, restored and left (layers changed since, left as they are)."),
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        manages_history=True, chat_only=True),
    ToolSpec(
        name=ADD_NOTE, title="Keep a note for this project",
        description=("Keep a short fact for the next conversations. scope project (default): saved with this project, "
                     "only when the user asks you to remember something or explains a fact to keep. scope user "
                     "(every project: a word or preference) or source (the data source of layer): only proposed on "
                     "a card. Nothing is saved before the user clicks to keep or correct it; the next request says "
                     "what they chose. Propose only after a user explanation or explicit request to remember, never "
                     "just because you searched a layer, field or value. Never for what a tool result, a layer or a "
                     "connector says on its own. One fact per note, 300 characters at most. Returns notes, or proposed."),
        input_schema={"type": "object", "properties": {
            "text": {"type": "string", "minLength": 1, "maxLength": 300, "description": "The fact, in one sentence"},
            "scope": {"type": "string", "enum": ["project", "user", "source"], "default": "project"},
            "layer": {"type": "string", "maxLength": 200, "description": "Scope source: the layer, by name or id"}},
            "required": ["text"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=REMOVE_NOTE, title="Forget a note",
        description=("Forget a note of this project by its number when the user asks or it no longer holds. "
                     "For a note kept across projects, give memory: its id among the notes actually sent with this "
                     "request, never a guessed id. Removal is only proposed on a card; nothing is removed before "
                     "the user clicks. Give number or memory. Returns notes, or proposed."),
        input_schema={"type": "object", "properties": {
            "number": {"type": "integer", "minimum": 1, "maximum": 20,
                       "description": "Number of a note of this project"},
            "memory": {"type": "string", "pattern": "^m[1-9][0-9]{0,12}$", "maxLength": 14,
                       "description": "Id of a cross-project note actually sent with this request"}},
            "additionalProperties": False},
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
        name=OPEN_LAYOUT, title="Open a print layout",
        description=("Open a print layout of the project in the layout designer of QGIS, in front, for the user to "
                     "see and finish (create_layout makes one, edit_layout changes it, export_layout writes it). "
                     "It changes nothing: opening it is not undone with the turn. Returns name and opened."),
        input_schema={"type": "object", "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 100,
                     "description": "A layout of the project (map_context lists them)"}},
            "required": ["name"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=FLASH_FEATURES, title="Flash features on the map",
        description=("Flash the features of a vector layer matching a QGIS expression (not SQL) on the map, a few "
                     "red blinks, selecting nothing: to point at what you mean while the user watches. Only plain "
                     "conditions, as select_features accepts them. At most 500 flash (more is a selection or a "
                     "zoom instead). It changes nothing. Returns layer and flashed."),
        input_schema={"type": "object", "properties": {
            "layer": {"type": "string", "minLength": 1, "maxLength": 1000, "description": "Vector layer, name or id"},
            "expression": {"type": "string", "minLength": 1, "maxLength": 2000,
                           "description": "QGIS expression the features flashed must match"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 500,
                      "description": "At most this many features flash"}},
            "required": ["layer", "expression"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=SET_ACTIVE_LAYER, title="Make a layer the active one",
        description=("Make a layer of the project the active one, and show it unfolded in the layer tree, so the "
                     "user sees which layer you mean and the tools of QGIS act on it. It changes nothing of the "
                     "project. Returns layer, active and revealed."),
        input_schema={"type": "object", "properties": {
            "layer": {"type": "string", "minLength": 1, "maxLength": 1000, "description": "Layer, name or id"},
            "reveal": {"type": "boolean", "default": True,
                       "description": "Also unfold its groups in the tree and scroll to it"}},
            "required": ["layer"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=SHOW_MESSAGE, title="Show a message in QGIS",
        description=("Show a short message in the bar of QGIS, as FilterMate does for its own warnings: to tell the "
                     "user something where they look, while you go on. Never for a question (ask_user asks it with "
                     "choices instead). It changes nothing. Returns shown and level."),
        input_schema={"type": "object", "properties": {
            "text": {"type": "string", "minLength": 1, "maxLength": 500, "description": "The message, one line"},
            "level": {"type": "string", "enum": ["info", "success", "warning", "critical"], "default": "info"},
            "duration": {"type": "integer", "minimum": 1, "maximum": 60, "default": 5,
                         "description": "Seconds the message stays"}},
            "required": ["text"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=PREVIEW_ATLAS, title="Turn an atlas page",
        description=("Turn a page of the atlas preview of a print layout (its atlas set by set_atlas): first, "
                     "previous, next or last feature; in the designer showing the layout, the preview is turned on "
                     "so the user sees the page change. The atlas itself is unchanged. Returns layout, action, page "
                     "(1-based) and pages."),
        input_schema={"type": "object", "properties": {
            "layout": {"type": "string", "minLength": 1, "maxLength": 100,
                       "description": "A layout of the project (map_context lists them)"},
            "action": {"type": "string", "enum": ["first", "previous", "next", "last"], "default": "next"},
            "preview": {"type": "boolean", "default": True,
                        "description": "Turn the preview on in its open designer, when there is one"}},
            "required": ["layout"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=CREATE_WIDGET, title="Make a widget for the user",
        description=("Make a control that stays in the AGENT panel, saved with the project, for the user to explore "
                     "a vector layer alone: range (two bounds on a number over its histogram, filters), values "
                     "(ticked values, at most 50, filters), stat (a number kept up to date) or chart (bars or a "
                     "histogram, filters nothing). "
                     "The widgets of a layer narrow it together. For a widget, slider or dashboard asked; one per "
                     "call; undone with the turn. Returns widget and widgets."),
        input_schema={"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["range", "values", "stat", "chart"]},
            "layer": {"type": "string", "minLength": 1, "maxLength": 1000, "description": "Vector layer, name or id"},
            "field": {"type": "string", "maxLength": 200,
                      "description": "Numeric for range and a stat but count; chart: a histogram when numeric"},
            "aggregate": {"type": "string", "enum": ["count", "sum", "mean", "min", "max"], "default": "count",
                          "description": "stat"},
            "title": {"type": "string", "maxLength": 60, "description": "In the words of the user"}},
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
        name=SHOW_CHART, title="Draw a chart in the chat",
        description=("Draw a Python chart in the thread (QGIS 3/Qt5 and QGIS 4/Qt6) from a layer as filtered now (FilterMate reads it: never type its "
                     "values) or from rows you give. bar, pie, kpi, treemap: field the categories, aggregate of "
                     "value_field (of the values of rows you give, which add up unless aggregate says otherwise); "
                     "histogram: field numeric; line, scatter, area: field the x, value_field the y. Returns "
                     "chart_id, points, features."),
        input_schema={"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["bar", "pie", "histogram", "line", "scatter",
                                                "kpi", "treemap", "area"]},
            "title": {"type": "string", "maxLength": 80},
            "layer": {"type": "string", "maxLength": 1000},
            "field": {"type": "string", "maxLength": 200},
            "value_field": {"type": "string", "maxLength": 200},
            "aggregate": {"type": "string", "enum": ["count", "sum", "mean", "min", "max"],
                          "description": "Layer default count; rows default sum"},
            "series_field": {"type": "string", "maxLength": 200, "description": "line, scatter, area"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 30, "description": "bar, pie, treemap: categories kept; kpi: total cards, 1-8 including Others"},
            "bins": {"type": "integer", "minimum": 2, "maximum": 50, "default": 12},
            "sort": {"type": "string", "enum": ["value", "label"], "default": "value"},
            "horizontal": {"type": "boolean"},
            "donut": {"type": "boolean", "default": True},
            "x_type": {"type": "string", "enum": ["number", "time"]},
            "x_label": {"type": "string", "maxLength": 60},
            "y_label": {"type": "string", "maxLength": 60},
            "rows": {"type": "array", "maxItems": 500, "items": {"type": "object"},
                     "description": "[{label, value}] or [{x, y, series}]"},
            "width": {"type": "integer", "minimum": 280, "maximum": 1600, "default": 640},
            "height": {"type": "integer", "minimum": 200, "maximum": 1200, "default": 400}},
            "required": ["kind"], "additionalProperties": False},
        read_only=True, chat_only=True),
    ToolSpec(
        name=RUN_CHART_CODE, title="Draw a chart with d3 code (expert)",
        description=("Draw a chart of this conversation again with d3 code you write, over its data, for what no kind "
                     "of show_chart draws (stacked bars, a heatmap, annotations). Offered only in the expert mode: "
                     "the user reads the code and confirms each run. code is the body of function(d3, svg, data, "
                     "width, height, palette); SVG shapes and text only. Returns a new chart_id, errors of the page, "
                     "and the image drawn."),
        input_schema={"type": "object", "properties": {
            "chart_id": {"type": "string", "minLength": 1, "maxLength": 20, "description": "Its data, from show_chart"},
            "purpose": {"type": "string", "minLength": 1, "maxLength": 300,
                        "description": "What the code draws, in one sentence the user reads before saying yes"},
            "code": {"type": "string", "minLength": 1, "maxLength": 20000}},
            "required": ["chart_id", "purpose", "code"], "additionalProperties": False},
        # Read only: it changes nothing in the project (no undo point, 2026-11-22 second review); destructive: asked
        # at every run, as code is (permissions.CODE_TOOLS).
        read_only=True, destructive=True, chat_only=True),
    ToolSpec(
        name=EXPORT_CHART, title="Save a chart as a file",
        description=("Write a chart of this conversation (chart_id from show_chart) as PNG, JPG, SVG or vector PDF in a sub-folder "
                     "of the export root, drawn light for paper. A file of the same name there is kept: the new one is "
                     "named <name>_2... The user is asked first, unless they allowed it. Returns path (relative to "
                     "the sub-folder) and bytes."),
        input_schema={"type": "object", "properties": {
            "chart_id": {"type": "string", "minLength": 1, "maxLength": 20},
            "format": {"type": "string", "enum": ["png", "jpg", "svg", "pdf"], "default": "png"},
            "dpi": {"type": "integer", "minimum": 48, "maximum": 600, "default": 192,
                    "description": "png, jpg: 96 is the size of the chart"},
            "name": {"type": "string", "maxLength": 100, "description": "File name; default: the title"},
            "subfolder": {"type": "string", "minLength": 1, "maxLength": 200, "default": "charts",
                          "description": "Sub-folder of the export root (a/b allowed, no ..)"}},
            "required": ["chart_id"], "additionalProperties": False},
        destructive=True, chat_only=True),
    ToolSpec(
        name=CHART_TO_LAYOUT, title="Put a chart in a print layout",
        description=("Put a chart of this conversation (chart_id) in a print layout of the project (create_layout "
                     "makes one), as a picture drawn light: FilterMate draws it again from its layer when the filter "
                     "of that layer changes; export_layout writes the page. Position in millimetres from the top left "
                     "of the first page; default: its bottom right. Undone with the turn. Returns layout, item and its "
                     "place."),
        input_schema={"type": "object", "properties": {
            "chart_id": {"type": "string", "minLength": 1, "maxLength": 20},
            "layout": {"type": "string", "minLength": 1, "maxLength": 100,
                       "description": "A layout of the project (map_context lists them)"},
            "x": {"type": "number", "minimum": 0, "maximum": 2000},
            "y": {"type": "number", "minimum": 0, "maximum": 2000},
            "width": {"type": "number", "minimum": 10, "maximum": 2000, "description": "mm; the height follows"}},
            "required": ["chart_id", "layout"], "additionalProperties": False},
        chat_only=True),
    ToolSpec(
        name=SHOW_INFOGRAPHIC, title="Stack charts into an infographic",
        description=("Stack charts of this conversation into one infographic: a title, the charts in order, a "
                     "caption and a source. Draw each part with show_chart first (a kpi strip for the big numbers, "
                     "then the chart that tells the story) and pass their chart_ids. Only when the user asks for an "
                     "infographic, a figure that sums up, or something to share. Always light, made to be shared; "
                     "it stays as composed when the filters change. Returns infographic_id, title, charts, caption "
                     "and source."),
        input_schema={"type": "object", "properties": {
            "title": {"type": "string", "minLength": 1, "maxLength": 80,
                      "description": "What the infographic says, in the words of the user"},
            "charts": {"type": "array", "minItems": 1, "maxItems": 4, "uniqueItems": True, "items": {
                "type": "string", "pattern": "^c[1-9][0-9]*$", "maxLength": 20},
                "description": "chart_ids from show_chart, in order, 4 at most"},
            "caption": {"type": "string", "maxLength": 200,
                        "description": "How to read it, in one sentence"},
            "source": {"type": "string", "maxLength": 200,
                       "description": "Where the numbers come from"}},
            "required": ["title", "charts"], "additionalProperties": False},
        read_only=True, chat_only=True),
    ToolSpec(
        name=EXPORT_INFOGRAPHIC, title="Save an infographic as a file",
        description=("Write an infographic of this conversation (infographic_id from show_infographic) as a "
                     "standalone HTML page (offline: it opens out of QGIS), PNG, JPG, SVG or vector PDF, in a sub-folder of "
                     "the export root. A file of the same name there is kept: the new one is named <name>_2... "
                     "The user is asked first, unless they allowed it. Returns path (relative to the sub-folder), "
                     "bytes and format."),
        input_schema={"type": "object", "properties": {
            "infographic_id": {"type": "string", "minLength": 1, "maxLength": 20},
            "format": {"type": "string", "enum": ["html", "png", "jpg", "svg", "pdf"], "default": "html"},
            "dpi": {"type": "integer", "minimum": 48, "maximum": 600, "default": 192,
                    "description": "png, jpg: 96 is the size of the infographic"},
            "name": {"type": "string", "maxLength": 100, "description": "File name; default: the title"},
            "subfolder": {"type": "string", "minLength": 1, "maxLength": 200, "default": "infographics",
                          "description": "Sub-folder of the export root (a/b allowed, no ..)"}},
            "required": ["infographic_id"], "additionalProperties": False},
        destructive=True, chat_only=True),
    ToolSpec(
        name=SAVE_RECIPE, title="Keep what was just done as a recipe",
        description=("Keep the changes of a request as a recipe of this project, under a name: the user runs it again "
                     "from the panel (More > Recipes), step by step, without you and without sending anything. Only "
                     "when the user asks to keep, save or reuse what was done (a recipe, a routine, a chain to run "
                     "again). It keeps the changes made so far in this request, or, when this request changed nothing "
                     "yet, those of the last request that did; reads, notes, widgets, code and connectors are not "
                     "kept. The same name replaces the recipe; never run its steps yourself. Returns recipe (its name "
                     "and steps) and recipes."),
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
                     "tool; memory: the notes kept from one project to the next; other_applications: the MCP server), or a "
                     "setting of FilterMate in the configuration "
                     "tree (target setting, with its path). Use it with your answer when the user should change "
                     "something you may not (the settings of the agent, APP.OPTIONS.AGENT, a name or a path), or "
                     "asks where a setting is; target feedback: a form of the site, usage (an opinion, a problem), "
                     "feature (an idea), testers (try what comes next), services (training, support), when the user "
                     "wants to say so. It changes nothing; the user clicks it. Returns shown."),
        input_schema={"type": "object", "properties": {
            "target": {"type": "string", "enum": list(SETTINGS_TABS) + ["setting", "feedback"]},
            "path": {"type": "string", "maxLength": 200,
                     "description": "For target setting: the path of the setting (from describe_settings)"},
            "form": {"type": "string", "enum": list(FEEDBACK_FORMS), "description": "Target feedback"}},
            "required": ["target"], "additionalProperties": False},
        read_only=True, chat_only=True),
    ToolSpec(
        name=ASK_USER, title="Ask the user",
        description=("Ask the user questions with choices to click, answered in this turn: for a "
                     "decision that is theirs and changes what you do, never for what a reading tool says nor as a "
                     "confirmation (an answer authorizes nothing). Recommended option first, its label ending "
                     "\" (Recommended)\"; the panel adds \"Other\". Returns answers, or declined: then say what you "
                     "would have done and stop, or go on with what needs no answer."),
        input_schema={"type": "object", "properties": {
            "questions": {"type": "array", "minItems": 1, "maxItems": 4, "items": {
                "type": "object", "properties": {
                    "question": {"type": "string", "minLength": 1, "maxLength": 300,
                                 "description": "In the language of the user"},
                    "header": {"type": "string", "minLength": 1, "maxLength": 12,
                               "description": "A chip: Roads, Look"},
                    "multi_select": {"type": "boolean", "default": False},
                    "options": {"type": "array", "minItems": 2, "maxItems": 4, "items": {
                        "type": "object", "properties": {
                            "label": {"type": "string", "minLength": 1, "maxLength": 60},
                            "description": {"type": "string", "maxLength": 200}},
                        "required": ["label"], "additionalProperties": False}}},
                "required": ["question", "header", "options"], "additionalProperties": False}}},
            "required": ["questions"], "additionalProperties": False},
        read_only=True, chat_only=True),
    # The options of the agent itself (2026-11-16, core/agent/agent_options.py): what it reaches, read; turned off
    # (that only narrows it) like any other change of the project: run alone from the standard level, asked at the
    # careful one, refused at the advisor one (core/agent/permissions.py: class "project", as set_layer_options);
    # turned on once the user says yes, at every level.
    ToolSpec(
        AGENT_OPTIONS,
        "The options of the agent: the provider and model in use and those the user set up, each source and MCP "
        "connector with its group and whether it is ticked, the MCP server of the plugin. Returns provider, providers, "
        "sources [{id, title, group, on}] and mcp_server.",
        {"type": "object", "properties": {}, "additionalProperties": False},
        title="Read the options of the agent", read_only=True, chat_only=True),
    ToolSpec(
        TURN_OFF_OPTIONS,
        "Untick sources or MCP connectors (their ids from agent_options) or stop the MCP server of the plugin, when "
        "the user asks. Applies after this request: the next one runs without their tools. Returns turned_off and "
        "already.",
        {"type": "object", "properties": {
            "sources": {"type": "array", "items": {"type": "string", "maxLength": 200}, "maxItems": 100},
            "mcp_server": {"type": "boolean", "enum": [False], "description": "false stops the MCP server"}},
         "additionalProperties": False},
        title="Turn options of the agent off", chat_only=True),
    ToolSpec(
        TURN_ON_OPTIONS,
        "Tick sources or MCP connectors (their ids from agent_options), start the MCP server of the plugin, or switch "
        "to another provider the user set up (its label from agent_options). The user is asked first, and it applies "
        "after this request (another provider: in a new conversation). Never a key nor the consent to send data: "
        "those are the user's, in the agent settings. Returns turned_on, already, provider and mcp_server.",
        {"type": "object", "properties": {
            "sources": {"type": "array", "items": {"type": "string", "maxLength": 200}, "maxItems": 100},
            "mcp_server": {"type": "boolean", "enum": [True], "description": "true starts the MCP server"},
            "provider": {"type": "string", "maxLength": 300, "description": "A label of providers, from agent_options"}},
         "additionalProperties": False},
        # destructive: confirmed by the user like a change of this machine (a setting kept beyond the project)
        title="Turn options of the agent on", destructive=True, chat_only=True),
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
# Token diet, lot 1: a request carries the core of the tools (core/agent/families.py); use_tools adds the others the
# instructions list in their index (core/agent/tool_index.py). Offered by the chat when that option is on.
USE_TOOLS = "use_tools"
MAX_USE_TOOLS = 20
USE_TOOLS_TOOL = ToolSpec(
    USE_TOOLS,
    "Add tools from the index of the instructions to this conversation, from the next turn on. Add in one "
    "call every tool the request needs. Returns added and already (offered before).",
    {"type": "object", "properties": {"names": {"type": "array", "items": {"type": "string", "maxLength": 100},
                                                "minItems": 1, "maxItems": MAX_USE_TOOLS}},
     "required": ["names"], "additionalProperties": False},
    title="Add tools", read_only=True, chat_only=True, summary="Add tools of this index to the request")


# Instructions for one kind of task, sent when the task comes rather than with every request (skills/<name>/, read by
# core/agent/skills.py).
def skill_tool(offered: Optional[set] = None, approved: Optional[Approved] = None, audience: str = "chat",
               connectors: Sequence[Tuple[str, str]] = (), with_skills: bool = True,
               declined: Optional[Approved] = None) -> ToolSpec:
    """load_skill, listing the skills of ``audience`` whose required tools are among ``offered`` (the pyqgis skill:
    the expert mode). ``approved`` tells which skills from elsewhere the user allowed, ``declined`` which they said no
    to: the others are named, and none of their words is in the description (core/agent/skills.skill_list).

    ``connectors``: pairs ``(entry name, line)`` of the MCP connectors the user enabled (core/agent/connectors.py),
    listed after the skills. ``with_skills`` False: the connectors alone."""
    names = list(skill_names(offered, audience)) if with_skills else []
    listed = "; ".join(f"{name}: {line}" for name, line in connectors)
    if with_skills:
        description = ("Load the instructions of a kind of task before doing it, once per conversation and task, "
                       "and follow them. Skills: "
                       + skill_list(offered, approved, audience, declined) + ".")
        if connectors:
            description += (" Connectors the user enabled, loaded the same way when the request needs their data (the "
                            "user is asked the first time; their tools come from the next turn on): " + listed + ".")
    else:  # no skill can be loaded here: a description that promised some had the model try their names
        description = ("Load an external connector the user enabled, when the request needs its data: the user is asked "
                       "the first time, and its tools come from the next turn on. Connectors: " + listed + ".")
    names += [name for name, _ in connectors]
    return ToolSpec(
        name=LOAD_SKILL, title="Load the instructions of a task", description=description,
        input_schema={"type": "object", "properties": {"name": {"type": "string", "enum": names}},
                      "required": ["name"], "additionalProperties": False},
        read_only=True, idempotent=True)


def with_skill_tool(tools, offered: Optional[set] = None, approved: Optional[Approved] = None, audience: str = "chat",
                    declined: Optional[Approved] = None) -> List[ToolSpec]:
    """``tools`` with load_skill as ``skill_tool`` makes it, or without it when it would list no skill (skills/ missing
    or unreadable): some providers refuse an empty enum, and the whole request with it (2026-11-13)."""
    listed = skill_tool(offered, approved, audience, declined=declined)
    if not listed.input_schema["properties"]["name"]["enum"]:
        return [tool for tool in tools if tool.name != LOAD_SKILL]
    return [listed if tool.name == LOAD_SKILL else tool for tool in tools]


SKILL_TOOLS = (skill_tool(),)


def chat_tools(path: Optional[Path] = None) -> Tuple[ToolSpec, ...]:
    """The tools the chat offers."""
    from .tool_index import SUMMARIES
    tools = (tuple(tool for tool in load_catalog(path) if tool.name not in NOT_IN_CHAT) + SETTINGS_TOOLS + SKILL_TOOLS
             + CHAT_ONLY)
    return tuple(replace(tool, summary=SUMMARIES.get(tool.name, tool.summary)) for tool in tools)


# What a local model gets when the user asks for the filtering tools only (a slow computer): reading the project and
# filtering it, the selection and the view, the export of the result, and the agent's own undo and recipes. Every tool
# of the chat weighs 15,000 to 18,000 tokens with the system prompt, these 8,000 to 9,000. Measured on 2026-11-11 with
# qwen3.5:4b on the 48 cases of the bench these tools cover: 33 passed with every tool, 29 with these, for half the
# tokens; so every tool stays the default. The memory of the model and its context, not the tools, decide what fits.
FILTERING_TOOLS = frozenset({
    "list_layers", "filter_state", "list_favorites", "describe_layer", "field_values", "layer_statistics",
    "sample_features", "preview_filter", "map_context", "apply_filter", "cross_filter", "geometry_filter",
    "point_cloud_filter", "clear_filters", "apply_favorite", "save_favorite", "zoom_to", "select_features",
    "set_layers_visibility", "export_layers", "undo_agent_step", "save_recipe", "add_project_note", "ask_user",
})
FILTERING_NOTE = ("\n\nOnly the tools for reading and filtering the project are offered with this local model. For "
                  "styles, Processing, editing, layouts, layers to add or remove, widgets: say so, and that the user can "
                  "offer every tool again in the settings of the agent.")


def filtering_only(tools) -> Tuple[ToolSpec, ...]:
    """``tools`` without what a local model is not offered by default."""
    return tuple(tool for tool in tools if tool.name in FILTERING_TOOLS)


# The families of the chat tools (S4): six groups the Tools tab and the cards read instead of a flat list of
# seventy. Assigned by name, by what the tool mainly does: a network lookup that creates a layer is data
# (it ends on the map like add_layer), a pure lookup is outside; the settings of FilterMate live outside QGIS
# files and project, with the network and the code. Unknown tools (a connector ``mcp_*``, a tool added since)
# fall outside too: cautiously grouped, as ``asked_alone`` cautiously asks them alone.
FAMILY_READ = "read"
FAMILY_FILTER = "filter"
FAMILY_STYLE = "style"
FAMILY_DATA = "data"
FAMILY_LAYOUT = "layout"
FAMILY_OUTSIDE = "outside"
TOOL_FAMILIES = (FAMILY_READ, FAMILY_FILTER, FAMILY_STYLE, FAMILY_DATA, FAMILY_LAYOUT, FAMILY_OUTSIDE)

FAMILY_TITLES = {
    FAMILY_READ: "Read",
    FAMILY_FILTER: "Filter",
    FAMILY_STYLE: "Style",
    FAMILY_DATA: "Layers and data",
    FAMILY_LAYOUT: "Layouts and charts",
    FAMILY_OUTSIDE: "Outside QGIS",
}

_FAMILY_OF = {}
for _name in ("list_layers", "filter_state", "list_favorites", "describe_layer", "field_values", "layer_statistics",
              "sample_features", "identify_at", "map_context", "find_algorithms", "describe_algorithm",
              "layer_options", "export_options", "describe_layout", "suggest_crs", "list_style_presets",
              "list_palettes", "list_database_tables", "filter_status", "view_map"):
    _FAMILY_OF[_name] = FAMILY_READ
for _name in ("preview_filter", "apply_filter", "undo_filter", "redo_filter", "cross_filter", "geometry_filter",
              "point_cloud_filter", "clear_filters", "apply_favorite", "save_favorite", "set_exploring",
              "set_layer_options", "zoom_to", "select_features", "set_layers_visibility", "undo_agent_step",
              "ask_user"):
    _FAMILY_OF[_name] = FAMILY_FILTER
for _name in ("set_layer_style", "set_labels", "apply_style_preset", "design_style", "make_cartogram",
              "create_widget", "remove_widget"):
    _FAMILY_OF[_name] = FAMILY_STYLE
for _name in ("update_features", "delete_features", "add_features", "add_field", "join_layers", "set_form",
              "relations", "group_layers", "rename_layer", "duplicate_layer", "local_copy", "remove_layers",
              "run_algorithm", "open_model", "contour_lines", "segment_objects", "similar_objects", "add_layer",
              "add_service_layer", "add_basemap", "add_elevation", "add_population", "add_osm_features",
              "add_database_table", "export_layers", "add_project_note", "remove_project_note", "save_recipe",
              "remove_recipe", "bookmark", "map_theme", "set_project_crs", "flash_features", "set_active_layer",
              "show_message", "set_export_options"):
    _FAMILY_OF[_name] = FAMILY_DATA
for _name in ("create_layout", "export_layout", "edit_layout", "set_atlas", "open_layout", "preview_atlas",
              "add_chart_to_layout", "show_chart", "export_chart", "show_infographic", "export_infographic"):
    _FAMILY_OF[_name] = FAMILY_LAYOUT
for _name in ("search_open_data", "search_imagery", "find_place", "run_pyqgis", "run_chart_code", "load_skill",
              "change_settings", "apply_settings_profile", "turn_on_agent_options", "describe_settings",
              "get_setting", "diagnose_performance", "export_settings_profile", "show_settings_link",
              "agent_options", "turn_off_agent_options"):
    _FAMILY_OF[_name] = FAMILY_OUTSIDE
del _name


def family_of(name: str) -> str:
    """The family of a tool (one of ``TOOL_FAMILIES``); connectors and unknown tools fall outside."""
    text = str(name or "")
    if text.startswith("mcp_"):
        return FAMILY_OUTSIDE
    return _FAMILY_OF.get(text, FAMILY_OUTSIDE)


def family_title(family: str) -> str:
    """The English title of a family, for the Tools tab and the cards."""
    return FAMILY_TITLES.get(str(family or ""), str(family or FAMILY_OUTSIDE))


# The tools whose catalog title puzzles users, shown with plainer words in the Tools tab and the cards (S4).
# Keys are tool names, values the display titles (English source, translated where shown).
TOOL_DISPLAY_NAMES = {
    "set_exploring": "Linked preview",
    "cross_filter": "Cross-layer filter",
    "local_copy": "Local copy (detaches from the service)",
    "segment_objects": "AI object selection",
    "similar_objects": "Similar objects (AI)",
    "set_layer_options": "Layer panel options",
}


def display_title(name: str, title: str = "") -> str:
    """The title of a tool as the user reads it: the plainer words when it has some, else its catalog title."""
    return TOOL_DISPLAY_NAMES.get(str(name or ""), title or str(name or ""))


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

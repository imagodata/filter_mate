# -*- coding: utf-8 -*-
"""One line per tool, and the index of the tools a conversation may add with use_tools (token diet, lot 1).

Plain Python. A request carries the core of the tools only (core/agent/families.py); the instructions hold this
index, one line per tool the conversation may add: the model adds what a request needs in one use_tools call.
"""
from __future__ import annotations

from typing import Sequence

MAX_SUMMARY = 60
MAX_INDEX = 4800  # every tool of the chat (the worst case): 4,322 on 2026-11-16 (lot 2), 3,100 for the default settings
INDEX_TITLE = ("\n\nTools you can add with use_tools. Before saying a thing cannot be done, look here; add in one call "
               "every tool the request needs:")

SUMMARIES = {
    # reading the project
    "list_layers": "Layers with kind, count and filter",
    "filter_state": "Layers filtered now",
    "list_favorites": "Saved filters (favorites)",
    "describe_layer": "Fields, bands or point attributes of a layer",
    "field_values": "Distinct values of a field",
    "layer_statistics": "Count, sum, mean, min, max, in all or by group",
    "sample_features": "A few features with their attributes",
    "identify_at": "What lies at a point: features, raster values",
    "map_context": "Extent, scale, CRS, active layer, selections",
    "view_map": "See the map as an image",
    # filtering
    "preview_filter": "Count what an expression keeps, changing nothing",
    "apply_filter": "Filter a vector layer by an expression",
    "cross_filter": "Filter layers by their relation to a source layer",
    "geometry_filter": "Filter layers by a WKT area or extent",
    "point_cloud_filter": "Keep points by class, elevation, intensity, return",
    "clear_filters": "Remove the filters of layers",
    "apply_favorite": "Apply a favorite as it is",
    "export_layers": "Write layers, as filtered, to files",
    "undo_agent_step": "Undo the last request of the agent",
    # the map and the layer tree
    "zoom_to": "Zoom to a layer, a selection, an extent",
    "select_features": "Select features by an expression",
    "set_layers_visibility": "Show or hide layers",
    "group_layers": "Group layers or move them in the tree",
    "rename_layer": "Rename a layer or a group",
    "bookmark": "Spatial bookmarks: list, save, go to, remove",
    "map_theme": "Map themes: list, save, apply, remove",
    "set_project_crs": "Set the project CRS",
    "find_place": "Find a place by name or address",
    # styles and layouts
    "set_layer_style": "Style a layer: colors, classes, rules, ramp, relief",
    "set_labels": "Label features, or remove labels",
    "create_layout": "A print layout",
    "export_layout": "A print layout to PDF or PNG",
    # data and analysis
    "find_algorithms": "Find a Processing algorithm by words",
    "describe_algorithm": "Parameters of a Processing algorithm",
    "run_algorithm": "Run a Processing algorithm (buffer, clip...)",
    "add_field": "Add a field filled by an expression",
    "join_layers": "Join fields of a layer by a common field",
    "update_features": "Change attribute values (edit buffer)",
    "delete_features": "Delete features (edit buffer)",
    "add_features": "Add features from WKT (edit buffer)",
    "duplicate_layer": "A second layer on the same data",
    "contour_lines": "Contour lines of an elevation raster",
    "segment_objects": "SAM: objects guide features point at",
    "similar_objects": "SAM: objects like an example",
    # layers from elsewhere
    "add_layer": "Add a local file or a public https URL",
    "remove_layers": "Remove layers",
    "search_open_data": "Search an open data platform",
    "add_service_layer": "Add a WFS, WMS or WMTS layer",
    "search_imagery": "Satellite scenes over an area",
    "add_basemap": "Add a web basemap",
    "add_elevation": "Elevation of an area, as a raster",
    "add_population": "Population of an area, as a raster",
    "add_osm_features": "OpenStreetMap features of given tags in an area",
    "local_copy": "Copy a WFS / WMS layer to a local file, or back",
    "list_database_tables": "Tables of a PostgreSQL connection",
    "add_database_table": "Add a PostgreSQL table as a layer",
    # FilterMate itself
    "describe_settings": "Find settings of FilterMate",
    "get_setting": "Read a setting of FilterMate",
    "change_settings": "Change settings of FilterMate",
    "diagnose_performance": "Why FilterMate is slow, from its timings",
    "export_settings_profile": "Save changed settings as a profile",
    "apply_settings_profile": "Apply a profile of settings",
    "show_settings_link": "A button to a setting or feedback form",
    "agent_options": "Provider, sources, connectors, MCP server",
    "turn_off_agent_options": "Untick sources, connectors; stop the MCP server",
    "turn_on_agent_options": "Tick sources, connectors, MCP server, provider",
    "layer_options": "A layer's EXPLORING and FILTERING options",
    "set_layer_options": "Set EXPLORING and FILTERING options",
    "set_exploring": "Drive EXPLORING: its layer, its rail tools",
    "export_options": "EXPORTING panel options",
    "set_export_options": "Prepare the EXPORTING panel",
    # the conversation
    "load_skill": "Instructions of a kind of task",
    "use_tools": "Add tools of this index",
    "ask_user": "Ask questions with choices to click",
    "add_project_note": "Keep a fact about this project",
    "remove_project_note": "Forget a note of this project",
    "save_recipe": "Keep a request's changes as a recipe",
    "remove_recipe": "Forget a recipe",
    "create_widget": "A control in the AGENT panel to explore a layer",
    "remove_widget": "Remove a widget",
    "show_chart": "A d3 chart in the chat",
    "export_chart": "A chart as PNG, JPG or SVG",
    "describe_layout": "Read a layout",
    "set_atlas": "Atlas of a layout",
    "suggest_crs": "Projections suited to the data",
    "edit_layout": "Change a layout",
    "add_chart_to_layout": "A chart in a layout",
    "run_chart_code": "Draw a chart with your d3 code (expert)",
    "run_pyqgis": "Run Python in QGIS, approved by the user (expert)",
}


def index_block(available: Sequence) -> str:
    """The index of the tools ``available`` (``ToolSpec`` with their ``summary``), in their order; "" without any."""
    if not available:
        return ""
    return INDEX_TITLE + "".join(f"\n- {tool.name}: {tool.summary}" for tool in available)

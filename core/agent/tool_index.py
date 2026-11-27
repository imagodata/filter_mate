# -*- coding: utf-8 -*-
"""One line per tool, and the index of the tools a conversation may add with use_tools (token diet, lot 1).

Plain Python. A request carries the core of the tools only (core/agent/families.py); the instructions hold this
index, one line per tool the conversation may add: the model adds what a request needs in one use_tools call.
"""
from __future__ import annotations

from typing import Sequence

MAX_SUMMARY = 60
# Every tool of the chat (the worst case): 4,322 on 2026-11-16 (lot 2), 3,100 for the default settings; on 2026-11-22
# the layouts, projections, cartograms, forms, styles and official styles of the agent brought it near 5,000; on
# 2026-11-26 the five visible-automation tools (open_layout, preview_atlas, flash_features, set_active_layer and
# show_message) bring it near 5,300.
MAX_INDEX = 5500
INDEX_TITLE = ("\n\nTools you can add with use_tools. Before saying a thing cannot be done, look here; "
               "add in one call every tool the request needs:")

SUMMARIES = {
    # reading the project
    "list_layers": "Layers with kind, count and filter",
    "filter_state": "Layers filtered now",
    "list_favorites": "Saved filters",
    "describe_layer": "Layer fields, bands or point attributes",
    "field_values": "Distinct values of a field",
    "layer_statistics": "Count, sum, mean, min, max, in all or by group",
    "sample_features": "Sample features and attributes",
    "identify_at": "Features and raster values at a point",
    "map_context": "Extent, scale, CRS, active layer, selections",
    'qgis_capabilities': 'QGIS actions and panels',
    'control_qgis': 'QGIS tables, properties, panels, tools, views',
    "view_map": "Map image",
    # filtering
    "preview_filter": "Count matching features without changes",
    "apply_filter": "Filter a vector layer by an expression",
    "cross_filter": "Filter layers by their relation to a source layer",
    "geometry_filter": "Filter layers by a WKT area or extent",
    "point_cloud_filter": "Keep points by class, elevation, intensity, return",
    "clear_filters": "Remove the filters of layers",
    "apply_favorite": "Apply a favorite as it is",
    "save_favorite": "Keep the current filter as a favorite",
    "export_layers": "Write layers, as filtered, to files",
    "undo_agent_step": "Undo the last request of the agent",
    # the map and the layer tree
    "zoom_to": "Zoom to a layer, a selection, an extent",
    "select_features": "Select features by an expression",
    "set_layers_visibility": "Show or hide layers",
    "group_layers": "Group or move layers in the tree",
    "rename_layer": "Rename layer/group",
    "bookmark": "Spatial bookmarks: list, save, go to, remove",
    "map_theme": "Map themes: list, save, apply, remove",
    "set_project_crs": "Set the project CRS",
    "find_place": "Find a place by name or address",
    # styles and layouts
    "set_layer_style": "Style: colors, classes, heatmap, sizes, relief",
    "set_labels": "Label features, or remove labels",
    "list_style_presets": "IGN/OSM layer styles",
    "apply_style_preset": "Apply an IGN/OSM style",
    "create_layout": "A print layout",
    "export_layout": "A print layout to PDF or PNG",
    # data and analysis
    "find_algorithms": "Find Processing algorithms",
    "open_model": "Processing model editor",
    "describe_algorithm": "Processing parameters",
    "run_algorithm": "Run Processing (buffer, clip...)",
    "add_field": "Add a field filled by an expression",
    "join_layers": "Join layer fields by key",
    "set_form": "Attribute form of a layer",
    "relations": "Parent/child relations",
    "update_features": "Change attribute values (edit buffer)",
    "delete_features": "Delete features (edit buffer)",
    "add_features": "Add features from WKT (edit buffer)",
    "duplicate_layer": "A second layer on the same data",
    "contour_lines": "Contour lines of an elevation raster",
    "segment_objects": "SAM: objects guide features point at",
    "similar_objects": "SAM: objects like an example",
    # layers from elsewhere
    "add_layer": "Add a file or public https URL",
    "remove_layers": "Remove layers",
    "search_open_data": "Open data search",
    'search_data_sources': 'Find candidate data sources on the web',
    "add_service_layer": "Add a WFS, WMS or WMTS layer",
    "search_imagery": "Satellite scenes over an area",
    "add_basemap": "Add a web basemap",
    "add_elevation": "Elevation of an area, as a raster",
    "add_population": "Population of an area, as a raster",
    "add_osm_features": "OSM features by tags and area",
    "local_copy": "WFS/WMS copy or original",
    "list_database_tables": "Tables of a PostgreSQL connection",
    "add_database_table": "Add a PostgreSQL table as a layer",
    # FilterMate itself
    "describe_settings": "Find settings of FilterMate",
    "get_setting": "Read a setting of FilterMate",
    "change_settings": "Change settings of FilterMate",
    "diagnose_performance": "Why FilterMate is slow, from its timings",
    "export_settings_profile": "Save changed settings as a profile",
    "apply_settings_profile": "Apply a profile of settings",
    "show_settings_link": "Settings or feedback link",
    "agent_options": "Sources on/off, provider, MCP",
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
    "create_widget": "AGENT control to explore a layer",
    "remove_widget": "Remove a widget",
    "show_chart": "A Python chart in the chat",
    "export_chart": "A chart as PNG, JPG, SVG or PDF",
    "show_infographic": "Up to four charts in one infographic",
    "export_infographic": "An infographic as offline HTML, an image, SVG or PDF",
    "describe_layout": "Read a layout",
    "open_layout": "Open a layout in its designer",
    "preview_atlas": "Turn the pages of the atlas preview",
    "flash_features": "Flash features on the map, selecting nothing",
    "set_active_layer": "Make a layer active and show it in the tree",
    "show_message": "Show a message in the bar of QGIS",
    "set_atlas": "Atlas of a layout",
    "suggest_crs": "Projections suited to the data",
    "design_style": "A style from a validated palette",
    "list_palettes": "Checked palettes by role",
    "make_cartogram": "Areas that show a number",
    "edit_layout": "Change a layout",
    "add_chart_to_layout": "A chart in a layout",
    "run_chart_code": "A chart drawn by your d3 code",
    "run_pyqgis": "Run approved Python in QGIS (expert)",
}


def index_block(available: Sequence) -> str:
    """The index of the tools ``available`` (``ToolSpec`` with their ``summary``), in their order; "" without any."""
    if not available:
        return ""
    return INDEX_TITLE + "".join(f"\n- {tool.name}: {tool.summary}" for tool in available)

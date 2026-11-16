# -*- coding: utf-8 -*-
"""One line per tool, and the index of the tools a conversation may add with use_tools (token diet, lot 1).

Plain Python. A request carries the core of the tools only (core/agent/families.py); the instructions end with this
index, one line per tool the conversation may add: the model adds what a request needs in one use_tools call.
"""
from __future__ import annotations

from typing import Sequence

MAX_SUMMARY = 90
MAX_INDEX = 6000
INDEX_TITLE = ("\n\nTools you can add with use_tools. Before saying a thing cannot be done, look here; add in one call "
               "every tool the request needs:")

SUMMARIES = {
    # reading the project
    "list_layers": "List the layers of the project with their kind, count and filter",
    "filter_state": "List the layers filtered now, of any kind, with their filter",
    "list_favorites": "List the saved filters (favorites) of the project",
    "describe_layer": "Fields, bands or point attributes of a layer, with its kind, CRS and count",
    "field_values": "Distinct values of a field, to write a filter with the exact spelling",
    "layer_statistics": "Count, sum, mean, min, max of a field or geometries, in all or by group",
    "sample_features": "A few features of a vector layer with their attributes",
    "identify_at": "What lies at a point of the map: features and raster values",
    "map_context": "The visible extent, scale, CRS, active layer and selections of the map",
    "view_map": "Look at the map as an image, to check a change judged by eye",
    # filtering
    "preview_filter": "Count what a filter expression keeps, without changing the layer",
    "apply_filter": "Set the filter expression of a vector layer, or narrow it with AND",
    "cross_filter": "Filter layers by their spatial relation to a source layer (intersect, within, distance)",
    "geometry_filter": "Filter layers by a WKT geometry: a drawn area, an extent, an outline",
    "point_cloud_filter": "Keep the points of a point cloud by class, elevation, intensity or return",
    "clear_filters": "Remove the filters of layers, or of every layer",
    "apply_favorite": "Apply a saved filter (favorite) as it is",
    "export_layers": "Write layers, as filtered now, to files (asks the user first)",
    "undo_agent_step": "Undo the last request of the agent as a whole",
    # the map and the layer tree
    "zoom_to": "Zoom the map to a layer, its selection, a WKT extent or everything",
    "select_features": "Select the features of a vector layer matching an expression",
    "set_layers_visibility": "Show or hide layers in the layer tree",
    "group_layers": "Put layers in a group of the layer tree, or move them above another",
    "rename_layer": "Rename a layer or a group of the layer tree",
    "bookmark": "List, save, go to or remove the spatial bookmarks of the project",
    "map_theme": "List, save, apply or remove the map themes of the project",
    "set_project_crs": "Set the CRS of the project, which the map follows",
    "find_place": "Find a place by its name or address on a geocoder the user allowed",
    # styles and layouts
    "set_layer_style": "Draw a layer anew: one color, categories, classes, rules, raster ramp, relief",
    "set_labels": "Label the features of a vector layer with a field or expression, or remove labels",
    "create_layout": "Make a print layout of the map with title, legend, scale bar and north arrow",
    "export_layout": "Write a print layout as a PDF or PNG file (asks the user first)",
    # data and analysis
    "find_algorithms": "Find a Processing algorithm of QGIS by words",
    "describe_algorithm": "How to give each parameter of a Processing algorithm",
    "run_algorithm": "Run a Processing algorithm; the layers it makes join the project",
    "add_field": "Add a field to a vector layer, filled by an expression, in its edit buffer",
    "join_layers": "Join the fields of a layer to another by a common field",
    "update_features": "Change attribute values of features, in the edit buffer",
    "delete_features": "Delete features of a vector layer, in its edit buffer (asks the user first)",
    "add_features": "Add features from WKT geometries and attributes, in the edit buffer",
    "duplicate_layer": "Add a second layer on the same data, with its own style and filter",
    "contour_lines": "Draw the contour lines of an elevation raster as a new layer",
    "segment_objects": "Draw with SAM, on a raster, the objects that guide features point at",
    "similar_objects": "Find with SAM, on a raster, the objects that look like an example",
    # layers from elsewhere
    "add_layer": "Add a layer from a local file or a public https URL",
    "remove_layers": "Remove layers from the project (asks the user first)",
    "search_open_data": "Search datasets on an open data platform the user allowed",
    "add_service_layer": "Add a layer of a WFS, WMS or WMTS service",
    "search_imagery": "Find satellite scenes over an area, newest first",
    "add_basemap": "Add a web basemap under the other layers",
    "add_elevation": "Add the elevation of an area as a raster",
    "add_population": "Add the population of an area as a raster of people per pixel",
    "add_osm_features": "Add the OpenStreetMap features of given tags in an area",
    "list_database_tables": "List the tables of a PostgreSQL connection the user enabled",
    "add_database_table": "Add a table of a PostgreSQL connection the user enabled as a layer",
    # FilterMate itself
    "describe_settings": "Find settings of FilterMate itself by words or section",
    "get_setting": "Read one setting of FilterMate by its path",
    "change_settings": "Change settings of FilterMate, all or none, shown to the user first",
    "diagnose_performance": "Read the timings FilterMate logged, to find why it is slow",
    "export_settings_profile": "Save the settings the user changed as a profile file to share",
    "apply_settings_profile": "Apply a profile of settings of FilterMate by its name",
    "show_settings_link": "Put a button in the thread to a setting the user changes themselves",
    "layer_options": "What a layer shows in FilterMate's EXPLORING panel, and its FILTERING options",
    "set_layer_options": "Set what layers show in EXPLORING and their FILTERING options",
    "export_options": "The options of FilterMate's EXPORTING panel",
    "set_export_options": "Prepare FilterMate's EXPORTING panel for the user to export from it",
    # the conversation
    "load_skill": "Load the instructions of a kind of task",
    "use_tools": "Add tools of this index to the request",
    "ask_user": "Ask the user one to four questions with choices to click",
    "add_project_note": "Keep a fact about this project for the next conversations",
    "remove_project_note": "Forget a note kept for this project",
    "save_recipe": "Keep the changes of a request as a recipe the user runs again",
    "remove_recipe": "Forget a recipe of this project",
    "create_widget": "Make a control in the AGENT panel to explore a vector layer",
    "remove_widget": "Remove a widget of the AGENT panel",
    "run_pyqgis": "Run Python code in QGIS, read and approved by the user (expert mode)",
}


def index_block(available: Sequence) -> str:
    """The index of the tools ``available`` (``ToolSpec`` with their ``summary``), in their order; "" without any."""
    if not available:
        return ""
    return INDEX_TITLE + "".join(f"\n- {tool.name}: {tool.summary}" for tool in available)

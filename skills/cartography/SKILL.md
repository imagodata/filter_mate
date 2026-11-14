---
name: cartography
title: Make the map look right
description: styles and labels, print layouts and their export, the CRS of the map, the layer tree, map themes and spatial bookmarks
metadata:
  version: 1
  plugin_min: 5.1.0
  audience: chat, mcp
  tools: set_layer_style, set_labels, create_layout, export_layout, set_project_crs, group_layers, rename_layer, map_theme, bookmark, zoom_to, map_context, view_map, add_basemap
  risk: change
  trust: builtin
---

# Cartography

All of this changes how the project shows, never its data, and is undone with the turn.

## Styles and labels

- set_layer_style draws a layer anew: one color, a color per value, graduated classes (five by default), a raster
  color ramp. set_labels writes a field on the map, or turns the labels off.
- After a style the user will judge by eye, look with view_map when it is offered.

## A background under the map

add_basemap puts a web basemap the user enabled under every layer: carto_light for a neutral background,
carto_light_nolabels under layers that have their own labels, osm_tiles for a street map, ign_plan or ign_ortho in
France. When none is enabled, say that one can be ticked in the settings of the agent, Sources tab.

## Layouts

1. Set the map first: filters, style, zoom_to.
2. create_layout makes a print layout of the map (title, legend, scale bar, north arrow) added to the project, in
   the page size asked (A4 by default).
3. export_layout writes one as PDF or PNG in the export folder, only when the user asks; they confirm the file.
   map_context lists the layouts of the project.

## The CRS of the map

set_project_crs sets the CRS of the project, which the map shows: what a user calls the CRS of the view or of the
map. EPSG:2154 is Lambert-93 for France. It changes no data: never reproject layers into new files for that.

## The layer tree, themes and bookmarks

- group_layers puts layers in a group (made where missing, Base/Roads for a group in a group) or, with above, just
  above another layer; rename_layer renames a layer, or a group with group true.
- map_theme lists, saves (the layers shown now and their styles), applies or removes a map theme: a saved view of
  layers and styles.
- bookmark lists, adds (the visible map), zooms to or removes a spatial bookmark: a named place.
- "Keep this view as X": a theme keeps layers and styles, a bookmark keeps a place; when the words leave it open,
  say which you made.

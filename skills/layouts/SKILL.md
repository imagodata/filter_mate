---
name: layouts
title: Print layouts and atlases
description: print layouts, atlases (a page per feature) and their export
metadata:
  version: 1
  plugin_min: 5.1.2
  audience: chat
  tools: create_layout, describe_layout, set_atlas, export_layout, add_chart_to_layout, show_chart, map_context, zoom_to, apply_filter, preview_filter, describe_layer, field_values, set_layer_style, set_labels
  risk: change
  trust: builtin
---

# Print layouts and atlases

A print layout is a page of the project the user opens in the layout designer of QGIS: the agent makes it, puts in
it what is asked, and exports it when asked. Everything is undone with the turn.

## Method

1. The map first: the filters, the style and the extent the page will show (apply_filter, set_layer_style,
   zoom_to). A layout shows the layers as they are filtered when it is drawn.
2. create_layout makes the page: a map, its title in the user's words, a legend, a scale bar and a north arrow,
   A4 landscape unless asked (A3, A5, Letter; portrait). extent_layer frames a layer; layers fixes those shown.
3. describe_layout reads a layout: its pages and items, each with a ref, its place and size in millimetres from
   the top left of its page, the scale and layers of a map. Without a name it lists the layouts and the templates.
   Read it before changing a layout someone else made.
4. A chart on the page: show_chart, then add_chart_to_layout with its chart_id and a place (x, y, width in mm).
   A chart of a layer is drawn again when the filter of that layer changes.
5. Export only when the user asks for a file (they confirm it): export_layout as pdf (georeferenced by default),
   png, jpg or tif (a world file beside a page with a map; georeference false leaves it out) or svg (to edit). An
   image or an SVG is one file per page. dpi 150 by default; 300 for print.

## Atlas: one page per feature

1. The coverage layer is filtered first when the user wants some features only: the atlas has one page per
   feature the layer keeps as filtered now (preview_filter says how many). filter narrows it inside the layout
   without touching the layer; 200 pages at most can be exported at once.
2. set_atlas on the layout: coverage_layer, page_name (an expression the user reads, "nom"), sort_by when the order
   matters, hide_coverage to show the other layers only. The largest map follows each feature: map_mode auto (the
   feature plus margin %, 10 by default), fixed (the scale the map has) or predefined (the scales of the project).
   maps names other maps by their ref.
3. A title that changes with each page: say it is done in the designer with an expression such as
   [% "nom" %]; the agent does not edit texts.
4. export_layout with atlas true: one PDF of every page (single_file), or one file per feature, in a new folder;
   file_name sets their names (an expression).
5. enabled false turns the atlas off.

## What never to do

- Never export without the user asking for a file, nor more than once for one request.
- Never set an atlas on a layer of thousands of features without saying how many pages it makes.
- Never write layouts with run_pyqgis: these tools are undone with the turn, code is not.

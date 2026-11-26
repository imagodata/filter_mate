---
name: layouts
title: Print layouts and atlases
description: print layouts, atlases (a page per feature) and their export
metadata:
  version: 3
  plugin_min: 5.1.2
  audience: chat
  tools: create_layout, describe_layout, edit_layout, set_atlas, export_layout, open_layout, preview_atlas, add_chart_to_layout, show_chart, map_context, zoom_to, apply_filter, preview_filter, describe_layer, field_values, set_layer_style, set_labels
  risk: change
  trust: builtin
---

# Print layouts and atlases

A print layout is a page of the project the user opens in the layout designer of QGIS: the agent makes it, puts in
it what is asked, and exports it when asked. Layout changes are undone with the turn; opening the designer and
turning preview pages are not. open_layout and preview_atlas require a QGIS window and belong to the built-in
chat only, never to external MCP clients.

## Method

1. The map first: the filters, the style and the extent the page will show (apply_filter, set_layer_style,
   zoom_to). A layout shows the layers as they are filtered when it is drawn. For the style itself, load the skill
   styles.
2. create_layout makes the page: a map, its title in the user's words, a legend, a scale bar and a north arrow,
   A4 landscape unless asked (A3, A5, Letter; portrait). extent_layer frames a layer; layers fixes those shown.
   template starts from a template of the profile instead (describe_layout lists them): its texts stay as they are.
   open_layout opens the page in the layout designer, in front, for the user to see and finish.
   One page carries one message: its title says it, short, top left.
3. describe_layout reads a layout: its pages and items, each with a ref, its place and size in millimetres from
   the top left of its page, the scale and layers of a map. Without a name it lists the layouts and the templates.
   Read it before changing a layout someone else made, and leave the map room: the map stays the largest item of
   its page.
4. edit_layout changes a layout in one call, all or nothing (20 changes at most), each change a do:
   - add_text (text, font_size; [% "nom" %] shows a field of the atlas feature, [% @atlas_pagename %] its name);
   - add_map with extent_layer, or overview_of a map (a map of situation that frames where the other one is);
   - add_legend, add_scale_bar, add_north_arrow (of map, the largest by default), add_shape (a frame);
   - add_table: an attribute table of layer, columns, max_rows (30 by default); the rows of each atlas page when
     layer is the coverage layer;
   - add_page; move (x, y, width, height, page), remove, set_text, set_map (layers, extent_layer, scale) by ref.
   Places are in mm from the top left of a page: read describe_layout first and leave the map room.
5. A chart on the page: show_chart, then add_chart_to_layout with its chart_id and a place (x, y, width in mm).
   A chart of a layer is drawn again when the filter of that layer changes. For the chart itself, load the skill
   charts.
6. Export only when the user asks for a file (they confirm it): export_layout as pdf for paper (georeferenced by
   default), png or jpg for slides, tif (a world file beside a page with a map; georeference false leaves it out)
   or svg (to edit). An image or an SVG is one file per page. dpi 150 by default; 300 for print.

## Page design

- The map leads: the largest item of the page, with white space around it; nothing is put over it.
- The legend sits beside the map, with only the layers the page shows; short titles in the user's words.
- The scale bar and the north arrow go together at the bottom, tied to the largest map.
- An overview map stays small, top right.
- A chart sits at the bottom right, drawn light for paper; a table keeps 30 rows at most, fewer read better, with
  short column names.
- Labels after the style: set_labels with a buffer, the names in the user's words.

## Atlas: one page per feature

1. The coverage layer is filtered first when the user wants some features only: the atlas has one page per
   feature the layer keeps as filtered now (preview_filter says how many). filter narrows it inside the layout
   without touching the layer; 200 pages at most can be exported at once.
2. set_atlas on the layout: coverage_layer, page_name (an expression the user reads, "nom"), sort_by when the order
   matters, hide_coverage to show the other layers only. The largest map follows each feature: map_mode auto (the
   feature plus margin %, 10 by default), fixed (the scale the map has) or predefined (the scales of the project).
   maps names other maps by their ref.
3. A title that changes with each page: edit_layout add_text or set_text with [% "nom" %] (a field of the
   coverage layer) or [% @atlas_pagename %].
4. export_layout with atlas true: one PDF of every page (single_file), or one file per feature, in a new folder;
   file_name sets their names (an expression).
5. enabled false turns the atlas off.
6. preview_atlas turns the pages of the preview (first, previous, next, last); in the designer showing the layout
   the preview is turned on so the user sees the page change. The atlas itself is unchanged.

## What never to do

- Never export without the user asking for a file, nor more than once for one request.
- Never set an atlas on a layer of thousands of features without saying how many pages it makes.
- Never write layouts with run_pyqgis: these tools are undone with the turn, code is not.
- Never cover the map with a legend, a chart, a table or a text: the map stays the largest item of its page.

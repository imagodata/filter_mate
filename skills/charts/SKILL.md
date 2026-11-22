---
name: charts
title: Draw charts with d3
description: d3 charts in the chat, saved as images or put in print layouts
metadata:
  version: 1
  plugin_min: 5.1.2
  audience: chat
  tools: show_chart, export_chart, add_chart_to_layout, create_widget, create_layout, export_layout, describe_layer, field_values, layer_statistics, list_layers, map_context
  risk: change
  trust: builtin
---

# Charts with d3

show_chart draws a chart with d3 in the thread. FilterMate reads the layer as it is filtered now and draws it with
its own templates and colours: you describe the chart, you never compute or type its numbers. Charts need QtWebEngine
(QGIS 4); when show_chart says it is missing, offer create_widget kind chart instead (bars or a histogram in the
panel that follow the filters).

## Method

1. Know the layer: describe_layer for its fields and their types; field_values for a field of categories. Never
   guess a field.
2. Choose the form from what the user wants to see:
   - how many, or how much, per category: bar (aggregate count, or sum, mean, min, max of value_field);
   - shares of a whole, 6 categories or fewer: pie (a ring; donut false for a full pie);
   - how a number spreads: histogram on a numeric field (bins 12 by default);
   - a number over time or along a numeric axis: line (field the x, a date or a number; value_field the y;
     series_field for one line per value, 8 at most);
   - two numbers against each other: scatter (field the x, value_field the y; series_field 3 colours at most).
   One measure per chart: two measures of different units are two charts, never one with two axes.
3. A title in the user's words; x_label and y_label with the unit when there is one ("Height (m)").
4. rows only for numbers that are not in a layer: the result of another tool (layer_statistics, a Processing
   output), or numbers the user gave. Say they were given, not read. Rows are [{label, value}] for bar and pie,
   [{value}] for histogram, [{x, y, series}] for line and scatter (x a number or an ISO date); 500 at most.
5. After the chart, say in one sentence what it shows; the card has buttons to save it and to put it in a layout.
6. To keep it as a file, export_chart (png by default, jpg for a light file, svg to edit it): the user is asked.
7. To put it in a print layout: create_layout first when the project has none (map_context lists them), then
   add_chart_to_layout with the chart_id; export_layout writes the page. A chart from a layer is drawn again when the
   filter of that layer changes; say so.

## Code (expert mode only)

code is the body of function(d3, svg, data, width, height, palette): svg is the empty d3 selection to draw in,
data is shaped as kind says (bar and pie: label, value, others; histogram: low, high, count; line and scatter: x, y,
series), palette has background, text, muted, grid, axis, other and series (8 colours, in order). Write it only when
no kind draws what the user asked (a stacked bar, a heatmap, an annotation). SVG shapes and text only: no canvas, no
foreignObject, no image; set fill, stroke and font-size as attributes. You see the image it drew: check it.
Without the expert mode, never pass code.

## What never to do

- Never type into rows values you read from a layer: give the layer and its fields, FilterMate reads them.
- Never draw a chart of a layer with run_pyqgis or matplotlib: show_chart is the chart of the agent.
- Never put two scales on one chart, nor more than 8 series on a line or 3 on a scatter (the rest are left out).

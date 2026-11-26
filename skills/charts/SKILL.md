---
name: charts
title: Draw charts and infographics
description: charts in the chat, vector PDF and image exports, offline infographics and print layouts
metadata:
  version: 4
  plugin_min: 5.1.2
  audience: chat
  tools: show_chart, run_chart_code, export_chart, add_chart_to_layout, show_infographic, export_infographic, create_widget, create_layout, export_layout, describe_layer, field_values, layer_statistics, list_layers, map_context
  risk: change
  trust: builtin
  requires: show_chart
---

# Charts and infographics

show_chart draws a chart in Python in the thread on QGIS 3/Qt5 and QGIS 4/Qt6. FilterMate reads the layer as it is
filtered now and draws it with its own templates and colours: you describe the chart, you never compute or type its
numbers. Only run_chart_code needs QtWebEngine. create_widget kind chart gives live bars or a histogram in the panel.

## Method

1. Know the layer: describe_layer for its fields and their types; field_values for a field of categories. Never
   guess a field.
2. Choose the form from what the user wants to see:
   - how many, or how much, per category: bar (aggregate count, or sum, mean, min, max of value_field), the largest
     first (sort value), the 10 largest and the rest in one grey Others (limit); horizontal true when the names are
     long, so every name reads;
   - shares of a whole, 6 categories or fewer: pie (a ring; donut false for a full pie); past 6 slices a bar reads
     better;
   - how a number spreads: histogram on a numeric field (bins 12 by default, up to 50 for a wide range);
   - a number over time or along a numeric axis: line (field the x, a date or a number with x_type time or number;
     value_field the y; series_field for one line per value, 8 at most);
   - two numbers against each other: scatter (field the x, value_field the y; series_field 3 colours at most; past
     5000 dots the layer is sampled, evenly: say so);
   - big numbers side by side: kpi (4 cards by default, 8 at most, including Others when categories are grouped);
   - shares of a whole with many categories: treemap (rectangles sized by share, past 6 slices it reads better than
     a pie; negatives are left out, said);
   - a number over time with its ground filled to zero: area (as line, for levels, totals, flood heights;
     several series overlap, they are not stacked).
   One measure per chart: two measures of different units are two charts, never one with two axes.
3. A title in the user's words, 80 characters at most; x_label and y_label with the unit when there is one ("Height
   (m)"); no axis label where the axis names itself (the categories of a bar).
4. A size for the use: 640 by 400 by default; wider for a long time series or many bars, taller for many horizontal
   bars; 280 by 200 at least.
5. rows only for numbers that are not in a layer: the result of another tool (layer_statistics, a Processing
   output), or numbers the user gave. Say they were given, not read. Rows are [{label, value}] for bar, pie, kpi and
   treemap, [{value}] for histogram, [{x, y, series}] for line, scatter and area (x a number or an ISO date);
   500 at most.
6. After the chart, say in one sentence what it shows, on the data as filtered now (how many features); the card has
   buttons to save it and to put it in a layout.
7. To keep it as a file, export_chart (png by default, jpg for a light file, svg to edit it, pdf for vectors;
   192 dpi by default, 300 for print, 48 to 600 for images): the user is asked. It is drawn light
   for paper, even in a dark chat. DPI does not change the size of a vector PDF.
8. To put it in a print layout: create_layout first when the project has none (map_context lists them), then
   add_chart_to_layout with the chart_id and a place (its bottom right by default); export_layout writes the page.
   For the page itself, load the skill layouts. A chart from a layer is drawn again when the filter of that layer
   changes; say so. A chart of rows or of code stays as it was drawn.
9. A save or an export shows the chart as its card shows it, drawn light: draw it again with show_chart to take a
   new filter into account.
10. To sum up in one figure, show_infographic stacks charts of this conversation under a title, with a caption and a
    source: draw each part with show_chart first (a kpi strip for the big numbers, then the chart that tells the
    story), then stack their chart_ids in order, 4 at most. Only when the user asks for an infographic, a figure or
    something to share. It is always light and stays as composed when the filters change; say both. To keep it as a
    file, export_infographic (a standalone HTML page by default: it opens out of QGIS, offline, without scripts or
    fetched assets; png, jpg, svg or vector pdf for paper): the user is asked. A layout never holds one.

## Limits and sharing

- A chart is 280–1600 by 200–1200 pixels. An infographic stacks up to four charts and is at most 6000 pixels tall.
  An image export above 40 million pixels is refused: choose fewer parts or lower DPI. SVG, HTML and PDF retain
  vectors. Long labels are shortened to fit; the HTML caption and source keep their full text.
- Treemaps draw positive shares only; negative shares are reported as omitted. Their Python rectangle arrangement
  differs from the expert d3 template. Very small tiles cannot hold labels. KPI values use compact number formats.
- In tested Qt5 exports, PDF text becomes vector outlines and cannot be selected or extracted. Qt6 exports embed
  fonts and retain extractable text. Both retain vector geometry. For a compact KPI strip, ask for height 200.
- When values are not shared, no layer categories, numbers or chart image are sent to the model. Counts and chart
  metadata can still be returned. Local cards and exported files contain their values: sharing a file shares those
  values. Expert errors are redacted, and an expert chart is never rerun for an export or infographic.

## Code (expert mode only)

run_chart_code draws a chart of this conversation again with d3 you write, over its data: only when no kind draws
what the user asked (stacked bars, a heatmap, an annotation), and only when it is offered (expert mode with
QtWebEngine). QGIS 3 installations without it cannot run code charts. The user reads the code and says yes at each
run. Draw the data with show_chart first, then run_chart_code with its chart_id,
a purpose in one sentence and code: the body of function(d3, svg, data, width, height, palette). svg is the empty
d3 selection to draw in, data is shaped as kind says (bar, pie, kpi and treemap: label, value, others; histogram:
low, high, count; line, scatter and area: x, y, series), palette has background, text, muted, grid, axis, other and series (8 colours, in
order). Keep the habits of the templates: a title, labelled axes, room for long labels; the series in the order of
palette.series, the text in palette.text, the axes in palette.muted, what is left out in palette.other. SVG shapes
and text only: an image, a canvas or a link is left out; set fill, stroke and font-size as attributes, with no
stylesheet, no classes, no em and no dominant-baseline: the file is drawn by QtSvg, which reads none of them. You see
the image it drew when the user shares values: check it.

## What never to do

- Never type into rows values you read from a layer: give the layer and its fields, FilterMate reads them.
- Never draw a chart of a layer with run_pyqgis or matplotlib: show_chart is the chart of the agent.
- Never put two scales on one chart, nor more than 8 series on a line or 3 on a scatter (the rest are left out).
- Never a pie of more than 6 slices, nor upright bars with names that no longer read: a bar, the largest first, with
  the rest in Others; horizontal true for long names.

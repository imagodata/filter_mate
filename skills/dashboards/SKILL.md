---
name: dashboards
title: Build a dashboard of widgets
description: build a small dashboard in the AGENT panel to explore a vector layer without asking again (sliders, ticked values, numbers, charts), saved with the project
metadata:
  version: 1
  plugin_min: 5.1.0
  audience: chat
  tools: create_widget, remove_widget, apply_filter, describe_layer, field_values, layer_statistics, list_layers
  risk: change
  trust: builtin
---

# Dashboards of widgets

create_widget makes controls described as data and drawn by FilterMate: no code, saved with the project, undone with
the turn. Use them when the user wants to explore, play with values, follow a number or see a distribution. Never
write code (run_pyqgis) to make a window or a panel: widgets are the interface the agent builds.

## Method

1. Know the layer: describe_layer for its fields and types, field_values for the values a field takes,
   layer_statistics for the range of a number. Never guess a field.
2. Plan a few widgets, in this order, and tell the user what each one does:
   - a stat with count first (the number of features shown, kept up to date);
   - a chart of the field that matters most (the 8 most frequent values and the others, or a histogram of 10
     classes for a number);
   - a range on the key numeric field (two bounds: moving them filters the layer);
   - values on a field with few values (50 at most; unticking filters the layer).
3. Titles in the user's words, short.
4. Then say how to use them: the widgets of one layer narrow it together, after the filter it had when its first
   widget was made; a chart or a stat filters nothing.

## Limits

- 12 widgets at most in the panel; one widget that filters per field of a layer (a second one on that field is
  refused: choose another field or remove_widget first).
- Vector layers only; numeric fields for range and for a stat other than count.
- The widget ids come with each request: remove_widget takes one when the user asks to remove it.

## What never to do

- Never stack many widgets the user did not ask for: three or four answer most requests.
- Never set a filter with apply_filter on the same field a widget controls: the widget would no longer show it.

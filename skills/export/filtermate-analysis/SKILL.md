---
name: filtermate-analysis
description: Analyse with Processing, fields and joins through the MCP server of the FilterMate QGIS plugin: make new layers with the Processing algorithms of QGIS (buffer, centroids, dissolve, clip, intersection, join by location, heatmap, slope...), add computed fields, join tables. Use when the user asks for it in QGIS with FilterMate.
---

<!-- Generated from skills/analysis/SKILL.md by scripts/export_agent_skills.py: do not edit by hand. -->

Needs the MCP server of FilterMate: in QGIS, Agent settings (menu ⋯ of the AGENT panel), tab Other applications: turn it on and copy the configuration for this application. Its tools carry the names below.

# Analysis

## Filter or make a layer?

To keep features of a layer, filter it (apply_filter and the other filters): filters change no data and need no new
layer. Make a layer only when the user asks for something new: a buffer zone, centroids, a dissolve, a clip, an
intersection, points to a heatmap, a slope. To answer "how many" or "how long", compute with layer_statistics.

## Processing

1. find_algorithms with English words (buffer, centroid, dissolve, clip, intersection, join attributes by location,
   heatmap, slope).
2. describe_algorithm for its parameters: never guess a parameter name or a value.
3. run_algorithm with the layers by name or id and plain values; give names to the outputs the user will see.

The layers it makes are added to the project and undone with the turn. Distances are in the units of the layer's CRS
(describe_layer says it): a geographic CRS counts in degrees, so reproject or say so.

## Fields and joins

- add_field adds a field to a vector layer in its edit buffer, filled at once by a QGIS expression when given (a
  density, a category, a cleaned name, a height per floor guarded against zero). Nothing is saved: say the user saves
  the layer edits.
- join_layers shows the fields of another layer or table beside each feature, matched by a field, without writing
  anything; keep the fields the user asked for.
- Prefer a field or a join to explaining how to compute it by hand.

## What never to do

- Never make a layer when a filter answers the request.
- Never run an algorithm that writes over an existing file or layer of the user.

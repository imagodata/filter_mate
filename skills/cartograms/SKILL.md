---
name: cartograms
title: Cartograms and maps out of the ordinary
description: cartograms (areas that show a number), hexagon and grid maps
metadata:
  version: 1
  plugin_min: 5.2.0
  audience: chat, mcp
  tools: make_cartogram, describe_layer, layer_statistics, apply_filter, preview_filter, set_layer_style, set_labels, find_algorithms, describe_algorithm, run_algorithm, suggest_crs, set_project_crs, list_layers
  risk: change
  trust: builtin
---

# Cartograms and maps out of the ordinary

A cartogram gives each place the size of a quantity (people, votes, cases) instead of its land: big empty regions
shrink, dense small ones grow. It answers "where are the people, the votes" better than a choropleth, which a big
empty region dominates.

## Cartograms: make_cartogram

1. describe_layer: the numeric field of the quantity (a count or a total: population, votes; never a rate or a
   density, which already divide by area). Filter the layer first when the map is about some places only
   (preview_filter, apply_filter): the cartogram uses the layer as filtered now, 5,000 features at most.
2. Choose the kind:
   - contiguous: the polygons deform and stay joined; the map still reads as the territory. 8 iterations by
     default; more (up to 30) when error_after stays far above 1. Polygons only.
   - noncontiguous: each polygon keeps its shape and is scaled around its centre; the densest keeps its size. Exact
     areas, gaps between places.
   - dorling: one circle per place, its area the quantity, moved apart so that none overlap; demers: squares.
     Points accepted. Best for a quick comparison of many places.
3. The new layer comes at the top of the tree; then set_layer_style on it, usually graduated on a second field (a
   rate, a share, the winner) so that size shows the quantity and colour another variable, and set_labels with the
   names when there are few places.
4. Say what it shows, and error_after: 1 is exact; a contiguous cartogram above 1.3 is a rough one.
5. A layer in degrees is compared in an equal-area projection made for it (the answer names it): suggest_crs and
   set_project_crs put the map in a suitable one too.

## Hexagon and grid maps (Processing)

For many points (accidents, trees, shops), a grid of equal cells counts them evenly, whatever the shape of the
administrative areas:
1. find_algorithms "create grid", then run_algorithm native:creategrid with TYPE 4 (hexagon) or 2 (rectangle), the
   EXTENT of the points, HSPACING and VSPACING in the units of their CRS (metres: never degrees; suggest_crs first).
2. run_algorithm native:countpointsinpolygon with the grid as POLYGONS and the points as POINTS (a FIELD to sum a
   value, as WEIGHT).
3. set_layer_style graduated on NUMPOINTS, 5 to 7 classes, a sequential ramp; filter out the empty cells with
   apply_filter "NUMPOINTS" > 0 when they clutter the map.

## What never to do

- Never make a cartogram of a rate, a density or a percentage: only of counts and totals.
- Never compute the geometries with code: make_cartogram is undone with the turn, code is not.

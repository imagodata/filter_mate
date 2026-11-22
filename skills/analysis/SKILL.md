---
name: analysis
title: Analyse with Processing, fields and joins
description: new layers with Processing (buffer, clip, join by location...), computed fields, joined tables
metadata:
  version: 2
  plugin_min: 5.1.0
  audience: chat, mcp
  tools: find_algorithms, describe_algorithm, run_algorithm, add_field, join_layers, apply_filter, layer_statistics, describe_layer, export_layers
  risk: change
  trust: builtin
---

# Analysis

## Filter or make a layer?

To keep features of a layer, filter it (apply_filter and the other filters): filters change no data and need no new
layer. Make a layer only when the user asks for something new: a buffer zone, centroids, a dissolve, a clip, an
intersection, points to a heatmap, a slope. To answer "how many" or "how long", compute with layer_statistics.

## Processing

1. The algorithm: one of the list below by its id, or find_algorithms with English words (buffer, centroid,
   dissolve, clip, intersection, join attributes by location, heatmap, slope) for anything else.
2. describe_algorithm for its parameters: never guess a parameter name or a value.
3. run_algorithm with the layers by name or id and plain values; give names to the outputs the user will see.

The layers it makes are added to the project and undone with the turn. Each one is a temporary file, lost when QGIS
closes: when the user wants to keep one, export_layers writes it. Distances are in the units of the layer's CRS
(describe_layer says it): a geographic CRS counts in degrees, so reproject or say so.

## Which algorithm

These ids are the same in every QGIS FilterMate runs in: go straight to describe_algorithm. When one is refused or
missing in this QGIS, search with find_algorithms.

- A zone around features: native:buffer (DISSOLVE for one zone). Features merged, all or by a field:
  native:dissolve.
- A layer cut by another: native:clip keeps the inside, native:difference the outside, native:intersection the
  parts in common with the fields of both. An overlay that fails on invalid geometries: native:fixgeometries first.
- The fields of a layer on the features of another, by place: native:joinattributesbylocation; by the nearest
  feature, with its distance: native:joinbynearest.
- Counting in polygons: points with native:countpointsinpolygon, the length of lines with native:sumlinelengths.
- A raster under each polygon (the mean elevation of each commune): native:zonalstatisticsfb; the share of each
  class of a raster in each polygon: native:zonalhistogram; the value of a raster at each point:
  native:rastersampling.
- A raster as a whole: native:rasterlayerstatistics answers the minimum, maximum and mean of a band,
  native:rasterlayeruniquevaluesreport the count and surface of each of its values. They answer values, no layer.
- Terrain from an elevation raster: native:slope, native:aspect, native:hillshade. Classes from values:
  native:reclassifybytable.
- Points to a surface: qgis:heatmapkerneldensityestimation (a density), qgis:idwinterpolation and
  qgis:tininterpolation (a value carried by the points).
- Shapes: native:centroids, native:convexhull, native:boundingboxes, native:simplifygeometries,
  native:multiparttosingleparts.
- A layer in another CRS, as a new layer: native:reprojectlayer (to measure in metres from a layer in degrees).
- A grid of squares or hexagons over an area: native:creategrid, then native:countpointsinpolygon on it for a
  density map.
- Groups of points: native:dbscanclustering (by distance), native:kmeansclustering (a number of groups).
- Along a network of lines (roads): the shortest path between two points with native:shortestpathpointtopoint, what
  is reached within a distance or a time with native:serviceareafrompoint and native:serviceareafromlayer. They
  follow the lines as they are drawn: say that the result depends on roads that are connected.

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

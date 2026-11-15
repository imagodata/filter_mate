---
name: workflows
title: Chain the steps of a request
description: a request that needs several steps - what lies within a distance or inside an area, a place found then the data around it, a count by category, several criteria at once, a thematic map ready to print, data fetched then filtered - done with the fewest calls, in the right order
metadata:
  version: 1
  plugin_min: 5.1.0
  audience: chat, mcp
  tools: list_layers, describe_layer, field_values, layer_statistics, sample_features, map_context, preview_filter, apply_filter, cross_filter, geometry_filter, clear_filters, select_features, zoom_to, set_layers_visibility, export_layers, find_place, search_open_data, add_layer, add_service_layer, set_layer_style, set_labels, create_layout, export_layout, run_algorithm
  risk: change
  trust: builtin
---

# Workflows

A request of several steps is done in one turn, each step with the tool made for it. The chains below are the short
ones: take the one that fits, leave out the steps the project already answers.

## Fewer calls

- Read once. What list_layers, describe_layer or map_context answered in this conversation still holds, unless you
  or the user changed it: do not ask again.
- Readings that do not depend on each other go in the same turn (describe_layer of two layers, field_values of two
  fields).
- A filter, not a layer: a distance, an area or a relation between layers is a cross_filter or a geometry_filter,
  which make no new layer. run_algorithm is for what the user wants to keep as a layer (a buffer zone drawn on the
  map, a dissolve, a clip).
- One call for several layers: target_layers of cross_filter and geometry_filter, layers of clear_filters,
  set_layers_visibility and export_layers take a list.
- preview_filter is for an expression you wrote. A condition already tested in this conversation, or a spatial
  filter, needs no preview.
- Report once, at the end: what was kept on each layer, with the numbers the tools answered.

## What lies near, inside or along

"The buildings within 200 m of the rivers", "the parcels the road crosses", "the points inside the commune".

1. The source features: select_features on the source layer when the user means some of them (one river, the
   communes of a department); nothing to do when its filter already keeps them; selected_only false for every
   feature of an unfiltered source.
2. cross_filter with source_layer, target_layers, the predicate (Intersect for near or crossing, Are within for
   inside) and buffer for a distance, in metres. One call, no buffer layer.
3. Report kept for each target. A warning that nothing was kept points at the call: check the direction of the
   predicate and the source selection before saying "none".
4. Say the other warnings as they are: a WFS layer cut by the extent of the source (a rectangle: features beside
   the source stay; a smaller source or a selection gives the exact cut), a web map (WMS, WMTS, tiles) turned
   into a still image at one resolution, with holes when its service did not answer.

## Around a place

"Show the schools around Albi", "what is within 1 km of this address".

1. find_place with the name; when several places match, ask which one.
2. zoom_to with its extent_wkt and crs EPSG:4326.
3. geometry_filter with that extent_wkt and crs EPSG:4326 on the target layers, with buffer for a distance around
   it. A place that is a feature of a layer of the project (a commune, a district) is better taken there:
   select_features on that layer, then cross_filter.

## Several criteria

"The industrial buildings over 10 m, in the communes of more than 5 000 inhabitants, outside the flood zone."

1. The conditions on the layer's own fields first, in one apply_filter (one expression with AND).
2. Then each spatial condition, one cross_filter each, with operator AND so that it narrows what is left. Disjoint
   keeps what lies outside the source.
3. Never copy the current filter of a layer into a new expression: operator AND adds the new condition alone.

## How many, by what

"How many buildings per usage", "the total length of roads by nature", "which commune has the most".

One layer_statistics: group_by for the categories, field for a sum or a mean, measure for lengths and areas. It
counts the features the layer shows now, so filter first when the question is about a part of the layer. No new
layer, no field to add.

## A thematic map

"A map of the communes by population, with their names, to print."

1. The data on the map: filters, then zoom_to the layer.
2. set_layer_style on the field: categorized for a text or a code with few values, graduated for a number
   (quantile when a few values are far above the others, as populations and surfaces are), rules for thresholds the
   user gives. The cartography skill says more on methods, ramps and colors: load it when the choice is not plain.
3. set_labels when names are asked.
4. create_layout once the map looks right, with a title that says what the map shows. export_layout only when the
   user asks for a file.

## Data that is not in the project

"Add the cycle paths of Toulouse and keep those over 2 km."

1. search_open_data on an enabled platform (add_service_layer for a layer of a WFS, WMS or WMTS platform).
2. add_layer with a geojson or gpkg resource; the user confirms.
3. describe_layer on the new layer: its fields and values are not those you expect. Then filter it as any layer.

## Start again, or keep

- "Start again", "show everything": clear_filters on the layers you filtered, in one call.
- "Keep the result": export_layers writes the layers as filtered now, only when the user asks for files.

## What never to do

- Never make a layer with run_algorithm when a filter answers the request.
- Never repeat a step that failed with the same arguments: read what the tool answered and change the call.
- Never go on with the next steps of a chain when one was refused or declined: say where it stopped.

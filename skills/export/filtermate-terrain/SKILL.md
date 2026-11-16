---
name: filtermate-terrain
description: "Draw the relief through the MCP server of the FilterMate QGIS plugin: a relief map: elevation brought in, colors by height, shaded relief, contour lines, slopes. Use when the user asks for it in QGIS with FilterMate."
---

<!-- Generated from skills/terrain/SKILL.md by scripts/export_agent_skills.py: do not edit by hand. -->

Needs the MCP server of FilterMate: in QGIS, Agent settings (menu ⋯ of the AGENT panel), tab Other applications: turn it on and copy the configuration for this application. Its tools carry the names below.

# Terrain

A relief map is layers stacked, from the bottom up: a basemap, the elevation in colors, a shaded relief, the
contour lines. Each has its tool. Do the whole chain in one turn, in this order, then look at the result once.

## The chain

1. **Where.** find_place with the name of the place, then zoom_to with its extent_wkt and crs EPSG:4326. When
   several places match, ask which. A place the map already shows: map_context gives the view as extent_wkt. "The
   centre of a town" is the extent find_place answers, not its whole region: the smaller the area, the finer the
   relief reads.
2. **The background**, when one is asked: add_basemap (google_satellite or ign_ortho for photographs,
   carto_light_nolabels for a neutral one). It goes under every layer by itself.
3. **The elevation.** add_elevation with the same extent_wkt and crs. It answers the layer and its minimum, maximum
   and mean heights, in metres: keep them, they decide the contour interval and they are what the user is told. Leave
   resolution and target_crs out unless asked: 30 m, on a grid in metres.
4. **Colors by height.** set_layer_style on the elevation layer: mode pseudocolor, ramp Terrain, cut 2. The cut
   stretches the colors between the 2nd and the 98th percentile, so that a few extreme pixels do not flatten the
   others. Flat color bands instead of a continuous ramp: discrete true, with classes (8 reads well).
5. **The shaded relief.** duplicate_layer on the elevation layer (name it after what it is, such as Hillshade),
   then set_layer_style on the copy: mode hillshade, multidirectional true, blend multiply. One layer is drawn one
   way: the copy is what lets the same elevation show as colors and as a relief.
6. **The contours.** contour_lines on the elevation layer with interval, and index_interval for the index
   contours. Closed contours of a few pixels (the bumps of buildings, in a surface model) are left out, and
   counted in left_out. The layer comes on top, in thin brown lines with the index contours thicker: restyle it only when asked
   (set_layer_style, mode rules, a rule on "is_index" = 1 with its width, a rule with an empty expression for the
   others).
7. **Look.** With view_map when it is offered, once the stack is complete: does the basemap show through, does
   the relief read, are the contours lines and not a brown blur? Correct what reads wrong with set_layer_style in
   mode keep (opacity or blend alone), two corrections at most, then look again once.
8. **Answer** in a few sentences: what was added, the heights of the area, the number of contours and of index
   contours, where the elevation comes from.

## Choosing the values

When the user gives none, choose, and say what you chose.

- **Opacity.** Over a photograph (a satellite basemap): the colored elevation at 0.45 to 0.6, the hillshade at 0.2
  to 0.35, so that the photograph still reads. Over a neutral basemap or none: the elevation at 0.8 to 1, the
  hillshade at 0.4 to 0.5. "Subtle" is the low end, "strong" the high end.
- **The light** comes from the north-west, as on every relief map. multidirectional shows the slopes that face
  away from it. In flat country (less than 100 m between minimum and maximum) pass z_factor 2 or 3 to deepen the
  relief.
- **The contour interval**, from maximum minus minimum: under 100 m, every 5 (index 25); 100 to 400 m, every 10
  (index 50); 400 to 1500 m, every 25 (index 100); above, every 50 (index 250) or every 100 (index 500). An index
  contour is every fourth or fifth one, and index_interval is a multiple of interval.
- **The ramp.** Terrain (green low ground, brown heights, pale summits) for a relief map. Spectral with invert, or
  Viridis, when heights are a measure to read rather than a landscape. YlOrRd for a slope.
- **Labels on the contours**, when asked: set_labels on the contour layer with expression
  if("is_index" = 1, "elevation", ''), placement curved, size 7, and visible_from_scale 50000 on a large area. Only
  the index contours are labeled: a height on every line is unreadable.

## More than a relief map

- A slope or an aspect map: run_algorithm with native:slope or native:aspect on the elevation layer
  (describe_algorithm first), then set_layer_style on the result. The elevation of add_elevation is in metres on a
  grid in metres, so slopes are right as they come.
- Data by the slope, aspect or roughness of the ground ("the buildings on slopes over 15 %"): cross_filter with the
  elevation raster as source_layer and raster_selection {"mode": "range", "derivative": "slope_percent", "minimum":
  15}. derivative is slope_degrees, slope_percent, aspect, hillshade or roughness; the bounds are then in degrees,
  percent... of that quantity, read from the band as a DTM. No new layer is written.
- A hillshade as a raster file of its own: native:hillshade. Only when the user wants the file: to show a relief,
  the hillshade mode draws it without writing anything.
- The mean height of each polygon of a layer, the height at each point: the analysis skill (zonal statistics,
  raster sampling).
- A print of the map: the cartography skill (a print layout, once the map looks right).

## What to tell the user

- Copernicus DEM is a surface model at 30 m: buildings and trees are in it, so a dense town or a forest stands a
  few metres above its ground, and nothing smaller than 30 m shows. Good for a map and for a first reading of the
  relief, not for a building site.
- The elevation is a file kept in the QGIS profile; the contours are a temporary layer: export_layers keeps them
  when the user asks.
- Undoing the turn removes every layer of the chain.

## What never to do

- Never bring the elevation in again when the project already holds an elevation raster over the area
  (list_layers, describe_layer): style that one, and draw the contours from it.
- Never write an address. When add_elevation or add_basemap is not offered, its source is not ticked: say that it
  can be ticked in the settings of the agent, Sources tab (Copernicus DEM under Satellite imagery, the basemaps
  under Basemaps), and stop there.
- Never ask for a whole region when a town is asked, nor for a finer resolution than the 30 m of the source.
- Never change the CRS of the project for a relief map: the layers are reprojected on the fly.
- Never go on with the next steps of the chain when one was refused or declined: say where it stopped.

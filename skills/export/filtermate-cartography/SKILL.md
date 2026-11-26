---
name: filtermate-cartography
description: "Make the map look right through the MCP server of the FilterMate QGIS plugin: styles, labels, a simple print layout, the map CRS, the layer tree, map themes, bookmarks. Use when the user asks for it in QGIS with FilterMate."
---

<!-- Generated from skills/cartography/SKILL.md by scripts/export_agent_skills.py: do not edit by hand. -->

Needs the MCP server of FilterMate: in QGIS, Agent settings (menu ⋯ of the AGENT panel), tab Other applications: turn it on and copy the configuration for this application. Its tools carry the names below.

# Cartography

Styles and layouts change how the project shows, never its data, and are undone with the turn. The view tools
below only change what the window shows and are not undone.

## Styles

- set_layer_style draws a layer anew; every mode replaces its style. To change the opacity or the blending alone,
  use the mode keep: the categories of a layer and the colors of an orthophoto stay. It is the only mode of a WMS,
  WMTS or basemap image. blend multiply darkens (colors over a photograph), normal covers.
- width is in millimetres: a line, an outline, the size of a point; each rule takes its own (the main roads
  thicker). For the modes below it is the radius of a heatmap, the distance under which points gather, the largest
  proportional symbol, the size of a dot.
- A raster with values takes pseudocolor (cut 2 leaves the extreme values out; discrete for flat steps), gray, or
  hillshade. A relief map with contours is the terrain skill: load it.
- One layer is drawn one way. duplicate_layer adds a second layer on the same data, just above, for what needs two:
  a road with a wider line under it, an elevation as colors and as a relief.
- After a style the user will judge by eye, look with view_map when it is offered.

## Official styles

- A layer of the BD TOPO of IGN (batiment, troncon_de_route, commune...) or of OpenStreetMap (a column highway,
  building, landuse...) can be drawn as its producer draws it. When the user asks for that, or for a map that looks official: call
  list_style_presets with the layer first; it lists the presets whose table fits it (by its name or its fields).
- apply_style_preset with one of them: rules, symbols, labels and scale ranges of the producer. It is refused when
  the layer lacks a field the style reads: say which, never imitate it with set_layer_style.
- variant gris for a discreet background under other data, sombre over a dark basemap.
- The producer draws a class only from a scale (drawn_from): nothing shows further out. Say so; all_scales draws it
  at every scale. Credit the attribution on a layout.

## Which map for which data

When the user names no mode, choose from the data (describe_layer for the fields and the geometry, field_values for a
text, layer_statistics for a number), and say in one sentence what you chose and why.

- A text or a code with few values (a nature, a usage): categorized. Up to about 12 values the colors can be told
  apart; above, group them with rules or filter first (above 100 the mode is refused).
- Thresholds that mean something (over 10 000 inhabitants): rules, one color per condition, a last rule with an
  empty expression for the others.
- A count or an amount (inhabitants, jobs, accidents, tonnes) over areas of different sizes: proportional (a circle
  in each polygon, its area in proportion to the value), never graduated colors: a large commune would look
  important only for its size. Colors are for rates, shares and densities (per km², per 1,000 inhabitants, %): with
  graduated. When the user asks for colors of a count, do it, and say in one sentence that circles or a density read
  better.
- A count over polygons, to show where it is spread: dot_density (one dot for per_dot units of the field; by default
  a round share that puts about 100 dots in the largest).
- Many points (thousands of accidents, trees, shops): heatmap, weighed by a field when each point counts for more
  than one (field). Points close together that hide each other: point_cluster (one disc with their number) or
  point_displacement (spread around their place, for a few at the same address). Both keep the categories the
  layer had for the points left apart: style categorized first, then cluster.
- Polygons with a height (buildings): 2.5d with the height field, z_factor to stretch it on a small scale map.
- Lines with an amount (traffic, flows): proportional widths.
- No field at all: single, with the color asked.

## Classes and colors

1. Graduated classes: five read well, three to seven is the range, twelve at most. Read the field with
   layer_statistics first:
   - a few very large values (the mean well under the middle of minimum and maximum): quantile, or jenks for natural
     groups; equal_interval would put nearly everything in the first class.
   - values spread evenly: equal_interval, or pretty for round limits in the legend.
   - a value with a meaningful middle (a change, a balance, a gap from the average): give center (0 for a change,
     the mean or a reference value), with a diverging ramp. The middle color falls on center, the classes on each
     side darken as they go away; equal_interval, pretty or stddev put a limit exactly at center.
2. The ramp says what the values mean:
   - more of something, light to dark: Blues, Greens, Reds, YlOrRd, Viridis (read by color-blind people and in grey).
   - two directions around a middle: RdBu, RdYlGn, BrBG, PiYG, always with center. RdYlGn puts red on the low
     values: pass invert when high is bad.
   - categories: Spectral by default; give the colors yourself with rules when they have a meaning.
   - a heatmap: YlOrRd by default, Magma or Inferno on a dark basemap; its lowest values are left transparent.
   - an elevation raster: pseudocolor with Terrain, Spectral inverted or Viridis.
3. Colors people expect: water blue, vegetation green, built-up grey or red, a risk in red, what is allowed in green.
   A color is a name (red, steelblue) or #rrggbb.
4. A neutral basemap without labels under a colored layer; an opacity of 0.6 to 0.8 on filled polygons that hide
   the background.

## Labels that stay readable

- set_labels writes a field, or an expression that joins values ("nom" || ' (' || "population" || ')'), and turns
  the labels off. Labels on a few hundred features at most, or from a scale on a larger layer: visible_from_scale
  50000 shows them from 1:50 000 and closer; visible_to_scale hides them closer than a scale.
- The halo (buffer, on by default) reads on any background. On a photograph or a busy map, a background box
  (white, background_opacity 0.8) with buffer false reads better.
- placement: lines curved (rivers, contours) or parallel; polygons centroid, horizontal, free (anywhere inside),
  around or perimeter; points around. callouts draws a line to a label moved away from its feature.
- Long names: wrap at 12 to 20 characters per line. priority 8 to 10 for the labels that must show (towns), lower
  for the others; obstacle false on a layer that other labels may cover (a background of polygons).
- font names an installed family; bold for the main names, italic for water by custom.

## A background under the map

add_basemap puts a web basemap the user enabled under every layer: carto_light for a neutral background,
carto_light_nolabels under layers that have their own labels, osm_tiles for a street map, google_satellite for
photographs anywhere, ign_plan or ign_ortho in France. When none is enabled, say that one can be ticked in the
settings of the agent, Sources tab.

## Showing the user

While the user watches, point at what you mean instead of only telling it. In the chat, flash_features flashes the
features an expression keeps (selecting nothing), set_active_layer makes a layer active and shows it unfolded in the
tree, and show_message tells something in the bar of QGIS (never a question: ask_user asks it instead).
These three tools require a QGIS window and belong to the built-in chat only; external MCP clients do not expose
them. Use them only when they are offered in this conversation.

## Layouts

1. Set the map first: filters, style, zoom_to.
2. create_layout makes a print layout of the map (title, legend, scale bar, north arrow), A4 by default.
3. export_layout writes it (PDF, PNG, JPG, SVG or TIFF) only when the user asks; they confirm the file.
   map_context lists the layouts. In the chat, an atlas, a chart on the page or an existing layout to read: load
   the skill layouts.

## The CRS of the map

set_project_crs sets the CRS of the project, which the map shows: what a user calls the CRS of the view or of the
map. EPSG:2154 is Lambert-93 for France. It changes no data: never reproject layers into new files for that.

## The layer tree, themes and bookmarks

- group_layers puts layers in a group (made where missing, Base/Roads for a group in a group) or, with above, just
  above another layer; rename_layer renames a layer, or a group with group true.
- map_theme lists, saves (the layers shown now and their styles), applies or removes a map theme: a saved view of
  layers and styles.
- bookmark lists, adds (the visible map), zooms to or removes a spatial bookmark: a named place.
- "Keep this view as X": a theme keeps layers and styles, a bookmark keeps a place; when the words leave it open,
  say which you made.

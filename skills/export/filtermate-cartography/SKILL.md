---
name: filtermate-cartography
description: "Make the map look right through the MCP server of the FilterMate QGIS plugin: styles and labels, print layouts and their export, the CRS of the map, the layer tree, map themes and spatial bookmarks. Use when the user asks for it in QGIS with FilterMate."
---

<!-- Generated from skills/cartography/SKILL.md by scripts/export_agent_skills.py: do not edit by hand. -->

Needs the MCP server of FilterMate: in QGIS, Agent settings (menu ⋯ of the AGENT panel), tab Other applications: turn it on and copy the configuration for this application. Its tools carry the names below.

# Cartography

All of this changes how the project shows, never its data, and is undone with the turn.

## Styles and labels

- set_layer_style draws a layer anew: one color, a color per value, graduated classes (five by default), a raster
  color ramp, or rules: a color per condition ("population" > 10000 in red, the others in grey with a rule whose
  expression is empty), for what a single field does not say. set_labels writes a field on the map, or an expression
  that joins or formats values ("nom" || ' (' || "population" || ')'), and turns the labels off. With
  visible_from_scale the labels only show once the map is close enough (50000: from 1:50 000).
- Every mode replaces the style of the layer. To change its opacity alone, use the mode keep with opacity: the
  categories of a layer and the colors of an orthophoto stay. It is the only mode of a WMS, WMTS or basemap image.
- A single symbol and each rule take a width in millimetres (a line, an outline, the size of a point): the main
  roads thicker than the others is rules with a width each. blend says how a layer mixes with what is under it:
  multiply darkens (colors over a photograph), normal covers; it goes with any mode, keep included.
- A raster with values takes pseudocolor (a ramp; cut 2 leaves the extreme values out of it; discrete for flat
  steps), gray, or hillshade (a shaded relief drawn from elevations). A relief map, with its contours, is the
  terrain skill: load it.
- Labels of a layer of lines follow them with placement curved (rivers, roads).
- One layer is drawn one way. duplicate_layer adds a second layer on the same data, just above the first, for
  what needs two: a road with a wider line under it, an elevation as colors and as a relief.
- After a style the user will judge by eye, look with view_map when it is offered.

## Choosing a style

When the user names no mode, ramp or number of classes, choose from the data, and say in one sentence what you chose.

1. What the field holds (describe_layer for its type, field_values for a text field):
   - a text or a code with few values (a nature, a usage, a class): categorized. Above about 12 values the colors
     can no longer be told apart, and above 100 the mode is refused: group them with rules, or filter first.
   - a number that measures (a population, a surface, a height, a rate): graduated.
   - thresholds the user gives, or that have a meaning (over 10 000 inhabitants, under 5 % of slope): rules, one
     color per condition, a last rule with an empty expression for the others.
   - no field at all (the layer as a whole): single, with the color asked.
2. For graduated, read the field with layer_statistics before choosing the method:
   - the mean well under the middle of minimum and maximum (a few very large values: populations, surfaces):
     quantile, or jenks when the user wants natural groups; equal_interval would put nearly everything in the first
     class.
   - values spread evenly: equal_interval, or pretty for round limits in the legend.
   - a value compared with the average: stddev, with a diverging ramp.
   - five classes read well; three to seven is the range. More only when asked.
3. The ramp says what the values mean:
   - more of something, from light to dark: Blues, Greens, Reds, YlOrRd, Viridis (read by color-blind people, and
     in grey when printed).
   - two directions around a middle (a change, a gap from the average, a balance): RdBu, RdYlGn, BrBG, with stddev
     or with rules around the middle. RdYlGn puts red on the low values: pass invert when high is bad.
   - categories: Spectral by default. Give the colors yourself with rules when they have a meaning.
   - an elevation raster: pseudocolor with Terrain (the tints of a relief map), Spectral inverted or Viridis; a
     slope or a density with YlOrRd.
4. Colors people expect: water blue, vegetation green, built-up areas grey or red, a risk or an alert in red, what
   is allowed in green. The color of a single symbol is a name (red, steelblue) or #rrggbb.
5. Make it readable: a neutral basemap without labels under a colored layer; an opacity under 1 (0.6 to 0.8) on
   filled polygons that hide the background; labels only on a layer of a few hundred features, or from a scale
   (visible_from_scale) on a larger one.

## A background under the map

add_basemap puts a web basemap the user enabled under every layer: carto_light for a neutral background,
carto_light_nolabels under layers that have their own labels, osm_tiles for a street map, google_satellite for
photographs anywhere, ign_plan or ign_ortho in France. When none is enabled, say that one can be ticked in the
settings of the agent, Sources tab.

## Layouts

1. Set the map first: filters, style, zoom_to.
2. create_layout makes a print layout of the map (title, legend, scale bar, north arrow) added to the project, in
   the page size asked (A4 by default).
3. export_layout writes one as PDF or PNG in the export folder, only when the user asks; they confirm the file.
   map_context lists the layouts of the project.

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

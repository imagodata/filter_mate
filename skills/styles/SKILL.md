---
name: styles
title: Design a modern style
description: finished styles from validated palettes, looks, SVG icons and variants
metadata:
  version: 1
  plugin_min: 5.1.2
  audience: chat, mcp
  tools: design_style, list_palettes, describe_layer, field_values, layer_statistics, set_labels, set_layer_style, map_context
  risk: change
  trust: builtin
---

# Design a modern style

design_style composes a finished style: the colours of a palette chosen by the job they do and checked for the
readers who see colours differently, one symbol or categories or classes, a look made for the geometry, SVG icons in
the colour of their category, and a variant for the map the layer goes on. Prefer it to set_layer_style when the user
wants a map that looks right; set_layer_style stays for what design_style does not draw (heatmaps, proportional
symbols, rules, rasters).

## Method

1. describe_layer: the geometry and the fields; field_values for a field of categories (how many values).
2. The job of the colour decides the mode and the palette:
   - identity (a type, a nature, an owner): mode categorized, a categorical palette (filtermate by default,
     okabe_ito for the best separation for every reader); limit 8 categories at most, the rest in one grey;
   - magnitude (a count per area, a rate, a height): mode graduated, a sequential palette (blues by default,
     viridis or cividis, ylorrd for heat), 5 classes (3 to 7), method quantile, or jenks for clustered values;
   - a gap from a centre (a change, an anomaly, above or below a mean): mode graduated with a diverging palette
     (rdbu, puor, brbg, piyg), reverse when red must mean the other side;
   - one layer of context: mode single (color for a given colour).
3. The look, by geometry:
   - polygons: flat for a full coverage, outlined for areas that sit on a basemap, hatched for a second layer over
     another one or a zone to highlight;
   - lines: casing for roads and networks (the casing of every line under every line: crossings join), halo over a
     busy basemap, dashed for a limit or a planned line, flat otherwise;
   - points: flat (dots with a ring), icon (an SVG of QGIS named by a word: school, hospital, library, bus,
     parking... in the colour of each category), badge (the icon on a dot of the colour, readable on any background).
4. The variant: light by default; dark over a dark basemap (dark colours of the palette, ramps turned over);
   print for paper (no step too pale); discreet for a background layer under a thematic one.
5. Read problems in the answer: two colours some readers cannot tell apart, a colour lost on the background. Change
   the palette (okabe_ito), the number of categories or the variant, or say it when the user keeps the choice.
   A note says when thin lines were darkened in their own hue to stand out.
6. Labels after: set_labels with a buffer, the names in the user's words.
7. list_palettes shows the palettes by role, with their source and licence; cite ColorBrewer when its palette is used
   (the answer carries the credit).

## What never to do

- Never colour counts with a sequential palette on polygons of unequal areas without saying a rate would be truer.
- Never use a categorical palette for classes, nor a rainbow, nor red and green alone to tell two things apart.
- Never stack more than one style tool for one request: design_style replaces the style.

---
name: panels
title: Set up the panels of FilterMate
description: FilterMate's panels: the fields EXPLORING shows, its filtering options, the export options
metadata:
  version: 1
  plugin_min: 5.1.0
  audience: chat, mcp
  tools: layer_options, set_layer_options, export_options, set_export_options, list_layers, describe_layer, field_values, export_layers, ask_user
  risk: change
  trust: builtin
---

# Set up the panels of FilterMate

FilterMate's panel keeps, for each vector layer, what EXPLORING shows (a field or an expression for the single,
multiple and custom selection) and its FILTERING options; and, for the project, the EXPORTING options. The user works
in the panel with them. layer_options and export_options read them; set_layer_options and set_export_options set
them, all or none, as the user would in the panel, undone with the turn. They need the panel open.

## Fields of EXPLORING

1. Read the layer with describe_layer, and its values with field_values when the user shares them; without values,
   start from the names of the fields and the display expression of QGIS.
2. Single selection: the most readable field, unique when possible (a name, a label). Never a technical id (fid,
   uuid, a numeric key) when a name exists. The panel keeps a field here, not an expression.
3. Multiple selection: a field too, short, that sorts and has few values (a status, a type, a zone), so that ticking
   several makes sense. Custom selection: any expression, such as a label made of two fields,
   `"nom" || ' (' || "code_insee" || ')'`.
4. The fields that link the layers (a zone id present in most layers) come first: they filter the whole network on
   one zone.
5. A real choice between two labels: in the chat, ask with ask_user. For the whole project: one set_layer_options
   call with every layer, never one question or one call per layer. Say what each layer now shows.

## Filtering options of a layer

layers_to_filter, geometric_predicates, the combine operators, buffer_value and buffer_type are what the FILTERING
panel uses when the user clicks Filter on that layer. Set them when the user asks to prepare a filter for later; to
filter now, use the filtering tools instead.

## Export options

Prepare the EXPORTING panel (layers, format, CRS, styles, folder, zip) when the user wants to export from it
themselves. When they ask for the export itself, export_layers does it: do not only prepare the panel.

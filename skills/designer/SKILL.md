---
name: designer
title: Coordinate styles, themes and print layouts
description: design styles, QGIS map themes and print layouts together
metadata:
  version: 1
  plugin_min: 5.1.3
  audience: chat
  tools: describe_layer, list_layers, map_context, qgis_capabilities, control_qgis, list_palettes, list_style_presets, design_style, apply_style_preset, set_layer_style, set_labels, map_theme, set_layers_visibility, group_layers, create_layout, describe_layout, edit_layout, set_atlas, open_layout, preview_atlas, export_layout, view_map, ask_user, show_settings_link
  requires: describe_layer, qgis_capabilities
  risk: change
  trust: builtin
---

# Advanced Designer workspace

Coordinate the map's visual hierarchy, labels, QGIS map themes and print layouts. The workspace is an independent
chat preference, not an authorization mode: Respond, Propose and Act and existing sharing/tool restrictions still
apply. Use only the tools offered. Never enable an expert mode or run arbitrary Python to extend these controls.

## Inspect and refine

Use supplied context first. When inventory is missing, qgis_capabilities.project_assets lists bounded map theme
and print layout names without changing the project. If available is false or truncation is reported, state the
limit; do not claim the inventory is complete or use truncated names as identifiers. Describe only relevant layers
and existing layouts. Load brainstorm
when offered for an open design question: compare two or three directions and refine with the user. A request for
proposals does not authorize applying a style, saving a theme, creating a layout or exporting a file.

## Styles and labels

Check geometry and available fields with describe_layer before proposing a renderer or labels. Use list_palettes
and existing presets when appropriate; distinguish a tested preset from a suggested design. Define hierarchy,
meaningful colors, symbol size, contrast, scale ranges and readable labels. Load styles or cartography when offered
for the detailed tools. design_style changes the project; it is not a read-only preview of a proposal. Use view_map
after an authorized change when offered, and report what was actually observed, not an imagined visual result.

For a setting not exposed by these tools, offer native layer styling: control_qgis with action properties, layer
and page style. The native modal editor opens after the request finishes successfully. The user edits
it manually; do not claim the agent can drive arbitrary controls or has applied the proposed settings.

## QGIS map themes

Themes are named map views of layer visibility and named layer style references. They are distinct from the light
or dark interface theme. They do not keep an independent frozen renderer: changing the same named style later can
change the appearance of several themes. For independent variants, explain that separate named layer styles must
first be prepared in native QGIS style management. The current tools do not create those named styles.

Read names through qgis_capabilities before using map_theme, whose list/save/apply/remove operations follow the
normal tool policy. Never invent rename or duplicate operations. Saving an existing name replaces that theme;
ask before replacing when the user's request did not specify replacement. Applying or removing a theme also
requires a request to do so. Preserve unrelated themes, groups and layer visibility. When asked to save the current
view, use that view; do not restyle or change the extent as an extra step.

## Print composer and atlas

Agree on audience, page format/orientation, extent, map scale, legend, typography and output only where missing.
Use create_layout for a requested new layout. For an existing layout, call describe_layout first and use returned
item IDs with edit_layout; do not invent them or recreate the entire layout to change a title. Binding a layout
map to a named theme is currently a manual operation in the native composer, not an edit_layout option.
Load layouts for atlas and detailed item controls when offered. Use open_layout to hand off to the native QGIS
composer and preview_atlas for a requested atlas preview. Neither means that a PDF has been exported.

Export only on request through export_layout and the user-selected export folder. Do not write into QGIS profiles
or change export preferences as part of a design proposal. After authorized work, state the exact changed assets,
what was verified and any remaining manual work. Do not imply a native editor change is covered by chat undo.

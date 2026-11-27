---
name: qgis-interface
title: Use the QGIS window
description: open native tables and layer properties, reveal existing QGIS or plugin panels, choose map tools and navigate views
metadata:
  version: 1
  plugin_min: 5.1.3
  audience: chat
  tools: qgis_capabilities, control_qgis, list_layers, describe_layer, map_context, find_algorithms, describe_algorithm, run_algorithm
  requires: qgis_capabilities, control_qgis
  risk: change
  trust: builtin
---

# Use the QGIS window

Inspect qgis_capabilities before choosing a registered panel or map tool. Use the exact panel id from this session;
titles may be translated or duplicated, and unloading a plugin removes its panel. An unavailable or ambiguous id
requires rediscovery, not a guessed action name.

control_qgis supports:

- attributes: a vector layer's native table. An optional QGIS expression filters that table only; it does not change
  the layer's filter or selection. Read describe_layer for actual field names before supplying an expression.
- properties: the native properties dialog, optionally on information, source, style or metadata. A scheduled
  result means it opens after this response finishes successfully and its changes are recorded. Finish the response
  to hand off to the user; queued follow-ups wait for the dialog to close. Do not fill fields or claim a change was applied.
- show_panel and hide_panel: an existing registered dock, including plugin docks. Opening a panel does not execute
  its treatment or prove that its services and models are configured.
- map_tool: pan, zoom_in, zoom_out or identify. Selecting a tool prepares the user's interaction; it does not click
  the map or modify data.
- previous_view and next_view: QGIS navigation history, leaving layer data and selections as they are.

For a plugin treatment, discover its registered Processing algorithm with find_algorithms and describe_algorithm,
then run_algorithm only when the request authorizes execution. A panel without a Processing algorithm or a
supported adapter is a manual interface. Say what is available.
Never use arbitrary Python or QAction names to get around an unavailable capability or a refusal.

An unavailable window is normal in a headless session. A requested result confirms an interface invocation, not
that the user completed a form, saved a style or ran a plugin. Describe the actual result and handoff.

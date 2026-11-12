---
name: filtermate-editing
description: Edit the data of a layer through the MCP server of the FilterMate QGIS plugin: change, delete or add features of a vector layer, in its edit buffer, when the user asks to change the data itself. Use when the user asks for it in QGIS with FilterMate.
---

<!-- Generated from skills/editing/SKILL.md by scripts/export_agent_skills.py: do not edit by hand. -->

Needs the MCP server of FilterMate: in QGIS, Agent settings (menu ⋯ of the AGENT panel), tab Other applications: turn it on and copy the configuration for this application. Its tools carry the names below.

# Editing data

## Edit or filter?

Only edit data when the user asks to change, delete or add features. To show fewer features ("hide", "keep only",
"remove from the map"), filter instead (apply_filter): a filter changes no data.

## Method

1. Find the features with an expression tested first: preview_filter says how many it keeps; field_values gives the
   exact values. For specific features the user points at, select them (select_features) and use selected_only.
2. update_features changes attribute values, delete_features deletes features, add_features adds features from WKT
   and attributes. Each works in the edit buffer of the layer: nothing is saved.
3. Say what changed and how many features, and that the changes are not saved: the user reviews and saves the layer
   edits. Undoing the turn takes the changes out of the buffer.

## What never to do

- Never delete or change features to answer a request to hide or filter them.
- Never save the edits of a layer (only the user does).
- Never edit a layer the user protected.

---
name: editing
title: Edit the data of a layer
description: change, delete or add features of a vector layer, in its edit buffer, when the user asks to change the data itself
metadata:
  version: 1
  plugin_min: 5.1.0
  audience: chat, mcp
  tools: update_features, delete_features, add_features, select_features, preview_filter, field_values, apply_filter
  risk: change
  trust: builtin
---

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

---
name: filtermate-raster-objects
description: Objects on a raster and SAM through the MCP server of the FilterMate QGIS plugin: filter with the objects the user drew on a raster in the dock, draw objects with SAM from guide features, find objects that look like an example. Use when the user asks for it in QGIS with FilterMate.
---

<!-- Generated from skills/raster-objects/SKILL.md by scripts/export_agent_skills.py: do not edit by hand. -->

Needs the MCP server of FilterMate: in QGIS, Agent settings (menu ⋯ of the AGENT panel), tab Other applications: turn it on and copy the configuration for this application. Its tools carry the names below.

# Objects on a raster

## Objects drawn in the dock

map_context lists drawn_objects: the rasters on which the user drew objects in the dock. To filter with them ("the
buildings under what I drew"), call cross_filter with that raster as source_layer and raster_selection
{"dock_objects": true}. When no raster has drawn objects, say so: the user draws them in the dock first.

## SAM

- segment_objects draws with SAM, on a raster, the object each feature of a guide layer points at (points, or
  polygons such as building footprints) and adds them as a new layer with sam_score and sam_iou. Select the guide
  features meant first (select_features). A low sam_iou points at a footprint to look at; it does not prove a change.
- similar_objects finds the objects that look like an example (one selected feature of a layer, or with
  use_dock_object the last object drawn in the dock) in an area. About half of what it finds is right and it misses
  most: tell the user to check the layer, never present it as a count.
- When SAM is not installed, tell the user to install it from the PIPETTE group of the dock.

## What never to do

- Never present what SAM found as a complete or exact count.
- Never filter with drawn objects that are not there: check drawn_objects first.

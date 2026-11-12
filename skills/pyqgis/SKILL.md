---
name: pyqgis
title: Write PyQGIS for the expert mode
description: write the Python code of run_pyqgis (expert mode) for what no tool does, in a way that works from QGIS 3.22 to 4.x and keeps QGIS responsive
metadata:
  version: 1
  plugin_min: 5.1.0
  audience: chat
  tools: run_pyqgis, apply_filter, list_layers, describe_layer, map_context, zoom_to, set_layers_visibility, group_layers, set_layer_style, create_widget, change_settings
  risk: change
  trust: builtin
  requires: run_pyqgis
---

# PyQGIS in the expert mode

run_pyqgis runs your code in the QGIS of the user, with their rights. They read all of it and say yes at every run,
and it is NOT undone with the turn. Use it last.

## Before writing code

1. A tool first: zoom_to, set_layers_visibility, group_layers, set_layer_style and the other tools are undone with
   the turn and checked; code is not. Write code only for what no tool does (a map scale, a canvas setting, a layout
   detail, a computation no tool gives).
2. Read the project with the tools (list_layers, describe_layer, map_context): never guess a layer id, a field or a
   CRS in code.
3. Say in purpose, in one sentence of the user's language, what the code does and what it changes.

## What never to do in code

- Never change a layer the user protected (listed with each request), the settings of the agent, nor the settings of
  FilterMate (change_settings does that, shown to the user). Never use code to get around a refusal or a question.
- No network, no files outside what the user asked for, no subprocess, no package installed, nothing read from the
  authentication database or the keys.
- No modal dialog, no new dock or window: for a control the user keeps, use create_widget.
- Do not save layer edits (commitChanges) unless the user asked to save: leave changes in the edit buffer.
- No endless loop, no sleep: the code runs on the main thread and QGIS is frozen meanwhile.

## The environment

- iface and project (QgsProject.instance()) are defined; import the rest (`from qgis.core import ...`,
  `from qgis.PyQt.QtCore import ...`). Assign `result` to return a value; print() output comes back too; an error
  comes back as a traceback: read it, fix once, do not loop.
- Find a layer by its id from list_layers: `layer = project.mapLayer(layer_id)`; by name only when unique:
  `project.mapLayersByName(name)`.

## Versions: QGIS 3.22 to 4.x, Qt5 and Qt6

- Version: `Qgis.QGIS_VERSION_INT` (e.g. 33400 for 3.34); Qt: `from qgis.PyQt.QtCore import QT_VERSION_STR`.
- Write Qt enums in full, as Qt6 requires and Qt5 accepts: `Qt.AlignmentFlag.AlignLeft`,
  `Qt.ItemDataRole.DisplayRole`, `Qgis.MessageLevel.Info`.
- Field types: `QMetaType.Type.Int` from QGIS 3.38, `QVariant.Int` before; test the version and pick one.
- Many enums moved into `Qgis` over the 3.x series (geometry types among them from 3.30): compare with the value
  the layer gives (`layer.geometryType()`) rather than writing a name that one version lacks, or test the version.

## Working with data

- Iterate with a request that asks little: `QgsFeatureRequest().setFilterExpression(...)`, `.setLimit(n)`,
  `.setSubsetOfAttributes([...], layer.fields())`. Never loop over a whole large layer without a limit.
- Edit in the buffer: `layer.startEditing()`, then `layer.changeAttributeValue(...)`; say the user saves the edits.
- A filter is set by the tools (apply_filter and the others keep the history of FilterMate); do not call
  setSubsetString in code.

## The interface

- Messages: `iface.messageBar().pushMessage("FilterMate", text, level=Qgis.MessageLevel.Info, duration=5)`.
- The map: `canvas = iface.mapCanvas()`; `canvas.zoomScale(5000)` for a scale, `canvas.refresh()` after a change.
- The layer tree: `project.layerTreeRoot().findLayer(layer_id)`; for visibility and groups, prefer the tools.
- Layouts: `project.layoutManager().layoutByName(name)`; create and export them with the layout tools.

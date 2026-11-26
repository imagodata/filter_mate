---
name: processing-models
title: Processing models and designer
description: reusable Processing chains and their QGIS editor
metadata:
  version: 3
  plugin_min: 5.1.3
  audience: chat
  tools: open_model, find_algorithms, describe_algorithm, run_algorithm, describe_layer
  risk: change
  trust: builtin
  requires: open_model
---

# Processing models

## Open, inspect and run

- open_model with no arguments opens a blank QGIS graphical model designer.
- find_algorithms with query model finds registered models, including project and installed provider models.
  Search a provider name (GDAL, GRASS, SAGA, PDAL) and task words for its algorithms.
- describe_algorithm gives the real parameter names, provider, model steps and requires_disk. Never invent ids,
  parameter names or output names. Missing providers and unsupported steps are not executable through the agent.
- open_model with algorithm_id opens a copy in the native editor. Opening it neither runs its steps nor changes
  the original file. Save asks for a location; Save in project embeds it in the current project.
- run_algorithm runs a registered model like an ordinary algorithm. Inputs are project layers by name or id,
  and plain values. Outputs are added to the project and undone with the turn.
- Native outputs and intermediate layers stay in memory. A file-only provider (also inside a model) requires the
  user to choose Save project and layers in the agent menu first. Its outputs and working files then use that
  chosen data folder; never choose a profile or operating-system temporary folder for the user.

## Build a reusable chain

Build only when the user asks for a model, or accepts an offer to keep a working chain. A request to open the
editor alone needs no definition. Creating a draft executes nothing and writes no file. Expert mode is not needed.

1. Keep the working Processing steps of the conversation; exclude exploratory or failed calls. Ask which chain
   when several are possible. Filters and styles outside Processing stay outside the model: say so when relevant.
2. describe_algorithm for any step whose inputs or outputs are unclear.
3. open_model with definition containing name, optional group, inputs, steps and outputs.
4. The user reviews the graph in QGIS and saves it to a chosen .model3 location or in the project. Do not report a
   saved model before that user action. File saves appear as clickable outputs in the chat; saved models are
   available through find_algorithms for the project session. Running it needs its own user request.

Definition format (no source code or file paths):

```json
{
  "name": "buffer_centroids",
  "inputs": [
    {"name": "INPUT", "step": "buffer", "parameter": "INPUT", "description": "Input features"},
    {"name": "DISTANCE", "step": "buffer", "parameter": "DISTANCE", "default": 500}
  ],
  "steps": [
    {"id": "buffer", "algorithm_id": "native:buffer", "parameters": {
      "INPUT": {"input": "INPUT"}, "DISTANCE": {"input": "DISTANCE"}, "SEGMENTS": 5
    }},
    {"id": "centroids", "algorithm_id": "native:centroids", "parameters": {
      "INPUT": {"step": "buffer", "output": "OUTPUT"}, "ALL_PARTS": false
    }}
  ],
  "outputs": [
    {"name": "RESULT", "step": "centroids", "output": "OUTPUT", "description": "Centroids of buffers"}
  ]
}
```

- Each model input clones its referenced step parameter, preserving its type and options. Choose layers when
  running: no layer ids or paths as defaults. Numeric, field and option inputs may have checked defaults.
- A step parameter is a plain value, {"input": "NAME"}, or {"step": "earlier_id", "output": "OUTPUT_NAME"}.
  Layers must be connected; never embed a session layer id. An input can feed several compatible steps.
- Names start with a letter and contain only letters, digits or underscores. Step ids and output names are unique.
- Destinations belong in outputs, never in step parameters. QGIS derives the runnable model output names:
  describe_algorithm after saving gives the actual names.
- Up to 30 steps, 60 inputs and 30 outputs. Unsupported parameters, extra command-line options, SQL, recursive
  dependencies and missing algorithms are refused. Never bypass a refusal with code.

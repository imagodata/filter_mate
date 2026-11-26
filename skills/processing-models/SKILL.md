---
name: processing-models
title: Save a workflow as a Processing model
description: Keep, reuse or share a chain of Processing treatments run in this session as a .model3 model
metadata:
  version: 2
  plugin_min: 5.1.2
  audience: chat
  tools: list_layers, describe_layer, find_algorithms, describe_algorithm, run_algorithm
  risk: change
  trust: builtin
  requires: run_pyqgis
---

# Processing models

## Propose it as an option

This skill is offered only in the built-in chat with expert mode enabled (run_pyqgis available). It has no MCP
export: external clients cannot call run_pyqgis. When it is unavailable, explain that the user enables expert mode
in the agent settings; never offer to bypass the restriction.

After a chain of two or more run_algorithm steps that works, or when the user says keep, reuse, share, automate
or replay: propose once, in one sentence, to save the chain as a reusable Processing model. Build it only on an
explicit yes. Never build it unasked, and never propose it twice for the same chain.

## Collect the chain

1. Read the run_algorithm calls of this conversation: each algorithm_id with its parameters and outputs. What
   list_layers, describe_layer or describe_algorithm answered still holds: do not ask again.
2. When the session holds tries besides the final chain, ask which steps to keep. Drop exploratory and failed
   calls: the model keeps the working chain only.
3. describe_algorithm for each kept algorithm whose parameters are unclear: never guess a parameter name or
   a value.

## Map the session to model inputs

- Each project layer used as an input becomes one model input of the matching kind (vector or raster), named
  after the layer.
- Each literal (a distance, a number, a field name, a choice) becomes one model input of the matching kind
  (number, string, field, enum), with the session value as its default.
- A model holds Processing steps only: filters and styles applied in the session stay outside it. Say so when
  the user expects them inside.

## Build it with run_pyqgis

run_pyqgis runs your code in the QGIS of the user, with their rights. They read all of it and say yes at every
run, and it is NOT undone with the turn. Say in purpose, in one sentence of the user's language, what the code
does and what file it writes.

1. Ask the file name and where to write it (next to the project file by default, as .model3). Never overwrite
   an existing file: check first and ask for another name.
2. Write the code with QgsProcessingModelAlgorithm: one model input per mapped input, one child per kept step,
   each child parameter wired to a model input or to an output of an earlier child. Keep the values the session
   tested.
   Resolve the final layer ids back to the outputs that produced them: do not embed a temporary session layer id
   or a temporary output path. Use QgsProcessingModelChildParameterSource for model parameters and child outputs,
   and QgsProcessingModelOutput for the final outputs. Give every child a stable, unique id.
   Use child.addParameterSources(name, [source]) for each parameter: setParameterSources has incompatible Python
   bindings in some QGIS builds. scripts/build_processing_models.py and tests/qgis_headless/check_processing_models.py
   show the version-compatible construction API.
3. Write the file with the model save call, read it back, and report: the file, its inputs, its steps in order,
   and how to run it from the Processing toolbox. Test the version and pick the API the running QGIS has, from
   QGIS 3.22 to 4.x.
   Check that toFile succeeds and fromFile reads the saved model, then validate it with the current Processing
   registry. Do not report success for a partial model, missing algorithm, disconnected input or missing final
   output. Creating the model never runs its algorithms; a test run needs its own request and confirmation.
   Read destinationParameterDefinitions() after reloading to obtain the actual output parameter names; QGIS may
   derive them from output descriptions rather than child ids.

## What never to do

- Never build a model without an explicit yes to the proposal.
- Never overwrite a file of the user: ask for another name first.
- Never guess an algorithm parameter: describe_algorithm says it.
- Never put filters or styles in the model: it holds Processing steps only.
- No network, no files outside what the user asked for, no subprocess, no package installed, nothing read from
  the authentication database or the keys.
- No modal dialog, no new dock or window. No endless loop, no sleep: the code runs on the main thread and QGIS
  is frozen meanwhile.
- Never use code to get around a refusal or a question.

## Where to look

- The shipped examples: processing/models/*.model3 of the plugin.
- The analysis skill for choosing and checking algorithms; the pyqgis skill for version-safe code.

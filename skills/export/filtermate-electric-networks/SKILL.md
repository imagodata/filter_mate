---
name: filtermate-electric-networks
description: "Electricity distribution networks through the MCP server of the FilterMate QGIS plugin: electricity MV/LV or HTA/BT asset inventories, substation/feeder dependencies, radial or looped supply architectures and topological outage scenarios. Use when the user asks for it in QGIS with FilterMate."
---

<!-- Generated from skills/electric-networks/SKILL.md by scripts/export_agent_skills.py: do not edit by hand. -->

Needs the MCP server of FilterMate: in QGIS, Agent settings (menu ⋯ of the AGENT panel), tab Other applications: turn it on and copy the configuration for this application. Its tools carry the names below.

# Electricity distribution networks

## Identify the operational question

Distinguish an asset inventory, an existing feeder trace, an extension/architecture comparison and a simulated
equipment outage. Read list_layers and describe_layer for sources/substations, buses, lines/cables, transformers,
switches and delivery points. Inspect actual IDs, endpoint/terminal or feeder relationships, voltage levels,
phase/circuit, operating state, nominal capacity and the date of that state. Use field_values or sample_features
only for information the task needs and when offered. Ask for the source or scenario state when it is ambiguous.

## Build the right connectivity model

- A spatial crossing, a common pole or coincident cables do not make an electrical connection. Use terminal IDs,
  circuit and voltage information; transformers connect their documented terminals across voltage levels.
  Avoid snapping separate circuits or voltage levels together. Preserve parallel circuits and source IDs.
- An existing feeder/substation ID supports an attribute inventory with apply_filter and join_layers. It does
  not by itself prove the current energized supply path or an outage's effect.
- Use known switch positions and in-service flags for the scenario graph. Unknown states remain unknown; ask for
  them or compare explicitly labelled assumptions. Do not derive operational direction from digitizing order.
- A radial feeder is rooted in an identified supply. Multiple supplies require a rooted forest or a stated
  assignment rule. Keep mesh loops and normally open ties in the model; do not silently discard them to get a tree.
  Check components, root reachability, cycles and orphan delivery points before calculating downstream effects.

## Deliver the requested study

- Inventory: layer_statistics for lengths and asset counts by actual voltage, feeder or status fields. Keep missing
  classifications separate and use a suitable CRS/measurement model for length.
- Dependency trace: follow validated relationships or reachable paths from the stated source under the stated
  switch configuration. Report ambiguous or unassigned delivery points rather than assigning the nearest source.
- Architecture: compare candidate radial, looped and meshed corridors using a supplied objective and constraints.
  Minimum length or graph cost alone does not establish electrical feasibility. Preserve reserved ties and label
  each variant, its sources, costs, unserved demand and assumptions.
- Outage: remove the failed asset only in an analysis copy/derived graph. Compare source reachability before and
  after, considering alternative supplies and the specified switch states. Report newly disconnected points,
  already unserved points and uncertain cases separately. A bridge is structurally critical in that graph; its
  business impact depends on the sources and delivery points it isolates.
- Demand/capacity: sum supplied demand values only where units, time basis, coincidence and equipment relationships
  are compatible. kW, kVA, voltage and current are different quantities. Unknown values are not zero. Aggregate
  demand is a screening indicator, not a validated loading calculation.

## Processing and physical calculations

Use find_algorithms with short terms such as shortest path, components, bridge or spanningtree to discover the
installed providers/models. describe_algorithm must establish the returned ID, inputs, costs, directions and
outputs before run_algorithm. GRASS graph operations can support topology when available. A service-area result
follows graph cost; it does not determine energized supply or voltage. If no suitable graph operation is offered,
state the limitation and provide supported inventory/relationship checks; never use run_pyqgis to get around it.

Power flow, voltage drop, losses, short-circuit and protection studies need a suitable available solver, an
electrical model and its boundary conditions. Never present a shortest path, buffer or topological trace as such
a calculation. Discover an installed specialist model when requested; do not invent an algorithm ID, impedance,
diversity factor or equipment rating, and do not install a solver on the user's behalf.

Preserve source topology and operational state. duplicate_layer can create a scenario; run_algorithm outputs must
have new names. Let FilterMate choose output storage; requires_disk needs the user's chosen storage folder first.
Use set_layer_style/set_labels for a requested map and export_layers for a requested export. State source date,
roots, switch assumptions, metric, disconnected assets and the boundaries of the conclusion. cross_filter can
identify assets near a proposed corridor, never prove their electrical connection.

## Where to look

- QGIS network analysis, with actual parameters read from this installation:
  https://docs.qgis.org/latest/en/docs/user_manual/processing_algs/qgis/networkanalysis.html
- GRASS network topology operations:
  https://grass.osgeo.org/grass-stable/manuals/topic_network.html
- The distinction between an electrical graph and a solver's physical model:
  https://pandapower.readthedocs.io/en/latest/topology.html
  https://pandapower.readthedocs.io/en/latest/powerflow.html

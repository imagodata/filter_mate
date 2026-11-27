---
name: filtermate-water-networks
description: "Drinking water networks through the MCP server of the FilterMate QGIS plugin: drinking-water pipe and valve inventories, supply-sector connectivity, customer dependencies, isolation scenarios and extension corridors. Use when the user asks for it in QGIS with FilterMate."
---

<!-- Generated from skills/water-networks/SKILL.md by scripts/export_agent_skills.py: do not edit by hand. -->

Needs the MCP server of FilterMate: in QGIS, Agent settings (menu ⋯ of the AGENT panel), tab Other applications: turn it on and copy the configuration for this application. Its tools carry the names below.

# Drinking water networks

## Identify the study and its inputs

Use this skill for pressurized drinking-water distribution. A gravity sewer upstream/downstream study is a different
model: clarify that request rather than interpreting water-pipe digitizing direction as a flow direction.

Use list_layers and describe_layer for reservoirs/tanks, supply nodes, pumps, pipes, valves, service connections
and customer/demand points. Identify actual asset IDs, endpoint IDs, parent/sector assignments, pipe properties,
valve/pump type and state, source boundaries, units and state date. Use field_values or sample_features only when
needed and offered. A building near a pipe is a connection candidate, not a known subscriber or a supplied point.

## Establish connectivity and sectors

- Prefer verified node IDs and service relations. Check duplicate IDs, dangling references, disconnected components
  and parallel pipes. A crossing is connected only when documented as a junction; a valve lying along a line must
  be represented at the correct graph location before its closure can break that connection.
- Explain any proposed endpoint matching or snapping tolerance in a suitable metric CRS and work on a new analysis
  layer. Preserve original pipe and valve IDs, and keep distinct elevation/pressure zones separate.
- Respect known closed valves, check-valve directions, pumps and inactive assets in the scenario. Unknown operating
  states remain unknown. Geometric line direction, nearest reservoir and terrain elevation alone do not establish
  flow direction in a pressurized looped network.
- Existing sector/source IDs can support apply_filter and join_layers for an inventory. Validate what they mean;
  an administrative sector does not establish physical isolation. Keep multiple sources and loops in reachability
  checks. An arborescence is a derived representation, not evidence that the real network has no alternative feed.

## Carry out the mission

- Inventory: layer_statistics for pipe lengths by actual material, diameter, age or sector fields, and counts of
  valves/connections. Preserve unknown properties as their own group; do not replace them with average values.
- Supply trace: follow verified service relations or graph reachability from the stated supply sources under the
  stated operating configuration. Distinguish connected, disconnected and uncertain demand points.
- Isolation study: define the failed pipe and candidate valve closures. Compare source reachability before and
  after those closures on a derived graph/copy. Include alternative feeds and relevant one-way devices. Identify
  newly disconnected service points, pre-existing disconnections, boundary valves and unresolved topology. A
  suggested isolation sector is a scenario, not an operational valve-switching instruction or a pressure result.
- Extension: compare allowed corridors and connection candidates by supplied cost/length and known constraints.
  cross_filter can support proximity screening. Report demand coverage and route assumptions; shortest distance
  does not determine pipe diameter, available head or water quality.

## Processing and hydraulic limits

Search find_algorithms with short terms such as components, shortest path, bridge or network for the installed
providers/models. Read describe_algorithm for the exact ID, inputs, directed connectivity, output and requires_disk
before run_algorithm. Do not assume GRASS or a specialist hydraulic provider is installed. If the operation is
unavailable, give the supported inventory and missing operation; never use run_pyqgis to get around a refusal.

Pressure, discharge, head loss, pump performance, storage dynamics and water quality require a hydraulic model and
an available suitable solver. They need documented elevations, diameters, roughness, demands, boundary conditions
and device behavior as relevant. Discover an installed EPANET-based workflow when requested; never invent its QGIS
algorithm ID or install it, and never turn geometric connectivity into a claim of adequate pressure or supply.

duplicate_layer can hold a working scenario; never change the source valves or pipes to simulate a closure. Name
new outputs by scenario and let FilterMate manage storage. A file-only provider needs the user's chosen data
folder first. Use set_layer_style/set_labels for a requested map and export_layers only for a requested export.
Report source dates, assumptions, source/valve IDs, affected connection counts and unresolved data separately.

## Where to look

- QGIS network Processing algorithms:
  https://docs.qgis.org/latest/en/docs/user_manual/processing_algs/qgis/networkanalysis.html
- GRASS connectivity operations, when installed:
  https://grass.osgeo.org/grass-stable/manuals/topic_network.html
- EPANET hydraulic model capabilities and inputs:
  https://www.epa.gov/water-research/epanet

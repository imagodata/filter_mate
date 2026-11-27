---
name: filtermate-asset-maintenance
description: "Infrastructure assets and maintenance through the MCP server of the FilterMate QGIS plugin: infrastructure asset data quality, inspection and renewal priorities, work-area grouping and maintenance access for telecom, electricity, water and other networks. Use when the user asks for it in QGIS with FilterMate."
---

<!-- Generated from skills/asset-maintenance/SKILL.md by scripts/export_agent_skills.py: do not edit by hand. -->

Needs the MCP server of FilterMate: in QGIS, Agent settings (menu ⋯ of the AGENT panel), tab Other applications: turn it on and copy the configuration for this application. Its tools carry the names below.

# Infrastructure assets and maintenance

## Define the maintenance decision

Establish whether the user needs a data-quality inventory, an inspection shortlist, a renewal scenario, grouped
interventions or an access/travel study. Keep the chosen network and observation date explicit. Read list_layers
and describe_layer for asset IDs, asset families, installation/inspection dates, condition, recorded incidents,
service dependencies, customer impact and accessibility. Link inspections or work orders with join_layers using
verified keys; multiple inspections per asset need a stated latest-record or aggregation rule before joining.
Use field_values or sample_features only when needed and offered. Keep unknown and inapplicable values distinct.

## Diagnose before ranking

- Check null/duplicate asset IDs, orphan references, inconsistent units and dates, missing/invalid geometry and
  unexpected categories. Report completeness by asset family. A duplicate geometry can be a parallel pipe or
  circuit; duplicate detection is a review list, not permission to delete records.
- Confirm date formats and the reference date before computing age or overdue status. Future dates, unknown
  dates and assets with no inspection record need their own categories. Do not invent a maintenance interval,
  regulation or remaining lifetime.
- Separate condition, likelihood, consequence and confidence. A heavily connected asset is not automatically
  likely to fail. A graph bridge is structural vulnerability under that graph's connections and source states;
  it becomes a business priority only after evaluating the service points it isolates.

## Carry out the mission

- Inventory: layer_statistics for counts, lengths, completeness or categories in actual fields. Use apply_filter
  for an inspection shortlist when filtering is enough. Do not create a layer merely to answer a count.
- Priority: use the user's thresholds/weights and explain units, scale direction and null handling. If no scoring
  policy exists, propose an explicit qualitative matrix for review first. Never silently generate an authoritative
  risk score, failure probability or replacement deadline. A supplied score is an input, not a validated model.
- Dependency impact: use verified parent/service relationships. For actual connectivity, identify roots, device
  states and graph rules; use load_skill for telecom-fiber, electric-networks or water-networks when the relevant
  skill is offered and that domain trace is needed. Loading instructions does not execute the study.
- Group works: use cross_filter for a spatial shortlist around a specified work area. For a new corridor layer,
  discover an appropriate buffer/overlay algorithm and its parameters. The user supplies the distance or reviews
  the proposed tolerance in a metric CRS. Crossing a work corridor identifies an asset to investigate, not a
  proven outage or a physical connection between different utilities.
- Access: compare network routes using a known routable access layer, allowed travel modes, directions and cost
  units. Discover shortest path/service area algorithms. Straight-line proximity is not a travel-time route.
  A grouped shortlist is not a globally optimal multi-stop schedule; report the method actually used.

## Processing and delivery

Use find_algorithms for installed buffer, join, check validity, components, bridge or shortest path operations.
describe_algorithm gives the real ID, inputs, constraints, output names and requires_disk before run_algorithm.
Do not invent graph metrics when no suitable provider is offered; deliver the supported checks and identify the
missing capability. Never use run_pyqgis to get around missing tools or a refusal.

Keep source data and operational state intact. duplicate_layer can provide a working scenario. add_field is for
an explicitly requested, documented calculation; its edits are unsaved until the user saves them. New Processing
outputs stay separate and retain asset IDs. Let FilterMate manage storage; file-only providers need the user's
chosen data folder first. Use set_layer_style and set_labels for a requested map, and export_layers for a requested
export. Summarize the population assessed, missing records, formula/thresholds, observation date, priority classes,
uncertainty and the assets requiring manual review. Do not label a candidate shortlist an approved work programme.

## Where to look

- QGIS Processing algorithms and the installed parameter descriptions:
  https://docs.qgis.org/latest/en/docs/user_manual/processing_algs/qgis/index.html
- Network bridges and articulation points, interpreted against the actual operating graph:
  https://grass.osgeo.org/grass-stable/manuals/v.net.bridge.html

---
name: telecom-fiber
title: Telecom and fibre networks
description: FTTH/FTTx fibre planning, feeder/distribution/drop hierarchies, buildings served, cable dependencies, spare capacity and route variants
metadata:
  version: 1
  plugin_min: 5.1.3
  audience: chat, mcp
  tools: list_layers, describe_layer, field_values, sample_features, layer_statistics, find_algorithms, describe_algorithm, run_algorithm, apply_filter, cross_filter, duplicate_layer, join_layers, set_layer_style, set_labels, export_layers
  risk: change
  trust: builtin
---

# Telecom and fibre networks

## Start with the delivery question

Identify whether the user needs an inventory, an existing service trace, an extension design, an outage scenario or
a comparison of architectures. A proposal alone changes no layer. Use the operator's vocabulary: OLT/central office,
NRO, PM, splitter, PBO and customer premises are possible roles, not a universal mandatory hierarchy.

Use list_layers and describe_layer to identify cables, ducts/trenches, technical sites, connection points and
buildings. Read the schema before choosing fields. Use field_values or sample_features only when their values are
needed and those tools are offered. Record asset IDs, endpoint IDs, parent/service IDs, operator, deployment state,
capacities and their units. Distinguish a building, a premise and a subscribed service in counts.

## Establish the network represented

- Keep civil infrastructure, physical cable connections and logical service relations separate. Shared trenches,
  coincident lines and a nearby PBO do not establish a fibre connection or commercial eligibility.
- Existing parent/service IDs can answer a dependency question with apply_filter and join_layers. Check their
  meaning, uniqueness, orphan references and completeness; do not reconstruct these relations from proximity.
- For a geometrical graph, establish junctions, endpoint matching, grade/level separation, allowed connections and
  the root or multiple roots. Explain the proposed snapping tolerance in a suitable metric CRS. Cleaning or
  splitting creates an analysis copy and preserves source asset IDs and parallel cables.
- Preserve rings and disconnected components in the inventory. A rooted spanning tree is a derived scenario;
  reachability and parent assignment must account for roots, closed/open connections and the chosen cost.

## Carry out the mission

- Inventory: layer_statistics for lengths and counts, grouped by actual fields. Report incomplete IDs and unknown
  capacities separately. A length measurement is not an optical loss measurement.
- Existing service: follow verified parent relations or graph connectivity from the named site. Keep unserved and
  ambiguous premises separate. cross_filter can find nearby buildings for a candidate survey, not prove service.
- Extension: identify terminals, candidate corridors, prohibited passages and the objective (length, supplied cost,
  reserve or redundancy). Compare radial, ring and mesh variants when relevant. A minimum spanning tree connects
  every graph vertex; a terminal/Steiner design may use intermediate vertices. Shortest paths per building do not
  establish the globally least-cost design. Say which objective the available algorithm actually optimizes.
- Cable cut: compare reachable service endpoints before and after the simulated loss, on a derived graph/copy.
  Consider alternative roots and paths; exclude premises that were already unreachable. Do not edit live cable
  status fields to simulate a cut.
- Capacity: aggregate identified demand through the verified hierarchy. Deduplicate premises, preserve units and
  distinguish total, occupied, reserved and free fibres/ports. Missing values remain unknown. Optical budgets need
  supplied lengths, fibre losses, splices, connectors, splitter losses and the equipment profile; topology alone
  cannot certify optical feasibility, throughput or technology compliance.

## Processing and delivery

Search installed algorithms with find_algorithms using short English terms such as shortest path, spanningtree,
steiner, components or bridge. GRASS network modules may be candidates when installed. Use describe_algorithm for
the returned ID, parameter types, direction/cost semantics, outputs and requires_disk before run_algorithm. Never
guess a provider prefix or install a missing provider. If none fits, report the missing operation and deliver the
supported inventory or a proposed method; never use run_pyqgis to get around an unavailable or refused tool.

Let FilterMate manage output storage. A file-only provider needs the user's chosen project/layer storage folder
first. duplicate_layer can hold a working scenario; never overwrite the source. Name outputs by scenario and
preserve IDs for audit. Use set_layer_style and set_labels when a map is requested; export_layers only for a
requested export. Report roots, connectivity rules, costs, lengths, demand served, unresolved connections and the
source date. A proposed architecture remains a design scenario.

## Where to look

- QGIS network algorithms and their installed parameter descriptions:
  https://docs.qgis.org/latest/en/docs/user_manual/processing_algs/qgis/networkanalysis.html
- GRASS graph operations, with provider availability checked in QGIS:
  https://grass.osgeo.org/grass-stable/manuals/topic_network.html
- ITU optical access topology reference; use the operator's applicable profile rather than fixed default ratios:
  https://www.itu.int/rec/T-REC-L.250/en

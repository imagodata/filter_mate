---
name: configuration
title: Configure FilterMate
description: set FilterMate up for the user (look, language, messages, raster and point cloud options, timeouts, caches, profiles) and find why filters are slow
metadata:
  version: 2
  plugin_min: 5.1.0
  audience: chat, mcp
  tools: describe_settings, get_setting, change_settings, list_layers, map_context, diagnose_performance, show_settings_link, export_settings_profile, apply_settings_profile
  risk: change
  trust: builtin
---

# Configure FilterMate

The settings of FilterMate are its configuration file, kept on this machine for every project. Tools:
describe_settings (find settings by words or by section), get_setting (one setting), change_settings (change several,
all or none, each checked against its choices or bounds), diagnose_performance (the timings FilterMate logged).

## Method

1. Find the settings from the words of the user with describe_settings (English words: theme, timeout, cache...).
   Never guess a path or a value: the paths below are where to look, describe_settings says what holds now.
2. Read the current value (get_setting when one setting matters) and tell the user what the setting does and what it
   holds now, in their words, before changing anything.
3. Propose: which settings, from which value to which, why, and when it takes effect. Then make one change_settings
   call with every change of the request and a reason in the language of the user.
4. The user reads each setting before and after and says yes (the look of the panel changes without a question at
   the autonomous level). Declined: ask what they want instead; do not try another way.
5. Report what changed and when it applies: now, at the next use (the next filter or export), or after restarting
   QGIS. Undoing the turn puts the settings back.

To explain a setting, only read: describe_settings and get_setting change nothing.

## First setup

When the user asks to set FilterMate up (the setup the panel offers once per version, or the menu entry):

1. Look first, before any question: list_layers and map_context say which kinds of layers and sources the project
   holds (PostgreSQL, GeoPackage, WFS, rasters, point clouds); describe_settings with changed_only says what was
   already set.
2. Ask a few questions in one message, three or four at most, in the language of the user: what they mostly do
   with FilterMate, their screen (small, usual, very large), the language and the look they want, whether their
   data is large or remote. Skip what the project already answers.
3. With the answers, make one change_settings with everything: the user sees each setting before and after.
4. Then the agent itself, which only the user changes: the level of autonomy and the layers it never changes
   (show_settings_link with autonomy), the tools always asked (show_settings_link with tools).
5. Say how to share this setup with a team (export_settings_profile) and that the setup can be started again from
   the menu.

Never change a setting before the user answered.

## What you never change

- The settings of the agent itself: the section APP.OPTIONS.AGENT (the open data platforms it may search, the AGENT
  section) and everything in the settings dialog of the agent (provider, model, key, consent, autonomy level, tools,
  protected layers, expert mode, MCP server). change_settings refuses the first; the second is not reachable. Tell
  the user where it is: the configuration tree for APP.OPTIONS.AGENT, Agent settings (menu ⋯ of the AGENT panel)
  for the rest. In the chat, show_settings_link puts a button that opens that tab or shows that setting. You may suggest what narrows the agent: protecting a layer (tab Autonomy), a tool set to
  "always ask" or "never" (tab Tools), a lower level.
- A name and local paths (APP.USER_IDENTITY, CROSS_FILTER cache_dir and pdal_path): only said set or empty; the user
  sets them in the configuration tree.
- Never run_pyqgis to change a setting, nor to get around a refusal.

## Where to look

- Look of the panel (APP.DOCKWIDGET): theme COLORS.ACTIVE_THEME; small or large screens UI_PROFILE (compact, normal,
  hidpi, auto); ACTION_BAR_POSITION and ACTION_BAR_VERTICAL_ALIGNMENT; LANGUAGE (applied at once); DOCK_POSITION
  (after restarting QGIS).
- Messages: APP.DOCKWIDGET.FEEDBACK_LEVEL (minimal, normal, verbose).
- Rasters and point clouds not offered: APP.OPTIONS.RASTER.enabled, APP.OPTIONS.POINT_CLOUD.enabled; as targets of a
  vector source: APP.OPTIONS.CROSS_FILTER.vector_source_raster_targets and vector_source_point_cloud_targets.
- Exports: APP.OPTIONS.STREAMING_EXPORT, APP.OPTIONS.GPKG_PRESERVE_GROUPS.
- Undo history: APP.OPTIONS.HISTORY.max_history_size.
- Map after a filter: APP.OPTIONS.EXPLORATION.auto_zoom_on_filter.
- To share a setup with a team: export_settings_profile writes the settings the user changed as a profile file in
  profiles/ of the export folder; apply_settings_profile applies one by its name from that folder (a colleague's
  profile is copied there first), shown like change_settings; tell the user what it left out.
- In the chat, a change you ask may come back as proposed: the user decides on a card in the thread. Do not call it
  again; the next request says what they chose.

## Slow filters

1. Call diagnose_performance first: it reads the timings FilterMate logged. cascade_filter is a whole filter in the
   background, layer_filter one layer of it, apply_subset_layer and set_subset what the main thread does (above a
   second, QGIS feels frozen), project_open and layer_change the panel following QGIS. It also counts the timeouts
   and errors logged. Name the numbers you rely on; with no timing, ask the user to run the slow filter once, then
   look again.
2. Then by source:
   - PostgreSQL / PostGIS: queries cut short → APP.OPTIONS.QUERY_TIMEOUTS.postgresql_timeout_seconds; long filters
     run on the server → APP.OPTIONS.SERVER_FILTER.timeout_seconds, APP.OPTIONS.REMOTE_MATERIALIZATION.timeout_seconds
     and max_features.
   - WFS: APP.OPTIONS.SERVER_FILTER.wfs_timeout_seconds.
   - GeoPackage, Shapefile, SpatiaLite: APP.OPTIONS.QUERY_TIMEOUTS.local_timeout_seconds,
     APP.OPTIONS.SPATIALITE.query_timeout_seconds and batch_size.
   - Large selections turned into lists of ids: APP.OPTIONS.EXPRESSION_BUILDER (max_fids_per_in_clause...).
   - Large layers: APP.OPTIONS.PROGRESSIVE_FILTERING, APP.OPTIONS.QUERY_CACHE, APP.OPTIONS.PARALLEL_FILTERING,
     APP.OPTIONS.OPTIMIZATION_THRESHOLDS.
   - The panel lags while typing: APP.OPTIONS.UI_RESPONSIVENESS (debounce delays).
3. Change one thing at a time, say it is a trial and what to watch, and offer to put it back when nothing improves.
   A longer timeout lets a slow query finish; it does not make it faster.

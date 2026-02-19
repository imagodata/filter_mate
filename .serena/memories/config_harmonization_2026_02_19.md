# Config Harmonization Session — 2026-02-19

## Overview
Full harmonization of FilterMate's configuration system. config.default.json is now the single source of truth.

## Problems Fixed
1. **P1 (HIGH)**: min/max constraints in config.default.json were ignored by JSON TreeView spinboxes
   - Fixed in `ui/widgets/json_view/datatypes.py` → `ConfigValueType.createEditor()`
   - QSpinBox and QDoubleSpinBox now read `data.get('min')` / `data.get('max')`

2. **P2 (MEDIUM)**: 6 params used raw values instead of `{value, description}` format
   - DISCORD_INVITE, GITHUB_PAGE, GITHUB_REPOSITORY, QGIS_PLUGIN_REPOSITORY, APP_SQLITE_PATH, FRESH_RELOAD_FLAG
   - All wrapped + backward-compat helpers `_get_option_value()` / `_set_option_value()` in config.py

3. **P3 (MEDIUM)**: config_schema.json desynchronized from config.default.json
   - Marked as deprecated (`_DEPRECATED` field added)
   - Never used in core flow (ConfigEditorWidget, ConfigMetadataHandler, ConfigValidator are dead code)

4. **P5 (LOW)**: FALLBACK_CONFIG had deprecated `DOCKWIDGET.THEME` key
   - Replaced with `DOCKWIDGET.COLORS.ACTIVE_THEME` + `THEME_SOURCE`

5. **Inconsistency**: MAX_ADD_LAYERS_QUEUE was 10 in task_orchestrator vs 50 in constants
   - Aligned to 50

## New Configurable Parameters (16 total)

### APP.OPTIONS.UI_RESPONSIVENESS
- `expression_debounce_ms`: 450 (min:100, max:2000) — dockwidget expression timer
- `filter_debounce_ms`: 300 (min:50, max:1000) — custom_widgets filter timer
- `canvas_refresh_delay_simple_ms`: 500 (min:100, max:5000) — task_completion_handler
- `canvas_refresh_delay_complex_ms`: 1500 (min:500, max:10000) — task_completion_handler

### APP.OPTIONS.FAVORITES
- `recent_favorites_limit`: 10 (min:1, max:100) — favorites_widget

### APP.OPTIONS.SPATIALITE
- `batch_size`: 5000 (min:100, max:100000) — interruptible_query batch processing
- `progress_interval`: 1000 (min:100, max:50000) — interruptible_query progress reporting
- `query_timeout_seconds`: 120 (min:10, max:3600) — interruptible_query timeout

### APP.OPTIONS.EXPRESSION_BUILDER
- `max_fids_per_in_clause`: 5000 (min:100, max:100000) — expression_builder FID batching
- `absolute_fid_limit`: 50000 (min:1000, max:500000) — expression_builder absolute limit
- `max_inline_features`: 1000 (min:10, max:50000) — expression_builder inline threshold
- `max_expression_length`: 10000 (min:1000, max:1000000) — expression_builder length limit

### APP.OPTIONS.QUERY_TIMEOUTS
- `postgresql_timeout_seconds`: 60.0 (min:5.0, max:600.0) — resilience circuit breaker
- `local_timeout_seconds`: 30.0 (min:5.0, max:300.0) — resilience circuit breaker

### APP.OPTIONS.EXPLORATION
- `point_buffer_distance_m`: 50 (min:1, max:10000) — exploring_controller buffer
- `feature_picker_limit`: 1000 (min:10, max:100000) — custom_widgets feature limit

## Architecture Notes
- Config read pattern: `ENV_VARS["CONFIG_DATA"]["APP"]["OPTIONS"]["SECTION"]["param"]`
- All params use `{value, description, min?, max?}` format
- TreeView auto-creates appropriate editors (spinbox with bounds, checkbox, line edit)
- `_get_option_value(option, default)` handles both wrapped and raw formats for backward compat
- `_set_option_value(options_dict, key, new_value)` handles both formats for writes

## Dead Code (kept but deprecated)
- `config_schema.json` — not used by any runtime code
- `ConfigEditorWidget` (config_editor_widget.py) — exported but never instantiated
- `ConfigMetadataHandler` (config_metadata_handler.py) — exported but never instantiated
- `ConfigValidator` (config_metadata.py) — exported but never instantiated

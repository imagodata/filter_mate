# FilterMate configuration

This folder holds the default configuration and the helpers that load, migrate, validate and read it. The user edits settings in the Configuration tab of the dock; the tab writes `config.json`.

## Files

| File | Role |
|---|---|
| `config.default.json` | Reference configuration, with the description, choices and limits of every setting. Shipped in the zip. |
| `config.json` | Copy used when the profile folder is unavailable. The active file is in the profile (see below). |
| `config.py` | `init_env_vars()`, `reload_config()`, `reset_config_to_default()`, migration, `_get_option_value` / `_get_option_bool` / `_get_option_int`, and the `ENV_VARS` dict. |
| `config_validator.py` | Structural validation of the loaded file (sections, `_CONFIG_VERSION`, value types, `choices`). Called by `init_env_vars()`; it only logs. |
| `feedback_config.py` | Message verbosity (`minimal`, `normal`, `verbose`): `should_show_message(category)`, `set_feedback_level_from_string`. |
| `theme_helpers.py` | `get_active_theme`, `get_theme_colors` and related readers of the theme settings. |
| `config.v2.example.json` | Example of a proposed v2 layout (lower-case keys). Not used by the code. |

## Where the active file is

`init_env_vars()` uses `<QGIS profile>/FilterMate/config.json` (`QgsApplication.qgisSettingsDirPath()`). If it does not exist, it is copied from `config.default.json`. `ENV_VARS["CONFIG_JSON_PATH"]` holds the path actually in use; `get_config_json_path()` returns it. If the profile folder cannot be used, `config/config.json` in the plugin folder is the fallback.

At each start `_migrate_config` merges keys that are new in `config.default.json`, overwrites the schema-owned fields of existing keys (`description`, `choices`, `min`, `max`, `applies_to`, `_hidden`, `_display_name`), removes obsolete sections, and keeps the user's `value`s. It rewrites `config.json` only when something changed.

## Format

Sections are `_CONFIG_VERSION`, `_CONFIG_META`, `APP`, `CURRENT_PROJECT` and `EXTENSIONS`. A setting is an object with a `value`:

```json
"cache_max_gb": {
  "value": 5,
  "description": "Maximum size of the FilterMate cache of derived rasters and point clouds"
}
```

Optional fields: `choices` (list of allowed values), `min`, `max`. Keys starting with `_` are not settings: `_display_name` names a group in the Configuration tab and `_hidden` hides it.

## Reading a setting

`ENV_VARS["CONFIG_DATA"]` holds the loaded dict. `reload_config()` updates it in place, so references stay valid. The `_get_option_*` helpers accept a wrapped option (`{"value": ...}`) or a raw value, and tolerate a hand-edited file:

```python
from filter_mate.config.config import ENV_VARS, _get_option_bool, _get_option_int

options = ENV_VARS.get("CONFIG_DATA", {}).get("APP", {}).get("OPTIONS", {})
raster_on = _get_option_bool(options.get("RASTER", {}).get("enabled"), False)
cache_gb = _get_option_int(options.get("CROSS_FILTER", {}).get("cache_max_gb"), 5)
```

`adapters/qgis/point_cloud_capability.py` (`is_raster_filtering_enabled`) is a real example.

## Adding a setting

1. Add it to `config.default.json` with `value` and `description` (and `choices`, `min`, `max` when they apply). Put it in an existing group or create one with `_display_name`.
2. Read it with the `_get_option_*` helpers. Existing users get it at the next start through the migration.
3. The Configuration tab shows it without further code: it displays the JSON tree (`ui/widgets/json_view/`, `ui/managers/config_model_manager.py`).

Extensions add their own keys under `EXTENSIONS.<id>` by returning them from `config_schema()` (see `extensions/base.py`).

## Metadata

The description, choices and limits of every setting live in `config.default.json`; `config.py` overlays them on the user's file at each start (`_sync_metadata`). The former `config_schema.json`, `ConfigMetadata` and `ConfigMetadataHandler` (which only read that file) were removed. `ConfigEditorWidget` and `SimpleConfigDialog` (`ui/dialogs/config_editor_widget.py`) build a form without metadata hints; the dock does not use them.

## Tests

`tests/unit/test_config_migration.py` covers the merge and the metadata overlay of `config.py`. `tests/unit/test_plugin_config.py` covers the forced language and the configuration reset in `filter_mate.py`.

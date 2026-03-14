# FilterMate — Plugin Lifecycle

How FilterMate initializes, how layers are tracked, and how the plugin responds to QGIS events.

---

## Plugin Initialization Sequence

```
QGIS loads plugin
  → FilterMate.__init__()
      → Loads config/config.json
      → Sets up QGIS factory (dependency injection)

  → FilterMate.initGui()
      → Creates toolbar button + menu entry
      → Reloads config from disk
      → Auto-migrates config if needed
      → Checks geometry validation settings
      → Installs message log filter

  → User clicks toolbar button (or auto-activate)
  → FilterMate.run()
      → Creates FilterMateDockWidget
      → Connects dockwidget signals to FilterMateApp
      → Adds dock widget to QGIS interface

  → DockWidget.__init__()
      → setupUi() (from .ui file)
      → setupUiCustom() (dynamic widgets: checkable comboboxes, header bar, centroids checkbox)
      → ConfigurationManager.configure_widgets() (signal connections)
      → manage_configuration_model() (JSON tree editor)

  → widgetsInitialized signal emitted
      → FilterMateApp._on_widgets_initialized()
          → Connects to QgsProject.layersAdded signal
          → Loads existing project layers
          → Restores properties from SQLite database
          → Detects backends for each layer
          → Updates backend indicator
          → Setup complete
```

---

## Layer Lifecycle

### When Layers Are Added to the Project

1. `QgsProject.layersAdded` signal fires
2. `FilterMateApp._on_layers_added()` catches it
3. Layers are **accumulated for 500ms** (batching — prevents rapid-fire processing during project load, when many layers may be added in quick succession)
4. `_process_pending_added_layers()` runs:
   - Filters to usable vector layers with geometry (non-geometry layers are ignored)
   - Detects PostgreSQL layers → warns if `psycopg2` is missing
   - Validates PostgreSQL connections (schedules retry for connections not yet ready)
   - Calls `manage_task('add_layers', filtered_layers)`
5. For each layer added:
   - Creates entry in `PROJECT_LAYERS[layer_id]` with infos, exploring, and filtering defaults
   - Attempts to restore saved properties from SQLite table `fm_project_layers_properties`
   - Detects the best display field via `get_best_display_field()`
   - Updates comboboxes (source layer, target layers, export layers)

### When Layers Are Removed from the Project

- Cleans up `PROJECT_LAYERS[layer_id]` for each removed layer
- Cancels any running tasks associated with that layer
- Updates all comboboxes to remove the stale reference

### When the Source Layer Changes (User or Auto-Sync)

1. `current_layer_changed(layer, manual_change)` called
2. Validates layer (`is_valid`, has geometry)
3. Updates `self.current_layer`
4. Restores layer-specific properties from `PROJECT_LAYERS[layer_id]`
5. Repopulates exploring widgets (feature picker, field expression widget)
6. Restores GroupBox state (which GroupBox was active last time this layer was selected)
7. Restores filtering toggle states (which toggles were checked for this layer)
8. Updates backend indicator
9. Updates undo/redo button states

---

## get_best_display_field() — Auto Field Selection

When a layer is loaded, FilterMate automatically selects the best field to display in the feature picker (Single Selection GroupBox).

### Priority Order

| Priority | Source | Condition |
|---|---|---|
| 1 | **Layer's configured display expression** | If set in QGIS Layer Properties → Display tab |
| 2 | **ValueRelation fields** | Fields with value relations → generates `represent_value()` expression |
| 3 | **Name-pattern fields** | Fields named: `name`, `nom`, `label`, `titre`, `title`, `description`, `libelle`, `bezeichnung`, `nombre`, `nome`, `naam`, `display_name`, `full_name` — only if they have non-null values |
| 4 | **First text/string field** | That is not an ID field AND has non-null values |
| 5 | **Primary key** | Always has values; last resort before absolute fallback |
| 6 | **First field with values** | Absolute fallback |

### How to Influence Field Selection

- **Set the display expression** in QGIS Layer Properties → Display tab → "Display Name" expression. This is Priority 1 and overrides everything else.
- **Change the field expression manually** in the FilterMate Exploring GroupBox after loading. This takes effect immediately for the current session and is persisted per-layer in the SQLite database.

---

## SQLite Persistence

FilterMate persists layer-specific properties to a SQLite database between sessions:

- **Table:** `fm_project_layers_properties`
- **Stored per layer:** exploring state (field expression, active GroupBox), filtering state (which toggles were on, buffer values, predicates), backend override
- **On layer load:** properties are restored automatically if a matching record exists
- **On layer removal or reset:** properties can be cleared from the database

This is what allows FilterMate to "remember" your configuration across QGIS restarts.

---

## Config Migration

During `initGui()`, FilterMate checks the loaded config version and **auto-migrates** if needed:

- Missing keys are added with defaults
- Renamed keys are updated
- Deprecated structures are cleaned up
- Migration is non-destructive — existing valid settings are preserved
- No user action required; migration runs silently on startup

---

## Message Log Filter

FilterMate installs a custom **message log filter** during `initGui()`. This:

- Intercepts QGIS log messages from the FilterMate log channel
- Routes them to the appropriate feedback level display
- Ensures all internal log calls also appear in the QGIS Log Messages panel (View → Panels → Log Messages → FilterMate tab)

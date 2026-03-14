# FilterMate — Signal & Interaction Map

> Complete reference of all signal connections between widgets, buttons, and handlers.
> This documents the reactive behavior chain: what happens when a user clicks, toggles, or changes any widget.

---

## How Signals Work in FilterMate

Every widget has a **signal** (Qt event) connected to a **handler** (Python method). The `ConfigurationManager.configure_widgets()` method sets up all connections at startup. Additional connections are made in `_setup_conditional_widget_states()` and `_setup_buffer_buttons_dependency()`.

**Key pattern:** Most toggle buttons use a generic `layer_property_changed()` or `project_property_changed()` handler that:
1. Updates the property in `PROJECT_LAYERS[layer_id]` dictionary
2. Calls custom callback functions (`ON_TRUE`, `ON_FALSE`, `ON_CHANGE`)
3. Reconnects exploring widget signals

---

## ACTION Buttons → Signals

| Widget | Signal | Handler | What Happens |
|---|---|---|---|
| **Filter** button | `clicked` | `launchTaskEvent(state, 'filter')` | Validates config → emits `launchingTask` signal → FilterTask runs in background thread |
| **Undo** button | `clicked` | `launchTaskEvent(state, 'undo')` | Restores previous filter state from history stack |
| **Redo** button | `clicked` | `launchTaskEvent(state, 'redo')` | Re-applies previously undone filter |
| **Unfilter** button | `clicked` | `launchTaskEvent(state, 'unfilter')` | Uses history undo to restore previous state; clears filter if no history |
| **Export** button | `clicked` | `launchTaskEvent(state, 'export')` | Syncs HAS_LAYERS_TO_EXPORT flag → runs export task |
| **About** button | `clicked` | `open_project_page()` | Opens FilterMate website in browser |

### launchTaskEvent Special Behaviors
- **User action tasks** (`undo`, `redo`, `unfilter`, `reset`, `export`) bypass the `_filtering_in_progress` protection window
- If `current_layer` is None during a user action, the handler tries 3 recovery strategies:
  1. Recover from `_saved_layer_id_before_filter`
  2. Recover from combobox current selection
  3. Use first layer in `PROJECT_LAYERS`
- **Export** task does a just-in-time sync of HAS_LAYERS_TO_EXPORT flag before execution (Qt may restore widget states without emitting signals)

---

## EXPLORING Buttons → Signals

| Widget | Signal | Handler | What Happens |
|---|---|---|---|
| **Identify** | `clicked` | `exploring_identify_clicked()` | Opens QGIS Identify Results for selected feature |
| **Zoom** | `clicked` | `exploring_zoom_clicked()` | Pans/zooms map canvas to feature extent |
| **Select** (toggle) | `toggled` | `layer_property_changed('is_selecting', state)` | ON: calls `exploring_select_features()` → highlights on map. OFF: calls `exploring_deselect_features()` |
| **Track** (toggle) | `toggled` | `layer_property_changed('is_tracking', state)` | ON: calls `exploring_zoom_clicked()` immediately, then auto-zooms on every feature change |
| **Link** (toggle) | `toggled` | `layer_property_changed('is_linking', state)` | ON/OFF: calls `exploring_link_widgets()` → syncs all exploring GroupBox widgets together |
| **Reset** | `clicked` | `resetLayerVariableEvent()` | Clears all exploring properties for the current layer |

---

## EXPLORING Content Widgets → Signals

| Widget | Signal | Handler | What Happens |
|---|---|---|---|
| **Single Selection Feature Picker** | `featureChanged` | `exploring_features_changed()` | Selected feature changed → updates map, triggers zoom/select/identify if enabled |
| **Single Selection Field Expression** | `fieldChanged` | *(handled by ExploringController with debounce)* | Display field changed → repopulates feature picker with new field values |
| **Multiple Selection Features List** | `updatingCheckedItemList` | `exploring_features_changed()` | Checked features changed → updates selection |
| **Multiple Selection Features List** | `filteringCheckedItemList` | `exploring_source_params_changed(groupbox_override='multiple_selection')` | Feature list filter applied → refreshes source parameters |
| **Multiple Selection Field Expression** | `fieldChanged` | *(handled by ExploringController with debounce)* | Display field changed → repopulates feature list |
| **Custom Selection Field Expression** | `fieldChanged` | *(handled by ExploringController with debounce)* | Expression changed → used directly as filter |

### GroupBox Signals (Exclusive Behavior)

| Widget | Signal | Handler | What Happens |
|---|---|---|---|
| **Single Selection GroupBox** | `toggled` | `_on_groupbox_clicked('single_selection', checked)` | If checked → unchecks & collapses Multiple + Custom (mutual exclusion) |
| **Single Selection GroupBox** | `collapsedStateChanged` | `_on_groupbox_collapse_changed('single_selection', collapsed)` | Collapse/expand visual state |
| **Multiple Selection GroupBox** | `toggled` | `_on_groupbox_clicked('multiple_selection', checked)` | If checked → unchecks & collapses Single + Custom |
| **Multiple Selection GroupBox** | `collapsedStateChanged` | `_on_groupbox_collapse_changed('multiple_selection', collapsed)` | Collapse/expand visual state |
| **Custom Selection GroupBox** | `toggled` | `_on_groupbox_clicked('custom_selection', checked)` | If checked → unchecks & collapses Single + Multiple |
| **Custom Selection GroupBox** | `collapsedStateChanged` | `_on_groupbox_collapse_changed('custom_selection', collapsed)` | Collapse/expand visual state |

**Exclusive logic:** `_force_exploring_groupbox_exclusive(active_groupbox)` blocks all signals, sets checked/collapsed states, then unblocks. Has stuck-state timeout protection (500ms).

---

## FILTERING Buttons → Signals

| Widget | Signal | Handler | Custom Callbacks | What Happens |
|---|---|---|---|---|
| **Auto Current Layer** | `clicked` | `filtering_auto_current_layer_changed(state)` | — | Toggles auto-sync between QGIS layer panel and source layer combobox |
| **Layers to Filter** | `toggled` | `layer_property_changed('has_layers_to_filter', state)` | `ON_CHANGE`: `filtering_layers_to_filter_state_changed()` | Shows/enables target layers combobox + distant centroids checkbox |
| **Combine Operator** | `toggled` | `layer_property_changed('has_combine_operator', state)` | `ON_CHANGE`: `filtering_combine_operator_state_changed()` | Shows/enables AND/OR operator comboboxes |
| **Geometric Predicates** | `toggled` | `layer_property_changed('has_geometric_predicates', state)` | `ON_CHANGE`: `filtering_geometric_predicates_state_changed()` | Shows/enables predicates combobox. **Also controls buffer buttons dependency** |
| **Buffer Value** | `toggled` | `layer_property_changed('has_buffer_value', state)` | `ON_CHANGE`: `filtering_buffer_value_state_changed()` | Shows/enables buffer spinbox + PropertyOverrideButton |
| **Buffer Type** | `toggled` | `layer_property_changed('has_buffer_type', state)` | `ON_CHANGE`: `filtering_buffer_type_state_changed()` | Shows/enables buffer type combo + segments spinbox |

---

## FILTERING Content Widgets → Signals

| Widget | Signal | Handler | What Happens |
|---|---|---|---|
| **Source Layer Combobox** | `layerChanged` | `current_layer_changed(layer, manual_change=True)` | New source layer → repopulates all widgets, updates exploring, resets properties |
| **Layers to Filter Combobox** | `checkedItemsChanged` | `layer_property_changed('layers_to_filter', state)` | Target layers selection changed → stores in `PROJECT_LAYERS` via `get_layers_to_filter()` |
| **Source Combine Operator** | `currentIndexChanged` | `layer_property_changed('source_layer_combine_operator', index)` | AND/OR selection changed for source layer conditions |
| **Other Layers Combine Operator** | `currentIndexChanged` | `layer_property_changed('other_layers_combine_operator', index)` | AND/OR selection changed for cross-layer conditions |
| **Geometric Predicates Combobox** | `checkedItemsChanged` | `layer_property_changed('geometric_predicates', state)` | Selected predicates changed → stores list (intersects, within, etc.) |
| **Use Centroids (Source)** | `stateChanged` | `layer_property_changed('use_centroids_source_layer', bool(state))` | `ON_CHANGE`: `_update_buffer_validation()` — Updates buffer validation rules |
| **Use Centroids (Distant)** | `stateChanged` | `layer_property_changed('use_centroids_distant_layers', bool(state))` | Stores centroid preference for target layers |
| **Buffer Value SpinBox** | `valueChanged` | `layer_property_changed_with_buffer_style('buffer_value', value)` | Updates buffer value + changes spinbox visual style (yellow if negative = erosion) |
| **Buffer PropertyOverrideButton** | `changed` | `layer_property_changed('buffer_value_property', state)` | `ON_CHANGE`: `filtering_buffer_property_changed()`, `CUSTOM_DATA`: `get_buffer_property_state()`. Toggles expression override mode |
| **Buffer Type Combobox** | `currentTextChanged` | `layer_property_changed('buffer_type', text)` | Buffer geometry type changed |
| **Buffer Segments SpinBox** | `valueChanged` | `layer_property_changed('buffer_segments', value)` | Buffer circle approximation quality changed |

### Buffer Value Special Behavior: Negative = Erosion
When buffer value is negative:
- Spinbox background turns **yellow** (`#FFF3CD`, border `#FFC107`)
- Tooltip changes to "Negative buffer (erosion): shrinks polygons inward"
- When positive or zero: default style, tooltip "Buffer value in meters (positive=expand, negative=shrink polygons)"

---

## EXPORTING Buttons → Signals

| Widget | Signal | Handler | What Happens |
|---|---|---|---|
| **Layers** | `toggled` | `project_property_changed('has_layers_to_export', state)` | Enables/disables layers combobox |
| **Projection** | `toggled` | `project_property_changed('has_projection_to_export', state)` | Enables/disables CRS selector |
| **Styles** | `toggled` | `project_property_changed('has_styles_to_export', state)` | Enables/disables styles combobox |
| **Datatype** | `toggled` | `project_property_changed('has_datatype_to_export', state)` | Enables/disables format combobox |
| **Output Folder** | `clicked` | `project_property_changed('has_output_folder_to_export', state)` | `ON_CHANGE`: `dialog_export_output_path()` — Opens file browser dialog |
| **Zip** | `clicked` | `project_property_changed('has_zip_to_export', state)` | `ON_CHANGE`: `dialog_export_output_pathzip()` — Opens file browser dialog |

**Note:** Output Folder and Zip use `clicked` (not `toggled`) — they open a file dialog on every click.

---

## EXPORTING Content Widgets → Signals

| Widget | Signal | Handler | What Happens |
|---|---|---|---|
| **Layers to Export Combobox** | `checkedItemsChanged` | `project_property_changed('layers_to_export', state)` | Selected export layers changed, stored via `get_layers_to_export()` |
| **Projection Selector** | `crsChanged` | `project_property_changed('projection_to_export', state)` | Export CRS changed, stored via `get_current_crs_authid()` |
| **Styles Combobox** | `currentTextChanged` | `project_property_changed('styles_to_export', text)` | Style export option changed |
| **Datatype Combobox** | `currentTextChanged` | `project_property_changed('datatype_to_export', text)` | Output format changed |
| **Output Folder LineEdit** | `textEdited` | `project_property_changed('output_folder_to_export', text)` | `ON_CHANGE`: `reset_export_output_path()` — Validates/resets output path |
| **Zip LineEdit** | `textEdited` | `project_property_changed('zip_to_export', text)` | `ON_CHANGE`: `reset_export_output_pathzip()` — Validates/resets zip path |
| **Batch Output Folder Checkbox** | `stateChanged` | `project_property_changed('batch_output_folder', bool(state))` | Per-layer export toggle |
| **Batch Zip Checkbox** | `stateChanged` | `project_property_changed('batch_zip', bool(state))` | Per-layer zip toggle |

---

## DOCK Widgets → Signals

| Widget | Signal | Handler | What Happens |
|---|---|---|---|
| **ToolBox** (FILTERING/EXPORTING tabs) | `currentChanged` | `select_tabTools_index(index)` | Switches action button states (see tab-switching table below) |
| **Config Tree View** | `collapsed` / `expanded` | *(None — visual only)* | JSON tree collapse/expand |
| **Config Model** | `itemChanged` | *(None — handled elsewhere)* | Config value edited |
| **Config ButtonBox** | `accepted` / `rejected` | *(None — handled elsewhere)* | Config dialog accept/cancel |

---

## QGIS Integration → Signals

| Widget | Signal | Handler | What Happens |
|---|---|---|---|
| **QGIS Layer Tree View** | `currentLayerChanged` | `current_layer_changed(layer, manual_change=<auto_flag>)` | Layer selected in QGIS panel → if Auto Current Layer is ON, updates FilterMate source layer. `manual_change` is True when auto-sync is enabled. |

---

## Signal Flow Chains

### Chain 1: User Selects a Feature (Single Selection)
```
FeaturePickerWidget.featureChanged
  → exploring_features_changed()
    → if IS_TRACKING checked → exploring_zoom_clicked() → map zooms
    → if IS_SELECTING checked → exploring_select_features() → map highlights
    → updates PROJECT_LAYERS[layer_id] with selection data
```

### Chain 2: User Toggles Geometric Predicates
```
pushButton_checkable_filtering_geometric_predicates.toggled(True)
  → layer_property_changed('has_geometric_predicates', True)
    → filtering_geometric_predicates_state_changed()
      → comboBox_filtering_geometric_predicates.setEnabled(True)
  → _on_predicates_toggled(True)  [from _setup_buffer_buttons_dependency]
    → pushButton_checkable_filtering_buffer_value.setEnabled(True)
    → pushButton_checkable_filtering_buffer_type.setEnabled(True)

pushButton_checkable_filtering_geometric_predicates.toggled(False)
  → layer_property_changed('has_geometric_predicates', False)
    → filtering_geometric_predicates_state_changed()
      → comboBox_filtering_geometric_predicates.setEnabled(False)
  → _on_predicates_toggled(False)
    → pushButton_checkable_filtering_buffer_value.setEnabled(False) + setChecked(False)
    → pushButton_checkable_filtering_buffer_type.setEnabled(False) + setChecked(False)
    → (unchecking triggers toggled(False) → all buffer widgets disabled)
```

### Chain 3: User Clicks Filter Button
```
pushButton_action_filter.clicked
  → launchTaskEvent(state, 'filter')
    → validates: widgets_initialized + current_layer + PROJECT_LAYERS
    → checks _filtering_in_progress protection
    → checks edit mode (shows popup if layer in edit mode)
    → emits launchingTask signal
      → FilterTask created in background thread
        → selects backend (PostgreSQL/Spatialite/OGR/Memory)
        → builds expression from configuration
        → applies subset string to layer(s)
        → emits completion → undo stack updated
```

### Chain 4: Tab Switch (FILTERING → EXPORTING → CONFIGURATION)
```
toolBox_tabTools.currentChanged(1)
  → select_tabTools_index(1)
    → FILTER btn: disabled
    → UNDO btn: disabled
    → REDO btn: disabled
    → UNFILTER btn: disabled
    → EXPORT btn: ENABLED
    → ABOUT btn: always enabled
    → set_exporting_properties()
    → undoRedoStateRequested.emit()
```

### Chain 5: Source Layer Changed
```
comboBox_filtering_current_layer.layerChanged(layer)
  → current_layer_changed(layer, manual_change=True)
    → validates layer (is_valid, has geometry)
    → updates self.current_layer
    → repopulates exploring widgets (feature picker, field expressions)
    → repopulates filtering widgets (layers to filter list)
    → updates backend indicator
    → restores layer-specific properties from PROJECT_LAYERS
    → updates undo/redo button states
```

### Chain 6: GroupBox Exclusive Toggle
```
mGroupBox_exploring_multiple_selection.toggled(True)
  → _on_groupbox_clicked('multiple_selection', True)
    → _force_exploring_groupbox_exclusive('multiple_selection')
      → blocks all signals
      → single_selection: setChecked(False), setCollapsed(True)
      → multiple_selection: setChecked(True), setCollapsed(False)
      → custom_selection: setChecked(False), setCollapsed(True)
      → unblocks all signals
      → forces layout update (prevents widget_exploring_keys from disappearing)
```

---

## property_changed vs project_property_changed

| Method | Used By | Stores In | Purpose |
|---|---|---|---|
| `layer_property_changed()` | FILTERING + EXPLORING widgets | `PROJECT_LAYERS[layer_id][group][property]` | Per-layer properties (filtering config is layer-specific) |
| `project_property_changed()` | EXPORTING widgets | `project_props` (project-level) | Project-wide properties (export config is global) |

Both methods support custom callback dictionaries:
- `ON_TRUE`: called when value is truthy
- `ON_FALSE`: called when value is falsy
- `ON_CHANGE`: called on every change regardless of value
- `CUSTOM_DATA`: lambda to compute stored data (e.g., `get_layers_to_filter()`)

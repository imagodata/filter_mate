# FilterMate — UI Guide

> **This is the most important reference file.** It describes every visual element, button, and widget in the FilterMate dock panel, in layout order (top to bottom, left to right).

---

## Top-Level Structure

FilterMate is a **QDockWidget** divided into three main zones by a vertical `QSplitter`:

```
┌─────────────────────────────────────────┐
│  A) EXPLORING ZONE   (stretch factor 2)  │
├─────────────────────────────────────────┤  ← splitter handle (6px, not collapsible)
│  B) TOOLBOX ZONE     (stretch factor 5)  │
│     [FILTERING tab | EXPORTING tab]     │
└─────────────────────────────────────────┘
         C) ACTION BAR (position configurable)
```

- **Minimum dock size:** 356 × 317 px
- **Font:** Segoe UI, 8–12pt depending on element
- **All buttons:** `PointingHandCursor`
- **Sidebar columns** (`widget_exploring_keys`, `widget_filtering_keys`, `widget_exporting_keys`): 38–48px wide

---

## A) EXPLORING ZONE (`frame_exploring`)

The top section. Used to **browse and select features** from a layer before filtering.

### Layout

```
┌────────────┬──────────────────────────────────────────┐
│            │  ┌── SINGLE SELECTION (GroupBox) ──────┐ │
│  SIDEBAR   │  │  QgsFeaturePickerWidget              │ │
│  (6 btns)  │  │  QgsFieldExpressionWidget            │ │
│            │  └─────────────────────────────────────┘ │
│            │  ┌── MULTIPLE SELECTION (GroupBox) ────┐ │
│            │  │  (collapsed by default)              │ │
│            │  └─────────────────────────────────────┘ │
│            │  ┌── CUSTOM SELECTION (GroupBox) ──────┐ │
│            │  │  (collapsed by default)              │ │
│            │  └─────────────────────────────────────┘ │
└────────────┴──────────────────────────────────────────┘
```

---

### A1) Left Sidebar — Exploring Buttons

Six 32×32px square buttons, stacked vertically.

#### 1. Identify
- **Icon:** `identify_alt.png`
- **Checkable:** ❌ No (one-shot action)
- **Action:** Opens the QGIS **Identify Results** dialog for the currently selected feature in the picker.
- **Use:** Inspect all attribute fields of a feature without opening the attribute table.

#### 2. Zoom
- **Icon:** `zoom.png`
- **Checkable:** ❌ No (one-shot action)
- **Action:** Zooms and pans the QGIS map canvas to the **extent of the selected feature**.
- **Use:** Quickly jump to a feature on the map.

#### 3. Select
- **Icon:** `select_black.png`
- **Checkable:** ✅ Yes (toggle)
- **Action (ON):** Selects the current feature(s) on the map canvas (highlights them in yellow/blue).
- **Action (OFF):** Deselects features.
- **Use:** Visually highlight which feature you're working with on the map.

#### 4. Track
- **Icon:** `track.png`
- **Checkable:** ✅ Yes (toggle)
- **Action (ON):** **Auto-zooms** the map every time the selected feature changes in the picker.
- **Use:** Useful when browsing through features one by one — the map follows your selection automatically.

#### 5. Link
- **Icon:** `link.png`
- **Checkable:** ✅ Yes (toggle)
- **Action (ON):** **Links** all Exploring GroupBoxes together — changing selection in one updates the others.
- **Use:** Keep Single, Multiple, and Custom selection widgets in sync.

#### 6. Reset
- **Icon:** `reset_properties.png`
- **Checkable:** ❌ No (one-shot action)
- **Action:** **Resets all exploring properties** for the current layer — clears selections, toggles, etc.
- **Use:** Start fresh without reloading the plugin.

---

### A2) Right Content Area — Selection GroupBoxes

Three **QgsCollapsibleGroupBox** panels. Each has:
- A **checkbox** (left of title): enables/disables that selection mode
- A **collapse arrow** (right of title): shows/hides the content without disabling it

Only one selection mode should be active at a time.

---

#### GroupBox 1: SINGLE SELECTION
- **Default state:** Expanded ✅ + Checked ✅
- **Widgets:**
  - **QgsFeaturePickerWidget** — A searchable dropdown that lists features from the source layer.
    - Type to search by display field value
    - Browse buttons (← →) to step through features
    - Loads up to **10,000 features** maximum
    - Shows the selected feature's display value
  - **QgsFieldExpressionWidget** — Choose which field (or expression) to use as the **display label** in the picker above.
    - Example: set to `"name"` to show city names instead of feature IDs

**What it does:** Select exactly ONE feature at a time to use as the spatial reference for filtering.

---

#### GroupBox 2: MULTIPLE SELECTION
- **Default state:** Collapsed ❌ + Unchecked ❌
- **Widgets:**
  - **QgsCheckableComboBoxFeaturesListPickerWidget** — A checkable combobox where you can **tick multiple features** from the list.
    - Each item shows the feature's display value
    - Check any combination of features
  - **QgsFieldExpressionWidget** — Same as above: controls the display label shown in the list.

**What it does:** Select MULTIPLE features simultaneously to use as the spatial reference. The filter will use the union of their geometries.

---

#### GroupBox 3: CUSTOM SELECTION
- **Default state:** Collapsed ❌ + Unchecked ❌
- **Widgets:**
  - **QgsFieldExpressionWidget** — A free-form QGIS expression editor.
    - Write any valid QGIS expression, e.g.: `"population" > 10000`
    - Supports all QGIS expression functions
    - Has syntax highlighting and auto-complete

**What it does:** Filter by an arbitrary expression instead of picking features from a list. No geometry-based selection needed — the expression IS the filter.

---

## B) TOOLBOX ZONE (`frame_toolset`)

The bottom section. A **QToolBox** with three tabs:
- **FILTERING** (icon: `filter_multi.png`)
- **EXPORTING** (icon: not specified but present)

Each tab uses the same layout pattern: left sidebar of toggle buttons + right content area.

---

## B1) FILTERING TAB

Controls **how** to spatially filter layers.

### Layout

```
┌──────────────┬──────────────────────────────────────────┐
│              │  Source Layer: [combobox] [centroid □]   │
│  SIDEBAR     │  Target Layers: [checkable combobox]     │
│  (6 toggles) │  Combine Operator: [src op] [tgt op]     │
│              │  Geometric Predicates: [checkable combo] │
│              │  Buffer Value: [spinbox] [expr override] │
│              │  Buffer Type: [combobox]                 │
│              │  Buffer Segments: [spinbox]              │
└──────────────┴──────────────────────────────────────────┘
```

---

### B1a) Left Sidebar — Filtering Toggle Buttons

Six 32×32px **checkable toggle** buttons. Turning a toggle ON **shows** the corresponding widget in the right area; turning it OFF **hides** it (and usually disables that feature).

#### 1. Auto Current Layer
- **Icon:** `auto_layer_white.png`
- **Checkable:** ✅ Yes
- **Action (ON):** The **Source Layer** combobox automatically updates to match whichever layer is selected in the QGIS Layers Panel.
- **Use:** Quickly filter based on whatever layer you're working on without manually switching the source layer.

#### 2. Layers to Filter
- **Icon:** `layers.png`
- **Checkable:** ✅ Yes
- **Action (ON):** Shows the **Target Layers** checkable combobox in the right area, allowing you to pick which layers will be filtered.
- **Action (OFF):** Hides target layers — filtering applies only to the source layer itself.
- **Use:** Multi-layer filtering. Enable this to filter OTHER layers based on the source geometry.

#### 3. Combine Operator
- **Icon:** `add_multi.png`
- **Checkable:** ✅ Yes
- **Action (ON):** Shows two **AND/OR dropdowns** to control how filter conditions are combined.
- **Use:** Control boolean logic when filtering with multiple features or across multiple layers.

#### 4. Geometric Predicates
- **Icon:** `geo_predicates.png`
- **Checkable:** ✅ Yes
- **Action (ON):** Shows the **Geometric Predicates** checkable combobox.
- **Use:** Choose which spatial relationship(s) to test (intersects, within, contains, etc.).

#### 5. Buffer Value
- **Icon:** `buffer_value.png`
- **Checkable:** ✅ Yes
- **Action (ON):** Shows the **Buffer Value** spinbox and expression override button.
- **Use:** Apply a distance buffer around the source geometry before filtering. Units depend on the layer's CRS.

#### 6. Buffer Type
- **Icon:** `buffer_type.png`
- **Checkable:** ✅ Yes
- **Action (ON):** Shows the **Buffer Type** combobox and **Buffer Segments** spinbox.
- **Use:** Control the shape of the buffer geometry (round, flat, square corners, etc.).

---

### B1b) Right Content Area — Filtering Widgets

Widgets appear/disappear based on which sidebar toggles are ON.

#### Source Layer
- **Widget:** `QgsMapLayerComboBox`
- **Filter:** Only shows vector layers **with geometry** (no geometry-less tables)
- **Always visible**
- Select the layer whose geometry will be used as the spatial reference for filtering.

#### Centroid (Source)
- **Widget:** Checkbox with icon `centroid.png`
- **Next to:** Source Layer combobox
- **Action:** When checked, uses the **centroid** (center point) of the source geometry instead of the full geometry.
- **Trade-off:** Faster computation, but less spatially precise.

#### Target Layers
- **Widget:** Checkable combobox
- **Visible when:** "Layers to Filter" toggle is ON
- Lists all vector layers in the project. Check any layers that should be filtered.
- The source layer itself is typically excluded or marked separately.

#### Centroid (Target)
- **Widget:** Checkbox with icon `centroid.png`
- **Visible when:** "Layers to Filter" toggle is ON
- Uses centroids of target layer features for the spatial test instead of full geometries.

#### Combine Operators
- **Visible when:** "Combine Operator" toggle is ON
- **Two separate dropdowns (ComboBox: AND / OR):**
  - **Source layer operator:** Combines conditions when multiple features are selected on the source layer (e.g., feature A OR feature B)
  - **Other layers operator:** Combines the filter conditions across the different target layers

#### Geometric Predicates
- **Widget:** Checkable combobox
- **Visible when:** "Geometric Predicates" toggle is ON
- **Options (check any combination):**
  - `intersects` — features that share any space
  - `contains` — target features that fully contain source
  - `within` — target features fully inside source
  - `touches` — features that share a boundary but not interior
  - `crosses` — features whose interiors intersect but neither contains the other
  - `overlaps` — features of same dimension that partially overlap
  - `disjoint` — features with NO spatial relationship (opposite of intersects)

#### Buffer Value
- **Widget:** `QgsDoubleSpinBox` (decimal number input)
- **Visible when:** "Buffer Value" toggle is ON
- **Units:** Map units of the source layer CRS (could be meters, feet, degrees)
- **PropertyOverrideButton:** Yellow "data-defined override" button next to the spinbox. Click to write a QGIS expression that dynamically calculates the buffer distance (e.g., from a field value like `"buffer_dist"`).
- Enter the distance zone to expand the source geometry before applying the spatial test.

#### Buffer Type
- **Widget:** ComboBox
- **Visible when:** "Buffer Type" toggle is ON
- Controls the geometry shape of the buffer (e.g., round ends, flat ends, square corners).

#### Buffer Segments
- **Widget:** `QgsSpinBox` (integer)
- **Visible when:** "Buffer Type" toggle is ON
- Controls how many segments approximate a circle in the buffer. Higher = smoother but slower.

---

## B2) EXPORTING TAB

Controls **what and where** to export.

### Layout

```
┌──────────────┬──────────────────────────────────────────┐
│              │  Layers: [checkable combobox]            │
│  SIDEBAR     │  Projection: [CRS selector]              │
│  (6 toggles) │  Styles: [combobox]                      │
│              │  Datatype: [combobox]                    │
│              │  Output Folder: [path] [browse btn]      │
│              │  Zip: [path] [browse btn]                │
│              │  [batch checkboxes]                      │
└──────────────┴──────────────────────────────────────────┘
```

---

### B2a) Left Sidebar — Exporting Toggle Buttons

Six 32×32px **checkable toggle** buttons. Each shows/hides its corresponding export option.

#### 1. Layers
- **Icon:** `layers.png`
- **Action (ON):** Shows the **Layers** checkable combobox to select which layers to include in the export.

#### 2. Projection
- **Icon:** `projection_black.png`
- **Action (ON):** Shows the **Projection selector** to choose an output CRS for the export.
- If not set, uses each layer's native CRS.

#### 3. Styles
- **Icon:** `styles_black.png`
- **Action (ON):** Shows the **Styles** option. Include QGIS layer styles (symbology, labels, etc.) in the export.

#### 4. Datatype
- **Icon:** `datatype.png`
- **Action (ON):** Shows the **output format** selector (GeoPackage is the primary format; others may be available).

#### 5. Output Folder
- **Icon:** `folder_black.png`
- **Action (ON):** Shows the **output folder path** input and file browser button.

#### 6. Zip
- **Icon:** `zip.png`
- **Action (ON):** Shows the **ZIP output path** input and browse button. Compresses the export into a `.zip` file.

---

### B2b) Right Content Area — Exporting Widgets

#### Layers Checkable Combobox
- Lists all vector layers in the project
- Check which layers to include in the export
- Visible when "Layers" toggle is ON

#### Projection Selector
- **Widget:** `QgsProjectionSelectionWidget`
- Choose the CRS for the exported layers (e.g., reproject to EPSG:4326)
- Visible when "Projection" toggle is ON

#### Styles Combobox
- Choose how to include styles (embedded, external, etc.)
- Visible when "Styles" toggle is ON

#### Datatype Combobox
- Select output format (primarily GeoPackage `.gpkg`)
- Visible when "Datatype" toggle is ON

#### Output Folder
- **Widget:** LineEdit + file dialog button
- Type or browse to the folder where the export will be saved
- **Batch checkbox:** Export each layer as a separate file in the folder
- Visible when "Output Folder" toggle is ON

#### Zip Path
- **Widget:** LineEdit + file dialog button
- Path for the ZIP archive containing the export
- **Batch checkbox:** Create a separate ZIP per layer
- Visible when "Zip" toggle is ON

---

## C) ACTION BAR

A row of **6 main action buttons**. Position is configurable: **top / bottom / left / right** of the dock panel.

These are the primary "do it" buttons. All other UI elements configure _what_ these buttons will do.

| # | Button | Icon | Checkable | Action |
|---|---|---|---|---|
| 1 | **Filter** | `filter.png` | ❌ | Apply the current filter configuration to the selected layers |
| 2 | **Undo** | `undo.png` | ❌ | Undo the last filter operation (restores previous filter state) |
| 3 | **Redo** | `redo.png` | ❌ | Redo a previously undone filter |
| 4 | **Unfilter** | `unfilter.png` | ❌ | Remove ALL active filters from ALL layers (full reset) |
| 5 | **Export** | `export.png` | ❌ | Export using the current Exporting tab configuration |
| 6 | **About** | `icon.png` | ❌ | Opens the FilterMate project page (website/documentation) |

**Notes:**
- **Filter** button is **disabled** if no valid configuration exists (need at least: source layer + selection OR custom expression)
- **Export** button is **disabled** if no export path or layers are configured
- **Undo/Redo** are disabled when there is nothing to undo/redo

---

## Other UI Elements

### Backend Indicator
- A small **clickable label/widget** showing the current active backend name for the source layer:
  - `PostgreSQL`, `Spatialite`, `OGR`, or `Memory`
- **Right-click** (or click): Opens a context menu to **force a specific backend** for the current layer.
- Useful for: troubleshooting filter issues, benchmarking backend performance.

### History Widget
- Shows the **filter history** — a log of all applied filters in the session.
- Navigate through history for undo/redo reference.
- Displayed as a scrollable list of past filter states.

### Favorites Widget
- Accessed via a **star button** (⭐) in the UI.
- Opens the **Favorites Manager dialog**:
  - Browse, search, and manage saved filter configurations
  - Apply a saved favorite to instantly restore a filter setup
  - Delete or rename favorites

### Configuration Tree View
- An advanced widget showing the current plugin configuration as a **JSON tree**.
- Allows direct editing of config values for power users.
- Not intended for regular use — prefer the normal UI.

### Theme Support
- FilterMate detects the QGIS theme (dark or light).
- **Dark mode:** Icons with `_black` in their filename are swapped for `_white` variants (and vice versa). Other icons are inverted automatically.
- If icons look wrong after a theme switch, restart the plugin (disable/re-enable in Plugin Manager).

---

## Summary: Toggle Visibility Map

| Sidebar Toggle | Widget(s) It Shows/Hides |
|---|---|
| Auto Current Layer | (no widget — modifies source layer combobox behavior) |
| Layers to Filter | Target Layers combobox + target Centroid checkbox |
| Combine Operator | Source operator dropdown + Other layers operator dropdown |
| Geometric Predicates | Geometric predicates checkable combobox |
| Buffer Value | Buffer Value spinbox + PropertyOverrideButton |
| Buffer Type | Buffer Type combobox + Buffer Segments spinbox |
| Layers (Export) | Layers checkable combobox |
| Projection (Export) | CRS projection selector |
| Styles (Export) | Styles combobox |
| Datatype (Export) | Format combobox |
| Output Folder (Export) | Folder path LineEdit + browse button + batch checkbox |
| Zip (Export) | Zip path LineEdit + browse button + batch checkbox |

---

## Dynamic Widget Behaviors & Interactions

This section documents how widgets are **dynamically created, linked, enabled/disabled** at runtime — behaviors not visible in the static `.ui` file.

### Dynamically Created Widgets (not in Qt Designer)

These widgets are created in `setupUiCustom()` at startup, NOT defined in the `.ui` file:

| Widget | Type | Where Inserted |
|---|---|---|
| `checkableComboBoxFeaturesListPickerWidget_exploring_multiple_selection` | `QgsCheckableComboBoxFeaturesListPickerWidget` | Into `horizontalLayout_exploring_multiple_feature_picker` (Multiple Selection GroupBox) |
| `checkableComboBoxLayer_filtering_layers_to_filter` | `QgsCheckableComboBoxLayer` | Into `verticalLayout_filtering_values` at position 2 (with centroid checkbox in HBoxLayout) |
| `checkableComboBoxLayer_exporting_layers` | `QgsCheckableComboBoxLayer` | Into `verticalLayout_exporting_values` at position 0 |
| `checkBox_filtering_use_centroids_distant_layers` | `QCheckBox` | Next to target layers combobox (in shared HBoxLayout) |
| `frame_header` | `QFrame` (13px high) | Inserted at top of `verticalLayout_8` (position 0, above everything) |
| `favorites_indicator_label` | `ClickableLabel` | Inside `frame_header`, right-aligned |
| `backend_indicator_label` | `ClickableLabel` | Inside `frame_header`, right-aligned, next to favorites |

### Header Bar (frame_header)

A thin 13px-high bar at the very top of the dock widget containing:
- A spacer pushing items to the right
- **★ Favorites indicator** — Orange "mousse" pill button (gold `#f5b041`, hover `#f39c12`), 32px wide. Click opens Favorites Manager dialog.
- **Backend indicator** — Blue "mousse" pill button (blue `#5dade2`, hover `#3498db`), 38px wide. Shows current backend name ("OGR", "PostgreSQL", etc.) or "..." when no layers loaded. Click opens backend selection menu.

### Exploring GroupBox Exclusive Behavior

The 3 exploring GroupBoxes (**Single**, **Multiple**, **Custom Selection**) are **mutually exclusive**:
- When you **check** one GroupBox → the other two are automatically **unchecked and collapsed**
- Only ONE selection mode can be active at a time
- Checking a GroupBox also expands it; unchecking collapses it
- This is enforced by `_force_exploring_groupbox_exclusive()` with signal blocking to prevent cascading events

### Tab-Switching & Action Button States

When switching tabs in the QToolBox:

| Active Tab | Filter btn | Undo btn | Redo btn | Unfilter btn | Export btn |
|---|---|---|---|---|---|
| **FILTERING** (index 0) | ✅ Enabled | ✅ Enabled | ✅ Enabled | ✅ Enabled | ❌ Disabled |
| **EXPORTING** (index 1) | ❌ Disabled | ❌ Disabled | ❌ Disabled | ❌ Disabled | ✅ Enabled |
| **CONFIGURATION** (index 2) | ❌ Disabled | ❌ Disabled | ❌ Disabled | ❌ Disabled | ❌ Disabled |
| **About** button | Always ✅ | | | | |

### Toggle → Widget Enable/Disable Mappings

Every sidebar toggle button controls the **enabled state** of its associated widgets. When a toggle is OFF, the corresponding widgets are **grayed out/disabled** (not hidden):

**FILTERING section:**
| Toggle Button | Controls (enables/disables) |
|---|---|
| Auto Current Layer | *(no associated widgets)* |
| Layers to Filter | `checkableComboBoxLayer_filtering_layers_to_filter` + `checkBox_filtering_use_centroids_distant_layers` |
| Combine Operator | `comboBox_filtering_source_layer_combine_operator` + `comboBox_filtering_other_layers_combine_operator` |
| Geometric Predicates | `comboBox_filtering_geometric_predicates` |
| Buffer Value | `mQgsDoubleSpinBox_filtering_buffer_value` + `mPropertyOverrideButton_filtering_buffer_value_property` |
| Buffer Type | `comboBox_filtering_buffer_type` + `mQgsSpinBox_filtering_buffer_segments` |

**EXPORTING section:**
| Toggle Button | Controls (enables/disables) |
|---|---|
| Layers | `checkableComboBoxLayer_exporting_layers` |
| Projection | `mQgsProjectionSelectionWidget_exporting_projection` |
| Styles | `comboBox_exporting_styles` |
| Datatype | `comboBox_exporting_datatype` |
| Output Folder | `lineEdit_exporting_output_folder` + `checkBox_batch_exporting_output_folder` |
| Zip | `lineEdit_exporting_zip` + `checkBox_batch_exporting_zip` |

### Always-Enabled Widgets

These widgets remain **always enabled** regardless of toggle states:
- `comboBox_filtering_current_layer` (source layer — must always be selectable)
- `checkBox_filtering_use_centroids_source_layer` (source centroid option)
- `pushButton_checkable_exporting_output_folder` (always clickable to browse)
- `pushButton_checkable_exporting_zip` (always clickable to browse)

### Buffer Buttons Dependency Chain

Buffer options have an extra dependency:
- **Buffer Value** and **Buffer Type** toggle buttons are **disabled** unless **Geometric Predicates** is checked
- If Geometric Predicates is unchecked → both buffer buttons are forced unchecked AND disabled
- This prevents users from configuring a buffer without spatial predicates (which would be meaningless)

```
Geometric Predicates ON  →  Buffer Value btn enabled  →  Buffer spinbox enabled
                         →  Buffer Type btn enabled   →  Buffer type combo enabled
                                                       →  Buffer segments enabled
Geometric Predicates OFF →  Buffer Value btn DISABLED + UNCHECKED
                         →  Buffer Type btn DISABLED + UNCHECKED
                         →  All buffer widgets DISABLED
```

### Buffer Value Expression Override

When the **PropertyOverrideButton** next to Buffer Value is activated (data-defined expression):
- The buffer spinbox is **disabled** (expression overrides manual value)
- The PropertyOverrideButton remains enabled
- Expression is evaluated per-feature at filter time (dynamic buffer distances)

### Auto Current Layer Sync

When **Auto Current Layer** toggle is ON:
- Clicking a layer in the QGIS **Layers Panel** (layer tree view) automatically changes the source layer in FilterMate
- The layer change is treated as a "manual change" to bypass protection windows
- When OFF, the source layer in FilterMate is independent of the QGIS panel selection

### Export Buttons Initialization

All 6 exporting sidebar buttons start **disabled** at initialization. They become enabled only after the plugin fully loads and layers are available. This prevents premature export configuration.

### Layer Type Filtering

The source layer combobox (`comboBox_filtering_current_layer`) is filtered to show only vector layers **with geometry** (`HasGeometry` = Point + Line + Polygon). Non-spatial tables are excluded.

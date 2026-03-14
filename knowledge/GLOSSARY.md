# FilterMate — Glossary

Definitions for all key terms used in FilterMate's UI, documentation, and codebase. Ordered alphabetically.

---

## Action Bar
The row of 6 main action buttons (Filter, Undo, Redo, Unfilter, Export, About). Position is configurable: top, bottom, left, or right of the dock panel. These are the "do it" buttons — everything else in the UI configures what they will do.

---

## Auto Current Layer
A toggle in the FILTERING TAB sidebar. When ON, the Source Layer combobox automatically follows the currently selected layer in the QGIS Layers Panel. Avoids manually switching the source layer when you're working on different layers.

---

## Backend
The internal query engine FilterMate uses to build and execute spatial queries. Each backend translates FilterMate's filter configuration into the appropriate SQL or expression syntax for the data source.

**Available backends:**

| Backend | Best For | How It Works |
|---|---|---|
| `PostgreSQL` | PostGIS layers | Native PostgreSQL/PostGIS spatial SQL |
| `Spatialite` | `.sqlite` / `.gpkg` files | Spatialite spatial SQL |
| `OGR` | Shapefiles, WFS, most others | GDAL/OGR expression syntax |
| `Memory` | In-memory / scratch layers | QGIS memory layer expressions |

FilterMate **auto-selects** the best backend based on the data source. You can **override** it per layer via the Backend Indicator widget.

---

## Backend Indicator
A small clickable widget in the FilterMate panel showing the current backend name for the active layer. Right-clicking (or clicking) opens a context menu to force a specific backend. Useful for troubleshooting and performance comparison.

---

## Buffer
A distance zone expanded around a geometry. In FilterMate, you set a buffer distance (in map units) around the source geometry before applying the spatial predicate. 

- **Buffer Value:** The numeric distance (e.g., `500` for 500 meters in a metric CRS)
- **Buffer Type:** The geometry shape of the buffer (round, square, flat ends)
- **Buffer Segments:** How many straight segments approximate the curved parts of the buffer (higher = smoother circle, more processing)

> ⚠️ Buffer units depend on the layer's CRS. Projected CRS (e.g., UTM) = meters. Geographic CRS (e.g., WGS84) = degrees. Always check your CRS before setting a buffer.

---

## Centroid
When the Centroid checkbox is enabled, FilterMate uses the **center point** of geometries for spatial operations instead of the full polygon/line geometry.

- **Faster** — point-to-geometry tests are much cheaper than polygon-to-polygon
- **Less precise** — a centroid may fall inside a geometry even if the full geometry barely overlaps, or vice versa
- Available separately for Source Layer and Target Layers

---

## Combine Operator
AND/OR logic dropdowns that control how filter conditions are combined when there are multiple source features or target layers.

- **Source layer operator:** If multiple features are selected on the source layer, this controls whether features must be near ALL of them (AND) or ANY of them (OR).
- **Other layers operator:** Controls how conditions are combined across the different target layers being filtered.

Shown/hidden by the **Combine Operator** toggle in the FILTERING TAB sidebar (icon: `add_multi.png`).

---

## Configuration Tree View
An advanced JSON tree view widget showing the current FilterMate configuration in raw JSON format. Allows direct editing for power users who want to tweak settings not exposed in the normal UI. Not intended for routine use.

---

## Custom Selection
The third GroupBox in the EXPLORING ZONE. Instead of selecting features from a list, you write any valid **QGIS expression** directly. FilterMate uses that expression as the filter condition.

- Expression example: `"population" > 1000000`
- Uses `QgsFieldExpressionWidget` (QGIS's built-in expression editor with syntax highlighting and autocomplete)
- Default state: collapsed and unchecked

---

## Display Expression
A QGIS layer property that controls how features are displayed in pickers and dropdowns. Set in Layer Properties → Display tab → "Display Name" expression. FilterMate uses this as **Priority 1** when selecting the display field for the feature picker — it overrides all automatic field detection. Setting this in QGIS layer properties is the most reliable way to control what FilterMate shows in the Single Selection picker.

---

## Dock Widget
The UI container that holds the entire FilterMate interface. A `QDockWidget` in Qt terminology. Can be docked to any side of QGIS or floated as a standalone window.

---

## Feedback Level
A configuration setting that controls the verbosity of QGIS message bar notifications from FilterMate. Three levels:
- **minimal** — only errors, warnings, performance warnings, and export success messages
- **normal** *(default)* — above + generic success messages and export results
- **verbose** — everything, including filter counts, undo/redo confirmations, backend info, config changes, layer loading details, and initialization info

Configurable in the CONFIGURATION tab. See [FEEDBACK.md](FEEDBACK.md) for the full category matrix.

---

## Exploring Zone
The top section of the FilterMate panel (`frame_exploring`). Used to **browse and select features** from a layer. Contains three selection GroupBoxes (Single, Multiple, Custom) and a sidebar with exploration tools (Identify, Zoom, Select, Track, Link, Reset).

---

## Export
One of the 6 Action Bar buttons. Triggers the export process using the current EXPORTING TAB configuration. Produces a GeoPackage (or other format) with embedded QGIS project.

---

## Favorites
Saved filter configurations that can be loaded and reapplied later. Each favorite stores:
- Source layer reference
- Target layer references
- Filter settings (predicates, buffer, operators)
- Spatial context (map extent at time of saving)

Accessed via the **star button** (⭐) which opens the Favorites Manager dialog. Favorites persist between QGIS sessions and can be shared between users.

---

## Filter
The primary action in FilterMate. Clicking the **Filter** button in the Action Bar applies the current configuration — it modifies the **Subset String** of affected layers to show only features matching the spatial/attribute criteria.

---

## Filter Chaining
A technique where you apply multiple filters sequentially, using dynamic buffer expressions that reference values from a previously filtered layer. Enables complex multi-step spatial analysis workflows.

---

## Geometric Predicate
A spatial relationship test between two geometries. FilterMate supports:

| Predicate | Meaning |
|---|---|
| `intersects` | Geometries share any space (most common) |
| `contains` | Source geometry fully contains the target |
| `within` | Target geometry is fully inside the source |
| `touches` | Geometries share a boundary but not interior space |
| `crosses` | Interiors intersect but neither fully contains the other (lines/polygons) |
| `overlaps` | Same-dimension geometries partially overlap |
| `disjoint` | No spatial relationship at all (opposite of intersects) |

Multiple predicates can be checked simultaneously — a feature passes if it satisfies ANY of the checked predicates.

---

## GeoPackage
The primary export format for FilterMate. A `.gpkg` file is an SQLite database that stores vector layers, styles, and can include an embedded QGIS project. Preserves: layer groups, symbology, CRS, labels.

---

## GroupBox
A collapsible/checkable panel in the EXPLORING ZONE. Each GroupBox has:
- **Checkbox** (left of title): Enables/disables that selection mode
- **Collapse arrow** (right of title): Shows/hides the content area (without disabling the mode)

The three GroupBoxes are: SINGLE SELECTION, MULTIPLE SELECTION, CUSTOM SELECTION.

---

## History Widget
A widget showing the log of all filter operations applied in the current session. Enables navigation through filter history for undo/redo purposes.

---

## Identify
One of the 6 sidebar buttons in the EXPLORING ZONE (icon: `identify_alt.png`). Opens the QGIS Identify Results dialog for the currently selected feature. Shows all attribute values. NOT checkable — it's a one-shot action button.

---

## Layer Lifecycle
The process by which FilterMate tracks layers as they are added to or removed from the QGIS project. Key behaviors:
- Layers are **batched on add** (500ms accumulation window) to prevent rapid-fire processing during project load
- On add: properties are restored from the SQLite database, display field is auto-detected, comboboxes updated
- On remove: `PROJECT_LAYERS[layer_id]` entry is cleaned up, running tasks cancelled, comboboxes updated

See [LIFECYCLE.md](LIFECYCLE.md) for the full event sequence.

---

## Link
A toggle button in the EXPLORING ZONE sidebar (icon: `link.png`). When ON, synchronizes all three selection GroupBoxes — changing the selection in one (Single/Multiple/Custom) updates the others to match.

---

## Materialized View
A temporary PostgreSQL table created by FilterMate for complex spatial queries involving many source features (>500 FIDs). FilterMate creates the materialized view, runs the spatial query against it, then cleans it up afterwards. This avoids passing large IN-lists directly in SQL and improves query plan efficiency for large selections. If cleanup fails, a "Schema cleanup failed" warning is shown.

---

## Memory Layer
A temporary, in-memory vector layer in QGIS (also called a "scratch layer"). FilterMate uses a dedicated Memory backend for these layers.

---

## Message Bar
QGIS's notification system displayed at the top of the main window, just below the menu bar. FilterMate uses the message bar for all user feedback — successes, warnings, errors, and info messages. Color-coded by severity (green/yellow/red/blue). Verbosity is controlled by the Feedback Level setting. All messages are also mirrored to the QGIS Log Messages panel regardless of level.

---

## Multiple Selection
The second GroupBox in the EXPLORING ZONE. Shows a **checkable combobox** (`QgsCheckableComboBoxFeaturesListPickerWidget`) where you can select MULTIPLE features simultaneously by checking them in a list. The union of their geometries is used for filtering. Default state: collapsed and unchecked.

---

## OGR
The GDAL/OGR library. FilterMate's OGR backend provides broad compatibility for data sources not covered by the PostgreSQL or Spatialite backends (shapefiles, WFS, CSV, etc.).

---

## Progressive Filtering
A two-phase filtering strategy used by FilterMate for complex PostgreSQL queries:
- **Phase 1 (fast):** Applies a bounding box spatial filter to reduce the candidate set quickly
- **Phase 2 (precise):** Applies the actual geometry predicate (intersects, contains, etc.) to the reduced Phase 1 result set

This avoids running expensive precise geometry tests against every feature in a large table. Phase 1 leverages spatial indexes; Phase 2 is only run on the much smaller filtered set.

---

## PropertyOverrideButton
The **data-defined override button** — a small yellow button with a "⊕" or similar icon, appearing next to the Buffer Value spinbox. Clicking it lets you replace the fixed buffer value with a **QGIS expression** that is evaluated dynamically per feature (e.g., use a field value `"buffer_radius"` as the buffer distance). Also called a "data-defined button" in QGIS terminology.

---

## Reset
A button in the EXPLORING ZONE sidebar (icon: `reset_properties.png`). Resets all exploring properties for the current layer — clears selections, turns off toggles (Track, Select, Link), etc. NOT checkable — one-shot action.

---

## Select
A toggle button in the EXPLORING ZONE sidebar (icon: `select_black.png`). When ON, the feature currently selected in the picker is also **selected on the QGIS map canvas** (highlighted). Toggling OFF deselects features on the canvas.

---

## Single Selection
The first (and default active) GroupBox in the EXPLORING ZONE. Shows a `QgsFeaturePickerWidget` — a searchable dropdown to pick ONE feature at a time. Browse with ← → buttons. Display field is controlled by a `QgsFieldExpressionWidget` below the picker. Default state: expanded and checked.

---

## Source Layer
The reference layer in the FILTERING TAB. Its geometry (or the geometry of selected features within it) is used as the spatial reference for filtering target layers. Only vector layers with geometry are available.

---

## Splitter
The vertical divider between the EXPLORING ZONE and the TOOLBOX ZONE. Drag it up or down to resize the two zones. The handle is 6px wide. It is NOT collapsible (you can't fully hide either zone by dragging).

---

## Streaming Export
An export mode automatically activated for large datasets (>10 000 features). Instead of loading all features into memory at once, FilterMate processes and writes them in **chunks of 5 000 features**. This prevents memory exhaustion when exporting large PostGIS tables or GeoPackages. Transparent to the user — the output is identical to a non-streaming export.

---

## Subset String
QGIS's internal mechanism for filtering vector layers. It's a SQL `WHERE` clause applied to the layer's data provider. When FilterMate "filters" a layer, it sets the layer's Subset String. When FilterMate "unfilters," it clears the Subset String.

Example subset string: `"fid" IN (1, 5, 42, 107)`

---

## Target Layers / Layers to Filter
The layers that will be filtered based on the Source Layer's geometry. Shown in a checkable combobox when the **Layers to Filter** toggle is ON. You can select multiple target layers at once. If not configured, filtering applies only to the source layer.

---

## Toolbox Zone
The bottom section of the FilterMate panel (`frame_toolset`). A `QToolBox` widget with three tabs: **FILTERING**, **EXPORTING**, and **CONFIGURATION**. FILTERING and EXPORTING each have a left sidebar of toggle buttons and a right content area. CONFIGURATION contains the JSON tree editor for advanced settings.

---

## Track
A toggle button in the EXPLORING ZONE sidebar (icon: `track.png`). When ON, the QGIS map canvas **automatically zooms** to the selected feature every time the selection changes in the picker. Useful for browsing features sequentially.

---

## Unfilter
One of the 6 Action Bar buttons (icon: `unfilter.png`). Removes ALL active filters from ALL layers in the project by clearing their Subset Strings. Full reset — returns all data to visible.

---

## ValueRelation
A QGIS field widget type where a field's values reference features from another layer (a lookup/reference table). FilterMate detects ValueRelation fields during display field selection and generates `represent_value()` expressions for them, so the feature picker shows the human-readable label (e.g., "Paris") instead of the raw foreign key integer (e.g., `75056`). Priority 2 in `get_best_display_field()`.

---

## Zoom
A button in the EXPLORING ZONE sidebar (icon: `zoom.png`). Zooms and pans the QGIS map canvas to fit the currently selected feature's bounding box. NOT checkable — one-shot action.

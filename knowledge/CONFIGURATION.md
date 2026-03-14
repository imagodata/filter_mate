# FilterMate — Configuration Reference

> Everything that can be configured in FilterMate, from user-facing settings to performance tuning.
> Configuration lives in `config/config.json` and is editable via the Configuration Tree View in the UI.

---

## Configuration File

**Path:** `config/config.json`
**Format:** JSON, version 2.0
**Editable via:** Configuration Tree View (advanced JSON tree in the UI) or direct file editing

Structure:
```
config.json
├── _CONFIG_VERSION: 2.0
├── _CONFIG_META: { description, version, last_updated }
├── APP/
│   ├── AUTO_ACTIVATE: { value, description }
│   ├── DOCKWIDGET/
│   │   ├── FEEDBACK_LEVEL
│   │   ├── LANGUAGE
│   │   ├── UI_PROFILE
│   │   ├── DOCK_POSITION
│   │   ├── ACTION_BAR_POSITION
│   │   ├── ACTION_BAR_VERTICAL_ALIGNMENT
│   │   ├── PushButton/ (ICONS, ICONS_SIZES)
│   │   └── COLORS/ (ACTIVE_THEME, THEMES)
│   └── OPTIONS/
│       ├── Links (Discord, GitHub, QGIS plugin page)
│       ├── SMALL_DATASET_OPTIMIZATION
│       ├── AUTO_OPTIMIZATION
│       ├── PROGRESSIVE_FILTERING
│       ├── QUERY_CACHE
│       ├── PARALLEL_FILTERING
│       ├── STREAMING_EXPORT
│       ├── PERFORMANCE
│       ├── OPTIMIZATION_THRESHOLDS
│       ├── HISTORY
│       └── GEOMETRY_SIMPLIFICATION
└── CURRENT_PROJECT/
    ├── EXPORTING/ (default export settings)
    ├── OPTIONS/ (project-level settings)
    └── layers: []
```

---

## User-Facing Settings

### Language
- **Key:** `APP.DOCKWIDGET.LANGUAGE`
- **Default:** `auto` (uses QGIS locale)
- **Choices:** `auto`, `en`, `fr`, `de`, `es`, `it`, `nl`, `pt`, `pl`, `zh`, `ru`, `id`, `vi`, `tr`, `hi`, `fi`, `da`, `sv`, `nb`, `sl`, `tl`, `am`, `uz`
- **22 languages** at 100% translation coverage

### Feedback Level
- **Key:** `APP.DOCKWIDGET.FEEDBACK_LEVEL`
- **Default:** `normal`
- **Choices:**
  - `minimal` — Errors and warnings only
  - `normal` — Balanced: success messages, filter counts, undo/redo info
  - `verbose` — Everything: debug info, backend startup, config changes, layer loading

### UI Profile (Display Scaling)
- **Key:** `APP.DOCKWIDGET.UI_PROFILE`
- **Default:** `auto`
- **Choices:**
  - `auto` — Detects from screen resolution and DPI
  - `compact` — For screens < 1920×1080 (default on laptops)
  - `normal` — For standard displays ≥ 1920×1080
  - `hidpi` — For 4K/Retina displays (device pixel ratio > 1.5)
- **Auto-detection thresholds:**
  - Compact if width < 1920 or height < 1080
  - HiDPI if pixel ratio > 1.5 or physical width > 3840

### Dock Position
- **Key:** `APP.DOCKWIDGET.DOCK_POSITION`
- **Default:** `right`
- **Choices:** `left`, `right`, `top`, `bottom`

### Action Bar Position
- **Key:** `APP.DOCKWIDGET.ACTION_BAR_POSITION`
- **Default:** `bottom`
- **Choices:** `top`, `bottom`, `left`, `right`
- When `left` or `right`: buttons stack vertically

### Action Bar Vertical Alignment
- **Key:** `APP.DOCKWIDGET.ACTION_BAR_VERTICAL_ALIGNMENT`
- **Default:** `top`
- **Choices:** `top`, `bottom`
- Only applies when action bar is in vertical mode (left/right position)

### Color Theme
- **Key:** `APP.DOCKWIDGET.COLORS.ACTIVE_THEME`
- **Default:** `default`
- **Choices:** `auto` (detect from QGIS), `default`, `dark`, `light`
- **Theme source:** `config` (use configured), `qgis` (inherit from QGIS), `system` (OS theme)
- **3 built-in themes** with full color definitions: backgrounds, fonts, accents with hover/pressed states

### Auto-Activate
- **Key:** `APP.AUTO_ACTIVATE`
- **Default:** `false`
- When enabled, plugin auto-activates when opening a project with vector layers

---

## Performance & Optimization Settings

### Small Dataset Optimization
- **Key:** `APP.OPTIONS.SMALL_DATASET_OPTIMIZATION`
- **Default:** enabled, threshold 5000 features
- For PostgreSQL layers with fewer features than threshold, uses OGR memory backend (faster for small datasets)
- Method: `ogr_memory` (default) or `qgis_processing`
- `prefer_native_for_postgresql_project`: When all layers are PostgreSQL, stay on PostgreSQL backend

### Auto-Optimization
- **Key:** `APP.OPTIONS.AUTO_OPTIMIZATION`
- **Default:** enabled
- Intelligent automatic optimizations based on layer characteristics:
  - **Auto centroid for distant layers:** Threshold 5000 features
  - **Auto centroid for local layers:** Threshold 50000 features
  - **Auto simplify geometry:** Before and after buffer operations
  - **Auto strategy selection:** Picks best query strategy
  - **Optimization hints:** Show tips in message bar

### Progressive Filtering
- **Key:** `APP.OPTIONS.PROGRESSIVE_FILTERING`
- **Default:** enabled
- Two-phase filtering for complex queries on large PostgreSQL datasets:
  - Phase 1: Quick bounding box filter
  - Phase 2: Precise geometry filter on reduced dataset
  - Complexity threshold: 100 (minimum score to trigger)
  - Lazy cursor threshold: 50,000 features
  - Chunk size: 5000 IDs per batch

### Query Cache
- **Key:** `APP.OPTIONS.QUERY_CACHE`
- **Default:** enabled, max 100 entries, no TTL
- Caches built expressions to avoid rebuilding identical queries
- Also caches result counts and complexity scores

### Parallel Filtering
- **Key:** `APP.OPTIONS.PARALLEL_FILTERING`
- **Default:** enabled, min 2 layers, auto-detect workers
- Filters multiple target layers simultaneously using thread pool
- `max_workers: 0` = auto-detect based on CPU cores

### Streaming Export
- **Key:** `APP.OPTIONS.STREAMING_EXPORT`
- **Default:** enabled, threshold 10,000 features, chunk size 5000
- For large datasets, exports in batches to avoid memory issues

### Geometry Simplification
- **Key:** `APP.OPTIONS.GEOMETRY_SIMPLIFICATION`
- **Default:** enabled, max WKT 100,000 chars
- Automatically simplifies complex geometries when WKT exceeds threshold
- Preserves topology by default
- Tolerance range: 1m to 100m

### Optimization Thresholds
- **Key:** `APP.OPTIONS.OPTIMIZATION_THRESHOLDS`
- All-in-one threshold configuration:

| Threshold | Default | Purpose |
|---|---|---|
| `large_dataset_warning` | 50,000 | Show performance warning above this |
| `async_expression_threshold` | 10,000 | Use async expression building |
| `update_extents_threshold` | 50,000 | Auto-update layer extents below this |
| `centroid_optimization_threshold` | 5,000 | Auto-enable centroids above this |
| `exists_subquery_threshold` | 100,000 | Use EXISTS subquery for WKT > this chars |
| `source_mv_fid_threshold` | 500 | Max source FIDs for materialized views |
| `parallel_processing_threshold` | 100,000 | Use parallel processing above this |
| `progress_update_batch_size` | 100 | Features between progress bar updates |

### History (Undo/Redo)
- **Key:** `APP.OPTIONS.HISTORY`
- **Default:** max 100 entries, persist to disk
- `max_history_size`: Maximum undo/redo steps
- `persist_history`: Save history between sessions

---

## Project Settings (CURRENT_PROJECT)

### Export Defaults
Stored in `CURRENT_PROJECT.EXPORTING`:
- All `HAS_*` flags default to `false`
- Default projection: `EPSG:3857`
- Default style format: `QML`
- Default data format: `GPKG`
- Batch modes default to `false`

### Project Options
Stored in `CURRENT_PROJECT.OPTIONS`:
- `LAYERS.LINK_LEGEND_LAYERS_AND_CURRENT_LAYER_FLAG`: When true, QGIS layer panel changes update FilterMate source layer (same as Auto Current Layer toggle)
- `PROJECT_ID`, `PROJECT_PATH`: QGIS project references
- `ACTIVE_POSTGRESQL`, `IS_ACTIVE_POSTGRESQL`: PostgreSQL connection info

---

## Icon Configuration

### Button → Icon Mapping
Stored in `APP.DOCKWIDGET.PushButton.ICONS`:

**ACTION buttons:**
| Button | Icon |
|---|---|
| FILTER | `filter.png` |
| UNDO_FILTER | `undo.png` |
| REDO_FILTER | `redo.png` |
| UNFILTER | `unfilter.png` |
| EXPORT | `export.png` |
| ABOUT | `icon.png` |

**EXPLORING buttons:**
| Button | Icon |
|---|---|
| IDENTIFY | `identify_alt.png` |
| ZOOM | `zoom.png` |
| IS_SELECTING | `select_black.png` |
| IS_TRACKING | `track.png` |
| IS_LINKING | `link.png` |
| RESET_ALL_LAYER_PROPERTIES | `reset_properties.png` |

**FILTERING buttons:**
| Button | Icon |
|---|---|
| AUTO_CURRENT_LAYER | `auto_layer_white.png` |
| HAS_LAYERS_TO_FILTER | `layers.png` |
| HAS_COMBINE_OPERATOR | `add_multi.png` |
| HAS_GEOMETRIC_PREDICATES | `geo_predicates.png` |
| HAS_BUFFER_VALUE | `buffer_value.png` |
| HAS_BUFFER_TYPE | `buffer_type.png` |

**EXPORTING buttons:**
| Button | Icon |
|---|---|
| HAS_LAYERS_TO_EXPORT | `layers.png` |
| HAS_PROJECTION_TO_EXPORT | `projection_black.png` |
| HAS_STYLES_TO_EXPORT | `styles_black.png` |
| HAS_DATATYPE_TO_EXPORT | `datatype.png` |
| HAS_OUTPUT_FOLDER_TO_EXPORT | `folder_black.png` |
| HAS_ZIP_TO_EXPORT | `zip.png` |

### Icon Sizes
- **ACTION buttons:** 24px (configurable)
- **All other buttons:** 20px (configurable)

---

## Configuration Panel (QToolBox Tab 3)

The CONFIGURATION tab is the third tab in the QToolBox (after FILTERING and EXPORTING). It provides a full JSON editor for advanced plugin settings.

### Layout
```
┌─────────────────────────────────────────────┐
│  🔍 Search configuration...            [0]  │
├─────────────────────────────────────────────┤
│  Property              │  Value             │
│  ├─ _CONFIG_VERSION    │  2.0               │
│  ├─ _CONFIG_META/      │                    │
│  ├─ APP/               │                    │
│  │   ├─ AUTO_ACTIVATE/ │                    │
│  │   │   ├─ value      │  False  ← editable │
│  │   │   └─ description│  Auto-activate...  │
│  │   ├─ DOCKWIDGET/    │                    │
│  │   │   ├─ LANGUAGE/  │                    │
│  │   │   │   ├─ value  │  auto   ← editable │
│  │   │   │   └─ choices│  [auto,en,fr,...]  │
│  │   └─ OPTIONS/       │                    │
│  └─ CURRENT_PROJECT/   │                    │
├─────────────────────────────────────────────┤
│  [Reload Plugin]                            │
│  [         OK         ] [     Cancel     ]  │
└─────────────────────────────────────────────┘
```

### Components

**SearchableJsonView** — A widget combining a search bar with a JSON tree:
- **Search bar** (top): Type to filter the tree. Shows match count (e.g., "3 matches"). Type to search, click X to clear.
- **JSON Tree** (center): `QTreeView` with 2 columns — Property (keys, 180px) and Value (editable, 240px)
- Alternating row colors for readability
- Theme-aware: dark mode uses VS Code-inspired dark palette, light mode uses standard white/gray
- Right-click context menu: Change (for enumerated values), Rename, Add child, Insert sibling, Remove

**JsonModel** — The underlying data model:
- Keys are **read-only** (editable_keys=False)
- Values are **editable** (editable_values=True)
- Data types are color-coded: strings, numbers, booleans, arrays, objects each have distinct colors
- Supports themes (e.g., "monokai", "nord") via the themes system

### Editing Workflow

1. **Find a setting:** Use search bar or browse the tree
2. **Edit a value:** Click on the Value column → edit inline
3. **For choices:** Right-click → "Change" → select from available options (e.g., language choices)
4. **Changes are tracked:** `itemChanged` signal → `data_changed_configuration_model()` → changes stored as "pending"
5. **OK/Cancel buttons become enabled** when pending changes exist
6. **Click OK:** Applies all pending changes → saves to `config.json` → syncs `ENV_VARS`
7. **Click Cancel:** Reverts all changes → reloads from `config.json` → rebuilds model

### Reload Plugin Button
- Below the tree, above OK/Cancel
- Click → asks confirmation dialog: "Do you want to reload FilterMate to apply all configuration changes?"
- If Yes: saves config then fully reloads the plugin (needed for layout changes like action bar position)

### What Can Be Changed Live (No Reload)
- Language, feedback level, theme colors, optimization thresholds, cache settings

### What Requires Plugin Reload
- Dock position, action bar position, action bar vertical alignment, UI profile

---

## Per-Layer Variables (PROJECT_LAYERS)

FilterMate stores properties **per layer** in the `PROJECT_LAYERS` dictionary. These properties persist across sessions via QGIS layer variables + a SQLite database.

### Structure: `PROJECT_LAYERS[layer_id]`

```python
{
    "infos": {
        "layer_name": "communes",
        "primary_key_name": "id",
        "provider_type": "ogr",
        ...
    },
    "exploring": {
        "is_selecting": False,          # Select toggle state
        "is_tracking": False,           # Track toggle state
        "is_linking": True,             # Link toggle state
        "current_exploring_groupbox": "single_selection",  # Active GroupBox
        "single_selection_expression": "name",    # Display field for single picker
        "multiple_selection_expression": "name",  # Display field for multi picker
        "custom_selection_expression": "name",    # Expression for custom selection
        "is_changing_all_layer_properties": True  # Internal flag
    },
    "filtering": {
        "has_layers_to_filter": False,            # Toggle state
        "layers_to_filter": [],                   # List of target layer IDs
        "has_combine_operator": False,
        "source_layer_combine_operator": "AND",   # AND or OR
        "other_layers_combine_operator": "AND",
        "has_geometric_predicates": False,
        "geometric_predicates": [],               # List: ["intersects", "within", ...]
        "has_buffer_value": False,
        "buffer_value": 0.0,                      # Buffer distance in map units
        "buffer_value_property": False,            # PropertyOverrideButton active?
        "buffer_value_expression": "",             # Data-defined expression
        "has_buffer_type": False,
        "buffer_type": "Round",                   # Buffer geometry type
        "buffer_segments": 5,                     # Circle approximation segments (range: 1-100)
        "use_centroids_source_layer": False,
        "use_centroids_distant_layers": False
    }
}
```

### Persistence: Dual Storage

Properties are saved to **two locations** for redundancy:

1. **QGIS Layer Variables** (runtime access):
   - Stored as QGIS expression variables: `exploring_is_tracking`, `filtering_buffer_value`, etc.
   - Accessible via QGIS expressions: `@exploring_is_tracking`
   - Lost when QGIS project is not saved

2. **SQLite Database** (persistent):
   - Table: `fm_project_layers_properties`
   - Columns: uuid, datetime, project_uuid, layer_id, key_group, key, value
   - Survives across sessions

### When Variables Are Saved

Variables are saved via `settingLayerVariable` signal, emitted when:
- A filter is applied
- A toggle button is changed
- Layer properties are reset
- GroupBox selection changes

### Reset Layer Properties

When the **Reset** button (Exploring sidebar) is clicked:
- All `exploring` properties reset to defaults (tracking OFF, selecting OFF, linking ON by default)
- All `filtering` properties reset to defaults (all toggles OFF, buffer 0.0, no predicates)
- Display fields reset to best detected field (via `get_best_display_field()`)
- QGIS message bar shows "Layer properties reset to defaults"

---

### Theme-Aware Icons
Icons adapt to dark/light mode:
- **Variant icons** (have `_black`/`_white` versions): `auto_layer`, `folder`, `map`, `pointing`, `projection`, `styles`, `select`
- **Force-inverted in dark mode:** `layers`, `datatype`, `zip`, `filter`, `undo`, `redo`, `unfilter`, `reset`, `export`, `identify_alt`, `zoom`, `track`, `link`, `save_properties`, `add_multi`, `geo_predicates`, `buffer_value`, `buffer_type`, `filter_multi`, `save`, `parameters`
- **Never inverted:** `logo.png`, `icon.png`

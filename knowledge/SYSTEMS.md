# FilterMate — Internal Systems

> How the backend selection, favorites, history, and optimization systems work.
> This is the "engine room" — what happens behind the UI.

---

## Backend System

FilterMate has 4 backends, each optimized for a specific data source type.

### The 4 Backends

| Backend | Data Sources | SQL Dialect | Strengths |
|---|---|---|---|
| **PostgreSQL** | PostGIS layers | PostGIS SQL | Native spatial functions (`ST_Intersects`, `ST_Buffer`, `ST_Centroid`), materialized views, connection pooling |
| **Spatialite** | `.sqlite`, `.gpkg` files | Spatialite SQL | Native spatial SQL (`Intersects`, `Buffer`), good for medium datasets |
| **OGR** | Shapefiles, WFS, GeoJSON, CSV, any file | QGIS Expression | Universal compatibility, QGIS-native expressions |
| **Memory** | In-memory layers, virtual layers | QGIS Expression | Fastest for small datasets, no disk I/O |

### Auto-Selection Logic (Priority Order)

```
1. User forced backend? → Use that backend
2. Memory layer? → Memory backend
3. PostgreSQL layer? → ALWAYS PostgreSQL (even without psycopg2)
4. Spatialite/GPKG? → Spatialite backend
5. OGR (file-based)? → OGR backend
6. Unknown? → OGR fallback
```

### Small Dataset Optimization

For PostgreSQL layers with **< 5000 features** (configurable):
- Can switch to OGR Memory backend for faster filtering
- Copies data to memory → filters in RAM → applies result
- **Disabled** when `prefer_native_for_postgresql_project` is true (all layers are PostgreSQL → stay consistent)

### Backend Indicator (UI)

- Blue pill badge in the header bar showing current backend name
- Click opens context menu with:
  - Current backend (highlighted)
  - Available backends for the current layer
  - Option to force a specific backend
- Forced backends are stored per-layer in `forced_backends` dictionary
- Backend updates automatically when source layer changes

---

## Favorites System

Saved filter configurations with full spatial context, persisted in SQLite.

### What Gets Saved in a Favorite

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Unique identifier |
| `name` | String | User-given name |
| `expression` | String | The filter expression |
| `layer_name` | String | Source layer name |
| `layer_id` | String | Source layer QGIS ID |
| `layer_provider` | String | Provider type (ogr, postgres, etc.) |
| `description` | String | Optional description |
| `tags` | List | User tags for organization |
| `remote_layers` | Dict | Target layers configuration |
| `spatial_config` | Dict | Full spatial filtering config (predicates, buffer, centroids, etc.) |
| `created_at` | ISO DateTime | Creation timestamp |
| `updated_at` | ISO DateTime | Last modification |
| `use_count` | Integer | How many times applied |
| `last_used_at` | ISO DateTime | Last application time |

### Storage

- **Database:** SQLite file (path configurable)
- **Organization:** Per-project (each QGIS project has its own favorites)
- **Global favorites:** Special UUID `00000000-0000-0000-0000-000000000000` for cross-project favorites
- Tables: `favorites`, `project_favorites`, `tags`

### Favorites Manager Dialog (UI)

Opened by clicking the **★ star indicator** in the header bar.

**Layout:** Two-panel dialog:
- **Left panel:** Searchable list of favorites with name, layer count, use count
- **Right panel:** 3 tabs with details:
  1. **General:** Name, description, layer info, tags, creation date, usage stats
  2. **Expression:** Full filter expression text
  3. **Remote:** Target layers and spatial configuration

**Actions:**
- **Search:** Filter favorites by name/expression/tags
- **Apply:** Load a favorite → restores filter configuration and applies it
- **Save:** Create new favorite from current configuration
- **Delete:** Remove a favorite
- **Sort:** By name, date, usage count

### Applying a Favorite

When a favorite is applied:
1. Source layer is set (if the layer exists in the current project)
2. Filter expression is restored
3. Target layers are configured (if they exist)
4. Spatial config (predicates, buffer, centroids) is restored
5. The filter is applied automatically
6. `use_count` increments, `last_used_at` updates

---

## History / Undo-Redo System

### Architecture

- **Stack-based:** Two stacks — undo stack and redo stack
- **Per-session:** History is session-scoped (cleared on plugin restart unless persistence is enabled)
- **Configurable:** Max 100 entries (configurable in `APP.OPTIONS.HISTORY`)
- **Persistence:** Optionally saves to disk between sessions

### What Gets Stored per History Entry

Each filter operation stores:
- The **subset strings** (SQL WHERE clauses) applied to each affected layer
- Layer IDs and their state before/after filtering
- Timestamp of the operation

### Operations

| User Action | Undo Stack | Redo Stack |
|---|---|---|
| Apply filter | Push current state | Clear |
| Click Undo | Pop → restore | Push current state |
| Click Redo | Push current state | Pop → restore |
| Click Unfilter | Uses history undo if available, otherwise clears filter directly |

### History Widget (UI)

- Scrollable list showing past filter operations
- Each entry shows: timestamp, layer name, filter type
- Navigate through history visually

---

## Optimization Systems

### 4 Performance Optimizers

1. **Query Cache** — Caches built expressions (max 100 entries, no expiry by default)
2. **Parallel Filtering** — Filters multiple target layers simultaneously (thread pool, auto-detect workers)
3. **Progressive Filtering** — Two-phase: bounding box first, then precise geometry (for complex PostgreSQL queries)
4. **Geometry Simplification** — Simplifies complex WKT when exceeding threshold (100K chars)

### Smart Caching

```
User clicks Filter
  → Check query cache: same expression for same layer?
    → HIT: skip expression building (2-8x faster)
    → MISS: build expression, cache it
  → Execute query
  → Cache result count
```

Cache is keyed by: `(layer_id, expression_hash)`

### Auto-Optimization Decisions

FilterMate automatically makes optimization decisions based on data characteristics:

| Condition | Auto-Optimization |
|---|---|
| Target layer > 5000 features | Auto-enable centroids for target layers |
| Source layer > 50000 features | Auto-enable centroids for source layer |
| Complex geometry buffer | Auto-simplify before buffer |
| Buffer result geometry | Auto-simplify after buffer |
| Multiple target layers (≥2) | Use parallel filtering |
| PostgreSQL + complex query (score > 100) | Use progressive filtering |
| WKT string > 100K chars | Use EXISTS subquery instead of inline WKT |
| Source FIDs > 500 | Use materialized view approach (PostgreSQL) |

### Streaming Export

For datasets > 10,000 features:
- Export happens in chunks of 5000 features
- Prevents memory exhaustion on large datasets
- Progress bar updates between chunks

---

## Theme & Styling System

### Theme Detection

```
Theme Source (config):
  'config' → Use ACTIVE_THEME from config
  'qgis'   → Read QGIS application stylesheet/palette
  'system'  → Use OS dark/light mode
```

### Theme Application Order

1. **IconManager** detects theme → swaps icon variants or inverts colors
2. **StyleManager** applies QSS stylesheets for all widgets
3. **ThemeWatcher** monitors QGIS theme changes → auto-refreshes

### Icon Theme Logic

For each icon, the system checks:
1. Is it a variant icon? (`auto_layer_black.png` → swap to `auto_layer_white.png` in dark mode)
2. Is it in the force-invert list? → Invert pixel colors
3. Is it in the never-invert list? → Leave as-is (logos, etc.)
4. Cache the result for performance

---

## Expression Building

Each backend builds filter expressions differently:

### PostgreSQL Example
```sql
-- Single feature, intersects predicate, with buffer
SELECT id FROM target_layer
WHERE ST_Intersects(
    target_layer.geom,
    ST_Buffer(
        ST_GeomFromText('POINT(2.35 48.85)', 4326),
        1000
    )
)
```

### OGR/Memory Example (QGIS Expression)
```
-- Same filter as QGIS expression
intersects(
    $geometry,
    buffer(
        geom_from_wkt('POINT(2.35 48.85)'),
        1000
    )
)
```

### Spatialite Example
```sql
-- Same filter in Spatialite SQL
SELECT id FROM target_layer
WHERE Intersects(
    target_layer.geom,
    Buffer(
        GeomFromText('POINT(2.35 48.85)', 4326),
        1000
    )
)
```

### How Expressions Are Applied

The final expression becomes a **subset string** on the QGIS layer:
```python
layer.setSubsetString("id IN (1, 5, 12, 34)")  # For PostgreSQL/Spatialite
layer.setSubsetString("$id IN (1, 5, 12, 34)")  # For OGR/Memory
```

This is QGIS's native filtering mechanism — it tells the data provider to only return matching features.

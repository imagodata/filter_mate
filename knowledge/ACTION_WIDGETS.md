# FilterMate — Action Widgets Reference

> Detailed reference for the interactive action widgets: Action Bar, History, Favorites, and Backend Indicator.
> These are the "do things" widgets — they execute tasks, manage history, save configs, and control backends.

---

## Action Bar

The 6 main action buttons. Position is configurable (`top`, `bottom`, `left`, `right` of the dock). When placed `left`/`right`, buttons stack vertically.

### Filter Button
- **Icon:** `filter.png`
- **Type:** PushButton (not checkable)
- **Signal:** `clicked` → `launchTaskEvent(state, 'filter')`
- **Enabled when:** FILTERING tab is active + valid configuration exists
- **Disabled when:** EXPORTING tab is active, or no source layer, or no features selected, or `_filtering_in_progress`
- **What it does:**
  1. Gets source features from active Exploring GroupBox (`get_current_features()`)
  2. Gets filtering config from `PROJECT_LAYERS` (predicates, buffer, target layers)
  3. Checks for edit mode conflict (shows popup if layer is in edit mode)
  4. Emits `launchingTask` signal
  5. Creates `FilterTask` in background thread
  6. Auto-selects backend (or uses forced backend)
  7. Builds SQL expression per backend dialect
  8. Applies as subset string to source layer + target layers
  9. Updates undo stack
  10. Refreshes map canvas

### Undo Button
- **Icon:** `undo.png`
- **Type:** PushButton (not checkable)
- **Signal:** `clicked` → `launchTaskEvent(state, 'undo')`
- **Enabled when:** FILTERING tab + undo stack is non-empty
- **Tooltip:** Dynamic — shows description of the state to restore (e.g., "Undo: Filter on communes")
- **What it does:**
  1. Bypasses `_filtering_in_progress` protection (user action)
  2. Recovers `current_layer` if null (3 fallback strategies)
  3. Pops from undo stack → pushes current state to redo stack
  4. Restores previous subset strings on all affected layers
  5. Refreshes map

### Redo Button
- **Icon:** `redo.png`
- **Type:** PushButton (not checkable)
- **Signal:** `clicked` → `launchTaskEvent(state, 'redo')`
- **Enabled when:** FILTERING tab + redo stack is non-empty
- **Tooltip:** Dynamic — shows description of the state to re-apply
- **What it does:**
  1. Same bypasses as Undo
  2. Pops from redo stack → pushes current state to undo stack
  3. Re-applies the undone subset strings
  4. Refreshes map

### Unfilter Button
- **Icon:** `unfilter.png`
- **Type:** PushButton (not checkable)
- **Signal:** `clicked` → `launchTaskEvent(state, 'unfilter')`
- **Enabled when:** FILTERING tab is active
- **What it does:**
  1. Uses history manager to undo the current filter state (if history available)
  2. If no history available, clears the subset string entirely
  3. Clears Spatialite cache for the layer
  4. Refreshes map showing restored/unfiltered features

### Export Button
- **Icon:** `export.png`
- **Type:** PushButton (not checkable)
- **Signal:** `clicked` → `launchTaskEvent(state, 'export')`
- **Enabled when:** EXPORTING tab is active
- **Disabled when:** FILTERING tab is active
- **What it does:**
  1. Syncs `HAS_LAYERS_TO_EXPORT` flag (just-in-time, because Qt may restore widget states without signals)
  2. Gets checked layers from export combobox
  3. Gets export config (CRS, styles, format, output path)
  4. Exports each layer to GeoPackage (or other format)
  5. Optionally embeds QGIS project (preserves layer groups, styles, CRS)
  6. Optionally zips the output
  7. Supports batch mode (one file per layer)
  8. Uses streaming for large datasets (> 10K features)

### About Button
- **Icon:** `icon.png` (FilterMate logo — never inverted in dark mode)
- **Type:** PushButton (not checkable)
- **Signal:** `clicked` → `open_project_page()`
- **Always enabled** regardless of active tab
- **What it does:** Opens FilterMate project page in the default web browser

---

## History Widget

A compact undo/redo navigation bar, embedded in the plugin UI.

### Visual Layout
```
[ ↶ ] [ ↷ ]  2/5
 undo  redo   position/total
```

### Components

| Element | Size | Description |
|---|---|---|
| **Undo button** (↶) | 28×28px | Styled button with gray background, bold font |
| **Redo button** (↷) | 28×28px | Same styling as undo |
| **Position label** | auto | Gray text, 10px font, shows "current/total" (e.g., "3/7") |

### Styling
```
Default: light gray background (#f0f0f0), 1px border (#ccc), rounded 4px
Hover: slightly darker (#e0e0e0), darker border (#999)
Pressed: even darker (#d0d0d0)
Disabled: very light (#f8f8f8), text #ccc, border #ddd
```

### Button States
| Undo Stack | Redo Stack | Undo Button | Redo Button | Label |
|---|---|---|---|---|
| Empty | Empty | ❌ Disabled | ❌ Disabled | (empty) |
| Has items | Empty | ✅ Enabled | ❌ Disabled | "3/3" |
| Has items | Has items | ✅ Enabled | ✅ Enabled | "2/5" |

### Dynamic Tooltips
- Default undo: "Undo last filter"
- With state info: "Undo: Filter on communes layer" (shows next undo description, truncated to 40 chars)
- Default redo: "Redo filter"
- With state info: "Redo: Buffer 500m on parcels"

### Context Menu (right-click)
| Action | Icon | Enabled When | What It Does |
|---|---|---|---|
| Undo | ↶ | Undo available | Same as undo button |
| Redo | ↷ | Redo available | Same as redo button |
| *(separator)* | | | |
| Clear History | 🗑 | History non-empty | Clears all history for current layer |
| *(separator)* | | | |
| Browse History... | 📋 | History non-empty | Opens full history browser (future feature) |

### Signals Emitted
| Signal | When |
|---|---|
| `undoRequested` | Undo button clicked or menu undo |
| `redoRequested` | Redo button clicked or menu redo |
| `historyCleared` | Clear History menu action |
| `historyBrowseRequested` | Browse History menu action |

### Layer-Aware
History is **per-layer**. When the source layer changes:
- `update_for_layer(layer_id)` is called
- Buttons update to reflect that layer's history stack
- Position label shows that layer's position

### What Gets Stored Per History Entry
| Field | Type | Description |
|---|---|---|
| `description` | String | Human-readable description of the filter operation |
| `timestamp` | ISO DateTime | When the filter was applied |
| `feature_count` | Integer | How many features matched the filter |
| Subset strings | Dict | `{layer_id: subset_string}` for all affected layers |

---

## Favorites Indicator & Menu

An orange star badge (★) in the header bar. Shows favorites count and provides quick access.

### Visual States

**With favorites saved:**
```
★ 5
```
- Gold/orange background (`#f39c12`), white text, 8pt bold
- Hover: darker orange (`#d68910`)
- Tooltip: "★ 5 Favorites saved — Click to apply or manage"

**No favorites:**
```
★
```
- Light gray background (`#ecf0f1`), gray text (`#95a5a6`)
- Hover: slightly darker gray (`#d5dbdb`)
- Tooltip: "★ No favorites saved — Click to add current filter"

### Click Menu

Clicking the star opens a context menu:

```
⭐ Add Current Filter to Favorites     ← disabled if no active filter
─────────────────────────────────────
📋 Saved Favorites (5)                 ← header (disabled, just info)
  ★ Communes intersects buffer...      ← click to apply
  ★ Rivers within 1km (3×)            ← (3×) = used 3 times
  ★ Multi-layer filter [4]            ← [4] = 4 layers involved
  ... 2 more favorites                 ← click to open manager
─────────────────────────────────────
⚙️ Manage Favorites...                 ← opens FavoritesManagerDialog
📤 Export Favorites...                  ← save to JSON file
📥 Import Favorites...                  ← load from JSON file
```

### Menu Item Details

**Favorite entries show:**
- Truncated name (25 chars max)
- Layer count badge `[N]` if > 1 layer
- Use count `(N×)` if used at least once
- Tooltip with: expression preview (80 chars), source layer name, up to 5 remote layer names

**Add Current Filter:**
- Collects current expression from active filter
- Collects source layer info (name, ID, provider)
- Scans ALL project layers for active subset strings → saves as `remote_layers`
- Opens "Add to Favorites" dialog:
  - **Name** field (auto-generated: "Filter (N layers)")
  - **Description** field (auto-generated with date, source, remote layers list)
  - OK / Cancel buttons

**Export Favorites:**
- Opens file save dialog (default: `filtermate_favorites.json`)
- Exports all favorites to JSON

**Import Favorites:**
- Opens file open dialog (*.json)
- Asks: "Merge with existing? Yes = Add / No = Replace All / Cancel"
- Imports and saves to project

### Signals Emitted
| Signal | When |
|---|---|
| `favoriteAdded(favorite_id)` | New favorite saved |
| `favoriteApplied(favorite_id)` | Favorite applied from menu |
| `favoritesExported(file_path)` | Favorites exported to file |
| `favoritesImported(file_path)` | Favorites imported from file |
| `managerRequested` | "Manage Favorites..." clicked |

---

## Favorites Manager Dialog

Opened from the favorites menu ("Manage Favorites...") or from the star indicator.

### Layout: Two-Panel Dialog

```
┌────────────────────────┬──────────────────────────────────┐
│  SEARCH: [___________] │  ┌──────────────────────────────┐│
│                        │  │ General │ Expression │ Remote ││
│  ★ Communes filter     │  ├──────────────────────────────┤│
│  ★ Rivers buffer 1km   │  │ Name: Communes filter        ││
│  ★ Multi-layer [4]     │  │ Description: Filter on...    ││
│    → selected           │  │ Layer: communes              ││
│  ★ Parcels within      │  │ Tags: [urban] [analysis]     ││
│                        │  │ Created: 2026-01-15 14:30    ││
│                        │  │ Used: 5 times                ││
│                        │  │ Last used: 2026-03-12        ││
│                        │  └──────────────────────────────┘│
├────────────────────────┤                                  │
│ [Apply] [Save] [Delete]│                     [Close]      │
└────────────────────────┴──────────────────────────────────┘
```

### Left Panel
- **Search bar:** Filter favorites by name, expression, or tags
- **Scrollable list:** Shows all favorites with name + indicators
- **Selection:** Click to show details in right panel

### Right Panel — 3 Tabs
1. **General:** Name, description, layer info, tags, creation date, use count, last used
2. **Expression:** Full filter expression text (read-only)
3. **Remote:** Target layers configuration, spatial config details

### Action Buttons
| Button | Action |
|---|---|
| **Apply** | Load and apply the selected favorite → restores full filter config |
| **Save** | Update the selected favorite with current changes |
| **Delete** | Remove the selected favorite (with confirmation) |
| **Close** | Close the dialog |

---

## Backend Indicator

A color-coded pill badge in the header bar showing the current backend.

### Visual States by Backend

| Backend | Text | Color | Hover | Icon |
|---|---|---|---|---|
| **PostgreSQL** | `POSTGRESQL` | Green `#58d68d` | `#27ae60` | 🐘 |
| **Spatialite** | `SPATIALITE` | Purple `#bb8fce` | `#9b59b6` | 💾 |
| **OGR** | `OGR` | Blue `#5dade2` | `#3498db` | 📁 |
| **Memory** | `MEMORY` | Orange `#f0b27a` | `#e67e22` | 💭 |
| **Unknown** | `?` | Gray `#aab7b8` | `#95a5a6` | ❓ |
| **Waiting** (no layers) | `...` | Gray `#aab7b8` | `#95a5a6` | — |

All badges: white text, 8pt, 500 weight, 2px padding, 10px rounded corners, 40px min width, 20px max height.

### Click Behavior

**In waiting state (no layers loaded):**
- Emits `reloadRequested` signal → triggers layer reload

**With layers loaded:**
- Opens backend selection context menu

### Backend Context Menu

```
Select Backend:                        ← header (disabled)
─────────────────────────────────────
🐘 PostgreSQL ✓                        ← current backend has checkmark
💾 Spatialite
📁 OGR
💭 Memory
─────────────────────────────────────
⚙️ Auto (Default) ✓                    ← checkmark if no forced backend
─────────────────────────────────────
🎯 Auto-select Optimal for All Layers  ← auto-detect best backend per layer
─────────────────────────────────────
🔒 Force POSTGRESQL for All Layers     ← force current backend everywhere
```

### Menu Actions

| Action | What It Does |
|---|---|
| Select a backend | Sets forced backend for **current layer only** |
| Auto (Default) | Clears forced backend → auto-detection resumes |
| Auto-select Optimal for All Layers | Runs auto-detection for every layer in the project |
| Force [X] for All Layers | Forces the currently detected backend for every layer |

### Forced Backends Storage
- Stored in `_forced_backends` dictionary: `{layer_id: backend_type}`
- **Per-layer:** Each layer can have a different forced backend
- **Not persistent:** Forced backends are reset when plugin restarts (session-scoped)
- Clearing: `clear_forced_backends()` removes all overrides

### Automatic Updates
The indicator updates automatically when:
- Source layer changes → detects backend for new layer
- Forced backend is set → shows the forced backend
- Layer is removed → may show waiting state

### Signals Emitted
| Signal | Parameters | When |
|---|---|---|
| `backendChanged` | `(layer_id, backend_type)` | Backend changed for a specific layer |
| `backendForAllChanged` | `(backend_type)` | Backend forced for all layers |
| `autoSelectRequested` | *(none)* | User requests auto-select for all layers |
| `reloadRequested` | *(none)* | Clicked in waiting state |

---

## Widget Interaction Summary

### Header Bar (left to right)
```
[spacer] → [★ Favorites indicator] → [POSTGRESQL backend indicator]
```
- Height: 13px frame, 18px labels
- Right-aligned (spacer pushes to right)
- Both are clickable (PointingHandCursor)

### How Action Buttons Interact with Other Widgets

| Action | Uses Exploring? | Uses Filtering? | Uses Exporting? | Updates History? |
|---|---|---|---|---|
| **Filter** | ✅ Gets source features | ✅ Gets spatial config | ❌ | ✅ Push to undo stack |
| **Undo** | ❌ | ❌ (restores stored state) | ❌ | ✅ Pop undo → push redo |
| **Redo** | ❌ | ❌ (restores stored state) | ❌ | ✅ Pop redo → push undo |
| **Unfilter** | ❌ | ❌ | ❌ | ❌ No history change |
| **Export** | ❌ | ❌ | ✅ Gets export config | ❌ |
| **About** | ❌ | ❌ | ❌ | ❌ |

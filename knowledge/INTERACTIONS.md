# FilterMate — Panel Interactions & Widget Relationships

> How the Exploring, Filtering, and Exporting panels **work together** as a system.
> This is the "functional glue" — what activates what, which buttons depend on which panels, and how data flows between zones.

---

## The Big Picture: How a Filter Actually Works

FilterMate's UI is split into 3 roles that chain together:

```
EXPLORING (source data)  →  FILTERING (spatial config)  →  ACTION BAR (execute)
"WHAT features?"            "HOW to filter?"                "DO IT"
```

1. **EXPLORING** determines the **source features** (the geometry reference)
2. **FILTERING** determines the **spatial operation** (predicates, buffer, target layers)
3. **ACTION BAR** executes the task and manages history

The **EXPORTING** panel is independent — it doesn't use Exploring data, it exports layers with optional CRS/style options.

---

## Panel Cooperation: Exploring ↔ Filtering

### The Source Layer Is Shared

The **source layer** in the FILTERING combobox (`comboBox_filtering_current_layer`) is the SAME layer used by EXPLORING widgets. When it changes:

```
Source Layer Changed
  → Exploring: repopulates feature picker, field expressions, resets selection
  → Filtering: updates available target layers, resets predicates
  → Backend Indicator: detects backend type (PostgreSQL/Spatialite/OGR/Memory)
  → History: clears undo/redo for old layer
  → Properties: restores saved properties from PROJECT_LAYERS for new layer
```

### What EXPLORING Provides to the Filter Task

When the user clicks **Filter**, the system calls `get_current_features()` which reads from the **active exploring GroupBox**:

| Active GroupBox | What It Provides | Used As |
|---|---|---|
| **Single Selection** | One feature from `QgsFeaturePickerWidget` | Source geometry for spatial filter |
| **Multiple Selection** | Multiple checked features from checkable combobox | Union of geometries for spatial filter |
| **Custom Selection** | A QGIS expression (e.g., `"pop" > 10000`) | Applied directly as subset string (no geometry) |

**Critical:** Without a valid selection in EXPLORING, the **Filter button does nothing**.

### Feature Retrieval Priority

`get_current_features()` tries multiple strategies in order:
1. ExploringController delegation (primary path)
2. Cache lookup (`_exploring_cache`) — keyed by `(layer_id, groupbox_type)`
3. Fallback widget reading (direct widget access)
4. Canvas selection fallback (selected features on QGIS map)

---

## Identify & Zoom: Depend on Exploring Selection

The **Identify** and **Zoom** buttons in the Exploring sidebar are **dynamically enabled/disabled** based on whether features are currently selected:

```
_update_exploring_buttons_state():

  Single Selection active:
    → Check picker.feature() validity OR saved FID
    → If feature exists → Identify ✅ Zoom ✅
    → If no feature    → Identify ❌ Zoom ❌

  Multiple Selection active:
    → Check combobox.checkedItems()
    → If items checked → Identify ✅ Zoom ✅
    → If nothing checked → Identify ❌ Zoom ❌

  Custom Selection active:
    → Check expression().strip()
    → If non-empty expression → Identify ✅ Zoom ✅
    → If empty → Identify ❌ Zoom ❌

  Last resort fallback:
    → Check current_layer.selectedFeatureIds() (QGIS canvas selection)
    → If any selected → Identify ✅ Zoom ✅
```

---

## Select Toggle: Links EXPLORING to the QGIS Map Canvas

When **Select** (IS_SELECTING) is toggled ON:
1. Activates QGIS Rectangle Selection tool on canvas
2. Sets the source layer as the active QGIS layer
3. Gets features from current GroupBox via `get_current_features()`
4. Selects those features on the canvas (highlights them)
5. Enables the active GroupBox for interaction

When toggled OFF:
1. Clears selection on the source layer
2. Switches QGIS to Pan tool
3. Disables the sync between GroupBox and canvas

---

## Track Toggle: Auto-Zoom Chain

When **Track** (IS_TRACKING) is ON:
- Every time a feature changes in the picker → `exploring_zoom_clicked()` is called automatically
- This creates a "follow" behavior: browsing features in Single Selection moves the map

The chain:
```
FeaturePickerWidget.featureChanged
  → exploring_features_changed()
    → if IS_TRACKING.isChecked():
      → exploring_zoom_clicked()
        → gets feature geometry
        → calculates bounding box
        → pans/zooms QGIS canvas
```

---

## Link Toggle: Synchronizes GroupBox Widgets

When **Link** (IS_LINKING) is ON:
- Changing the expression/field in one GroupBox updates the others
- `exploring_link_widgets()` propagates the current expression across all 3 GroupBoxes
- This ensures Single, Multiple, and Custom all use the same field/expression

---

## Filtering Toggle Dependencies (Cascade)

The 6 filtering sidebar toggles have a **dependency chain**:

```
LEVEL 0 (always available):
  ├── Auto Current Layer
  ├── Layers to Filter
  └── Combine Operator

LEVEL 1 (always available):
  └── Geometric Predicates

LEVEL 2 (requires Geometric Predicates ON):
  ├── Buffer Value
  └── Buffer Type
```

### Detailed Cascade:

**Geometric Predicates OFF →**
- Buffer Value button: **DISABLED + UNCHECKED**
- Buffer Type button: **DISABLED + UNCHECKED**
- All buffer widgets: **DISABLED**

**Geometric Predicates ON →**
- Buffer Value button: **ENABLED** (user can now check it)
- Buffer Type button: **ENABLED** (user can now check it)

**Buffer Value ON + PropertyOverrideButton active with expression →**
- Buffer SpinBox: **DISABLED** (expression overrides manual input)
- PropertyOverrideButton: **ENABLED** (to deactivate the override)

### Visual Feedback for Each Toggle State

| Toggle | ON (checked) | OFF (unchecked) |
|---|---|---|
| Auto Current Layer | Source combobox follows QGIS layer panel | Source combobox independent |
| Layers to Filter | Target layers combobox **enabled** + centroid checkbox **enabled** | Both **grayed out/disabled** |
| Combine Operator | Two AND/OR dropdowns **enabled** | Both **grayed out/disabled** |
| Geometric Predicates | Predicates combobox **enabled** + buffer buttons **enabled** | Predicates **disabled** + buffer buttons **disabled + unchecked** |
| Buffer Value | SpinBox **enabled** + PropertyOverride **enabled** | Both **grayed out/disabled** |
| Buffer Type | Type combobox **enabled** + Segments spinbox **enabled** | Both **grayed out/disabled** |

---

## Always-Enabled Widgets (Never Disabled)

These 4 widgets are **always interactive** regardless of any toggle state:

| Widget | Why |
|---|---|
| Source Layer combobox | Must always be able to change the source layer |
| Source Centroids checkbox | Always available option for source geometry |
| Output Folder button | Always clickable (opens file dialog) |
| Zip button | Always clickable (opens file dialog) |

---

## Tab Switching: FILTERING ↔ EXPORTING

The QToolBox tabs control which Action Bar buttons are active:

| Tab | Filter | Undo | Redo | Unfilter | Export | About |
|---|---|---|---|---|---|---|
| **FILTERING** (tab 0) | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **EXPORTING** (tab 1) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **CONFIGURATION** (tab 2) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Key:** You can't Filter when on the Export tab, and you can't Export when on the Filter tab. About is always available.

Additionally, when switching to EXPORTING:
- `set_exporting_properties()` is called → syncs export configuration
- `undoRedoStateRequested` signal is emitted → updates undo/redo availability

---

## EXPORTING Panel: Independent from Exploring

Unlike Filtering, the EXPORTING panel does **NOT use** the Exploring selection:
- It works with **whole layers**, not individual features
- Layers to export are selected from a **separate** checkable combobox
- Export operates on the current filter state of each layer (if a layer is filtered, only filtered features are exported)

### Export Button Enable Logic:
- Export button is enabled ONLY when on the EXPORTING tab
- The button calls `launchTaskEvent(state, 'export')` which does a just-in-time sync of `HAS_LAYERS_TO_EXPORT`
- Export needs: at least one layer checked + output folder OR zip path set

### Export Button Initialization:
All 6 exporting sidebar toggles start **disabled** at plugin load. They become enabled once layers are available in the project.

---

## GroupBox Exclusive Behavior (Exploring)

Only ONE GroupBox can be active at a time. The exclusive logic:

### Check one → others uncheck
```
User checks "Multiple Selection"
  → Single Selection: unchecked ❌ + collapsed ▶
  → Multiple Selection: checked ✅ + expanded ▼
  → Custom Selection: unchecked ❌ + collapsed ▶
```

### Try to uncheck the only active one → blocked
```
User unchecks "Single Selection" (the only checked one)
  → System re-checks it immediately (prevents all-unchecked state)
  → Single Selection stays: checked ✅ + expanded ▼
```

### Expand a collapsed one → becomes active
```
User expands "Custom Selection" (currently collapsed)
  → Custom Selection: checked ✅ + expanded ▼
  → Others: unchecked ❌ + collapsed ▶
```

### Per-layer memory
Each layer remembers which GroupBox was active:
```
Switch from Layer A (Multiple active) → Layer B
  → Layer B restores its saved GroupBox (e.g., Single)
Switch back to Layer A
  → Layer A restores Multiple Selection
```

Stored in: `PROJECT_LAYERS[layer_id]["exploring"]["current_exploring_groupbox"]`

---

## Combined Feature → Filter Pipeline

Here's the complete data flow from user action to filtered map:

```
1. USER selects feature(s) in EXPLORING
   └→ stored in widget state + exploring cache

2. USER configures FILTERING
   └→ toggles stored in PROJECT_LAYERS[layer_id]["filtering"]
   └→ target layers, predicates, buffer, operators

3. USER clicks FILTER
   └→ launchTaskEvent('filter')
     └→ get_current_features() reads from active GroupBox
     └→ gets filtering config from PROJECT_LAYERS
     └→ selects backend (PostgreSQL/Spatialite/OGR/Memory)
     └→ backend builds SQL expression
     └→ expression applied as subset string to layer(s)
     └→ map refreshes showing only matching features
     └→ undo stack updated

4. USER clicks UNDO
   └→ previous subset strings restored
   └→ map refreshes to previous state

5. USER clicks UNFILTER
   └→ ALL subset strings removed from ALL layers
   └→ map shows all features again
```

---

## Undo/Redo System

FilterMate maintains a **per-session history stack**:

| Action | Effect |
|---|---|
| **Filter** applied | Push current state to undo stack, clear redo stack |
| **Undo** clicked | Pop from undo stack, push to redo stack, restore previous state |
| **Redo** clicked | Pop from redo stack, push to undo stack, re-apply state |
| **Unfilter** clicked | Uses history undo if available, otherwise clears filter. Affects undo stack. |

Button states update after each operation:
- Undo enabled when undo stack is non-empty
- Redo enabled when redo stack is non-empty
- Both disabled when on EXPORTING tab

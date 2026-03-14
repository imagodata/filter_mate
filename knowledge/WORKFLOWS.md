# FilterMate — User Workflows

Step-by-step guides for common FilterMate tasks. Each workflow assumes the FilterMate dock panel is open in QGIS.

---

## Workflow 1: Basic Filtering by Feature Selection

**Goal:** Show only the features you've selected — filter a layer to just one or a few features.

**Steps:**

1. In the **EXPLORING ZONE** (top of the dock), the **Source Layer** is implicitly the layer you'll work with. But first, go to the **FILTERING TAB** (bottom) and select your layer in the **Source Layer** combobox.
   - Only vector layers with geometry appear here.

2. Back in the **EXPLORING ZONE**, the **SINGLE SELECTION** GroupBox should be expanded and checked (it is by default).

3. In the **QgsFieldExpressionWidget** below the picker, choose a display field — e.g., `"name"` or `"id"` — so features are labelled meaningfully in the picker.

4. In the **QgsFeaturePickerWidget**, type to search for a feature by name, or use the ← → browse buttons to step through features.
   - The picker loads up to 10,000 features.

5. Select the feature you want to filter to.

6. Click the **Filter** button in the **Action Bar**.

**Result:** The source layer is filtered — only the selected feature(s) remain visible on the map. Other features are hidden (a subset string / SQL WHERE clause is applied internally).

**To remove the filter:** Click **Unfilter** in the Action Bar.

---

## Workflow 2: Geometric Filtering with Buffer

**Goal:** Filter a target layer to show only features within a set distance of a reference feature.

**Example:** Show all buildings within 500m of a selected park.

**Steps:**

1. In the **FILTERING TAB**, set the **Source Layer** to your reference layer (e.g., "Parks").

2. In the **EXPLORING ZONE**, select the reference feature (the park you want to use) using the feature picker.

3. In the **FILTERING TAB** left sidebar, enable the **Layers to Filter** toggle (icon: `layers.png`).
   - The **Target Layers** checkable combobox appears.
   - Check the layer(s) you want to filter (e.g., "Buildings").

4. Enable the **Geometric Predicates** toggle (icon: `geo_predicates.png`).
   - The predicates combobox appears.
   - Check `intersects` (or `within`, etc.) as appropriate.

5. Enable the **Buffer Value** toggle (icon: `buffer_value.png`).
   - The buffer spinbox appears.
   - Enter a distance value (e.g., `500` for 500 map units — check your CRS for units).
   - *(Optional)* Click the **PropertyOverrideButton** (yellow icon) to write a dynamic expression for the buffer distance instead of a fixed number.

6. *(Optional)* Enable **Centroid** checkboxes for source and/or target layers to speed up the spatial query (trades precision for speed).

7. *(Optional)* Enable **Buffer Type** toggle to control the buffer shape (round vs. flat).

8. Click **Filter** in the Action Bar.

**Result:** The target layer (Buildings) is filtered to show only features that satisfy the spatial predicate relative to the buffered source geometry (Park + 500m buffer).

---

## Workflow 3: Multi-Layer Filtering

**Goal:** Filter multiple layers at once using the same source geometry.

**Example:** Select a city boundary and simultaneously filter roads, buildings, and POIs to that boundary.

**Steps:**

1. Set the **Source Layer** (e.g., "City Boundaries") in the FILTERING TAB.

2. Select the reference feature in the EXPLORING ZONE.

3. Enable the **Layers to Filter** toggle → the Target Layers combobox appears.
   - Check all layers you want to filter (e.g., Roads ✅, Buildings ✅, POIs ✅).

4. Enable the **Combine Operator** toggle (icon: `add_multi.png`).
   - Two AND/OR dropdowns appear:
     - **Source layer operator:** How to combine if multiple source features are selected (e.g., `OR` = union of geometries, `AND` = intersection)
     - **Other layers operator:** How to combine conditions across the target layers

5. Set predicates and buffer as needed (see Workflow 2).

6. Click **Filter**.

**Result:** All checked target layers are filtered simultaneously. Each layer now shows only features that satisfy the spatial relationship with the selected source feature(s).

---

## Workflow 4: Data Exploration

**Goal:** Browse features visually — identify attributes, zoom to locations, highlight on map.

**Steps:**

1. Set the **Source Layer** (any vector layer with geometry).

2. In the EXPLORING ZONE, use the **SINGLE SELECTION** GroupBox:
   - Set the display field to something meaningful (e.g., `"name"`).
   - Use the feature picker to find and select a feature.

3. Use the sidebar buttons to explore:

   - **Identify** (icon: `identify_alt.png`) — Click to open the Identify Results panel showing all attributes of the selected feature. Useful for inspecting without opening the full attribute table.

   - **Zoom** (icon: `zoom.png`) — Click to zoom and pan the map to the selected feature's bounding box.

   - **Select** (icon: `select_black.png`, toggle) — Enable to automatically select (highlight) the feature on the map canvas whenever you pick it in the explorer.

   - **Track** (icon: `track.png`, toggle) — Enable to **auto-zoom** every time you change the selected feature. Great for browsing features sequentially — the map follows you.

   - **Link** (icon: `link.png`, toggle) — Enable to synchronize all three selection GroupBoxes. Changing the selection in Single Selection updates Multiple and Custom as well.

4. Use ← → browse buttons in the picker to step through features while Track is ON — the map automatically zooms to each feature as you browse.

5. When done exploring, click **Reset** (icon: `reset_properties.png`) to clear all exploring state.

---

## Workflow 5: Export to GeoPackage

**Goal:** Export a subset of your project's layers to a GeoPackage file with styles and QGIS project embedded.

**Steps:**

1. In the **TOOLBOX ZONE**, click the **EXPORTING** tab.

2. Enable the **Layers** toggle (icon: `layers.png`).
   - The Layers combobox appears.
   - Check all layers you want to include in the export.

3. *(Optional)* Enable the **Projection** toggle (icon: `projection_black.png`).
   - The CRS selector appears.
   - Choose the output CRS (e.g., EPSG:4326 for WGS84). If not set, each layer keeps its native CRS.

4. *(Optional)* Enable the **Styles** toggle (icon: `styles_black.png`).
   - Choose whether to embed layer styles. This preserves symbology, labels, and renderer settings.

5. *(Optional)* Enable the **Datatype** toggle (icon: `datatype.png`).
   - Select the output format (GeoPackage is the primary option).

6. Enable the **Output Folder** toggle (icon: `folder_black.png`).
   - Type a path or click the browse button to choose the output directory.
   - *(Optional)* Check the **Batch** checkbox to export each layer as a separate file.

7. *(Optional)* Enable the **Zip** toggle (icon: `zip.png`).
   - Choose a ZIP file path. The export will be compressed into a `.zip`.
   - *(Optional)* Check the **Batch** checkbox for per-layer ZIP files.

8. Click **Export** in the Action Bar.

**Result:** A GeoPackage (`.gpkg`) is created containing:
- Selected layers (with any active filters applied — exports what's currently visible)
- Embedded QGIS project preserving layer groups, styles, and CRS
- Optionally compressed as ZIP

---

## Workflow 6: Using the Favorites System

**Goal:** Save a filter configuration to reuse later without reconfiguring everything.

### Saving a Favorite

1. Set up a complete filter configuration (source layer, target layers, predicates, buffer, etc.).
2. Click the **star button** (⭐) to open the Favorites Widget.
3. Click **Save / Add Favorite**.
4. Give the favorite a name.
5. The favorite is stored with:
   - All filter settings
   - Layer references
   - Spatial extent (current map view)

### Loading a Favorite

1. Click the **star button** to open the Favorites Manager dialog.
2. Browse or search for the saved favorite.
3. Click **Apply** — all filter settings are restored instantly.
4. Click **Filter** in the Action Bar to apply the restored filter.

**Notes:**
- If the layers referenced by the favorite no longer exist in the project, loading may fail or partially restore.
- Favorites can be shared between users if the layer sources are accessible from both machines.

---

## Workflow 7: Undo / Redo Filters

**Goal:** Step back and forward through filter history.

**Steps:**

1. Apply one or more filters using the **Filter** button.

2. The **Undo** button in the Action Bar becomes active after the first filter.

3. Click **Undo** → the previous filter state is restored (or the filter is removed if it was the first one).

4. Click **Redo** → re-applies the undone filter.

5. For full history, check the **History Widget** — it shows all filter operations in the session, and you can navigate to any point.

**Notes:**
- Undo/Redo is session-based (not persisted between QGIS restarts).
- Clicking **Unfilter** restores the previous filter state via history (undo), or clears filters entirely if no history. Affects all layers that have active filters. Use Undo for step-by-step reversal.

---

## Workflow 8: Custom Expression Filtering

**Goal:** Filter a layer using any QGIS expression instead of picking features from a list.

**Example:** Filter a population layer to show only cities with population > 1,000,000.

**Steps:**

1. Set the **Source Layer** in the FILTERING TAB.

2. In the **EXPLORING ZONE**, expand and check the **CUSTOM SELECTION** GroupBox (third one, collapsed by default).
   - Uncheck SINGLE SELECTION and MULTIPLE SELECTION if they are active.

3. In the **QgsFieldExpressionWidget**, write your QGIS expression:
   - Example: `"population" > 1000000`
   - Example: `"type" = 'capital' AND "country" = 'France'`
   - The expression builder button opens the full QGIS expression dialog with autocomplete, function browser, and field list.

4. Click **Filter** in the Action Bar.

**Result:** The layer is filtered to only show features matching your expression. FilterMate converts this expression into a subset string (SQL WHERE clause) applied to the layer.

---

## Workflow 9: Backend Override

**Goal:** Manually switch the query backend for a layer (e.g., to troubleshoot or test performance).

**Steps:**

1. Load a layer (e.g., a PostGIS layer — FilterMate would normally use the PostgreSQL backend).

2. Look at the **Backend Indicator** widget — it shows the current backend (e.g., `PostgreSQL`).

3. **Click** the Backend Indicator to open a context menu.

4. The menu shows the available backends for the current layer:
   - `PostgreSQL`
   - `Spatialite`
   - `OGR`
   - `Memory`

5. Click a backend to **force** FilterMate to use it.

6. Apply a filter normally — FilterMate will now use the selected backend.

**Use Cases:**
- **Troubleshooting:** A PostGIS layer's filter produces wrong results → force OGR backend to compare
- **Performance testing:** Compare filter speed between PostgreSQL and OGR backends
- **Compatibility:** Some data sources behave differently depending on the backend

---

## Workflow 10: Combining Workflows (Power Use)

**Goal:** Filter multiple layers by a buffered reference feature, then export results to GeoPackage.

**Steps:**

1. **Configure Exploring:**
   - Set Source Layer to your reference layer
   - Select the reference feature(s) using SINGLE or MULTIPLE SELECTION

2. **Configure Filtering:**
   - Enable Layers to Filter → select target layers
   - Enable Geometric Predicates → choose `intersects`
   - Enable Buffer Value → set distance
   - Enable Centroid (optional, for speed)

3. **Apply:** Click **Filter**

4. **Switch to Exporting tab:**
   - Enable Layers → select all target layers
   - Enable Projection → choose output CRS
   - Enable Styles → include styles
   - Enable Output Folder → set path

5. **Export:** Click **Export**

**Result:** Filtered data exported to GeoPackage with full QGIS project embedded.

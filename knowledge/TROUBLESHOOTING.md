# FilterMate — Troubleshooting Guide

Common issues, their causes, and how to fix them.

---

## UI / Display Issues

### No layers appear in the Source Layer combobox
**Symptom:** The Source Layer dropdown in the FILTERING TAB is empty or doesn't show expected layers.

**Cause:** FilterMate only shows vector layers **with geometry**. Geometry-less attribute tables (e.g., CSV joins, non-spatial tables) are excluded.

**Fix:**
- Ensure your layer is a vector layer with actual geometry (points, lines, or polygons).
- Check the Layers Panel in QGIS — if the layer has no geometry icon, it won't appear.
- WFS and PostGIS views without geometry are also excluded.

---

### Features not appearing in the feature picker
**Symptom:** The QgsFeaturePickerWidget (Single Selection) shows no results or only partial results.

**Causes & Fixes:**
1. **Display field is invalid** — The `QgsFieldExpressionWidget` below the picker controls what label is shown. If the expression is broken or the field doesn't exist, the picker may appear empty. Try setting the display field to a simple field name like `"fid"` or `"id"`.
2. **Layer has 0 features** — Check the layer in QGIS (open attribute table). If it truly has no features, there's nothing to pick.
3. **Layer is filtered** — If the layer already has an active subset string from a previous filter, only matching features are shown. Click **Unfilter** to clear.
4. **Too many features** — The picker loads a maximum of **10,000 features**. For very large layers, narrow your search by typing in the picker's search box.
5. **Layer not set as source** — Make sure the correct layer is selected in the Source Layer combobox in the FILTERING TAB.

---

### Dark mode icons look wrong / inverted incorrectly
**Symptom:** After switching QGIS between dark and light theme, some FilterMate icons appear as wrong color or invisible.

**Cause:** The theme watcher detects theme changes and inverts icons, but sometimes the signal doesn't fire immediately.

**Fix:**
1. Wait a moment — the theme watcher may update shortly.
2. If icons stay wrong: **disable and re-enable** FilterMate in QGIS Plugin Manager (Plugins → Manage and Install Plugins → find FilterMate → uncheck and recheck).
3. Restart QGIS if the issue persists.

---

### The dock panel is very small / cramped
**Symptom:** UI elements are cut off or too small to use.

**Fix:**
- Resize the dock by dragging its edges.
- **Minimum size is 356×317px** — below this, UI elements will overlap.
- Try floating the dock (double-click the title bar) and making it larger.
- Use the splitter between EXPLORING and TOOLBOX zones to redistribute vertical space.

---

## Filter Issues

### Filter button is disabled (grayed out)
**Symptom:** The **Filter** button in the Action Bar is not clickable.

**Cause:** No valid filter configuration exists. FilterMate requires at minimum:
- A **Source Layer** selected
- AND at least one of: a feature selected (Single/Multiple) OR a valid custom expression (Custom Selection)

**Fix:**
1. Check that a layer is selected in the Source Layer combobox.
2. Check that one of the three Selection GroupBoxes is active (checked) and has a valid selection:
   - Single Selection: a feature must be chosen in the picker
   - Multiple Selection: at least one feature must be checked
   - Custom Selection: a valid QGIS expression must be entered (green border = valid)
3. If using Custom Selection, make sure the expression is syntactically valid (the widget shows red/green border as validation feedback).

---

### Filter applies but nothing changes on the map
**Symptom:** Clicking Filter completes without error, but all features remain visible.

**Causes & Fixes:**
1. **Wrong target layer** — If "Layers to Filter" is OFF, FilterMate filters the source layer itself. If you expected another layer to be filtered, enable the toggle and select the target layers.
2. **All features match** — The spatial predicate matched all features (common with `disjoint` or a very large buffer). The layer IS filtered — it just happens to show everything.
3. **Backend issue** — The backend may have generated an incorrect query. Try overriding the backend via the Backend Indicator.
4. **Layer in edit mode** — See "Edit mode conflict" below.

---

### Filter produces incorrect or unexpected results
**Symptom:** The filter runs but shows wrong features.

**Causes & Fixes:**
1. **CRS mismatch** — Source and target layers are in different coordinate reference systems. QGIS reprojects on the fly, but this can cause precision issues. Try reprojecting layers to a common CRS.
2. **Buffer units wrong** — If using a buffer, check that the buffer value is in the correct units for your CRS. A buffer of `500` in degrees (WGS84) is enormous (~55,000 km). Switch to a projected CRS (meters/feet) before using buffer.
3. **Wrong predicate** — `contains` and `within` are opposite: `contains` = source contains target; `within` = target is inside source. Double-check you've chosen the right one.
4. **Centroid mode** — Centroid mode trades precision for speed. A feature's centroid may not reflect its actual spatial relationship. Disable centroid checkboxes if results are unexpected.
5. **Wrong backend** — Different backends may handle edge cases differently. Try overriding to a different backend.

---

### Slow filtering performance
**Symptom:** Applying a filter takes a long time.

**Fixes (try in order):**
1. **Enable Centroid mode** — Checking the Centroid checkbox for source and/or target layers switches from geometry-to-geometry tests to point-to-geometry tests. Much faster, especially for complex polygons.
2. **Reduce Buffer Segments** — If using a buffer with round ends, fewer segments = simpler buffer geometry = faster. Try reducing from default to 5–8 segments.
3. **Switch backend** — Click the Backend Indicator and try a different backend. PostgreSQL backend is typically fastest for PostGIS layers.
4. **Reduce target layer size** — Pre-filter the target layer with an attribute filter before using FilterMate.
5. **Reduce source feature count** — Don't select all 10,000 features if you only need a few.

---

### Buffer not working / Buffer has no effect
**Symptom:** Setting a buffer value doesn't appear to expand the filter area.

**Causes & Fixes:**
1. **Buffer Value toggle is OFF** — The buffer spinbox being visible doesn't mean it's active. Make sure the **Buffer Value** toggle button in the sidebar is checked (ON).
2. **Buffer value is 0** — Check the spinbox; it may have defaulted to 0.
3. **Wrong CRS units** — Using degrees instead of meters. In WGS84, `1` degree ≈ 111km. Use a metric projected CRS for meaningful buffers.
4. **Buffer Type toggle not set** — If you enabled Buffer Type but set an unusual type, the buffer shape may be unexpected.

---

## Edit Mode Conflict

### Warning popup when filtering a layer in edit mode
**Symptom:** A dialog/popup appears when you try to filter a layer.

**Cause:** FilterMate cannot apply a Subset String to a layer that is currently being **edited** in QGIS (edit mode active). This is a QGIS limitation — modifying a layer's filter while edits are in progress could corrupt data.

**Fix:**
1. **Save or discard edits** — Stop editing the layer (toggle off the edit pencil icon in QGIS toolbar). Then apply the filter.
2. **Filter other layers** — If you're editing Layer A and want to filter Layer B, that's fine — only the layer in edit mode is affected.

---

## Export Issues

### Export button is disabled (grayed out)
**Symptom:** The **Export** button in the Action Bar is not clickable.

**Cause:** Minimum export configuration not met.

**Fix:** At minimum, you need:
1. At least one layer selected (enable **Layers** toggle → check at least one layer)
2. An output folder set (enable **Output Folder** toggle → enter a valid path)

Both conditions must be met for Export to activate.

---

### Export creates empty GeoPackage / layers are empty
**Symptom:** The exported file exists but layers have no features.

**Cause:** If layers are currently filtered (a Subset String is active), the export respects the filter — it exports only what's visible. If the filter returned 0 features, the export will be empty.

**Fix:**
- Click **Unfilter** before exporting if you want all features.
- Or check that your active filter is returning results before exporting.

---

### Export fails with a path error
**Symptom:** Export errors with a message about the output path.

**Fixes:**
1. Ensure the output folder **exists** and you have write permissions.
2. Avoid special characters in the path.
3. On Windows, avoid very long paths (>260 characters).
4. Make sure no other application has the output file open (e.g., QGIS itself with the previous export open).

---

## Favorites Issues

### Favorites not loading / applying correctly
**Symptom:** Opening a saved favorite doesn't restore the expected configuration, or shows an error.

**Causes & Fixes:**
1. **Source/target layers no longer exist** — Favorites store layer references by ID/name. If those layers were removed from the project, the favorite can't reconnect to them. Re-add the layers to the project with the same name/source.
2. **Layer source has changed** — If a PostGIS table was renamed or a file was moved, the layer reference breaks. Update the layer source in QGIS (Layer Properties → Source).
3. **Project was not saved before loading** — Favorites are tied to the project context. Open the correct QGIS project before applying favorites.

---

### Favorites manager doesn't open
**Symptom:** Clicking the star button (⭐) does nothing or throws an error.

**Fix:**
- Try restarting QGIS.
- Check the QGIS Python error log (Plugins → Python Console, or View → Panels → Log Messages, filter by "FilterMate") for error details.

---

## Undo / Redo Issues

### Undo button stays disabled after filtering
**Symptom:** The Undo button remains grayed out even after applying a filter.

**Cause:** The filter may not have been registered in the history (e.g., if it failed silently or the history is disabled).

**Fix:**
- Check if the filter actually applied (look at the layer's feature count or subset string in Layer Properties → Source).
- If the filter applied but Undo is still disabled, this may be a bug — check the QGIS log for errors from FilterMate.

---

## General Tips

### Check the QGIS Log
FilterMate writes diagnostic messages to the QGIS log. To view:
1. Go to **View → Panels → Log Messages** (or open from the QGIS status bar).
2. Filter by "FilterMate" or "Python" to see plugin-specific messages.
3. Error tracebacks are shown here — useful for bug reports.

### Plugin Not Loading
If FilterMate fails to load at QGIS startup:
1. Open **Plugins → Manage and Install Plugins**
2. Find FilterMate — check if it's enabled
3. Try disabling and re-enabling
4. Check minimum QGIS version compatibility (requires QGIS 3.22+)

### After a QGIS Update
Sometimes QGIS updates change APIs. If FilterMate breaks after a QGIS update:
1. Check the FilterMate plugin page for an updated version
2. Update the plugin via Plugin Manager (Plugins → Manage and Install Plugins → Upgradeable tab)

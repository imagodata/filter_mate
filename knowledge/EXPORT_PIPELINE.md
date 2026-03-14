# FilterMate — Export Pipeline

Full documentation of the export system: how it works, what it produces, and what options control it.

---

## Export Flow

1. **User switches to EXPORTING tab** (index 1 in the Toolbox Zone)
2. **Configures export options:**
   - Layers to export (checkable combobox — select which layers)
   - Projection / CRS (CRS selector widget)
   - Styles to embed (QML and/or SLD checkboxes)
   - Output format (GPKG or KML)
   - Output folder (directory picker)
   - Zip output path (optional)
3. **Clicks the Export button** in the Action Bar
4. `launchTaskEvent(state, 'export')` is called
5. **Just-in-time sync** of the `HAS_LAYERS_TO_EXPORT` flag (checked against current combobox state)
6. **ExportGroupRecapDialog** appears — a pre-export confirmation dialog:
   - Displays layer group hierarchy as a `QTreeWidget` (folders = groups, leaves = layers with icons)
   - Summary line: `"N couches dans M groupes + K hors groupe"` (N layers in M groups + K outside groups)
   - Output path displayed for review
   - **"Preserve group structure in GPKG" checkbox** — enabled only when groups exist in the selection
   - Cancel / Export buttons (Export button = green `#27ae60`, bold font)
   - Format-specific descriptive text changes based on GPKG vs KML selection
7. **If accepted** → export process begins
8. **For each selected layer:**
   - Exports features (filtered subset if a filter is active, or all features if unfiltered)
   - Optionally attaches styles (QML and/or SLD) per layer
9. **For GPKG format:** optionally embeds a QGIS project file with the layer tree structure preserved
10. **For large datasets (>10 000 features):** uses streaming export in chunks of 5 000 features to avoid memory exhaustion
11. **Batch mode:** if batch checkbox is checked, creates a separate output file per layer instead of a single combined file
12. **Zip:** if a zip output path is configured, compresses the output file(s) into a ZIP archive

---

## Supported Export Formats

### GeoPackage (GPKG)
- **Default format.** An SQLite-based container.
- Supports embedded QGIS project file (preserves layer tree, symbology, labels, CRS)
- Supports layer group structure preservation via the GeoPackage Layer Tree Writer
- Supports per-layer QML and SLD styles
- Most feature-complete option — recommended for QGIS-to-QGIS workflows

### KML
- Google Earth / OGC format
- Supports folder structure via `kml_folder_writer`
- Suitable for sharing with non-QGIS consumers
- Fewer metadata/style preservation capabilities compared to GPKG

---

## Export Styles

Two style formats can be exported and attached to each layer in the output:

| Format | Description |
|---|---|
| **QML** | QGIS native style format — full fidelity, QGIS-only |
| **SLD** | OGC Styled Layer Descriptor standard — portable, partial fidelity |

Both can be enabled simultaneously. Styles are attached per-layer in the output file metadata.

---

## GeoPackage Layer Tree Writer

When the **"Preserve group structure in GPKG"** checkbox is checked in the ExportGroupRecapDialog:

- Reads the QGIS layer tree (all groups, subgroups, and layer order)
- Serializes group structure into GPKG metadata tables
- When the resulting GPKG is opened in QGIS, it recreates the original layer tree — groups, subgroups, and layer ordering are restored automatically

This checkbox is only enabled if the selected layers include at least one that belongs to a layer group.

---

## Batch Export Mode

| Checkbox | Behavior |
|---|---|
| Batch output folder | One GPKG file per layer, all written to the output folder |
| Batch zip | One ZIP archive per layer |

File names are derived from layer names (sanitized for filesystem compatibility).

When batch mode is off (default), all selected layers are written into a single output GPKG.

---

## Export Validation

Minimum requirements for a successful export:

- At least one layer must be checked in the export combobox
- An output folder **or** a zip output path must be set
- If neither is configured, clicking Export does nothing useful (no output is produced)

These conditions are checked at export launch time (just-in-time sync of `HAS_LAYERS_TO_EXPORT`).

---

## Streaming Export (Large Datasets)

For layers with more than **10 000 features**, FilterMate switches to a streaming export mode:

- Features are processed and written in **chunks of 5 000**
- Prevents excessive memory usage during export of large PostGIS or GeoPackage tables
- Transparent to the user — same output, just handled differently internally

---

## Summary: What Gets Exported

| Component | Exported? | Condition |
|---|---|---|
| Layer features | ✅ Always | Filtered subset if filter active, all features otherwise |
| QML style | ✅ Optional | If QML checkbox enabled |
| SLD style | ✅ Optional | If SLD checkbox enabled |
| Layer group structure | ✅ Optional | If "Preserve group structure" checked (GPKG only) |
| Embedded QGIS project | ✅ Optional | GPKG only |
| CRS reprojection | ✅ Optional | If a target CRS is selected |

# FilterMate — Plugin Overview

**Version:** 4.6.1  
**Type:** QGIS Dock Widget Plugin  
**Purpose:** Spatial filtering, data exploration, and export for QGIS vector layers

---

## What Is FilterMate?

FilterMate is a QGIS plugin that lets you spatially filter, explore, and export vector data — faster and more flexibly than QGIS's built-in tools. It lives as a dockable panel inside QGIS and works with virtually any vector data source.

Instead of manually writing SQL or using QGIS's layer filter dialog, FilterMate gives you a point-and-click interface to:
- Select a reference feature (or features)
- Define a spatial relationship (intersects, within, buffer, etc.)
- Apply that filter to one or many target layers simultaneously
- Export the results

---

## Supported Data Sources

FilterMate works with **any vector layer in QGIS**:

| Source Type | Notes |
|---|---|
| PostgreSQL / PostGIS | Full native SQL support |
| Spatialite | `.sqlite` and `.gpkg` files |
| GeoPackage | `.gpkg` files |
| Shapefiles | `.shp` files |
| WFS | Web Feature Services |
| Memory layers | Temporary/scratch layers |
| Any OGR-compatible source | Broad fallback support |

---

## Multi-Backend Architecture

FilterMate automatically picks the best query engine ("backend") for each data source:

| Backend | Used For | Advantage |
|---|---|---|
| **PostgreSQL** | PostGIS layers | Native spatial SQL, server-side processing |
| **Spatialite** | SQLite/GeoPackage | Embedded spatial SQL |
| **OGR** | Shapefiles, WFS, others | Universal fallback |
| **Memory** | In-memory layers | Optimized for temporary data |

The backend is auto-selected, but you can override it per layer using the **Backend Indicator** widget. This is useful for troubleshooting or benchmarking.

---

## Key Features

### Performance
- **4 performance optimizers** built-in
- **Smart caching** to avoid redundant queries
- **2–8× faster** than native QGIS layer filtering in many scenarios
- Centroid mode for faster (but approximate) spatial operations

### Filtering
- Filter by single feature, multiple features, or any QGIS expression
- Spatial filtering with geometric predicates (intersects, contains, within, touches, crosses, overlaps, disjoint)
- Buffer support: apply a distance zone before filtering
- Multi-layer filtering: filter many layers at once from one source
- AND/OR logic to combine filter conditions
- **Undo/Redo** system for filter states

### Exploration
- Searchable feature picker (Single Selection)
- Checkable feature list (Multiple Selection)
- Free-form expression input (Custom Selection)
- Identify, zoom, select on map, and track (auto-zoom on change)

### Favorites
- Save any filter configuration as a "favorite"
- Favorites store: source layer, target layers, predicates, buffer, spatial context
- Load and apply favorites later — even across sessions
- Can be shared between users

### Export
- Export to **GeoPackage** with embedded QGIS project
- Preserves: layer groups, styles, CRS, symbology
- Optional reprojection on export
- Optional ZIP compression
- Batch export support

---

## Theme & Compatibility

- **Dark/Light theme**: Icons automatically adapt to QGIS theme (dark mode inverts icons; some icons have `_black` / `_white` variants)
- **22 languages** supported at 100% translation
- **QGIS 3.22 to 4.x** compatible
- Works with both **Qt5 and Qt6**

---

## Where It Lives in QGIS

FilterMate appears as a **dockable panel** (QDockWidget). It can be:
- Docked to any side of the QGIS window
- Floated as a standalone window
- The **Action Bar** (the row of main buttons) can be repositioned: top, bottom, left, or right of the panel

---

## Files of Interest

| File | Purpose |
|---|---|
| `knowledge/UI_GUIDE.md` | Full UI layout — every button, widget, and zone |
| `knowledge/WORKFLOWS.md` | Step-by-step user workflows |
| `knowledge/GLOSSARY.md` | Definitions of all key terms |
| `knowledge/TROUBLESHOOTING.md` | Common issues and fixes |

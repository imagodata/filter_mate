# ![FilterMate](https://github.com/imagodata/filter_mate/blob/main/icon.png?raw=true) FilterMate

**Version 4.8.9** | QGIS Plugin | **Production-Ready** 🎉

> 🚀 Explore, filter & export vector data with lightning-fast performance on ANY data source.

[![Tests](https://github.com/imagodata/filter_mate/actions/workflows/test.yml/badge.svg)](https://github.com/imagodata/filter_mate/actions/workflows/test.yml)
[![Documentation](https://img.shields.io/badge/docs-website-blue)](https://imagodata.github.io/filter_mate)
[![QGIS Plugin](https://img.shields.io/badge/QGIS-Plugin-green)](https://plugins.qgis.org/plugins/filter_mate)
[![QGIS 4 / Qt6](https://img.shields.io/badge/QGIS%204%20%2F%20Qt6-supported-brightgreen)](CHANGELOG.md#488---2026-09-12)
[![GitHub](https://img.shields.io/badge/GitHub-repo-black)](https://github.com/imagodata/filter_mate)
[![Issues](https://img.shields.io/badge/issues-report-red)](https://github.com/imagodata/filter_mate/issues)

**QGIS 3 / Qt5 and QGIS 4 / Qt6:** v4.8.9 is a measured performance release: spatial cascades on GeoPackage use the R-tree (371 s to under 3 s on a 37-layer project), PostgreSQL targets keep their GiST index with the centroid option, no more connection stalls on `localhost`, and the canvas is redrawn once per task. See [what's new](#-whats-new-in-489).

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Search** | Intuitive entity search across all layer types |
| 📐 **Geometric Filtering** | Spatial predicates with buffer support |
| ⭐ **Filter Favorites** | Save and reuse filter configurations |
| 🤝 **Favorites Sharing** | Publish favorites to git repos with QGIS authcfg credentials |
| 🌐 **REST API** | Drive FilterMate from external tools (X-API-Key auth) |
| 📝 **Undo/Redo** | Complete filter history |
| 🌍 **34 Languages** | Full internationalization |
| 🎨 **Dark Mode** | Automatic theme detection |
| 📦 **GPKG Project Export** | Embedded QGIS project with group hierarchy, styles & CRS |
| 🚀 **Multi-Backend** | PostgreSQL, Spatialite, OGR |
| 🧰 **Processing Toolbox** | Batch-filter multiple layers with one expression, from the Processing panel or a model |

### 🆕 What's new in 4.8.9

- **GeoPackage cascades use the spatial index**: the Spatialite expression starts with the R-tree candidate clause GDAL uses for its own spatial filter. Filtering 37 BD TOPO layers by the commune of Toulouse took 371 s; it now takes 1.6 to 3 s. No second full scan after a filter (`reload()` removed on PostgreSQL/OGR).
- **PostgreSQL with the centroid option keeps its GiST index**: `"t"."geom" && source` is tested before `ST_Intersects(ST_PointOnSurface("t"."geom"), source)`. A five-commune cascade went from 49.6 s to under 4 s, and the worker no longer counts each target twice.
- **Connection and rendering**: psycopg2 tries an IPv4 `hostaddr` with `gssencmode=disable` first (a 21 s stall on `localhost` resolving to IPv6 first), the canvas is frozen for the whole task and redrawn once, no auto-zoom after unfilter/reset, no fixed pauses between layers of the same GeoPackage.
- **Fix**: a filter launched with no target layer no longer fails.
- More `⏱` timing lines in `filtermate.log` (`pg_layer_connect`, `apply_subsets`, `apply_subset_layer`, `layer_filter`, `cascade_filter`, `set_subset`).

See the [4.8.9 changelog](CHANGELOG.md#489---2026-09-12) for details.

### What's new in 4.8.8

- **No more freezes on large layers**: the multiple-selection list loads at most `feature_picker_limit` rows (default 1000, sorted). When truncated, the text filter searches the whole layer, "Select All" loads the full list and canvas selections beyond the loaded rows are fetched by identifier. A click on a row is one indexed lookup instead of a full-layer scan.
- **Faster project load**: layer variables are applied per layer in one batched write instead of 42 gated writes per layer; unchanged values are skipped; display-field detection is memoised.
- **Filter engine**: GEOS cascaded union replaces the quadratic `combine()` loop, Spatialite source features load without attributes, interruptible SQLite queries wake up as soon as the worker finishes.
- **Hygiene**: stale unsaved projects are purged from the FilterMate database, INFO log level by default (`FILTERMATE_LOG_LEVEL=DEBUG` for verbose output), and three timing lines (`⏱ project_open`, `⏱ layer_change`, `⏱ task_filter`) in `filtermate.log` to compare releases.

See the [4.8.8 changelog](CHANGELOG.md#488---2026-09-12) for details.

### What's new in 4.8.7

- **Consistent panels**: Exploring and Filtering share input dimensions, button-bar styles and checkboxes across dark, light and gray themes. Gutters match the panel background, with more space below Exploring titles.
- **Readable configuration**: white labels and values on dark backgrounds, including custom configuration cells.
- **Theme-change fix**: remove the obsolete `IconManager.set_theme()` call that raised an error on QGIS palette changes.
- **Project shutdown**: cancel pending layer additions and avoid repeated per-layer cleanup when removing all layers or unloading the plugin.

See the [4.8.7 changelog](CHANGELOG.md#487---2026-09-09) for details.

### What's new in 4.8.6

- **QGIS themes**: follow native colors in Default, Night Mapping and Blend of Gray. Existing `default` settings now follow QGIS; choose `light` or `dark` to force an appearance.
- **Readable icons**: invert PNG artwork in dark mode and refresh icons after startup and subsequent changes, including tabs and centroid controls.
- **Filtering alignment**: match the upper and lower icon-rail widths and expand the second layer row like the first. All buttons and their dimensions are preserved.
- **Compatibility**: retain the Qt5/Qt6 checkbox and mouse-event fixes. The 37 targeted theme/configuration tests pass under both bindings; see [validation details](docs/UI_UX_QGIS4.md).

### What's new in 4.8.4

- **Checkbox rendering**: correct the QStyle primitive name used by the custom delegate.
- **Feature-list clicks**: support both Qt5 `pos()` and Qt6 `position()`.
- **Tests**: 1499 passed, 1 skipped (Python 3.12).

### What's new in 4.8.3

- **Config log cleanup**: the "Schema file not found" message logged on every config reload (the schema was intentionally removed as unused in an earlier release) is now `Info` instead of `Warning`. Also closed out 2 live-testing reports as confirmed non-bugs: the `QGIS3`-named settings path is QGIS 4.2's own behavior, and a 33%-stuck "Adding layers" dialog turned out to be QGIS's own project loader, not FilterMate.
- **Tests**: 1493 ✅.

### What's new in 4.8.2

- 🚑 **Second QGIS 4.x hotfix**: v4.8.1's dockwidget fix still crashed (`DockWidgetFeature has no attribute 'AllDockWidgetFeatures'`) — that convenience constant was deprecated in Qt 5.13 and is fully removed in Qt6, not just moved into a nested enum. Now ORs the 3 individual flags it used to stand for.
- **Tests**: 1493 ✅.

### What's new in 4.8.1

- 🚑 **Critical QGIS 4.x fix**: the dockwidget could fail to load entirely on QGIS 4.x — PyQt6's UI loader can't resolve the `.ui` file's dock-widget `features` flag, so plugin startup crashed outright. Now set programmatically instead. Also fixed the new Processing Toolbox algorithm crashing on open (`BatchFilterAlgorithm.tr()` was missing — `QgsProcessingAlgorithm` never provides it). Found via real-world QGIS 4.2/Windows testing right after v4.8.0.
- **Tests**: 1493 ✅.

### What's new in 4.8.0

- 🎉 **Full QGIS 4.2 / Qt6 support**: closed out every remaining PyQt5→PyQt6 gap found by three sweeps across the codebase — `QgsField.type()` field-detection migrated to `QMetaType.Type`, `QShortcut` moved back to `QtGui` (Qt6 relocated it there along with `QAction`/`QActionGroup`/`QFileSystemModel`/`QUndoCommand`/`QUndoGroup`/`QUndoStack`, which was breaking dockwidget keyboard shortcuts and the JSON config search widget at load time), and the last flat PyQt5-style enum accesses qualified to their scoped form. Two new AST-based static regression guards keep these bug classes from resurfacing.
- **New — Processing Toolbox**: FilterMate algorithms are now registered via a `QgsProcessingProvider`. First algorithm, **"Filtrer plusieurs couches (batch)"**, applies one filter expression to multiple vector layers in a single run — usable from Processing models and batch processing.
- **Tests**: 1486 ✅ (7 pre-existing, unrelated export-pipeline failures tracked separately).

---

## 📦 Installation

### From QGIS Plugin Repository (Recommended)

1. QGIS → `Plugins` → `Manage and Install Plugins`
2. Search "FilterMate" → `Install Plugin`

### Manual Installation

Download from [GitHub Releases](https://github.com/imagodata/filter_mate/releases) and extract to:

| OS | Path |
|---|---|
| **Windows** | `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\` |
| **Linux** | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/` |
| **macOS** | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/` |

### Optional: PostgreSQL Support

```bash
pip install psycopg2-binary
```

---

## 🎬 Video Tutorials

| Tutorial | Link |
|----------|------|
| 📺 Complete Overview | [Watch](https://www.youtube.com/watch?v=2gOEPrdl2Bo) |
| 🔍 Dataset Exploration | [Watch](https://youtu.be/YwEalDjgEdY) |
| 🛣️ Road Network Filtering | [Watch](https://youtu.be/svElL8cDpWE) |
| 📦 GeoPackage Export | [Watch](https://youtu.be/gPLi2OudKcI) |
| 📐 Negative Buffer | [Watch](https://youtu.be/9rZb-9A-tko) |

---

## ⚡ Backend Performance

| Backend | 10k | 100k | 1M Features |
|---------|:---:|:----:|:-----------:|
| 🟢 PostgreSQL | <1s | <2s | ~10s |
| 🔵 Spatialite | <2s | ~10s | ~60s |
| 🟠 OGR | ~5s | ~30s | >120s |

**Tip**: Install `psycopg2-binary` for optimal performance with large datasets.

---

## 📋 Requirements

- **QGIS**: 3.22+ — including **QGIS 4.x / Qt6** (fully supported since v4.8.0)
- **Python**: 3.9+ (included with QGIS)
- **Optional**: psycopg2 for PostgreSQL backend

---

## 📚 Documentation

- **Users**: [Documentation Website](https://imagodata.github.io/filter_mate)
- **Developers**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

## 🤝 Contributing

See [Contributing Guidelines](.github/copilot-instructions.md)

---

## 📄 License

GNU General Public License v3.0 - See [LICENSE](LICENSE)

---

**Developed by**: imagodata | **Contact**: simon.ducournau+filter_mate@gmail.com

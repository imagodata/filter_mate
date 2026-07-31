# ![FilterMate](https://github.com/imagodata/filter_mate/blob/main/icon.png?raw=true) FilterMate

**Version 4.8.2** | QGIS Plugin | **Production-Ready** 🎉

> 🚀 Explore, filter & export vector data with lightning-fast performance on ANY data source.

[![Tests](https://github.com/imagodata/filter_mate/actions/workflows/test.yml/badge.svg)](https://github.com/imagodata/filter_mate/actions/workflows/test.yml)
[![Documentation](https://img.shields.io/badge/docs-website-blue)](https://imagodata.github.io/filter_mate)
[![QGIS Plugin](https://img.shields.io/badge/QGIS-Plugin-green)](https://plugins.qgis.org/plugins/filter_mate)
[![QGIS 4 / Qt6](https://img.shields.io/badge/QGIS%204%20%2F%20Qt6-supported-brightgreen)](CHANGELOG.md#482---2026-07-31)
[![GitHub](https://img.shields.io/badge/GitHub-repo-black)](https://github.com/imagodata/filter_mate)
[![Issues](https://img.shields.io/badge/issues-report-red)](https://github.com/imagodata/filter_mate/issues)

🎉 **FilterMate now fully supports QGIS 4.2 / Qt6** — alongside QGIS 3.22+ / Qt5 — after three sweeps closing out every remaining PyQt5→PyQt6 compatibility gap, plus static regression guards to keep it that way. v4.8.2 fixes a second dockwidget-load crash on QGIS 4.x found right after v4.8.1 shipped. See [what's new](#-whats-new-in-482).

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

### 🆕 What's new in 4.8.2

- 🚑 **Second QGIS 4.x hotfix**: v4.8.1's dockwidget fix still crashed (`DockWidgetFeature has no attribute 'AllDockWidgetFeatures'`) — that convenience constant was deprecated in Qt 5.13 and is fully removed in Qt6, not just moved into a nested enum. Now ORs the 3 individual flags it used to stand for.
- **Tests**: 1493 ✅.

### What's new in 4.8.1

- 🚑 **Critical QGIS 4.x fix**: the dockwidget could fail to load entirely on QGIS 4.x — PyQt6's UI loader can't resolve the `.ui` file's dock-widget `features` flag, so plugin startup crashed outright. Now set programmatically instead. Also fixed the new Processing Toolbox algorithm crashing on open (`BatchFilterAlgorithm.tr()` was missing — `QgsProcessingAlgorithm` never provides it). Found via real-world QGIS 4.2/Windows testing right after v4.8.0.
- **Tests**: 1493 ✅.

### What's new in 4.8.0

- 🎉 **Full QGIS 4.2 / Qt6 support**: closed out every remaining PyQt5→PyQt6 gap found by three sweeps across the codebase — `QgsField.type()` field-detection migrated to `QMetaType.Type`, `QShortcut` moved back to `QtGui` (Qt6 relocated it there along with `QAction`/`QActionGroup`/`QFileSystemModel`/`QUndoCommand`/`QUndoGroup`/`QUndoStack`, which was breaking dockwidget keyboard shortcuts and the JSON config search widget at load time), and the last flat PyQt5-style enum accesses qualified to their scoped form. Two new AST-based static regression guards keep these bug classes from resurfacing.
- **New — Processing Toolbox**: FilterMate algorithms are now registered via a `QgsProcessingProvider`. First algorithm, **"Filtrer plusieurs couches (batch)"**, applies one filter expression to multiple vector layers in a single run — usable from Processing models and batch processing.
- **Tests**: 1486 ✅ (7 pre-existing, unrelated export-pipeline failures tracked separately).

### What's new in 4.7.3

- **Crash fix**: dockable panel creation could fail outright on QGIS 4.0.1 / Windows ("No module named 'sip'") due to an unguarded top-level `import sip`; routed through the plugin's already-hardened sip-safety helper instead. (#47)
- **Security**: resolved every Bandit finding — real fixes (asserts replaced with explicit raises, corrected `nosec` code for the ElementTree import) plus documented suppressions for reviewed-safe patterns. Zero unresolved findings on re-scan.
- **Qt6 readiness**: qualified ~165 flat PyQt/PyQGIS enum accesses to their scoped form and dropped `.exec_()` across 50 files — purely additive, no behavior change on the current Qt5 install.
- **Tests**: 1491+ ✅.

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

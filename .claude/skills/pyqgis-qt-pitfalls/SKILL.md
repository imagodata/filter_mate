---
name: pyqgis-qt-pitfalls
description: Pitfalls of PyQGIS and Qt met while developing FilterMate across QGIS 3.22 to 4.x (Qt5 and Qt6) - enums, imports, the dock and its stylesheets, the configuration tree, rendering, the plugin repository scan. Use when writing or reviewing code of the plugin that touches Qt widgets, QGIS APIs that changed between versions, or the packaging of a release.
---

# PyQGIS and Qt in FilterMate

The plugin runs on QGIS 3.22 (Qt5) to QGIS 4.x (Qt6). Check in 3.22, LTR and latest (skill `qgis-headless-bench`).

## Qt5 and Qt6

- Enums are scoped in Qt6: write `Qt.ItemDataRole.UserRole`, `Qt.AlignmentFlag.AlignLeft`,
  `QDialog.DialogCode.Accepted`; the flat forms fail in Qt6. The plugin repository rejects flat enums too.
- Moved classes: `QShortcut` is in QtGui in Qt6, QtWidgets in Qt5 (try one, fall back to the other).
- `QPainter.drawEllipse(QPointF, rx, ry)` needs a `QPointF` in PyQt6.
- Field types: `QMetaType` from QGIS 3.38, `QVariant` before.

## The plugin package

- Imports inside the plugin are relative (`from ..config import UIConfig`). An absolute import (`from ui.config
  import ...`) works in the tests, where the root is on the path, and fails in QGIS: a setting did nothing for months
  because of one.
- `metadata.txt` is read by configparser: no `%` anywhere.
- The plugin repository scans each release (Bandit, detect-secrets, Qt6 enums); reproduce the scan before uploading.

## The dock

- `QToolBox` sizes its tab buttons from their size hint and ignores stylesheet heights. A new stylesheet (a change
  of theme) gives them their hint again: apply the dimensions of the profile again after it
  (`apply_dynamic_dimensions`).
- A widget of the dock that styles itself must keep its look when the dock resets styles (the `OWN_STYLE_PROPERTY`
  convention of the agent panel).
- `QApplication.processEvents()` in a handler can run another handler of the same widget: guard the state first.
- A modal dialog in a code path that the headless checks reach hangs them: make the question injectable.

## The configuration tree

- Edit a value as its editor does: set the display text, then the value dict in `UserRole` (`ChoicesType` /
  `ConfigValueType.setModelData`); `itemChanged` runs the live handlers and saves. Rebuilding the model skips them.
- A section shown under a `_display_name` keeps its JSON key in the `UserRole` of its key item.
- `CONFIG_DATA` is shared by reference (`ENV_VARS`, the registry): mutate it in place, never rebind it.

## Rendering and maps

- `canvas.grab()` can return the previous frame: render with `QgsMapRendererSequentialJob` for a picture.
- `QgsRubberBand.setToGeometry(geometry, crs)`: pass the CRS of the geometry.

## Threads

- `QgsTask` work runs off the main thread: never touch widgets or the project there; hand results back in
  `finished()`. Closing a task from `taskTerminated` crashed QGIS 4.2.
- Network: through `QgsNetworkAccessManager` (the plugin's `bounded_http`), never `urllib` in the plugin.

# FilterMate — Theme & Styling System

> How FilterMate detects, applies, and manages visual themes.
> Covers QSS stylesheets, icon theming, button styling, and the QGIS theme watcher.

---

## Architecture Overview

```
QGISThemeWatcher (singleton)
  │ watches QApplication.paletteChanged
  │
  ├──→ StyleLoader.detect_qgis_theme()
  │      └→ luminance check: dark if < 128, light otherwise
  │
  ├──→ ThemeManager.set_theme(new_theme)
  │      ├→ loads QSS from resources/styles/{theme}.qss
  │      ├→ replaces {color_*} placeholders with theme colors
  │      ├→ applies stylesheet to dockWidgetContents (NOT the QDockWidget)
  │      └→ notifies callbacks
  │
  ├──→ IconManager.on_theme_changed(new_theme)
  │      ├→ swaps variant icons (_black ↔ _white)
  │      ├→ inverts force-invert icons
  │      ├→ skips never-invert icons (logo, icon.png)
  │      └→ clears icon cache
  │
  └──→ ButtonStyler.on_theme_changed(new_theme)
         └→ re-applies button QSS with new colors
```

---

## Theme Detection

**How QGIS theme is detected:**
```python
palette = QgsApplication.palette()
bg_color = palette.color(palette.Window)
luminance = 0.299 * R + 0.587 * G + 0.114 * B
→ luminance < 128 = "dark"
→ luminance ≥ 128 = "default" (light)
```

**When detection runs:**
- Plugin startup → `ThemeManager.setup()`
- QGIS palette change → `QGISThemeWatcher._on_palette_changed()`
- Manual theme change via config

---

## 3 Built-in Themes

### Color Schemes

| Color Variable | Default (Light) | Dark | Light |
|---|---|---|---|
| `color_bg_0` (frame bg) | `#EFEFEF` | `#1E1E1E` | `#FFFFFF` |
| `color_1` (widget bg) | `#FFFFFF` | `#252526` | `#F8F8F8` |
| `color_2` (selection bg) | `#D0D0D0` | `#37373D` | `#CCCCCC` |
| `color_bg_3` (hover) | `#2196F3` | `#0E639C` | `#2196F3` |
| `color_3` (text accent) | `#4A4A4A` | `#CCCCCC` | `#333333` |
| `color_font_0` (primary) | `#1A1A1A` | `#D4D4D4` | `#000000` |
| `color_font_1` (secondary) | `#4A4A4A` | `#9D9D9D` | `#333333` |
| `color_font_2` (muted) | `#888888` | `#6A6A6A` | `#999999` |
| `color_accent` | `#1565C0` | `#007ACC` | `#1976D2` |
| `color_accent_hover` | `#1E88E5` | `#1177BB` | `#2196F3` |
| `color_accent_pressed` | `#0D47A1` | `#005A9E` | `#0D47A1` |
| `color_accent_light_bg` | `#E3F2FD` | `#264F78` | `#E3F2FD` |
| `color_accent_dark` | `#01579B` | `#FFFFFF` | `#0D47A1` |
| `icon_filter` | `none` | `invert(100%)` | `none` |

---

## QSS Stylesheets

### Files
- **`resources/styles/default.qss`** — Main stylesheet (1215 lines), used for all themes
- **`resources/styles/dynamic_template.qss`** — Template for dynamic style generation (509 lines)

### How Colors Are Applied

The QSS file contains placeholders like `{color_bg_0}`, `{color_accent}`, etc. At load time, `ThemeManager._load_stylesheet()` replaces each placeholder with the actual color value from the active theme's `COLOR_SCHEMES`.

### Scope: dockWidgetContents Only

**Critical design decision:** Styles are applied to `#dockWidgetContents`, NOT the `QDockWidget` itself. This prevents FilterMate's styles from leaking into QGIS child dialogs (like the Expression Builder). All QSS selectors are prefixed with `#dockWidgetContents`.

### Styled Widget Types

The QSS covers these widget types (all scoped to `#dockWidgetContents`):

| Widget | Styled Properties |
|---|---|
| **Splitter** | Handle color (2px rounded), hover/pressed accent, vertical 6px height, horizontal 6px width |
| **QgsMapLayerComboBox** | Background, border, padding, dropdown arrow |
| **QComboBox** | Background, border-radius 4px, padding, dropdown styling |
| **QCheckBox** | Indicator size 14×14px, background, border-radius 3px, check color |
| **QgsCollapsibleGroupBox** | Title background, border, font-weight bold, collapse indicator |
| **QToolBox** (tabs) | Tab background, selected highlight, text color, hover states |
| **QPushButton** (action) | Background gradient, border-radius, hover animation, disabled state |
| **QPushButton** (sidebar) | Flat style, 32×32px, checked state background, cursor pointer |
| **QgsDoubleSpinBox** | Background, border, alignment, special prefix/suffix styling |
| **QLineEdit** | Background, border, focus ring, placeholder color |
| **QDialogButtonBox** | OK/Cancel button styling |
| **ScrollBars** | 8px wide, rounded handle, minimal track |

---

## Icon Theming

### 3 Icon Categories

**1. Variant Icons (have _black/_white versions)**

Automatically swap between variants based on theme:

| Base Name | Light Mode | Dark Mode |
|---|---|---|
| `auto_layer` | `auto_layer_black.png` | `auto_layer_white.png` |
| `folder` | `folder_black.png` | `folder_white.png` |
| `map` | `map_black.png` | `map_white.png` |
| `pointing` | `pointing_black.png` | `pointing_white.png` |
| `projection` | `projection_black.png` | `projection_white.png` |
| `styles` | `styles_black.png` | `styles_white.png` |
| `select` | `select_black.png` | `selection_white.png` |

**2. Force-Invert Icons (single file, pixel-inverted in dark mode)**

These have only one file. In dark mode, the IconManager inverts all pixel colors:

`layers.png`, `datatype.png`, `zip.png`, `filter.png`, `undo.png`, `redo.png`, `unfilter.png`, `reset.png`, `export.png`, `identify_alt.png`, `zoom.png`, `track.png`, `link.png`, `save_properties.png`, `add_multi.png`, `geo_predicates.png`, `buffer_value.png`, `buffer_type.png`, `filter_multi.png`, `save.png`, `parameters.png`

**3. Never-Invert Icons (always shown as-is)**

`logo.png`, `icon.png` — these are the FilterMate logo/icon and should never be color-modified.

### Icon Inversion Process

```python
def _invert_pixmap(pixmap):
    image = pixmap.toImage()
    image.invertPixels()  # Inverts RGB, preserves alpha
    return QPixmap.fromImage(image)
```

### Icon Cache

Icons are cached in `_icon_cache: Dict[str, QIcon]`. Cache is cleared on theme change to force reload with new theme variant/inversion.

---

## Button Styling

### ButtonStyler — Responsive Button Sizes

Buttons adapt to the UI profile (compact/normal):

| Button Type | Compact Height | Normal Height | Compact Icon | Normal Icon |
|---|---|---|---|---|
| **Standard** (sidebar) | 24px | 28px | 16px | 20px |
| **Action** (action bar) | 28px | 36px | 20px | 24px |
| **Tool** (small) | 22px | 26px | 14px | 18px |

### Checkable Button States

Sidebar toggle buttons have 4 visual states:

| State | Appearance |
|---|---|
| **Unchecked** | Flat background, normal icon |
| **Checked** | Accent background color, icon may be inverted |
| **Hover** | Lighter accent background |
| **Disabled** | Grayed out, reduced opacity |

---

## Dialog Style Protection

### Problem
FilterMate's QSS would leak into QGIS dialogs (Expression Builder, etc.) because Qt inherits parent widget stylesheets.

### Solution: 3-Layer Protection

1. **Scope all QSS** to `#dockWidgetContents` (prevents inheritance via CSS specificity)
2. **GlobalDialogStyleFilter** — QApplication event filter that resets stylesheets on known QGIS dialogs when they're shown
3. **ChildDialogStyleFilter** — Per-widget event filter that catches child windows

### Protected Dialog Classes
Dialogs that get their stylesheet reset:
- `QgsExpressionBuilderDialog`
- `QgsExpressionBuilderWidget`
- `QgsProjectionSelectionDialog`
- `QgsNewHttpConnection`
- `QgsAuthConfigSelect`
- Any `QDialog` with "Expression" in its class name

---

## QGISThemeWatcher

**Singleton** that monitors QGIS palette changes in real-time.

### How It Works
1. Connects to `QgsApplication.paletteChanged` signal
2. On palette change → detects new theme via luminance check
3. If theme changed → notifies all registered callbacks
4. Callbacks trigger: `ThemeManager.set_theme()`, `IconManager.on_theme_changed()`, `ButtonStyler.on_theme_changed()`

### When Theme Changes Happen
- User changes QGIS theme to "Night Mapping" → palette changes → auto-detected
- User changes QGIS style/color in Settings → palette changes → auto-detected
- User manually sets theme in FilterMate config → direct set_theme()

### Cascade on Theme Change
```
Theme change detected
  → ThemeManager: reloads QSS with new colors, applies to dockWidgetContents
  → IconManager: clears cache, reloads all button icons with new variants/inversions
  → ButtonStyler: re-applies button CSS with new colors
  → JsonView (config tree): refreshes stylesheet (dark/light palette)
  → BackendIndicator: colors stay fixed (always use their own badge colors)
  → FavoritesIndicator: colors stay fixed (gold/gray)
```

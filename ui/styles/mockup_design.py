# -*- coding: utf-8 -*-
"""
FilterMate 5 design (mockup "FilterMate 5.0 — Exploring adaptatif").

One place for the look of the dock:

* Color tokens, dark (the mockup) and light (same structure, light surfaces),
  substituted into ``resources/styles/mockup.qss`` which is appended last to
  the dock stylesheet, so it wins over the older rules.
* Layer kind colors (vector blue, raster amber, point cloud teal) used by the
  badge, the layer cards and the target lists.
* The stroke icons of the mockup, drawn in the text color of the theme and
  served by :class:`IconManager` in place of the PNG files they replace.
* The badge stylesheets (backend / layer kind, favorites).
* The spacing scale (:data:`SPACING`), shared by mockup.qss (``{fm_edge}``...)
  and ``ui/layout/mockup_layout.py``.

Pure functions except :func:`render_icon`, which needs QtSvg.
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

FONT_FAMILY = "IBM Plex Sans"
MONO_FAMILY = "IBM Plex Mono"

TOKENS: Dict[str, Dict[str, str]] = {
    'dark': {
        'fm_bg': '#1c1c1c',            # dock background
        'fm_header': '#202020',        # title strip, action bar
        'fm_rail': '#262626',          # icon rails
        'fm_group': '#242424',         # collapsible groups
        'fm_group_on': '#272727',      # checked group
        'fm_group_border': '#343434',
        'fm_group_border_on': '#4a4a4a',
        'fm_field': '#333333',         # combos, line edits, spin boxes
        'fm_field_border': '#3d3d3d',
        'fm_field_hover': '#4a4a4a',
        'fm_list': '#2a2a2a',          # lists and item views
        'fm_text': '#e8e8e8',
        'fm_text_muted': '#a9a9a9',
        'fm_text_disabled': '#6f6f6f',
        'fm_hover': '#353535',         # rail button hover
        'fm_active': '#3a4656',        # checked rail button / selected chip
        'fm_active_border': '#5b7391',
        'fm_accent': '#8fc3f5',        # check boxes, focus, links
        'fm_accent_text': '#141414',
        'fm_section': '#262626',       # FILTERING / EXPORTING / CONFIGURATION headers
        'fm_section_border': '#333333',
        'fm_section_on': '#c8434a',    # open section outline (mockup red)
        'fm_danger': '#e57373',
        'fm_scroll': '#4a4a4a',
        'fm_icon': '#e6e6e6',
    },
    'light': {
        'fm_bg': '#f3f3f3',
        'fm_header': '#ebebeb',
        'fm_rail': '#e4e4e4',
        'fm_group': '#fafafa',
        'fm_group_on': '#ffffff',
        'fm_group_border': '#d9d9d9',
        'fm_group_border_on': '#bdbdbd',
        'fm_field': '#ffffff',
        'fm_field_border': '#cfcfcf',
        'fm_field_hover': '#9e9e9e',
        'fm_list': '#ffffff',
        'fm_text': '#1f1f1f',
        'fm_text_muted': '#5f5f5f',
        'fm_text_disabled': '#a0a0a0',
        'fm_hover': '#d6d6d6',
        'fm_active': '#d3e3f5',
        'fm_active_border': '#7fa6d1',
        'fm_accent': '#2f6db5',
        'fm_accent_text': '#ffffff',
        'fm_section': '#e4e4e4',
        'fm_section_border': '#d0d0d0',
        'fm_section_on': '#c8434a',
        'fm_danger': '#c62828',
        'fm_scroll': '#b5b5b5',
        'fm_icon': '#2e2e2e',
    },
}

# One spacing scale for the whole dock, in logical pixels.
SPACING: Dict[str, int] = {
    'fm_edge': 8,    # dock edge -> every block (header, EXPLORING, sections, action bar)
    'fm_block': 8,   # between two blocks: header, EXPLORING, each section header, action bar
    'fm_gap': 6,     # between two widgets: rows, fields of a row, groups, rail -> widgets
    'fm_inset': 8,   # group border -> its widgets
    'fm_band': 34,   # section header and collapsed group height (title band)
}

HEADER_BADGE_HEIGHT = 24  # backend / layer kind and favorites badges

# Layer kinds of the mockup: badge background, and the dot / square shape.
KIND_COLORS = {
    'vector': '#6fb1f0',
    'raster': '#f0b35a',
    'point_cloud': '#4fd1b0',
}
BADGE_TEXT = '#141414'

# Stroke icons of the mockup, 24 x 24 view box, ``currentColor`` = theme icon color.
ICON_BODIES: Dict[str, str] = {
    'identify': '<circle cx="12" cy="12" r="7"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>',
    'zoom': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21M10.5 8v5M8 10.5h5"/>',
    'select': '<rect x="3" y="3" width="13" height="11" stroke-dasharray="2.5 2"/><path d="M12 10l8 3.2-3.4 1.2L15.4 18z"/>',
    'track': '<path d="M3 8V4h4M17 4h4v4M21 16v4h-4M7 20H3v-4"/><circle cx="11.5" cy="11.5" r="3.5"/>'
             '<path d="M14 14l2.5 2.5"/>',
    'link': '<rect x="3" y="7" width="11" height="11" rx="2"/><rect x="10" y="3" width="11" height="11" rx="2"/>',
    'reset_props': '<circle cx="12" cy="12" r="8"/><path d="M6.5 6.5l11 11"/>',
    'source_layer': '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    'layers': '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 12l9 5 9-5M3 16l9 5 9-5"/>',
    'combine': '<path d="M7 4v6M4 7h6M17 10v6M14 13h6M9 15v6M6 18h6"/>',
    'predicates': '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18"/>',
    'buffer': '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="9"/>',
    'buffer_type': '<path d="M4 12h6"/><circle cx="14" cy="12" r="6"/><path d="M14 6v12"/>',
    'filter': '<path d="M3 4h18l-7 8v6l-4 2v-8z"/>',
    'undo': '<path d="M9 14L4 9l5-5"/><path d="M4 9h11a5 5 0 010 10h-3"/>',
    'redo': '<path d="M15 14l5-5-5-5"/><path d="M20 9H9a5 5 0 000 10h3"/>',
    'unfilter': '<path d="M3 4h18l-7 8v6l-4 2v-8z"/><path d="M16 16l5 5M21 16l-5 5"/>',
    'export': '<path d="M12 15V3M7 8l5-5 5 5"/><path d="M5 13v7h14v-7"/>',
    'reset_all': '<path d="M12 21s-6-5.5-6-11a6 6 0 0112 0c0 5.5-6 11-6 11z"/><path d="M4 4l16 16"/>',
    'settings': '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/>'
                '<circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    'projection': '<circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="4"/>',
    'styles': '<path d="M14 4l6 6-8 8-6-6z"/><path d="M6 12l-2 8 8-2"/>',
    'datatype': '<path d="M6 3h9l5 5v13H6z"/><path d="M14 3v6h6"/><path d="M10 14l-2 2 2 2M14 14l2 2-2 2"/>',
    'folder': '<path d="M3 6h6l2 2h10v11H3z"/>',
    'zip': '<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M12 3v2M12 7v2M12 11v2"/>'
           '<rect x="10" y="13" width="4" height="4"/>',
    'centroid': '<rect x="4" y="4" width="16" height="16" rx="1"/><circle cx="12" cy="12" r="2" fill="currentColor"/>',
    'star': '<path d="M12 3l2.8 5.8 6.2.9-4.5 4.4 1.1 6.2L12 17.4 6.4 20.3l1.1-6.2L3 9.7l6.2-.9z" fill="currentColor"/>',
}

# PNG files of the plugin replaced by a mockup icon. Files not listed keep their artwork.
PNG_TO_ICON: Dict[str, str] = {
    'identify.png': 'identify', 'identify_alt.png': 'identify',
    'zoom.png': 'zoom',
    'select_black.png': 'select', 'selection_white.png': 'select',
    'track.png': 'track',
    'link.png': 'link',
    'reset_properties.png': 'reset_props',
    'auto_layer_black.png': 'source_layer', 'auto_layer_white.png': 'source_layer',
    'layers.png': 'layers',
    'add_multi.png': 'combine',
    'geo_predicates.png': 'predicates',
    'buffer_value.png': 'buffer',
    'buffer_type.png': 'buffer_type',
    'filter.png': 'filter', 'filter_multi.png': 'filter',
    'undo.png': 'undo',
    'redo.png': 'redo',
    'unfilter.png': 'unfilter',
    'export.png': 'export', 'save.png': 'export',
    'reset.png': 'reset_all',
    'parameters.png': 'settings',
    'projection_black.png': 'projection', 'projection_white.png': 'projection',
    'styles_black.png': 'styles', 'styles_white.png': 'styles',
    'datatype.png': 'datatype',
    'folder_black.png': 'folder', 'folder_white.png': 'folder',
    'zip.png': 'zip',
    'centroid.png': 'centroid',
}

# Icons drawn in the danger color instead of the text color.
DANGER_ICONS = frozenset({'reset_all'})


FONT_FILES = ('IBMPlexSans-Regular.ttf', 'IBMPlexSans-SemiBold.ttf', 'IBMPlexMono-Regular.ttf')
_FONTS_REGISTERED: Dict[str, bool] = {}


def register_fonts() -> bool:
    """Add the bundled IBM Plex fonts (SIL OFL 1.1) to the application, once.

    Returns True when IBM Plex Sans is available; the stylesheet names it
    first and falls back to the system font otherwise.
    """
    if 'done' in _FONTS_REGISTERED:
        return _FONTS_REGISTERED['done']
    ok = False
    try:
        import os
        from qgis.PyQt.QtGui import QFontDatabase
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'resources', 'fonts')
        for name in FONT_FILES:
            path = os.path.join(folder, name)
            if os.path.exists(path) and QFontDatabase.addApplicationFont(path) >= 0 and 'Sans' in name:
                ok = True
    except Exception as exc:  # pragma: no cover - depends on the Qt build
        logger.debug(f"IBM Plex fonts not registered: {exc}")
    _FONTS_REGISTERED['done'] = ok
    return ok


def tokens(dark: bool) -> Dict[str, str]:
    """Color tokens of the dark (mockup) or light variant."""
    return dict(TOKENS['dark' if dark else 'light'])


def apply_tokens(stylesheet: str, dark: bool) -> str:
    """Replace every ``{fm_*}`` placeholder of ``stylesheet``."""
    for key, value in tokens(dark).items():
        stylesheet = stylesheet.replace('{' + key + '}', value)
    for kind, color in KIND_COLORS.items():
        stylesheet = stylesheet.replace('{fm_kind_' + kind + '}', color)
    # A group's title band is its top padding plus its 1 px top border.
    stylesheet = stylesheet.replace('{fm_band_padding}', f"{SPACING['fm_band'] - 1}px")
    # Header: 24 px badges one block under the dock title (ui/layout/mockup_layout.py HEADER_HEIGHT).
    stylesheet = stylesheet.replace('{fm_header_height}', f"{HEADER_BADGE_HEIGHT + SPACING['fm_block']}px")
    for key, value in SPACING.items():
        stylesheet = stylesheet.replace('{' + key + '}', f'{value}px')
    return stylesheet


def icon_key_for(filename: str) -> Optional[str]:
    """Mockup icon replacing a plugin PNG (path or file name), None to keep the PNG."""
    if not filename:
        return None
    name = str(filename).replace('\\', '/').rsplit('/', 1)[-1]
    return PNG_TO_ICON.get(name)


def icon_color(key: str, dark: bool) -> str:
    palette = tokens(dark)
    return palette['fm_danger'] if key in DANGER_ICONS else palette['fm_icon']


def svg_document(key: str, color: str) -> str:
    """Standalone SVG of a mockup icon in ``color``."""
    body = ICON_BODIES[key].replace('currentColor', color)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


_ICON_CACHE: Dict[tuple, object] = {}


def render_icon(key: str, dark: bool, color: Optional[str] = None):
    """QIcon of a mockup icon (cached), None when QtSvg is unavailable."""
    color = color or icon_color(key, dark)
    cache_key = (key, color)
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]
    try:
        from qgis.PyQt.QtCore import QByteArray, Qt
        from qgis.PyQt.QtGui import QIcon, QPainter, QPixmap
        from qgis.PyQt.QtSvg import QSvgRenderer
    except ImportError:
        return None
    renderer = QSvgRenderer(QByteArray(svg_document(key, color).encode('utf-8')))
    icon = QIcon()
    for size in (16, 24, 32, 48, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    _ICON_CACHE[cache_key] = icon
    return icon


def clear_icon_cache() -> None:
    _ICON_CACHE.clear()


def badge_stylesheet(object_name: str, background: str, text: str = BADGE_TEXT) -> str:
    """Rectangular badge of the mockup (kind / backend)."""
    return (f"QLabel#{object_name}{{color:{text};background-color:{background};font-size:8pt;font-weight:600;"
            f"padding:3px 10px;border-radius:4px;border:none;}}"
            f"QLabel#{object_name}:hover{{background-color:{background};}}")


def favorites_badge_stylesheet(object_name: str, count: int, dark: bool) -> str:
    """Light square star button of the mockup; amber once favorites exist."""
    background = '#f0b35a' if count > 0 else ('#e8e8e8' if dark else '#dcdcdc')
    hover = '#f5c47a' if count > 0 else '#ffffff'
    return (f"QLabel#{object_name}{{color:#555555;background-color:{background};font-size:9pt;font-weight:600;"
            f"padding:3px 8px;border-radius:4px;border:none;}}"
            f"QLabel#{object_name}:hover{{background-color:{hover};}}")


def vector_badge_text(backend_text: str, vector_label: str = 'Vector') -> str:
    """``"Vector · Spatialite"``; the bare text for transient states (``...``, ``⟳``, ``!``).

    ``vector_label`` is translated by the caller (a literal ``tr("Vector")`` there, so
    pylupdate files it under the caller's context).
    """
    text = (backend_text or '').strip()
    if not text or not any(char.isalpha() for char in text):
        return text
    return f"{vector_label} · {text}"


def is_dark_color(hex_color: str) -> bool:
    """Whether a ``#rrggbb`` color is dark (perceived luminance below 128)."""
    try:
        value = hex_color.lstrip('#')
        red, green, blue = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    except (ValueError, IndexError, AttributeError):
        return False
    return 0.299 * red + 0.587 * green + 0.114 * blue < 128

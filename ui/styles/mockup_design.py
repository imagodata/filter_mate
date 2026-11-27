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
from typing import Any, Dict, Optional

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
        # Selection strip between EXPLORING and FILTERING, tinted with the source layer kind.
        'fm_strip_vector_bg': '#1d2630',
        'fm_strip_vector_border': '#2f4258',
        'fm_strip_vector_text': '#6fb1f0',
        'fm_strip_raster_bg': '#2b251b',
        'fm_strip_raster_border': '#4d3f26',
        'fm_strip_raster_text': '#f0b35a',
        'fm_strip_point_cloud_bg': '#1f2b28',
        'fm_strip_point_cloud_border': '#2f4a43',
        'fm_strip_point_cloud_text': '#4fd1b0',
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
        # Same tints on a light background; darker texts keep a 4.5:1 contrast.
        'fm_strip_vector_bg': '#e7f0fa',
        'fm_strip_vector_border': '#a9c8ea',
        'fm_strip_vector_text': '#1d5b99',
        'fm_strip_raster_bg': '#fbf1e1',
        'fm_strip_raster_border': '#e3c38f',
        'fm_strip_raster_text': '#7f5210',
        'fm_strip_point_cloud_bg': '#e2f5ef',
        'fm_strip_point_cloud_border': '#96d4c1',
        'fm_strip_point_cloud_text': '#146a55',
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
    'agent': '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/>',
    # Keep the section's chat glyph; the welcome and activity indicator use the user's network mark.
    'agent_network': '<path d="M5 5l14 14M19 5L5 19" stroke-width="1.2"/>'
             '<circle cx="5" cy="5" r="2.2" fill="#3884d4" stroke="none"/>'
             '<circle cx="19" cy="5" r="2.2" fill="#d95d65" stroke="none"/>'
             '<circle cx="5" cy="19" r="2.2" fill="#ba7b1e" stroke="none"/>'
             '<circle cx="19" cy="19" r="2.2" fill="#248c68" stroke="none"/>'
             '<circle cx="12" cy="12" r="3.1" fill="currentColor" stroke="none"/>',
    'agent_send': '<path d="M4 12l16-8-6 16-3-6z"/><path d="M11 14l9-10"/>',
    'agent_push': '<path d="M13 2L3 14h8l-1 8 11-12h-8z"/>',
    'agent_queue': '<path d="M4 6h16M4 12h7M4 18h7"/><circle cx="17" cy="16" r="5"/>'
                   '<path d="M17 13v3l2 1"/>',
    'agent_microphone': '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M6 10v2a6 6 0 0 0 12 0v-2M12 18v3M9 21h6"/>',
    'agent_stop': '<rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/>',
    'history': '<path d="M3 10a9 9 0 1 1 1.8 7.4M3 4v6h6"/><path d="M12 7v5l3 2"/>',
    'effort': '<path d="M4 19a9 9 0 1 1 16 0M12 4v2M5.6 7l1.5 1.5M18.4 7l-1.5 1.5M3 13h2M19 13h2"/>'
              '<path d="M12 13l4-4"/><circle cx="12" cy="13" r="1.5"/>',
    'new_conversation': '<path d="M12 4H4v16l5-4h11v-5"/><path d="M17 2v8M13 6h8"/>',
    'recipes': '<path d="M4 4h16v16H7a3 3 0 0 1 0-6h13M4 4v13"/><path d="M10 7l5 2.5-5 2.5z"/>',
    'save': '<path d="M4 3h13l4 4v14H3V3z"/><path d="M7 3v6h10V3M7 21v-8h10v8"/>',
    'play': '<path d="M8 4l12 8-12 8z"/>',
    'refresh': '<path d="M20 7v5h-5M4 17v-5h5M5.2 7a8 8 0 0 1 13.2-1L20 8M4 16l1.6 2a8 8 0 0 0 13.2-1"/>',
    'trash': '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
    'help': '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.8 2.1c-1.3.8-1.3 1.4-1.3 2.4M12 17h0"/>',
    'compare': '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 2v20M6 12l3-3M6 16l3-3M15 8h3M15 12h3M15 16h3"/>',
    'more': '<circle cx="5" cy="12" r="1.4" fill="currentColor"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/>'
            '<circle cx="19" cy="12" r="1.4" fill="currentColor"/>',
    'settings': '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/>'
                '<circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    'projection': '<circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="4"/>',
    'styles': '<path d="M14 4l6 6-8 8-6-6z"/><path d="M6 12l-2 8 8-2"/>',
    'datatype': '<path d="M6 3h9l5 5v13H6z"/><path d="M14 3v6h6"/><path d="M10 14l-2 2 2 2M14 14l2 2-2 2"/>',
    'folder': '<path d="M3 6h6l2 2h10v11H3z"/>',
    'zip': '<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M12 3v2M12 7v2M12 11v2"/>'
           '<rect x="10" y="13" width="4" height="4"/>',
    'centroid': '<rect x="4" y="4" width="16" height="16" rx="1"/><circle cx="12" cy="12" r="2" fill="currentColor"/>',
    'class_pipette': '<path d="M20.5 3.5a2.1 2.1 0 0 0-3 0L14 7l-1.5-1.5-1.5 1.5 1.5 1.5L4 16v4h4l7.5-7.5L17 14l1.5-1.5L17 11l3.5-3.5a2.1 2.1 0 0 0 0-3z"/>',
    'pixel_picker': '<rect x="3" y="3" width="18" height="18" rx="1"/><path d="M9 3v18M15 3v18M3 9h18M3 15h18"/>'
                    '<rect x="9" y="9" width="6" height="6" fill="currentColor"/>',
    'preview': '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    # 2026-10-18: an eye over a few points, no longer the same drawing as 'track'.
    'live_preview': '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="9" cy="12" r="1.2"/>'
                    '<circle cx="12.5" cy="10.2" r="1.2"/><circle cx="14.8" cy="13.6" r="1.2"/>',
    # Collapse arrows of the groups (QGIS draws them dark in every theme: invisible on the dark dock).
    'group_expand': '<path d="M9 6l7 6-7 6z" fill="currentColor"/>',
    'group_collapse': '<path d="M6 9l6 7 6-7z" fill="currentColor"/>',
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
_FONTS_APP_PROPERTY = 'filtermate_plex_fonts'


def register_fonts() -> bool:
    """Add the bundled IBM Plex fonts (SIL OFL 1.1) to the application, once.

    Returns True when IBM Plex Sans is available; the stylesheet names it
    first and falls back to the system font otherwise.
    """
    if 'done' in _FONTS_REGISTERED:
        return _FONTS_REGISTERED['done']
    ok = False
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        app = QCoreApplication.instance()
        # Plugin reloads re-import this module: the application keeps the answer, so the
        # fonts are added once per QGIS session (they are then visible to the whole session).
        if app is not None and app.property(_FONTS_APP_PROPERTY) is not None:
            _FONTS_REGISTERED['done'] = bool(app.property(_FONTS_APP_PROPERTY))
            return _FONTS_REGISTERED['done']
    except Exception:
        app = None
    try:
        import os
        from qgis.PyQt.QtGui import QFontDatabase
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'resources', 'fonts')
        from qgis.PyQt.QtCore import QByteArray
        for name in FONT_FILES:
            path = os.path.join(folder, name)
            if not os.path.exists(path):
                continue
            # From the bytes: Qt 5 on Windows does not load a font from a network path
            # (plugin folder under \\wsl.localhost or a shared drive), Qt 6 does.
            with open(path, 'rb') as handle:
                font_id = QFontDatabase.addApplicationFontFromData(QByteArray(handle.read()))
            if font_id >= 0 and 'Sans' in name:
                ok = True
    except Exception as exc:  # pragma: no cover - depends on the Qt build
        logger.debug(f"IBM Plex fonts not registered: {exc}")
    _FONTS_REGISTERED['done'] = ok
    if app is not None:
        app.setProperty(_FONTS_APP_PROPERTY, ok)
    return ok


# Shared EXPLORING buttons whose icon changes with the layer kind (mockup rails);
# a button not listed keeps its vector icon.
KIND_BUTTON_ICONS: Dict[str, Dict[str, str]] = {
    'raster': {
        'pushButton_checkable_exploring_selecting': 'preview',  # Identify is hidden on a raster (2026-10-18)
    },
    'point_cloud': {
        'pushButton_exploring_identify': 'class_pipette',  # 2026-10-18: Identify is the class pipette
        'pushButton_checkable_exploring_selecting': 'live_preview',
    },
}


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


def stylesheet_is_dark(widget: Any) -> Optional[bool]:
    """Variant of the FilterMate stylesheet applied above ``widget``, None before any is applied.

    Read from the radio glyph the stylesheet names (style_loader picks it with the token variant),
    so it is the theme actually drawn, whatever the managers or the QGIS palette say.
    """
    owner = widget
    while owner is not None:
        try:
            sheet = owner.styleSheet() if hasattr(owner, 'styleSheet') else ''
        except RuntimeError:
            return None
        if sheet:
            if 'radio_dot_dark.svg' in sheet:
                return True
            if 'radio_dot_white.svg' in sheet:
                return False
        owner = owner.parentWidget()
    return None


def plugin_is_dark(widget: Any) -> bool:
    """Plugin theme of the dock holding ``widget``, which may differ from QGIS'.

    The applied stylesheet first, then the icon manager of the dock, then the widget palette.
    """
    applied = stylesheet_is_dark(widget)
    if applied is not None:
        return applied
    owner = widget
    while owner is not None and getattr(owner, '_icon_manager', None) is None:
        owner = owner.parentWidget()
    if owner is not None:
        return bool(getattr(owner._icon_manager, 'is_dark_mode', False))
    return widget.palette().window().color().lightness() < 128


def svg_document(key: str, color: str) -> str:
    """Standalone SVG of a mockup icon in ``color``."""
    body = ICON_BODIES[key].replace('currentColor', color)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


AGENT_ACTIVITY_STYLES = {
    # orbit seconds, pulse seconds, moving points, point radius (on the 24-unit grid)
    'thinking': (5.4, 2.4, 3, 1.8),
    'reading': (3.6, 1.9, 2, 2.0),
    'working': (2.1, 1.2, 3, 2.1),
    'fetching': (2.8, 1.6, 3, 2.0),
    'responding': (4.2, 2.0, 1, 1.9),
    'waiting': (0, 3.8, 0, 0),
    'retry': (6.4, 3.0, 1, 1.8),
    'stopping': (0, 2.6, 0, 0),
    'idle': (0, 0, 0, 0),
    'complete': (0, 0, 0, 0),
    'drafting': (0, 0, 0, 0),
    'queued': (0, 0, 0, 0),
    'error': (0, 0, 0, 0),
    'searching': (3.0, 1.6, 2, 1.9),
    'processing': (1.6, 1.1, 3, 2.1),
    'editing': (3.2, 1.7, 1, 2.0),
    'exporting': (2.6, 1.5, 2, 2.0),
    'designing': (4.5, 2.0, 3, 1.9),
    'navigating': (2.4, 1.8, 1, 2.0),
    'confirming': (0, 3.8, 0, 0),
    'listening': (0, 1.2, 0, 0),
    'transcribing': (2.9, 1.6, 2, 1.8),
}

STATIC_AGENT_PHASES = frozenset({'idle', 'complete', 'drafting', 'queued', 'error'})

# Simple center marks remain legible in the 32 px activity indicator. Color is never the only state cue.
_AGENT_PHASE_MARKS = {
    'complete': ('#248c68', '<path d="m10.4 12 1.1 1.2 2.2-2.5"/>'),
    'error': ('#c54a56', '<path d="M12 10.2v2.2m0 1v.1"/>'),
    'drafting': ('#3884d4', '<path d="m10.4 12.7-.3 1.1 1.1-.3 2.5-2.5-.8-.8z"/>'),
    'editing': ('#ba7b1e', '<path d="m10.4 12.7-.3 1.1 1.1-.3 2.5-2.5-.8-.8z"/>'),
    'queued': ('#ba7b1e', '<path d="M10.3 10.8h3.4m-3.4 1.2h2.6m-2.6 1.2H12"/>'),
    'reading': ('#3884d4', '<path d="M12 10.7v2.6m0-2.6-1.7-.3v2.6l1.7.3 1.7-.3v-2.6z"/>'),
    'searching': ('#3884d4', '<circle cx="11.6" cy="11.6" r="1.2"/><path d="m12.5 12.5 1.3 1.3"/>'),
    'processing': ('#248c68', '<path d="M10.5 11.7v1.6M12 10.5v2.8m1.5-2v2"/>'),
    'exporting': ('#248c68', '<path d="M12 13.5v-3m-1.2 1.2 1.2-1.2 1.2 1.2m-2.7 1.9v.6h3v-.6"/>'),
    'designing': ('#8656bc', '<path d="m12 10.2.5 1.3 1.3.5-1.3.5-.5 1.3-.5-1.3-1.3-.5 1.3-.5z"/>'),
    'navigating': ('#248c68', '<circle cx="12" cy="12" r="1.1"/><path d="M12 9.8v.8m0 2.8v.8m-2.2-2.2h.8m2.8 0h.8"/>'),
    'waiting': ('#ba7b1e', '<path d="M11 10.5v3m2-3v3"/>'),
    'confirming': ('#ba7b1e', '<path d="M10.9 11a1.1 1.1 0 0 1 2.2 0c0 .8-1.1.7-1.1 1.6m0 .9v.1"/>'),
    'retry': ('#ba7b1e', '<path d="M13.4 11.5a1.5 1.5 0 1 0-.2 1.5m.2-2.5v1.2h-1.2"/>'),
    'stopping': ('#ba7b1e', '<rect x="10.8" y="10.8" width="2.4" height="2.4" rx=".2"/>'),
    'listening': ('#3884d4', '<rect x="11.4" y="10" width="1.2" height="2.5" rx=".6"/><path d="M10.5 11.8a1.5 1.5 0 0 0 3 0M12 13.3v.8"/>'),
    'transcribing': ('#8656bc', '<path d="M10.3 10.5h3.4M12 10.5v3m-1 .1h2"/>'),
}


def agent_activity_svg(color: str, animated: bool = False, phase: str = 'thinking', hovered: bool = False) -> str:
    """Network mark with Qt 5/6 compatible pulse and orbit animations.

    The supplied artwork uses animate/animateMotion, which QtSvg ignores. animateTransform works in both
    supported Qt versions. Keep this renderer out of the QIcon cache: it belongs to one visible activity widget.
    Hover enlarges the central disk and its phase mark together, around their shared center.
    """
    phase = phase if phase in AGENT_ACTIVITY_STYLES else 'thinking'
    animated = animated and phase not in STATIC_AGENT_PHASES
    document = svg_document('agent_network', color)
    orbit, duration, count, radius = AGENT_ACTIVITY_STYLES.get(phase, AGENT_ACTIVITY_STYLES['thinking'])
    accent, mark = _AGENT_PHASE_MARKS.get(phase, (color, ''))
    if mark:
        document = document.replace(f'cx="12" cy="12" r="3.1" fill="{color}"',
                                    f'cx="12" cy="12" r="3.1" fill="{accent}"')
    center_transform = ' transform="translate(12 12) scale(1.5 1.5) translate(-12 -12)"' if hovered else ''
    if hovered:
        center = f'<circle cx="12" cy="12" r="3.1" fill="{accent}" stroke="none"/>'
        document = document.replace(center, f'<g{center_transform}>{center}</g>')
    pulse = ''
    if animated:
        pulse = (
            '<g transform="translate(12 12)"><g>'
            # Qt 6 needs both scale components; a single value can load as animated but never change a pixel.
            '<animateTransform attributeName="transform" type="scale" values="0.7 0.7;1.15 1.15;0.7 0.7" '
            f'dur="{duration}s" repeatCount="indefinite"/>'
            f'<circle r="4.8" fill="none" stroke="{accent}" stroke-opacity="0.5" stroke-width="0.7"/>'
            '</g></g>'
        )
    if count:
        pulse += '<g>'
        if animated:
            direction = -360 if phase in ('searching', 'transcribing') else 360
            pulse += ('<animateTransform attributeName="transform" type="rotate" from="0 12 12" '
                      f'to="{direction} 12 12" dur="{orbit}s" repeatCount="indefinite"/>')
        points = ((18.6, 12, '#3884d4'), (8.7, 17.72, '#d95d65'), (8.7, 6.28, '#ba7b1e'))
        if phase == 'retry':
            points = ((18.6, 12, '#ba7b1e'),)
        for x, y, fill in points[:count]:
            pulse += f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" stroke="none"/>'
        pulse += '</g>'
    if mark:
        ink = '#202020' if accent == '#ba7b1e' else '#ffffff'
        pulse += f'<g{center_transform} stroke="{ink}" stroke-width=".7" fill="none">{mark}</g>'
    return document.replace('</svg>', pulse + '</svg>')


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


TITLE_BADGE_RADIUS = 4
TITLE_BADGE_TEXT = '#555555'
TITLE_BADGE_PRESSED = '#c8c8c8'


def title_badge_colors(dark: bool) -> tuple:
    """``(background, hover)`` of the grey badges of the title bar: favorites without any, float, close."""
    return ('#e8e8e8' if dark else '#dcdcdc'), '#ffffff'


def favorites_badge_stylesheet(object_name: str, count: int, dark: bool) -> str:
    """Light square star button of the mockup; amber once favorites exist."""
    background, hover = title_badge_colors(dark)
    if count > 0:
        background, hover = '#f0b35a', '#f5c47a'
    return (f"QLabel#{object_name}{{color:{TITLE_BADGE_TEXT};background-color:{background};font-size:9pt;"
            f"font-weight:600;padding:3px 8px;border-radius:{TITLE_BADGE_RADIUS}px;border:none;}}"
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

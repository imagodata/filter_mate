# -*- coding: utf-8 -*-
"""
Dock additions of the raster / point cloud mode (FilterMate 5 mockup).

* A layer card at the top of the coverage panels: name, then
  ``1 band · Float32 · 1 m · NoData -99999`` or ``38.4 M points · Z 141.8 → 318.7``.
* Tools of the layer kind in the EXPLORING tool rail, between the vector
  buttons and the reset button. Raster: value under the cursor, statistics of
  a rectangle. Point cloud: elevation profile, 3D map view. The tracking and
  linking buttons only make sense for vector layers: they are hidden meanwhile.
* The layer card shows vector layers too (geometry type, feature count).

Kept apart from :class:`CoverageModeController`, which calls :meth:`show_for`,
:meth:`show_vector`, :meth:`leave` and :meth:`teardown`. The text builders are
pure functions, testable without Qt.
"""
import logging
import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    from qgis.PyQt.QtCore import QObject, QTimer
except ImportError:  # pragma: no cover - unit tests without Qt
    QObject = object
    QTimer = None

logger = logging.getLogger(__name__)

HOVER_DELAY_MS = 60
ZONE_SAMPLE_SIZE = 250000
TOOL_RAIL_ANCHOR = 'pushButton_checkable_exploring_linking_widgets'
VECTOR_ONLY_BUTTONS = ('pushButton_checkable_exploring_tracking', 'pushButton_checkable_exploring_linking_widgets')
LAYER_CARD_NAME = 'label_exploring_coverage_layer'
# Stroke icons of the mockup (24 x 24 view box).
ICON_HOVER = ('<path d="M3 8V4h4M17 4h4v4M21 16v4h-4M7 20H3v-4"/><circle cx="11.5" cy="11.5" r="3.5"/>'
              '<path d="M14 14l2.5 2.5"/>')
ICON_ZONE = '<rect x="3" y="4" width="18" height="14" stroke-dasharray="2.5 2"/><path d="M8 15v-3M12 15V8M16 15v-5"/>'
ICON_PROFILE = '<path d="M2 18l5-7 4 4 4-8 7 11M2 21h20"/>'
ICON_LINK_STYLE = '<path d="M4 20V10M9 20V5M14 20v-8M19 20v-4M2 20h20"/>'
ICON_PIPETTE = '<path d="M20.5 3.5a2.1 2.1 0 0 0-3 0L14 7l-1.5-1.5-1.5 1.5 1.5 1.5L4 16v4h4l7.5-7.5L17 14l1.5-1.5L17 11l3.5-3.5a2.1 2.1 0 0 0 0-3z"/>'
ICON_3D = '<path d="M12 2l9 5v10l-9 5-9-5V7z"/><path d="M12 12l9-5M12 12L3 7M12 12v10"/>'

# QGIS main window actions run by the point cloud tools, first name found wins
# (the 3D action is ``mActionNew3DMapCanvas`` in QGIS 4.2, ``mActionNew3DMapView`` in older builds).
ACTION_ELEVATION_PROFILE = ('mActionElevationProfile',)
ACTION_NEW_3D_VIEW = ('mActionNew3DMapCanvas', 'mActionNew3DMapView')
# Vector providers whose feature count is a server / database query: the card leaves it out
# (it is read on the main thread at every layer change). Lower case: QGIS names its web
# providers 'WFS' and 'OAPIF' (compared case-insensitively, see feature_count_is_cheap).
UNCOUNTED_PROVIDERS = ('postgres', 'oracle', 'mssql', 'hana', 'wfs', 'oapif', 'arcgisfeatureserver',
                       'sensorthings', 'virtual')


def _identity(text: str) -> str:
    return text


# ---------------------------------------------------------------------------
# Pure helpers (no Qt)
# ---------------------------------------------------------------------------

def format_number(value: float, max_decimals: int = 2) -> str:
    """``1.0`` -> ``"1"``, ``0.5`` -> ``"0.5"``, ``141.84`` -> ``"141.84"``; ``""`` when not finite."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(number):
        return ""
    if abs(number) >= 1e7:
        return f"{number:.6g}"  # Float32 NoData (-3.4e38) must not print 39 digits
    text = f"{number:.{max(0, int(max_decimals))}f}"
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return "0" if text in ("-0", "") else text


def pixel_size_text(size_x: float, size_y: float, unit: str = "") -> str:
    """``"1 m"``, ``"0.5 × 0.25 m"``; ``""`` when unknown.

    Sizes below 0.01 (geographic CRS) keep 6 decimals.
    """
    sizes = []
    for size in (size_x, size_y):
        try:
            size = abs(float(size))
        except (TypeError, ValueError):
            return ""
        if not math.isfinite(size) or size <= 0:
            return ""
        sizes.append(size)
    decimals = 6 if min(sizes) < 0.01 else 3
    first, second = (format_number(size, decimals) for size in sizes)
    text = first if first == second else f"{first} × {second}"
    return f"{text} {unit}".strip()


def raster_card_text(bands: Sequence[Tuple[str, Optional[float]]], size_x: float, size_y: float,
                     unit: str = "", translate: Callable[[str], str] = _identity) -> str:
    """Second line of the raster card: ``"1 band · Float32 · 1 m · NoData -99999"``.

    Args:
        bands: ``(data_type, nodata)`` per band, in band order.
        size_x: Pixel width in layer units.
        size_y: Pixel height in layer units.
        unit: Abbreviated layer unit (``"m"``, ``"°"``), may be empty.
        translate: Translation function of the caller (named so pylupdate skips these calls).
    """
    count = len(bands)
    parts = [translate("1 band") if count == 1 else translate("{0} bands").format(count)]
    types = []
    for data_type, _nodata in bands:
        if data_type and data_type not in types:
            types.append(data_type)
    if types:
        parts.append(types[0] if len(types) == 1 else " / ".join(types))
    size = pixel_size_text(size_x, size_y, unit)
    if size:
        parts.append(size)
    nodata = format_number(bands[0][1], 3) if bands and bands[0][1] is not None else ""
    if nodata:
        parts.append(f"NoData {nodata}")
    return " · ".join(parts)


def point_cloud_card_text(point_count: Optional[int], z_range: Optional[Tuple[float, float]],
                          translate: Callable[[str], str] = _identity) -> str:
    """Second line of the point cloud card: ``"38.4 M points · Z 141.8 → 318.7"``; ``""`` when nothing is known."""
    from ..widgets.coverage_panels.point_cloud_exploring_panel import format_count
    parts = []
    counted = format_count(point_count) if point_count is not None and point_count >= 0 else ""
    if counted:
        parts.append(translate("{0} points").format(counted))
    if z_range is not None and z_range[0] is not None and z_range[1] is not None:
        parts.append(f"Z {format_number(z_range[0], 2)} → {format_number(z_range[1], 2)}")
    return " · ".join(parts)


def vector_card_text(geometry_label: str, feature_count: Optional[int],
                     translate: Callable[[str], str] = _identity) -> str:
    """Second line of the vector card: ``"Line · 12 438 features"``; ``""`` when nothing is known."""
    parts = [geometry_label] if geometry_label else []
    if feature_count is not None and feature_count >= 0:
        parts.append(translate("{0} features").format(f"{int(feature_count):,}".replace(",", "\u202f")))
    return " · ".join(parts)


def feature_count_is_cheap(provider: str, subset: str) -> bool:
    """Whether the card may count the features: a local source without a filter.

    A filtered GeoPackage / Spatialite layer counts through its subset
    (``EXISTS``, ``ST_DWithin``...), a database or web layer runs a query.
    """
    return not (subset or '').strip() and (provider or '').lower() not in UNCOUNTED_PROVIDERS


def card_html(name: str, kind_label: str, meta: str, color: str, square: bool) -> str:
    """Rich text of the layer card: a kind bullet, the bold name, then ``kind · meta`` (mockup)."""
    from html import escape
    bullet = "■" if square else "●"
    second = " · ".join(part for part in (kind_label, meta) if part)
    head = f'<span style="color:{color}">{bullet}</span>&nbsp;<b>{escape(name)}</b>'
    return f"{head}<br>{escape(second)}" if second else head


# The rail keeps the shared EXPLORING buttons that matter most: pixel picker, zoom to the selection,
# preview and reset. On top of them: the colour pipette (a selection tool, like the picker) and the style
# link for a raster (no QGIS tool stretches the colours over the selected range), and the class pipette for
# a point cloud (a click on the map checks the class of the points there). The other tools (value under the
# cursor, statistics of a rectangle, elevation profile, 3D view) are still implemented below but not put on
# the rail: the picker reads the value and QGIS has its own statistics, profile and 3D tools. List a tool
# here to bring it back.
RAIL_TOOLS = {
    'raster': ('pushButton_checkable_exploring_raster_pipette', 'pushButton_checkable_exploring_raster_link'),
    'point_cloud': ('pushButton_checkable_exploring_point_cloud_pipette',),
}
_RAIL_TOOL_NAMES = frozenset(name for names in RAIL_TOOLS.values() for name in names)


def tools_for(kind_value: str) -> List[str]:
    """Object names of the extra tool buttons shown for a layer kind value."""
    return list(RAIL_TOOLS.get(kind_value, ()))


def zone_pixel_estimate(width: float, height: float, size_x: float, size_y: float) -> Optional[int]:
    """Pixels covered by a rectangle, None when the pixel size is unknown."""
    try:
        if size_x <= 0 or size_y <= 0:
            return None
        return int(round(abs(width) / size_x)) * int(round(abs(height) / size_y))
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _svg_document(body: str, color: str) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


# ---------------------------------------------------------------------------
# Dock additions
# ---------------------------------------------------------------------------

class CoverageDockExtras(QObject):
    """Layer card, kind tools and source geometry line of the coverage mode."""

    def __init__(self, controller: Any) -> None:
        super().__init__(controller if isinstance(controller, QObject) else None)
        self._controller = controller
        self._card = None
        self._tools: Dict[str, Any] = {}
        self._hidden_vector_buttons: Dict[str, bool] = {}
        self._hover_connected = False
        self._hover_point = None
        self._hover_timer = None
        self._zone_tool = None
        self._zone_previous_tool = None
        self._layer_id: Optional[str] = None
        self._hover_base = None
        self._hover_base_key: Optional[Tuple[str, str]] = None  # (layer id, source) the base was opened for
        self._link_connected = False
        self._linked_layer_id: Optional[str] = None  # raster whose style follows the range

    @property
    def dockwidget(self) -> Any:
        return self._controller.dockwidget

    def _catalog(self) -> None:  # pragma: no cover - never called
        """Literal tr() calls of the texts built by the module helpers, for pylupdate.

        The helpers receive ``self.tr`` and translate at run time in this class context;
        pylupdate only extracts literal calls made inside the class.
        """
        self.tr("1 band")
        self.tr("{0} bands")
        self.tr("{0} points")
        self.tr("{0} features")
        self.tr("Vector")
        self.tr("Raster")
        self.tr("Point cloud")

    # === Building ===

    def ensure(self, host: Any) -> None:
        """Build the layer card and the tool buttons, once."""
        self.ensure_card()
        if not self._tools:
            self._build_tools()

    def ensure_card(self) -> None:
        """Layer card at the top of EXPLORING, above the groups of every layer kind (mockup)."""
        if self._card is not None:
            return
        layout = getattr(self.dockwidget, 'verticalLayout_exploring_tabs_content', None)
        if layout is None:
            return
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtWidgets import QLabel
        card = QLabel()
        card.setObjectName(LAYER_CARD_NAME)
        card.setWordWrap(True)
        card.setTextFormat(Qt.TextFormat.RichText)
        card.setVisible(False)
        layout.insertWidget(0, card)
        self._card = card

    def _build_tools(self) -> None:
        from qgis.PyQt.QtWidgets import QPushButton
        dw = self.dockwidget
        anchor = getattr(dw, TOOL_RAIL_ANCHOR, None)
        layout = self._controller._find_parent_layout(anchor) if anchor is not None else None
        if layout is None or not hasattr(layout, 'insertWidget'):
            logger.debug("[FM5] EXPLORING tool rail not found, kind tools not added")
            return
        self._link_tip = self.tr("Link the range to the style: the layer colours stretch over the selected range")
        self._class_pipette_tip = self.tr(
            "Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds "
            "another one")
        specs = (
            ('pushButton_checkable_exploring_raster_pipette', True,
             self.tr("Pipette: click the map and the pixels that look like the one you click are selected (a color "
                     "on an image, a value on a DTM or an index, a class on a classified raster, with the tolerance "
                     "of the panel). Ctrl+click adds another one"),
             self._on_pipette_toggled),
            ('pushButton_checkable_exploring_raster_hover', True,
             self.tr("Value under the cursor: follow the pixel value (or the slope, aspect... the range applies to) "
                     "while moving over the map"),
             self._on_hover_toggled),
            ('pushButton_checkable_exploring_raster_zone', True,
             self.tr("Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current "
                     "band (or of the slope, aspect... the range applies to)"),
             self._on_zone_toggled),
            ('pushButton_checkable_exploring_raster_link', True, self._link_tip, self._on_link_toggled),
            ('pushButton_checkable_exploring_point_cloud_pipette', True, self._class_pipette_tip,
             self._on_class_pipette_toggled),
            ('pushButton_exploring_point_cloud_profile', False,
             self.tr("Elevation profile: open the QGIS elevation profile of the map"), self._open_elevation_profile),
            ('pushButton_exploring_point_cloud_3d', False,
             self.tr("3D view: open a new QGIS 3D map view"), self._open_3d_view),
        )
        specs = tuple(spec for spec in specs if spec[0] in _RAIL_TOOL_NAMES)
        index = layout.indexOf(anchor) + 1
        for offset, (name, checkable, tip, slot) in enumerate(specs):
            button = QPushButton(anchor.parentWidget())
            button.setObjectName(name)
            button.setCheckable(checkable)
            button.setToolTip(tip)
            button.setAccessibleName(tip.split(':')[0])
            button.setSizePolicy(anchor.sizePolicy())
            button.setMinimumSize(anchor.minimumSize())
            button.setMaximumSize(anchor.maximumSize())
            button.setIconSize(anchor.iconSize())
            button.setCursor(anchor.cursor())
            button.setFlat(anchor.isFlat())
            button.setVisible(False)
            if checkable:
                button.toggled.connect(slot)
            else:
                button.clicked.connect(slot)
            layout.insertWidget(index + offset, button, 0, layout.itemAt(layout.indexOf(anchor)).alignment())
            self._tools[name] = button

    def _refresh_icons(self) -> None:
        """Draw the tool icons in the text color of the current theme."""
        try:
            from qgis.PyQt.QtCore import QByteArray, Qt
            from qgis.PyQt.QtGui import QIcon, QPainter, QPalette, QPixmap
            from qgis.PyQt.QtSvg import QSvgRenderer
        except ImportError:
            return
        bodies = {
            'pushButton_checkable_exploring_raster_pipette': ICON_PIPETTE,
            'pushButton_checkable_exploring_raster_hover': ICON_HOVER,
            'pushButton_checkable_exploring_raster_zone': ICON_ZONE,
            'pushButton_checkable_exploring_raster_link': ICON_LINK_STYLE,
            'pushButton_checkable_exploring_point_cloud_pipette': ICON_PIPETTE,
            'pushButton_exploring_point_cloud_profile': ICON_PROFILE,
            'pushButton_exploring_point_cloud_3d': ICON_3D,
        }
        for name, button in self._tools.items():
            color = button.palette().color(QPalette.ColorRole.ButtonText).name()
            renderer = QSvgRenderer(QByteArray(_svg_document(bodies[name], color).encode('utf-8')))
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            button.setIcon(QIcon(pixmap))

    # === Showing ===

    def show_for(self, layer: Any, kind: Any) -> None:
        """Adapt the card, the tool rail and the source geometry line to a raster / point cloud layer."""
        kind_value = getattr(kind, 'value', str(kind))
        layer_id = self._safe_id(layer)
        if layer_id != self._layer_id:
            self.leave()
        self._layer_id = layer_id
        self._update_card(layer, kind_value)
        self._hide_vector_buttons()
        visible = set(tools_for(kind_value))
        for name, button in self._tools.items():
            button.setVisible(name in visible)
        if kind_value == 'point_cloud':
            self._tools_enabled_by_action()
            self._guarded(self._class_pipette_enabled, layer)
        if kind_value == 'raster':
            self._guarded(self._watch_panel)
        self._refresh_icons()
        self._guarded(self._set_kind_icons, kind_value)

    def _watch_panel(self) -> None:
        """Keep the tools in step with the quantity the range applies to (connected once)."""
        panel = self._controller._raster_panel
        if panel is not None and getattr(self, '_watched_panel', None) is not panel:
            panel.selectionChanged.connect(self._sync_derivative_tools)
            self._watched_panel = panel  # a panel rebuilt after a teardown is watched again
        self._sync_derivative_tools()

    def _sync_derivative_tools(self, *_args) -> None:
        """The style link cannot follow a slope or an aspect: the button is off while the range applies to one."""
        panel = self._controller._raster_panel
        button = self._tools.get('pushButton_checkable_exploring_raster_link')
        if panel is None or button is None:
            return
        terrain = panel.current_derivative().is_terrain
        if terrain and button.isChecked():
            button.setChecked(False)  # runs the toggled slot: the style is given back
        button.setEnabled(not terrain)
        button.setToolTip(
            self.tr("The style link follows pixel values: not available while the range applies to a slope, "
                    "aspect, hillshade or roughness") if terrain else self._link_tip)

    def show_vector(self, layer: Any = None) -> None:
        """Vector layer: its card, no kind tool, vector buttons back (no card without a layer: it was removed)."""
        self._layer_id = None
        for step in (self.leave, self._hide_coverage_widgets, self._restore_vector_buttons):
            self._guarded(step)
        self._guarded(self._set_kind_icons, 'vector')
        if layer is not None:
            self._guarded(self.ensure_card)
            self._guarded(self._update_card, layer, 'vector')
        elif self._card is not None:
            self._guarded(self._card.setVisible, False)

    @staticmethod
    def _safe_id(layer: Any) -> Optional[str]:
        try:
            return layer.id() if layer is not None else None
        except RuntimeError:
            return None

    @staticmethod
    def _guarded(step: Callable, *args) -> None:
        """Run one step; a deleted Qt object must not stop the following ones."""
        try:
            step(*args)
        except (RuntimeError, AttributeError, TypeError) as exc:
            logger.debug(f"[FM5] dock addition step {getattr(step, '__name__', step)} skipped: {exc}")

    def _hide_coverage_widgets(self) -> None:
        for button in self._tools.values():
            button.setVisible(False)

    def leave(self) -> None:
        """Stop the map interactions of the outgoing layer (hover, rectangle tool)."""
        for name in ('pushButton_checkable_exploring_raster_pipette', 'pushButton_checkable_exploring_raster_hover',
                     'pushButton_checkable_exploring_raster_zone', 'pushButton_checkable_exploring_raster_link',
                     'pushButton_checkable_exploring_point_cloud_pipette'):
            button = self._tools.get(name)
            if button is not None:
                self._guarded(self._uncheck, button)
        self._guarded(self._stop_hover)
        self._guarded(self._stop_zone_tool)
        self._hover_base, self._hover_base_key = None, None

    @staticmethod
    def _uncheck(button: Any) -> None:
        if button.isChecked():
            button.setChecked(False)  # runs the toggled slot, which disconnects

    def forget_layers(self, layer_ids: Optional[Sequence[str]] = None) -> None:
        """Layers removed from the project (None: the project was closed).

        Their saved styles are dropped, never restored (a layer opened again
        with the same id has its own style); the tools of the shown layer stop.
        """
        from ...adapters.qgis.coverage_layers.raster_adapter import forget_linked_styles
        forget_linked_styles(layer_ids)

        def gone(layer_id: Optional[str]) -> bool:
            return layer_id is not None and (layer_ids is None or layer_id in layer_ids)

        if gone(self._linked_layer_id):
            self._linked_layer_id = None
        if gone(self._layer_id):
            self.leave()
            self._layer_id = None

    def teardown(self) -> None:
        self.leave()
        self._guarded(self._unlink_all_styles)  # plugin unloaded: every layer gets its own style back
        self._guarded(self._restore_vector_buttons)
        self._guarded(self._release_zone_tool)
        widgets = [self._card, *self._tools.values()]
        self._card, self._tools = None, {}
        for widget in widgets:
            if widget is None:
                continue
            try:
                widget.setParent(None)
                widget.deleteLater()
            except RuntimeError:
                pass

    def _update_card(self, layer: Any, kind_value: str) -> None:
        if self._card is None:
            return
        builders = {'raster': self._raster_meta, 'point_cloud': self._point_cloud_meta, 'vector': self._vector_meta}
        try:
            meta = builders.get(kind_value, self._vector_meta)(layer)
        except Exception as exc:
            logger.debug(f"[FM5] layer card not filled: {exc}")
            meta = ''
        from ..styles.mockup_design import KIND_COLORS
        labels = {'raster': self.tr("Raster"), 'point_cloud': self.tr("Point cloud"), 'vector': self.tr("Vector")}
        self._card.setText(card_html(layer.name() if layer is not None else '', labels.get(kind_value, ''), meta,
                                     KIND_COLORS.get(kind_value, KIND_COLORS['vector']), kind_value == 'raster'))
        self._card.setToolTip(layer.publicSource() if layer is not None else '')  # no password
        self._card.setVisible(True)

    def _vector_meta(self, layer: Any) -> str:
        geometry = ''
        try:
            from qgis.core import QgsWkbTypes
            geometry = QgsWkbTypes.geometryDisplayString(layer.geometryType())
        except Exception:
            geometry = ''
        try:
            count = layer.featureCount() if feature_count_is_cheap(layer.providerType(), layer.subsetString()) else None
        except Exception:
            count = None
        return vector_card_text(geometry, count, self.tr)

    def _raster_meta(self, layer: Any) -> str:
        from ...adapters.qgis.coverage_layers.raster_adapter import read_raster_summary
        summary = read_raster_summary(layer)
        bands = [(info.data_type, info.nodata) for info in summary.bands]
        return raster_card_text(bands, summary.pixel_size_x, summary.pixel_size_y, self._unit(layer), self.tr)

    def _point_cloud_meta(self, layer: Any) -> str:
        from ...adapters.qgis.point_cloud_layer_adapter import read_point_cloud_summary
        from ..widgets.coverage_panels.point_cloud_exploring_panel import summary_bounds
        summary = read_point_cloud_summary(layer)
        return point_cloud_card_text(summary.point_count, summary_bounds(summary, 'Z'), self.tr)

    @staticmethod
    def _unit(layer: Any) -> str:
        try:
            from qgis.core import QgsUnitTypes
            return QgsUnitTypes.toAbbreviatedString(layer.crs().mapUnits())
        except Exception:
            return ''

    def _set_kind_icons(self, kind_value: str) -> None:
        """Icons of the shared EXPLORING buttons for the layer kind (mockup rails); vector icons back otherwise."""
        from ..styles.mockup_design import KIND_BUTTON_ICONS, render_icon
        dw = self.dockwidget
        manager = getattr(dw, '_icon_manager', None)
        dark = bool(getattr(manager, 'is_dark_mode', False))
        swapped = set()
        for names in KIND_BUTTON_ICONS.values():
            swapped.update(names)
        wanted = KIND_BUTTON_ICONS.get(kind_value, {})
        for name in swapped:
            button = getattr(dw, name, None)
            if button is None:
                continue
            if name in wanted:
                icon = render_icon(wanted[name], dark)
                if icon is not None:
                    button.setIcon(icon)
            elif manager is not None and button.property('icon_name'):
                button.setIcon(manager.get_icon(button.property('icon_name')))  # the vector icon

    def _hide_vector_buttons(self) -> None:
        dw = self.dockwidget
        for name in VECTOR_ONLY_BUTTONS:
            button = getattr(dw, name, None)
            if button is None:
                continue
            if name not in self._hidden_vector_buttons:
                self._hidden_vector_buttons[name] = not button.isHidden()
            button.setVisible(False)

    def _restore_vector_buttons(self) -> None:
        dw = self.dockwidget
        for name, visible in self._hidden_vector_buttons.items():
            button = getattr(dw, name, None)
            if button is not None:
                try:
                    button.setVisible(visible)
                except RuntimeError:
                    pass
        self._hidden_vector_buttons = {}

    # === Point cloud: class pipette ===

    def _on_class_pipette_toggled(self, checked: bool) -> None:
        self._controller._on_class_pick_toggled(checked)

    def _class_pipette_enabled(self, layer: Any) -> None:
        """A point cloud without the Classification attribute has no class to pick."""
        button = self._tools.get('pushButton_checkable_exploring_point_cloud_pipette')
        if button is None:
            return
        from ...adapters.qgis.point_cloud_layer_adapter import may_have_classes
        enabled = may_have_classes(layer)
        button.setEnabled(enabled)
        button.setToolTip(self._class_pipette_tip if enabled else self.tr(
            "Class pipette: this point cloud has no Classification attribute"))

    def set_class_pipette_checked(self, checked: bool) -> None:
        """The class picker left the map: the pipette button follows without running its slot."""
        button = self._tools.get('pushButton_checkable_exploring_point_cloud_pipette')
        if button is not None:
            button.blockSignals(True)
            button.setChecked(bool(checked))
            button.blockSignals(False)

    # === Raster: colour pipette ===

    def _on_pipette_toggled(self, checked: bool) -> None:
        self._controller._on_color_pick_toggled(checked)

    def set_pipette_checked(self, checked: bool) -> None:
        """The pixel picker left the map: the pipette button follows without running its slot."""
        button = self._tools.get('pushButton_checkable_exploring_raster_pipette')
        if button is not None:
            button.blockSignals(True)
            button.setChecked(bool(checked))
            button.blockSignals(False)

    # === Raster: value under the cursor ===

    def _canvas(self):
        iface = self._controller._iface()
        return iface.mapCanvas() if iface is not None else None

    def _on_hover_toggled(self, checked: bool) -> None:
        if checked:
            self._start_hover()
        else:
            self._stop_hover()

    def _start_hover(self) -> None:
        canvas = self._canvas()
        if canvas is None or self._hover_connected:
            return
        if self._hover_timer is None:
            self._hover_timer = QTimer(self)
            self._hover_timer.setSingleShot(True)
            self._hover_timer.setInterval(HOVER_DELAY_MS)
            self._hover_timer.timeout.connect(self._read_hover_value)
        canvas.xyCoordinates.connect(self._on_canvas_moved)
        self._hover_connected = True

    def _stop_hover(self) -> None:
        if self._hover_timer is not None:
            self._hover_timer.stop()
        self._hover_point = None
        if self._hover_connected:
            canvas = self._canvas()
            try:
                if canvas is not None:
                    canvas.xyCoordinates.disconnect(self._on_canvas_moved)
            except (TypeError, RuntimeError):
                pass
            self._hover_connected = False
        panel = self._controller._raster_panel
        if panel is not None:
            try:
                panel.set_hover_value(None, None)
            except RuntimeError:
                pass

    def _on_canvas_moved(self, point: Any) -> None:
        self._hover_point = point
        if self._hover_timer is not None and not self._hover_timer.isActive():
            self._hover_timer.start()

    def _layer_point(self, point: Any) -> Any:
        from qgis.core import QgsCoordinateTransform, QgsProject
        layer, canvas = self._controller.active_layer, self._canvas()
        try:
            transform = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(), layer.crs(), QgsProject.instance())
            return transform.transform(point)
        except Exception:
            return point

    def _read_hover_value(self) -> None:
        controller, point = self._controller, self._hover_point
        layer, panel = controller.active_layer, controller._raster_panel
        if layer is None or panel is None or point is None:
            return
        from ...adapters.qgis.coverage_layers.raster_adapter import identify_values
        layer_point = self._layer_point(point)
        try:
            key = (layer.id(), layer.source())
            if self._hover_base_key != key:
                # FilterMate derived source: the original raster is opened once, not every 60 ms;
                # again when a filter / undo changed the source.
                self._hover_base, self._hover_base_key = controller._base_raster(layer), key
            values = identify_values(self._hover_base, layer_point)
            derived = None
            if panel.current_derivative().is_terrain:
                terrain = controller._terrain_at(self._hover_base, layer_point)
                derived = terrain.get(panel.current_derivative())
        except Exception as exc:
            logger.debug(f"[FM5] value under the cursor unreadable: {exc}")
            return
        panel.set_hover_value(layer_point.x(), layer_point.y(), values.get(panel.current_band()), derived)

    # === Raster: range linked to the layer style ===

    def _on_link_toggled(self, checked: bool) -> None:
        panel = self._controller._raster_panel
        if panel is None:
            return
        if checked:
            if not self._link_connected:
                panel.selectionChanged.connect(self._apply_link)
                self._link_connected = True
            self._apply_link()
        else:
            if self._link_connected:
                try:
                    panel.selectionChanged.disconnect(self._apply_link)
                except (TypeError, RuntimeError):
                    pass
                self._link_connected = False
            self._unlink_style()

    def _link_range(self) -> Tuple[Optional[float], Optional[float]]:
        """Range of the panel, an open side replaced by the band minimum / maximum."""
        panel = self._controller._raster_panel
        selection = panel.selection() if panel is not None else None
        low, high = panel._data_bounds() if panel is not None else (None, None)
        if selection is not None and getattr(selection.mode, 'value', '') == 'range':
            low = selection.minimum if selection.minimum is not None else low
            high = selection.maximum if selection.maximum is not None else high
        return low, high

    def _apply_link(self, *_args) -> None:
        layer, panel = self._controller.active_layer, self._controller._raster_panel
        if layer is None or panel is None:
            return
        from ...adapters.qgis.coverage_layers.raster_adapter import link_range_to_style
        if panel.current_derivative().is_terrain:
            self._unlink_style()  # the range is in slope / aspect units, not in those of the style
            return
        selection = panel.selection()
        mode = getattr(getattr(panel, 'active_mode', lambda: None)(), 'value', '')
        if (selection is not None and getattr(selection.mode, 'value', '') != 'range') or (selection is None and mode == 'pipette'):
            # A colour, a class or an expression has no range: the current stretch stays as it is
            # (stretching over the whole data would undo the user's contrast for nothing).
            return
        low, high = self._link_range()
        try:
            if self._linked_layer_id not in (None, layer.id()):
                self._unlink_style()  # one linked raster at a time
            self._linked_layer_id = layer.id()
            if not link_range_to_style(layer, panel.current_band(), low, high):
                self._link_refused()
        except RuntimeError:
            pass

    def _link_refused(self) -> None:
        """The style has no single band range on the band of the panel: say so, the button comes up."""
        logger.debug("[FM5] this raster style has no single band range to link")
        button = self._tools.get('pushButton_checkable_exploring_raster_link')
        if button is not None and button.isChecked():
            button.setChecked(False)  # runs the toggled slot: disconnected, a previous link given back
        iface = self._controller._iface()
        if iface is not None:
            iface.messageBar().pushInfo("FilterMate", self.tr(
                "The style cannot follow the range: it needs a single band grey or pseudocolor style "
                "on the band of the panel"))

    def _unlink_style(self) -> None:
        """Give the linked raster its style back: the layer that was linked, which is no longer
        the active one when the controller has already moved to the next layer."""
        layer_id, self._linked_layer_id = self._linked_layer_id, None
        layer = self._controller._map_layer(layer_id) if layer_id is not None else None
        if layer is None:
            return
        from ...adapters.qgis.coverage_layers.raster_adapter import unlink_range_from_style
        try:
            unlink_range_from_style(layer)
        except RuntimeError:
            pass

    @staticmethod
    def _unlink_all_styles() -> None:
        from ...adapters.qgis.coverage_layers.raster_adapter import unlink_all_styles
        unlink_all_styles()

    # === Raster: statistics of a rectangle ===

    def _on_zone_toggled(self, checked: bool) -> None:
        if checked:
            self._start_zone_tool()
        else:
            self._stop_zone_tool()

    def _start_zone_tool(self) -> None:
        canvas = self._canvas()
        if canvas is None:
            return
        try:
            from qgis.gui import QgsMapToolExtent
        except ImportError:
            return
        if self._zone_tool is None:
            self._zone_tool = QgsMapToolExtent(canvas)
            self._zone_tool.extentChanged.connect(self._on_zone_drawn)
            self._zone_tool.deactivated.connect(self._on_zone_tool_deactivated)
        current = canvas.mapTool()
        if current is self._zone_tool:
            return
        controller = self._controller
        if current is not None and current is getattr(controller, '_pixel_tool', None):
            # Take over the tool the pixel picker would have restored: never restore the picker itself.
            current, controller._previous_map_tool = controller._previous_map_tool, None
        self._zone_previous_tool = current
        canvas.setMapTool(self._zone_tool)

    def _stop_zone_tool(self) -> None:
        canvas = self._canvas()
        if canvas is None or self._zone_tool is None or canvas.mapTool() is not self._zone_tool:
            self._zone_previous_tool = None
            return
        previous, self._zone_previous_tool = self._zone_previous_tool, None
        try:
            if previous is not None and previous is not self._zone_tool:
                canvas.setMapTool(previous)
                return
        except RuntimeError:
            pass  # the previous tool was deleted (plugin unloaded)
        canvas.unsetMapTool(self._zone_tool)

    def _release_zone_tool(self) -> None:
        tool, self._zone_tool = self._zone_tool, None
        if tool is None:
            return
        canvas = self._canvas()
        if canvas is not None and canvas.mapTool() is tool:
            canvas.unsetMapTool(tool)
        for signal, slot in ((tool.extentChanged, self._on_zone_drawn), (tool.deactivated, self._on_zone_tool_deactivated)):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        tool.deleteLater()

    def _on_zone_tool_deactivated(self) -> None:
        """Another map tool took over: the button follows, and that tool inherits ours."""
        controller = self._controller
        if getattr(controller, '_previous_map_tool', None) is self._zone_tool:
            # The pixel picker just remembered the rectangle tool: hand it the tool before ours.
            controller._previous_map_tool = self._zone_previous_tool
        self._zone_previous_tool = None
        button = self._tools.get('pushButton_checkable_exploring_raster_zone')
        if button is not None and button.isChecked():
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)

    def _on_zone_drawn(self, extent: Any) -> None:
        controller = self._controller
        layer, panel = controller.active_layer, controller._raster_panel
        if layer is None or panel is None or extent is None or extent.isEmpty():
            return
        try:
            from qgis.core import QgsCoordinateTransform, QgsProject
            from ...adapters.qgis.coverage_layers.raster_adapter import band_statistics
            canvas = self._canvas()
            transform = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(), layer.crs(), QgsProject.instance())
            rect = transform.transformBoundingBox(extent).intersect(layer.extent())
            if rect.isEmpty():
                panel.set_zone_statistics(None, None)
                return
            base = controller._base_raster(layer)
            band = panel.current_band()
            if panel.current_derivative().is_terrain:
                from ...adapters.qgis.coverage_layers.raster_adapter import derivative_zone_statistics
                found = derivative_zone_statistics(base, band, rect, panel.current_derivative(), ZONE_SAMPLE_SIZE)
                if found is None:
                    panel.set_zone_statistics(None, None)
                else:
                    panel.set_zone_statistics(*found)
                return
            stats = band_statistics(base.dataProvider(), band, rect, ZONE_SAMPLE_SIZE)
        except Exception as exc:
            logger.debug(f"[FM5] statistics of the rectangle unreadable: {exc}")
            return
        if stats.minimumValue > stats.maximumValue:
            panel.set_zone_statistics(None, None)
            return
        width = layer.width() or 0
        height = layer.height() or 0
        size_x = layer.extent().width() / width if width else 0.0
        size_y = layer.extent().height() / height if height else 0.0
        pixels = zone_pixel_estimate(rect.width(), rect.height(), size_x, size_y)
        count = int(stats.elementCount) if pixels is not None and pixels <= ZONE_SAMPLE_SIZE else None
        panel.set_zone_statistics(float(stats.minimumValue), float(stats.maximumValue), float(stats.mean), count)

    # === Point cloud: profile and 3D view ===

    def _main_window_action(self, names: Sequence[str]) -> Any:
        iface = self._controller._iface()
        if iface is None:
            return None
        try:
            from qgis.PyQt.QtGui import QAction
        except ImportError:  # QGIS < 3.34.2 (Qt5): QAction is in QtWidgets
            from qgis.PyQt.QtWidgets import QAction
        for name in names:
            try:
                action = iface.mainWindow().findChild(QAction, name)
            except Exception:
                action = None
            if action is not None:
                return action
        return None

    def _tools_enabled_by_action(self) -> None:
        for name, action_name in (('pushButton_exploring_point_cloud_profile', ACTION_ELEVATION_PROFILE),
                                  ('pushButton_exploring_point_cloud_3d', ACTION_NEW_3D_VIEW)):
            button = self._tools.get(name)
            if button is not None:
                button.setEnabled(self._main_window_action(action_name) is not None)

    def _trigger(self, action_names: Sequence[str]) -> None:
        action = self._main_window_action(action_names)
        if action is None:
            logger.info(f"[FM5] QGIS action {' / '.join(action_names)} not available in this version")
            return
        layer = self._controller.active_layer
        iface = self._controller._iface()
        try:
            if layer is not None and iface is not None:
                iface.setActiveLayer(layer)
            action.trigger()
        except Exception as exc:
            logger.debug(f"[FM5] QGIS action {action.objectName()} failed: {exc}")

    def _open_elevation_profile(self, *_args) -> None:
        self._trigger(ACTION_ELEVATION_PROFILE)

    def _open_3d_view(self, *_args) -> None:
        self._trigger(ACTION_NEW_3D_VIEW)

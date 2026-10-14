# -*- coding: utf-8 -*-
"""
Layout changes of the FilterMate 5 design (mockup), applied once after setupUi.

* EXPLORING: the tool rail sits beside the scroll area so its grey band takes the
  visible height, and its tools are spread evenly over that height.
* Section headers (FILTERING, EXPORTING, CONFIGURATION) get the mockup height.
* FILTERING, buffer: the buffer type and the segment count join the buffer
  value row (``25,00 m | Round | 5``). The emptied row and its spacer leave the
  values column, the buffer type button and its spacer leave the buttons
  column, so the two columns stay aligned row by row. The buffer type follows
  the buffer button: one switch, as in the mockup.
"""
import logging
from typing import Any

try:
    from qgis.PyQt.QtCore import QEvent, QObject
except ImportError:  # pragma: no cover - unit tests without Qt
    QEvent = QObject = None

logger = logging.getLogger(__name__)

BUFFER_TYPE_MAX_WIDTH = 110
SEGMENTS_MAX_WIDTH = 64


def _remove_spacer(layout: Any, name_hint: str, index_hint: int) -> bool:
    """Take the spacer at ``index_hint`` out of ``layout`` (spacers have no object name)."""
    if layout is None or not 0 <= index_hint < layout.count():
        return False
    item = layout.itemAt(index_hint)
    if item is None or item.spacerItem() is None:
        logger.debug(f"mockup layout: no spacer at {name_hint}")
        return False
    layout.takeAt(index_hint)
    return True


def _index_of_layout(parent: Any, child: Any) -> int:
    for index in range(parent.count()):
        if parent.itemAt(index).layout() is child:
            return index
    return -1


def merge_buffer_rows(dw: Any) -> bool:
    """Buffer type and segments on the buffer value row; True when done."""
    values = getattr(dw, 'verticalLayout_filtering_values', None)
    value_row = getattr(dw, 'horizontalLayout_filtering_values_buttons', None)
    type_row = getattr(dw, 'horizontalLayout_filtering_buffer_type_segments', None)
    combo = getattr(dw, 'comboBox_filtering_buffer_type', None)
    segments = getattr(dw, 'mQgsSpinBox_filtering_buffer_segments', None)
    keys = getattr(dw, 'verticalLayout_filtering_keys', None)
    value_button = getattr(dw, 'pushButton_checkable_filtering_buffer_value', None)
    type_button = getattr(dw, 'pushButton_checkable_filtering_buffer_type', None)
    if None in (values, value_row, type_row, combo, segments, keys, value_button, type_button):
        return False
    if dw.property('fm_buffer_rows_merged'):
        return True
    type_index = _index_of_layout(values, type_row)
    if type_index < 0:
        return False

    # Values column: widgets onto the value row, then the empty row and the spacer above it go.
    for widget, max_width in ((combo, BUFFER_TYPE_MAX_WIDTH), (segments, SEGMENTS_MAX_WIDTH)):
        type_row.removeWidget(widget)
        widget.setMaximumWidth(max_width)
        value_row.addWidget(widget)
    values.takeAt(type_index)
    _remove_spacer(values, 'verticalSpacer_filtering_values_buttons_bottom1', type_index - 1)

    # Buttons column: the buffer type button and the spacer above it go too.
    button_index = keys.indexOf(type_button)
    if button_index >= 0:
        keys.takeAt(button_index)
        type_button.setVisible(False)
        _remove_spacer(keys, 'verticalSpacer_filtering_keys_field_bottom', button_index - 1)

    def follow(checked: bool) -> None:
        if type_button.isChecked() != checked:
            type_button.setChecked(checked)

    value_button.toggled.connect(follow)
    dw.setProperty('fm_buffer_rows_merged', True)
    return True


def rail_gap(available: int, heights, minimum: int = 6) -> int:
    """Even gap spreading buttons of ``heights`` over ``available`` px (one gap above, between, below)."""
    heights = [int(h) for h in heights if h > 0]
    if not heights:
        return minimum
    free = int(available) - sum(heights)
    return max(minimum, free // (len(heights) + 1))


class _RailSpreader(QObject if QObject is not None else object):
    """Keeps the EXPLORING tools spread over the whole height of their grey band.

    Recomputed on resize and whenever a button is shown or hidden (raster / point
    cloud tools, tracking and linking hidden), so the gaps stay even.
    """

    def __init__(self, rail: Any, layout: Any) -> None:
        super().__init__(rail)
        self._rail, self._layout = rail, layout
        rail.installEventFilter(self)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest):
            self.spread()
        return False

    def spread(self) -> None:
        layout = self._layout
        buttons = [layout.itemAt(i).widget() for i in range(layout.count())]
        heights = [w.height() or w.sizeHint().height() for w in buttons if w is not None and not w.isHidden()]
        outer = self._rail.layout()
        margins = outer.contentsMargins() if outer is not None else None
        available = self._rail.height() - ((margins.top() + margins.bottom()) if margins is not None else 0)
        gap = rail_gap(available, heights)
        if layout.spacing() != gap:
            layout.setSpacing(gap)
        top = layout.contentsMargins()
        if top.top() != gap:
            layout.setContentsMargins(top.left(), gap, top.right(), 0)


def pack_exploring_rail(dw: Any) -> bool:
    """EXPLORING tools spread evenly over the whole grey band (user request on the mockup).

    The spacers between the buttons go, an even gap computed from the visible
    buttons replaces them, and a stretch below takes the rounding.
    """
    layout = getattr(dw, 'verticalLayout_exploring_content', None)
    rail = getattr(dw, 'widget_exploring_keys', None)
    if layout is None or rail is None or layout.property('fm_packed'):
        return layout is not None
    for index in reversed(range(layout.count())):
        if layout.itemAt(index).spacerItem() is not None:
            layout.takeAt(index)
    layout.addStretch(1)
    layout.setProperty('fm_packed', True)
    dw._fm_rail_spreader = _RailSpreader(rail, layout)
    layout.invalidate()
    return True


SECTION_TAB_HEIGHT = 34
SECTION_ICON_SIZE = 16
SECTION_ICON_LEFT = 12
SECTION_ICONS = ('filter', 'export', 'settings')  # FILTERING, EXPORTING, CONFIGURATION


def size_section_tabs(dw: Any) -> bool:
    """FILTERING / EXPORTING / CONFIGURATION headers 34 px high, as in the mockup.

    QToolBox sizes its tab buttons from their size hint and ignores the
    stylesheet heights: the icon was drawn above the text in a 25 px button.
    """
    toolbox = getattr(dw, 'toolBox_tabTools', None)
    if toolbox is None:
        return False
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtGui import QIcon
    from qgis.PyQt.QtWidgets import QAbstractButton, QLabel
    buttons = {button.text(): button for button in toolbox.findChildren(QAbstractButton)
               if button.objectName() == 'qt_toolbox_toolboxbutton'}
    labels = {}
    for index in range(toolbox.count()):
        button = buttons.get(toolbox.itemText(index))
        if button is None:
            continue
        button.setMinimumHeight(SECTION_TAB_HEIGHT)
        # Qt draws a tab icon at the top of the tab: the icon becomes a label centred on the left.
        toolbox.setItemIcon(index, QIcon())
        label = QLabel(button)
        label.setObjectName('label_section_icon')
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        label.setScaledContents(True)  # a 64 px pixmap shown at 16 px stays sharp on HiDPI screens
        label.setGeometry(SECTION_ICON_LEFT, (SECTION_TAB_HEIGHT - SECTION_ICON_SIZE) // 2,
                          SECTION_ICON_SIZE, SECTION_ICON_SIZE)
        labels[index] = label
    dw._fm_section_icon_labels = labels
    update_section_icons(dw)
    return bool(labels)


def update_section_icons(dw: Any, dark: Any = None) -> bool:
    """Draw the section header icons in the theme color; False when the tabs keep native icons."""
    labels = getattr(dw, '_fm_section_icon_labels', None)
    if not labels:
        return False
    from ..styles.mockup_design import render_icon
    if dark is None:
        dark = bool(getattr(getattr(dw, '_icon_manager', None), 'is_dark_mode', False))
    for index, label in labels.items():
        if index < len(SECTION_ICONS):
            icon = render_icon(SECTION_ICONS[index], dark)
            if icon is not None:
                label.setPixmap(icon.pixmap(64, 64))
    return True


RAIL_GAP = 8
RAIL_LEFT_INSET = 5  # lines the EXPLORING rail up with the FILTERING one (toolbox page padding)


def rail_outside_scroll(dw: Any) -> bool:
    """EXPLORING rail beside the scroll area instead of inside it (mockup).

    Inside, the grey band took the height of the scrolled content (cut at the bottom, or
    short); beside it, the band takes the visible height and only the groups scroll.
    """
    rail = getattr(dw, 'widget_exploring_keys', None)
    grid = getattr(dw, 'gridLayout_main_actions', None)
    outer = getattr(dw, 'verticalLayout_main_content', None)
    scroll = getattr(dw, 'scrollArea_frame_exploring', None)
    if None in (rail, grid, outer, scroll) or dw.property('fm_rail_outside'):
        return False
    index = outer.indexOf(scroll)
    if index < 0 or grid.indexOf(rail) < 0:
        return False
    from qgis.PyQt.QtWidgets import QHBoxLayout
    grid.removeWidget(rail)
    grid.setColumnMinimumWidth(0, 0)
    grid.setHorizontalSpacing(0)
    outer.removeWidget(scroll)
    row = QHBoxLayout()
    row.setObjectName('horizontalLayout_exploring_rail_and_groups')
    row.setContentsMargins(RAIL_LEFT_INSET, 0, 0, 0)
    row.setSpacing(RAIL_GAP)
    row.addWidget(rail, 0)
    row.addWidget(scroll, 1)
    outer.insertLayout(index, row, 1)
    dw.setProperty('fm_rail_outside', True)
    return True


def apply_mockup_layout(dw: Any) -> None:
    """Every layout change of the design; each one is skipped on its own if the form differs."""
    for change in (merge_buffer_rows, pack_exploring_rail, size_section_tabs, rail_outside_scroll):
        try:
            change(dw)
        except Exception as exc:
            logger.warning(f"mockup layout change {change.__name__} skipped: {exc}")

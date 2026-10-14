# -*- coding: utf-8 -*-
"""
Layout changes of the FilterMate 5 design (mockup), applied once after setupUi.

* EXPLORING: the tool rail sits beside the scroll area so its grey band takes the
  visible height, and its tools are spread evenly over that height.
* Section headers (FILTERING, EXPORTING, CONFIGURATION) get the mockup height.
* One 8 px vertical rhythm: header, EXPLORING, sections; FILTERING / EXPORTING rows grouped at the top.
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
RAIL_LEFT_INSET = 3  # lines the EXPLORING rail up with the FILTERING one (toolbox page padding)


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


BLOCK_GAP = 8          # between the header, EXPLORING and each section of the tool box
HEADER_HEIGHT = 32     # badges are 24 px high: 4 px above and below
ROW_GAP = 6            # between two rows of FILTERING / EXPORTING


def tighten_vertical_rhythm(dw: Any) -> bool:
    """One 8 px rhythm from the header to the action bar (mockup).

    * The header was fixed at 13 px while its badges are 24 px high.
    * The tool box laid its section headers edge to edge (stylesheet margins are ignored).
    * FILTERING and EXPORTING pages took the whole tool box height and their expanding
      spacers spread the rows apart: the pages now sit at the top at their natural height
      (both columns keep their spacers, so the buttons stay in front of their rows).
    """
    from qgis.PyQt.QtCore import Qt
    header = getattr(dw, 'frame_header', None)
    if header is not None:
        header.setFixedHeight(HEADER_HEIGHT)
    toolset = getattr(dw, 'frame_toolset', None)
    if toolset is not None and toolset.layout() is not None:
        toolset.layout().setContentsMargins(0, 0, 0, 0)
    toolbox = getattr(dw, 'toolBox_tabTools', None)
    if toolbox is None:
        return False
    if toolbox.layout() is not None:
        toolbox.layout().setSpacing(BLOCK_GAP)
    for index in range(toolbox.count()):
        page = toolbox.widget(index)
        if page is not None and page.objectName() in ('FILTERING', 'EXPORTING') and page.layout() is not None:
            page.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
    # Rows of the values columns closer together (mockup); the key buttons follow (align_key_columns).
    for name in ('verticalLayout_filtering_values', 'verticalLayout_exporting_values'):
        values = getattr(dw, name, None)
        if values is None:
            continue
        values.setSpacing(ROW_GAP)
        for position in reversed(range(values.count())):
            if values.itemAt(position).spacerItem() is not None:
                values.takeAt(position)  # a 0 px spacer still costs one layout spacing
    return True


FILTERING_PAIRS = (
    ('pushButton_checkable_filtering_auto_current_layer', 'comboBox_filtering_current_layer'),
    ('pushButton_checkable_filtering_layers_to_filter', 'checkableComboBoxLayer_filtering_layers_to_filter'),
    ('pushButton_checkable_filtering_current_layer_combine_operator', 'comboBox_filtering_source_layer_combine_operator'),
    ('pushButton_checkable_filtering_geometric_predicates', 'comboBox_filtering_geometric_predicates'),
    ('pushButton_checkable_filtering_buffer_value', 'mQgsDoubleSpinBox_filtering_buffer_value'),
)
EXPORTING_PAIRS = (
    ('pushButton_checkable_exporting_layers', 'checkableComboBoxLayer_exporting_layers'),
    ('pushButton_checkable_exporting_projection', 'mQgsProjectionSelectionWidget_exporting_projection'),
    ('pushButton_checkable_exporting_styles', 'comboBox_exporting_styles'),
    ('pushButton_checkable_exporting_datatype', 'comboBox_exporting_datatype'),
    ('pushButton_checkable_exporting_output_folder', 'lineEdit_exporting_output_folder'),
    ('pushButton_checkable_exporting_zip', 'lineEdit_exporting_zip'),
)


def spacer_adjustments(deltas) -> list:
    """Height to add to the spacer above each button so its centre meets its row's.

    ``deltas[i]`` = row centre - button centre, measured before any change; moving
    the spacer above button i also moves every later button, hence the running shift.
    """
    shift, out = 0, []
    for delta in deltas:
        needed = int(round(delta)) - shift
        out.append(needed)
        shift += needed
    return out


class _ColumnAligner(QObject if QObject is not None else object):
    """Puts each key button in front of its value row, exactly.

    The two columns of FILTERING / EXPORTING are separate layouts; their expanding
    spacers only lined up while the page was stretched. Here the spacer above each
    button gets the height that centres it on its row, after every layout pass.
    """

    def __init__(self, page: Any, keys_layout: Any, pairs) -> None:
        super().__init__(page)
        self._page, self._keys, self._pairs = page, keys_layout, list(pairs)
        self._pending = False
        page.installEventFilter(self)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest) and not self._pending:
            self._pending = True
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(0, self.align)  # positions are final once the layout pass is over
        return False

    def _spacer_above(self, button: Any):
        index = self._keys.indexOf(button)
        for position in range(index - 1, -1, -1):
            item = self._keys.itemAt(position)
            if item.widget() is not None and isinstance(item.widget(), type(button)):
                return None  # reached the previous button: no spacer of its own
            if item.spacerItem() is not None:
                return item.spacerItem()
        return None

    def align(self) -> None:
        self._pending = False
        try:
            rows = []
            for button, value in self._pairs:
                if button.isHidden() or value.isHidden() or self._keys.indexOf(button) < 0:
                    continue
                spacer = self._spacer_above(button)
                b = button.mapTo(self._page, button.rect().center()).y()
                v = value.mapTo(self._page, value.rect().center()).y()
                rows.append((spacer, v - b))
            if not rows or all(abs(delta) < 1 for _, delta in rows):
                return
            from qgis.PyQt.QtWidgets import QSizePolicy
            for (spacer, _), needed in zip(rows, spacer_adjustments([delta for _, delta in rows])):
                if spacer is None or needed == 0:
                    continue
                height = max(0, spacer.sizeHint().height() + needed)
                spacer.changeSize(spacer.sizeHint().width(), height, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            self._keys.invalidate()
        except RuntimeError:
            pass  # widgets deleted (plugin closing)


def align_key_columns(dw: Any) -> bool:
    """Exact button / row alignment in FILTERING and EXPORTING (see :class:`_ColumnAligner`)."""
    done = False
    for page_name, keys_name, pairs in (('FILTERING', 'verticalLayout_filtering_keys', FILTERING_PAIRS),
                                        ('EXPORTING', 'verticalLayout_exporting_keys', EXPORTING_PAIRS)):
        page, keys = getattr(dw, page_name, None), getattr(dw, keys_name, None)
        widgets = [(getattr(dw, b, None), getattr(dw, v, None)) for b, v in pairs]
        widgets = [(b, v) for b, v in widgets if b is not None and v is not None]
        if page is None or keys is None or not widgets:
            continue
        setattr(dw, f'_fm_aligner_{page_name.lower()}', _ColumnAligner(page, keys, widgets))
        done = True
    return done


class _ToolBoxFitter(QObject if QObject is not None else object):
    """Tool box only as tall as its headers plus the natural height of the open section.

    QToolBox gives the open page all the remaining height; with the FILTERING rows
    grouped at the top that left a blank before EXPORTING. The surplus now goes below
    the last header (mockup), and a page that does not fit still scrolls.
    """

    def __init__(self, toolbox: Any) -> None:
        super().__init__(toolbox)
        self._toolbox = toolbox
        self._pending = False
        toolbox.currentChanged.connect(self._schedule)
        for index in range(toolbox.count()):
            page = toolbox.widget(index)
            if page is not None:
                page.installEventFilter(self)
        toolbox.installEventFilter(self)
        self._schedule()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.Show):
            self._schedule()
        return False

    def _schedule(self, *_args) -> None:
        if not self._pending:
            self._pending = True
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(0, self.fit)

    def fit(self) -> None:
        self._pending = False
        try:
            toolbox = self._toolbox
            layout = toolbox.layout()
            page = toolbox.currentWidget()
            if layout is None or page is None:
                return
            from qgis.PyQt.QtWidgets import QAbstractButton
            headers = [b for b in toolbox.findChildren(QAbstractButton)
                       if b.objectName() == 'qt_toolbox_toolboxbutton' and not b.isHidden()]
            natural = page.layout().sizeHint().height() if page.layout() is not None else page.sizeHint().height()
            margins = layout.contentsMargins()
            frame = 2 * toolbox.frameWidth() if hasattr(toolbox, 'frameWidth') else 0
            height = (sum(max(b.height(), b.minimumHeight()) for b in headers) + natural + 4
                      + layout.spacing() * len(headers) + margins.top() + margins.bottom() + frame)
            if toolbox.maximumHeight() != height:
                toolbox.setMaximumHeight(height)
        except RuntimeError:
            pass


def fit_tool_box(dw: Any) -> bool:
    """See :class:`_ToolBoxFitter`; a stretch under the tool box takes the surplus."""
    toolbox = getattr(dw, 'toolBox_tabTools', None)
    container = getattr(dw, 'verticalLayout_filtering_container', None)
    if toolbox is None or container is None or container.indexOf(toolbox) < 0:
        return False
    container.addStretch(1)
    dw._fm_toolbox_fitter = _ToolBoxFitter(toolbox)
    return True


def apply_mockup_layout(dw: Any) -> None:
    """Every layout change of the design; each one is skipped on its own if the form differs."""
    for change in (merge_buffer_rows, pack_exploring_rail, size_section_tabs, rail_outside_scroll,
                   tighten_vertical_rhythm, align_key_columns, fit_tool_box):
        try:
            change(dw)
        except Exception as exc:
            logger.warning(f"mockup layout change {change.__name__} skipped: {exc}")

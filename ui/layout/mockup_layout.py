# -*- coding: utf-8 -*-
"""
Layout changes of the FilterMate 5 design (mockup), applied once after setupUi.

* EXPLORING: the tool rail sits beside the scroll area so its grey band takes the
  visible height, and its tools are spread evenly over that height.
* Section headers (FILTERING, EXPORTING, CONFIGURATION) get the mockup height.
* One spacing scale (``SPACING`` in ``ui/styles/mockup_design.py``, also used by mockup.qss):
  every block between the same edges and 8 px apart, 6 px between two widgets (rows, fields,
  groups, rail and widgets), 8 px inside a group, 34 px title bands (section headers, collapsed
  groups). FILTERING / EXPORTING rows grouped at the top.
* FILTERING, buffer: the buffer type and the segment count join the buffer
  value row (``25,00 m | Round | 5``). The emptied row and its spacer leave the
  values column, the buffer type button and its spacer leave the buttons
  column, so the two columns stay aligned row by row. The buffer type follows
  the buffer button: one switch, as in the mockup.
"""
import logging
import os
from typing import Any

try:
    from qgis.PyQt.QtCore import QEvent, QObject
except ImportError:  # pragma: no cover - unit tests without Qt
    QEvent = QObject = None

from ..styles.mockup_design import HEADER_BADGE_HEIGHT, SPACING

logger = logging.getLogger(__name__)

EDGE = SPACING['fm_edge']      # dock edge -> every block
BLOCK = SPACING['fm_block']    # between two blocks
GAP = SPACING['fm_gap']        # between two widgets
INSET = SPACING['fm_inset']    # group border -> its widgets (mockup.qss padding)
BAND = SPACING['fm_band']      # section header / collapsed group height
DOCK_MARGIN = 2                # dockWidgetContents layout margin, part of EDGE
QWIDGETSIZE_MAX = 16777215

_SPLITTER_SHEET = (
    "QSplitter::handle:vertical {{ margin: 0px 30px; background-color: transparent; image: url({grip}); }}"
    "QSplitter::handle:vertical:hover, QSplitter::handle:vertical:pressed"
    " {{ background-color: transparent; image: url({hover}); }}"
)


def _style_file(name: str) -> str:
    """Path of a file of resources/styles, with forward slashes for a stylesheet url()."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, 'resources', 'styles', name).replace('\\', '/')


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
    # The data-defined override button goes last: the row starts with the value, like the others.
    override = getattr(dw, 'mPropertyOverrideButton_filtering_buffer_value_property', None)
    if override is not None and value_row.indexOf(override) >= 0:
        value_row.removeWidget(override)
        value_row.addWidget(override)
    values.takeAt(type_index)
    _remove_spacer(values, 'verticalSpacer_filtering_values_buttons_bottom1', type_index - 1)

    # Buttons column: the buffer type button and the spacer above it go too.
    button_index = keys.indexOf(type_button)
    if button_index >= 0:
        keys.takeAt(button_index)
        type_button.setVisible(False)
        _remove_spacer(keys, 'verticalSpacer_filtering_keys_field_bottom', button_index - 1)

    link_buffer_type_to_value(value_button, type_button, combo, segments)
    dw.setProperty('fm_buffer_rows_merged', True)
    return True


def link_buffer_type_to_value(value_button: Any, type_button: Any, combo: Any, segments: Any = None) -> None:
    """The hidden buffer type switch follows the buffer value row (FilterMate 5 design).

    It follows the value switch, and (2026-10-17) it is turned on when the
    type or the segment count is changed while a buffer is active: the type
    shown on the row is the type applied. ``has_buffer_type`` used to stay
    False after a layer change (signals blocked), and Flat / Square buffers
    came out Round. The filter task applies the type whenever a buffer is
    active anyway (SourceSubsetBufferBuilder._extract_buffer_type); this keeps
    the stored flag, the favorites and the history consistent with it.
    """
    def follow(checked: bool) -> None:
        if type_button.isChecked() != checked:
            type_button.setChecked(checked)

    def type_changed(*_args) -> None:
        if value_button.isChecked() and not type_button.isChecked():
            type_button.setChecked(True)

    value_button.toggled.connect(follow)
    combo.currentIndexChanged.connect(type_changed)
    if segments is not None and hasattr(segments, 'valueChanged'):
        segments.valueChanged.connect(type_changed)


GAP_ITEM = None  # an expanding gap in a rail plan


def rail_plan(visible) -> list:
    """Order of the rail items: an expanding gap above, between and below the visible buttons.

    ``visible[i]`` tells whether button ``i`` is shown; hidden buttons keep their place
    without a gap of their own, so the shown ones stay evenly spread.
    """
    plan = []
    for index, shown in enumerate(visible):
        if shown:
            plan.append(GAP_ITEM)
        plan.append(index)
    if any(visible):
        plan.append(GAP_ITEM)
    return plan


def rail_floor(button_heights, gap: int) -> int:
    """Height under which the rail buttons would overlap: the shown buttons plus one gap around each."""
    heights = [int(h) for h in button_heights]
    return sum(heights) + gap * (len(heights) + 1) if heights else 0


COMPACT_BUTTON_MIN = 22  # a rail button never goes under this (16 px icon with a margin)


def compact_height(available: int, count: int, gap: int, natural: int) -> int:
    """Height of the rail buttons for the band height ``available``: natural when it fits, else compacted.

    A vector layer with eight tools and collapsed groups gives the rail a 260 px band for
    342 px of buttons (2026-10-18): rather than overlapping, or forcing EXPLORING taller (the
    splitter could no longer shrink it), the buttons share the band with one gap around each,
    never under :data:`COMPACT_BUTTON_MIN`.
    """
    if count <= 0:
        return natural
    if rail_floor([natural] * count, gap) <= available:
        return natural
    return max(COMPACT_BUTTON_MIN, min(natural, (available - gap * (count + 1)) // count))


class _RailSpreader(QObject if QObject is not None else object):
    """Keeps the EXPLORING tools spread over the whole height of their grey band.

    The buttons sit between expanding gaps of at least ``GAP``: the free height is shared
    and the rail minimum stays the buttons plus those gaps (a spacing computed from the
    height entered the minimum, and the splitter could no longer shrink EXPLORING). Rebuilt when a button is shown, hidden or added (raster /
    point cloud tools of ``coverage_dock_extras``, tracking and linking hidden).
    """

    def __init__(self, rail: Any, layout: Any, dw: Any = None) -> None:
        super().__init__(rail)
        self._layout = layout
        self._dw = dw
        self._state = None
        self._watched = set()
        self._pending = False
        rail.installEventFilter(self)
        self.spread()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        try:
            if event.type() in (QEvent.Type.ShowToParent, QEvent.Type.HideToParent,
                                QEvent.Type.ChildAdded, QEvent.Type.LayoutRequest):
                self._schedule()
            elif event.type() == QEvent.Type.Resize and watched is self.parent():
                self._fit()  # the band changed: the buttons fit it (compact or natural)
        except RuntimeError:
            pass  # plugin closing
        return False

    def _schedule(self) -> None:
        if not self._pending:
            self._pending = True
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(0, self.spread)

    def reset(self) -> None:
        """Rebuild even if no button changed: the dimensions manager resets the rail spacing and
        resizes its spacers (``apply_dynamic_dimensions`` runs after this spreader is built)."""
        self._state = None
        self.spread()

    def spread(self) -> None:
        self._pending = False
        try:
            layout = self._layout
            items = [layout.itemAt(i) for i in range(layout.count())]
            buttons = [(item.widget(), item.alignment()) for item in items if item.widget() is not None]
            visible = [not button.isHidden() for button, _ in buttons]
            state = tuple((id(button), shown) for (button, _), shown in zip(buttons, visible))
            if state == self._state:
                return
            self._state = state
            for button, _ in buttons:
                if id(button) not in self._watched:
                    button.installEventFilter(self)  # its show / hide re-spreads the rail
                    self._watched.add(id(button))
            from qgis.PyQt.QtWidgets import QSizePolicy, QSpacerItem
            while layout.count():
                layout.takeAt(0)
            for entry in rail_plan(visible):
                if entry is GAP_ITEM:
                    layout.addItem(QSpacerItem(0, GAP, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.MinimumExpanding))
                else:
                    layout.addWidget(buttons[entry][0], 0, buttons[entry][1])
            layout.setSpacing(0)
            margins = layout.contentsMargins()
            layout.setContentsMargins(margins.left(), 0, margins.right(), 0)
            layout.invalidate()
            self._fit([button for (button, _), shown in zip(buttons, visible) if shown])
        except RuntimeError:
            pass  # plugin closing

    def _shown_buttons(self) -> list:
        layout = self._layout
        return [layout.itemAt(i).widget() for i in range(layout.count())
                if layout.itemAt(i).widget() is not None and not layout.itemAt(i).widget().isHidden()]

    def _fit(self, shown=None) -> None:
        """The shown buttons take their natural height when the band has room, else a compact one.

        The frame keeps its configured minimum (the splitter can still shrink EXPLORING): a band
        shorter than the buttons plus their gaps compacts the buttons (:func:`compact_height`)
        instead of overlapping them. The natural height (the dimensions manager's) is kept on
        each button and given back when the band grows.
        """
        rail = self.parent()
        if rail is None:
            return
        try:
            buttons = self._shown_buttons() if shown is None else list(shown)
            if not buttons:
                return
            naturals = []
            for button in buttons:
                natural = button.property('fm_natural_height')
                if natural is None:
                    natural = max(button.minimumHeight(), button.sizeHint().height())
                    button.setProperty('fm_natural_height', natural)
                    button.setProperty('fm_natural_max', button.maximumHeight())
                naturals.append(int(natural))
            margins = self._layout.contentsMargins()
            available = rail.height() - margins.top() - margins.bottom()
            if available <= 0:
                return
            natural = max(naturals)
            height = compact_height(available, len(buttons), GAP, natural)
            for button in buttons:
                wanted = min(height, int(button.property('fm_natural_height')))
                if height >= natural:  # room enough: the natural sizes come back
                    if button.minimumHeight() != wanted or button.maximumHeight() != int(button.property('fm_natural_max')):
                        button.setMinimumHeight(wanted)
                        button.setMaximumHeight(int(button.property('fm_natural_max')))
                elif button.minimumHeight() != wanted or button.maximumHeight() != wanted:
                    button.setFixedHeight(wanted)
        except RuntimeError:
            pass


def pack_exploring_rail(dw: Any) -> bool:
    """EXPLORING tools spread evenly over the whole grey band (user request on the mockup)."""
    layout = getattr(dw, 'verticalLayout_exploring_content', None)
    rail = getattr(dw, 'widget_exploring_keys', None)
    if layout is None or rail is None or layout.property('fm_packed'):
        return layout is not None
    for index in reversed(range(layout.count())):
        if layout.itemAt(index).spacerItem() is not None:
            layout.takeAt(index)
    layout.setProperty('fm_packed', True)
    dw._fm_rail_spreader = _RailSpreader(rail, layout, dw)
    return True


SECTION_TAB_HEIGHT = BAND
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
    if getattr(dw, '_fm_section_icon_labels', None):
        return True  # already done: a second pass would stack a second set of labels
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
    """Draw the section header icons in the theme color.

    False when the tabs keep native icons or when no icon could be drawn (QtSvg missing).
    """
    labels = getattr(dw, '_fm_section_icon_labels', None)
    if not labels:
        return False
    from ..styles.mockup_design import render_icon
    if dark is None:
        dark = bool(getattr(getattr(dw, '_icon_manager', None), 'is_dark_mode', False))
    drawn = False
    for index, label in labels.items():
        icon = render_icon(SECTION_ICONS[index], dark) if index < len(SECTION_ICONS) else None
        label.setVisible(icon is not None)
        if icon is not None:
            label.setPixmap(icon.pixmap(64, 64))
            drawn = True
    return drawn


RAIL_GAP = GAP       # rail -> widgets, as in FILTERING / EXPORTING
RAIL_LEFT_INSET = 0  # both rails start at the dock edge


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


BLOCK_GAP = BLOCK      # between the header, EXPLORING and each section of the tool box
BADGE_HEIGHT = HEADER_BADGE_HEIGHT
HEADER_HEIGHT = BADGE_HEIGHT + BLOCK  # badges one block below the dock title
ROW_GAP = GAP          # between two rows of FILTERING / EXPORTING


def tighten_vertical_rhythm(dw: Any) -> bool:
    """One 8 px rhythm from the header to the action bar (mockup).

    * The header was fixed at 13 px while its badges are 24 px high.
    * The tool box laid its section headers edge to edge (stylesheet margins are ignored).
    * FILTERING and EXPORTING rows: one stretch between two rows (see below); the lower
      zone is resized with the splitter (no height cap on the tool box).
    """
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
    # Rows of the values columns: one stretch between two rows, so a taller section (the
    # splitter lets the user enlarge the lower zone) spreads its rows evenly and a short one
    # keeps the row gap; the key buttons follow their rows (align_key_columns).
    for name in ('verticalLayout_filtering_values', 'verticalLayout_exporting_values'):
        values = getattr(dw, name, None)
        if values is None:
            continue
        values.setSpacing(ROW_GAP)
        for position in reversed(range(values.count())):
            if values.itemAt(position).spacerItem() is not None:
                values.takeAt(position)  # the .ui spacers: two of them between some rows
        for position in reversed(range(1, values.count())):
            values.insertStretch(position, 1)
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


def spacer_adjustments(deltas, adjustable=None) -> list:
    """Height to add to the spacer above each button so its centre meets its row's.

    ``deltas[i]`` = row centre - button centre, measured before any change; moving
    the spacer above button i also moves every later button, hence the running shift.
    ``adjustable[i]`` False: no spacer above button i, it gets 0 and shifts nothing.
    """
    shift, out = 0, []
    for index, delta in enumerate(deltas):
        if adjustable is not None and not adjustable[index]:
            out.append(0)
            continue
        needed = int(round(delta)) - shift
        out.append(needed)
        shift += needed
    return out


class _ColumnAligner(QObject if QObject is not None else object):
    """Puts each key button in front of its value row, exactly.

    The two columns of FILTERING / EXPORTING are separate layouts; their expanding
    spacers only lined up while the page was stretched. Here the spacer above each
    button gets the height that centres it on its row, after every layout pass.

    The layout is invalidated only when a spacer really changed, and at most
    ``MAX_ROUNDS`` passes follow one another until the next resize or show: when the
    exact position cannot be reached (spacer already at 0, no spacer) the aligner stops
    instead of looping on its own layout requests. Hidden pages are left alone.
    """

    MAX_ROUNDS = 6

    def __init__(self, page: Any, keys_layout: Any, pairs) -> None:
        super().__init__(page)
        self._page, self._keys, self._pairs = page, keys_layout, list(pairs)
        self._pending = False
        self._rounds = 0
        page.installEventFilter(self)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        try:
            kind = event.type()
            if kind in (QEvent.Type.Resize, QEvent.Type.Show):
                self._rounds = 0
            if kind in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest):
                self.schedule()
        except RuntimeError:
            pass
        return False

    def schedule(self) -> None:
        """Align once the current layout pass is over (positions are final then)."""
        if not self._pending:
            self._pending = True
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(0, self.align)

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
            if not self._page.isVisible():
                return
            if self._pairs:
                _keys_follow_rows(self._pairs[0][0].parentWidget())
            rows = []
            for button, value in self._pairs:
                if button.isHidden() or value.isHidden() or self._keys.indexOf(button) < 0:
                    continue
                spacer = self._spacer_above(button)
                b = button.mapTo(self._page, button.rect().center()).y()
                v = value.mapTo(self._page, value.rect().center()).y()
                rows.append((spacer, v - b))
            if not rows or all(abs(delta) < 1 for _, delta in rows):
                self._rounds = 0
                return
            if self._rounds >= self.MAX_ROUNDS:
                return  # cannot be reached exactly: wait for the next resize, show or aligned pass
            from qgis.PyQt.QtWidgets import QSizePolicy
            changed = False
            adjustments = spacer_adjustments([delta for _, delta in rows], [spacer is not None for spacer, _ in rows])
            for (spacer, _), needed in zip(rows, adjustments):
                if spacer is None or needed == 0:
                    continue
                current = spacer.sizeHint().height()
                height = max(0, current + needed)
                if height != current:
                    spacer.changeSize(spacer.sizeHint().width(), height, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                    changed = True
            if changed:
                self._rounds += 1
                self._keys.invalidate()
        except RuntimeError:
            pass  # widgets deleted (plugin closing)


def _keys_follow_rows(holder: Any) -> None:
    """The key column follows the value rows and never sets the page height.

    The aligner grows the fixed spacers of the key column up to the value rows; those rows
    are spread by stretches over the page height. With the key column counting in the page's
    minimum height, every alignment made the page taller (it sits in a resizable scroll area),
    the stretches wider and the next alignment larger: rows ended up 4000 px apart (FILTERING
    showed one row). With an ``Ignored`` vertical policy its height is the row's, set by the
    value column alone. ``holder`` is the widget holding the key buttons (widget_filtering_keys).
    An explicit minimum height (1 px) wins over the minimum size hint whatever the policy, which
    the dimension managers reset: both are enforced at every alignment pass.
    """
    from qgis.PyQt.QtWidgets import QSizePolicy
    if holder is None:
        return
    if holder.minimumHeight() != 1:
        holder.setMinimumHeight(1)
    policy = holder.sizePolicy()
    if policy.verticalPolicy() != QSizePolicy.Policy.Ignored:
        policy.setVerticalPolicy(QSizePolicy.Policy.Ignored)
        holder.setSizePolicy(policy)


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
        if getattr(dw, f'_fm_aligner_{page_name.lower()}', None) is None:
            setattr(dw, f'_fm_aligner_{page_name.lower()}', _ColumnAligner(page, keys, widgets))
        done = True
    return done


FIELD_GAP = GAP    # between two widgets of one row
SCROLLBAR_MARGIN = 6  # between the widgets and the scroll bar (user request)
GROUP_GAP = GAP    # between two EXPLORING groups, and between their rows


def _row_widgets(layout: Any):
    """Widgets placed directly in ``layout`` and its sub-layouts (not their children)."""
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is not None:
            yield item.widget()
        elif item.layout() is not None:
            yield from _row_widgets(item.layout())


def _row_layouts(layout: Any):
    for index in range(layout.count()):
        child = layout.itemAt(index).layout()
        if child is not None:
            yield child
            yield from _row_layouts(child)


def _set_layout(layout: Any, margins=None, spacing=None) -> None:
    if layout is None:
        return
    if margins is not None:
        layout.setContentsMargins(*margins)
    if spacing is not None:
        layout.setSpacing(spacing)


class _CollapsedBand(QObject if QObject is not None else object):
    """Keeps a collapsed group exactly one title band high.

    QgsCollapsibleGroupBox caps a collapsed group at its title height plus 6 px,
    but its minimum still counts the stylesheet padding, the layout margins and the
    minimum set by the dimensions manager: collapsed groups came out 60 px high in
    EXPLORING and 25 px in the raster panel. Refitted on every resize and show (the
    dock disconnects ``collapsedStateChanged`` wholesale, and QGIS sets its own
    maximum in its showEvent, after this filter); the expanded minimum is kept.
    """

    def __init__(self, group: Any) -> None:
        super().__init__(group)
        self._group = group
        self._pending = False
        self._collapsed = False
        self._expanded_min = group.minimumHeight()
        group.installEventFilter(self)
        self.fit()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        try:
            if event.type() in (QEvent.Type.Show, QEvent.Type.Resize):
                self._schedule()
        except RuntimeError:
            pass  # plugin closing
        return False

    def _schedule(self, *_args) -> None:
        if not self._pending:
            self._pending = True
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(0, self.fit)

    def fit(self) -> None:
        self._pending = False
        group = self._group
        try:
            if group.isCollapsed():
                if not self._collapsed:
                    self._expanded_min = group.minimumHeight()
                    self._collapsed = True
                elif group.minimumHeight() != BAND:
                    self._expanded_min = group.minimumHeight()  # set while collapsed (profile change)
                if group.minimumHeight() != BAND or group.maximumHeight() != BAND:
                    group.setMinimumHeight(BAND)
                    group.setMaximumHeight(BAND)
            else:
                if self._collapsed:
                    group.setMinimumHeight(self._expanded_min)
                    self._collapsed = False
                if group.maximumHeight() == BAND:
                    group.setMaximumHeight(QWIDGETSIZE_MAX)
        except RuntimeError:
            pass  # group deleted


COLLAPSE_BUTTON_HEIGHT = BAND - 2  # inside the borders: arrow and title centred in the band


def fit_group(group: Any) -> None:
    """A group of EXPLORING or of a raster / point cloud panel on the spacing scale.

    The stylesheet padding gives the title band and the inset; the layout adds
    nothing but the gap between widgets. Safe to call more than once.
    """
    if group is None:
        return
    layout = group.layout()
    _set_layout(layout, (0, 0, 0, 0), GAP)
    if layout is not None:
        for row in _row_layouts(layout):
            row.setSpacing(GAP)
    # QGIS places the title from the collapse button height (its own stylesheet, written at the
    # first show): 38 px buttons in EXPLORING, 16 px in the panels, so titles sat 10 px apart.
    from qgis.PyQt.QtWidgets import QAbstractButton
    for button in group.findChildren(QAbstractButton):
        if button.parentWidget() is group and (button.objectName() == 'collapseButton'
                                               or type(button).__name__ == 'QgsGroupBoxCollapseButton'):
            button.setFixedHeight(COLLAPSE_BUTTON_HEIGHT)
    if hasattr(group, 'collapsedStateChanged') and getattr(group, '_fm_band', None) is None:
        group._fm_band = _CollapsedBand(group)
    # A layout centres a widget in a taller cell: top-aligned, the gaps stay one GAP.
    parent = group.parentWidget()
    holder = _layout_holding(parent.layout(), group) if parent is not None else None
    if holder is not None:
        from qgis.PyQt.QtCore import Qt
        holder.setAlignment(group, Qt.AlignmentFlag.AlignTop)


def _layout_holding(layout: Any, widget: Any):
    """The layout (``layout`` or one of its sub-layouts) that holds ``widget`` directly."""
    if layout is None:
        return None
    if layout.indexOf(widget) >= 0:
        return layout
    for child in _row_layouts(layout):
        if child.indexOf(widget) >= 0:
            return child
    return None


def fit_panel(panel: Any) -> None:
    """Raster / point cloud EXPLORING panel on the spacing scale (built lazily, after harmonize)."""
    if panel is None or panel.layout() is None:
        return
    from qgis.PyQt.QtWidgets import QGroupBox
    _set_layout(panel.layout(), (0, 0, 0, 0), GAP)
    for row in _row_layouts(panel.layout()):
        row.setSpacing(GAP)
    for group in panel.findChildren(QGroupBox):
        fit_group(group)


def _crs_row_gap(dw: Any) -> None:
    """The CRS combo and its picker button one gap apart (the button is sized in mockup.qss)."""
    widget = getattr(dw, 'mQgsProjectionSelectionWidget_exporting_projection', None)
    layout = widget.layout() if widget is not None else None
    if layout is None:
        return
    layout.setSpacing(GAP)
    for index in reversed(range(layout.count())):
        if layout.itemAt(index).spacerItem() is not None:
            layout.takeAt(index)  # QGIS puts 3 px between them, on top of the spacing


def harmonize_spacing(dw: Any) -> bool:
    """One spacing scale for the whole dock (see the module docstring); field heights are in mockup.qss.

    Run after the dimension and spacing managers (end of ``apply_dynamic_dimensions``),
    which set their own per-layout values.
    """
    from qgis.PyQt.QtWidgets import QBoxLayout, QGroupBox
    side = EDGE - DOCK_MARGIN
    # Header: badges one block under the dock title, right edge on the dock edge.
    header = getattr(dw, 'frame_header', None)
    if header is not None:
        _set_layout(header.layout(), (side, BLOCK, side, 0))
        header.setFixedHeight(HEADER_HEIGHT)
    splitter = getattr(dw, 'splitter_main', None)
    if splitter is not None:
        # EXPLORING -> FILTERING header, one block. The handle is handleWidth plus what the
        # stylesheets add around it (it came out 12 px, then 14): the width is lowered until
        # the handle measures one block. The splitter manager's sheet is replaced.
        # The handle shows a short centred grip (a bar of the dock width hugged the selection
        # strip and the header on hover, and nothing showed at rest); this sheet beats the
        # dock-wide handle colours of default.qss / mockup.qss.
        splitter.setStyleSheet(_SPLITTER_SHEET.format(grip=_style_file('splitter_grip.svg'),
                                                      hover=_style_file('splitter_grip_hover.svg')))
        handle = splitter.handle(1) if splitter.count() > 1 else None
        for width in range(BLOCK, 1, -1):
            splitter.setHandleWidth(width)
            if handle is None or handle.sizeHint().height() <= BLOCK:
                break
        else:
            splitter.setHandleWidth(BLOCK)  # could not be measured: keep a handle one can grab
    # EXPLORING: rail on the dock edge, groups one gap beside it, no stacked margins.
    _set_layout(getattr(dw, 'verticalLayout_main_content', None), (0, 0, 0, 0), GAP)
    if getattr(dw, '_fm_rail_spreader', None) is not None:
        dw._fm_rail_spreader.reset()
    _set_layout(getattr(dw, 'horizontalLayout_exploring_rail_and_groups', None), (RAIL_LEFT_INSET, 0, 0, 0), RAIL_GAP)
    # A small right margin, like a default Qt layout, between the widgets and the scroll bar,
    # and one gap under the last widget so a scrolled panel does not end flush on the edge.
    _set_layout(getattr(dw, 'gridLayout_main_header', None), (0, 0, SCROLLBAR_MARGIN, GAP))
    _set_layout(getattr(dw, 'gridLayout_main_actions', None), (0, 0, 0, 0))
    _set_layout(getattr(dw, 'verticalLayout_exploring_tabs_content', None), (0, 0, 0, 0), GROUP_GAP)
    for name in ('mGroupBox_exploring_single_selection', 'mGroupBox_exploring_multiple_selection',
                 'mGroupBox_exploring_custom_selection'):
        fit_group(getattr(dw, name, None))
    frame = getattr(dw, 'frame_exploring', None)
    if frame is not None:
        for group in frame.findChildren(QGroupBox):
            fit_group(group)  # raster / point cloud panels already built
    stack = getattr(dw, 'stackedWidget_exploring_coverage', None)
    if stack is not None:
        _set_layout(stack.layout(), (0, 0, 0, 0))
    # FILTERING / EXPORTING: rail on the section edge, widgets one gap beside it, rows one gap apart.
    for section in ('filtering', 'exporting'):
        _set_layout(getattr(dw, f'horizontalLayout_{section}_main', None), (0, 0, SCROLLBAR_MARGIN, 0), 0)
        _set_layout(getattr(dw, f'horizontalLayout_{section}_content', None), (0, 0, 0, 0), RAIL_GAP)
        values = getattr(dw, f'verticalLayout_{section}_values', None)
        if values is None:
            continue
        values.setSpacing(ROW_GAP)
        for row in _row_layouts(values):
            if isinstance(row, QBoxLayout) and row.direction() in (QBoxLayout.Direction.LeftToRight,
                                                                   QBoxLayout.Direction.RightToLeft):
                row.setSpacing(FIELD_GAP)
    configuration = getattr(dw, 'CONFIGURATION', None)
    if configuration is not None and configuration.layout() is not None:
        m = configuration.layout().contentsMargins()
        configuration.layout().setContentsMargins(m.left(), m.top(), SCROLLBAR_MARGIN, m.bottom())
    _crs_row_gap(dw)
    for aligner in ('_fm_aligner_filtering', '_fm_aligner_exporting'):
        if getattr(dw, aligner, None) is not None:
            getattr(dw, aligner).schedule()  # geometry is stale until the layouts have run
    return True


def even_exploring_groups(dw: Any) -> bool:
    """Spacers between two EXPLORING groups go: the layout spacing alone separates them."""
    layout = getattr(dw, 'verticalLayout_exploring_tabs_content', None)
    if layout is None:
        return False
    for index in reversed(range(1, layout.count() - 1)):
        before, item, after = layout.itemAt(index - 1), layout.itemAt(index), layout.itemAt(index + 1)
        if item.spacerItem() is not None and before.widget() is not None and after.widget() is not None:
            layout.takeAt(index)
    # Groups at their natural height, the final spacer takes the rest: equal gaps between them.
    from qgis.PyQt.QtWidgets import QSizePolicy
    for name in ('mGroupBox_exploring_single_selection', 'mGroupBox_exploring_multiple_selection',
                 'mGroupBox_exploring_custom_selection'):
        group = getattr(dw, name, None)
        if group is not None:
            group.setSizePolicy(group.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Maximum)
    if not layout.property('fm_stretched'):
        layout.addStretch(1)  # without an expanding item, the surplus would widen every gap
        layout.setProperty('fm_stretched', True)
    let_list_group_grow(dw)
    return True


def list_group_stretch(expanded: bool) -> tuple:
    """``(group stretch, final spacer stretch)``: the expanded multiple selection takes the free height."""
    return (1, 0) if expanded else (0, 1)


class _ListGroupGrowth(QObject if QObject is not None else object):
    """Follows the multiple selection group: expanded, it takes the free height of EXPLORING.

    Event filter (Show / Resize / LayoutRequest), not ``collapsedStateChanged``: the dock
    disconnects every slot of that signal when it rewires the groups.
    """

    def __init__(self, group: Any, layout: Any) -> None:
        super().__init__(group)
        self._group, self._layout = group, layout
        self._expanded = None
        group.installEventFilter(self)
        self.apply()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if event.type() in (QEvent.Type.Show, QEvent.Type.Hide, QEvent.Type.Resize, QEvent.Type.LayoutRequest):
            self.apply()
        return False

    def apply(self) -> None:
        try:
            group, layout = self._group, self._layout
            collapsed = group.isCollapsed() if hasattr(group, 'isCollapsed') else False
            expanded = not collapsed and not group.isHidden()
            if expanded == self._expanded:
                return
            self._expanded = expanded
            from qgis.PyQt.QtWidgets import QSizePolicy
            policy = QSizePolicy.Policy.MinimumExpanding if expanded else QSizePolicy.Policy.Maximum
            group.setSizePolicy(group.sizePolicy().horizontalPolicy(), policy)
            group_stretch, end_stretch = list_group_stretch(expanded)
            layout.setStretch(layout.indexOf(group), group_stretch)
            last = layout.count() - 1
            if last >= 0 and layout.itemAt(last).spacerItem() is not None:
                layout.setStretch(last, end_stretch)
        except RuntimeError:
            pass  # deleted (plugin closing)


def let_list_group_grow(dw: Any) -> bool:
    """The multiple selection group, when expanded, grows with EXPLORING (its feature list can use it).

    The other groups keep their natural height (an empty band otherwise); the final spacer
    takes the free height when the multiple selection is collapsed.
    """
    layout = getattr(dw, 'verticalLayout_exploring_tabs_content', None)
    group = getattr(dw, 'mGroupBox_exploring_multiple_selection', None)
    if layout is None or group is None or layout.indexOf(group) < 0 or dw.property('fm_list_group_grows'):
        return False
    dw._fm_list_group_growth = _ListGroupGrowth(group, layout)
    dw.setProperty('fm_list_group_grows', True)
    return True


def apply_mockup_layout(dw: Any) -> None:
    """Every layout change of the design; each one is skipped on its own if the form differs."""
    for change in (merge_buffer_rows, pack_exploring_rail, size_section_tabs, rail_outside_scroll,
                   tighten_vertical_rhythm, align_key_columns, even_exploring_groups):
        try:
            change(dw)
        except Exception as exc:
            logger.warning(f"mockup layout change {change.__name__} skipped: {exc}")

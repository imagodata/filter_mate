from qgis.PyQt import QtWidgets, QtCore, QtGui

from .datatypes import DataType, TypeRole


# Type badge colors (used for the small colored dot next to keys)
TYPE_BADGE_COLORS = {
    'DictType': QtGui.QColor("#61AFEF"),      # Blue
    'ListType': QtGui.QColor("#E5C07B"),      # Yellow
    'StrType': QtGui.QColor("#98C379"),        # Green
    'ColorType': QtGui.QColor("#98C379"),      # Green
    'IntType': QtGui.QColor("#D19A66"),        # Orange
    'FloatType': QtGui.QColor("#D19A66"),      # Orange
    'BoolType': QtGui.QColor("#E06C75"),       # Red
    'NoneType': QtGui.QColor("#5C6370"),       # Gray
    'UrlType': QtGui.QColor("#56B6C2"),        # Cyan
    'FilepathType': QtGui.QColor("#56B6C2"),   # Cyan
    'FilepathTypeImages': QtGui.QColor("#56B6C2"),
    'RangeType': QtGui.QColor("#C678DD"),      # Purple
    'ChoicesType': QtGui.QColor("#C678DD"),     # Purple
    'ConfigValueType': QtGui.QColor("#98C379"), # Green
}

# Monospace font family (cross-platform)
MONOSPACE_FAMILY = "Consolas, 'Source Code Pro', 'DejaVu Sans Mono', monospace"


class JsonDelegate(QtWidgets.QStyledItemDelegate):
    """Enhanced delegate with type badges, styled fonts, and improved rendering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._monospace_font = None
        self._bold_font = None
        self._italic_font = None

    def _get_monospace_font(self, base_font):
        """Get a monospace font based on the base font size."""
        if self._monospace_font is None or self._monospace_font.pointSize() != base_font.pointSize():
            self._monospace_font = QtGui.QFont("Consolas", base_font.pointSize())
            self._monospace_font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        return self._monospace_font

    def _get_bold_font(self, base_font):
        """Get a bold font."""
        if self._bold_font is None or self._bold_font.pointSize() != base_font.pointSize():
            self._bold_font = QtGui.QFont(base_font)
            self._bold_font.setBold(True)
        return self._bold_font

    def _get_italic_font(self, base_font):
        """Get an italic font."""
        if self._italic_font is None or self._italic_font.pointSize() != base_font.pointSize():
            self._italic_font = QtGui.QFont(base_font)
            self._italic_font.setItalic(True)
        return self._italic_font

    def sizeHint(self, option, index):
        """Slightly taller rows for better readability."""
        return QtCore.QSize(option.rect.width(), 28)

    def paint(self, painter, option, index):
        """Enhanced painting with type badges and styled text."""
        # Let custom DataType paint handle value column if implemented
        if index.column() == 1:
            type_ = index.data(TypeRole)
            if isinstance(type_, DataType):
                try:
                    return type_.paint(painter, option, index)
                except NotImplementedError:
                    pass
            # Enhanced value column painting
            return self._paint_value(painter, option, index)

        # Key column (column 0) - add type badge
        return self._paint_key(painter, option, index)

    def _paint_key(self, painter, option, index):
        """Paint key column with type badge and styled font."""
        painter.save()

        # Draw selection/hover background
        self._draw_item_background(painter, option)

        type_ = index.data(TypeRole)
        type_name = type_.__class__.__name__ if type_ else ''
        is_container = type_name in ('DictType', 'ListType')

        rect = option.rect
        x_offset = rect.left() + 4

        # Draw type badge (colored dot)
        badge_color = TYPE_BADGE_COLORS.get(type_name, QtGui.QColor("#888888"))
        badge_radius = 4
        badge_y = rect.center().y()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(badge_color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QPointF(x_offset + badge_radius, badge_y), badge_radius, badge_radius)
        x_offset += badge_radius * 2 + 6

        # Set font: bold for containers, regular for leaves
        base_font = option.font
        if is_container:
            painter.setFont(self._get_bold_font(base_font))
        else:
            painter.setFont(base_font)

        # Set text color
        if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.color(QtGui.QPalette.ColorRole.HighlightedText))
        else:
            fg = index.data(QtCore.Qt.ItemDataRole.ForegroundRole)
            if fg and isinstance(fg, QtGui.QBrush):
                painter.setPen(fg.color())
            else:
                painter.setPen(option.palette.color(QtGui.QPalette.ColorRole.Text))

        # Draw key text
        key_text = index.data(QtCore.Qt.ItemDataRole.DisplayRole) or ''
        text_rect = QtCore.QRect(x_offset, rect.top(), rect.width() - x_offset + rect.left() - 4, rect.height())

        # For containers, append child count
        if is_container:
            source_item = self._get_source_item(index)
            if source_item and source_item.rowCount() > 0:
                count = source_item.rowCount()
                suffix = f"  ({count})" if type_name == 'DictType' else f"  [{count}]"
                # Draw key text
                fm = painter.fontMetrics()
                key_width = fm.horizontalAdvance(str(key_text))
                painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft, str(key_text))

                # Draw count in lighter color
                count_rect = QtCore.QRect(x_offset + key_width, rect.top(), rect.width() - x_offset - key_width, rect.height())
                count_color = painter.pen().color()
                count_color.setAlpha(120)
                painter.setPen(count_color)
                painter.setFont(self._get_italic_font(base_font))
                painter.drawText(count_rect, QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft, suffix)
                painter.restore()
                return

        painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft, str(key_text))
        painter.restore()

    def _paint_value(self, painter, option, index):
        """Paint value column with monospace font, styled None/Bool, right-aligned numbers."""
        painter.save()

        # Draw selection/hover background
        self._draw_item_background(painter, option)

        type_ = index.data(TypeRole)
        type_name = type_.__class__.__name__ if type_ else ''
        display = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        rect = option.rect.adjusted(6, 0, -4, 0)

        # Set text color
        if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.color(QtGui.QPalette.ColorRole.HighlightedText))
        else:
            fg = index.data(QtCore.Qt.ItemDataRole.ForegroundRole)
            if fg and isinstance(fg, QtGui.QBrush):
                painter.setPen(fg.color())
            else:
                painter.setPen(option.palette.color(QtGui.QPalette.ColorRole.Text))

        base_font = option.font
        alignment = QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft

        if type_name == 'NoneType':
            # Italic + dimmed for None
            painter.setFont(self._get_italic_font(base_font))
            color = painter.pen().color()
            color.setAlpha(140)
            painter.setPen(color)
            painter.drawText(rect, alignment, "null")

        elif type_name in ('IntType', 'FloatType'):
            # Monospace + right-aligned for numbers
            painter.setFont(self._get_monospace_font(base_font))
            alignment = QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight
            painter.drawText(rect, alignment, str(display) if display is not None else '')

        elif type_name == 'BoolType':
            # Bool already has checkbox; draw nothing extra (checkbox handled by Qt)
            pass

        elif type_name == 'StrType':
            # Monospace for string values
            painter.setFont(self._get_monospace_font(base_font))
            text = str(display) if display is not None else ''
            # Elide if too long
            fm = painter.fontMetrics()
            elided = fm.elidedText(text, QtCore.Qt.TextElideMode.ElideRight, rect.width())
            painter.drawText(rect, alignment, elided)

        elif type_name in ('DictType', 'ListType'):
            # Containers show nothing in value column (empty)
            pass

        else:
            # Default: monospace rendering
            painter.setFont(self._get_monospace_font(base_font))
            text = str(display) if display is not None else ''
            fm = painter.fontMetrics()
            elided = fm.elidedText(text, QtCore.Qt.TextElideMode.ElideRight, rect.width())
            painter.drawText(rect, alignment, elided)

        painter.restore()

    def _draw_item_background(self, painter, option):
        """Draw the standard item background (selection, hover, alternating)."""
        style = QtWidgets.QApplication.style()
        style.drawPrimitive(QtWidgets.QStyle.PrimitiveElement.PE_PanelItemViewItem, option, painter)

    def _get_source_item(self, index):
        """Get the QStandardItem from an index, handling proxy models."""
        model = index.model()
        if hasattr(model, 'sourceModel'):
            # Proxy model - map to source
            source_index = model.mapToSource(index)
            return model.sourceModel().itemFromIndex(source_index)
        if hasattr(model, 'itemFromIndex'):
            return model.itemFromIndex(index)
        return None

    def createEditor(self, parent, option, index):
        """Use method from the data type or fall back to the default."""
        if index.column() == 0:
            return super().createEditor(parent, option, index)
        try:
            return index.data(TypeRole).createEditor(parent, option, index)
        except NotImplementedError:
            return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        """Use method from the data type or fall back to the default."""
        if index.column() == 0:
            return super().setEditorData(editor, index)
        try:
            type_ = index.data(TypeRole)
            if hasattr(type_, 'setEditorData'):
                return type_.setEditorData(editor, index)
        except (NotImplementedError, AttributeError):
            pass
        return super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        """Use method from the data type or fall back to the default."""
        if index.column() == 0:
            return super().setModelData(editor, model, index)
        try:
            type_ = index.data(TypeRole)
            if hasattr(type_, 'setModelData'):
                result = type_.setModelData(editor, model, index)
                model.dataChanged.emit(index, index)
                return result
        except (NotImplementedError, AttributeError):
            pass
        result = super().setModelData(editor, model, index)
        model.dataChanged.emit(index, index)
        return result

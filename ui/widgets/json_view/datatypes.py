from functools import partial
import re
import webbrowser
import os
from shutil import copyfile

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtCore import QCoreApplication
from qgis.gui import QgsColorButton
from . import themes


TypeRole = QtCore.Qt.ItemDataRole.UserRole + 1
HiddenDataRole = QtCore.Qt.ItemDataRole.UserRole + 10
PLUGIN_DIR = ''


class DataType(object):
    """Base class for data types."""
    COLOR = QtCore.Qt.GlobalColor.black
    THEME_COLOR_KEY = 'string'  # Default theme color key

    def get_color(self):
        """Get the color for this data type from the current theme."""
        return themes.get_current_theme().get_color(self.THEME_COLOR_KEY)

    def matches(self, data):
        """Logic to define whether the given data matches this type."""
        raise NotImplementedError

    def next(self, model, data, parent):
        """Implement if this data type has to add child items to itself."""

    def actions(self, index):
        """Re-implement to return custom QActions."""

        return ["Rename", "Add child", "Insert sibling up", "Insert sibling down", "Remove"]

    def paint(self, painter, option, index):
        """Optionally re-implement for use by the delegate."""
        raise NotImplementedError

    def createEditor(self, parent, option, index):
        """Optionally re-implement for use by the delegate."""
        raise NotImplementedError

    def setModelData(self, editor, model, index):
        """Optionally re-implement for use by the delegate."""
        raise NotImplementedError

    def serialize(self, model, item, data, parent):
        """Serialize this data type."""
        value_item = parent.child(item.row(), 1)
        value = value_item.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if isinstance(data, dict):
            key_item = parent.child(item.row(), 0)
            key = key_item.data(QtCore.Qt.ItemDataRole.DisplayRole)
            data[key] = value
        elif isinstance(data, list):
            data.append(value)

    def key_item(self, key, model, datatype=None, editable=True):
        """Create an item for the key column for this data type."""
        key_item = QtGui.QStandardItem(key)
        key_item.setData(datatype, TypeRole)
        key_item.setData(datatype.__class__.__name__, QtCore.Qt.ItemDataRole.ToolTipRole)
        key_item.setData(
            QtGui.QBrush(self.get_color()), QtCore.Qt.ForegroundRole)
        key_item.setFlags(
            QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
        if editable and model.editable_keys:
            key_item.setFlags(key_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        return key_item

    def value_item(self, value, model, key=None):
        """Create an item for the value column for this data type."""
        display_value = value
        item = QtGui.QStandardItem(display_value)
        item.setData(display_value, QtCore.Qt.ItemDataRole.DisplayRole)
        item.setData(value, QtCore.Qt.ItemDataRole.UserRole)
        item.setData(self, TypeRole)
        item.setData(QtGui.QBrush(self.get_color()), QtCore.Qt.ForegroundRole)
        item.setFlags(
            QtCore.Qt.ItemFlag.ItemIsSelectable |
            QtCore.Qt.ItemFlag.ItemIsEnabled)
        if model.editable_values:
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        return item


# -----------------------------------------------------------------------------
# Default Types
# -----------------------------------------------------------------------------


class NoneType(DataType):
    """None"""
    THEME_COLOR_KEY = 'none'

    def matches(self, data):
        return data is None

    def value_item(self, value, model, key=None):
        item = super(NoneType, self).value_item(value, model, key)
        item.setData('None', QtCore.Qt.ItemDataRole.DisplayRole)
        return item

    def serialize(self, model, item, data, parent):
        value_item = parent.child(item.row(), 1)
        value = value_item.data(QtCore.Qt.ItemDataRole.DisplayRole)
        value = value if value != 'None' else None
        if isinstance(data, dict):
            key_item = parent.child(item.row(), 0)
            key = key_item.data(QtCore.Qt.ItemDataRole.DisplayRole)
            data[key] = value
        elif isinstance(data, list):
            data.append(value)


class StrType(DataType):
    """Strings and unicodes"""

    def matches(self, data):
        return isinstance(data, str) or isinstance(data, unicode)  # noqa: F821


class ColorType(DataType):
    """Hex color strings displayed with QgsColorButton."""
    THEME_COLOR_KEY = 'string'

    # Pattern to match hex colors: #RGB, #RRGGBB, #RRGGBBAA
    HEX_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?([0-9A-Fa-f]{2})?$')

    def matches(self, data):
        """Check if data is a hex color string."""
        if not isinstance(data, str):
            return False
        return bool(self.HEX_COLOR_PATTERN.match(data))

    def createEditor(self, parent, option, index):
        """Create a QgsColorButton editor for color selection."""
        color_button = QgsColorButton(parent)
        color_button.setAllowOpacity(True)
        color_button.setShowNoColor(False)
        color_button.setMinimumSize(30, 22)
        color_button.setMaximumHeight(30)

        # Set initial color from current value
        current_color = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if current_color:
            qcolor = QtGui.QColor(current_color)
            if qcolor.isValid():
                color_button.setColor(qcolor)

        # Connect signal to update immediately on color change
        color_button.colorChanged.connect(
            lambda: self.setModelData(color_button, index.model(), index)
        )

        return color_button

    def setEditorData(self, editor, index):
        """Set the editor data from the model."""
        if isinstance(editor, QgsColorButton):
            color_str = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
            if color_str:
                qcolor = QtGui.QColor(color_str)
                if qcolor.isValid():
                    editor.setColor(qcolor)

    def setModelData(self, editor, model, index):
        """Update model with selected color from QgsColorButton."""
        if isinstance(editor, QgsColorButton):
            color = editor.color()
            # Format color as hex string with alpha if present
            if color.alpha() < 255:
                hex_color = color.name(QtGui.QColor.HexArgb)
            else:
                hex_color = color.name(QtGui.QColor.HexRgb)

            model.setData(index, hex_color, QtCore.Qt.ItemDataRole.EditRole)

    def paint(self, painter, option, index):
        """Paint a color preview rectangle next to the color value."""
        painter.save()

        # Get color value
        color_str = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        qcolor = QtGui.QColor(color_str)

        if qcolor.isValid():
            # Draw color rectangle
            rect = option.rect
            color_rect = QtCore.QRect(
                rect.left() + 2,
                rect.top() + 2,
                20,
                rect.height() - 4
            )
            painter.fillRect(color_rect, qcolor)
            painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black, 1))
            painter.drawRect(color_rect)

            # Draw text after color rectangle
            text_rect = QtCore.QRect(
                color_rect.right() + 5,
                rect.top(),
                rect.width() - color_rect.width() - 7,
                rect.height()
            )
            painter.setPen(self.get_color())
            painter.drawText(
                text_rect,
                QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
                color_str
            )
        else:
            # Fallback to default painting if color is invalid
            painter.setPen(self.get_color())
            painter.drawText(
                option.rect,
                QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
                " " + color_str
            )

        painter.restore()


class IntType(DataType):
    """Integers"""
    THEME_COLOR_KEY = 'integer'

    def matches(self, data):
        return isinstance(data, int) and not isinstance(data, bool)


class FloatType(DataType):
    """Floats"""
    THEME_COLOR_KEY = 'float'

    def matches(self, data):
        return isinstance(data, float)


class BoolType(DataType):
    """Bools are displayed as checkable items with a check box."""
    THEME_COLOR_KEY = 'boolean'

    def matches(self, data):
        return isinstance(data, bool)

    def value_item(self, value, model, key=None):
        item = super(BoolType, self).value_item(value, model, key)
        item.setCheckState(QtCore.Qt.CheckState.Checked if value else QtCore.Qt.CheckState.Unchecked)
        item.setData('', QtCore.Qt.ItemDataRole.DisplayRole)
        if model.editable_values:
            item.setFlags(
                item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable |
                QtCore.Qt.ItemFlag.ItemIsUserCheckable)
        return item

    def serialize(self, model, item, data, parent):
        value_item = parent.child(item.row(), 1)
        value = value_item.checkState() == QtCore.Qt.CheckState.Checked
        if isinstance(data, dict):
            key_item = parent.child(item.row(), 0)
            key = key_item.data(QtCore.Qt.ItemDataRole.DisplayRole)
            data[key] = value
        elif isinstance(data, list):
            data.append(value)


class ListType(DataType):
    """Lists"""
    THEME_COLOR_KEY = 'list'

    def matches(self, data):
        return isinstance(data, list)

    def next(self, model, data, parent):
        for i, value in enumerate(data):
            type_ = match_type(value)
            key_item = self.key_item(
                str(i), datatype=type_, editable=False, model=model)
            value_item = type_.value_item(value, model=model, key=str(i))
            parent.appendRow([key_item, value_item])
            type_.next(model, data=value, parent=key_item)

    def value_item(self, value, model, key):
        item = QtGui.QStandardItem()
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
        return item

    def serialize(self, model, item, data, parent):
        key_item = parent.child(item.row(), 0)
        if key_item:
            if isinstance(data, dict):
                key = key_item.data(QtCore.Qt.ItemDataRole.DisplayRole)
                data[key] = []
                data = data[key]
            elif isinstance(data, list):
                new_data = []
                data.append(new_data)
                data = new_data
        for row in range(item.rowCount()):
            child_item = item.child(row, 0)
            type_ = child_item.data(TypeRole)
            type_.serialize(
                model=self, item=child_item, data=data, parent=item)


class DictType(DataType):
    """Dictionaries"""
    THEME_COLOR_KEY = 'dict'

    # Keys that are config metadata, not user data — always hidden from tree
    _META_KEYS = {'_hidden', '_display_name', '_CONFIG_VERSION'}

    def matches(self, data):
        return isinstance(data, dict)

    def _is_hidden(self, key, value):
        """Check if a key/value pair should be hidden from the config tree."""
        # Skip metadata keys (start with _)
        if isinstance(key, str) and key.startswith('_'):
            return True
        # Skip dicts that have explicit _hidden flag
        if isinstance(value, dict) and value.get('_hidden') is True:
            return True
        return False

    def next(self, model, data, parent):
        # Collect hidden entries to preserve during serialization
        hidden_data = {}
        for key, value in data.items():
            if self._is_hidden(key, value):
                hidden_data[key] = value
                continue
            type_ = match_type(value)
            # Use _display_name from child dict if available
            display_key = key
            if isinstance(value, dict) and '_display_name' in value:
                display_key = value['_display_name']
            key_item = self.key_item(display_key, datatype=type_, model=model)
            # Store the original JSON key so serialize() can reconstruct it
            if display_key != key:
                key_item.setData(key, QtCore.Qt.ItemDataRole.UserRole)
            value_item = type_.value_item(value, model, key)
            parent.appendRow([key_item, value_item])
            type_.next(model, data=value, parent=key_item)

        # Store hidden data on the parent's value item (column 1) for roundtrip.
        # Deep-sanitize to strip non-JSON objects (e.g. psycopg2.connection
        # stored at runtime in CURRENT_PROJECT.OPTIONS.ACTIVE_POSTGRESQL).
        if hidden_data:
            clean = self._deep_sanitize(hidden_data)
            value_sibling = parent.parent().child(parent.row(), 1) if parent.parent() else None
            if value_sibling is None:
                # Root level — store on invisible root via model attribute
                if not hasattr(model, '_hidden_data'):
                    model._hidden_data = {}
                model._hidden_data.update(clean)
            else:
                existing = value_sibling.data(HiddenDataRole) or {}
                existing.update(clean)
                value_sibling.setData(existing, HiddenDataRole)

    def value_item(self, value, model, key):
        item = QtGui.QStandardItem()
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
        return item

    def serialize(self, model, item, data, parent):
        key_item = parent.child(item.row(), 0)
        if key_item:
            if isinstance(data, dict):
                # Use original JSON key if stored, otherwise display text
                original_key = key_item.data(QtCore.Qt.ItemDataRole.UserRole)
                key = original_key if original_key else key_item.data(QtCore.Qt.ItemDataRole.DisplayRole)
                data[key] = {}
                data = data[key]
            elif isinstance(data, list):
                new_data = {}
                data.append(new_data)
                data = new_data

        # Re-inject hidden data that was stripped from the tree
        value_item = parent.child(item.row(), 1) if key_item else None
        if value_item:
            hidden = value_item.data(HiddenDataRole)
            if isinstance(hidden, dict):
                self._merge_json_safe(data, hidden)

        for row in range(item.rowCount()):
            child_item = item.child(row, 0)
            type_ = child_item.data(TypeRole)
            type_.serialize(model=self, item=child_item, data=data, parent=item)

        # Re-inject root-level hidden data
        if parent == getattr(model, 'invisibleRootItem', lambda: None)():
            root_hidden = getattr(model, '_hidden_data', None)
            if isinstance(root_hidden, dict):
                self._merge_json_safe(data, root_hidden)

    @staticmethod
    def _deep_sanitize(obj):
        """Recursively strip non-JSON-serializable values from a data structure."""
        if isinstance(obj, dict):
            return {
                k: DictType._deep_sanitize(v)
                for k, v in obj.items()
                if isinstance(v, (dict, list, str, int, float, bool, type(None)))
            }
        if isinstance(obj, list):
            return [
                DictType._deep_sanitize(v)
                for v in obj
                if isinstance(v, (dict, list, str, int, float, bool, type(None)))
            ]
        return obj

    @staticmethod
    def _merge_json_safe(target, source):
        """Merge source into target, skipping non-JSON-serializable values."""
        for k, v in source.items():
            if isinstance(v, (dict, list, str, int, float, bool, type(None))):
                target[k] = DictType._deep_sanitize(v)


# -----------------------------------------------------------------------------
# Derived Types
# -----------------------------------------------------------------------------


class RangeType(DataType):
    """A range, shown as three spinboxes next to each other.

    A range is defined as a dict with start, end and step keys.
    It supports both floats and ints.
    """
    THEME_COLOR_KEY = 'range'
    KEYS = ['start', 'end', 'step']

    def matches(self, data):
        if isinstance(data, dict) and len(data) == 3:
            if all([True if k in self.KEYS else False for k in data.keys()]):
                return True
        return False

    def paint(self, painter, option, index):
        data = index.data(QtCore.Qt.ItemDataRole.UserRole)

        painter.save()

        painter.setPen(QtGui.QPen(index.data(QtCore.Qt.ForegroundRole).color()))
        metrics = painter.fontMetrics()
        spinbox_option = QtWidgets.QStyleOptionSpinBox()
        start_rect = QtCore.QRect(option.rect)
        start_rect.setWidth(start_rect.width() / 3.0)
        spinbox_option.rect = start_rect
        spinbox_option.frame = True
        spinbox_option.state = option.state
        spinbox_option.buttonSymbols = QtWidgets.QAbstractSpinBox.NoButtons
        for i, key in enumerate(self.KEYS):
            if i > 0:
                spinbox_option.rect.adjust(
                    spinbox_option.rect.width(), 0,
                    spinbox_option.rect.width(), 0)
            QtWidgets.QApplication.style().drawComplexControl(
                QtWidgets.QStyle.CC_SpinBox, spinbox_option, painter)
            value = str(data[key])
            value_rect = QtCore.QRectF(
                spinbox_option.rect.adjusted(6, 1, -2, -2))
            value = metrics.elidedText(
                value, QtCore.Qt.TextElideMode.ElideRight, value_rect.width() - 20)
            painter.drawText(value_rect, value)

        painter.restore()

    def createEditor(self, parent, option, index):
        data = index.data(QtCore.Qt.ItemDataRole.UserRole)
        wid = QtWidgets.QWidget(parent)
        wid.setLayout(QtWidgets.QHBoxLayout(parent))
        wid.layout().setContentsMargins(0, 0, 0, 0)
        wid.layout().setSpacing(0)

        start = data['start']
        end = data['end']
        step = data['step']

        if isinstance(start, float):
            start_spinbox = QtWidgets.QDoubleSpinBox(wid)
        else:
            start_spinbox = QtWidgets.QSpinBox(wid)

        if isinstance(end, float):
            end_spinbox = QtWidgets.QDoubleSpinBox(wid)
        else:
            end_spinbox = QtWidgets.QSpinBox(wid)

        if isinstance(step, float):
            step_spinbox = QtWidgets.QDoubleSpinBox(wid)
        else:
            step_spinbox = QtWidgets.QSpinBox(wid)

        start_spinbox.setRange(-16777215, 16777215)
        end_spinbox.setRange(-16777215, 16777215)
        step_spinbox.setRange(-16777215, 16777215)
        start_spinbox.setValue(start)
        end_spinbox.setValue(end)
        step_spinbox.setValue(step)
        wid.layout().addWidget(start_spinbox)
        wid.layout().addWidget(end_spinbox)
        wid.layout().addWidget(step_spinbox)
        return wid

    def setModelData(self, editor, model, index):
        # if isinstance(model, QtWidgets.QAbstractProxyModel):
        #    index = model.mapToSource(index)
        #    model = model.sourceModel()
        data = index.data(QtCore.Qt.ItemDataRole.UserRole)
        data['start'] = editor.layout().itemAt(0).widget().value()
        data['end'] = editor.layout().itemAt(1).widget().value()
        data['step'] = editor.layout().itemAt(2).widget().value()
        model.itemFromIndex(index).setData(data, QtCore.Qt.ItemDataRole.UserRole)

    def value_item(self, value, model, key=None):
        """Item representing a value."""
        value_item = super(RangeType, self).value_item(None, model, key)
        value_item.setData(value, QtCore.Qt.ItemDataRole.UserRole)
        return value_item

    def serialize(self, model, item, data, parent):
        value_item = parent.child(item.row(), 1)
        value = value_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            key_item = parent.child(item.row(), 0)
            key = key_item.data(QtCore.Qt.ItemDataRole.DisplayRole)
            data[key] = value
        elif isinstance(data, list):
            data.append(value)


class UrlType(DataType):
    """Provide a link to urls."""
    THEME_COLOR_KEY = 'url'
    REGEX = re.compile(r'(?:https?):\/\/|(?:file):\/\\/')

    def matches(self, data):
        if isinstance(data, str) or isinstance(data, unicode):  # noqa: F821
            if self.REGEX.match(data) is not None:
                return True
        return False

    def actions(self, index):
        explore = QtGui.QAction(
            QCoreApplication.translate("UrlType", "Explore ..."), None)
        explore.triggered.connect(
            partial(webbrowser.open, index.data(QtCore.Qt.ItemDataRole.DisplayRole)))
        return [explore]


class FilepathType(DataType):
    """Files and paths can be opened."""
    THEME_COLOR_KEY = 'filepath'
    POSITIVE_REGEX = re.compile(r'(\/.*)|([A-Za-z]:\\.*)')
    NEGATIVE_REGEX = re.compile(r'(\.png)|(\.jpg)|(\.jpeg)|(\.gif)$')

    def matches(self, data):
        if isinstance(data, str) or isinstance(data, unicode):  # noqa: F821
            if self.POSITIVE_REGEX.search(data) is not None:
                if self.NEGATIVE_REGEX.search(data) is None:
                    return True
        return False

    def value_item(self, value, model, key):
        """Item representing a value."""
        value_item = super(FilepathType, self).value_item(value, model, key)
        if os.path.exists(value):
            if os.path.isdir(value):
                value_item.setData(value, QtCore.Qt.ItemDataRole.DisplayRole)
            elif os.path.isfile(value):
                value_item.setData(os.path.basename(value), QtCore.Qt.ItemDataRole.DisplayRole)
                value_item.setData(os.path.normcase(value), QtCore.Qt.ItemDataRole.UserRole)
        return value_item

    def actions(self, index):
        view = QtGui.QAction(
            QCoreApplication.translate("FilepathType", "View"), None)
        self.change = QtGui.QAction(
            QCoreApplication.translate("FilepathType", "Change"), None)
        path = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        view.triggered.connect(partial(webbrowser.open, path))
        self.change.triggered.connect(partial(self.change_path, path, index))
        return [view, self.change]

    def change_path(self, input_path, index):
        new_path = None
        filename = None
        if os.path.isdir(input_path):
            new_path = os.path.normcase(str(QtWidgets.QFileDialog.getExistingDirectory(
                None,
                QCoreApplication.translate("FilepathType", "Select a folder"),
                input_path)))
        else:
            if os.path.exists(input_path):
                extension = os.path.basename(input_path).split('.')[-1]
                new_path = os.path.normcase(str(QtWidgets.QFileDialog.getOpenFileName(
                    None,
                    QCoreApplication.translate("FilepathType", "Select a file"),
                    input_path,
                    '*.{extension}'.format(extension=extension))[0]))
                filename = os.path.basename(new_path)
            else:
                extension = os.path.basename(input_path).split('.')[-1]
                new_path = os.path.normcase(str(QtWidgets.QFileDialog.getSaveFileName(
                    None,
                    QCoreApplication.translate("FilepathType", "Save to a file"),
                    input_path,
                    '*.{extension}'.format(extension=extension))[0]))
                filename = os.path.basename(new_path)
        if new_path is not None:
            if filename is not None:
                self.change.setData([filename, new_path])
            else:
                self.change.setData([new_path])


class FilepathTypeImages(DataType):
    """Files and paths can be opened."""
    THEME_COLOR_KEY = 'filepath'
    REGEX = re.compile(r'(\.png)|(\.jpg)|(\.jpeg)|(\.gif)$')

    def matches(self, data):
        if isinstance(data, str) or isinstance(data, unicode):  # noqa: F821
            if self.REGEX.search(data) is not None:
                return True
        return False

    def value_item(self, value, model, key):
        """Item representing a value."""
        value_item = super(FilepathTypeImages, self).value_item(value, model, key)
        value_item.setData(value, QtCore.Qt.ItemDataRole.DisplayRole)
        value_item.setData(os.path.normcase(os.path.join(PLUGIN_DIR, "icons", value)), QtCore.Qt.ItemDataRole.UserRole)
        return value_item

    def actions(self, index):
        view = QtGui.QAction(
            QCoreApplication.translate("FilepathTypeImages", "View"), None)
        self.change = QtGui.QAction(
            QCoreApplication.translate("FilepathTypeImages", "Change"), None)
        path_view = index.data(QtCore.Qt.ItemDataRole.UserRole)
        path_change = os.path.normcase(os.path.join(PLUGIN_DIR, "icons"))
        view.triggered.connect(partial(webbrowser.open, path_view))
        self.change.triggered.connect(partial(self.change_icon, path_change, index))
        return [view, self.change]

    def change_icon(self, folder_path, index):
        filepath = os.path.normcase(str(QtWidgets.QFileDialog.getOpenFileName(
            None,
            QCoreApplication.translate("FilepathTypeImages", "Select an icon"),
            folder_path,
            'Images (*.png *.jpg *.jpeg *.gif)')[0]))
        if filepath:
            new_filepath = filepath
            filename = os.path.basename(filepath)
            if filepath.find(folder_path) < 0:
                new_filepath = os.path.join(folder_path, filename)
                copyfile(filepath, new_filepath)
            self.change.setData([filename, new_filepath])


class ChoicesType(DataType):
    """A combobox that allows for a number of choices.

    The data has to be a dict with at least 'value' and 'choices' keys.
    Supports extended format with optional 'description' and other metadata.

    Basic format:
    {
        "value": "A",
        "choices": ["A", "B", "C"]
    }

    Extended format (v2.0 config):
    {
        "value": "auto",
        "choices": ["auto", "compact", "normal"],
        "description": "UI display profile setting",
        "additional_metadata": "any value"
    }
    """
    THEME_COLOR_KEY = 'choices'
    REQUIRED_KEYS = ['value', 'choices']

    def matches(self, data):
        """Match dict with 'value' and 'choices' keys (and optionally more)."""
        if isinstance(data, dict):
            # Must have both 'value' and 'choices' keys
            if all(k in data for k in self.REQUIRED_KEYS):
                # 'choices' must be a list
                if isinstance(data.get('choices'), list):
                    return True
        return False

    def createEditor(self, parent, option, index):
        data = index.data(QtCore.Qt.ItemDataRole.UserRole)
        cbx = QtWidgets.QComboBox(parent)
        # Use display labels when available (e.g. "fr (Français)" instead of "fr")
        labels = data.get('available_translations')
        if labels and len(labels) == len(data['choices']) - 1:
            # available_translations doesn't include 'auto' — prepend it
            display_items = ['auto'] + list(labels)
        elif labels and len(labels) == len(data['choices']):
            display_items = list(labels)
        else:
            display_items = [str(d) for d in data['choices']]
        cbx.addItems(display_items)
        # Find current value by matching against choices (codes)
        try:
            current_idx = list(data['choices']).index(data['value'])
        except ValueError:
            current_idx = 0
        # Block signals during init so setCurrentIndex doesn't trigger commit
        cbx.blockSignals(True)
        cbx.setCurrentIndex(current_idx)
        cbx.blockSignals(False)
        if 'description' in data:
            cbx.setToolTip(str(data['description']))

        # Auto-apply on user selection. Use 'activated' signal — it only fires
        # on actual user interaction (click/Enter), never on programmatic changes
        # (setCurrentIndex, setEditorData, etc.).
        choices_type = self
        captured_index = QtCore.QPersistentModelIndex(index)

        def _on_activated(new_idx):
            if not captured_index.isValid():
                return
            model_idx = QtCore.QModelIndex(captured_index)
            m = model_idx.model()
            if not m or not hasattr(m, 'itemFromIndex'):
                return
            choices_type.setModelData(cbx, m, model_idx)

        cbx.activated.connect(_on_activated)
        return cbx

    def setModelData(self, editor, model, index):
        data = index.data(QtCore.Qt.ItemDataRole.UserRole)
        data['value'] = data['choices'][editor.currentIndex()]
        # Display the label if available, otherwise the raw value
        labels = data.get('available_translations')
        if labels and len(labels) == len(data['choices']) - 1:
            display_items = ['auto'] + list(labels)
        elif labels and len(labels) == len(data['choices']):
            display_items = list(labels)
        else:
            display_items = None
        display_text = display_items[editor.currentIndex()] if display_items else str(data['value'])
        model.itemFromIndex(index).setData(display_text, QtCore.Qt.ItemDataRole.DisplayRole)
        model.itemFromIndex(index).setData(data, QtCore.Qt.ItemDataRole.UserRole)

    def value_item(self, value, model, key=None):
        """Item representing a value with optional tooltip from description."""
        # Show label instead of code when available_translations exists
        display_value = value['value']
        labels = value.get('available_translations')
        choices = value.get('choices', [])
        if labels and display_value in choices:
            idx = choices.index(display_value)
            if len(labels) == len(choices) - 1 and idx > 0:
                display_value = labels[idx - 1]
            elif len(labels) == len(choices):
                display_value = labels[idx]
        value_item = super(ChoicesType, self).value_item(display_value, model, key)
        value_item.setData(value, QtCore.Qt.ItemDataRole.UserRole)
        if 'description' in value:
            value_item.setData(str(value['description']), QtCore.Qt.ItemDataRole.ToolTipRole)
        return value_item

    def serialize(self, model, item, data, parent):
        value_item = parent.child(item.row(), 1)
        value = value_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            key_item = parent.child(item.row(), 0)
            key = key_item.data(QtCore.Qt.ItemDataRole.DisplayRole)
            data[key] = value
        elif isinstance(data, list):
            data.append(value)


class ConfigValueType(DataType):
    """A simple config value with description metadata.

    The data has to be a dict with 'value' key and optionally 'description'.
    This type handles config values that have metadata but no choices.

    Format:
    {
        "value": true,
        "description": "Auto-activate plugin when project loaded"
    }

    Or with additional metadata:
    {
        "value": "path/to/file",
        "description": "Database file path",
        "applies_to": "Plugin initialization"
    }

    NOTE: This type must NOT match if 'choices' key is present -
    those should be handled by ChoicesType.
    """
    THEME_COLOR_KEY = 'string'

    def matches(self, data):
        """Match dict with 'value' key but WITHOUT 'choices' key."""
        if isinstance(data, dict):
            # Must have 'value' key
            if 'value' in data:
                # Must NOT have 'choices' key (that's for ChoicesType)
                if 'choices' not in data:
                    # Should have at least description or other metadata
                    # (otherwise it's just a plain value in a dict)
                    return len(data) >= 2
        return False

    def _auto_commit(self, editor, index):
        """Connect editor signals to auto-commit on value change.

        Calls setModelData directly instead of relying on Qt commit signals.
        """
        config_type = self

        def _commit():
            config_type.setModelData(editor, index.model(), index)

        if isinstance(editor, QtWidgets.QCheckBox):
            editor.stateChanged.connect(lambda: _commit())
        elif isinstance(editor, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            editor.editingFinished.connect(_commit)

    def createEditor(self, parent, option, index):
        """Create appropriate editor based on value type."""
        data = index.data(QtCore.Qt.ItemDataRole.UserRole)
        value = data.get('value')

        if isinstance(value, bool):
            cbx = QtWidgets.QCheckBox(parent)
            cbx.setChecked(value)
            if 'description' in data:
                cbx.setToolTip(str(data['description']))
            self._auto_commit(cbx, index)
            return cbx
        elif isinstance(value, int) and not isinstance(value, bool):
            spinbox = QtWidgets.QSpinBox(parent)
            spinbox.setMinimum(int(data['min']) if 'min' in data else -2147483648)
            spinbox.setMaximum(int(data['max']) if 'max' in data else 2147483647)
            spinbox.setValue(value)
            if 'description' in data:
                spinbox.setToolTip(str(data['description']))
            self._auto_commit(spinbox, index)
            return spinbox
        elif isinstance(value, float):
            spinbox = QtWidgets.QDoubleSpinBox(parent)
            min_val = data.get('min')
            max_val = data.get('max')
            decimals = 6
            for ref in (min_val, max_val, value):
                if ref is not None:
                    s = str(ref)
                    if '.' in s:
                        decimals = max(decimals, len(s.split('.')[1]))
                    break
            spinbox.setDecimals(decimals)
            spinbox.setMinimum(float(min_val) if min_val is not None else -1e10)
            spinbox.setMaximum(float(max_val) if max_val is not None else 1e10)
            spinbox.setValue(value)
            if 'description' in data:
                spinbox.setToolTip(str(data['description']))
            self._auto_commit(spinbox, index)
            return spinbox
        else:
            line_edit = QtWidgets.QLineEdit(parent)
            line_edit.setText(str(value) if value is not None else '')
            if 'description' in data:
                line_edit.setToolTip(str(data['description']))
            return line_edit

    def setModelData(self, editor, model, index):
        """Set model data based on editor type."""
        data = index.data(QtCore.Qt.ItemDataRole.UserRole)
        original_value = data.get('value')

        if isinstance(editor, QtWidgets.QCheckBox):
            new_value = editor.isChecked()
        elif isinstance(editor, QtWidgets.QSpinBox):
            new_value = editor.value()
        elif isinstance(editor, QtWidgets.QDoubleSpinBox):
            new_value = editor.value()
        else:
            # Line edit - try to preserve type
            text = editor.text()
            if isinstance(original_value, bool):
                new_value = text.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(original_value, int) and not isinstance(original_value, bool):
                try:
                    new_value = int(text)
                except ValueError:
                    new_value = text
            elif isinstance(original_value, float):
                try:
                    new_value = float(text)
                except ValueError:
                    new_value = text
            else:
                new_value = text

        data['value'] = new_value
        # Display the value, not the full dict
        display_text = str(new_value)
        if isinstance(new_value, bool):
            display_text = 'true' if new_value else 'false'
        model.itemFromIndex(index).setData(display_text, QtCore.Qt.ItemDataRole.DisplayRole)
        model.itemFromIndex(index).setData(data, QtCore.Qt.ItemDataRole.UserRole)

    def value_item(self, value, model, key=None):
        """Item representing a value with optional tooltip from description."""
        actual_value = value.get('value', value)
        # Convert bool to string for display
        if isinstance(actual_value, bool):
            display_text = 'true' if actual_value else 'false'
        else:
            display_text = str(actual_value) if actual_value is not None else ''

        value_item = QtGui.QStandardItem(display_text)
        value_item.setData(display_text, QtCore.Qt.ItemDataRole.DisplayRole)
        value_item.setData(value, QtCore.Qt.ItemDataRole.UserRole)
        value_item.setData(self, TypeRole)
        value_item.setData(QtGui.QBrush(self.get_color()), QtCore.Qt.ForegroundRole)
        value_item.setFlags(
            QtCore.Qt.ItemFlag.ItemIsSelectable |
            QtCore.Qt.ItemFlag.ItemIsEnabled)
        if model.editable_values:
            value_item.setFlags(value_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)

        # Set tooltip from description if available
        if isinstance(value, dict) and 'description' in value:
            value_item.setData(str(value['description']), QtCore.Qt.ItemDataRole.ToolTipRole)

        return value_item

    def serialize(self, model, item, data, parent):
        """Serialize the full dict structure back."""
        value_item = parent.child(item.row(), 1)
        value = value_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            key_item = parent.child(item.row(), 0)
            key = key_item.data(QtCore.Qt.ItemDataRole.DisplayRole)
            data[key] = value
        elif isinstance(data, list):
            data.append(value)


# Add any custom DataType to this list
# NOTE: Order matters! More specific types must come before generic ones.
# - ChoicesType must match before ConfigValueType (has 'choices' key)
# - ConfigValueType must match before DictType (has 'value' key with metadata)
# - DictType is the fallback for all other dicts
#
DATA_TYPES = [
    NoneType(),
    UrlType(),
    FilepathTypeImages(),
    FilepathType(),
    ColorType(),  # Must be before StrType to match color strings first
    StrType(),
    IntType(),
    FloatType(),
    BoolType(),
    ListType(),
    RangeType(),
    ChoicesType(),      # Match {value, choices, ...} - dropdown editor
    ConfigValueType(),  # Match {value, description, ...} without choices - typed editor
    DictType()          # Fallback for all other dicts
]


def match_type(data):
    """Try to match the given data object to a DataType"""
    for type_ in DATA_TYPES:
        if type_.matches(data):
            return type_


def set_plugin_dir(plugin_dir):
    """Set the global PLUGIN_DIR variable used by FilepathTypeImages."""
    global PLUGIN_DIR
    PLUGIN_DIR = plugin_dir

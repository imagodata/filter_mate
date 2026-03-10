from qgis.PyQt import QtGui, QtCore, QtWidgets
from . import delegate
from . import themes
from .datatypes import TypeRole


class JsonView(QtWidgets.QTreeView):
    """Tree to display the JsonModel."""
    onLeaveEvent = QtCore.pyqtSignal()

    def __init__(self, model, plugin_dir=None, parent=None):
        super(JsonView, self).__init__(parent)
        self.model = model
        self.plugin_dir = plugin_dir

        # CRITICAL: Set model IMMEDIATELY to avoid Qt crashes
        if model is not None:
            self.setModel(model)

        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.setItemDelegate(delegate.JsonDelegate())

        # Apply theme-aware stylesheet
        self._apply_theme_stylesheet()

        # Visual configuration
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setIndentation(18)
        self.setRootIsDecorated(True)
        self.setExpandsOnDoubleClick(True)
        self.setWordWrap(False)

        font = self.font()
        font.setPointSize(9)
        self.setFont(font)

        # Column configuration
        header = self.header()
        header.setStretchLastSection(True)
        header.setVisible(True)
        header.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.resizeSection(0, 200)
        header.setMinimumSectionSize(100)
        header.setHighlightSections(False)

    def _apply_theme_stylesheet(self):
        """Apply stylesheet based on detected theme (dark/light)."""
        # Check if theme was forced externally
        if hasattr(self, '_forced_dark') and self._forced_dark is not None:
            is_dark = self._forced_dark
        else:
            # Détection simple du thème basée sur la palette
            try:
                from qgis.core import QgsApplication
                palette = QgsApplication.palette()
                bg_color = palette.color(QtGui.QPalette.Window)
                is_dark = bg_color.lightness() < 128
            except (ImportError, AttributeError):
                is_dark = False

        if is_dark:
            self.setStyleSheet(self._dark_stylesheet())
        else:
            self.setStyleSheet(self._light_stylesheet())

    @staticmethod
    def _dark_stylesheet():
        """Dark theme stylesheet with enhanced tree indicators."""
        return """
            QTreeView {
                font-size: 9pt;
                background-color: #1E1E1E;
                alternate-background-color: #232324;
                selection-background-color: #264F78;
                selection-color: #FFFFFF;
                border: 1px solid #3E3E42;
                color: #D4D4D4;
                outline: none;
            }
            QTreeView::item {
                padding: 2px 4px;
                min-height: 24px;
                border: none;
                border-bottom: 1px solid #2A2A2D;
            }
            QTreeView::item:hover {
                background-color: #2A2D2E;
            }
            QTreeView::item:selected {
                background-color: #264F78;
                color: #FFFFFF;
            }
            QTreeView::item:selected:hover {
                background-color: #1B3A5C;
            }

            /* Tree branch indicators */
            QTreeView::branch {
                background-color: transparent;
            }
            QTreeView::branch:has-siblings:!adjoins-item {
                border-image: none;
                background: transparent;
            }
            QTreeView::branch:has-siblings:adjoins-item {
                border-image: none;
            }
            QTreeView::branch:!has-children:!has-siblings:adjoins-item {
                border-image: none;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                image: none;
                border-image: none;
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                image: none;
                border-image: none;
            }

            /* Indentation guide lines */
            QTreeView::branch:has-siblings:!adjoins-item {
                border-left: 1px solid #3E3E42;
            }
            QTreeView::branch:has-siblings:adjoins-item {
                border-left: 1px solid #3E3E42;
            }

            /* Header */
            QHeaderView::section {
                background-color: #2D2D30;
                padding: 5px 8px;
                border: none;
                border-bottom: 2px solid #007ACC;
                border-right: 1px solid #3E3E42;
                font-weight: bold;
                font-size: 9pt;
                min-height: 26px;
                color: #CCCCCC;
            }
            QHeaderView::section:first {
                border-left: none;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QHeaderView::section:hover {
                background-color: #353539;
            }

            /* Scrollbar */
            QScrollBar:vertical {
                background-color: #1E1E1E;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #424242;
                min-height: 30px;
                border-radius: 4px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #555555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar:horizontal {
                background-color: #1E1E1E;
                height: 10px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background-color: #424242;
                min-width: 30px;
                border-radius: 4px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #555555;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
            }
        """

    @staticmethod
    def _light_stylesheet():
        """Light theme stylesheet with enhanced tree indicators."""
        return """
            QTreeView {
                font-size: 9pt;
                background-color: #FFFFFF;
                alternate-background-color: #F8F9FA;
                selection-background-color: #0078D4;
                selection-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                color: #333333;
                outline: none;
            }
            QTreeView::item {
                padding: 2px 4px;
                min-height: 24px;
                border: none;
                border-bottom: 1px solid #EEEEEE;
            }
            QTreeView::item:hover {
                background-color: #E8F0FE;
            }
            QTreeView::item:selected {
                background-color: #0078D4;
                color: #FFFFFF;
            }
            QTreeView::item:selected:hover {
                background-color: #106EBE;
            }

            /* Tree branch indicators */
            QTreeView::branch {
                background-color: transparent;
            }
            QTreeView::branch:has-siblings:!adjoins-item {
                border-left: 1px solid #D0D0D0;
            }
            QTreeView::branch:has-siblings:adjoins-item {
                border-left: 1px solid #D0D0D0;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                image: none;
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                image: none;
            }

            /* Header */
            QHeaderView::section {
                background-color: #F3F3F3;
                padding: 5px 8px;
                border: none;
                border-bottom: 2px solid #0078D4;
                border-right: 1px solid #E0E0E0;
                font-weight: bold;
                font-size: 9pt;
                min-height: 26px;
                color: #444444;
            }
            QHeaderView::section:first {
                border-left: none;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QHeaderView::section:hover {
                background-color: #E8E8E8;
            }

            /* Scrollbar */
            QScrollBar:vertical {
                background-color: #F5F5F5;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #C0C0C0;
                min-height: 30px;
                border-radius: 4px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #A0A0A0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar:horizontal {
                background-color: #F5F5F5;
                height: 10px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background-color: #C0C0C0;
                min-width: 30px;
                border-radius: 4px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #A0A0A0;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
            }
        """

    # def leaveEvent(self, QEvent):
    #     self.onLeaveEvent.emit()

    def _menu(self, position):
        """Show the actions of the DataType (if any)."""
        menu = QtWidgets.QMenu()
        index = self.indexAt(position)
        data = index.data(TypeRole)
        if data is None:
            return
        actions = data.actions(index)
        if actions is not None and len(actions) > 0:
            # Convert string actions to QAction objects if needed
            qactions = []
            for action in actions:
                if isinstance(action, str):
                    qaction = QtGui.QAction(action, None)
                    qactions.append(qaction)
                else:
                    qactions.append(action)
            menu.addActions(qactions)
        action = menu.exec_(self.viewport().mapToGlobal(position))
        if action:
            action_data = action.data()
            item = self.model.itemFromIndex(index)

            if action_data is not None:
                if action.text() == "Change":
                    if len(action_data) == 2:
                        item.setData(action_data[0], QtCore.Qt.ItemDataRole.DisplayRole)
                    elif len(action_data) == 3:
                        item.setData(action_data[0], QtCore.Qt.ItemDataRole.DisplayRole)
                        item.setData(action_data[1], QtCore.Qt.ItemDataRole.UserRole)

            if action.text() == "Rename":
                self.edit(index)

            if action.text() == "Add child":

                self.model.addData(item)

            if action.text() == "Insert sibling up":
                self.model.addData(item, 'up')

            if action.text() == "Insert sibling down":
                self.model.addData(item, 'down')

            if action.text() == "Remove":

                self.model.removeData(item)

    def set_theme(self, theme_name):
        """
        Change the color theme for the JSON view.

        Args:
            theme_name (str): Name of the theme to apply (e.g., 'monokai', 'nord')

        Returns:
            bool: True if theme was changed successfully
        """
        if themes.set_theme(theme_name):
            # Refresh the view to apply new colors
            self.refresh_colors()
            return True
        return False

    def get_current_theme_name(self):
        """
        Get the name of the currently active theme.

        Returns:
            str: Name of the current theme
        """
        return themes.get_current_theme().name

    def get_available_themes(self):
        """
        Get list of available theme names.

        Returns:
            dict: Dictionary mapping theme keys to display names
        """
        return themes.get_theme_display_names()

    def refresh_colors(self):
        """
        Refresh all item colors in the view based on the current theme.
        """
        if not self.model:
            return

        # Recursively update colors for all items
        def update_item_colors(item):
            if item is None:
                return

            # Update the item's color if it has a DataType
            data_type = item.data(TypeRole)
            if data_type is not None:
                item.setData(QtGui.QBrush(data_type.get_color()), QtCore.Qt.ForegroundRole)

            # Update children
            for row in range(item.rowCount()):
                for col in range(item.columnCount()):
                    child = item.child(row, col)
                    if child:
                        update_item_colors(child)

        # Update all root items
        for row in range(self.model.rowCount()):
            for col in range(self.model.columnCount()):
                item = self.model.item(row, col)
                if item:
                    update_item_colors(item)

        # Force view update
        self.viewport().update()

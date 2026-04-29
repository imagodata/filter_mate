"""
FilterMate FavoritesManagerDialog.

Dialog for managing filter favorites with list, edit, delete, and search capabilities.
Extracted from filter_mate_dockwidget.py for better modularity.
"""
from typing import Optional
import logging

try:
    from qgis.PyQt.QtWidgets import (
        QButtonGroup, QComboBox, QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
        QListWidgetItem, QPushButton, QLabel, QLineEdit, QTextEdit, QMessageBox,
        QFormLayout, QDialogButtonBox, QRadioButton, QSplitter, QTreeWidget,
        QTreeWidgetItem, QHeaderView, QTabWidget, QWidget
    )
    from qgis.PyQt.QtCore import Qt, pyqtSignal
    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False
    # Stub classes for type hints when QGIS not available
    QDialog = object
    QWidget = object
    QVBoxLayout = object
    QHBoxLayout = object
    QListWidget = object
    QListWidgetItem = object
    QPushButton = object
    QLabel = object
    QLineEdit = object
    QTextEdit = object
    QMessageBox = None
    QFormLayout = object
    QDialogButtonBox = object
    QButtonGroup = object
    QComboBox = object
    QRadioButton = object
    QSplitter = object
    QTreeWidget = object
    QTreeWidgetItem = object
    QHeaderView = None
    QTabWidget = object
    Qt = None
    pyqtSignal = lambda *args: None

# Scope badge + label constants — kept close to the UI so copywriter
# tweaks don't require touching the domain layer.
_SCOPE_BADGES = {
    "shared_here":   "👥",   # project=this, owner=NULL
    "shared_global": "🌐",   # project=GLOBAL, owner=NULL
    "mine_here":     "🔒",   # project=this, owner=me
    "mine_global":   "👤",   # project=GLOBAL, owner=me
    "foreign":       "•",    # someone else's favorite (visible in shared DB)
}


def _favorite_scope_kind(fav, current_user, current_project_uuid, global_uuid):
    """Classify a favorite for badge/filter purposes.

    Returns one of the keys in ``_SCOPE_BADGES``. "foreign" means the
    favorite belongs to another user — kept visible because forbidding
    the owner column would be surprising, but flagged so users can tell
    which ones aren't theirs.
    """
    owner = getattr(fav, "owner", None)
    is_mine = bool(current_user) and owner == current_user
    is_shared = owner is None
    is_foreign = (not is_mine) and (not is_shared)
    # The manager's cache is pinned to ONE project_uuid — so every row
    # in the cache has the manager's project. The "global" vs "here"
    # distinction therefore depends on which project the manager is
    # pinned to, not on the favorite's own project_uuid (absent from
    # the dataclass).
    is_global = current_project_uuid == global_uuid
    if is_foreign:
        return "foreign"
    if is_mine:
        return "mine_global" if is_global else "mine_here"
    return "shared_global" if is_global else "shared_here"


logger = logging.getLogger(__name__)


class FavoritesManagerDialog(QDialog if HAS_QGIS else object):
    """
    Dialog for managing filter favorites.

    Features:
    - List all favorites with search/filter
    - Edit favorite name, description, tags, and expression
    - Delete favorites
    - Apply favorites directly
    - View remote layer details

    Signals:
        favoriteApplied: Emitted when a favorite is applied (favorite_id)
        favoriteDeleted: Emitted when a favorite is deleted (favorite_id)
        favoriteUpdated: Emitted when a favorite is updated (favorite_id)
        favoritesChanged: Emitted when favorites list changes
    """

    if HAS_QGIS:
        favoriteApplied = pyqtSignal(str)
        favoriteDeleted = pyqtSignal(str)
        favoriteUpdated = pyqtSignal(str)
        favoritesChanged = pyqtSignal()

    def __init__(self, favorites_manager, parent=None, extension_bridge=None):
        """
        Initialize FavoritesManagerDialog.

        Args:
            favorites_manager: FavoritesManager instance
            parent: Parent widget
            extension_bridge: Optional FavoritesExtensionBridge — when
                provided, the dialog routes its sharing flows (shared
                picker / publish) through it instead of importing the
                extension UI directly. Restores the F5 invariant that
                ``favorites_extension_bridge`` is the single coupling
                point with ``favorites_sharing``.
        """
        if HAS_QGIS:
            super().__init__(parent)

        self._favorites_manager = favorites_manager
        self._extension_bridge = extension_bridge
        self._current_fav_id = None
        self._all_favorites = []
        # FIX 2026-04-22: re-entrancy guard so our own update/delete don't bounce
        # back through the external-change refresh slot.
        self._suppress_external_refresh = False
        # F13 fix 2026-04-27: track the external-change subscription so
        # closeEvent can disconnect it. Without this the manager keeps a
        # hard ref to the dialog through the signal slot — every open/close
        # cycle leaked one dialog instance.
        self._external_change_connected = False

        if HAS_QGIS:
            self._setup_ui()

            # FIX 2026-04-22: keep the dialog in sync when favorites change
            # externally (import, apply updating use_count, another controller
            # editing the same manager). Without this the list stayed stale.
            if self._favorites_manager is not None and hasattr(self._favorites_manager, 'favorites_changed'):
                try:
                    self._favorites_manager.favorites_changed.connect(self._on_external_favorites_changed)
                    self._external_change_connected = True
                except (TypeError, RuntimeError):
                    pass

    def _on_external_favorites_changed(self) -> None:
        """Refresh list when favorites change outside this dialog."""
        if self._suppress_external_refresh:
            return
        try:
            previous_id = self._current_fav_id
            self.refresh()
            # Keep the user's previous selection if still present
            if previous_id:
                for i in range(self._list_widget.count()):
                    if self._list_widget.item(i).data(Qt.ItemDataRole.UserRole) == previous_id:
                        self._list_widget.setCurrentRow(i)
                        break
        except (RuntimeError, AttributeError) as e:
            logger.debug(f"Could not refresh dialog on external change: {e}")

    def _show_error(self, message: str) -> None:
        """Push a critical/error notification to the QGIS message bar.

        F11 policy: transactional failures (delete, save) surface via
        ``infrastructure.feedback.show_error`` rather than a modal
        ``QMessageBox.warning`` — the dialog stays usable, the toast is
        visible at the top of the canvas, and the full traceback can be
        read in View → Panels → Log Messages.
        """
        try:
            from ...infrastructure.feedback import show_error
            show_error(message)
        except ImportError:
            logger.error(message)

    def closeEvent(self, event):
        """Disconnect from external signals before Qt destroys the dialog.

        F13 fix 2026-04-27: the manager's ``favorites_changed`` signal
        held a hard ref to ``_on_external_favorites_changed``, keeping
        every closed dialog alive across Open → Close → Open cycles.
        """
        if self._external_change_connected and self._favorites_manager is not None:
            try:
                self._favorites_manager.favorites_changed.disconnect(
                    self._on_external_favorites_changed
                )
            except (TypeError, RuntimeError):
                pass
            self._external_change_connected = False
        if HAS_QGIS:
            super().closeEvent(event)

    def _setup_ui(self):
        """Build the dialog UI."""
        self.setWindowTitle(self.tr("FilterMate - Favorites Manager"))
        self.setMinimumSize(600, 450)
        self.resize(720, 520)
        self.setModal(True)

        # Apply FilterMate dialog style
        self.setStyleSheet(self._get_dialog_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header row with count + optional shared-favorites shortcut
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        fav_count = self._favorites_manager.count if self._favorites_manager else 0
        self._header_label = QLabel(
            self.tr("<b>Saved Favorites ({0})</b>").format(fav_count)
        )
        self._header_label.setObjectName("dialogHeader")
        header_row.addWidget(self._header_label)
        header_row.addStretch()

        # FIX 2026-04-23: discoverable shortcut to the Resource Sharing
        # picker — only shown when the favorites_sharing extension is active
        # so regular users never see a button they can't use.
        self._shared_btn = QPushButton("📡 " + self.tr("Shared..."))
        self._shared_btn.setObjectName("sharedBtn")
        self._shared_btn.setToolTip(self.tr(
            "Browse favorites shared via QGIS Resource Sharing collections"
        ))
        self._shared_btn.clicked.connect(self._on_shared_clicked)
        self._shared_btn.setVisible(self._is_sharing_active())
        header_row.addWidget(self._shared_btn)

        # Publish button — symmetric counterpart that pushes favorites into
        # a Resource Sharing collection. Hidden when the extension is
        # inactive or when there is nothing to publish.
        self._publish_btn = QPushButton("📤 " + self.tr("Publish..."))
        self._publish_btn.setObjectName("publishBtn")
        self._publish_btn.setToolTip(self.tr(
            "Publish selected favorites into a Resource Sharing collection"
        ))
        self._publish_btn.clicked.connect(self._on_publish_clicked)
        self._publish_btn.setVisible(
            self._is_sharing_active() and fav_count > 0
        )
        header_row.addWidget(self._publish_btn)

        layout.addLayout(header_row)

        # Search box + scope filter (v5.1)
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        search_label = QLabel("🔍")
        search_label.setObjectName("searchIcon")
        search_layout.addWidget(search_label)

        self._search_edit = QLineEdit()
        self._search_edit.setObjectName("searchEdit")
        self._search_edit.setPlaceholderText(
            self.tr("Search by name, expression, tags, or description...")
        )
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_edit, 1)

        # Scope filter — dropdown between search and the count badge.
        # Stays visible even when the extension/owner cascade resolves to
        # None (the user can still filter by "Shared" vs "All"); the
        # "Mine ..." entries simply match nothing when no identity is set.
        self._scope_combo = QComboBox()
        self._scope_combo.setObjectName("scopeCombo")
        self._scope_combo.setToolTip(self.tr(
            "Filter favorites by scope (owner × project)."
        ))
        # Keep enum keys in sync with FavoriteScope so the lookup is
        # a direct dict access — no parallel mapping to maintain.
        self._scope_combo.addItem("🔎 " + self.tr("All"), "all")
        self._scope_combo.addItem("🌐 " + self.tr("Shared · All projects"), "global_shared")
        self._scope_combo.addItem("👥 " + self.tr("Shared · This project"), "project_shared")
        self._scope_combo.addItem("👤 " + self.tr("Mine · All projects"), "global_mine")
        self._scope_combo.addItem("🔒 " + self.tr("Mine · This project"), "project_mine")
        self._scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        search_layout.addWidget(self._scope_combo)
        layout.addLayout(search_layout)

        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")
        splitter.setHandleWidth(2)  # Minimal handle width
        splitter.setChildrenCollapsible(False)

        # Left panel: List of favorites
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel: Details with tabs
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)

        # Set splitter proportions (30% list, 70% details)
        splitter.setSizes([220, 480])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        # Buttons
        button_layout = self._create_buttons()
        layout.addLayout(button_layout)

        # Initial population (handle None favorites_manager)
        if self._favorites_manager:
            self._all_favorites = self._favorites_manager.get_all_favorites()
        else:
            self._all_favorites = []
        self._populate_list(self._all_favorites)

        # Select first item
        if self._list_widget.count() > 0:
            self._list_widget.setCurrentRow(0)

    def _get_dialog_stylesheet(self) -> str:
        """Get FilterMate harmonized stylesheet for the dialog."""
        return """
            /* Dialog background */
            QDialog {
                background-color: #f8f9fa;
            }

            /* Header */
            QLabel#dialogHeader {
                font-size: 14pt;
                font-weight: 600;
                color: #2c3e50;
                padding: 8px 0px;
                margin-bottom: 4px;
            }

            /* Search */
            QLabel#searchIcon {
                font-size: 14pt;
                padding: 4px;
            }
            QLineEdit#searchEdit {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: white;
                font-size: 10pt;
            }
            QLineEdit#searchEdit:focus {
                border-color: #f39c12;
                background-color: #fffef5;
            }

            /* List widget */
            QListWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px;
                font-size: 10pt;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 6px;
                margin: 2px 0px;
            }
            QListWidget::item:selected {
                background-color: #f5b041;
                color: white;
            }
            QListWidget::item:hover:!selected {
                background-color: #fef5e7;
            }

            /* Tab widget */
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                padding: 8px;
                margin-top: -1px;
            }
            QTabBar {
                qproperty-drawBase: 0;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #555555;
                border: 1px solid #ddd;
                border-bottom: none;
                padding: 8px 14px;
                margin-right: 3px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 10pt;
                min-width: 70px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #2c3e50;
                border-bottom: 2px solid #f39c12;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background-color: #fef5e7;
                color: #34495e;
            }

            /* Form inputs */
            QLineEdit, QTextEdit {
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 6px 10px;
                background-color: white;
                font-size: 10pt;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #f39c12;
                background-color: #fffef5;
            }

            /* Tree widget */
            QTreeWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                alternate-background-color: #fafafa;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: 500;
            }

            /* Buttons - FilterMate mousse style */
            QPushButton {
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 10pt;
                font-weight: 500;
                border: none;
            }
            QPushButton#applyBtn {
                background-color: #27ae60;
                color: white;
            }
            QPushButton#applyBtn:hover {
                background-color: #219a52;
            }
            QPushButton#applyBtn:disabled {
                background-color: #95d5b2;
                color: #e8e8e8;
            }
            QPushButton#saveBtn {
                background-color: #3498db;
                color: white;
            }
            QPushButton#saveBtn:hover {
                background-color: #2980b9;
            }
            QPushButton#saveBtn:disabled {
                background-color: #a9cce3;
                color: #e8e8e8;
            }
            QPushButton#deleteBtn {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton#deleteBtn:hover {
                background-color: #c0392b;
            }
            QPushButton#deleteBtn:disabled {
                background-color: #f5b7b1;
                color: #e8e8e8;
            }
            QPushButton#closeBtn {
                background-color: #ecf0f1;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
            }
            QPushButton#closeBtn:hover {
                background-color: #d5dbdb;
            }

            /* Labels */
            QLabel {
                color: #34495e;
            }
            QLabel#infoLabel {
                color: #7f8c8d;
                font-size: 9pt;
            }
            QLabel#noRemoteLabel {
                color: #95a5a6;
                font-style: italic;
                padding: 20px;
            }

            /* Splitter */
            QSplitter::handle {
                background-color: #e0e0e0;
                width: 1px;
            }
            QSplitter::handle:hover {
                background-color: #f39c12;
            }
        """

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with favorites list."""
        # M3 (#41): pass self as parent so the widget stays anchored to the
        # dialog's lifetime until the splitter takes ownership. Without it,
        # a teardown race could GC the widget while Qt is still iterating
        # children on shutdown.
        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self._list_widget = QListWidget()
        self._list_widget.setMinimumWidth(180)
        self._list_widget.setMaximumWidth(250)
        self._list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list_widget.currentItemChanged.connect(self._on_selection_changed)

        left_layout.addWidget(self._list_widget)
        return left_panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with details tabs."""
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._tab_widget = QTabWidget()

        # Tab 1: General Info
        general_tab = self._create_general_tab()
        self._tab_widget.addTab(general_tab, self.tr("General"))

        # Tab 2: Expression
        expr_tab = self._create_expression_tab()
        self._tab_widget.addTab(expr_tab, self.tr("Expression"))

        # Tab 3: Remote Layers
        remote_tab = self._create_remote_tab()
        self._tab_widget.addTab(remote_tab, self.tr("Remote"))

        right_layout.addWidget(self._tab_widget)
        return right_panel

    def _create_general_tab(self) -> QWidget:
        """Create the General Info tab."""
        general_tab = QWidget(self)
        general_layout = QFormLayout(general_tab)
        general_layout.setContentsMargins(12, 12, 12, 12)
        general_layout.setSpacing(10)
        general_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(self.tr("Favorite name"))
        general_layout.addRow(self.tr("Name:"), self._name_edit)

        self._description_edit = QTextEdit()
        self._description_edit.setMaximumHeight(70)
        self._description_edit.setPlaceholderText(self.tr("Description (auto-generated, editable)"))
        general_layout.addRow(self.tr("Description:"), self._description_edit)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText(
            self.tr("Enter tags separated by commas (e.g., urban, population, 2024)")
        )
        self._tags_edit.setToolTip(
            self.tr("Tags help organize and search favorites.\nSeparate multiple tags with commas.")
        )
        general_layout.addRow(self.tr("Tags:"), self._tags_edit)

        self._layer_label = QLabel("-")
        self._layer_label.setObjectName("infoLabel")
        self._layer_label.setWordWrap(True)
        general_layout.addRow(self.tr("Source Layer:"), self._layer_label)

        self._provider_label = QLabel("-")
        self._provider_label.setObjectName("infoLabel")
        general_layout.addRow(self.tr("Provider:"), self._provider_label)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 4, 0, 0)
        self._use_count_label = QLabel("-")
        self._created_label = QLabel("-")
        self._created_label.setObjectName("infoLabel")
        stats_layout.addWidget(QLabel(self.tr("Used:")))
        stats_layout.addWidget(self._use_count_label)
        stats_layout.addStretch()
        stats_layout.addWidget(QLabel(self.tr("Created:")))
        stats_layout.addWidget(self._created_label)
        general_layout.addRow(stats_layout)

        # Scope controls (v5.1) — two independent dimensions: owner (mine
        # vs shared) and project (this vs all). Each dimension is a pair
        # of mutually exclusive radios; the combination gives the 4
        # scopes surfaced in the header filter combo.
        scope_container = QWidget(general_tab)
        scope_v = QVBoxLayout(scope_container)
        scope_v.setContentsMargins(0, 0, 0, 0)
        scope_v.setSpacing(4)

        owner_row = QHBoxLayout()
        owner_row.setSpacing(8)
        self._scope_mine_radio = QRadioButton(self.tr("Mine"))
        self._scope_shared_radio = QRadioButton(self.tr("Shared"))
        self._scope_owner_group = QButtonGroup(self)
        self._scope_owner_group.addButton(self._scope_mine_radio)
        self._scope_owner_group.addButton(self._scope_shared_radio)
        owner_row.addWidget(self._scope_mine_radio)
        owner_row.addWidget(self._scope_shared_radio)
        owner_row.addStretch()
        scope_v.addLayout(owner_row)

        project_row = QHBoxLayout()
        project_row.setSpacing(8)
        self._scope_proj_here_radio = QRadioButton(self.tr("This project"))
        self._scope_proj_all_radio = QRadioButton(self.tr("All projects"))
        # Project dimension is read-only for now: moving a favorite
        # across projects would require cross-cache bookkeeping that
        # belongs in a dedicated "move/duplicate" flow. Radios show the
        # current project scope for transparency but can't be flipped.
        self._scope_proj_here_radio.setEnabled(False)
        self._scope_proj_all_radio.setEnabled(False)
        ro_tip = self.tr(
            "Project scope is set when the favorite is created. Move it "
            "via the filtering tab (coming soon) to switch projects."
        )
        self._scope_proj_here_radio.setToolTip(ro_tip)
        self._scope_proj_all_radio.setToolTip(ro_tip)
        self._scope_project_group = QButtonGroup(self)
        self._scope_project_group.addButton(self._scope_proj_here_radio)
        self._scope_project_group.addButton(self._scope_proj_all_radio)
        project_row.addWidget(self._scope_proj_here_radio)
        project_row.addWidget(self._scope_proj_all_radio)
        project_row.addStretch()
        scope_v.addLayout(project_row)

        # A small owner label showing who currently owns this favorite —
        # useful when editing someone else's shared favorite so the user
        # isn't surprised when "Mine" gets auto-selected on save.
        self._owner_label = QLabel("-")
        self._owner_label.setObjectName("infoLabel")
        scope_v.addWidget(self._owner_label)

        general_layout.addRow(self.tr("Visibility:"), scope_container)

        return general_tab

    def _create_expression_tab(self) -> QWidget:
        """Create the Expression tab."""
        expr_tab = QWidget(self)
        expr_layout = QVBoxLayout(expr_tab)
        expr_layout.setContentsMargins(12, 12, 12, 12)
        expr_layout.setSpacing(8)

        source_expr_label = QLabel(self.tr("<b>Source Layer Expression:</b>"))
        expr_layout.addWidget(source_expr_label)

        self._expression_edit = QTextEdit()
        self._expression_edit.setPlaceholderText(self.tr("Filter expression for source layer"))
        self._expression_edit.setStyleSheet(
            "font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 10pt;"
        )
        expr_layout.addWidget(self._expression_edit)

        return expr_tab

    def _create_remote_tab(self) -> QWidget:
        """Create the Remote Layers tab."""
        remote_tab = QWidget(self)
        remote_layout = QVBoxLayout(remote_tab)
        remote_layout.setContentsMargins(12, 12, 12, 12)
        remote_layout.setSpacing(8)

        remote_header = QLabel(self.tr("<b>Filtered Remote Layers:</b>"))
        remote_layout.addWidget(remote_header)

        self._remote_tree = QTreeWidget()
        self._remote_tree.setHeaderLabels([self.tr("Layer"), self.tr("Features"), self.tr("Expression")])
        self._remote_tree.setColumnCount(3)
        self._remote_tree.header().setStretchLastSection(True)
        self._remote_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._remote_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._remote_tree.setAlternatingRowColors(True)
        remote_layout.addWidget(self._remote_tree)

        self._no_remote_label = QLabel(self.tr("<i>No remote layers in this favorite</i>"))
        self._no_remote_label.setObjectName("noRemoteLabel")
        self._no_remote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        remote_layout.addWidget(self._no_remote_label)

        return remote_tab

    def _create_buttons(self) -> QHBoxLayout:
        """Create the button row."""
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 12, 0, 0)
        button_layout.setSpacing(10)

        self._apply_btn = QPushButton("▶ " + self.tr("Apply"))
        self._apply_btn.setObjectName("applyBtn")
        self._apply_btn.setEnabled(False)
        self._apply_btn.setToolTip(self.tr("Apply this favorite filter to the project"))
        self._apply_btn.clicked.connect(self._on_apply)

        self._save_btn = QPushButton("💾 " + self.tr("Save Changes"))
        self._save_btn.setObjectName("saveBtn")
        self._save_btn.setEnabled(False)
        self._save_btn.setToolTip(self.tr("Save modifications to this favorite"))
        self._save_btn.clicked.connect(self._on_save)

        self._delete_btn = QPushButton("🗑️ " + self.tr("Delete"))
        self._delete_btn.setObjectName("deleteBtn")
        self._delete_btn.setEnabled(False)
        self._delete_btn.setToolTip(self.tr("Permanently delete this favorite"))
        self._delete_btn.clicked.connect(self._on_delete)

        close_btn = QPushButton(self.tr("Close"))
        close_btn.setObjectName("closeBtn")
        close_btn.setToolTip(self.tr("Close this dialog"))
        close_btn.clicked.connect(self.reject)

        button_layout.addWidget(self._apply_btn)
        button_layout.addWidget(self._save_btn)
        button_layout.addStretch()
        button_layout.addWidget(self._delete_btn)
        button_layout.addWidget(close_btn)

        return button_layout

    def _populate_list(self, favorites_to_show: list):
        """Populate list widget with given favorites."""
        self._list_widget.clear()

        # Pre-resolve identity / project once — avoids a per-item cascade
        # lookup that would otherwise fire for every favorite.
        current_user = self._resolve_current_user()
        project_uuid = getattr(self._favorites_manager, "_project_uuid", None)
        try:
            from ...core.domain.favorites_manager import GLOBAL_PROJECT_UUID
        except Exception:
            GLOBAL_PROJECT_UUID = "00000000-0000-0000-0000-000000000000"

        for fav in favorites_to_show:
            layers_count = fav.get_layers_count() if hasattr(fav, 'get_layers_count') else 1

            kind = _favorite_scope_kind(
                fav, current_user, project_uuid, GLOBAL_PROJECT_UUID,
            )
            badge = _SCOPE_BADGES.get(kind, "")
            # Layout: "<badge> ★ <name> [<layers>] 🏷️"
            item_text = (f"{badge} " if badge else "") + f"★ {fav.name}"
            if layers_count > 1:
                item_text += f" [{layers_count}]"
            if fav.tags:
                item_text += " 🏷️"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, fav.id)

            owner = getattr(fav, "owner", None)
            owner_line = self._format_owner_line(owner, current_user)
            tooltip_lines = [
                f"Layer: {fav.layer_name}",
                f"Used: {fav.use_count} times",
                owner_line,
            ]
            if fav.tags:
                tooltip_lines.append(f"Tags: {', '.join(fav.tags)}")
            if fav.description:
                tooltip_lines.append("")
                tooltip_lines.append(fav.description)
            item.setToolTip("\n".join(tooltip_lines))

            self._list_widget.addItem(item)

    @staticmethod
    def _format_owner_line(owner, current_user) -> str:
        """Human-readable 'Owner: ...' line for list tooltips."""
        if owner is None:
            return "Owner: — (shared)"
        if current_user and owner == current_user:
            return f"Owner: {owner} (you)"
        return f"Owner: {owner}"

    def _on_search_changed(self, text: str):
        """Refresh the list using the current search + scope combo."""
        self._refresh_filtered_list()

    def _on_scope_changed(self, _index: int = 0):
        """Refresh the list when the scope combo changes."""
        self._refresh_filtered_list()

    def _refresh_filtered_list(self):
        """Recompute and repopulate the list from search × scope state.

        Ordering matters: we filter by scope first (cheap attribute check
        in-memory), then apply the text search on the narrowed subset so
        ``search_favorites()`` doesn't re-walk every row.
        """
        if not self._favorites_manager:
            return

        scope_key = self._current_scope_key()
        scoped = self._apply_scope_filter(self._all_favorites, scope_key)

        text = self._search_edit.text().strip() if self._search_edit else ""
        if text:
            query = text.lower()
            visible = [
                f for f in scoped
                if query in f.name.lower()
                or query in (f.expression or "").lower()
                or any(query in (t or "").lower() for t in (f.tags or []))
                or query in (f.description or "").lower()
            ]
        else:
            visible = scoped

        self._populate_list(visible)

        total = self._favorites_manager.count
        if len(visible) == total:
            self._header_label.setText(
                self.tr("<b>Saved Favorites ({0})</b>").format(total)
            )
        else:
            self._header_label.setText(
                self.tr("<b>Favorites ({0}/{1})</b>").format(len(visible), total)
            )

    def _current_scope_key(self) -> str:
        """Key of the currently-selected scope combo entry (defaults to 'all')."""
        if not hasattr(self, "_scope_combo") or self._scope_combo is None:
            return "all"
        data = self._scope_combo.currentData()
        return str(data) if data else "all"

    def _apply_scope_filter(self, favorites: list, scope_key: str) -> list:
        """Filter ``favorites`` in-memory by the given scope key.

        Mirrors ``FavoritesManager.list_by_scope`` but stays in the UI
        layer so the manager cache (already loaded + search-friendly)
        is reused rather than re-queried. Keeps "foreign" favorites
        (those owned by another user) visible in the ALL scope so users
        never get confused about missing rows.
        """
        if scope_key == "all" or not favorites:
            return list(favorites)

        current_user = self._resolve_current_user()
        project_uuid = getattr(self._favorites_manager, "_project_uuid", None)
        try:
            from ...core.domain.favorites_manager import GLOBAL_PROJECT_UUID
        except Exception:
            GLOBAL_PROJECT_UUID = "00000000-0000-0000-0000-000000000000"

        def _kind(fav):
            return _favorite_scope_kind(
                fav, current_user, project_uuid, GLOBAL_PROJECT_UUID,
            )

        # "shared_*" scopes: owner IS NULL × project dimension
        # "mine_*" scopes: owner == me × project dimension
        # "foreign" never matches a filter entry — always only visible in ALL.
        return [f for f in favorites if _kind(f) == scope_key]

    def _resolve_current_user(self):
        """Pull the current user identity from the manager (cached)."""
        mgr = self._favorites_manager
        if mgr is None:
            return None
        getter = getattr(mgr, "get_current_user", None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                return None
        return None

    def _on_selection_changed(self):
        """Handle selection change in list."""
        item = self._list_widget.currentItem()
        if not item or not self._favorites_manager:
            return

        fav_id = item.data(Qt.ItemDataRole.UserRole)
        fav = self._favorites_manager.get_favorite(fav_id)

        if not fav:
            return

        self._current_fav_id = fav_id

        # Update General tab
        self._name_edit.setText(fav.name)
        self._description_edit.setText(fav.description or "")
        self._tags_edit.setText(", ".join(fav.tags) if fav.tags else "")
        self._layer_label.setText(fav.layer_name or "-")
        self._provider_label.setText(fav.layer_provider or "-")
        self._use_count_label.setText(f"{fav.use_count} times")
        self._created_label.setText(fav.created_at[:16] if fav.created_at else "-")

        # Scope radios — owner dimension
        current_user = self._resolve_current_user()
        owner = getattr(fav, "owner", None)
        # ``blockSignals`` keeps the radios from triggering save-state
        # side effects while we initialise them from the loaded favorite.
        for radio in (
            self._scope_mine_radio, self._scope_shared_radio,
            self._scope_proj_here_radio, self._scope_proj_all_radio,
        ):
            radio.blockSignals(True)
        try:
            if owner is None:
                self._scope_shared_radio.setChecked(True)
            else:
                # Mine when the owner matches the resolved current user,
                # otherwise we still show "Mine" so saving doesn't silently
                # strip someone else's ownership — the owner label below
                # disambiguates for the user.
                self._scope_mine_radio.setChecked(True)

            # Scope radios — project dimension. _load_favorites only ever
            # loads one project at a time, so there's no per-row info here
            # — the dialog offers the choice as a "move on save" control.
            try:
                from ...core.domain.favorites_manager import GLOBAL_PROJECT_UUID
            except Exception:
                GLOBAL_PROJECT_UUID = "00000000-0000-0000-0000-000000000000"
            project_uuid = getattr(self._favorites_manager, "_project_uuid", None)
            if project_uuid == GLOBAL_PROJECT_UUID:
                self._scope_proj_all_radio.setChecked(True)
            else:
                self._scope_proj_here_radio.setChecked(True)
        finally:
            for radio in (
                self._scope_mine_radio, self._scope_shared_radio,
                self._scope_proj_here_radio, self._scope_proj_all_radio,
            ):
                radio.blockSignals(False)

        # Owner identity label
        if owner is None:
            self._owner_label.setText(self.tr("— (shared with everyone)"))
        elif current_user and owner == current_user:
            self._owner_label.setText(self.tr("{0} (you)").format(owner))
        else:
            # Editing someone else's favorite — highlight it so saving
            # as "Mine" doesn't feel surreptitious.
            self._owner_label.setText(self.tr(
                "{0} — selecting 'Mine' on save will transfer ownership to you"
            ).format(owner))

        # Update Expression tab
        self._expression_edit.setText(fav.expression)

        # Update Remote Layers tab
        self._remote_tree.clear()
        if fav.remote_layers and len(fav.remote_layers) > 0:
            self._no_remote_label.hide()
            self._remote_tree.show()

            for key, layer_data in fav.remote_layers.items():
                # Handle both new format (dict) and legacy format (string layer_id)
                if isinstance(layer_data, dict):
                    expr = layer_data.get('expression', '')
                    feature_count = layer_data.get('feature_count', '?')
                    # FIX 2026-04-23 (CRIT-3): key may be a portable signature
                    # (postgres::schema.table) when the favorite is v3 canonical.
                    # Prefer the payload's display_name so the UI shows the
                    # author's original label; fall back to the key (which is
                    # a layer name in legacy v1/v2 favorites).
                    display = layer_data.get('display_name') or key
                    signature = layer_data.get('layer_signature')
                else:
                    # Legacy format: layer_data is just the layer_id string
                    expr = ''
                    feature_count = '?'
                    display = key
                    signature = None
                tree_item = QTreeWidgetItem([
                    display,
                    str(feature_count),
                    expr[:80] + "..." if len(expr) > 80 else expr
                ])
                tooltip = expr
                if signature and signature != display:
                    tooltip = f"[{signature}]\n{expr}" if expr else f"[{signature}]"
                tree_item.setToolTip(0, signature or display)
                tree_item.setToolTip(2, tooltip)
                self._remote_tree.addTopLevelItem(tree_item)

            self._tab_widget.setTabText(
                2, self.tr("Remote ({0})").format(len(fav.remote_layers))
            )
        else:
            self._remote_tree.hide()
            self._no_remote_label.show()
            self._tab_widget.setTabText(2, self.tr("Remote"))

        # Enable buttons
        self._apply_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)

    def _on_apply(self):
        """Apply selected favorite."""
        if self._current_fav_id:
            self.favoriteApplied.emit(self._current_fav_id)
            self.accept()

    def _on_save(self):
        """Save changes to selected favorite."""
        if not self._current_fav_id or not self._favorites_manager:
            return

        new_name = self._name_edit.text().strip()
        new_expr = self._expression_edit.toPlainText().strip()
        new_desc = self._description_edit.toPlainText().strip()
        new_tags = [
            tag.strip() for tag in self._tags_edit.text().split(',')
            if tag.strip()
        ]

        # Resolve the target owner from the scope radios. "Shared" →
        # owner NULL; "Mine" → current resolved user. We never write
        # "Mine" when no identity is resolvable — would produce an
        # empty-string owner that the scope filter treats as a foreign
        # user, confusing everyone.
        desired_owner = None
        if hasattr(self, "_scope_mine_radio") and self._scope_mine_radio.isChecked():
            desired_owner = self._resolve_current_user() or None

        # Project dimension isn't editable inline (changing project_uuid
        # would require moving the row across caches, out of scope for
        # this dialog). The radio stays read-only: enabled visually so
        # the user sees the current state, but save does not act on it.

        if new_name:
            # F16 phase 4 lazy import: keeps this module importable in
            # tests that lack the 3-level package nesting needed by a
            # top-level ``from ...core.domain.exceptions`` statement.
            from ...core.domain.exceptions import FavoritePersistenceError
            # FIX 2026-04-22: suppress re-entrant external refresh triggered by
            # the manager's own favorites_changed emission.
            self._suppress_external_refresh = True
            try:
                self._favorites_manager.update_favorite(
                    self._current_fav_id,
                    name=new_name,
                    expression=new_expr,
                    description=new_desc,
                    tags=new_tags,
                    owner=desired_owner,
                )
                self._favorites_manager.save()
            except FavoritePersistenceError as e:
                self._show_error(self.tr(
                    "Could not save '{0}': {1}"
                ).format(new_name, e.__cause__ or e))
                return
            finally:
                self._suppress_external_refresh = False

            # FIX 2026-04-22: refresh the local cache so the next search or
            # populate_list() call reflects the edited name/tags. Without this,
            # _all_favorites still held the pre-edit FilterFavorite and
            # clearing the search box silently restored the old display.
            self._all_favorites = self._favorites_manager.get_all_favorites()
            # v5.1: re-render the list via the unified refresh so the
            # scope badge reflects the freshly-persisted owner. The
            # manual per-item text edit we used to do was out of sync
            # with the new badge prefix and lost the current scope filter.
            self._refresh_filtered_list()
            # Re-select the same id after repopulation so the details
            # pane keeps showing the user's edit.
            for i in range(self._list_widget.count()):
                if self._list_widget.item(i).data(Qt.ItemDataRole.UserRole) == self._current_fav_id:
                    self._list_widget.setCurrentRow(i)
                    break

            self.favoriteUpdated.emit(self._current_fav_id)
            self.favoritesChanged.emit()
            logger.info(f"Favorite updated: {new_name}")

    def _on_delete(self):
        """Delete selected favorite."""
        if not self._current_fav_id or not self._favorites_manager:
            return

        fav = self._favorites_manager.get_favorite(self._current_fav_id)
        if not fav:
            return

        # F11 policy: stays a modal QMessageBox.question because deletion
        # is destructive and a toast confirm would risk silent data loss
        # if missed.
        reply = QMessageBox.question(
            self,
            self.tr("Delete Favorite"),
            self.tr("Delete favorite '{0}'?").format(fav.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted_id = self._current_fav_id
        # F16 phase 4 lazy import — see _on_save for rationale.
        from ...core.domain.exceptions import FavoritePersistenceError
        # FIX 2026-04-22: suppress re-entrant external refresh from manager's
        # own favorites_changed emission during delete + save.
        self._suppress_external_refresh = True
        try:
            removed = self._favorites_manager.remove_favorite(deleted_id)
        except FavoritePersistenceError as e:
            self._show_error(self.tr(
                "Could not delete '{0}': {1}"
            ).format(fav.name, e.__cause__ or e))
            return
        finally:
            self._suppress_external_refresh = False

        # FIX 2026-04-23 (MED-5): unknown-id stays a soft False (Cat B
        # per F16 audit) — surface so the row stays visible. IO failures
        # are now caught above as PersistenceError.
        if not removed:
            self._show_error(self.tr(
                "'{0}' was not in the database — refresh and try again."
            ).format(fav.name))
            return

        self._list_widget.takeItem(self._list_widget.currentRow())

        # FIX 2026-04-22: keep the local cache in sync with the manager, else
        # clearing the search box re-populated the list with the deleted entry.
        self._all_favorites = [
            f for f in self._all_favorites
            if getattr(f, 'id', None) != deleted_id
        ]

        fav_count = self._favorites_manager.count if self._favorites_manager else 0
        self._header_label.setText(
            self.tr("<b>Saved Favorites ({0})</b>").format(fav_count)
        )

        # Save changes
        self._favorites_manager.save()

        # FIX 2026-04-23: after takeItem, Qt may auto-advance selection to the
        # next row and fire currentItemChanged. Resetting _current_fav_id=None
        # and calling setCurrentRow(0) afterwards silently fails (row is already
        # 0 -> no signal), leaving the remaining item visually selected but
        # with empty details and a disabled Delete button, making it impossible
        # to delete the last favorite without reopening the manager.
        if self._list_widget.count() > 0:
            # Force the selection handler to fire even if row 0 is already
            # current, so details/buttons reflect the remaining favorite.
            # Belt-and-braces: clear selection, reassign row 0, and invoke
            # the handler directly in case neither setCurrentRow call emits
            # (seen on some Qt versions when the list was rebuilt and the
            # internal "previous index" equals the target index).
            self._list_widget.clearSelection()
            self._list_widget.setCurrentRow(-1)
            self._list_widget.setCurrentRow(0)
            self._on_selection_changed()
        else:
            self._clear_details()
            self._current_fav_id = None
            self._apply_btn.setEnabled(False)
            self._save_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)

        self.favoriteDeleted.emit(deleted_id)
        self.favoritesChanged.emit()

    def _clear_details(self):
        """Clear all detail fields."""
        # Tab 1: General
        self._name_edit.clear()
        self._description_edit.clear()
        self._tags_edit.clear()
        self._layer_label.setText("-")
        self._provider_label.setText("-")
        self._use_count_label.setText("-")
        self._created_label.setText("-")
        # Scope radios — reset without firing signals so the next
        # selection starts from a clean state.
        for radio in (
            getattr(self, "_scope_mine_radio", None),
            getattr(self, "_scope_shared_radio", None),
            getattr(self, "_scope_proj_here_radio", None),
            getattr(self, "_scope_proj_all_radio", None),
        ):
            if radio is None:
                continue
            radio.blockSignals(True)
            radio.setChecked(False)
            radio.blockSignals(False)
        if hasattr(self, "_owner_label") and self._owner_label is not None:
            self._owner_label.setText("-")

        # Tab 2: Expression
        self._expression_edit.clear()

        # Tab 3: Remote Layers
        self._remote_tree.clear()
        self._no_remote_label.show()
        self._remote_tree.hide()
        self._tab_widget.setTabText(2, "🗂️ " + self.tr("Remote Layers"))

    # ─── favorites_sharing integration (optional) ─────────────────────

    def _is_sharing_active(self) -> bool:
        """True when the favorites_sharing extension is loaded + initialized.

        Delegates to the injected ``FavoritesExtensionBridge`` (F5
        invariant — single coupling point). When no bridge is provided
        (only happens in headless tests that don't exercise sharing),
        returns False so the sharing buttons stay inert.
        """
        if self._extension_bridge is None:
            return False
        try:
            return bool(self._extension_bridge.is_active())
        except Exception:
            return False

    def _on_shared_clicked(self) -> None:
        """Open the shared-favorites picker, then refresh the list on close.

        Routes through ``FavoritesExtensionBridge.open_shared_picker``
        (F5 invariant — single coupling point). The picker materialises
        chosen shared favorites into the user's DB via
        ``FavoritesSharingService.fork()``, which emits
        ``favorites_changed`` and triggers
        ``_on_external_favorites_changed`` — the list updates
        automatically. ``refresh()`` runs defensively in case the
        external signal was suppressed.
        """
        if not self._is_sharing_active() or self._favorites_manager is None:
            return
        try:
            self._extension_bridge.open_shared_picker(parent=self)
            self.refresh()
        except Exception as e:
            logger.debug(f"Could not open shared picker via bridge: {e}")

    def _on_publish_clicked(self) -> None:
        """Open the PublishFavoritesDialog pre-selecting the current row.

        Routes through ``FavoritesExtensionBridge.open_publish_dialog``
        (F5 invariant — single coupling point). When there is a
        selected favorite we pass its id as the default check; the user
        can still toggle others on/off in the publish dialog's list.
        """
        if not self._is_sharing_active() or self._favorites_manager is None:
            return
        preselected = [self._current_fav_id] if self._current_fav_id else []
        try:
            self._extension_bridge.open_publish_dialog(
                parent=self,
                preselected_ids=preselected or None,
            )
        except Exception as e:
            logger.debug(f"Could not open publish dialog via bridge: {e}")

    def refresh(self):
        """Refresh the favorites list, preserving the user's active filters.

        F10 fix 2026-04-27: previous implementation called
        ``_populate_list(self._all_favorites)`` directly, silently
        dropping any active search/scope filter when an external change
        triggered a refresh. We now re-fetch and delegate to
        ``_refresh_filtered_list`` so the user's filtering state
        survives ``favorites_changed`` and shared-picker imports.
        """
        if not self._favorites_manager:
            self._all_favorites = []
            self._populate_list(self._all_favorites)
            self._header_label.setText(self.tr("<b>Saved Favorites (0)</b>"))
            return
        self._all_favorites = self._favorites_manager.get_all_favorites()
        self._refresh_filtered_list()

    

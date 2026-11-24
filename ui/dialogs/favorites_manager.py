"""
FilterMate FavoritesManagerDialog.

Dialog for managing filter favorites with list, edit, delete, and search capabilities.
Extracted from filter_mate_dockwidget.py for better modularity.
"""
import copy
import logging

from ..styles.favorites_styles import favorites_dialog_stylesheet
from ..styles.mockup_design import MONO_FAMILY, render_icon
from .favorite_order import SORT_LAST_USED, SORT_MOST_USED, SORT_NAME, sorted_favorites
from .favorite_summary import date_text, scope_badge, summary_rows, use_text
from .favorite_summary_widgets import ExpressionView, text_value

try:
    from qgis.PyQt.QtWidgets import (
        QComboBox, QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
        QListWidgetItem, QPushButton, QLabel, QLineEdit, QTextEdit, QMessageBox,
        QAbstractItemView, QFormLayout, QFrame, QScrollArea, QSplitter,
        QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QWidget, QMenu
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
    QComboBox = object
    QFrame = object
    QScrollArea = object
    QSplitter = object
    QAbstractItemView = object
    QTableWidget = object
    QTableWidgetItem = object
    QHeaderView = None
    QTabWidget = object
    QMenu = object
    Qt = None

    def pyqtSignal(*args):
        return None

# Scope kinds of ``_favorite_scope_kind`` that apply to every project of this
# computer; the list shows them with the globe icon instead of the star.
_GLOBAL_SCOPE_KINDS = frozenset({"shared_global", "mine_global"})

# Scope combo entry (``FavoriteScope`` value) -> scope kind of ``_favorite_scope_kind``.
_SCOPE_KEY_KINDS = {
    "global_shared": "shared_global",
    "project_shared": "shared_here",
    "global_mine": "mine_global",
    "project_mine": "mine_here",
}


def _favorite_scope_kind(fav, current_user, current_project_uuid, global_uuid):
    """Classify a favorite for badge/filter purposes.

    Returns "shared_here", "shared_global", "mine_here", "mine_global" or
    "foreign". "foreign" means the
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

# Longest expression text shown in a Layers row; the tooltip has the full one.
_REMOTE_EXPRESSION_CHARS = 200


class FavoritesManagerDialog(QDialog if HAS_QGIS else object):
    """
    Dialog for managing filter favorites.

    Features:
    - List the project favorites then the global ones, with search/filter/sort
    - Double-click or context menu: apply, rename, duplicate, delete, copy to global/project
    - Read a summary of each favorite; edit its name, description and tags
    - Delete favorites
    - Apply favorites directly
    - View remote layer details

    Signals:
        favoriteApplied: Emitted when a project favorite is applied (favorite_id)
        globalFavoriteApplied: Emitted when a global favorite is applied (favorite_id)
        favoriteDeleted: Emitted when a favorite is deleted (favorite_id)
        favoriteUpdated: Emitted when a favorite is updated (favorite_id)
        favoritesChanged: Emitted when favorites list changes
    """

    if HAS_QGIS:
        favoriteApplied = pyqtSignal(str)
        globalFavoriteApplied = pyqtSignal(str)
        favoriteDeleted = pyqtSignal(str)
        favoriteUpdated = pyqtSignal(str)
        favoritesChanged = pyqtSignal()

    _dark = False  # theme of the dialog, set by _setup_ui

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

        self._favorites_service = favorites_manager
        self._extension_bridge = extension_bridge
        self._current_fav_id = None
        self._all_favorites = []  # the project favorites then the global ones
        self._global_ids = set()  # ids of the global ones among them
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
            if self._favorites_service is not None:
                try:
                    self._favorites_service.favorites_changed.connect(self._on_external_favorites_changed)
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
        if self._external_change_connected and self._favorites_service is not None:
            try:
                self._favorites_service.favorites_changed.disconnect(
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
        self.setMinimumSize(720, 500)
        self.resize(900, 620)
        self.setModal(True)

        # Theme of the plugin, read each time the dialog opens
        self._dark = self._plugin_theme_is_dark()
        self.setStyleSheet(favorites_dialog_stylesheet(self._dark))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header row with count + optional shared-favorites shortcut
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self._all_favorites = self._load_favorites()
        fav_count = self._favorites_service.count if self._favorites_service else 0
        self._header_label = QLabel(
            self.tr("<b>Saved Favorites ({0})</b>").format(len(self._all_favorites))
        )
        self._header_label.setObjectName("dialogHeader")
        header_row.addWidget(self._header_label)
        header_row.addStretch()

        # FIX 2026-04-23: discoverable shortcut to the Resource Sharing
        # picker — only shown when the favorites_sharing extension is active
        # so regular users never see a button they can't use.
        self._shared_btn = QPushButton(self.tr("Shared..."))
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
        self._publish_btn = QPushButton(self.tr("Publish..."))
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
        self._search_edit = QLineEdit()
        self._search_edit.setObjectName("searchEdit")
        self._search_edit.setPlaceholderText(
            self.tr("Search by name, expression, tags, or description...")
        )
        self._search_edit.setClearButtonEnabled(True)
        search_icon = self._theme_icon("/search.svg")
        if search_icon is not None:
            self._search_edit.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
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
        self._scope_combo.addItem(self.tr("All"), "all")
        self._scope_combo.addItem(self.tr("Shared · All projects"), "global_shared")
        self._scope_combo.addItem(self.tr("Shared · This project"), "project_shared")
        self._scope_combo.addItem(self.tr("Mine · All projects"), "global_mine")
        self._scope_combo.addItem(self.tr("Mine · This project"), "project_mine")
        self._scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        search_layout.addWidget(self._scope_combo)

        # Sort: by name (default), by last use or by number of uses
        self._sort_combo = QComboBox()
        self._sort_combo.setObjectName("sortCombo")
        self._sort_combo.setToolTip(self.tr("Sort the favorites."))
        self._sort_combo.addItem(self.tr("Name"), SORT_NAME)
        self._sort_combo.addItem(self.tr("Last used"), SORT_LAST_USED)
        self._sort_combo.addItem(self.tr("Most used"), SORT_MOST_USED)
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        search_layout.addWidget(self._sort_combo)
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

        # Set splitter proportions (list 1/3, details 2/3)
        splitter.setSizes([300, 600])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        # Buttons
        button_layout = self._create_buttons()
        layout.addLayout(button_layout)

        # Initial population (the favorites were loaded with the header)
        self._populate_list(sorted_favorites(self._all_favorites, self._current_sort_key()))

        # Select first item
        if self._list_widget.count() > 0:
            self._list_widget.setCurrentRow(0)

    @staticmethod
    def _plugin_theme_is_dark() -> bool:
        """True when the plugin theme is the dark one (anything else is light)."""
        try:
            from ..styles.style_loader import StyleLoader
            return StyleLoader.get_current_theme() == 'dark'
        except Exception:  # style loader unavailable: the light theme
            return False

    @staticmethod
    def _theme_icon(name: str):
        """QGIS theme icon ``name`` (e.g. ``/mActionFileSave.svg``), None when it is missing."""
        try:
            from qgis.core import QgsApplication
            icon = QgsApplication.getThemeIcon(name)
        except Exception:
            return None
        return None if icon is None or icon.isNull() else icon

    def _icon_button(self, text: str, icon_name: str) -> "QPushButton":
        """Button with the QGIS theme icon ``icon_name``; the text alone when the icon is missing."""
        button = QPushButton(text)
        icon = self._theme_icon(icon_name)
        if icon is not None:
            button.setIcon(icon)
        return button

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
        self._list_widget.setMinimumWidth(240)
        # A long name ends with "…" instead of widening the list or scrolling it.
        self._list_widget.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list_widget.currentItemChanged.connect(self._on_selection_changed)
        self._list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list_widget.customContextMenuRequested.connect(self._on_list_context_menu)

        left_layout.addWidget(self._list_widget)
        return left_panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with details tabs."""
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._tab_widget = QTabWidget()
        # A selected (bold) tab is never cut: no "…", scroll buttons when the tabs do not fit.
        self._tab_widget.tabBar().setElideMode(Qt.TextElideMode.ElideNone)
        self._tab_widget.tabBar().setUsesScrollButtons(True)

        self._tab_widget.addTab(self._create_summary_tab(), self.tr("Summary"))
        self._tab_widget.addTab(self._create_remote_tab(), self.tr("Layers"))

        right_layout.addWidget(self._tab_widget)
        return right_panel

    def _create_summary_tab(self) -> QWidget:
        """Create the Summary tab: what the favorite does, then what can be edited."""
        summary_tab = QWidget(self)
        tab_layout = QVBoxLayout(summary_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        # Everything scrolls vertically; the width never grows with a long expression.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("summaryContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 10, 12, 10)
        content_layout.setSpacing(10)

        self._scope_badge_label = QLabel("")
        self._scope_badge_label.setObjectName("scopeBadge")
        self._scope_badge_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.addWidget(self._scope_badge_label)
        badge_row.addStretch()
        content_layout.addLayout(badge_row)

        # Read-only summary rows (rebuilt on each selection by _show_summary_rows)
        self._summary_form = QFormLayout()
        self._summary_form.setContentsMargins(0, 0, 0, 0)
        self._summary_form.setSpacing(2)
        self._summary_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        self._summary_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        content_layout.addLayout(self._summary_form)

        # Editable fields
        edit_form = QFormLayout()
        edit_form.setContentsMargins(0, 0, 0, 0)
        edit_form.setSpacing(8)
        edit_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        edit_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(self.tr("Favorite name"))
        edit_form.addRow(self._field_label(self.tr("Name:")), self._name_edit)

        self._description_edit = QTextEdit()
        self._description_edit.setAcceptRichText(False)
        # 3 lines high (a longer text scrolls inside): the whole tab stays on one screen
        self._description_edit.setFixedHeight(self._lines_height(self._description_edit, 3))
        self._description_edit.setPlaceholderText(self.tr("Description (auto-generated, editable)"))
        edit_form.addRow(self._field_label(self.tr("Description:")), self._description_edit)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText(
            self.tr("Enter tags separated by commas (e.g., urban, population, 2024)")
        )
        self._tags_edit.setToolTip(
            self.tr("Tags help organize and search favorites.\nSeparate multiple tags with commas.")
        )
        edit_form.addRow(self._field_label(self.tr("Tags:")), self._tags_edit)
        content_layout.addLayout(edit_form)

        # "Used 3 times · created 24/11/2026"
        self._usage_label = QLabel("-")
        self._usage_label.setObjectName("infoLabel")
        self._usage_label.setWordWrap(True)
        content_layout.addWidget(self._usage_label)
        content_layout.addStretch()

        scroll.setWidget(content)
        tab_layout.addWidget(scroll)
        return summary_tab

    @staticmethod
    def _field_label(text: str) -> "QLabel":
        """Muted label of a form row, the same as the summary labels."""
        label = QLabel(text)
        label.setObjectName("summaryKey")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        return label

    @staticmethod
    def _lines_height(edit: "QTextEdit", lines: int) -> int:
        """Height of ``lines`` text lines in ``edit`` (its padding and frame included)."""
        return int(edit.fontMetrics().lineSpacing() * lines) + 24

    def _create_remote_tab(self) -> QWidget:
        """Create the Layers tab: the remote layers the favorite filters."""
        remote_tab = QWidget(self)
        remote_layout = QVBoxLayout(remote_tab)
        remote_layout.setContentsMargins(12, 12, 12, 12)
        remote_layout.setSpacing(8)

        self._remote_table = QTableWidget(0, 3)
        self._remote_table.setHorizontalHeaderLabels(
            [self.tr("Layer"), self.tr("Features"), self.tr("Expression")]
        )
        self._remote_table.verticalHeader().setVisible(False)
        # Rows grow with the wrapped expression and follow the column width
        self._remote_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._remote_table.setWordWrap(True)
        self._remote_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._remote_table.setShowGrid(False)
        self._remote_table.setAlternatingRowColors(True)
        self._remote_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._remote_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._remote_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header = self._remote_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        remote_layout.addWidget(self._remote_table)

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

        self._apply_btn = self._icon_button(self.tr("Apply"), "/mActionFilter2.svg")
        self._apply_btn.setObjectName("applyBtn")
        self._apply_btn.setEnabled(False)
        self._apply_btn.setToolTip(self.tr("Apply this favorite filter to the project"))
        self._apply_btn.clicked.connect(self._on_apply)

        self._save_btn = self._icon_button(self.tr("Save Changes"), "/mActionFileSave.svg")
        self._save_btn.setObjectName("saveBtn")
        self._save_btn.setEnabled(False)
        self._save_btn.setToolTip(self.tr("Save modifications to this favorite"))
        self._save_btn.clicked.connect(self._on_save)

        self._delete_btn = self._icon_button(self.tr("Delete"), "/mActionDeleteSelected.svg")
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

        # Pre-resolve identity once — avoids a per-item cascade
        # lookup that would otherwise fire for every favorite.
        current_user = self._resolve_current_user()

        for fav in favorites_to_show:
            kind = self._scope_kind(fav, current_user)
            # The scope is the icon (globe: all projects, star: this project);
            # the text is the name.
            item = QListWidgetItem(fav.name)
            is_global = fav.id in self._global_ids or kind in _GLOBAL_SCOPE_KINDS
            scope_icon = render_icon("projection" if is_global else "star", self._dark)
            if scope_icon is not None:
                item.setIcon(scope_icon)
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

    def _on_sort_changed(self, _index: int = 0):
        """Refresh the list when the sort combo changes."""
        self._refresh_filtered_list()

    def _current_sort_key(self) -> str:
        """Key of the sort combo entry (defaults to the name)."""
        combo = getattr(self, "_sort_combo", None)
        data = combo.currentData() if combo is not None else None
        return str(data) if data else SORT_NAME

    def _refresh_filtered_list(self):
        """Recompute and repopulate the list from search × scope state.

        Ordering matters: we filter by scope first (cheap attribute check
        in-memory), then apply the text search on the narrowed subset so
        ``search_favorites()`` doesn't re-walk every row.
        """
        if not self._favorites_service:
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

        self._populate_list(sorted_favorites(visible, self._current_sort_key()))
        self._select_favorite(self._current_fav_id, notify=False)

        total = len(self._all_favorites)
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

        def _kind(fav):
            return self._scope_kind(fav, current_user)

        # "shared_*" scopes: owner IS NULL × project dimension
        # "mine_*" scopes: owner == me × project dimension
        # "foreign" never matches a filter entry — always only visible in ALL.
        wanted = _SCOPE_KEY_KINDS.get(scope_key, scope_key)
        return [f for f in favorites if _kind(f) == wanted]

    def _resolve_current_user(self):
        """Pull the current user identity from the manager (cached)."""
        mgr = self._favorites_service
        if mgr is None:
            return None
        getter = getattr(mgr, "get_current_user", None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                return None
        return None

    def _scope_kind(self, fav, current_user=None) -> str:
        """Scope kind of ``fav`` (see ``_favorite_scope_kind``).

        A favorite of the global list is of the global project whatever the
        project the manager is pinned to.
        """
        try:
            from ...core.domain.favorites_manager import GLOBAL_PROJECT_UUID
        except Exception:
            GLOBAL_PROJECT_UUID = "00000000-0000-0000-0000-000000000000"
        if fav.id in self._global_ids:
            project_uuid = GLOBAL_PROJECT_UUID
        else:
            project_uuid = getattr(self._favorites_service, "_project_uuid", None)
        return _favorite_scope_kind(fav, current_user, project_uuid, GLOBAL_PROJECT_UUID)

    def _favorite_is_global(self, fav) -> bool:
        """True when ``fav`` applies to every project of this computer."""
        return (
            fav.id in self._global_ids
            or self._scope_kind(fav, self._resolve_current_user()) in _GLOBAL_SCOPE_KINDS
        )

    def _load_favorites(self) -> list:
        """The project favorites then the global ones; remembers which are global."""
        service = self._favorites_service
        if not service:
            self._global_ids = set()
            return []
        favorites = list(service.get_all_favorites())
        known = {fav.id for fav in favorites}
        global_favorites = [fav for fav in service.get_global_favorites() if fav.id not in known]
        self._global_ids = {fav.id for fav in global_favorites}
        return favorites + global_favorites

    def _find_favorite(self, fav_id):
        """The favorite of this id among the project and global ones, None when gone."""
        if fav_id in self._global_ids:
            return next((fav for fav in self._all_favorites if fav.id == fav_id), None)
        return self._favorites_service.get_favorite(fav_id) if self._favorites_service else None

    def _select_favorite(self, fav_id, notify: bool = True) -> bool:
        """Select the row of ``fav_id``; False when it is not listed.

        With ``notify`` False the details panel is left as it is (an edit in
        progress stays), only the highlighted row follows.
        """
        if not fav_id:
            return False
        for row in range(self._list_widget.count()):
            if self._list_widget.item(row).data(Qt.ItemDataRole.UserRole) == fav_id:
                if notify:
                    self._list_widget.setCurrentRow(row)
                else:
                    self._list_widget.blockSignals(True)
                    try:
                        self._list_widget.setCurrentRow(row)
                    finally:
                        self._list_widget.blockSignals(False)
                return True
        return False

    def _clear_summary_rows(self) -> None:
        """Remove the read-only rows of the Summary tab."""
        while self._summary_form.rowCount():
            self._summary_form.removeRow(0)

    def _show_summary_rows(self, fav) -> None:
        """Rebuild the read-only rows (Filter / Then / Spatial / Tags) of ``fav``."""
        self._clear_summary_rows()
        for label, text in summary_rows(fav, self.tr):
            key = self._field_label(label)
            # An expression wraps in a read-only view, every other value in a plain label;
            # neither is altered, so a selection copies exactly what is stored.
            value = ExpressionView(text, MONO_FAMILY) if label == self.tr("Filter") else text_value(text)
            self._summary_form.addRow(key, value)

    def _on_selection_changed(self):
        """Handle selection change in list."""
        item = self._list_widget.currentItem()
        if not item or not self._favorites_service:
            return

        fav_id = item.data(Qt.ItemDataRole.UserRole)
        fav = self._find_favorite(fav_id)

        if not fav:
            return

        self._current_fav_id = fav_id
        # A global favorite is read-only here (apply, copy and delete only)
        editable = fav_id not in self._global_ids
        for field in (self._name_edit, self._description_edit, self._tags_edit):
            field.setEnabled(editable)

        # Summary tab
        self._scope_badge_label.setText(scope_badge(self._favorite_is_global(fav), self.tr))
        self._show_summary_rows(fav)
        self._name_edit.setText(fav.name)
        self._description_edit.setText(fav.description or "")
        self._tags_edit.setText(", ".join(fav.tags) if fav.tags else "")
        self._usage_label.setText(self._usage_text(fav))

        # Layers tab
        self._remote_table.setRowCount(0)
        if fav.remote_layers and len(fav.remote_layers) > 0:
            self._no_remote_label.hide()
            self._remote_table.show()

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
                shown = expr if len(expr) <= _REMOTE_EXPRESSION_CHARS else expr[:_REMOTE_EXPRESSION_CHARS] + "…"
                row = self._remote_table.rowCount()
                self._remote_table.insertRow(row)
                cells = [
                    QTableWidgetItem(display),
                    QTableWidgetItem(str(feature_count)),
                    QTableWidgetItem(shown),
                ]
                # The full expression (and the layer signature) in the tooltip
                tooltip = expr
                if signature and signature != display:
                    tooltip = f"[{signature}]\n{expr}" if expr else f"[{signature}]"
                cells[0].setToolTip(signature or display)
                cells[2].setToolTip(tooltip)
                for column, cell in enumerate(cells):
                    self._remote_table.setItem(row, column, cell)

            self._tab_widget.setTabText(
                1, self.tr("Layers ({0})").format(len(fav.remote_layers))
            )
        else:
            self._remote_table.hide()
            self._no_remote_label.show()
            self._tab_widget.setTabText(1, self.tr("Layers"))

        # Enable buttons
        self._apply_btn.setEnabled(True)
        self._save_btn.setEnabled(editable)
        self._delete_btn.setEnabled(True)

    def _usage_text(self, fav) -> str:
        """'Used 3 times · created 24/11/2026'."""
        created = self.tr("created {0}").format(date_text(fav.created_at))
        return f"{use_text(fav.use_count, getattr(fav, 'last_used_at', None), self.tr)} · {created}"

    def _on_apply(self):
        """Apply selected favorite."""
        self._apply_favorite(self._current_fav_id)

    def _apply_favorite(self, fav_id) -> None:
        """Ask for ``fav_id`` to be applied (the signal depends on its scope), then close."""
        if not fav_id:
            return
        if fav_id in self._global_ids:
            self.globalFavoriteApplied.emit(fav_id)
        else:
            self.favoriteApplied.emit(fav_id)
        self.accept()

    def _on_item_double_clicked(self, item) -> None:
        """Double-click on a row applies its favorite."""
        self._apply_favorite(item.data(Qt.ItemDataRole.UserRole))

    def _on_list_context_menu(self, pos) -> None:
        """Context menu of a row: apply, rename, duplicate, delete, copy to global/project."""
        item = self._list_widget.itemAt(pos)
        if item is None:
            return
        self._list_widget.setCurrentItem(item)
        menu = self._build_context_menu(item.data(Qt.ItemDataRole.UserRole))
        menu.exec(self._list_widget.viewport().mapToGlobal(pos))

    def _build_context_menu(self, fav_id) -> "QMenu":
        """Menu of the favorite ``fav_id``; a global one cannot be renamed or duplicated."""
        is_global = fav_id in self._global_ids
        menu = QMenu(self)
        menu.addAction(self.tr("Apply")).triggered.connect(lambda: self._apply_favorite(fav_id))
        rename = menu.addAction(self.tr("Rename"))
        rename.setEnabled(not is_global)
        rename.triggered.connect(self._focus_name_edit)
        duplicate = menu.addAction(self.tr("Duplicate"))
        duplicate.setEnabled(not is_global)
        duplicate.triggered.connect(lambda: self._duplicate_favorite(fav_id))
        menu.addSeparator()
        menu.addAction(self.tr("Delete")).triggered.connect(self._on_delete)
        menu.addSeparator()
        if is_global:
            menu.addAction(self.tr("Copy to project")).triggered.connect(
                lambda: self._copy_to_project(fav_id)
            )
        else:
            menu.addAction(self.tr("Copy to global")).triggered.connect(
                lambda: self._copy_to_global(fav_id)
            )
        return menu

    def _focus_name_edit(self) -> None:
        """Rename: show the Summary tab with the Name field focused and selected."""
        self._tab_widget.setCurrentIndex(0)
        self._name_edit.setFocus()
        self._name_edit.selectAll()

    def _duplicate_favorite(self, fav_id) -> None:
        """Add a copy of the project favorite ``fav_id`` named '<name> (copy)' and select it."""
        fav = self._find_favorite(fav_id)
        if fav is None or fav_id in self._global_ids:
            return
        new_id = self._favorites_service.add_favorite(
            name=self.tr("{0} (copy)").format(fav.name),
            expression=fav.expression,
            layer_name=fav.layer_name,
            layer_id=fav.layer_id,
            layer_provider=fav.layer_provider,
            spatial_config=copy.deepcopy(fav.spatial_config),
            remote_layers=copy.deepcopy(fav.remote_layers),
            tags=list(fav.tags or []),
            description=fav.description or "",
        )
        if not new_id:
            self._show_error(self.tr("Could not duplicate '{0}'.").format(fav.name))
            return
        self._after_list_change(new_id)

    def _copy_to_global(self, fav_id) -> None:
        """Copy the project favorite ``fav_id`` to the global favorites and select the copy."""
        fav = self._find_favorite(fav_id)
        if fav is None or fav_id in self._global_ids:
            return
        from ...core.domain.exceptions import FavoritePersistenceError
        try:
            new_id = self._favorites_service.copy_to_global(fav_id)
        except FavoritePersistenceError as e:
            self._show_error(self.tr("Could not copy to global: {0}").format(e.__cause__ or e))
            return
        if not new_id:
            self._show_error(self.tr("Could not copy '{0}' to the global favorites.").format(fav.name))
            return
        self._after_list_change(new_id)

    def _copy_to_project(self, fav_id) -> None:
        """Copy the global favorite ``fav_id`` to this project and select the copy.

        A project favorite with the same name and expression is reused, as when
        the global favorite is applied.
        """
        fav = self._find_favorite(fav_id)
        if fav is None or fav_id not in self._global_ids:
            return
        from ...core.domain.exceptions import FavoritePersistenceError
        from ...core.domain.global_favorite_copy import project_copy_of_global
        existing = project_copy_of_global(fav, self._favorites_service.get_all_favorites())
        if existing is not None:
            self._select_favorite(existing.id)
            return
        try:
            new_id = self._favorites_service.import_global_to_project(fav_id)
        except FavoritePersistenceError as e:
            self._show_error(self.tr("Could not copy to project: {0}").format(e.__cause__ or e))
            return
        if not new_id:
            self._show_error(self.tr("Could not copy '{0}' to this project.").format(fav.name))
            return
        self._after_list_change(new_id)

    def _after_list_change(self, select_id) -> None:
        """Reload the list after a favorite was added, select ``select_id``, tell the owner."""
        self.refresh()
        self._select_favorite(select_id)
        self.favoritesChanged.emit()

    def _on_save(self):
        """Save changes to selected favorite."""
        if not self._current_fav_id or not self._favorites_service:
            return
        if self._current_fav_id in self._global_ids:  # read-only here
            return

        new_name = self._name_edit.text().strip()
        new_desc = self._description_edit.toPlainText().strip()
        new_tags = [
            tag.strip() for tag in self._tags_edit.text().split(',')
            if tag.strip()
        ]

        if new_name:
            # F16 phase 4 lazy import: keeps this module importable in
            # tests that lack the 3-level package nesting needed by a
            # top-level ``from ...core.domain.exceptions`` statement.
            from ...core.domain.exceptions import FavoritePersistenceError
            # FIX 2026-04-22: suppress re-entrant external refresh triggered by
            # the manager's own favorites_changed emission.
            self._suppress_external_refresh = True
            try:
                self._favorites_service.update_favorite(
                    self._current_fav_id,
                    name=new_name,
                    description=new_desc,
                    tags=new_tags,
                )
                self._favorites_service.save()
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
            self._all_favorites = self._load_favorites()
            # v5.1: re-render the list via the unified refresh so the
            # scope badge reflects the freshly-persisted owner. The
            # manual per-item text edit we used to do was out of sync
            # with the new badge prefix and lost the current scope filter.
            self._refresh_filtered_list()
            # The refresh already highlighted the saved row without notifying
            # (an edit in progress stays on an external change); here the edit is
            # saved, so rebuild the details from the stored favorite.
            self._on_selection_changed()

            self.favoriteUpdated.emit(self._current_fav_id)
            self.favoritesChanged.emit()
            logger.info(f"Favorite updated: {new_name}")

    def _on_delete(self):
        """Delete selected favorite."""
        if not self._current_fav_id or not self._favorites_service:
            return

        fav = self._find_favorite(self._current_fav_id)
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
        is_global = deleted_id in self._global_ids
        # F16 phase 4 lazy import — see _on_save for rationale.
        from ...core.domain.exceptions import FavoritePersistenceError
        # FIX 2026-04-22: suppress re-entrant external refresh from manager's
        # own favorites_changed emission during delete + save.
        self._suppress_external_refresh = True
        try:
            if is_global:
                removed = self._favorites_service.remove_global_favorite(deleted_id)
            else:
                removed = self._favorites_service.remove_favorite(deleted_id)
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

        self._global_ids.discard(deleted_id)
        self._header_label.setText(
            self.tr("<b>Saved Favorites ({0})</b>").format(len(self._all_favorites))
        )

        # Save changes
        self._favorites_service.save()

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
        # Summary tab
        self._scope_badge_label.setText("")
        self._clear_summary_rows()
        self._name_edit.clear()
        self._description_edit.clear()
        self._tags_edit.clear()
        for field in (self._name_edit, self._description_edit, self._tags_edit):
            field.setEnabled(True)
        self._usage_label.setText("-")

        # Layers tab
        self._remote_table.setRowCount(0)
        self._no_remote_label.show()
        self._remote_table.hide()
        self._tab_widget.setTabText(1, self.tr("Layers"))

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
        if not self._is_sharing_active() or self._favorites_service is None:
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
        if not self._is_sharing_active() or self._favorites_service is None:
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
        self._all_favorites = self._load_favorites()
        if not self._favorites_service:
            self._populate_list(self._all_favorites)
            self._header_label.setText(self.tr("<b>Saved Favorites (0)</b>"))
            return
        self._refresh_filtered_list()

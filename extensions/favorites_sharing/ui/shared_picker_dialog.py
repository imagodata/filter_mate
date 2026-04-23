# -*- coding: utf-8 -*-
"""
Shared Favorites picker dialog.

Lists favorites discovered from Resource Sharing collections and lets
the user Fork one into the current project's DB. Fully optional UI —
only loaded when the favorites_sharing extension is active.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

try:
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
        QListWidgetItem, QPushButton, QTextEdit, QLineEdit, QSplitter,
        QWidget, QInputDialog, QMessageBox,
    )
    HAS_QT = True
except ImportError:  # pragma: no cover
    HAS_QT = False

from ..scanner import SharedFavorite
from ..service import FavoritesSharingService

logger = logging.getLogger('FilterMate.FavoritesSharing.UI')


class SharedFavoritesPickerDialog(QDialog if HAS_QT else object):
    """Minimal picker — list on the left, details on the right, Fork at the bottom."""

    def __init__(
        self,
        service: FavoritesSharingService,
        favorites_service: Any,
        parent=None,
    ):
        if HAS_QT:
            super().__init__(parent)
        self._sharing_service = service
        self._favorites_service = favorites_service
        self._items: List[SharedFavorite] = []
        self._current: Optional[SharedFavorite] = None

        if HAS_QT:
            self._setup_ui()
            self._refresh()

    # ─── UI ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle(self.tr("FilterMate — Shared Favorites"))
        self.setMinimumSize(680, 480)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QLabel(self.tr(
            "<b>Shared Favorites</b> — discovered from QGIS Resource Sharing collections"
        ))
        root.addWidget(header)

        self._summary_label = QLabel()
        self._summary_label.setWordWrap(True)
        root.addWidget(self._summary_label)

        # Search
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("🔍"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(
            self.tr("Search by name, description, collection, or tags...")
        )
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self._search_edit)
        root.addLayout(search_row)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._list_widget = QListWidget()
        self._list_widget.setMinimumWidth(220)
        self._list_widget.currentItemChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._list_widget)

        details = QWidget()
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(8, 0, 0, 0)
        details_layout.setSpacing(6)

        self._details_header = QLabel(self.tr("Select a shared favorite to preview."))
        self._details_header.setWordWrap(True)
        details_layout.addWidget(self._details_header)

        self._details_body = QTextEdit()
        self._details_body.setReadOnly(True)
        details_layout.addWidget(self._details_body, 1)

        splitter.addWidget(details)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, 1)

        # Actions
        actions_row = QHBoxLayout()
        actions_row.addStretch()
        self._refresh_btn = QPushButton("🔄 " + self.tr("Rescan"))
        self._refresh_btn.clicked.connect(self._on_rescan_clicked)
        actions_row.addWidget(self._refresh_btn)

        self._fork_btn = QPushButton("⑂ " + self.tr("Fork to my project"))
        self._fork_btn.setEnabled(False)
        self._fork_btn.setDefault(True)
        self._fork_btn.clicked.connect(self._on_fork_clicked)
        actions_row.addWidget(self._fork_btn)

        close_btn = QPushButton(self.tr("Close"))
        close_btn.clicked.connect(self.reject)
        actions_row.addWidget(close_btn)
        root.addLayout(actions_row)

    # ─── Data wiring ──────────────────────────────────────────────────

    def _refresh(self) -> None:
        self._items = self._sharing_service.list_shared()
        self._populate_list(self._items)
        self._update_summary()

    def _update_summary(self) -> None:
        summary = self._sharing_service.collections_summary()
        if not summary:
            self._summary_label.setText(self.tr(
                "No shared collections found. Subscribe to a Resource Sharing "
                "repository that ships a <code>filter_mate/favorites</code> folder, "
                "or drop a <code>.fmfav.json</code> bundle in your resource_sharing "
                "collections directory."
            ))
        else:
            parts = [f"<b>{name}</b> ({count})" for name, count in summary.items()]
            self._summary_label.setText(
                self.tr("{0} favorite(s) across {1} collection(s): {2}").format(
                    sum(summary.values()), len(summary), ", ".join(parts)
                )
            )

    def _populate_list(self, items: List[SharedFavorite]) -> None:
        self._list_widget.clear()
        for fav in items:
            entry = QListWidgetItem(f"★ {fav.name}")
            entry.setData(Qt.ItemDataRole.UserRole, fav)
            tooltip_parts = [
                fav.name,
                self.tr("Collection: {0}").format(fav.source.collection_name),
            ]
            if fav.description:
                tooltip_parts.append(fav.description)
            entry.setToolTip("\n".join(tooltip_parts))
            self._list_widget.addItem(entry)

        if self._list_widget.count() > 0:
            self._list_widget.setCurrentRow(0)
        else:
            self._current = None
            self._fork_btn.setEnabled(False)
            self._details_header.setText(self.tr("No shared favorites match your search."))
            self._details_body.clear()

    def _on_search_changed(self, text: str) -> None:
        filtered = self._sharing_service.list_shared(search_query=text)
        self._populate_list(filtered)

    def _on_selection_changed(self) -> None:
        item = self._list_widget.currentItem()
        if item is None:
            self._current = None
            self._fork_btn.setEnabled(False)
            return

        shared = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(shared, SharedFavorite):
            self._current = None
            self._fork_btn.setEnabled(False)
            return

        self._current = shared
        self._fork_btn.setEnabled(True)
        self._details_header.setText(
            self.tr("<b>{0}</b> — from <i>{1}</i>").format(
                shared.name, shared.source.collection_name
            )
        )

        payload = shared.payload
        lines = []
        description = payload.get('description')
        if description:
            lines.append(str(description))
            lines.append("")

        expression = payload.get('expression') or ""
        lines.append(self.tr("<b>Expression</b>"))
        lines.append(f"<pre>{expression}</pre>")

        remote = payload.get('remote_layers') or {}
        if isinstance(remote, dict) and remote:
            lines.append(self.tr("<b>Remote layers</b>"))
            bullets = []
            for key, entry in remote.items():
                if isinstance(entry, dict):
                    display = entry.get('display_name') or key
                    sig = entry.get('layer_signature') or key
                    bullets.append(f"• <b>{display}</b> <code>[{sig}]</code>")
                else:
                    bullets.append(f"• {key}")
            lines.append("<br>".join(bullets))

        tags = payload.get('tags') or []
        if isinstance(tags, list) and tags:
            lines.append("")
            lines.append(self.tr("<b>Tags:</b> {0}").format(", ".join(str(t) for t in tags)))

        meta = shared.source.collection_metadata or {}
        author = meta.get('author')
        license_ = meta.get('license')
        if author or license_:
            lines.append("")
            lines.append(self.tr("<b>Provenance</b>"))
            if author:
                lines.append(self.tr("Author: {0}").format(author))
            if license_:
                lines.append(self.tr("License: {0}").format(license_))

        self._details_body.setHtml("<br>".join(lines))

    # ─── Actions ───────────────────────────────────────────────────────

    def _on_rescan_clicked(self) -> None:
        self._sharing_service.invalidate_cache()
        self._refresh()

    def _on_fork_clicked(self) -> None:
        if self._current is None or self._favorites_service is None:
            return

        current = self._current
        default_name = current.name
        proposed, ok = QInputDialog.getText(
            self,
            self.tr("Fork shared favorite"),
            self.tr("Name in your project:"),
            text=default_name,
        )
        if not ok:
            return
        proposed = (proposed or "").strip() or default_name

        new_id = self._sharing_service.fork(
            current, self._favorites_service, override_name=proposed,
        )
        if new_id:
            QMessageBox.information(
                self,
                self.tr("Fork successful"),
                self.tr("'{0}' was added to your favorites.").format(proposed),
            )
        else:
            QMessageBox.warning(
                self,
                self.tr("Fork failed"),
                self.tr("Could not add the shared favorite to your project."),
            )

    # ─── Translation helper ────────────────────────────────────────────

    def tr(self, message: str) -> str:  # type: ignore[override]
        try:
            from qgis.PyQt.QtCore import QCoreApplication
            return QCoreApplication.translate('SharedFavoritesPickerDialog', message)
        except Exception:
            return message

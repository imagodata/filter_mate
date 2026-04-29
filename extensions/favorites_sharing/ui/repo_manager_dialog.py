# -*- coding: utf-8 -*-
"""
Repo manager UI — Add / Edit / Delete / Test FilterMate remote repos.

Two dialogs:

* :class:`RepoEditDialog` — single-entry editor with typed fields and a
  ``QgsAuthConfigSelect`` widget so credentials never round-trip through
  ``config.json`` in plain text.

* :class:`RepoManagerDialog` — table of all configured repos with the
  CRUD buttons. Persists changes via
  :meth:`RemoteRepoManager.save_repos`.

Both dialogs are imported lazily from the JsonView context-menu action
(``Manage repos…``) so the import cost is paid only when the user opens
them.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

try:
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtWidgets import (
        QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox,
        QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
        QLineEdit, QMessageBox, QPushButton, QTableWidget,
        QTableWidgetItem, QVBoxLayout, QWidget,
    )
    HAS_QT = True
except ImportError:  # pragma: no cover - headless test env
    HAS_QT = False

try:
    from qgis.gui import QgsAuthConfigSelect  # type: ignore
    HAS_AUTH_SELECT = True
except ImportError:  # pragma: no cover - standalone
    HAS_AUTH_SELECT = False

from ..git_resolver import GitSource, resolve_for_extension
from ..remote_repo_manager import RemoteRepo, RemoteRepoManager

logger = logging.getLogger('FilterMate.FavoritesSharing.UI.RepoManager')


def _tr(message: str) -> str:
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('FilterMateRepoManager', message)
    except Exception:
        return message


class RepoEditDialog(QDialog if HAS_QT else object):
    """Single-repo editor.

    Constructed with an existing :class:`RemoteRepo` (to edit) or
    ``None`` (to add a new one). On accept, :meth:`get_repo` returns
    the new state.
    """

    def __init__(
        self,
        repo: Optional[RemoteRepo] = None,
        existing_names: Optional[List[str]] = None,
        manager: Optional[RemoteRepoManager] = None,
        parent=None,
    ):
        if HAS_QT:
            super().__init__(parent)
        self._original = repo
        self._existing_names = set(n for n in (existing_names or []) if n)
        self._manager = manager
        # H5: holds the QThread driving Test connection so it survives the
        # method call that spawned it. Set to None until the user clicks
        # Test for the first time.
        self._test_worker = None
        if HAS_QT:
            self._setup_ui()
            self._populate_from_repo(repo)

    # ─── UI ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle(_tr("Edit Remote Repo")
                            if self._original else _tr("Add Remote Repo"))
        self.setMinimumWidth(540)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        intro = QLabel(_tr(
            "Configure a git-backed publish target. Anonymous repos can "
            "leave Authentication empty — only publishers need credentials."
        ))
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #666;")
        root.addWidget(intro)

        form = QFormLayout()
        form.setSpacing(6)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(_tr("Display name (e.g. Acme team)"))
        form.addRow(_tr("Name *:"), self._name_edit)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText(_tr("https://github.com/org/repo.git"))
        form.addRow(_tr("Git URL:"), self._url_edit)

        self._branch_edit = QLineEdit()
        self._branch_edit.setPlaceholderText(_tr("main / master / … (empty = default)"))
        form.addRow(_tr("Branch:"), self._branch_edit)

        clone_row = QHBoxLayout()
        self._clone_edit = QLineEdit()
        self._clone_edit.setPlaceholderText(_tr(
            "Empty = [profile]/FilterMate/repos/<slug>"
        ))
        clone_row.addWidget(self._clone_edit, 1)
        browse = QPushButton("…")
        browse.setFixedWidth(32)
        browse.clicked.connect(self._on_browse_clone)
        clone_row.addWidget(browse)
        form.addRow(_tr("Local clone:"), clone_row)

        self._target_collection_edit = QLineEdit()
        self._target_collection_edit.setPlaceholderText(_tr(
            "Sub-directory under collections/ (empty = repo root)"
        ))
        form.addRow(_tr("Collection:"), self._target_collection_edit)

        # Auth row — prefer the native QGIS Auth Config selector when
        # available (gives the user access to the full create-edit-delete
        # auth manager UI in one click).
        if HAS_AUTH_SELECT:
            self._auth_widget: QWidget = QgsAuthConfigSelect()
            form.addRow(_tr("Authentication:"), self._auth_widget)
        else:
            # Headless / very old QGIS: fall back to a plain text field
            # for the authcfg_id. Users can still type a known id manually.
            self._auth_widget = QLineEdit()
            self._auth_widget.setPlaceholderText(_tr(
                "QGIS authcfg_id (Settings → Options → Authentication)"
            ))
            form.addRow(_tr("Auth config id:"), self._auth_widget)

        self._default_check = QCheckBox(_tr(
            "Use as default publish target"
        ))
        form.addRow("", self._default_check)

        root.addLayout(form)

        # Test connection row
        test_row = QHBoxLayout()
        self._test_btn = QPushButton("🔌 " + _tr("Test connection"))
        self._test_btn.clicked.connect(self._on_test_connection)
        test_row.addWidget(self._test_btn)
        self._test_status_label = QLabel("")
        self._test_status_label.setWordWrap(True)
        test_row.addWidget(self._test_status_label, 1)
        root.addLayout(test_row)

        # Buttons
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        root.addWidget(self._button_box)

    # ─── State <-> widgets ─────────────────────────────────────────────

    def _populate_from_repo(self, repo: Optional[RemoteRepo]) -> None:
        if repo is None:
            return
        self._name_edit.setText(repo.name)
        self._url_edit.setText(repo.git_url)
        self._branch_edit.setText(repo.branch)
        self._clone_edit.setText(repo.local_clone)
        self._target_collection_edit.setText(repo.target_collection)
        self._default_check.setChecked(repo.is_default)
        self._set_auth_id(repo.authcfg_id)

    def _set_auth_id(self, authcfg_id: str) -> None:
        if HAS_AUTH_SELECT and isinstance(self._auth_widget, QgsAuthConfigSelect):
            try:
                self._auth_widget.setConfigId(authcfg_id or "")
            except Exception:
                logger.debug("setConfigId failed", exc_info=True)
        elif isinstance(self._auth_widget, QLineEdit):
            self._auth_widget.setText(authcfg_id or "")

    def _get_auth_id(self) -> str:
        if HAS_AUTH_SELECT and isinstance(self._auth_widget, QgsAuthConfigSelect):
            try:
                return self._auth_widget.configId() or ""
            except Exception:
                return ""
        if isinstance(self._auth_widget, QLineEdit):
            return self._auth_widget.text().strip()
        return ""

    def get_repo(self) -> Optional[RemoteRepo]:
        """Return the validated RemoteRepo, or None when invalid."""
        name = self._name_edit.text().strip()
        if not name:
            return None
        return RemoteRepo(
            name=name,
            git_url=self._url_edit.text().strip(),
            branch=self._branch_edit.text().strip(),
            local_clone=self._clone_edit.text().strip(),
            target_collection=self._target_collection_edit.text().strip(),
            is_default=self._default_check.isChecked(),
            authcfg_id=self._get_auth_id(),
            # Carry the legacy header through unmodified so the manager
            # can decide to drop it on save (when authcfg_id is set).
            auth_header=(self._original.auth_header if self._original else ""),
            extra=(dict(self._original.extra) if self._original else {}),
        )

    # ─── Actions ───────────────────────────────────────────────────────

    def _on_browse_clone(self) -> None:
        start = self._clone_edit.text().strip() or os.path.expanduser("~")
        directory = QFileDialog.getExistingDirectory(
            self, _tr("Choose local clone directory"), start,
        )
        if directory:
            self._clone_edit.setText(directory)

    def _on_test_connection(self) -> None:
        if self._manager is None:
            self._test_status_label.setText(
                "<span style='color:#c33;'>"
                + _tr("No manager wired — cannot test.")
                + "</span>"
            )
            return
        repo = self.get_repo()
        if repo is None or not repo.name:
            self._test_status_label.setText(
                "<span style='color:#c33;'>"
                + _tr("Set a name first.") + "</span>"
            )
            return
        # H5 (audit 2026-04-27): ``test_connection`` runs ``git ls-remote``
        # which can hang up to ``timeout_seconds`` (15s here) on an
        # unreachable remote. Run it on a worker so the dialog stays
        # responsive — the user can keep editing fields while the probe
        # is in flight, and the result is rendered into the status label
        # whenever it lands.
        from .git_worker import start_git_worker

        self._test_status_label.setText(_tr("Testing…"))
        self._test_btn.setEnabled(False)

        def _probe():
            return self._manager.test_connection(repo)

        def _on_finished(result):
            self._test_btn.setEnabled(True)
            if result.success:
                if result.skipped_push_reason == "no_remote":
                    msg = _tr("OK — local-only target (path is writable).")
                else:
                    msg = _tr("OK — remote reachable.")
                self._test_status_label.setText(
                    f"<span style='color:#3a3;'>✔ {msg}</span>"
                )
            else:
                self._test_status_label.setText(
                    f"<span style='color:#c33;'>✗ {result.error_message}</span>"
                )

        def _on_error(msg):
            self._test_btn.setEnabled(True)
            self._test_status_label.setText(
                f"<span style='color:#c33;'>✗ {msg}</span>"
            )

        # Strong ref on self so the QThread is not GC'd before it runs;
        # the helper handles parent=None + deleteLater self-cleanup.
        self._test_worker = start_git_worker(_probe, _on_finished, _on_error)

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, _tr("Missing name"),
                                _tr("A repo name is required."))
            return
        # Conflict check (only for new entries / renamed entries)
        original_name = self._original.name if self._original else None
        if name != original_name and name in self._existing_names:
            QMessageBox.warning(
                self, _tr("Duplicate name"),
                _tr("A repo named '{0}' already exists.").format(name),
            )
            return
        self.accept()

    def closeEvent(self, event):  # type: ignore[override]
        """Wait for an in-flight Test connection worker before tearing down.

        ``ls-remote`` can hang up to ``timeout_seconds`` (15s) on an
        unreachable remote — terminating the QThread would orphan the git
        subprocess, so we wait via :func:`gracefully_close_worker`.
        """
        from .git_worker import gracefully_close_worker
        gracefully_close_worker(self._test_worker, timeout_ms=20_000)
        super().closeEvent(event)


class RepoManagerDialog(QDialog if HAS_QT else object):
    """Table view of configured repos + CRUD buttons.

    Edits are buffered in-memory; nothing is persisted until the user
    clicks OK (which calls :meth:`RemoteRepoManager.save_repos`).
    """

    _COL_NAME = 0
    _COL_URL = 1
    _COL_BRANCH = 2
    _COL_COLLECTION = 3
    _COL_AUTH = 4
    _COL_STATUS = 5
    _COL_DEFAULT = 6

    def __init__(self, manager: RemoteRepoManager, parent=None):
        if HAS_QT:
            super().__init__(parent)
        self._manager = manager
        self._repos: List[RemoteRepo] = list(manager.list_repos())
        if HAS_QT:
            self._setup_ui()
            self._refresh_table()

    # ─── UI ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle(_tr("FilterMate — Manage Remote Repos"))
        self.setMinimumSize(820, 420)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QLabel(_tr(
            "<b>Remote Repos</b> — git-backed publish targets for favorite "
            "collections. Anonymous read access is supported; only "
            "publishers need credentials."
        ))
        header.setWordWrap(True)
        root.addWidget(header)

        # Git binary status row — surfaces "git not found" before the user
        # gets bitten by it deep inside Test connection / Publish.
        git_row = QHBoxLayout()
        self._git_status_label = QLabel("")
        self._git_status_label.setWordWrap(True)
        git_row.addWidget(self._git_status_label, 1)
        self._git_config_btn = QPushButton("⚙ " + _tr("Configure git…"))
        self._git_config_btn.setToolTip(_tr(
            "Set an explicit git binary path or download Portable Git."
        ))
        self._git_config_btn.clicked.connect(self._on_configure_git)
        git_row.addWidget(self._git_config_btn)
        root.addLayout(git_row)
        self._refresh_git_status()

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            _tr("Name"), _tr("URL"), _tr("Branch"),
            _tr("Collection"), _tr("Auth"), _tr("Status"), _tr("Default"),
        ])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(lambda *_: self._on_edit())
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(self._COL_NAME, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self._COL_URL, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(self._COL_BRANCH, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self._COL_COLLECTION, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self._COL_AUTH, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self._COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self._COL_DEFAULT, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self._table, 1)

        # Action buttons
        actions = QHBoxLayout()
        self._add_btn = QPushButton("➕ " + _tr("Add"))
        self._add_btn.clicked.connect(self._on_add)
        actions.addWidget(self._add_btn)

        self._edit_btn = QPushButton("✏ " + _tr("Edit…"))
        self._edit_btn.clicked.connect(self._on_edit)
        actions.addWidget(self._edit_btn)

        self._del_btn = QPushButton("🗑 " + _tr("Delete"))
        self._del_btn.clicked.connect(self._on_delete)
        actions.addWidget(self._del_btn)

        self._set_default_btn = QPushButton("★ " + _tr("Set as default"))
        self._set_default_btn.clicked.connect(self._on_set_default)
        actions.addWidget(self._set_default_btn)

        actions.addStretch()
        root.addLayout(actions)

        # OK / Cancel
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_save)
        self._button_box.rejected.connect(self.reject)
        root.addWidget(self._button_box)

    # ─── Table refresh ────────────────────────────────────────────────

    def _refresh_table(self) -> None:
        self._table.setRowCount(len(self._repos))
        for row, repo in enumerate(self._repos):
            self._set_cell(row, self._COL_NAME, repo.name)
            self._set_cell(row, self._COL_URL, repo.git_url or "(local-only)")
            self._set_cell(row, self._COL_BRANCH, repo.branch or "(default)")
            self._set_cell(row, self._COL_COLLECTION, repo.target_collection or "(root)")
            self._set_cell(row, self._COL_AUTH, self._auth_label(repo))
            self._set_cell(row, self._COL_STATUS, repo.status_badge())
            self._set_cell(row, self._COL_DEFAULT, "★" if repo.is_default else "")

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, col, item)

    @staticmethod
    def _auth_label(repo: RemoteRepo) -> str:
        if repo.authcfg_id:
            return f"🔐 {repo.authcfg_id}"
        if repo.auth_header:
            return "⚠ plaintext"
        return "—"

    def _selected_index(self) -> int:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return -1
        return rows[0].row()

    # ─── Actions ───────────────────────────────────────────────────────

    def _on_add(self) -> None:
        existing = [r.name for r in self._repos]
        dlg = RepoEditDialog(
            repo=None,
            existing_names=existing,
            manager=self._manager,
            parent=self,
        )
        if dlg.exec():
            new_repo = dlg.get_repo()
            if new_repo is not None:
                self._repos.append(new_repo)
                self._enforce_single_default(new_repo if new_repo.is_default else None)
                self._refresh_table()

    def _on_edit(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        existing = [r.name for r in self._repos]
        dlg = RepoEditDialog(
            repo=self._repos[idx],
            existing_names=existing,
            manager=self._manager,
            parent=self,
        )
        if dlg.exec():
            updated = dlg.get_repo()
            if updated is not None:
                self._repos[idx] = updated
                self._enforce_single_default(updated if updated.is_default else None)
                self._refresh_table()

    def _on_delete(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        name = self._repos[idx].name
        confirm = QMessageBox.question(
            self, _tr("Delete repo"),
            _tr("Remove '{0}' from the configured repos?").format(name),
        )
        if confirm == QMessageBox.StandardButton.Yes:
            del self._repos[idx]
            self._refresh_table()

    def _on_set_default(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        for i, r in enumerate(self._repos):
            r.is_default = (i == idx)
        self._refresh_table()

    def _enforce_single_default(self, winner: Optional[RemoteRepo]) -> None:
        """When ``winner`` is the new default, demote the others."""
        if winner is None:
            return
        for r in self._repos:
            if r is not winner:
                r.is_default = False

    def _on_save(self) -> None:
        if not self._manager.save_repos(self._repos):
            QMessageBox.warning(
                self, _tr("Save failed"),
                _tr("Could not persist repos to FilterMate config. "
                    "Check the QGIS log for details."),
            )
            return
        self.accept()

    # ─── Git binary status / config ────────────────────────────────────

    def _refresh_git_status(self) -> None:
        """Refresh the inline status banner above the repos table.

        Shown labels mirror :class:`GitBinaryConfigDialog` to keep the UI
        coherent. The status is recomputed whenever the user closes the
        config dialog so a fresh portable install lights up immediately.
        """
        ext = getattr(self._manager, "_extension", None)
        if ext is None:
            self._git_status_label.setText("")
            return
        res = resolve_for_extension(ext)
        if res.found:
            label = {
                GitSource.CONFIGURED: _tr("configured path"),
                GitSource.PORTABLE: _tr("portable"),
                GitSource.SYSTEM: _tr("system PATH"),
            }.get(res.source, res.source.value)
            self._git_status_label.setText(
                f"<span style='color:#2a7a2a;'>✔ git ({label})</span> "
                f"<small style='color:#666;'>· {res.binary_path}</small>"
            )
        else:
            self._git_status_label.setText(
                "<span style='color:#c33;'>✗ "
                + _tr("git not found")
                + "</span> "
                + _tr(" — Test connection and Publish will fail until "
                      "this is configured.")
            )

    def _on_configure_git(self) -> None:
        """Open the git binary configuration dialog (lazy import)."""
        ext = getattr(self._manager, "_extension", None)
        if ext is None:
            return
        from .git_binary_dialog import GitBinaryConfigDialog
        dlg = GitBinaryConfigDialog(extension=ext, parent=self)
        dlg.exec()
        # Whether the user closed via Save or Close, the resolution may
        # have changed (path applied, portable downloaded). Re-render so
        # the banner reflects the new state without a manager round-trip.
        self._refresh_git_status()

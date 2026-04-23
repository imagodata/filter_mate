# -*- coding: utf-8 -*-
"""
PublishFavoritesDialog — UI for sharing favorites via Resource Sharing.

The dialog lets the user:
- pick a target collection (existing sub-directory of the Resource
  Sharing ``collections/`` root, or a brand-new one);
- name the bundle file (``<name>.fmfav-pack.json``);
- fill collection-level metadata (name, author, license, description,
  tags, homepage);
- select which favorites to include via multi-select checkboxes.

On OK the dialog delegates to
:meth:`FavoritesSharingService.publish_bundle`.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

try:
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtGui import QIcon
    from qgis.PyQt.QtWidgets import (
        QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
        QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
        QListWidgetItem, QMessageBox, QPushButton, QSplitter, QTextEdit,
        QVBoxLayout, QWidget,
    )
    HAS_QT = True
except ImportError:  # pragma: no cover
    HAS_QT = False

from ..service import CollectionTarget, FavoritesSharingService

logger = logging.getLogger('FilterMate.FavoritesSharing.UI.Publish')


class PublishFavoritesDialog(QDialog if HAS_QT else object):
    """Dialog that builds a v3 favorites bundle and writes it into a
    Resource Sharing collection directory.
    """

    # Sentinel keys in the target combo
    _TARGET_NEW_IN_ROOT = "__NEW_IN_ROOT__"
    _TARGET_CUSTOM_DIR = "__CUSTOM_DIR__"

    def __init__(
        self,
        sharing_service: FavoritesSharingService,
        favorites_service: Any,
        parent=None,
        preselected_ids: Optional[List[str]] = None,
    ):
        if HAS_QT:
            super().__init__(parent)
        self._sharing_service = sharing_service
        self._favorites_service = favorites_service
        self._preselected_ids = set(preselected_ids or [])
        self._targets: List[CollectionTarget] = []
        # Defaults pulled from config — author/license/homepage prefill so
        # publishing repeatedly into the same org doesn't require re-typing.
        self._config_defaults = self._read_config_defaults(sharing_service)

        if HAS_QT:
            self._setup_ui()
            self._refresh_targets()
            self._populate_favorites()
            self._apply_default_metadata_prefill()

    @staticmethod
    def _read_config_defaults(sharing_service: Optional[FavoritesSharingService]) -> dict:
        """Load pre-fill values from FilterMate config.

        Prefers the owning extension's typed accessors (single source of
        truth); falls back to a direct ENV_VARS lookup when the dialog is
        instantiated without an extension (legacy tests).
        """
        defaults = {
            'default_publish_collection': '',
            'default_publish_metadata': {
                'author': '', 'license': '', 'homepage': '',
            },
        }

        extension = getattr(sharing_service, "extension", None)
        if extension is not None:
            try:
                defaults['default_publish_collection'] = (
                    extension.get_default_publish_collection()
                )
                defaults['default_publish_metadata'] = (
                    extension.get_default_publish_metadata()
                )
                return defaults
            except Exception as exc:
                logger.debug("Extension config accessors failed: %s", exc)

        # Fallback — direct ENV_VARS lookup when no extension is available.
        try:
            from filter_mate.config.config import ENV_VARS, _get_option_value
            cfg = (ENV_VARS.get("CONFIG_DATA", {}) or {}) \
                .get("EXTENSIONS", {}) \
                .get("favorites_sharing", {})
            defaults['default_publish_collection'] = str(
                _get_option_value(cfg.get("default_publish_collection"), default="") or ""
            )
            meta = _get_option_value(
                cfg.get("default_publish_metadata"),
                default={'author': '', 'license': '', 'homepage': ''},
            ) or {}
            if isinstance(meta, dict):
                for k in ('author', 'license', 'homepage'):
                    defaults['default_publish_metadata'][k] = str(meta.get(k) or '')
        except Exception:
            pass
        return defaults

    def _apply_default_metadata_prefill(self) -> None:
        """Prefill author / license / homepage fields from config when the
        user hasn't already put something there (existing collection
        metadata still wins — we don't clobber per-collection author).
        """
        meta = self._config_defaults.get('default_publish_metadata') or {}
        if not self._meta_author_edit.text().strip():
            self._meta_author_edit.setText(str(meta.get('author') or ''))
        if not self._meta_license_edit.text().strip():
            self._meta_license_edit.setText(str(meta.get('license') or ''))
        if not self._meta_homepage_edit.text().strip():
            self._meta_homepage_edit.setText(str(meta.get('homepage') or ''))

    # ─── UI ───────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle(self.tr("FilterMate — Publish to Resource Sharing"))
        self.setMinimumSize(680, 560)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QLabel(self.tr(
            "<b>Publish Favorites</b> — write a shareable bundle into a "
            "QGIS Resource Sharing collection."
        ))
        header.setWordWrap(True)
        root.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        splitter.addWidget(self._build_form())
        splitter.addWidget(self._build_favorites_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._overwrite_check = QCheckBox(self.tr("Overwrite existing bundle"))
        self._overwrite_check.setChecked(False)
        btn_row.addWidget(self._overwrite_check)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("📤 " + self.tr("Publish"))
        self._button_box.accepted.connect(self._on_publish)
        self._button_box.rejected.connect(self.reject)
        btn_row.addWidget(self._button_box)

        root.addLayout(btn_row)

    def _build_form(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(8)

        # --- Target selection ---
        target_group = QLabel(self.tr("<b>1. Target collection</b>"))
        layout.addWidget(target_group)

        self._target_combo = QComboBox()
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)
        layout.addWidget(self._target_combo)

        target_row = QHBoxLayout()
        target_row.setSpacing(6)
        self._target_path_label = QLabel()
        self._target_path_label.setWordWrap(True)
        self._target_path_label.setStyleSheet("color: #666; font-size: 9pt;")
        target_row.addWidget(self._target_path_label, 1)
        self._browse_btn = QPushButton("📁 " + self.tr("Browse..."))
        self._browse_btn.clicked.connect(self._on_browse_clicked)
        target_row.addWidget(self._browse_btn)
        layout.addLayout(target_row)

        self._custom_dir: Optional[str] = None

        # --- Bundle filename ---
        layout.addWidget(QLabel(self.tr("<b>2. Bundle file name</b>")))
        self._bundle_name_edit = QLineEdit()
        self._bundle_name_edit.setPlaceholderText(self.tr("e.g. zones_bruxelles"))
        self._bundle_name_edit.setText("favorites")
        layout.addWidget(self._bundle_name_edit)
        layout.addWidget(QLabel(self.tr(
            "<small>→ <code>&lt;target&gt;/filter_mate/favorites/&lt;name&gt;.fmfav-pack.json</code></small>"
        )))

        # --- Metadata form ---
        layout.addWidget(QLabel(self.tr("<b>3. Collection metadata</b>")))
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)

        self._meta_name_edit = QLineEdit()
        self._meta_name_edit.setPlaceholderText(self.tr("Collection display name"))
        form.addRow(self.tr("Name:"), self._meta_name_edit)

        self._meta_author_edit = QLineEdit()
        self._meta_author_edit.setPlaceholderText(self.tr("Author / organisation"))
        form.addRow(self.tr("Author:"), self._meta_author_edit)

        self._meta_license_edit = QLineEdit()
        self._meta_license_edit.setPlaceholderText(self.tr("e.g. CC-BY-4.0, MIT, Proprietary"))
        form.addRow(self.tr("License:"), self._meta_license_edit)

        self._meta_tags_edit = QLineEdit()
        self._meta_tags_edit.setPlaceholderText(self.tr("Comma-separated tags"))
        form.addRow(self.tr("Tags:"), self._meta_tags_edit)

        self._meta_homepage_edit = QLineEdit()
        self._meta_homepage_edit.setPlaceholderText(self.tr("https://..."))
        form.addRow(self.tr("Homepage:"), self._meta_homepage_edit)

        self._meta_desc_edit = QTextEdit()
        self._meta_desc_edit.setMaximumHeight(90)
        self._meta_desc_edit.setPlaceholderText(
            self.tr("Short description (optional, supports plain text)")
        )
        form.addRow(self.tr("Description:"), self._meta_desc_edit)

        layout.addLayout(form)
        layout.addStretch()
        return container

    def _build_favorites_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(QLabel(self.tr("<b>4. Favorites to include</b>")))

        # Select-all / none row
        row = QHBoxLayout()
        select_all_btn = QPushButton(self.tr("Select all"))
        select_all_btn.clicked.connect(lambda: self._set_all_selected(True))
        row.addWidget(select_all_btn)
        select_none_btn = QPushButton(self.tr("Select none"))
        select_none_btn.clicked.connect(lambda: self._set_all_selected(False))
        row.addWidget(select_none_btn)
        row.addStretch()
        self._selected_count_label = QLabel()
        row.addWidget(self._selected_count_label)
        layout.addLayout(row)

        self._favorites_list = QListWidget()
        self._favorites_list.itemChanged.connect(self._update_selected_count)
        layout.addWidget(self._favorites_list, 1)
        return container

    # ─── Target resolution ────────────────────────────────────────────

    def _refresh_targets(self) -> None:
        self._targets = self._sharing_service.list_publish_targets()
        self._target_combo.blockSignals(True)
        self._target_combo.clear()

        for t in self._targets:
            icon = "📁 " if not t.is_new else "✨ "
            label = f"{icon}{t.display_name}  ({os.path.basename(t.collection_dir)})"
            self._target_combo.addItem(label, t)

        # Virtual options
        if self._sharing_service._scanner.get_collections_root() is not None:
            self._target_combo.addItem(
                "✨ " + self.tr("New collection in Resource Sharing root..."),
                self._TARGET_NEW_IN_ROOT,
            )
        self._target_combo.addItem(
            "📂 " + self.tr("Custom directory..."),
            self._TARGET_CUSTOM_DIR,
        )

        self._target_combo.blockSignals(False)

        # Pre-select the default collection from config when it matches
        # an existing target; otherwise fall back to the first one.
        default_path = (self._config_defaults.get('default_publish_collection') or '').strip()
        selected_index = -1
        if default_path:
            abs_default = os.path.abspath(default_path)
            for i in range(self._target_combo.count()):
                data = self._target_combo.itemData(i)
                if isinstance(data, CollectionTarget) and \
                        os.path.abspath(data.collection_dir) == abs_default:
                    selected_index = i
                    break
            # Second chance: match by basename (user can configure with
            # just the folder name, not the full path).
            if selected_index < 0:
                base = os.path.basename(default_path.rstrip(os.sep))
                for i in range(self._target_combo.count()):
                    data = self._target_combo.itemData(i)
                    if isinstance(data, CollectionTarget) and \
                            os.path.basename(data.collection_dir) == base:
                        selected_index = i
                        break
        if selected_index < 0 and self._targets:
            selected_index = 0
        if selected_index >= 0:
            self._target_combo.setCurrentIndex(selected_index)
        self._on_target_changed()

    def _on_target_changed(self) -> None:
        data = self._target_combo.currentData()

        if isinstance(data, CollectionTarget):
            self._set_path_hint(data.collection_dir)
            meta = data.existing_metadata or {}
            self._meta_name_edit.setText(str(meta.get('name') or data.display_name))
            self._meta_author_edit.setText(str(meta.get('author') or ""))
            self._meta_license_edit.setText(str(meta.get('license') or ""))
            tags = meta.get('tags')
            if isinstance(tags, list):
                self._meta_tags_edit.setText(", ".join(str(t) for t in tags))
            else:
                self._meta_tags_edit.setText("")
            self._meta_homepage_edit.setText(str(meta.get('homepage') or ""))
            self._meta_desc_edit.setPlainText(str(meta.get('description') or ""))
        elif data == self._TARGET_NEW_IN_ROOT:
            self._set_path_hint(self.tr("Will be created under the Resource Sharing root."))
        elif data == self._TARGET_CUSTOM_DIR:
            if self._custom_dir:
                self._set_path_hint(self._custom_dir)
            else:
                self._set_path_hint(self.tr("Click 'Browse...' to choose a directory."))

    def _set_path_hint(self, text: str) -> None:
        self._target_path_label.setText(f"<code>{text}</code>")

    def _on_browse_clicked(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            self.tr("Choose a collection directory"),
            self._custom_dir or os.path.expanduser("~"),
        )
        if directory:
            self._custom_dir = directory
            # Switch combo to the custom-dir virtual option
            for i in range(self._target_combo.count()):
                if self._target_combo.itemData(i) == self._TARGET_CUSTOM_DIR:
                    self._target_combo.setCurrentIndex(i)
                    break
            self._set_path_hint(directory)

    # ─── Favorites list ───────────────────────────────────────────────

    def _populate_favorites(self) -> None:
        self._favorites_list.clear()
        get_all = getattr(self._favorites_service, 'get_all_favorites', None)
        favorites = get_all() if callable(get_all) else []
        for fav in favorites:
            name = getattr(fav, 'name', '') or '(unnamed)'
            fav_id = getattr(fav, 'id', '')
            item = QListWidgetItem(f"★ {name}")
            item.setData(Qt.ItemDataRole.UserRole, fav_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Pre-select when caller asked OR when user had nothing pre-selected
            should_check = (
                fav_id in self._preselected_ids
                or not self._preselected_ids
            )
            item.setCheckState(
                Qt.CheckState.Checked if should_check else Qt.CheckState.Unchecked
            )
            desc = getattr(fav, 'description', '') or ''
            if desc:
                item.setToolTip(desc)
            self._favorites_list.addItem(item)
        self._update_selected_count()

    def _set_all_selected(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self._favorites_list.count()):
            self._favorites_list.item(i).setCheckState(state)

    def _update_selected_count(self, *_args) -> None:
        selected = sum(
            1 for i in range(self._favorites_list.count())
            if self._favorites_list.item(i).checkState() == Qt.CheckState.Checked
        )
        total = self._favorites_list.count()
        self._selected_count_label.setText(
            self.tr("{0} / {1} selected").format(selected, total)
        )

    def _selected_favorite_ids(self) -> List[str]:
        ids: List[str] = []
        for i in range(self._favorites_list.count()):
            item = self._favorites_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                fav_id = item.data(Qt.ItemDataRole.UserRole)
                if fav_id:
                    ids.append(fav_id)
        return ids

    # ─── Publish ──────────────────────────────────────────────────────

    def _resolve_target(self) -> Optional[CollectionTarget]:
        data = self._target_combo.currentData()
        if isinstance(data, CollectionTarget):
            return data

        display_name = self._meta_name_edit.text().strip() or "filter_mate_collection"

        if data == self._TARGET_NEW_IN_ROOT:
            suggested = self._sharing_service.suggest_new_collection_dir(display_name)
            if not suggested:
                QMessageBox.warning(
                    self,
                    self.tr("Cannot create collection"),
                    self.tr(
                        "Resource Sharing root not found. Use 'Browse...' to "
                        "pick a directory instead."
                    ),
                )
                return None
            return CollectionTarget(
                collection_dir=suggested,
                display_name=display_name,
                is_new=True,
            )

        if data == self._TARGET_CUSTOM_DIR:
            if not self._custom_dir:
                QMessageBox.warning(
                    self,
                    self.tr("Choose a directory"),
                    self.tr("Click 'Browse...' to pick a target directory."),
                )
                return None
            return CollectionTarget(
                collection_dir=self._custom_dir,
                display_name=display_name,
                is_new=not os.path.exists(self._custom_dir),
            )

        return None

    def _collect_metadata(self) -> dict:
        tags_raw = self._meta_tags_edit.text()
        tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
        return {
            'name': self._meta_name_edit.text().strip(),
            'author': self._meta_author_edit.text().strip(),
            'license': self._meta_license_edit.text().strip(),
            'description': self._meta_desc_edit.toPlainText().strip(),
            'tags': tags,
            'homepage': self._meta_homepage_edit.text().strip(),
        }

    def _on_publish(self) -> None:
        fav_ids = self._selected_favorite_ids()
        if not fav_ids:
            QMessageBox.warning(
                self,
                self.tr("No favorites selected"),
                self.tr("Select at least one favorite to publish."),
            )
            return

        target = self._resolve_target()
        if target is None:
            return

        bundle_name = self._bundle_name_edit.text().strip() or "favorites"
        metadata = self._collect_metadata()

        result = self._sharing_service.publish_bundle(
            favorites_service=self._favorites_service,
            target=target,
            bundle_filename=bundle_name,
            favorite_ids=fav_ids,
            collection_metadata=metadata,
            overwrite=self._overwrite_check.isChecked(),
        )

        if not result.success:
            QMessageBox.warning(
                self,
                self.tr("Publish failed"),
                result.error_message or self.tr("Unknown error."),
            )
            return

        message = self.tr(
            "Published {0} favorite(s) to:\n\n<code>{1}</code>"
        ).format(result.favorites_count, result.bundle_path)
        if result.collection_manifest_path:
            message += "\n\n" + self.tr(
                "Collection manifest updated:\n<code>{0}</code>"
            ).format(result.collection_manifest_path)
        QMessageBox.information(
            self, self.tr("Publish succeeded"), message,
        )
        self.accept()

    # ─── Translation helper ───────────────────────────────────────────

    def tr(self, message: str) -> str:  # type: ignore[override]
        try:
            from qgis.PyQt.QtCore import QCoreApplication
            return QCoreApplication.translate('PublishFavoritesDialog', message)
        except Exception:
            return message

# -*- coding: utf-8 -*-
"""
QFieldCloud Settings Dialog for FilterMate.

Allows users to configure QFieldCloud server URL, credentials,
and extension preferences.
"""

import logging
from typing import TYPE_CHECKING

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from ..extension import QFieldCloudExtension

logger = logging.getLogger('FilterMate.Extensions.QFieldCloud.UI.Settings')


class QFieldCloudSettingsDialog(QDialog):
    """
    Configuration dialog for QFieldCloud credentials and preferences.

    Layout:
        - Server URL
        - Username / Password (or Token)
        - Test connection button
        - Preferences (auto-package, default project)
    """

    def __init__(self, parent=None, extension: 'QFieldCloudExtension' = None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self._extension = extension
        self._credentials = extension._credentials_manager

        self.setWindowTitle("QFieldCloud Configuration")
        self.setMinimumWidth(450)
        self.setModal(True)

        self._init_ui()
        self._load_current_values()
        self._connect_signals()

    def _init_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout()

        # --- Server group ---
        server_group = QGroupBox("Server")
        server_layout = QFormLayout()

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://app.qfield.cloud/api/v1/")
        server_layout.addRow("URL:", self._url_edit)

        server_group.setLayout(server_layout)
        layout.addWidget(server_group)

        # --- Credentials group ---
        creds_group = QGroupBox("Credentials")
        creds_layout = QFormLayout()

        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("username")
        creds_layout.addRow("Username:", self._username_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText("password (for initial login)")
        creds_layout.addRow("Password:", self._password_edit)

        self._token_edit = QLineEdit()
        self._token_edit.setPlaceholderText("JWT token (auto-filled after login)")
        self._token_edit.setReadOnly(True)

        token_row = QHBoxLayout()
        token_row.addWidget(self._token_edit)
        self._refresh_btn = QPushButton("Login")
        self._refresh_btn.setToolTip("Login with username/password to get a token")
        token_row.addWidget(self._refresh_btn)
        creds_layout.addRow("Token:", token_row)

        # Connection status
        self._status_label = QLabel("")
        creds_layout.addRow("Status:", self._status_label)

        # Test button
        self._test_btn = QPushButton("Test Connection")
        creds_layout.addRow("", self._test_btn)

        creds_group.setLayout(creds_layout)
        layout.addWidget(creds_group)

        # --- Preferences group ---
        prefs_group = QGroupBox("Preferences")
        prefs_layout = QFormLayout()

        self._default_project_edit = QLineEdit()
        self._default_project_edit.setPlaceholderText("WYRE-POP_001")
        prefs_layout.addRow("Default project:", self._default_project_edit)

        self._auto_package_cb = QCheckBox("Trigger packaging after upload")
        self._auto_package_cb.setChecked(True)
        prefs_layout.addRow("", self._auto_package_cb)

        prefs_group.setLayout(prefs_layout)
        layout.addWidget(prefs_group)

        # --- Buttons ---
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._button_box)

        self.setLayout(layout)

    def _load_current_values(self):
        """Load current stored values into the form."""
        self._url_edit.setText(self._credentials.get_url())
        self._username_edit.setText(self._credentials.get_username())

        token = self._credentials.get_token()
        if token:
            # Show truncated token
            display = token[:20] + "..." if len(token) > 20 else token
            self._token_edit.setText(display)
            self._status_label.setText("Token stored")
            self._status_label.setStyleSheet("color: green;")

        self._default_project_edit.setText(
            self._credentials.get_default_project()
        )
        self._auto_package_cb.setChecked(
            self._credentials.get_auto_package()
        )

    def _connect_signals(self):
        """Connect button signals."""
        self._refresh_btn.clicked.connect(self._on_login)
        self._test_btn.clicked.connect(self._on_test_connection)
        self._button_box.accepted.connect(self._on_save)
        self._button_box.rejected.connect(self.reject)

    def _on_login(self):
        """Login with username/password to obtain a token."""
        url = self._url_edit.text().strip()
        username = self._username_edit.text().strip()
        password = self._password_edit.text()

        if not url or not username or not password:
            QMessageBox.warning(
                self, "Missing Fields",
                "Please fill in URL, username, and password.",
            )
            return

        self._status_label.setText("Logging in...")
        self._status_label.setStyleSheet("color: blue;")
        self._refresh_btn.setEnabled(False)

        try:
            from ..sdk_adapter import QFieldCloudAdapter

            adapter = QFieldCloudAdapter(url=url)
            token = adapter.login(username, password)

            display = token[:20] + "..." if len(token) > 20 else token
            self._token_edit.setText(display)
            self._password_edit.clear()

            # Store token immediately
            self._credentials.set_token(token)

            self._status_label.setText(f"Logged in as {username}")
            self._status_label.setStyleSheet("color: green;")

            if self._extension and self._extension._signals:
                self._extension._signals.authenticated.emit(username)

        except Exception as e:
            self._status_label.setText(f"Login failed: {e}")
            self._status_label.setStyleSheet("color: red;")

            if self._extension and self._extension._signals:
                self._extension._signals.authentication_failed.emit(str(e))

        finally:
            self._refresh_btn.setEnabled(True)

    def _on_test_connection(self):
        """Test connection with stored token."""
        url = self._url_edit.text().strip()
        token = self._credentials.get_token()

        if not url or not token:
            QMessageBox.warning(
                self, "Missing Configuration",
                "Please configure URL and login first.",
            )
            return

        self._status_label.setText("Testing connection...")
        self._status_label.setStyleSheet("color: blue;")
        self._test_btn.setEnabled(False)

        try:
            from ..sdk_adapter import QFieldCloudAdapter

            adapter = QFieldCloudAdapter(url=url, token=token)
            projects = adapter.list_projects()

            self._status_label.setText(
                f"Connected! ({len(projects)} projects accessible)"
            )
            self._status_label.setStyleSheet("color: green;")

        except Exception as e:
            self._status_label.setText(f"Connection failed: {e}")
            self._status_label.setStyleSheet("color: red;")

        finally:
            self._test_btn.setEnabled(True)

    def _on_save(self):
        """Save settings and close."""
        url = self._url_edit.text().strip()
        username = self._username_edit.text().strip()

        if not url:
            QMessageBox.warning(self, "Missing URL", "Server URL is required.")
            return

        self._credentials.set_url(url)
        self._credentials.set_username(username)
        self._credentials.set_default_project(
            self._default_project_edit.text().strip()
        )
        self._credentials.set_auto_package(
            self._auto_package_cb.isChecked()
        )

        # Store password in keyring if provided
        password = self._password_edit.text()
        if password:
            self._credentials.set_password(password)

        logger.info("QFieldCloud settings saved")
        self.accept()

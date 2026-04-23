# -*- coding: utf-8 -*-
"""
Regression tests for QFieldCloudExtension teardown.

Covers the signal-leak fix from commit a06f3062 (2026-04-23):
- triggered.disconnect() on the settings QAction
- clicked.disconnect() on the dockwidget push button
- iface.removePluginVectorMenu() for proper menu removal (the prior
  action.parent().removeAction() was a no-op because parent() returned
  the main window, not the vector menu)
- Graceful handling of already-disconnected signals
"""

from unittest.mock import MagicMock

import pytest

from extensions.qfieldcloud.extension import QFieldCloudExtension


@pytest.fixture
def extension_with_ui_state():
    """A QFieldCloudExtension primed with mocks simulating post-create_ui state."""
    ext = QFieldCloudExtension()
    ext._iface = MagicMock()
    ext._menu_name = "FilterMate"
    ext._settings_action = MagicMock()
    ext._qfc_button = MagicMock()
    ext._dockwidget = MagicMock()
    ext._actions = [ext._settings_action]
    return ext


class TestQFieldCloudTeardown:
    """Regression tests for the signal-leak fix."""

    def test_disconnects_settings_action_signal(self, extension_with_ui_state):
        ext = extension_with_ui_state
        settings_action = ext._settings_action

        ext.teardown()

        settings_action.triggered.disconnect.assert_called_once_with(
            ext._on_settings_triggered
        )

    def test_removes_menu_entry_via_iface(self, extension_with_ui_state):
        ext = extension_with_ui_state
        iface = ext._iface
        action = ext._settings_action

        ext.teardown()

        iface.removePluginVectorMenu.assert_called_once_with("FilterMate", action)

    def test_disconnects_button_click_signal(self, extension_with_ui_state):
        ext = extension_with_ui_state
        button = ext._qfc_button

        ext.teardown()

        button.clicked.disconnect.assert_called_once_with(ext._on_push_triggered)

    def test_destroys_button(self, extension_with_ui_state):
        ext = extension_with_ui_state
        button = ext._qfc_button

        ext.teardown()

        button.setParent.assert_called_once_with(None)
        button.deleteLater.assert_called_once()

    def test_removes_button_attribute_from_dockwidget(self, extension_with_ui_state):
        ext = extension_with_ui_state
        dockwidget = ext._dockwidget
        dockwidget.pushButton_action_qfieldcloud = object()  # attribute exists

        ext.teardown()

        assert not hasattr(dockwidget, "pushButton_action_qfieldcloud")

    def test_clears_state(self, extension_with_ui_state):
        ext = extension_with_ui_state

        ext.teardown()

        assert ext._settings_action is None
        assert ext._menu_name is None
        assert ext._qfc_button is None
        assert ext._dockwidget is None
        assert ext._iface is None
        assert ext._credentials_manager is None
        assert ext._signals is None
        assert ext._sdk_adapter is None
        assert ext._qfc_service is None
        assert ext._actions == []

    def test_tolerates_already_disconnected_signal(self, extension_with_ui_state):
        """If triggered.disconnect raises, teardown must still complete."""
        ext = extension_with_ui_state
        iface = ext._iface  # capture before teardown clears it
        ext._settings_action.triggered.disconnect.side_effect = TypeError(
            "already disconnected"
        )

        # Must not propagate
        ext.teardown()

        # Menu removal still happens after the disconnect attempt
        iface.removePluginVectorMenu.assert_called_once()

    def test_tolerates_button_disconnect_runtime_error(self, extension_with_ui_state):
        """If clicked.disconnect raises RuntimeError, button is still destroyed."""
        ext = extension_with_ui_state
        button = ext._qfc_button  # capture before teardown clears it
        button.clicked.disconnect.side_effect = RuntimeError(
            "signal already disconnected"
        )

        # Must not propagate
        ext.teardown()

        # Button destruction still happens after the disconnect attempt
        button.setParent.assert_called_once_with(None)
        button.deleteLater.assert_called_once()

    def test_teardown_without_iface_skips_menu_removal(self):
        """If teardown runs with no iface (edge case), no crash."""
        ext = QFieldCloudExtension()
        ext._iface = None
        ext._menu_name = "FilterMate"
        ext._settings_action = MagicMock()
        action = ext._settings_action
        ext._actions = [ext._settings_action]

        # Must not raise — just disconnect the signal, skip menu removal
        ext.teardown()

        action.triggered.disconnect.assert_called_once()

    def test_teardown_without_menu_name_skips_menu_removal(self):
        """If menu_name was never stored, iface.removePluginVectorMenu is not called."""
        ext = QFieldCloudExtension()
        iface = MagicMock()
        ext._iface = iface
        ext._menu_name = None
        ext._settings_action = MagicMock()
        ext._actions = [ext._settings_action]

        ext.teardown()

        iface.removePluginVectorMenu.assert_not_called()

    def test_teardown_without_button_skips_button_cleanup(self):
        """If no dockwidget UI was injected, teardown must not touch the button path."""
        ext = QFieldCloudExtension()
        iface = MagicMock()
        ext._iface = iface
        ext._menu_name = "FilterMate"
        ext._settings_action = MagicMock()
        ext._qfc_button = None
        ext._dockwidget = None
        ext._actions = [ext._settings_action]

        # Must not raise
        ext.teardown()

        iface.removePluginVectorMenu.assert_called_once()

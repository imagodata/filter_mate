# -*- coding: utf-8 -*-
"""
Tests for QFieldCloud credentials manager.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_qgs_settings():
    """Mock QgsSettings for credential storage."""
    store = {}

    class FakeSettings:
        def value(self, key, default="", type=str):
            val = store.get(key, default)
            if type == bool and isinstance(val, str):
                return val.lower() in ('true', '1', 'yes')
            return type(val) if val != default else default

        def setValue(self, key, value):
            store[key] = value

        def remove(self, key):
            store.pop(key, None)

    with patch('extensions.qfieldcloud.credentials_manager.QgsSettings', None):
        # We'll patch at the import level in each method
        pass

    return FakeSettings, store


@pytest.fixture
def credentials_manager():
    """Create a CredentialsManager with mocked backends."""
    with patch(
        'extensions.qfieldcloud.credentials_manager._keyring_available',
        return_value=False,
    ):
        from extensions.qfieldcloud.credentials_manager import (
            CredentialsManager,
        )

        mgr = CredentialsManager()
        return mgr


class TestCredentialsManager:
    """Tests for credential storage and retrieval."""

    def test_store_and_retrieve_url(self, credentials_manager):
        with patch('qgis.core.QgsSettings') as MockSettings:
            settings_store = {}
            instance = MockSettings.return_value
            instance.setValue = lambda k, v: settings_store.__setitem__(k, v)
            instance.value = lambda k, d="", **kw: settings_store.get(k, d)
            MockSettings.return_value = instance
            MockSettings.side_effect = lambda: instance

            credentials_manager.set_url("https://test.qfield.cloud/api/v1/")
            assert credentials_manager.get_url() == "https://test.qfield.cloud/api/v1/"

    def test_has_credentials_false_when_empty(self, credentials_manager):
        with patch('qgis.core.QgsSettings') as MockSettings:
            instance = MagicMock()
            instance.value.return_value = ""
            MockSettings.return_value = instance

            assert credentials_manager.has_credentials() is False

    def test_token_fallback_to_env(self, credentials_manager):
        """Token falls back to environment variable."""
        with patch('qgis.core.QgsSettings') as MockSettings:
            instance = MagicMock()
            instance.value.return_value = ""
            MockSettings.return_value = instance

            with patch.dict(
                'os.environ', {'QFIELDCLOUD_TOKEN': 'env-token-123'}
            ):
                token = credentials_manager.get_token()
                assert token == 'env-token-123'

    def test_clear_removes_settings(self, credentials_manager):
        with patch('qgis.core.QgsSettings') as MockSettings:
            instance = MagicMock()
            MockSettings.return_value = instance

            credentials_manager.clear()

            # Should call remove for each settings key
            assert instance.remove.call_count >= 5

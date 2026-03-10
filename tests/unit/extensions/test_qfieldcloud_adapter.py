# -*- coding: utf-8 -*-
"""
Tests for QFieldCloud SDK adapter with mocked Client.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from filter_mate.extensions.qfieldcloud.exceptions import (
    QFieldCloudAuthError,
    QFieldCloudError,
    QFieldCloudProjectError,
    QFieldCloudTimeoutError,
    QFieldCloudUploadError,
)


@pytest.fixture
def mock_sdk():
    """Mock qfieldcloud_sdk.sdk module."""
    with patch.dict('sys.modules', {
        'qfieldcloud_sdk': MagicMock(),
        'qfieldcloud_sdk.sdk': MagicMock(),
    }):
        yield


@pytest.fixture
def mock_client(mock_sdk):
    """Create adapter with mocked SDK client."""
    with patch('qfieldcloud_sdk.sdk.Client') as MockClient:
        client_instance = MagicMock()
        MockClient.return_value = client_instance

        from filter_mate.extensions.qfieldcloud.sdk_adapter import QFieldCloudAdapter

        adapter = QFieldCloudAdapter(url="https://test.qfield.cloud/api/v1/")
        adapter._client = client_instance
        yield adapter, client_instance


class TestQFieldCloudAdapterAuth:
    """Tests for authentication."""

    def test_login_success(self, mock_client):
        adapter, client = mock_client
        client.login.return_value = "test-jwt-token"

        token = adapter.login("user", "pass")

        assert token == "test-jwt-token"
        assert adapter.is_authenticated is True
        assert adapter.username == "user"
        client.login.assert_called_once_with("user", "pass")

    def test_login_failure_raises_auth_error(self, mock_client):
        adapter, client = mock_client
        client.login.side_effect = Exception("401 Unauthorized")

        with pytest.raises(QFieldCloudAuthError, match="Authentication failed"):
            adapter.login("user", "wrong")

        assert adapter.is_authenticated is False

    def test_login_with_token_success(self, mock_client):
        adapter, client = mock_client
        client.list_projects.return_value = []

        result = adapter.login_with_token("valid-token")

        assert result is True
        assert adapter.is_authenticated is True

    def test_login_with_token_failure(self, mock_client):
        adapter, client = mock_client
        client.list_projects.side_effect = Exception("Invalid token")

        with pytest.raises(QFieldCloudAuthError, match="Token authentication failed"):
            adapter.login_with_token("bad-token")


class TestQFieldCloudAdapterProjects:
    """Tests for project operations."""

    def test_list_projects(self, mock_client):
        adapter, client = mock_client
        adapter._authenticated = True
        client.list_projects.return_value = [
            {'id': '1', 'name': 'proj1'},
            {'id': '2', 'name': 'proj2'},
        ]

        projects = adapter.list_projects()

        assert len(projects) == 2
        assert projects[0]['name'] == 'proj1'

    def test_list_projects_requires_auth(self, mock_client):
        adapter, client = mock_client
        adapter._authenticated = False

        with pytest.raises(QFieldCloudAuthError, match="Not authenticated"):
            adapter.list_projects()

    def test_create_project_returns_id(self, mock_client):
        adapter, client = mock_client
        adapter._authenticated = True
        adapter._username = "testuser"
        client.create_project.return_value = {'id': 'new-id-123', 'name': 'test'}

        result = adapter.create_project("test", description="A test project")

        assert result['id'] == 'new-id-123'
        client.create_project.assert_called_once_with(
            name="test",
            owner="testuser",
            description="A test project",
            is_public=False,
        )

    def test_create_project_failure_raises(self, mock_client):
        adapter, client = mock_client
        adapter._authenticated = True
        adapter._username = "user"
        client.create_project.side_effect = Exception("403 Forbidden")

        with pytest.raises(QFieldCloudProjectError, match="Failed to create"):
            adapter.create_project("test")

    def test_find_project_by_name(self, mock_client):
        adapter, client = mock_client
        adapter._authenticated = True
        client.list_projects.return_value = [
            {'id': '1', 'name': 'WYRE-POP_001'},
            {'id': '2', 'name': 'WYRE-POP_002'},
        ]

        found = adapter.find_project_by_name('WYRE-POP_001')
        assert found['id'] == '1'

        not_found = adapter.find_project_by_name('NONEXISTENT')
        assert not_found is None


class TestQFieldCloudAdapterUpload:
    """Tests for file upload with retry."""

    def test_upload_retry_on_timeout(self, mock_client, tmp_path):
        adapter, client = mock_client
        adapter._authenticated = True
        adapter.BACKOFF_BASE = 0.01  # Speed up tests

        # Create test files
        (tmp_path / "test.gpkg").write_text("gpkg")
        (tmp_path / "test.qgs").write_text("qgs")

        # Fail twice, succeed on third
        client.upload_files.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            None,  # success
            None,  # success for second file
        ]

        count = adapter.upload_project_files(
            project_id="proj-1",
            local_dir=tmp_path,
        )

        assert count == 2
        assert client.upload_files.call_count == 4

    def test_upload_raises_after_max_retries(self, mock_client, tmp_path):
        adapter, client = mock_client
        adapter._authenticated = True
        adapter.BACKOFF_BASE = 0.01

        (tmp_path / "test.gpkg").write_text("data")

        client.upload_files.side_effect = Exception("Server down")

        with pytest.raises(QFieldCloudUploadError, match="after 3 attempts"):
            adapter.upload_project_files(
                project_id="proj-1",
                local_dir=tmp_path,
            )

    def test_upload_empty_dir_returns_zero(self, mock_client, tmp_path):
        adapter, client = mock_client
        adapter._authenticated = True

        count = adapter.upload_project_files(
            project_id="proj-1",
            local_dir=tmp_path,
        )
        assert count == 0

    def test_upload_progress_callback(self, mock_client, tmp_path):
        adapter, client = mock_client
        adapter._authenticated = True

        (tmp_path / "a.gpkg").write_text("data")
        (tmp_path / "b.qgs").write_text("data")
        client.upload_files.return_value = None

        progress_calls = []
        adapter.upload_project_files(
            project_id="proj-1",
            local_dir=tmp_path,
            progress_callback=lambda p, m: progress_calls.append((p, m)),
        )

        assert len(progress_calls) == 2
        assert progress_calls[-1][0] == 100  # Last call should be 100%


class TestQFieldCloudAdapterJobs:
    """Tests for job management."""

    def test_trigger_package(self, mock_client):
        adapter, client = mock_client
        adapter._authenticated = True
        client.job_trigger.return_value = {'id': 'job-123'}

        job_id = adapter.trigger_package("proj-1")

        assert job_id == "job-123"
        client.job_trigger.assert_called_once_with(
            project_id="proj-1", job_type="package"
        )

    def test_poll_job_timeout(self, mock_client):
        adapter, client = mock_client
        adapter._authenticated = True
        client.job_status.return_value = {'status': 'running'}

        with pytest.raises(QFieldCloudTimeoutError, match="did not finish"):
            adapter.poll_job_status("job-1", timeout=0.1, interval=0.05)

    def test_poll_job_success(self, mock_client):
        adapter, client = mock_client
        adapter._authenticated = True
        client.job_status.side_effect = [
            {'status': 'running'},
            {'status': 'finished'},
        ]

        result = adapter.poll_job_status("job-1", timeout=5, interval=0.01)
        assert result['status'] == 'finished'


class TestQFieldCloudAdapterHelpers:
    """Tests for helper methods."""

    def test_get_project_url(self, mock_client):
        adapter, _ = mock_client

        url = adapter.get_project_url("abc-123")
        assert url == "https://test.qfield.cloud/a/abc-123"

    def test_get_project_url_strips_api(self, mock_client):
        adapter, _ = mock_client
        adapter._url = "https://qfc.example.com/api/v1/"

        url = adapter.get_project_url("xyz")
        assert url == "https://qfc.example.com/a/xyz"

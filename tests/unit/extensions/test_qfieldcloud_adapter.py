# -*- coding: utf-8 -*-
"""
Tests for QFieldCloud adapter wrapping QFieldSync's CloudNetworkAccessManager.
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
def mock_nam():
    """Create a mock CloudNetworkAccessManager."""
    nam = MagicMock()
    nam.is_authenticated.return_value = True
    nam.has_token.return_value = True
    nam.get_username.return_value = "testuser"
    nam.server_url = "https://test.qfield.cloud/api/v1/"
    nam.get_projects_not_async.return_value = [
        {'id': '1', 'name': 'proj1'},
        {'id': '2', 'name': 'proj2'},
    ]
    return nam


@pytest.fixture
def adapter(mock_nam):
    """Create adapter with mocked NAM."""
    with patch.dict('sys.modules', {
        'qfieldsync': MagicMock(),
        'qfieldsync.core': MagicMock(),
        'qfieldsync.core.cloud_api': MagicMock(),
    }):
        from filter_mate.extensions.qfieldcloud.sdk_adapter import QFieldCloudAdapter
        return QFieldCloudAdapter(network_manager=mock_nam)


class TestQFieldCloudAdapterAuth:
    """Tests for authentication."""

    def test_is_authenticated_delegates_to_nam(self, adapter, mock_nam):
        mock_nam.is_authenticated.return_value = True
        assert adapter.is_authenticated is True

        mock_nam.is_authenticated.return_value = False
        assert adapter.is_authenticated is False

    def test_username_from_nam(self, adapter, mock_nam):
        assert adapter.username == "testuser"

    def test_login_success(self, adapter, mock_nam):
        mock_nam.login_with_credentials.return_value = MagicMock()
        mock_nam.is_authenticated.return_value = True

        result = adapter.login("user", "pass")

        assert result is True
        mock_nam.login_with_credentials.assert_called_once_with("user", "pass")

    def test_login_failure_raises_auth_error(self, adapter, mock_nam):
        mock_nam.login_with_credentials.return_value = MagicMock()
        mock_nam.is_authenticated.return_value = False
        mock_nam.get_last_login_error.return_value = "Invalid credentials"

        with pytest.raises(QFieldCloudAuthError, match="Authentication failed"):
            adapter.login("user", "wrong")

    def test_login_with_token_success(self, adapter, mock_nam):
        mock_nam.is_authenticated.return_value = True

        result = adapter.login_with_token("valid-token")

        assert result is True
        mock_nam.set_token.assert_called_once_with("valid-token")

    def test_login_with_token_failure(self, adapter, mock_nam):
        mock_nam.is_authenticated.return_value = False
        mock_nam.get_projects_not_async.side_effect = Exception("Invalid token")

        with pytest.raises(QFieldCloudAuthError, match="Token authentication failed"):
            adapter.login_with_token("bad-token")


class TestQFieldCloudAdapterProjects:
    """Tests for project operations."""

    def test_list_projects(self, adapter, mock_nam):
        projects = adapter.list_projects()

        assert len(projects) == 2
        assert projects[0]['name'] == 'proj1'

    def test_list_projects_requires_auth(self, adapter, mock_nam):
        mock_nam.is_authenticated.return_value = False

        with pytest.raises(QFieldCloudAuthError, match="Not authenticated"):
            adapter.list_projects()

    def test_create_project_returns_id(self, adapter, mock_nam):
        reply = MagicMock()
        reply.isFinished.return_value = True
        mock_nam.create_project.return_value = reply
        mock_nam.json_object.return_value = {'id': 'new-id-123', 'name': 'test'}

        result = adapter.create_project("test", description="A test project")

        assert result['id'] == 'new-id-123'

    def test_create_project_failure_raises(self, adapter, mock_nam):
        mock_nam.create_project.side_effect = Exception("403 Forbidden")

        with pytest.raises(QFieldCloudProjectError, match="Failed to create"):
            adapter.create_project("test")

    def test_find_project_by_name(self, adapter, mock_nam):
        found = adapter.find_project_by_name('proj1')
        assert found['id'] == '1'

        not_found = adapter.find_project_by_name('NONEXISTENT')
        assert not_found is None


class TestQFieldCloudAdapterUpload:
    """Tests for file upload with retry."""

    def test_upload_files(self, adapter, mock_nam, tmp_path):
        (tmp_path / "test.gpkg").write_text("gpkg")
        (tmp_path / "test.qgs").write_text("qgs")

        reply = MagicMock()
        reply.isFinished.return_value = True
        mock_nam.cloud_upload_files.return_value = reply
        mock_nam.handle_response.return_value = None

        count = adapter.upload_project_files(
            project_id="proj-1",
            local_dir=tmp_path,
        )

        assert count == 2
        assert mock_nam.cloud_upload_files.call_count == 2

    def test_upload_retry_on_failure(self, adapter, mock_nam, tmp_path):
        adapter.BACKOFF_BASE = 0.01  # Speed up tests

        (tmp_path / "test.gpkg").write_text("gpkg")

        reply = MagicMock()
        reply.isFinished.return_value = True
        mock_nam.cloud_upload_files.return_value = reply
        # Fail twice on handle_response, succeed on third
        mock_nam.handle_response.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            None,  # success
        ]

        count = adapter.upload_project_files(
            project_id="proj-1",
            local_dir=tmp_path,
        )

        assert count == 1
        assert mock_nam.cloud_upload_files.call_count == 3

    def test_upload_raises_after_max_retries(self, adapter, mock_nam, tmp_path):
        adapter.BACKOFF_BASE = 0.01

        (tmp_path / "test.gpkg").write_text("data")

        reply = MagicMock()
        reply.isFinished.return_value = True
        mock_nam.cloud_upload_files.return_value = reply
        mock_nam.handle_response.side_effect = Exception("Server down")

        with pytest.raises(QFieldCloudUploadError, match="after 3 attempts"):
            adapter.upload_project_files(
                project_id="proj-1",
                local_dir=tmp_path,
            )

    def test_upload_empty_dir_returns_zero(self, adapter, mock_nam, tmp_path):
        count = adapter.upload_project_files(
            project_id="proj-1",
            local_dir=tmp_path,
        )
        assert count == 0

    def test_upload_progress_callback(self, adapter, mock_nam, tmp_path):
        (tmp_path / "a.gpkg").write_text("data")
        (tmp_path / "b.qgs").write_text("data")

        reply = MagicMock()
        reply.isFinished.return_value = True
        mock_nam.cloud_upload_files.return_value = reply
        mock_nam.handle_response.return_value = None

        progress_calls = []
        adapter.upload_project_files(
            project_id="proj-1",
            local_dir=tmp_path,
            progress_callback=lambda p, m: progress_calls.append((p, m)),
        )

        assert len(progress_calls) == 2
        assert progress_calls[-1][0] == 100


class TestQFieldCloudAdapterJobs:
    """Tests for job management."""

    def test_trigger_package(self, adapter, mock_nam):
        reply = MagicMock()
        reply.isFinished.return_value = True
        mock_nam.cloud_post.return_value = reply
        mock_nam.json_object.return_value = {'id': 'job-123'}

        job_id = adapter.trigger_package("proj-1")

        assert job_id == "job-123"

    def test_poll_job_timeout(self, adapter, mock_nam):
        reply = MagicMock()
        reply.isFinished.return_value = True
        mock_nam.cloud_get.return_value = reply
        mock_nam.json_object.return_value = {'status': 'running'}

        with pytest.raises(QFieldCloudTimeoutError, match="did not finish"):
            adapter.poll_job_status("job-1", timeout=0.1, interval=0.05)

    def test_poll_job_success(self, adapter, mock_nam):
        reply = MagicMock()
        reply.isFinished.return_value = True
        mock_nam.cloud_get.return_value = reply
        mock_nam.json_object.side_effect = [
            {'status': 'running'},
            {'status': 'finished'},
        ]

        result = adapter.poll_job_status("job-1", timeout=5, interval=0.01)
        assert result['status'] == 'finished'


class TestQFieldCloudAdapterHelpers:
    """Tests for helper methods."""

    def test_get_project_url(self, adapter):
        url = adapter.get_project_url("abc-123")
        assert url == "https://test.qfield.cloud/a/abc-123"

    def test_server_url(self, adapter):
        assert adapter.server_url == "https://test.qfield.cloud/api/v1/"

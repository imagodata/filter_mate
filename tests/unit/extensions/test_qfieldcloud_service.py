# -*- coding: utf-8 -*-
"""
Tests for QFieldCloud service (push orchestration).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from filter_mate.extensions.qfieldcloud.service import (
    QFieldCloudPushResult,
    QFieldCloudService,
)


@pytest.fixture
def mock_adapter():
    """Create a mock SDK adapter."""
    adapter = MagicMock()
    adapter.is_authenticated = True
    adapter.find_project_by_name.return_value = None
    adapter.create_project.return_value = {'id': 'proj-123'}
    adapter.upload_project_files.return_value = 3
    adapter.trigger_package.return_value = 'job-456'
    adapter.get_project_url.return_value = 'https://qfc.test/a/proj-123'
    return adapter


@pytest.fixture
def mock_credentials():
    """Create a mock credentials manager."""
    creds = MagicMock()
    creds.has_credentials.return_value = True
    creds.get_auto_package.return_value = True
    return creds


@pytest.fixture
def mock_signals():
    """Create a mock signals instance."""
    signals = MagicMock()
    return signals


@pytest.fixture
def service(mock_adapter, mock_credentials, mock_signals):
    """Create a QFieldCloudService with mocked dependencies."""
    return QFieldCloudService(
        adapter=mock_adapter,
        credentials_manager=mock_credentials,
        signals=mock_signals,
    )


class TestQFieldCloudService:
    """Tests for push workflow."""

    @patch('filter_mate.extensions.qfieldcloud.service.shutil')
    @patch('filter_mate.extensions.qfieldcloud.service.tempfile')
    def test_push_project_creates_project_and_uploads(
        self, mock_tempfile, mock_shutil, service, mock_adapter, tmp_path
    ):
        """push_project creates project and uploads files."""
        mock_tempfile.mkdtemp.return_value = str(tmp_path)

        gpkg_path = tmp_path / "test.gpkg"
        gpkg_path.write_text("fake gpkg")

        # Mock project builder
        with patch(
            'filter_mate.extensions.qfieldcloud.project_builder.QFieldProjectBuilder'
        ) as MockBuilder:
            builder_instance = MagicMock()
            builder_instance.build.return_value = tmp_path / "test.qgs"
            MockBuilder.return_value = builder_instance

            result = service.push_project(
                project_name="TEST-001",
                gpkg_path=gpkg_path,
                description="Test project",
            )

        assert result.success is True
        assert result.project_id == 'proj-123'
        assert result.files_uploaded == 3
        assert result.project_url == 'https://qfc.test/a/proj-123'
        assert result.job_id == 'job-456'
        assert result.duration_seconds > 0

        # Verify adapter calls
        mock_adapter.create_project.assert_called_once_with(
            name="TEST-001", description="Test project"
        )
        mock_adapter.upload_project_files.assert_called_once()
        mock_adapter.trigger_package.assert_called_once_with('proj-123')

    @patch('filter_mate.extensions.qfieldcloud.service.shutil')
    @patch('filter_mate.extensions.qfieldcloud.service.tempfile')
    def test_push_updates_existing_project(
        self, mock_tempfile, mock_shutil, service, mock_adapter, tmp_path
    ):
        """push_project updates existing project when ID provided."""
        mock_tempfile.mkdtemp.return_value = str(tmp_path)

        gpkg_path = tmp_path / "test.gpkg"
        gpkg_path.write_text("fake")

        with patch(
            'filter_mate.extensions.qfieldcloud.project_builder.QFieldProjectBuilder'
        ) as MockBuilder:
            MockBuilder.return_value.build.return_value = tmp_path / "t.qgs"

            result = service.push_project(
                project_name="TEST-001",
                gpkg_path=gpkg_path,
                existing_project_id="existing-id",
            )

        assert result.success is True
        assert result.project_id == "existing-id"
        mock_adapter.create_project.assert_not_called()

    @patch('filter_mate.extensions.qfieldcloud.service.shutil')
    @patch('filter_mate.extensions.qfieldcloud.service.tempfile')
    def test_push_emits_signals(
        self, mock_tempfile, mock_shutil, service, mock_signals, tmp_path
    ):
        """Push emits progress and success signals."""
        mock_tempfile.mkdtemp.return_value = str(tmp_path)
        gpkg = tmp_path / "test.gpkg"
        gpkg.write_text("data")

        with patch(
            'filter_mate.extensions.qfieldcloud.project_builder.QFieldProjectBuilder'
        ) as MockBuilder:
            MockBuilder.return_value.build.return_value = tmp_path / "t.qgs"
            service.push_project("TEST", gpkg)

        mock_signals.project_pushed.emit.assert_called_once()
        assert mock_signals.progress_updated.emit.call_count > 0

    @patch('filter_mate.extensions.qfieldcloud.service.shutil')
    @patch('filter_mate.extensions.qfieldcloud.service.tempfile')
    def test_push_failure_emits_failed_signal(
        self, mock_tempfile, mock_shutil, service, mock_adapter, mock_signals, tmp_path
    ):
        """Push failure emits push_failed signal."""
        mock_tempfile.mkdtemp.return_value = str(tmp_path)
        gpkg = tmp_path / "test.gpkg"
        gpkg.write_text("data")

        mock_adapter.create_project.side_effect = Exception("Server error")

        with patch(
            'filter_mate.extensions.qfieldcloud.project_builder.QFieldProjectBuilder'
        ) as MockBuilder:
            MockBuilder.return_value.build.return_value = tmp_path / "t.qgs"
            result = service.push_project("TEST", gpkg)

        assert result.success is False
        assert "Server error" in result.error_message
        mock_signals.push_failed.emit.assert_called_once()

    @patch('filter_mate.extensions.qfieldcloud.service.shutil')
    @patch('filter_mate.extensions.qfieldcloud.service.tempfile')
    def test_push_calls_progress_callback(
        self, mock_tempfile, mock_shutil, service, tmp_path
    ):
        """Progress callback receives 0-100 updates."""
        mock_tempfile.mkdtemp.return_value = str(tmp_path)
        gpkg = tmp_path / "test.gpkg"
        gpkg.write_text("data")

        progress_calls = []

        with patch(
            'filter_mate.extensions.qfieldcloud.project_builder.QFieldProjectBuilder'
        ) as MockBuilder:
            MockBuilder.return_value.build.return_value = tmp_path / "t.qgs"
            service.push_project(
                "TEST", gpkg,
                progress_callback=lambda p, m: progress_calls.append(p),
            )

        assert len(progress_calls) > 0
        assert progress_calls[0] == 0
        assert progress_calls[-1] == 100


class TestQFieldCloudBatchPush:
    """Tests for batch push."""

    @patch('filter_mate.extensions.qfieldcloud.service.shutil')
    @patch('filter_mate.extensions.qfieldcloud.service.tempfile')
    def test_batch_push_three_zones(
        self, mock_tempfile, mock_shutil, service, mock_signals, tmp_path
    ):
        """batch_push_zones processes 3 zones."""
        mock_tempfile.mkdtemp.return_value = str(tmp_path)

        zone_configs = []
        for name in ["POP_001", "POP_002", "POP_003"]:
            gpkg = tmp_path / f"{name}.gpkg"
            gpkg.write_text("data")
            zone_configs.append({
                'zone_name': name,
                'gpkg_path': str(gpkg),
            })

        with patch(
            'filter_mate.extensions.qfieldcloud.project_builder.QFieldProjectBuilder'
        ) as MockBuilder:
            MockBuilder.return_value.build.return_value = tmp_path / "t.qgs"
            results = service.batch_push_zones(zone_configs, project_prefix="WYRE")

        assert len(results) == 3
        assert all(r.success for r in results)

        # Verify batch signal
        mock_signals.batch_completed.emit.assert_called_once_with(3, 3, 0)


class TestPushResult:
    """Tests for QFieldCloudPushResult."""

    def test_str_success(self):
        r = QFieldCloudPushResult(
            success=True, project_id="p1", files_uploaded=5, duration_seconds=3.2
        )
        s = str(r)
        assert "OK" in s
        assert "p1" in s

    def test_str_failure(self):
        r = QFieldCloudPushResult(
            success=False, error_message="Network error"
        )
        s = str(r)
        assert "FAILED" in s

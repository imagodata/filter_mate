# -*- coding: utf-8 -*-
"""Mixed export (vector + raster / point cloud) with a ZIP: the vector archive keeps its own files.

The raster / point cloud export runs at the same time as the vector export
into the same folder; the vector ZIP archives the folder. The coverage files
go to a subfolder that the vector ZIP leaves out (they have their own
``<name>_raster_lidar.zip``).
"""
import ast
import os
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_DOCKWIDGET = Path(__file__).resolve().parents[4] / "filter_mate_dockwidget.py"
COVERAGE_SUBFOLDER_NAME = "raster_lidar"  # literal: the vector-only test also runs without the constant


class TestCoverageFolder:
    def test_mixed_export_with_zip_uses_the_subfolder(self):
        from core.export.batch_exporter import COVERAGE_EXPORT_SUBFOLDER, coverage_export_folder
        assert coverage_export_folder('/out', '/out.zip', True) == os.path.join('/out', COVERAGE_EXPORT_SUBFOLDER)

    @pytest.mark.parametrize("zip_path, with_vector", [(None, True), ('', True), ('/out.zip', False)])
    def test_otherwise_the_folder_itself(self, zip_path, with_vector):
        from core.export.batch_exporter import coverage_export_folder
        assert coverage_export_folder('/out', zip_path, with_vector) == '/out'

    def test_no_folder_stays_none(self):
        from core.export.batch_exporter import coverage_export_folder
        assert coverage_export_folder(None, '/out.zip', True) is None


class TestFolderZip:
    def test_coverage_subfolder_left_out(self, tmp_path):
        from core.export.batch_exporter import COVERAGE_EXPORT_SUBFOLDER, BatchExporter
        (tmp_path / "roads.gpkg").write_bytes(b"gpkg")
        coverage = tmp_path / COVERAGE_EXPORT_SUBFOLDER
        coverage.mkdir()
        (coverage / "dem.tif.staging.tif").write_bytes(b"half written")
        (coverage / "cloud.laz").write_bytes(b"LASF")
        archive = tmp_path.parent / "vector.zip"
        assert BatchExporter.create_zip_archive(str(archive), str(tmp_path)) is True
        with zipfile.ZipFile(archive) as handle:
            assert handle.namelist() == ["roads.gpkg"]

    def test_archives_written_in_the_folder_left_out(self, tmp_path):
        """A ZIP saved into the exported folder: neither itself nor the raster / point cloud archive."""
        from core.export.batch_exporter import BatchExporter
        (tmp_path / "roads.gpkg").write_bytes(b"gpkg")
        (tmp_path / "export_raster_lidar.zip").write_bytes(b"PK half written")
        archive = tmp_path / "export.zip"
        assert BatchExporter.create_zip_archive(str(archive), str(tmp_path)) is True
        with zipfile.ZipFile(archive) as handle:
            assert handle.namelist() == ["roads.gpkg"]

    def test_vector_folder_unchanged(self, tmp_path):
        """Vector only: every file and subfolder of the export folder, as before."""
        from core.export.batch_exporter import BatchExporter
        (tmp_path / "roads.shp").write_bytes(b"shp")
        (tmp_path / "roads.dbf").write_bytes(b"dbf")
        (tmp_path / "styles").mkdir()
        (tmp_path / "styles" / "roads.qml").write_text("<qml/>")
        (tmp_path / "styles" / COVERAGE_SUBFOLDER_NAME).mkdir()
        (tmp_path / "styles" / COVERAGE_SUBFOLDER_NAME / "deep.txt").write_text("kept: not at the top level")
        archive = tmp_path.parent / "vector.zip"
        assert BatchExporter.create_zip_archive(str(archive), str(tmp_path)) is True
        with zipfile.ZipFile(archive) as handle:
            names = sorted(name.replace(os.sep, "/") for name in handle.namelist())
        assert names == ["roads.dbf", "roads.shp", f"styles/{COVERAGE_SUBFOLDER_NAME}/deep.txt", "styles/roads.qml"]


def test_dock_sends_the_coverage_export_to_its_folder():
    """launchTaskEvent: the folder of the pending coverage export goes through coverage_export_folder."""
    tree = ast.parse(_DOCKWIDGET.read_text(encoding="utf-8"))
    for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
        pending = [node for node in ast.walk(function) if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Attribute) and t.attr == '_pending_coverage_export' for t in node.targets)
                   and isinstance(node.value, ast.Tuple)]
        if not pending:
            continue
        calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == 'coverage_export_folder']
        assert calls and calls[0].lineno < pending[0].lineno
        assert [arg.id for arg in calls[0].args if isinstance(arg, ast.Name)] == ['folder', 'zip_path']
        return
    raise AssertionError("_pending_coverage_export assignment not found")

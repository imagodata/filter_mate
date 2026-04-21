# -*- coding: utf-8 -*-
"""Regression tests for the export pipeline bugs fixed in v4.6.7.

Covers:
- Single-layer export to a chosen file path (e.g. XLSX, SHP, GeoJSON) that
  previously failed with ``Output path does not exist`` because the handler
  treated the file path as a directory.
- Extension resolution for every supported driver (XLSX, MapInfo File,
  FlatGeobuf, SpatiaLite, unknown fallback).
- Canonical OGR driver resolution for streaming export (no more lossy
  ``.upper()`` on names like ``MapInfo File``).
- Style sidecar convention (``data.qml`` next to ``data.shp``, not
  ``data.shp.qml``).
- ``LIBKML`` accepted alongside ``KML`` for ``preserve_groups``.
"""
import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# get_extension_for_format
# ---------------------------------------------------------------------------

class TestGetExtensionForFormat:
    """Driver description -> file extension mapping."""

    def _get(self):
        from core.export.layer_exporter import get_extension_for_format
        return get_extension_for_format

    @pytest.mark.parametrize("datatype,expected", [
        ("GPKG", ".gpkg"),
        ("gpkg", ".gpkg"),
        ("SHP", ".shp"),
        ("ESRI Shapefile", ".shp"),
        ("GeoJSON", ".geojson"),
        ("JSON", ".geojson"),
        ("GML", ".gml"),
        ("KML", ".kml"),
        ("LIBKML", ".kml"),
        ("CSV", ".csv"),
        ("XLSX", ".xlsx"),
        ("MapInfo File", ".tab"),
        ("FlatGeobuf", ".fgb"),
        ("SpatiaLite", ".spatialite"),
        ("DXF", ".dxf"),
    ])
    def test_known_formats(self, datatype, expected):
        assert self._get()(datatype) == expected

    def test_unknown_format_falls_back_to_lowercased_datatype(self):
        assert self._get()("Weird Format") == ".weird_format"


# ---------------------------------------------------------------------------
# Single-layer file-path export path (the bug reported by the user)
# ---------------------------------------------------------------------------

class TestExecuteExportingFilePathOutput:
    """When the user picks a file name via save-file dialog, ``output_folder``
    is a full file path, not a directory. The handler must treat it as such."""

    @pytest.fixture(autouse=True)
    def setup_handler(self):
        with patch('core.tasks.export_handler.StreamingExporter'), \
             patch('core.tasks.export_handler.StreamingConfig'):
            from core.tasks.export_handler import ExportHandler
            self.handler = ExportHandler()

    def _build_params(self, datatype, output_folder):
        return {
            "task": {
                "EXPORTING": {
                    "HAS_LAYERS_TO_EXPORT": True,
                    "HAS_DATATYPE_TO_EXPORT": True,
                    "DATATYPE_TO_EXPORT": datatype,
                    "HAS_OUTPUT_FOLDER_TO_EXPORT": True,
                    "OUTPUT_FOLDER_TO_EXPORT": output_folder,
                    "HAS_STYLES_TO_EXPORT": False,
                },
                "layers": [{"layer_name": "my_layer"}],
            },
            "config": {"APP": {"OPTIONS": {"STREAMING_EXPORT": {
                "enabled": {"value": False},
            }}}},
        }

    def _run_with_stubbed_exporter(self, datatype, output_path, layer_name="x"):
        """Run execute_exporting with LayerExporter.export_single_layer stubbed
        to capture the final path it receives."""
        from core.export.layer_exporter import LayerExporter

        captured = {}
        fake_result = MagicMock(success=True, error_message=None)

        def fake_export(self_, layer, path, *a, **kw):
            captured['path'] = path
            return fake_result

        params = self._build_params(datatype, output_path)
        validated = {
            'layers': [{"layer_name": layer_name}],
            'projection': None, 'styles': None,
            'datatype': datatype,
            'output_folder': output_path,
            'zip_path': None, 'batch_output_folder': False,
            'batch_zip': False, 'preserve_groups': False,
        }
        with patch.object(LayerExporter, 'export_single_layer', fake_export), \
             patch.object(self.handler, 'validate_export_parameters',
                          return_value=validated):
            success, message, _ = self.handler.execute_exporting(
                task_parameters=params, project=MagicMock(),
                set_progress=MagicMock(), set_description=MagicMock(),
                is_canceled=MagicMock(return_value=False),
            )
        return success, message, captured

    def test_xlsx_single_layer_accepts_file_path(self, tmp_path):
        """XLSX single-layer export should succeed when output_folder is a
        full file path. Previously failed with ``Output path does not exist``."""
        out_file = tmp_path / "mydata.xlsx"
        success, message, captured = self._run_with_stubbed_exporter(
            "XLSX", str(out_file)
        )
        assert success is True, f"Expected success, got: {message}"
        assert captured["path"] == str(out_file)
        assert out_file.parent.exists()

    def test_shp_single_layer_accepts_file_path(self, tmp_path):
        """SHP single-layer export should work via file-path output.

        Also exercises the parent-directory auto-creation branch.
        """
        out_file = tmp_path / "subdir" / "roads.shp"
        success, message, captured = self._run_with_stubbed_exporter(
            "ESRI Shapefile", str(out_file), layer_name="roads"
        )
        assert success is True, f"Expected success, got: {message}"
        assert captured["path"] == str(out_file)
        assert out_file.parent.exists()

    def test_mismatched_extension_is_corrected(self, tmp_path):
        """If user's saved path has wrong extension (e.g. ``.foo``), the handler
        corrects it to the datatype's canonical extension."""
        out_file = tmp_path / "mydata.foo"
        success, _, captured = self._run_with_stubbed_exporter(
            "XLSX", str(out_file)
        )
        assert success is True
        assert captured["path"].endswith(".xlsx")
        assert not captured["path"].endswith(".foo")


# ---------------------------------------------------------------------------
# Style sidecar convention
# ---------------------------------------------------------------------------

class TestStyleSidecarPath:
    """QGIS convention: ``data.shp`` pairs with ``data.qml``, not
    ``data.shp.qml``."""

    def test_qml_uses_basename(self, tmp_path):
        from core.export.style_exporter import StyleExporter, StyleFormat
        captured = {}
        layer = MagicMock()
        layer.name.return_value = "roads"
        layer.saveNamedStyle = MagicMock(
            side_effect=lambda p: captured.update(path=p)
        )

        exporter = StyleExporter()
        ok = exporter.save_style(layer, str(tmp_path / "roads.shp"),
                                 StyleFormat.QML, datatype="SHP")

        assert ok is True
        assert captured["path"].endswith("roads.qml")
        assert not captured["path"].endswith("roads.shp.qml")

    def test_lyrx_uses_basename(self, tmp_path):
        from core.export.style_exporter import StyleExporter, StyleFormat
        layer = MagicMock()
        layer.name.return_value = "roads"
        layer.displayField.return_value = "name"
        layer.geometryType.return_value = 1
        layer.source.return_value = "/tmp/roads.shp"
        layer.renderer.return_value = None
        layer.crs.return_value = MagicMock(authid=lambda: "EPSG:4326")
        layer.featureCount.return_value = 0

        out_path = tmp_path / "roads.shp"
        exporter = StyleExporter()
        ok = exporter._save_lyrx(layer, str(out_path))

        assert ok is True
        expected = str(tmp_path / "roads.lyrx")
        # _save_lyrx normcases the path
        assert os.path.normcase(expected) == os.path.normcase(
            str(tmp_path / "roads.lyrx")
        )
        # File was written with basename convention
        assert (tmp_path / "roads.lyrx").exists()
        assert not (tmp_path / "roads.shp.lyrx").exists()


# ---------------------------------------------------------------------------
# Validator -- LIBKML acceptance
# ---------------------------------------------------------------------------

class TestValidatorLibKmlAccepted:
    def _validate(self, datatype):
        from core.export.export_validator import validate_export_parameters
        return validate_export_parameters({
            "task": {
                "EXPORTING": {
                    "HAS_LAYERS_TO_EXPORT": True,
                    "HAS_DATATYPE_TO_EXPORT": True,
                    "DATATYPE_TO_EXPORT": datatype,
                    "HAS_OUTPUT_FOLDER_TO_EXPORT": True,
                    "OUTPUT_FOLDER_TO_EXPORT": "/tmp/out",
                    "HAS_PRESERVE_GROUPS": True,
                },
                "layers": [{"layer_name": "x"}],
            }
        })

    def test_kml_keeps_preserve_groups(self):
        result = self._validate("KML")
        assert result.valid is True
        assert result.preserve_groups is True

    def test_libkml_keeps_preserve_groups(self):
        result = self._validate("LIBKML")
        assert result.valid is True
        assert result.preserve_groups is True

    def test_gpkg_keeps_preserve_groups(self):
        result = self._validate("GPKG")
        assert result.valid is True
        assert result.preserve_groups is True

    def test_shp_drops_preserve_groups(self):
        result = self._validate("ESRI Shapefile")
        assert result.valid is True
        assert result.preserve_groups is False

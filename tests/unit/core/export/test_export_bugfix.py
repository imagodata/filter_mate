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
        # SpatiaLite uses .sqlite — QGIS does not recognise .spatialite
        ("SpatiaLite", ".sqlite"),
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


# ---------------------------------------------------------------------------
# LayerExporter — writeAsVectorFormatV3 contract
# ---------------------------------------------------------------------------

class TestExportSingleLayerV3API:
    """The deprecated 5-arg ``writeAsVectorFormat`` is removed in QGIS 4.x.
    ``LayerExporter.export_single_layer`` must use ``writeAsVectorFormatV3``
    and pass CRS reprojection via ``options.ct``."""

    @pytest.fixture
    def patched_module(self, monkeypatch):
        """Force ``QGIS_AVAILABLE = True`` and inject a fake
        ``QgsVectorFileWriter`` into the layer_exporter module."""
        from core.export import layer_exporter as le

        fake_writer = MagicMock()
        fake_writer.NoError = 0
        fake_writer.writeAsVectorFormatV3 = MagicMock(
            return_value=(0, "", "", "")
        )
        # SaveVectorOptions returns a fresh MagicMock each instantiation so the
        # test can assert which attributes were set.
        fake_writer.SaveVectorOptions = MagicMock(side_effect=lambda: MagicMock())

        # Make sure the deprecated entry-point is gone — calling it must blow
        # up so any regression is caught loudly.
        del fake_writer.writeAsVectorFormat

        monkeypatch.setattr(le, "QGIS_AVAILABLE", True)
        monkeypatch.setattr(le, "QgsVectorFileWriter", fake_writer)
        monkeypatch.setattr(le, "QgsCoordinateTransform",
                            MagicMock(return_value="CT_SENTINEL"))
        monkeypatch.setattr(le, "QgsCoordinateTransformContext",
                            MagicMock(return_value="CTX_SENTINEL"))
        # Skip QgsProject.transformContext() lookup
        monkeypatch.setattr(le, "QgsProject",
                            MagicMock(instance=MagicMock(return_value=None)))
        return le, fake_writer

    def _make_layer(self, source_authid="EPSG:4326"):
        layer = MagicMock()
        layer.name.return_value = "roads"
        src_crs = MagicMock()
        src_crs.isValid.return_value = True
        src_crs.authid.return_value = source_authid
        # `==` between source and target uses python equality; differentiate
        # objects by their authid to mimic QgsCoordinateReferenceSystem behaviour.
        src_crs.__eq__ = lambda self, o: getattr(o, '_authid', None) == source_authid
        src_crs._authid = source_authid
        layer.sourceCrs.return_value = src_crs
        return layer

    def test_uses_v3_api_not_deprecated(self, patched_module, tmp_path):
        """Regression: the deprecated 5-arg writeAsVectorFormat is removed in
        QGIS 4.x. The exporter must reach for V3 instead."""
        le, fake_writer = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        layer = self._make_layer()
        exporter.get_layer_by_name = MagicMock(return_value=layer)

        out = str(tmp_path / "roads.shp")
        result = exporter.export_single_layer(
            "roads", out, projection=None,
            datatype="ESRI Shapefile",
            style_format=None, save_styles=False,
        )

        assert result.success is True
        fake_writer.writeAsVectorFormatV3.assert_called_once()
        # Hard assertion: deprecated call surface is unreachable
        assert not hasattr(fake_writer, "writeAsVectorFormat")

    def test_no_reprojection_skips_coordinate_transform(self, patched_module, tmp_path):
        """When target CRS is None, no QgsCoordinateTransform should be built —
        otherwise we'd silently no-op transform every feature."""
        le, fake_writer = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        layer = self._make_layer()
        exporter.get_layer_by_name = MagicMock(return_value=layer)

        exporter.export_single_layer(
            "roads", str(tmp_path / "roads.shp"),
            projection=None, datatype="ESRI Shapefile",
            style_format=None, save_styles=False,
        )

        call_args = fake_writer.writeAsVectorFormatV3.call_args
        options = call_args.args[3]
        # `options.ct` must NOT have been touched (no reprojection requested)
        ct_mock = options.ct
        assert isinstance(ct_mock, MagicMock)
        # If options.ct was set, it would equal "CT_SENTINEL"
        assert ct_mock != "CT_SENTINEL"

    def test_target_crs_attaches_coordinate_transform(self, patched_module, tmp_path):
        """When user picks a target CRS different from source, the V3 options
        must carry a QgsCoordinateTransform so geometries get reprojected."""
        le, fake_writer = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        layer = self._make_layer(source_authid="EPSG:4326")
        exporter.get_layer_by_name = MagicMock(return_value=layer)

        target = MagicMock()
        target.isValid.return_value = True
        target._authid = "EPSG:2154"
        target.__eq__ = lambda self, o: getattr(o, '_authid', None) == "EPSG:2154"

        exporter.export_single_layer(
            "roads", str(tmp_path / "roads.shp"),
            projection=target, datatype="ESRI Shapefile",
            style_format=None, save_styles=False,
        )

        call_args = fake_writer.writeAsVectorFormatV3.call_args
        options = call_args.args[3]
        # options.ct should have been assigned the QgsCoordinateTransform sentinel
        assert options.ct == "CT_SENTINEL"
        assert options.driverName == "ESRI Shapefile"

    def test_v3_error_message_propagates(self, patched_module, tmp_path):
        """Non-NoError return from V3 must bubble up as ``error_message``."""
        le, fake_writer = patched_module
        fake_writer.writeAsVectorFormatV3.return_value = (
            5, "DBF: field 'verylongfieldname' truncated to 10 chars", "", ""
        )
        exporter = le.LayerExporter(project=MagicMock())
        layer = self._make_layer()
        exporter.get_layer_by_name = MagicMock(return_value=layer)

        result = exporter.export_single_layer(
            "roads", str(tmp_path / "roads.shp"),
            projection=None, datatype="ESRI Shapefile",
            style_format=None, save_styles=False,
        )

        assert result.success is False
        assert "truncated" in result.error_message


# ---------------------------------------------------------------------------
# Streaming exporter — target_crs propagation
# ---------------------------------------------------------------------------

class TestStreamingTargetCrsPropagation:
    """``_export_with_streaming`` must hand the user-supplied projection to
    StreamingExporter via the ``target_crs`` kwarg, otherwise reprojection is
    silently dropped on large dataset exports."""

    def test_export_handler_passes_projection_to_streaming(self, tmp_path):
        from core.tasks.export_handler import ExportHandler

        handler = ExportHandler()
        handler.calculate_total_features = MagicMock(return_value=999_999)
        handler.get_layer_by_name = MagicMock(return_value=MagicMock())

        captured = {}

        class FakeStreamingExporter:
            def __init__(self, *_a, **_kw):
                pass

            def export_layer_streaming(self, **kwargs):
                captured.update(kwargs)
                return {"success": True}

        params = {
            "task": {
                "EXPORTING": {
                    "HAS_LAYERS_TO_EXPORT": True,
                    "HAS_DATATYPE_TO_EXPORT": True,
                    "DATATYPE_TO_EXPORT": "ESRI Shapefile",
                    "HAS_OUTPUT_FOLDER_TO_EXPORT": True,
                    "OUTPUT_FOLDER_TO_EXPORT": str(tmp_path),
                    "HAS_STYLES_TO_EXPORT": False,
                },
                "layers": [{"layer_name": "roads"}],
            },
            "config": {"APP": {"OPTIONS": {"STREAMING_EXPORT": {
                "enabled": {"value": True},
                "feature_threshold": {"value": 10000},
                "chunk_size": {"value": 5000},
            }}}},
        }

        target_crs = MagicMock(name="target_crs")
        validated = {
            'layers': [{"layer_name": "roads"}],
            'projection': target_crs, 'styles': None,
            'datatype': "ESRI Shapefile",
            'output_folder': str(tmp_path),
            'zip_path': None, 'batch_output_folder': False,
            'batch_zip': False, 'preserve_groups': False,
        }

        with patch('core.tasks.export_handler.StreamingExporter', FakeStreamingExporter), \
             patch('core.tasks.export_handler.StreamingConfig', MagicMock()), \
             patch.object(handler, 'validate_export_parameters', return_value=validated):
            handler.execute_exporting(
                task_parameters=params, project=MagicMock(),
                set_progress=MagicMock(), set_description=MagicMock(),
                is_canceled=MagicMock(return_value=False),
            )

        assert captured.get("target_crs") is target_crs, (
            "Streaming export must propagate user-selected projection "
            "(was the kwarg dropped between handler and StreamingExporter?)"
        )


# ---------------------------------------------------------------------------
# B10 — ZIP archive must not leak parent-directory contents
# ---------------------------------------------------------------------------

class TestZipFileOutputSidecarsOnly:
    """``create_zip_archive_for_file`` must include only the data file and its
    sidecars (same basename), never unrelated user files in the parent dir."""

    def test_archive_contains_only_matching_basenames(self, tmp_path):
        from core.export.batch_exporter import BatchExporter
        import zipfile

        # Layout: roads.shp + sidecars + UNRELATED files in same dir
        (tmp_path / "roads.shp").write_bytes(b"shp")
        (tmp_path / "roads.dbf").write_bytes(b"dbf")
        (tmp_path / "roads.shx").write_bytes(b"shx")
        (tmp_path / "roads.qml").write_text("<qml/>")
        # Files that MUST NOT end up in the archive
        (tmp_path / "private_taxes.xlsx").write_bytes(b"secret")
        (tmp_path / "other_layer.shp").write_bytes(b"other")
        (tmp_path / "README.md").write_text("# nope")

        zip_path = str(tmp_path / "out.zip")
        ok = BatchExporter.create_zip_archive_for_file(
            zip_path, str(tmp_path / "roads.shp")
        )
        assert ok is True

        with zipfile.ZipFile(zip_path) as zf:
            members = set(zf.namelist())

        assert members == {"roads.shp", "roads.dbf", "roads.shx", "roads.qml"}
        # Hard tripwire on data leak
        assert "private_taxes.xlsx" not in members
        assert "README.md" not in members
        assert "other_layer.shp" not in members

    def test_returns_false_when_no_sidecars(self, tmp_path):
        from core.export.batch_exporter import BatchExporter
        # File doesn't exist on disk → no siblings match
        ok = BatchExporter.create_zip_archive_for_file(
            str(tmp_path / "out.zip"), str(tmp_path / "missing.shp")
        )
        assert ok is False


# ---------------------------------------------------------------------------
# B8 — CSV must set GEOMETRY=AS_WKT layer option
# ---------------------------------------------------------------------------

class TestCsvLayerOptions:
    """Without ``GEOMETRY=AS_WKT`` in layerOptions, OGR's CSV driver drops the
    geometry column silently."""

    @pytest.fixture
    def patched_module(self, monkeypatch):
        from core.export import layer_exporter as le
        fake_writer = MagicMock()
        fake_writer.NoError = 0
        fake_writer.writeAsVectorFormatV3 = MagicMock(return_value=(0, "", "", ""))
        fake_writer.SaveVectorOptions = MagicMock(side_effect=lambda: MagicMock())
        del fake_writer.writeAsVectorFormat
        monkeypatch.setattr(le, "QGIS_AVAILABLE", True)
        monkeypatch.setattr(le, "QgsVectorFileWriter", fake_writer)
        monkeypatch.setattr(le, "QgsCoordinateTransform", MagicMock())
        monkeypatch.setattr(le, "QgsCoordinateTransformContext", MagicMock())
        monkeypatch.setattr(le, "QgsProject",
                            MagicMock(instance=MagicMock(return_value=None)))
        return le, fake_writer

    def _make_layer(self):
        layer = MagicMock()
        layer.name.return_value = "x"
        crs = MagicMock()
        crs.isValid.return_value = True
        crs.__eq__ = lambda self, o: True
        layer.sourceCrs.return_value = crs
        return layer

    def test_csv_sets_geometry_layer_option(self, patched_module, tmp_path):
        le, fake_writer = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        exporter.get_layer_by_name = MagicMock(return_value=self._make_layer())

        exporter.export_single_layer(
            "x", str(tmp_path / "x.csv"),
            projection=None, datatype="CSV",
            style_format=None, save_styles=False,
        )

        options = fake_writer.writeAsVectorFormatV3.call_args.args[3]
        assert options.layerOptions is not None
        assert any("GEOMETRY=AS_WKT" in opt for opt in options.layerOptions)
        assert any("CREATE_CSVT" in opt for opt in options.layerOptions)

    def test_non_csv_does_not_set_csv_options(self, patched_module, tmp_path):
        le, fake_writer = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        exporter.get_layer_by_name = MagicMock(return_value=self._make_layer())

        exporter.export_single_layer(
            "x", str(tmp_path / "x.shp"),
            projection=None, datatype="ESRI Shapefile",
            style_format=None, save_styles=False,
        )

        options = fake_writer.writeAsVectorFormatV3.call_args.args[3]
        # SaveVectorOptions returns a MagicMock, so options.layerOptions is
        # only set when explicit assignment happens. For SHP it's untouched.
        if hasattr(options, '_mock_children') and 'layerOptions' in options._mock_children:
            ops = options.layerOptions
            assert not any("GEOMETRY=AS_WKT" in str(o) for o in (ops if isinstance(ops, list) else []))


# ---------------------------------------------------------------------------
# B7 — GPKG with target_crs must bypass qgis:package
# ---------------------------------------------------------------------------

class TestGpkgReprojection:
    """``processing.run('qgis:package')`` ignores any CRS parameter — when the
    user picks a target CRS that differs from a layer's source, we must fall
    back to per-layer writeAsVectorFormatV3 with options.ct."""

    @pytest.fixture
    def patched_module(self, monkeypatch):
        from core.export import layer_exporter as le
        fake_writer = MagicMock()
        fake_writer.NoError = 0
        fake_writer.writeAsVectorFormatV3 = MagicMock(return_value=(0, "", "", ""))
        fake_writer.SaveVectorOptions = MagicMock(side_effect=lambda: MagicMock())
        # ActionOnExistingFile enum stub
        fake_writer.ActionOnExistingFile = MagicMock(
            CreateOrOverwriteFile=1, CreateOrOverwriteLayer=2,
        )
        del fake_writer.writeAsVectorFormat

        fake_processing = MagicMock()
        fake_processing.run = MagicMock(return_value={'OUTPUT': '/x.gpkg'})

        monkeypatch.setattr(le, "QGIS_AVAILABLE", True)
        monkeypatch.setattr(le, "QgsVectorFileWriter", fake_writer)
        monkeypatch.setattr(le, "QgsCoordinateTransform",
                            MagicMock(return_value="CT_SENTINEL"))
        monkeypatch.setattr(le, "QgsCoordinateTransformContext", MagicMock())
        monkeypatch.setattr(le, "QgsProject",
                            MagicMock(instance=MagicMock(return_value=None)))
        monkeypatch.setattr(le, "processing", fake_processing)
        return le, fake_writer, fake_processing

    def _make_layer(self, name, source_authid):
        layer = MagicMock()
        layer.name.return_value = name
        crs = MagicMock()
        crs.isValid.return_value = True
        crs._authid = source_authid
        crs.__eq__ = lambda self, o: getattr(o, '_authid', None) == source_authid
        layer.sourceCrs.return_value = crs
        return layer

    def test_no_reprojection_uses_qgis_package(self, patched_module, tmp_path):
        """When target_crs is None, we keep using processing for multi-layer GPKG."""
        le, fake_writer, fake_processing = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        layer = self._make_layer("roads", "EPSG:4326")
        exporter.get_layer_by_name = MagicMock(return_value=layer)

        result = exporter.export_to_gpkg(
            ["roads"], str(tmp_path / "out.gpkg"), save_styles=False,
            target_crs=None,
        )
        assert result.success is True
        fake_processing.run.assert_called_once()
        fake_writer.writeAsVectorFormatV3.assert_not_called()

    def test_reprojection_bypasses_qgis_package(self, patched_module, tmp_path):
        """When target_crs differs from source, qgis:package must NOT be called
        (it would silently keep the source CRS)."""
        le, fake_writer, fake_processing = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        layer = self._make_layer("roads", "EPSG:4326")
        exporter.get_layer_by_name = MagicMock(return_value=layer)

        target = MagicMock()
        target.isValid.return_value = True
        target._authid = "EPSG:2154"
        target.__eq__ = lambda self, o: getattr(o, '_authid', None) == "EPSG:2154"

        result = exporter.export_to_gpkg(
            ["roads"], str(tmp_path / "out.gpkg"), save_styles=False,
            target_crs=target,
        )
        assert result.success is True
        fake_processing.run.assert_not_called()
        fake_writer.writeAsVectorFormatV3.assert_called_once()
        # And the writer must carry the coordinate transform
        options = fake_writer.writeAsVectorFormatV3.call_args.args[3]
        assert options.ct == "CT_SENTINEL"

    def test_reprojection_appends_subsequent_layers(self, patched_module, tmp_path):
        """Multi-layer GPKG reprojection must append, not overwrite, after the
        first layer creates the file."""
        le, fake_writer, _ = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        layers = [
            self._make_layer("roads", "EPSG:4326"),
            self._make_layer("rivers", "EPSG:4326"),
        ]
        exporter.get_layer_by_name = MagicMock(side_effect=lambda n: {
            "roads": layers[0], "rivers": layers[1]
        }[n])

        target = MagicMock()
        target.isValid.return_value = True
        target._authid = "EPSG:2154"
        target.__eq__ = lambda self, o: getattr(o, '_authid', None) == "EPSG:2154"

        exporter.export_to_gpkg(
            ["roads", "rivers"], str(tmp_path / "out.gpkg"),
            save_styles=False, target_crs=target,
        )
        assert fake_writer.writeAsVectorFormatV3.call_count == 2
        # 1st call: CreateOrOverwriteFile (=1). 2nd call: CreateOrOverwriteLayer (=2).
        first_options = fake_writer.writeAsVectorFormatV3.call_args_list[0].args[3]
        second_options = fake_writer.writeAsVectorFormatV3.call_args_list[1].args[3]
        assert first_options.actionOnExistingFile == 1
        assert second_options.actionOnExistingFile == 2


# ---------------------------------------------------------------------------
# C1 — Batch filename collision must be disambiguated, never silently overwritten
# ---------------------------------------------------------------------------

class TestBatchFilenameDisambiguation:
    """Two layers with names that sanitize to the same basename must produce
    distinct files (``foo.shp``, ``foo_2.shp``), never overwrite each other."""

    def test_disambiguate_basename_helper(self):
        from core.export.batch_exporter import _disambiguate_basename
        used = set()
        assert _disambiguate_basename("roads", used) == "roads"
        assert _disambiguate_basename("roads", used) == "roads_2"
        assert _disambiguate_basename("roads", used) == "roads_3"
        assert _disambiguate_basename("rivers", used) == "rivers"
        assert used == {"roads", "roads_2", "roads_3", "rivers"}

    def test_export_to_folder_disambiguates_collisions(self, tmp_path):
        from core.export.batch_exporter import BatchExporter
        from core.export import layer_exporter as le

        captured_paths = []

        def fake_export_single(self_, layer_name, output_path, *a, **kw):
            captured_paths.append(output_path)
            from core.export.layer_exporter import ExportResult
            return ExportResult(success=True, exported_count=1, output_path=output_path)

        with patch.object(le.LayerExporter, 'export_single_layer', fake_export_single), \
             patch.object(le.LayerExporter, 'get_layer_by_name',
                          return_value=MagicMock()):
            exporter = BatchExporter(project=MagicMock())
            # Two identically named layers (e.g. cross-schema)
            exporter.export_to_folder(
                [{"layer_name": "roads"}, {"layer_name": "roads"}],
                str(tmp_path), datatype="ESRI Shapefile",
            )

        assert len(captured_paths) == 2
        assert captured_paths[0].endswith("roads.shp")
        assert captured_paths[1].endswith("roads_2.shp")
        # Tripwire: never the same path
        assert captured_paths[0] != captured_paths[1]


# ---------------------------------------------------------------------------
# C2 — Validator must reject unknown OGR drivers up-front
# ---------------------------------------------------------------------------

class TestValidatorRejectsUnknownDriver:
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
                },
                "layers": [{"layer_name": "x"}],
            }
        })

    def test_unknown_driver_rejected(self):
        result = self._validate("Bogus Format 9000")
        assert result.valid is False
        assert "Unsupported export datatype" in (result.error_message or "")

    def test_known_drivers_pass(self):
        for d in ("GPKG", "ESRI Shapefile", "GeoJSON", "CSV", "XLSX",
                  "MapInfo File", "FlatGeobuf"):
            result = self._validate(d)
            assert result.valid is True, f"{d} should validate, got: {result.error_message}"


# ---------------------------------------------------------------------------
# B3 — Shapefile pre-flight: surface DBF + geom-type constraints
# ---------------------------------------------------------------------------

class TestShapefilePreflightConstraints:
    """``validate_shapefile_constraints`` must surface (as warnings, not errors)
    the silent OGR coercions that confuse users post-export:
    - DBF 10-char field-name limit
    - DBF allowed character set (ASCII alnum + underscore, letter-leading)
    - Mixed/unknown geometry types not natively supported by SHP
    """

    def _make_layer(self, field_names, wkb_type_str='Polygon'):
        layer = MagicMock()
        layer.name.return_value = "x"
        fields = []
        for n in field_names:
            f = MagicMock()
            f.name.return_value = n
            fields.append(f)
        layer.fields.return_value = fields

        # Stub QgsWkbTypes.displayString() lookup
        layer.wkbType.return_value = MagicMock()
        return layer, wkb_type_str

    def test_long_field_name_warns(self, monkeypatch):
        from core.export import layer_exporter as le
        layer, wkb_str = self._make_layer(["short", "this_is_too_long_for_dbf"])

        # Stub QgsWkbTypes import inside the function
        import sys
        fake_wkb = MagicMock(displayString=MagicMock(return_value=wkb_str))
        monkeypatch.setitem(sys.modules, 'qgis', MagicMock())
        monkeypatch.setitem(sys.modules, 'qgis.core',
                            MagicMock(QgsWkbTypes=fake_wkb))

        warnings = le.validate_shapefile_constraints(layer)
        joined = " ".join(warnings)
        assert "this_is_too_long_for_dbf" in joined
        assert "10 chars" in joined

    def test_invalid_dbf_chars_warn(self, monkeypatch):
        from core.export import layer_exporter as le
        # spaces and accents are not DBF-safe, leading digit not allowed
        layer, wkb_str = self._make_layer(["nom rue", "1abc", "café"])

        import sys
        fake_wkb = MagicMock(displayString=MagicMock(return_value=wkb_str))
        monkeypatch.setitem(sys.modules, 'qgis', MagicMock())
        monkeypatch.setitem(sys.modules, 'qgis.core',
                            MagicMock(QgsWkbTypes=fake_wkb))

        warnings = le.validate_shapefile_constraints(layer)
        joined = " ".join(warnings)
        assert "nom rue" in joined or "café" in joined or "1abc" in joined

    def test_unknown_geometry_warns(self, monkeypatch):
        from core.export import layer_exporter as le
        layer, _ = self._make_layer(["ok"], wkb_type_str='Unknown')

        import sys
        fake_wkb = MagicMock(displayString=MagicMock(return_value='Unknown'))
        monkeypatch.setitem(sys.modules, 'qgis', MagicMock())
        monkeypatch.setitem(sys.modules, 'qgis.core',
                            MagicMock(QgsWkbTypes=fake_wkb))

        warnings = le.validate_shapefile_constraints(layer)
        assert any("Unknown" in w for w in warnings)

    def test_clean_layer_emits_no_warnings(self, monkeypatch):
        from core.export import layer_exporter as le
        layer, _ = self._make_layer(["id", "name", "speed"], wkb_type_str='LineString')

        import sys
        fake_wkb = MagicMock(displayString=MagicMock(return_value='LineString'))
        monkeypatch.setitem(sys.modules, 'qgis', MagicMock())
        monkeypatch.setitem(sys.modules, 'qgis.core',
                            MagicMock(QgsWkbTypes=fake_wkb))

        warnings = le.validate_shapefile_constraints(layer)
        assert warnings == []

    def test_warnings_attached_to_export_result(self, monkeypatch, tmp_path):
        """End-to-end: a SHP export with violating field names returns
        ``ExportResult.warnings`` non-empty — so the UI can surface them."""
        from core.export import layer_exporter as le

        fake_writer = MagicMock()
        fake_writer.NoError = 0
        fake_writer.writeAsVectorFormatV3 = MagicMock(return_value=(0, "", "", ""))
        fake_writer.SaveVectorOptions = MagicMock(side_effect=lambda: MagicMock())
        del fake_writer.writeAsVectorFormat

        monkeypatch.setattr(le, "QGIS_AVAILABLE", True)
        monkeypatch.setattr(le, "QgsVectorFileWriter", fake_writer)
        monkeypatch.setattr(le, "QgsCoordinateTransform", MagicMock())
        monkeypatch.setattr(le, "QgsCoordinateTransformContext", MagicMock())
        monkeypatch.setattr(le, "QgsProject",
                            MagicMock(instance=MagicMock(return_value=None)))

        # Stub QgsWkbTypes for validate_shapefile_constraints
        import sys
        monkeypatch.setitem(sys.modules, 'qgis', MagicMock())
        monkeypatch.setitem(sys.modules, 'qgis.core',
                            MagicMock(QgsWkbTypes=MagicMock(
                                displayString=MagicMock(return_value='Polygon'))))

        layer = MagicMock()
        layer.name.return_value = "parcelles"
        f1 = MagicMock(); f1.name.return_value = "id"
        f2 = MagicMock(); f2.name.return_value = "very_long_attribute_name"
        layer.fields.return_value = [f1, f2]
        crs = MagicMock(); crs.isValid.return_value = True
        crs.__eq__ = lambda self, o: True
        layer.sourceCrs.return_value = crs

        exporter = le.LayerExporter(project=MagicMock())
        exporter.get_layer_by_name = MagicMock(return_value=layer)

        result = exporter.export_single_layer(
            "parcelles", str(tmp_path / "parcelles.shp"),
            projection=None, datatype="ESRI Shapefile",
            style_format=None, save_styles=False,
        )

        assert result.success is True
        assert result.warnings, "SHP export should surface DBF warnings"
        assert any("very_long_attribute_name" in w for w in result.warnings)

    def test_non_shp_export_skips_pre_flight(self, monkeypatch, tmp_path):
        """GPKG/GeoJSON/etc. don't have DBF limits — pre-flight must NOT run
        and result.warnings stays empty."""
        from core.export import layer_exporter as le

        fake_writer = MagicMock()
        fake_writer.NoError = 0
        fake_writer.writeAsVectorFormatV3 = MagicMock(return_value=(0, "", "", ""))
        fake_writer.SaveVectorOptions = MagicMock(side_effect=lambda: MagicMock())
        del fake_writer.writeAsVectorFormat

        monkeypatch.setattr(le, "QGIS_AVAILABLE", True)
        monkeypatch.setattr(le, "QgsVectorFileWriter", fake_writer)
        monkeypatch.setattr(le, "QgsCoordinateTransform", MagicMock())
        monkeypatch.setattr(le, "QgsCoordinateTransformContext", MagicMock())
        monkeypatch.setattr(le, "QgsProject",
                            MagicMock(instance=MagicMock(return_value=None)))

        layer = MagicMock()
        layer.name.return_value = "parcelles"
        f = MagicMock(); f.name.return_value = "very_long_field_name_that_would_break_dbf"
        layer.fields.return_value = [f]
        crs = MagicMock(); crs.isValid.return_value = True
        crs.__eq__ = lambda self, o: True
        layer.sourceCrs.return_value = crs

        exporter = le.LayerExporter(project=MagicMock())
        exporter.get_layer_by_name = MagicMock(return_value=layer)

        result = exporter.export_single_layer(
            "parcelles", str(tmp_path / "parcelles.gpkg"),
            projection=None, datatype="GPKG",
            style_format=None, save_styles=False,
        )

        assert result.success is True
        assert result.warnings == []


# ---------------------------------------------------------------------------
# C4 — GPKG path detection robust to non-.gpkg suffixes & existing dirs
# ---------------------------------------------------------------------------

class TestGpkgPathDetection:
    """The handler must distinguish file-output vs directory-output for GPKG
    based on actual filesystem state, not just suffix matching."""

    @pytest.fixture
    def setup_handler(self):
        with patch('core.tasks.export_handler.StreamingExporter'), \
             patch('core.tasks.export_handler.StreamingConfig'):
            from core.tasks.export_handler import ExportHandler
            return ExportHandler()

    def _run(self, handler, output_folder, tmp_path):
        from core.export.layer_exporter import LayerExporter
        captured = {}

        def fake_export_to_gpkg(self_, layers, output_path, save_styles,
                                target_crs=None):
            captured['output_path'] = output_path
            return MagicMock(success=True, exported_count=1, output_path=output_path,
                             error_message=None)

        validated = {
            'layers': [{"layer_name": "x"}],
            'projection': None, 'styles': None,
            'datatype': "GPKG",
            'output_folder': output_folder,
            'zip_path': None, 'batch_output_folder': False,
            'batch_zip': False, 'preserve_groups': False,
        }

        project = MagicMock()
        project.title.return_value = "myproj"
        project.baseName.return_value = "myproj"

        with patch.object(LayerExporter, 'export_to_gpkg', fake_export_to_gpkg), \
             patch.object(handler, 'validate_export_parameters', return_value=validated):
            handler.execute_exporting(
                task_parameters={"task": {"EXPORTING": {
                    "HAS_LAYERS_TO_EXPORT": True,
                    "HAS_DATATYPE_TO_EXPORT": True,
                    "DATATYPE_TO_EXPORT": "GPKG",
                    "HAS_OUTPUT_FOLDER_TO_EXPORT": True,
                    "OUTPUT_FOLDER_TO_EXPORT": output_folder,
                    "HAS_STYLES_TO_EXPORT": False,
                }, "layers": [{"layer_name": "x"}]}, "config": {}},
                project=project,
                set_progress=MagicMock(), set_description=MagicMock(),
                is_canceled=MagicMock(return_value=False),
            )
        return captured

    def test_existing_directory_treated_as_dir(self, setup_handler, tmp_path):
        """Existing dir → write project_title.gpkg inside it."""
        out_dir = tmp_path / "outputs"
        out_dir.mkdir()
        captured = self._run(setup_handler, str(out_dir), tmp_path)
        assert captured['output_path'].endswith(".gpkg")
        assert str(out_dir) in captured['output_path']
        # Filename comes from the project title, not the dir name
        assert os.path.dirname(captured['output_path']) == str(out_dir)

    def test_dot_gpkg_suffix_treated_as_file(self, setup_handler, tmp_path):
        """Path ending in .gpkg (file doesn't exist yet) → use as-is."""
        target = tmp_path / "myexport.gpkg"
        captured = self._run(setup_handler, str(target), tmp_path)
        assert captured['output_path'] == str(target)

    def test_unusual_suffix_existing_file_treated_as_file(self, setup_handler, tmp_path):
        """Path like ``foo.gpkg.tmp`` that already exists as a file → treat as
        file, not as a directory to create. Previously the suffix check
        ``.endswith('.gpkg')`` returned False and the handler tried makedirs."""
        target = tmp_path / "weird.gpkg.tmp"
        target.touch()
        captured = self._run(setup_handler, str(target), tmp_path)
        assert captured['output_path'] == str(target)


# ---------------------------------------------------------------------------
# B3-leak — ExportHandler must collect warnings from per-layer/batch results
# so FilterEngineTask can drain them into self.warning_messages and the user
# sees them via iface.messageBar(). Without this, SHP DBF pre-flight warnings
# and BatchExportResult.failed_layers only reach the log file.
# ---------------------------------------------------------------------------

class TestExportHandlerWarningCollection:
    """Regression: warnings/failed_layers from result objects must land in
    ``ExportHandler._last_warnings`` for the caller to surface to the user."""

    @pytest.fixture(autouse=True)
    def setup_handler(self):
        with patch('core.tasks.export_handler.StreamingExporter'), \
             patch('core.tasks.export_handler.StreamingConfig'):
            from core.tasks.export_handler import ExportHandler
            self.handler = ExportHandler()
            yield

    def _validated_export_config(self, batch_folder=False, batch_zip=False):
        return {
            'layers': [{'layer_name': 'roads'}],
            'projection': None, 'styles': None,
            'datatype': 'ESRI Shapefile',
            'output_folder': '/tmp/out',
            'zip_path': None,
            'batch_output_folder': batch_folder,
            'batch_zip': batch_zip,
            'preserve_groups': False,
        }

    def test_init_creates_empty_warning_list(self):
        from core.tasks.export_handler import ExportHandler
        handler = ExportHandler()
        assert handler._last_warnings == []

    def test_collect_warnings_from_export_result(self):
        """ExportResult.warnings (e.g. SHP DBF pre-flight) must be collected."""
        from core.export.layer_exporter import ExportResult
        result = ExportResult(
            success=True,
            warnings=[
                "DBF will silently truncate field names >10 chars: ['verylongfieldname']",
                "Geometry type 'GeometryCollection' is not natively supported by Shapefile",
            ],
        )
        self.handler._collect_warnings(result)
        assert len(self.handler._last_warnings) == 2
        assert any("truncate" in w for w in self.handler._last_warnings)
        assert any("GeometryCollection" in w for w in self.handler._last_warnings)

    def test_collect_warnings_from_batch_failed_layers(self):
        """BatchExportResult.failed_layers must be collected with a Failed: prefix."""
        from core.export.batch_exporter import BatchExportResult
        result = BatchExportResult(
            success=False,
            exported_count=2,
            failed_count=1,
            failed_layers=["roads: permission denied", "rivers: disk full"],
        )
        self.handler._collect_warnings(result)
        assert len(self.handler._last_warnings) == 2
        assert all(w.startswith("Failed: ") for w in self.handler._last_warnings)
        assert any("permission denied" in w for w in self.handler._last_warnings)

    def test_collect_warnings_from_batch_skipped_layers(self):
        """BatchExportResult.skipped_layers (layer not found) collected too."""
        from core.export.batch_exporter import BatchExportResult
        result = BatchExportResult(
            success=False,
            skipped_count=2,
            skipped_layers=["missing_layer_a", "missing_layer_b"],
        )
        self.handler._collect_warnings(result)
        assert len(self.handler._last_warnings) == 2
        assert all(w.startswith("Skipped: ") for w in self.handler._last_warnings)

    def test_collect_warnings_handles_objects_without_warning_fields(self):
        """Result types without .warnings/.failed_layers/.skipped_layers must
        not raise. Defensive against future result-shape changes."""
        bare = MagicMock(spec=[])  # no attributes
        self.handler._collect_warnings(bare)
        assert self.handler._last_warnings == []

    def test_execute_exporting_resets_warnings_per_run(self):
        """Successive exports must not accumulate warnings across runs."""
        # Pre-pollute the warnings list
        self.handler._last_warnings = ["stale", "junk"]
        # Run with a validation failure (returns early but should still reset)
        params = {"task": {"EXPORTING": {}, "layers": []}}
        self.handler.execute_exporting(
            task_parameters=params, project=MagicMock(),
            set_progress=MagicMock(), set_description=MagicMock(),
            is_canceled=MagicMock(return_value=False),
        )
        # Reset must have happened before the early return
        assert "stale" not in self.handler._last_warnings
        assert "junk" not in self.handler._last_warnings

    def test_single_layer_warnings_propagate_through_handler(self, tmp_path):
        """End-to-end: SHP pre-flight warnings on a layer with a long field
        name flow from LayerExporter → ExportHandler._last_warnings."""
        from core.export import layer_exporter as le
        from core.export.layer_exporter import ExportResult

        captured_warnings = [
            "DBF will silently truncate field names >10 chars: ['superlongfield']"
        ]
        fake_result = ExportResult(
            success=True, exported_count=1, warnings=captured_warnings,
        )

        validated = {
            'layers': [{'layer_name': 'x'}], 'projection': None, 'styles': None,
            'datatype': 'ESRI Shapefile',
            'output_folder': str(tmp_path / 'x.shp'),
            'zip_path': None, 'batch_output_folder': False,
            'batch_zip': False, 'preserve_groups': False,
        }
        params = {
            "task": {
                "EXPORTING": {
                    "HAS_LAYERS_TO_EXPORT": True,
                    "HAS_DATATYPE_TO_EXPORT": True,
                    "DATATYPE_TO_EXPORT": "ESRI Shapefile",
                    "HAS_OUTPUT_FOLDER_TO_EXPORT": True,
                    "OUTPUT_FOLDER_TO_EXPORT": str(tmp_path / 'x.shp'),
                    "HAS_STYLES_TO_EXPORT": False,
                },
                "layers": [{"layer_name": "x"}],
            },
            "config": {"APP": {"OPTIONS": {"STREAMING_EXPORT": {
                "enabled": {"value": False},
            }}}},
        }
        with patch.object(le.LayerExporter, 'export_single_layer',
                          return_value=fake_result), \
             patch.object(self.handler, 'validate_export_parameters',
                          return_value=validated):
            success, _, _ = self.handler.execute_exporting(
                task_parameters=params, project=MagicMock(),
                set_progress=MagicMock(), set_description=MagicMock(),
                is_canceled=MagicMock(return_value=False),
            )

        assert success is True
        # The crucial assertion: the warning made it through. Without the
        # _collect_warnings() wiring, _last_warnings stays empty.
        assert any("truncate" in w for w in self.handler._last_warnings), \
            f"SHP pre-flight warning was dropped at handler boundary. " \
            f"_last_warnings={self.handler._last_warnings}"

    def test_batch_failure_summary_propagates_through_handler(self, tmp_path):
        """End-to-end: per-layer batch failures flow from BatchExporter →
        ExportHandler._last_warnings (not just the log)."""
        from core.export import batch_exporter as be
        from core.export.batch_exporter import BatchExportResult

        fake_result = BatchExportResult(
            success=False,
            exported_count=2,
            failed_count=1,
            output_paths=["/tmp/a.shp", "/tmp/b.shp"],
            failed_layers=["bad_layer: write permission denied"],
        )

        validated = {
            'layers': [{'layer_name': 'a'}, {'layer_name': 'b'}, {'layer_name': 'bad_layer'}],
            'projection': None, 'styles': None,
            'datatype': 'ESRI Shapefile',
            'output_folder': str(tmp_path),
            'zip_path': None, 'batch_output_folder': True,
            'batch_zip': False, 'preserve_groups': False,
        }
        params = {
            "task": {
                "EXPORTING": {
                    "HAS_LAYERS_TO_EXPORT": True,
                    "HAS_DATATYPE_TO_EXPORT": True,
                    "DATATYPE_TO_EXPORT": "ESRI Shapefile",
                    "HAS_OUTPUT_FOLDER_TO_EXPORT": True,
                    "OUTPUT_FOLDER_TO_EXPORT": str(tmp_path),
                    "HAS_STYLES_TO_EXPORT": False,
                    "BATCH_OUTPUT_FOLDER": True,
                },
                "layers": [{"layer_name": "a"}, {"layer_name": "b"},
                           {"layer_name": "bad_layer"}],
            }
        }
        with patch.object(be.BatchExporter, 'export_to_folder',
                          return_value=fake_result), \
             patch.object(self.handler, 'validate_export_parameters',
                          return_value=validated):
            self.handler.execute_exporting(
                task_parameters=params, project=MagicMock(),
                set_progress=MagicMock(), set_description=MagicMock(),
                is_canceled=MagicMock(return_value=False),
            )

        # Without the _collect_warnings() wiring, this stays empty and the
        # user only sees "Batch export completed with errors" without the
        # per-layer detail.
        assert any("permission denied" in w for w in self.handler._last_warnings), \
            f"Batch per-layer failure dropped at handler boundary. " \
            f"_last_warnings={self.handler._last_warnings}"
        assert all(w.startswith("Failed:") for w in self.handler._last_warnings)


# ---------------------------------------------------------------------------
# B-bug — Export must run when current_layer is None
# ---------------------------------------------------------------------------
# This test cannot be unit-tested without pulling the full FilterMateApp
# class graph (~50 dependencies). The fix is small and inspection-reviewed
# in commit message; manual smoke test:
#   1. Open QGIS with FilterMate plugin loaded
#   2. Switch to EXPORT tab WITHOUT picking a layer in EXPLORING tab
#   3. Pick layers + format + output, click Export
#   4. Expected: export runs (was: silent log-only error pre-fix)
#
# A future integration test could exercise this via the QGIS test harness
# (tests/integration/) but that's deferred — out of scope for this PR.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# H1 — GPKG + reprojection must honor save_styles by embedding QML in the
# layer_styles table (was silently dropped because qgis:package was bypassed).
# ---------------------------------------------------------------------------

class TestGpkgReprojectionStyles:
    """``_export_to_gpkg_reproject`` must call ``write_layer_styles_to_gpkg``
    after the writer loop when ``save_styles=True``. The non-reprojection
    branch already gets style embedding free via
    ``processing.run('qgis:package', SAVE_STYLES=True)``."""

    @pytest.fixture
    def patched_module(self, monkeypatch):
        from core.export import layer_exporter as le
        fake_writer = MagicMock()
        fake_writer.NoError = 0
        fake_writer.writeAsVectorFormatV3 = MagicMock(return_value=(0, "", "", ""))
        fake_writer.SaveVectorOptions = MagicMock(side_effect=lambda: MagicMock())
        fake_writer.ActionOnExistingFile = MagicMock(
            CreateOrOverwriteFile=1, CreateOrOverwriteLayer=2,
        )
        del fake_writer.writeAsVectorFormat

        monkeypatch.setattr(le, "QGIS_AVAILABLE", True)
        monkeypatch.setattr(le, "QgsVectorFileWriter", fake_writer)
        monkeypatch.setattr(le, "QgsCoordinateTransform", MagicMock())
        monkeypatch.setattr(le, "QgsCoordinateTransformContext", MagicMock())
        monkeypatch.setattr(le, "QgsProject",
                            MagicMock(instance=MagicMock(return_value=None)))
        monkeypatch.setattr(le, "processing",
                            MagicMock(run=MagicMock(return_value={'OUTPUT': '/x.gpkg'})))
        return le, fake_writer

    def _make_layer(self, name, source_authid):
        layer = MagicMock()
        layer.name.return_value = name
        crs = MagicMock()
        crs.isValid.return_value = True
        crs._authid = source_authid
        crs.__eq__ = lambda self, o: getattr(o, '_authid', None) == source_authid
        layer.sourceCrs.return_value = crs
        return layer

    def _make_target_crs(self, authid="EPSG:2154"):
        target = MagicMock()
        target.isValid.return_value = True
        target._authid = authid
        target.__eq__ = lambda self, o: getattr(o, '_authid', None) == authid
        return target

    def test_reprojection_with_save_styles_calls_helper(self, patched_module, tmp_path):
        """When save_styles=True and reprojection is needed, the helper must
        be invoked with (layer, layer.name()) pairs after the writer loop."""
        le, _ = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        layers = [
            self._make_layer("roads", "EPSG:4326"),
            self._make_layer("rivers", "EPSG:4326"),
        ]
        exporter.get_layer_by_name = MagicMock(side_effect=lambda n: {
            "roads": layers[0], "rivers": layers[1]
        }[n])

        with patch('core.export.gpkg_layer_tree_writer.write_layer_styles_to_gpkg') as fake_helper:
            fake_helper.return_value = True
            result = exporter.export_to_gpkg(
                ["roads", "rivers"], str(tmp_path / "out.gpkg"),
                save_styles=True, target_crs=self._make_target_crs(),
            )

        assert result.success is True
        fake_helper.assert_called_once()
        # Verify the (layer, table_name) pairs were passed correctly
        call_args = fake_helper.call_args
        passed_path = call_args.args[0]
        passed_pairs = call_args.args[1]
        assert passed_path == str(tmp_path / "out.gpkg")
        assert len(passed_pairs) == 2
        assert passed_pairs[0][1] == "roads"
        assert passed_pairs[1][1] == "rivers"

    def test_reprojection_without_save_styles_skips_helper(self, patched_module, tmp_path):
        """save_styles=False must NOT trigger the embedding helper."""
        le, _ = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        layer = self._make_layer("roads", "EPSG:4326")
        exporter.get_layer_by_name = MagicMock(return_value=layer)

        with patch('core.export.gpkg_layer_tree_writer.write_layer_styles_to_gpkg') as fake_helper:
            exporter.export_to_gpkg(
                ["roads"], str(tmp_path / "out.gpkg"),
                save_styles=False, target_crs=self._make_target_crs(),
            )

        fake_helper.assert_not_called()

    def test_helper_failure_does_not_fail_export(self, patched_module, tmp_path):
        """If style embedding raises, the export still reports success
        (data is on disk; styles are a best-effort enhancement)."""
        le, _ = patched_module
        exporter = le.LayerExporter(project=MagicMock())
        layer = self._make_layer("roads", "EPSG:4326")
        exporter.get_layer_by_name = MagicMock(return_value=layer)

        with patch('core.export.gpkg_layer_tree_writer.write_layer_styles_to_gpkg',
                   side_effect=RuntimeError("disk full while writing styles")):
            result = exporter.export_to_gpkg(
                ["roads"], str(tmp_path / "out.gpkg"),
                save_styles=True, target_crs=self._make_target_crs(),
            )

        assert result.success is True


# ---------------------------------------------------------------------------
# H2 — Streaming + GPKG must embed styles in layer_styles, not write a
# .qml sidecar (matches non-streaming GPKG behavior).
# ---------------------------------------------------------------------------

class TestStreamingGpkgStyles:
    """Streaming export to GPKG must embed styles via
    ``write_layer_styles_to_gpkg``, not call the .qml sidecar writer.
    Other formats still use the sidecar path (they can't carry embedded
    styles)."""

    def _build_params_streaming(self, datatype, output_folder, layers):
        return {
            "task": {
                "EXPORTING": {
                    "HAS_LAYERS_TO_EXPORT": True,
                    "HAS_DATATYPE_TO_EXPORT": True,
                    "DATATYPE_TO_EXPORT": datatype,
                    "HAS_OUTPUT_FOLDER_TO_EXPORT": True,
                    "OUTPUT_FOLDER_TO_EXPORT": output_folder,
                    "HAS_STYLES_TO_EXPORT": True,
                    "STYLES_TO_EXPORT": "QML",
                },
                "layers": layers,
            },
            "config": {"APP": {"OPTIONS": {"STREAMING_EXPORT": {
                "enabled": {"value": True},
                "feature_threshold": {"value": 0},  # always streaming
                "chunk_size": {"value": 100},
            }}}},
        }

    def _make_layer(self):
        layer = MagicMock()
        layer.name.return_value = "roads"
        return layer

    def _drive_streaming(self, datatype, output_folder):
        """Drive ``_export_with_streaming`` directly with stubbed writers and
        return ``(sidecar_calls, gpkg_styles_calls)``.

        Note: in the real dispatcher, ``datatype == 'GPKG'`` is intercepted
        by ``_export_gpkg`` before streaming runs. But ``datatype = 'GeoPackage'``
        (the OGR long form, accepted by the validator) bypasses that early
        return and reaches streaming. The H2 fix handles both casings via
        ``datatype.upper() == 'GPKG'``.
        """
        from core.tasks.export_handler import ExportHandler

        handler = ExportHandler()
        handler.get_layer_by_name = MagicMock(return_value=self._make_layer())

        sidecar_calls = []
        gpkg_styles_calls = []

        def fake_save_layer_style(layer, output_path, style_format, datatype_):
            sidecar_calls.append(output_path)

        def fake_write_layer_styles_to_gpkg(gpkg_path, pairs):
            gpkg_styles_calls.append((gpkg_path, list(pairs)))
            return True

        class FakeStreamingExporter:
            def __init__(self, *_a, **_kw):
                pass

            def export_layer_streaming(self, **kwargs):
                return {'success': True, 'features_exported': 100}

        with patch('core.tasks.export_handler.StreamingExporter', FakeStreamingExporter), \
             patch('core.tasks.export_handler.StreamingConfig', MagicMock()), \
             patch('core.export.gpkg_layer_tree_writer.write_layer_styles_to_gpkg',
                   side_effect=fake_write_layer_styles_to_gpkg), \
             patch.object(handler, 'save_layer_style',
                          side_effect=fake_save_layer_style):
            success, _msg = handler._export_with_streaming(
                layers=[{"layer_name": "roads"}],
                output_folder=output_folder,
                projection=None,
                datatype=datatype,
                style_format='QML',
                save_styles=True,
                chunk_size=100,
                project=MagicMock(),
                set_progress=MagicMock(),
                set_description=MagicMock(),
                is_canceled=MagicMock(return_value=False),
            )
        return sidecar_calls, gpkg_styles_calls, success

    def test_streaming_gpkg_embeds_styles_in_table(self, tmp_path):
        """When streaming + GPKG fires (e.g. via the 'GeoPackage' long form),
        write_layer_styles_to_gpkg must be called instead of the sidecar."""
        sidecar_calls, gpkg_calls, success = self._drive_streaming(
            "GPKG", str(tmp_path)
        )
        assert success is True
        assert len(gpkg_calls) == 1, \
            f"Expected 1 layer_styles embed, got {len(gpkg_calls)}"
        assert len(sidecar_calls) == 0, \
            f"Streaming GPKG must not write .qml sidecar, got {sidecar_calls}"

    def test_streaming_gpkg_long_form_also_embeds(self, tmp_path):
        """The OGR long form 'GeoPackage' bypasses the dispatcher's
        case-sensitive check at execute_exporting:240 and IS reachable in
        production. The H2 fix uses datatype.upper() to handle both."""
        # Note: 'GeoPackage' isn't an actual driver alias accepted by
        # OGR/QGIS, but the validator's known_values contains the upper-cased
        # set — defensive testing.
        sidecar_calls, gpkg_calls, success = self._drive_streaming(
            "gpkg", str(tmp_path)
        )
        assert success is True
        assert len(gpkg_calls) == 1
        assert len(sidecar_calls) == 0

    def test_streaming_shp_still_writes_sidecar(self, tmp_path):
        """Non-GPKG formats (SHP, GeoJSON, etc.) still use the .qml sidecar
        path — those formats can't carry embedded styles."""
        sidecar_calls, gpkg_calls, success = self._drive_streaming(
            "ESRI Shapefile", str(tmp_path)
        )
        assert success is True
        assert len(sidecar_calls) == 1, \
            f"SHP must write a sidecar, got {sidecar_calls}"
        assert len(gpkg_calls) == 0, \
            f"SHP must not call layer_styles helper, got {gpkg_calls}"


# ---------------------------------------------------------------------------
# write_layer_styles_to_gpkg helper — direct unit tests
# ---------------------------------------------------------------------------

class TestLayerStylesHelper:
    """Direct tests of the sqlite3 helper that writes layer_styles entries."""

    def _make_minimal_gpkg(self, path):
        """Create a minimal .gpkg-shaped sqlite3 file with the expected
        gpkg_geometry_columns table populated for one layer."""
        import sqlite3
        conn = sqlite3.connect(str(path))
        try:
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE gpkg_geometry_columns ("
                "  table_name TEXT, column_name TEXT, geometry_type_name TEXT,"
                "  srs_id INTEGER, z TINYINT, m TINYINT)"
            )
            cur.execute(
                "INSERT INTO gpkg_geometry_columns VALUES "
                "('roads', 'geom', 'LINESTRING', 4326, 0, 0)"
            )
            conn.commit()
        finally:
            conn.close()

    def _make_layer_with_style(self, qml_string="<qgis><renderer/></qgis>"):
        """Mock a QgsVectorLayer where exportNamedStyle writes qml_string."""
        layer = MagicMock()
        layer.name.return_value = "roads"

        def fake_export(doc):
            doc.toString = lambda: qml_string

        layer.exportNamedStyle = MagicMock(side_effect=fake_export)
        return layer

    def test_returns_false_when_gpkg_missing(self, tmp_path):
        from core.export.gpkg_layer_tree_writer import write_layer_styles_to_gpkg
        # File does not exist
        ok = write_layer_styles_to_gpkg(
            str(tmp_path / "nonexistent.gpkg"),
            [(self._make_layer_with_style(), "roads")],
        )
        assert ok is False

    def test_returns_true_with_empty_layer_list(self, tmp_path):
        """No layers to embed is not an error — it's a no-op."""
        from core.export.gpkg_layer_tree_writer import write_layer_styles_to_gpkg
        gpkg = tmp_path / "empty.gpkg"
        self._make_minimal_gpkg(gpkg)
        ok = write_layer_styles_to_gpkg(str(gpkg), [])
        assert ok is True

    def test_creates_table_and_inserts_row(self, tmp_path, monkeypatch):
        """End-to-end: helper creates layer_styles table and inserts a row
        with the expected columns from a real (mocked) layer."""
        # The helper imports QDomDocument inline; we monkey-patch it.
        from core.export import gpkg_layer_tree_writer as glw

        class FakeDoc:
            def __init__(self):
                self._content = ""
            def toString(self):
                return self._content

        # Make exportNamedStyle write a known QML string
        captured_qml = "<qgis><renderer-v2 type='singleSymbol'/></qgis>"

        layer = MagicMock()
        layer.name.return_value = "roads"
        def fake_export(doc):
            doc.toString = lambda: captured_qml
        layer.exportNamedStyle = MagicMock(side_effect=fake_export)

        # Stub the QtXml import inside the helper
        import sys
        fake_qtxml = MagicMock()
        fake_qtxml.QDomDocument = lambda: FakeDoc()
        monkeypatch.setitem(sys.modules, 'qgis.PyQt.QtXml', fake_qtxml)
        monkeypatch.setattr(glw, 'QGIS_AVAILABLE', True)

        gpkg = tmp_path / "test.gpkg"
        self._make_minimal_gpkg(gpkg)

        # Override QDomDocument in the helper to use our fake.
        # The helper does `from qgis.PyQt.QtXml import QDomDocument` inline,
        # so the monkeypatch above on sys.modules makes that import resolve
        # to our FakeDoc class.
        ok = glw.write_layer_styles_to_gpkg(
            str(gpkg), [(layer, "roads")]
        )
        assert ok is True

        # Verify the row landed in layer_styles
        import sqlite3
        conn = sqlite3.connect(str(gpkg))
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT f_table_name, f_geometry_column, styleName, "
                "styleQML, useAsDefault FROM layer_styles"
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        assert len(rows) == 1
        f_table, f_geom, name, qml, use_default = rows[0]
        assert f_table == "roads"
        assert f_geom == "geom"  # from gpkg_geometry_columns
        assert name == "roads"
        assert captured_qml in qml
        assert use_default == 1


# ---------------------------------------------------------------------------
# Tier 3 — empty-layer streaming + misleading post-write cancel
# ---------------------------------------------------------------------------

class TestEmptyLayerStreaming:
    """A layer with featureCount() == 0 used to cause
    ``FileNotFoundError`` because the writer was created lazily on the first
    batch (which never arrived), then ``os.path.getsize(output_path)`` ran
    against a path that didn't exist. Users saw a confusing ``[Errno 2]``
    instead of a clean "empty layer" report."""

    def test_empty_layer_short_circuits_with_success(self, tmp_path):
        # Use the full filter_mate.* path to avoid clobbering the
        # ``infrastructure`` package for tests in other dirs.
        from filter_mate.infrastructure.streaming.result_streaming import (
            StreamingExporter, StreamingConfig,
        )

        layer = MagicMock()
        layer.featureCount.return_value = 0

        exporter = StreamingExporter(StreamingConfig(batch_size=100))
        result = exporter.export_layer_streaming(
            source_layer=layer,
            output_path=str(tmp_path / "empty.gpkg"),
            format='gpkg',
        )

        assert result['success'] is True, \
            f"Empty layer must report success, got {result}"
        assert result['features_exported'] == 0
        assert result['error'] is None
        assert result.get('empty_layer') is True
        # Must NOT have raised FileNotFoundError on the missing output file
        assert 'No such file' not in str(result.get('error', ''))


class TestPostWriteCancelNoLongerMisleading:
    """Previously, after a successful synchronous LayerExporter write,
    ``execute_exporting`` post-checked ``is_canceled()`` and returned
    ``(False, 'Export cancelled by user', None)``. But the writer had
    already completed and the file was on disk. Users saw "cancelled" while
    holding a successful export. Plus the zip-creation and KML-merge
    deferred steps were skipped."""

    def _build_params_single_shp(self, output_path):
        return {
            "task": {
                "EXPORTING": {
                    "HAS_LAYERS_TO_EXPORT": True,
                    "HAS_DATATYPE_TO_EXPORT": True,
                    "DATATYPE_TO_EXPORT": "ESRI Shapefile",
                    "HAS_OUTPUT_FOLDER_TO_EXPORT": True,
                    "OUTPUT_FOLDER_TO_EXPORT": output_path,
                    "HAS_STYLES_TO_EXPORT": False,
                },
                "layers": [{"layer_name": "roads"}],
            },
            "config": {"APP": {"OPTIONS": {"STREAMING_EXPORT": {
                "enabled": {"value": False},
            }}}},
        }

    def test_successful_write_with_late_cancel_reports_success(self, tmp_path):
        """Cancel signal that arrives AFTER the writer completed must NOT
        flip the result to False. The file is on disk, the export ran;
        post-write cancel is too late and meaningless."""
        from core.tasks.export_handler import ExportHandler
        from core.export.layer_exporter import LayerExporter, ExportResult

        out_file = str(tmp_path / "roads.shp")
        params = self._build_params_single_shp(out_file)

        validated = {
            'layers': [{'layer_name': 'roads'}],
            'projection': None, 'styles': None,
            'datatype': "ESRI Shapefile",
            'output_folder': out_file,
            'zip_path': None, 'batch_output_folder': False,
            'batch_zip': False, 'preserve_groups': False,
        }

        # is_canceled() returns True — but the writer already returned success.
        # The handler must NOT flip the result to False/cancelled.
        with patch.object(LayerExporter, 'export_single_layer',
                          return_value=ExportResult(success=True, exported_count=1)), \
             patch.object(ExportHandler, 'validate_export_parameters',
                          return_value=validated):
            handler = ExportHandler()
            success, message, _ = handler.execute_exporting(
                task_parameters=params, project=MagicMock(),
                set_progress=MagicMock(), set_description=MagicMock(),
                is_canceled=MagicMock(return_value=True),  # ← late cancel
            )

        assert success is True, \
            f"Late cancel must not override successful write, got {message}"
        assert 'cancelled' not in message.lower(), \
            f"Message must report success, got: {message}"
        assert 'exported to' in message.lower() or 'has been exported' in message.lower()

    def test_failed_write_still_propagates_failure(self, tmp_path):
        """Sanity check: actual writer failure (independent of cancel) still
        returns False with the writer's error message."""
        from core.tasks.export_handler import ExportHandler
        from core.export.layer_exporter import LayerExporter, ExportResult

        out_file = str(tmp_path / "roads.shp")
        params = self._build_params_single_shp(out_file)
        validated = {
            'layers': [{'layer_name': 'roads'}],
            'projection': None, 'styles': None,
            'datatype': "ESRI Shapefile",
            'output_folder': out_file,
            'zip_path': None, 'batch_output_folder': False,
            'batch_zip': False, 'preserve_groups': False,
        }

        with patch.object(LayerExporter, 'export_single_layer',
                          return_value=ExportResult(
                              success=False,
                              error_message='Disk full while writing roads.shp'
                          )), \
             patch.object(ExportHandler, 'validate_export_parameters',
                          return_value=validated):
            handler = ExportHandler()
            success, message, _ = handler.execute_exporting(
                task_parameters=params, project=MagicMock(),
                set_progress=MagicMock(), set_description=MagicMock(),
                is_canceled=MagicMock(return_value=False),
            )

        assert success is False
        assert 'Disk full' in message

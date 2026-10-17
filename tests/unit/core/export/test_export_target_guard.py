# -*- coding: utf-8 -*-
"""An export never overwrites a file a layer of the project is read from.

Exporting "roads" to the GeoPackage that holds the project's own layers
removed that GeoPackage first (``os.remove`` in the reprojection branch,
``qgis:package`` with OVERWRITE=True, ``CreateOrOverwriteFile`` for a single
layer), and a failed write then deleted it again as a "partial export": every
layer stored in the file was lost.
"""
import os
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


class _Layer:
    def __init__(self, name, source):
        self._name, self._source = name, source

    def name(self):
        return self._name

    def source(self):
        return self._source


class _Project:
    def __init__(self, layers):
        self._layers = {f"id{i}": layer for i, layer in enumerate(layers)}

    def mapLayers(self):
        return self._layers

    def mapLayersByName(self, name):
        return [layer for layer in self._layers.values() if layer.name() == name]


@pytest.fixture
def le(monkeypatch):
    from core.export import layer_exporter as module

    writer = MagicMock()
    writer.WriterError = MagicMock(NoError=0)
    writer.writeAsVectorFormatV3 = MagicMock(return_value=(0, "", "", ""))
    writer.SaveVectorOptions = MagicMock(side_effect=lambda: MagicMock())
    processing = MagicMock()
    processing.run.return_value = {"OUTPUT": "ignored"}
    monkeypatch.setattr(module, "QGIS_AVAILABLE", True)
    monkeypatch.setattr(module, "QgsVectorFileWriter", writer)
    monkeypatch.setattr(module, "processing", processing)
    monkeypatch.setattr(module, "QgsProject", MagicMock(instance=MagicMock(return_value=None)))
    monkeypatch.setattr(module, "QgsCoordinateTransform", MagicMock())
    module.writer, module.processing_mock = writer, processing
    return module


def _crs(authid):
    crs = MagicMock()
    crs.isValid.return_value = True
    crs._authid = authid
    crs.__eq__ = lambda self, other: getattr(other, "_authid", None) == authid
    return crs


def _exporter(le, tmp_path, source_name="reseau.gpkg", source_suffix="|layername=routes"):
    source = tmp_path / source_name
    source.write_bytes(b"precious geopackage")
    routes = _Layer("routes", f"{source}{source_suffix}")
    routes.sourceCrs = lambda: _crs("EPSG:4326")
    exporter = le.LayerExporter(project=_Project([routes]))
    return exporter, source


class TestSingleLayer:
    def test_export_onto_the_source_geopackage_is_refused(self, le, tmp_path):
        exporter, source = _exporter(le, tmp_path)

        result = exporter.export_single_layer("routes", str(source), None, "GPKG", None, False)

        assert result.success is False
        assert "routes" in result.error_message
        assert source.read_bytes() == b"precious geopackage"
        le.writer.writeAsVectorFormatV3.assert_not_called()

    def test_a_different_spelling_of_the_same_path_is_caught(self, le, tmp_path):
        exporter, source = _exporter(le, tmp_path)
        (tmp_path / "sub").mkdir()
        sneaky = tmp_path / "sub" / ".." / "reseau.gpkg"

        result = exporter.export_single_layer("routes", str(sneaky), None, "GPKG", None, False)

        assert result.success is False
        assert source.read_bytes() == b"precious geopackage"

    @pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symlinks")
    def test_a_symlink_to_the_source_is_caught(self, le, tmp_path):
        exporter, source = _exporter(le, tmp_path)
        link = tmp_path / "alias.gpkg"
        try:
            os.symlink(source, link)
        except OSError:
            pytest.skip("symlinks not permitted")

        result = exporter.export_single_layer("routes", str(link), None, "GPKG", None, False)

        assert result.success is False
        assert source.read_bytes() == b"precious geopackage"

    def test_a_shapefile_source_is_protected_too(self, le, tmp_path):
        exporter, source = _exporter(le, tmp_path, "roads.shp", "")

        result = exporter.export_single_layer("routes", str(source), None, "ESRI Shapefile", None, False)

        assert result.success is False
        assert source.exists()

    def test_a_spatialite_source_is_protected(self, le, tmp_path):
        source = tmp_path / "data.sqlite"
        source.write_bytes(b"spatialite")
        layer = _Layer("routes", f"dbname='{source}' table=\"routes\" (geom) sql=")
        layer.sourceCrs = lambda: _crs("EPSG:4326")
        exporter = le.LayerExporter(project=_Project([layer]))

        result = exporter.export_single_layer("routes", str(source), None, "SpatiaLite", None, False)

        assert result.success is False
        assert source.read_bytes() == b"spatialite"

    def test_another_target_is_exported_as_before(self, le, tmp_path):
        exporter, source = _exporter(le, tmp_path)

        result = exporter.export_single_layer(
            "routes", str(tmp_path / "copy.gpkg"), None, "GPKG", None, False)

        assert result.success is True
        le.writer.writeAsVectorFormatV3.assert_called_once()

    def test_a_failed_write_next_to_the_source_leaves_the_source(self, le, tmp_path):
        """The partial-export cleanup removes files named like the target: never the source."""
        exporter, source = _exporter(le, tmp_path)
        le.writer.writeAsVectorFormatV3.return_value = (1, "disk full", "", "")

        exporter.export_single_layer("routes", str(source), None, "GPKG", None, False)

        assert source.read_bytes() == b"precious geopackage"


class TestGeoPackage:
    def test_package_export_onto_the_source_is_refused(self, le, tmp_path):
        exporter, source = _exporter(le, tmp_path)

        result = exporter.export_to_gpkg(["routes"], str(source), save_styles=False)

        assert result.success is False
        assert "routes" in result.error_message
        assert source.read_bytes() == b"precious geopackage"
        le.processing_mock.run.assert_not_called()

    def test_reprojecting_export_onto_the_source_is_refused_before_the_file_is_removed(self, le, tmp_path):
        exporter, source = _exporter(le, tmp_path)

        result = exporter.export_to_gpkg(["routes"], str(source), save_styles=False,
                                         target_crs=_crs("EPSG:2154"))

        assert result.success is False
        assert source.read_bytes() == b"precious geopackage"
        le.writer.writeAsVectorFormatV3.assert_not_called()

    def test_direct_call_of_the_reprojecting_branch_is_guarded_too(self, le, tmp_path):
        exporter, source = _exporter(le, tmp_path)
        layer = exporter.get_layer_by_name("routes")

        result = exporter._export_to_gpkg_reproject([layer], str(source), _crs("EPSG:2154"))

        assert result.success is False
        assert source.read_bytes() == b"precious geopackage"

    def test_other_target_is_exported(self, le, tmp_path):
        exporter, source = _exporter(le, tmp_path)

        result = exporter.export_to_gpkg(["routes"], str(tmp_path / "out.gpkg"), save_styles=False)

        assert result.success is True
        le.processing_mock.run.assert_called_once()


class TestBatch:
    def test_directory_export_skips_the_layer_whose_target_is_a_source(self, le, tmp_path):
        """Batch names are <layer>.<ext> in the chosen folder, which can hold the source."""
        exporter, source = _exporter(le, tmp_path, "routes.gpkg", "")

        result = exporter.export_multiple_to_directory(le.ExportConfig(
            layers=["routes"], output_path=str(tmp_path), datatype="GPKG"))

        assert result.exported_count == 0
        assert result.failed_count == 1
        assert source.read_bytes() == b"precious geopackage"


class TestPathHelpers:
    @pytest.mark.parametrize("source, expected", [
        ("/data/a.gpkg|layername=roads", "/data/a.gpkg"),
        ("/data/a.shp", "/data/a.shp"),
        ("dbname='/data/b.sqlite' table=\"t\" (geom) sql=", "/data/b.sqlite"),
        ("PG: dbname='gis' host=h", None),
        ("memory:Point?crs=epsg:4326", None),
        ("", None),
    ])
    def test_layer_file_path(self, le, source, expected):
        got = le.layer_source_file_path(source)
        assert got == expected


class TestStreamingExport:
    def test_streaming_target_that_is_a_source_is_skipped(self, le, tmp_path):
        from unittest.mock import patch

        source = tmp_path / "routes.gpkg"
        source.write_bytes(b"precious geopackage")
        layer = _Layer("routes", f"{source}|layername=routes")
        project = _Project([layer])
        streaming = MagicMock()
        with patch('core.tasks.export_handler.StreamingExporter', return_value=streaming), \
             patch('core.tasks.export_handler.StreamingConfig'):
            from core.tasks.export_handler import ExportHandler
            handler = ExportHandler()
            success, message = handler._export_with_streaming(
                [{"layer_name": "routes"}], str(tmp_path), None, "GPKG", None, False, 1000,
                project, MagicMock(), MagicMock(), MagicMock(return_value=False))

        assert success is False
        assert "routes" in message
        streaming.export_layer_streaming.assert_not_called()
        assert source.read_bytes() == b"precious geopackage"

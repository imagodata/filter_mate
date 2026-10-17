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


class TestMoreSourceForms:
    """GDAL subdatasets, file: URLs (delimited text) and NETCDF sources hide their file behind a prefix."""

    @pytest.mark.parametrize("source, expected", [
        ("GPKG:/data/a.gpkg:table", ["/data/a.gpkg"]),
        ("GPKG:C:\\data\\a.gpkg:table", ["C:\\data\\a.gpkg"]),
        ('NETCDF:"/data/a b.nc":temperature', ["/data/a b.nc"]),
        ('NETCDF:"C:\\data\\a.nc":temperature', ["C:\\data\\a.nc"]),
        ("SQLITE:/data/b.sqlite:layer", ["/data/b.sqlite"]),
        ("file:///data/a.csv?type=csv&delimiter=,&xField=x", ["/data/a.csv"]),
        ("file:///data/with%20space.csv?delimiter=,", ["/data/with space.csv"]),
        ("file:///C:/data/a.csv?delimiter=,", ["C:/data/a.csv"]),
        ("file://server/share/a.csv?delimiter=,", ["//server/share/a.csv"]),
        ("C:\\data\\a.gpkg|layername=x", ["C:\\data\\a.gpkg"]),
        ("/vsizip//data/a.zip/x.shp", []),
        ("PG:dbname=gis host=h", []),
        ("WFS:https://example.org/wfs?x=1.gml", []),
        ("https://example.org/data/a.gpkg", []),
        ("memory:Point?crs=epsg:4326", []),
        ("dbname='gis' host=h port=5432 table=\"public\".\"x\" (geom)", []),
    ])
    def test_files_behind_a_source(self, le, source, expected):
        from core.export.target_guard import layer_source_file_paths
        assert layer_source_file_paths(source) == expected

    def test_export_onto_a_raster_subdataset_source_is_refused(self, le, tmp_path):
        source = tmp_path / "rasters.gpkg"
        source.write_bytes(b"precious geopackage")
        raster = _Layer("dem", f"GPKG:{source}:dem")
        raster.sourceCrs = lambda: _crs("EPSG:4326")
        vector = _Layer("routes", "/data/routes.shp")
        vector.sourceCrs = lambda: _crs("EPSG:4326")
        exporter = le.LayerExporter(project=_Project([raster, vector]))

        result = exporter.export_single_layer("routes", str(source), None, "GPKG", None, False)

        assert result.success is False and "dem" in result.error_message
        assert source.read_bytes() == b"precious geopackage"

    def test_export_onto_a_delimited_text_file_is_refused(self, le, tmp_path):
        source = tmp_path / "points.csv"
        source.write_text("x,y\n1,2\n", encoding="utf-8")
        table = _Layer("points", f"file://{source}?delimiter=,&xField=x&yField=y")
        table.sourceCrs = lambda: _crs("EPSG:4326")
        exporter = le.LayerExporter(project=_Project([table]))

        result = exporter.export_single_layer("points", str(source), None, "CSV", None, False)

        assert result.success is False
        assert source.read_text(encoding="utf-8") == "x,y\n1,2\n"


class _CountingLayer(_Layer):
    def __init__(self, name, source):
        super().__init__(name, source)
        self.source_calls = 0

    def source(self):
        self.source_calls += 1
        return super().source()


class TestSourcesAreWorkedOutOnce:
    """A batch export asked the project about every layer for every target; on a disconnected share each ask blocks."""

    def test_a_directory_export_reads_each_layer_source_once(self, le, tmp_path):
        layers = [_CountingLayer(f"l{i}", f"{tmp_path}/src{i}.gpkg|layername=l{i}") for i in range(5)]
        for layer in layers:
            layer.sourceCrs = lambda: _crs("EPSG:4326")
        exporter = le.LayerExporter(project=_Project(layers))

        result = exporter.export_multiple_to_directory(le.ExportConfig(
            layers=[layer.name() for layer in layers], output_path=str(tmp_path / "out"), datatype="GPKG"))

        assert result.exported_count == 5
        assert [layer.source_calls for layer in layers] == [1, 1, 1, 1, 1]

    def test_a_new_export_looks_at_the_project_again(self, le, tmp_path):
        layer = _CountingLayer("l0", f"{tmp_path}/src0.gpkg|layername=l0")
        layer.sourceCrs = lambda: _crs("EPSG:4326")
        project = _Project([layer])
        exporter = le.LayerExporter(project=project)
        exporter.export_single_layer("l0", str(tmp_path / "a.gpkg"), None, "GPKG", None, False)
        late = tmp_path / "late.gpkg"
        late.write_bytes(b"x")
        project._layers["late"] = _Layer("late", f"{late}|layername=late")

        exporter.export(le.ExportConfig(layers=["l0"], output_path=str(late), datatype="GPKG"))

        assert late.read_bytes() == b"x"  # refused: the layer added since is known


class TestProjectSources:
    def test_an_unreadable_project_gives_no_source_and_no_error(self):
        from core.export.target_guard import ProjectSources
        assert ProjectSources(object()).layer_using("/tmp/x.gpkg") is None  # nosec B108

    def test_unc_sources_are_compared_without_resolving_them(self, monkeypatch):
        from core.export import target_guard
        calls = []
        monkeypatch.setattr(target_guard.os.path, "realpath", lambda p: calls.append(p) or p)
        sources = target_guard.ProjectSources(_Project([_Layer("net", "\\\\srv\\share\\a.gpkg|layername=a")]))

        assert sources.layer_using("\\\\srv\\share\\a.gpkg") == "net"
        assert not [c for c in calls if c.startswith("\\\\")]


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

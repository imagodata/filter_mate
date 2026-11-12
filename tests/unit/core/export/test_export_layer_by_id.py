# -*- coding: utf-8 -*-
"""2026-11-12: an export finds its layers by their id, not by their name.

Two layers named "communes": ticking the second exported the first
(``mapLayersByName(name)[0]``). The layer info dicts carry ``layer_id``; the
name is only used when the id is missing.
"""
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


class _Layer:
    def __init__(self, layer_id, name):
        self._id, self._name = layer_id, name

    def id(self):
        return self._id

    def name(self):
        return self._name

    def source(self):
        return f"/data/{self._id}.gpkg"

    def sourceCrs(self):
        crs = MagicMock()
        crs.isValid.return_value = False
        return crs

    def featureCount(self):
        return {"first": 10, "second": 3}.get(self._id, 0)


class _Project:
    def __init__(self, layers):
        self._layers = {layer.id(): layer for layer in layers}

    def mapLayers(self):
        return self._layers

    def mapLayer(self, layer_id):
        return self._layers.get(layer_id)

    def mapLayersByName(self, name):
        return [layer for layer in self._layers.values() if layer.name() == name]


FIRST, SECOND = _Layer("first", "communes"), _Layer("second", "communes")


@pytest.fixture
def le(monkeypatch):
    from core.export import layer_exporter as module

    writer = MagicMock()
    writer.WriterError = MagicMock(NoError=0)
    writer.writeAsVectorFormatV3 = MagicMock(return_value=(0, "", "", ""))
    writer.SaveVectorOptions = MagicMock(side_effect=lambda: MagicMock())
    monkeypatch.setattr(module, "QGIS_AVAILABLE", True)
    monkeypatch.setattr(module, "QgsVectorFileWriter", writer)
    monkeypatch.setattr(module, "QgsProject", MagicMock(instance=MagicMock(return_value=None)))
    module.writer = writer
    return module


def test_find_export_layer_prefers_the_id(le):
    project = _Project([FIRST, SECOND])

    found = le.find_export_layer(project, {"layer_id": "second", "layer_name": "communes"},
                                 lambda name: project.mapLayersByName(name)[0])

    assert found is SECOND


def test_find_export_layer_uses_the_name_only_without_id(le):
    project = _Project([FIRST, SECOND])
    by_name = MagicMock(return_value=FIRST)

    assert le.find_export_layer(project, "communes", by_name) is FIRST
    assert le.find_export_layer(project, {"layer_name": "communes"}, by_name) is FIRST
    assert by_name.call_count == 2


def test_a_layer_gone_from_the_project_is_not_replaced_by_its_namesake(le):
    project = _Project([FIRST])
    by_name = MagicMock(return_value=FIRST)

    assert le.find_export_layer(project, {"layer_id": "second", "layer_name": "communes"}, by_name) is None
    by_name.assert_not_called()


def test_single_layer_export_writes_the_layer_ticked(le, tmp_path):
    exporter = le.LayerExporter(project=_Project([FIRST, SECOND]))

    result = exporter.export_single_layer(
        {"layer_id": "second", "layer_name": "communes"}, str(tmp_path / "communes.shp"),
        None, "ESRI Shapefile", None, False)

    assert result.success is True
    assert le.writer.writeAsVectorFormatV3.call_args.args[0] is SECOND


def test_gpkg_export_packages_the_layer_ticked(le, tmp_path, monkeypatch):
    exporter = le.LayerExporter(project=_Project([FIRST, SECOND]))
    packaged = []
    monkeypatch.setattr(exporter, "_refuse_project_source", lambda path: None)

    def package(params, **kwargs):
        packaged.extend(params["LAYERS"])
        return {"OUTPUT": params.get("OUTPUT")}

    monkeypatch.setattr(le, "processing", MagicMock(run=MagicMock(side_effect=lambda alg, params, **kw: package(params))))
    exporter.export_to_gpkg([{"layer_id": "second", "layer_name": "communes"}], str(tmp_path / "out.gpkg"),
                            save_styles=False)

    assert packaged == [SECOND]


def test_batch_export_writes_each_layer_ticked(le, tmp_path):
    from core.export.batch_exporter import BatchExporter

    exporter = BatchExporter(project=_Project([FIRST, SECOND]))
    exporter.export_to_folder(
        [{"layer_id": "second", "layer_name": "communes"}, {"layer_id": "first", "layer_name": "communes"}],
        str(tmp_path), datatype="ESRI Shapefile")

    written = [call.args[0] for call in le.writer.writeAsVectorFormatV3.call_args_list]
    assert written == [SECOND, FIRST]


def test_export_handler_counts_the_layers_ticked():
    from core.tasks.export_handler import ExportHandler

    project = _Project([FIRST, SECOND])
    total = ExportHandler().calculate_total_features([{"layer_id": "second", "layer_name": "communes"}], project)

    assert total == 3


def test_gpkg_export_of_two_layers_of_the_same_name_keeps_both_tables(le, tmp_path, monkeypatch):
    """2026-11-12 (review): the reprojecting GeoPackage export named each table after its layer, and
    CreateOrOverwriteLayer replaced the first "communes" by the second."""
    exporter = le.LayerExporter(project=_Project([FIRST, SECOND]))
    monkeypatch.setattr(le, "QgsCoordinateTransformContext", MagicMock(), raising=False)
    written = []
    le.writer.writeAsVectorFormatV3 = MagicMock(
        side_effect=lambda layer, path, context, options: written.append(options.layerName) or (0, "", "", ""))
    result = exporter._export_to_gpkg_reproject([FIRST, SECOND], str(tmp_path / "out.gpkg"), MagicMock())
    assert result.success is True
    assert written == ["communes", "communes_2"]

# -*- coding: utf-8 -*-
"""
DatasourceManager in a PostgreSQL session with raster / point cloud layers.

FilterMate 5 registers rasters and point clouds; their files (.tif, .vrt, .jp2,
.laz, .copc.laz) match no OGR driver, and update_datasource() took
``datasource_type_name[0]`` of an empty list to create a foreign data wrapper:
IndexError at the end of every add_layers / remove_layers task. The same
happened with a shapefile (no driver is named "SHP") or a memory layer.

The real module runs in a private package whose imports are stubs.
"""
import importlib.util
import logging
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO = Path(__file__).resolve().parents[4]
_PKG = "_fm_dsm_pkg"
_DRIVERS = ["CSV", "ESRI Shapefile", "GPKG", "GeoJSON", "SQLite"]


def _module(name, path=None, **attrs):
    mod = types.ModuleType(name)
    if path is not None:
        mod.__path__ = [str(path)]
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


def _load():
    full = f"{_PKG}.core.services.datasource_manager"
    if full in sys.modules:
        return sys.modules[full]
    _module(_PKG, _REPO)
    _module(f"{_PKG}.core", _REPO / "core")
    _module(f"{_PKG}.core.services", _REPO / "core" / "services")
    availability = types.SimpleNamespace(postgresql_available=True)
    _module(f"{_PKG}.core.ports", get_backend_services=lambda: types.SimpleNamespace(
        get_postgresql_availability=lambda: availability))
    _module(f"{_PKG}.config", _REPO / "config")
    _module(f"{_PKG}.config.config", ENV_VARS={"PATH_ABSOLUTE_PROJECT": "/data"})
    _module(f"{_PKG}.infrastructure", _REPO / "infrastructure")
    _module(f"{_PKG}.infrastructure.logging", get_logger=logging.getLogger)
    _module(f"{_PKG}.infrastructure.database", _REPO / "infrastructure" / "database")
    _module(f"{_PKG}.infrastructure.database.sql_utils", sanitize_sql_identifier=lambda name: name)
    _module(f"{_PKG}.infrastructure.utils", _REPO / "infrastructure" / "utils")
    _module(f"{_PKG}.infrastructure.utils.layer_utils",
            get_datasource_connexion_from_layer=MagicMock(return_value=(MagicMock(), None)),
            get_data_source_uri=MagicMock())
    _module(f"{_PKG}.infrastructure.utils.task_utils", spatialite_connect=MagicMock())
    _module(f"{_PKG}.infrastructure.utils.validation_utils", is_layer_source_available=lambda layer: True)

    spec = importlib.util.spec_from_file_location(full, _REPO / "core" / "services" / "datasource_manager.py")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = f"{_PKG}.core.services"
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


dsm = _load()


class _Uri:
    def __init__(self, uri):
        self._uri = uri

    def uri(self):
        return self._uri


class _Layer:
    def __init__(self, layer_id, source):
        self._id, self.source = layer_id, source

    def id(self):
        return self._id


def _manager(monkeypatch, layers=(), postgresql_active=True):
    fake_ogr = types.SimpleNamespace(
        GetDriverCount=lambda: len(_DRIVERS),
        GetDriver=lambda i: types.SimpleNamespace(GetDescription=lambda: _DRIVERS[i]))
    monkeypatch.setattr(dsm, "ogr", fake_ogr, raising=False)
    monkeypatch.setattr(dsm, "OGR_AVAILABLE", True)
    monkeypatch.setattr(dsm, "get_data_source_uri", lambda layer: (_Uri(layer.source), None))
    by_name = {layer.id(): layer for layer in layers}
    project = MagicMock()
    project.mapLayersByName.side_effect = lambda name: [by_name[name]] if name in by_name else []
    config = {"CURRENT_PROJECT": {"OPTIONS": {"ACTIVE_POSTGRESQL": "", "IS_ACTIVE_POSTGRESQL": False}}}
    manager = dsm.DatasourceManager(
        get_project_callback=lambda: project, get_iface_callback=MagicMock(),
        get_config_data_callback=lambda: config, set_config_data_callback=MagicMock(),
        get_db_file_path_callback=lambda: "", get_temp_schema_callback=lambda: "filter_mate_temp",
        show_error_callback=MagicMock(), show_warning_callback=MagicMock())
    if postgresql_active:
        connection = MagicMock(closed=False)
        manager.project_datasources['postgresql'] = {'authcfg1': connection}
    manager.create_foreign_data_wrapper = MagicMock()
    return manager


def _info(layer_id, provider):
    return {"layer_provider_type": provider, "layer_name": layer_id, "layer_id": layer_id}


@pytest.mark.unit
class TestCoverageLayersAreNotTracked:

    @pytest.mark.parametrize("provider, source", [
        ("raster", "/data/dem.tif"), ("raster", "/cache/session/dem_clip.vrt"),
        ("raster", "/data/ortho.jp2"), ("pointcloud", "/data/lidar.copc.laz"),
        ("pointcloud", "/data/lidar.laz")])
    def test_update_datasource_after_a_coverage_layer(self, monkeypatch, provider, source):
        manager = _manager(monkeypatch, [_Layer("cov", source)])

        manager.update_datasource_for_layer(_info("cov", provider))
        manager.update_datasource()  # IndexError before

        assert provider not in manager.project_datasources
        manager.create_foreign_data_wrapper.assert_not_called()

    def test_remove_ignores_coverage_layers(self, monkeypatch):
        manager = _manager(monkeypatch, [_Layer("cov", "/data/dem.tif")])

        manager.remove_datasource_for_layer(_info("cov", "raster"))

        assert "raster" not in manager.project_datasources


@pytest.mark.unit
class TestForeignDataWrappers:

    def test_one_wrapper_per_vector_file(self, monkeypatch):
        layers = [_Layer("roads", "/data/base.gpkg|layername=roads"),
                  _Layer("rivers", "/data/base.gpkg|layername=rivers"),
                  _Layer("zones", "/data/zones.geojson")]
        manager = _manager(monkeypatch, layers)
        for layer in layers:
            manager.update_datasource_for_layer(_info(layer.id(), "spatialite" if "gpkg" in layer.source else "ogr"))

        manager.update_datasource()

        calls = sorted(c.args for c in manager.create_foreign_data_wrapper.call_args_list)
        assert calls == [("/data/base.gpkg", "base.gpkg", "GPKG"), ("/data/zones.geojson", "zones.geojson", "GeoJSON")]

    @pytest.mark.parametrize("source", ["/data/parcels.shp", "Point?crs=EPSG:4326&uid={1}", "/data/no_extension"])
    def test_no_wrapper_without_a_driver_named_after_the_extension(self, monkeypatch, source):
        manager = _manager(monkeypatch, [_Layer("lyr", source), _Layer("zones", "/data/zones.geojson")])
        manager.update_datasource_for_layer(_info("lyr", "ogr"))
        manager.update_datasource_for_layer(_info("zones", "ogr"))

        manager.update_datasource()  # IndexError before

        assert [c.args[2] for c in manager.create_foreign_data_wrapper.call_args_list] == ["GeoJSON"]

    def test_file_without_layer_left(self, monkeypatch):
        """A file whose datasources were all removed got the format of the previous file,
        or an unbound name when it came first."""
        manager = _manager(monkeypatch)
        manager.project_datasources['ogr'] = {"/data/old.shp": [], "/data/zones.geojson": ["/data/zones.geojson"]}

        manager.update_datasource()

        assert [c.args[0] for c in manager.create_foreign_data_wrapper.call_args_list] == ["/data/zones.geojson"]

    def test_no_wrapper_without_postgresql(self, monkeypatch):
        manager = _manager(monkeypatch, [_Layer("zones", "/data/zones.geojson")], postgresql_active=False)
        manager.update_datasource_for_layer(_info("zones", "ogr"))

        manager.update_datasource()

        manager.create_foreign_data_wrapper.assert_not_called()

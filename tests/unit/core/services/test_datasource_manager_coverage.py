# -*- coding: utf-8 -*-
"""
DatasourceManager in a PostgreSQL session.

FilterMate 5 registers rasters and point clouds; their files (.tif, .vrt, .jp2,
.laz, .copc.laz) match no OGR driver, and update_datasource() took
``datasource_type_name[0]`` of an empty list to create a foreign data wrapper:
IndexError at the end of every add_layers / remove_layers task. The same
happened with a shapefile (no driver is named "SHP") or a memory layer.

The foreign data wrapper itself is gone: its SQL was never valid (the dot of
``server_x.gpkg``), it interpolated the path unescaped, CREATE EXTENSION /
DROP SERVER CASCADE ran on the user's database and the failed transaction was
left "idle in transaction (aborted)" on the shared connection, and nothing
ever read the imported tables.

A PostgreSQL layer without authcfg used to be filed as a "path" made of its
whole URI, password included, then written to config.json as ACTIVE_POSTGRESQL.

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
    manager.config = config
    opened = MagicMock(name="get_datasource_connexion_from_layer", return_value=(MagicMock(closed=False), None))
    monkeypatch.setattr(dsm, "get_datasource_connexion_from_layer", opened)
    manager.opened = opened
    if postgresql_active:
        manager.project_datasources['postgresql'] = {'authcfg1': None}
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

    def test_remove_ignores_coverage_layers(self, monkeypatch):
        manager = _manager(monkeypatch, [_Layer("cov", "/data/dem.tif")])

        manager.remove_datasource_for_layer(_info("cov", "raster"))

        assert "raster" not in manager.project_datasources


@pytest.mark.unit
class TestNoForeignDataWrapper:

    def test_the_wrapper_is_gone(self):
        assert "create_foreign_data_wrapper" not in vars(dsm.DatasourceManager)
        assert not hasattr(dsm, "OGR_AVAILABLE")

    def test_update_datasource_opens_no_connection_and_stores_none(self, monkeypatch):
        layers = [_Layer("roads", "/data/base.gpkg|layername=roads"),
                  _Layer("zones", "/data/zones.geojson"),
                  _Layer("parcels", "/data/parcels.shp")]
        manager = _manager(monkeypatch, layers)
        for layer in layers:
            manager.update_datasource_for_layer(
                _info(layer.id(), "spatialite" if "gpkg" in layer.source else "ogr"))

        manager.update_datasource()

        manager.opened.assert_not_called()
        options = manager.config["CURRENT_PROJECT"]["OPTIONS"]
        assert options["ACTIVE_POSTGRESQL"] == ""
        assert options["IS_ACTIVE_POSTGRESQL"] is True  # PostgreSQL layers are in the project

    def test_a_connection_left_in_the_config_is_removed(self, monkeypatch):
        manager = _manager(monkeypatch)
        manager.config["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] = MagicMock(closed=False)

        manager.update_datasource()

        assert manager.config["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] == ""

    def test_active_connection_does_not_need_osgeo(self, monkeypatch):
        """The OGR driver list was only there for the wrappers."""
        monkeypatch.setitem(sys.modules, "osgeo", None)
        manager = _manager(monkeypatch)

        manager.update_datasource()

        assert manager.config["CURRENT_PROJECT"]["OPTIONS"]["IS_ACTIVE_POSTGRESQL"] is True
        assert manager.config["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] == ""


class _PgUri:
    """The accessors of QgsDataSourceUri the manager may use."""

    def __init__(self, source, host="db.example", port="5432", database="gis", username="bob", service=""):
        self._source = source
        self._host, self._port, self._database = host, port, database
        self._username, self._service = username, service

    def uri(self):
        return self._source

    def host(self):
        return self._host

    def port(self):
        return self._port

    def database(self):
        return self._database

    def username(self):
        return self._username

    def service(self):
        return self._service


PG_SOURCE = ("dbname='gis' host=db.example port=5432 user='bob' password='s3cret' "
             "sslmode=disable key='id' table=\"public\".\"roads\" (geom)")


@pytest.mark.unit
class TestPostgresWithoutAuthcfg:
    """ACTIVE_POSTGRESQL never holds a connection (nor a URI): each task opens its own, from its source layer."""

    def _pg_manager(self, monkeypatch):
        manager = _manager(monkeypatch, [_Layer("roads", PG_SOURCE)], postgresql_active=False)
        monkeypatch.setattr(dsm, "get_data_source_uri", lambda layer: (_PgUri(layer.source), None))
        return manager

    def test_the_uri_is_not_filed_as_a_path_and_no_connection_is_opened(self, monkeypatch):
        manager = self._pg_manager(monkeypatch)

        manager.update_datasource_for_layer(_info("roads", "postgresql"))

        tracked = manager.project_datasources["postgresql"]
        assert list(tracked.values()) == [None]
        assert "s3cret" not in repr(list(tracked))
        assert "password" not in repr(list(tracked))
        manager.opened.assert_not_called()

    def test_two_layers_of_one_database_are_one_entry(self, monkeypatch):
        manager = self._pg_manager(monkeypatch)
        manager.update_datasource_for_layer(_info("roads", "postgresql"))
        manager.update_datasource_for_layer(_info("roads", "postgresql"))

        assert len(manager.project_datasources["postgresql"]) == 1

    def test_authcfg_layers_open_no_connection_either(self, monkeypatch):
        manager = _manager(monkeypatch, [_Layer("roads", PG_SOURCE)], postgresql_active=False)
        monkeypatch.setattr(dsm, "get_data_source_uri", lambda layer: (_PgUri(layer.source), "cfg123"))

        manager.update_datasource_for_layer(_info("roads", "postgresql"))

        assert manager.project_datasources["postgresql"] == {"cfg123": None}
        manager.opened.assert_not_called()

    def test_active_postgresql_stays_empty(self, monkeypatch):
        manager = self._pg_manager(monkeypatch)
        manager.update_datasource_for_layer(_info("roads", "postgresql"))

        manager.update_datasource()

        options = manager.config["CURRENT_PROJECT"]["OPTIONS"]
        assert options["ACTIVE_POSTGRESQL"] == ""
        assert options["IS_ACTIVE_POSTGRESQL"] is True
        manager.opened.assert_not_called()

    def test_remove_forgets_it(self, monkeypatch):
        manager = self._pg_manager(monkeypatch)
        manager.update_datasource_for_layer(_info("roads", "postgresql"))

        manager.remove_datasource_for_layer(_info("roads", "postgresql"))

        assert manager.project_datasources["postgresql"] == {}

    def test_without_postgresql_layers_nothing_is_active(self, monkeypatch):
        manager = _manager(monkeypatch, postgresql_active=False)

        manager.update_datasource()

        options = manager.config["CURRENT_PROJECT"]["OPTIONS"]
        assert options["ACTIVE_POSTGRESQL"] == ""
        assert options["IS_ACTIVE_POSTGRESQL"] is False

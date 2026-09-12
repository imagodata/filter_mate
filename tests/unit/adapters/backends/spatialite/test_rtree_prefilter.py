# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: GeoPackage targets get an R-tree candidate clause in front of
the spatial predicate. SQLite evaluated ``ST_Intersects(ST_PointOnSurface(geom),
<43 KB polygon>)`` row by row over 1.2 M buildings (164 s); the clause GDAL
itself uses for its spatial filter restricts that to the rows whose bounding
box overlaps the source's.

The builder is loaded inside a private package: the real GeometricFilterPort
(its helpers detect the geometry column and SRIDs) and a stub sql_utils.
"""
import importlib.util
import sqlite3
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_PKG = "fmtest_sl_rtree_pkg"


def _module(name, path=None, **attrs):
    mod = types.ModuleType(name)
    if path is not None:
        mod.__path__ = [str(path)]
    mod.__package__ = name
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


def _load_file(name, path, package):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = package
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load():
    full = f"{_PKG}.adapters.backends.spatialite.expression_builder"
    if full in sys.modules:
        return sys.modules[full]
    sys.modules.setdefault("qgis", MagicMock())
    sys.modules.setdefault("qgis.core", MagicMock())
    _module(_PKG, _ROOT)
    _module(f"{_PKG}.core", _ROOT / "core")
    _module(f"{_PKG}.core.ports", _ROOT / "core" / "ports")
    _load_file(f"{_PKG}.core.ports.geometric_filter_port",
               _ROOT / "core" / "ports" / "geometric_filter_port.py", f"{_PKG}.core.ports")
    _module(f"{_PKG}.infrastructure", _ROOT / "infrastructure")
    _module(f"{_PKG}.infrastructure.database", _ROOT / "infrastructure" / "database")
    _module(f"{_PKG}.infrastructure.database.sql_utils", safe_set_subset_string=MagicMock(return_value=True))
    _module(f"{_PKG}.adapters", _ROOT / "adapters")
    _module(f"{_PKG}.adapters.backends", _ROOT / "adapters" / "backends")
    _module(f"{_PKG}.adapters.backends.spatialite", _ROOT / "adapters" / "backends" / "spatialite")
    return _load_file(full, _ROOT / "adapters" / "backends" / "spatialite" / "expression_builder.py",
                      f"{_PKG}.adapters.backends.spatialite")


def _sanitizer():
    name = f"{_PKG}.sanitizer"
    if name in sys.modules:
        return sys.modules[name]
    return _load_file(name, _ROOT / "core" / "filter" / "expression_sanitizer.py", _PKG)


@pytest.fixture
def gpkg(tmp_path):
    """A SQLite file holding the R-tree table of ``batiment``."""
    path = tmp_path / "bdtopo.gpkg"
    connection = sqlite3.connect(str(path))
    connection.execute("CREATE TABLE batiment (fid INTEGER PRIMARY KEY, geometrie BLOB)")
    connection.execute("CREATE TABLE rtree_batiment_geometrie (id INTEGER, minx REAL, maxx REAL, miny REAL, maxy REAL)")
    connection.execute("CREATE TABLE gpkg_extensions (table_name TEXT, column_name TEXT, extension_name TEXT)")
    connection.execute("INSERT INTO gpkg_extensions VALUES ('batiment', 'geometrie', 'gpkg_rtree_index')")
    connection.commit()
    connection.close()
    return path


@pytest.fixture(autouse=True)
def _fresh_cache():
    mod = _load()
    mod.clear_rtree_cache()
    yield
    mod.clear_rtree_cache()


def _layer(path, table="batiment", provider="ogr", geom="geometrie"):
    layer = MagicMock()
    layer.name.return_value = table
    layer.source.return_value = f"{path}|layername={table}"
    layer.providerType.return_value = provider
    layer.dataProvider.return_value.geometryColumn.return_value = geom
    layer.crs.return_value.isValid.return_value = True
    layer.crs.return_value.authid.return_value = "EPSG:2154"
    return layer


class _Rect:
    def __init__(self, xmin, ymin, xmax, ymax):
        self._v = (xmin, ymin, xmax, ymax)

    def isNull(self):
        return False

    def xMinimum(self):
        return self._v[0]

    def yMinimum(self):
        return self._v[1]

    def xMaximum(self):
        return self._v[2]

    def yMaximum(self):
        return self._v[3]


def _install_fake_geometry(monkeypatch, bbox=(10.0, 20.0, 12.0, 22.0), transformed=None):
    core = sys.modules["qgis.core"]
    geometry = SimpleNamespace(isEmpty=lambda: False, boundingBox=lambda: _Rect(*bbox))
    monkeypatch.setattr(core, "QgsGeometry", SimpleNamespace(fromWkt=lambda wkt: geometry), raising=False)
    crs = MagicMock()
    crs.return_value.isValid.return_value = True
    monkeypatch.setattr(core, "QgsCoordinateReferenceSystem", crs, raising=False)
    transform = MagicMock()
    transform.return_value.transformBoundingBox.return_value = _Rect(*(transformed or bbox))
    monkeypatch.setattr(core, "QgsCoordinateTransform", transform, raising=False)
    monkeypatch.setattr(core, "QgsProject", MagicMock(), raising=False)
    return transform


def _build(mod, layer, predicates=None, buffer_value=None, source_srid=2154):
    builder = mod.SpatialiteExpressionBuilder({})
    return builder.build_expression(
        layer_props={"layer": layer, "layer_name": layer.name()},
        predicates=predicates or {"intersects": True},
        source_geom="POLYGON ((10 20, 12 20, 12 22, 10 22, 10 20))",
        buffer_value=buffer_value,
        source_srid=source_srid,
    )


@pytest.mark.unit
class TestRtreePrefilter:

    def test_gpkg_layer_with_rtree_gets_the_candidate_clause(self, gpkg, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)

        expression = _build(mod, _layer(gpkg))

        assert expression.startswith(
            'ROWID IN (SELECT id FROM "rtree_batiment_geometrie" '
            'WHERE minx <= 12.0 AND maxx >= 10.0 AND miny <= 22.0 AND maxy >= 20.0) AND '
        )
        assert expression.endswith("ST_Intersects(\"geometrie\", ST_MakeValid(ST_GeomFromText('POLYGON ((10 20, 12 20, 12 22, 10 22, 10 20))', 2154)))")

    def test_buffer_grows_the_box(self, gpkg, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)

        expression = _build(mod, _layer(gpkg), buffer_value=5)

        assert "minx <= 17.0 AND maxx >= 5.0 AND miny <= 27.0 AND maxy >= 15.0" in expression

    def test_negative_buffer_keeps_the_original_box(self, gpkg, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)

        expression = _build(mod, _layer(gpkg), buffer_value=-5)

        assert "minx <= 12.0 AND maxx >= 10.0" in expression

    def test_box_is_transformed_when_srids_differ(self, gpkg, monkeypatch):
        mod = _load()
        transform = _install_fake_geometry(monkeypatch, transformed=(100.0, 200.0, 110.0, 220.0))

        expression = _build(mod, _layer(gpkg), source_srid=4326)

        transform.assert_called_once()
        assert "minx <= 110.0 AND maxx >= 100.0 AND miny <= 220.0 AND maxy >= 200.0" in expression
        assert "ST_Transform(" in expression

    def test_no_rtree_table_means_plain_predicate(self, tmp_path, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)
        path = tmp_path / "plain.gpkg"
        sqlite3.connect(str(path)).close()

        expression = _build(mod, _layer(path))

        assert expression.startswith("ST_Intersects(")

    def test_disjoint_predicate_disables_the_prefilter(self, gpkg, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)

        expression = _build(mod, _layer(gpkg), predicates={"disjoint": True})

        assert "ROWID" not in expression and expression.startswith("ST_Disjoint(")

    def test_non_gpkg_layer_is_untouched(self, gpkg, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)
        layer = _layer(gpkg, provider="spatialite")
        layer.source.return_value = "dbname='/data/x.sqlite' table=\"batiment\" (geometrie)"

        assert _build(mod, layer).startswith("ST_Intersects(")

    def test_unavailable_bbox_falls_back_to_plain_predicate(self, gpkg, monkeypatch):
        mod = _load()
        core = sys.modules["qgis.core"]
        monkeypatch.setattr(core, "QgsGeometry", SimpleNamespace(fromWkt=lambda wkt: None), raising=False)

        assert _build(mod, _layer(gpkg)).startswith("ST_Intersects(")

    def test_lookup_is_cached_per_file(self, gpkg, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)
        _build(mod, _layer(gpkg))
        monkeypatch.setattr(mod, "sqlite3", SimpleNamespace(
            connect=MagicMock(side_effect=AssertionError("second lookup")),
            OperationalError=sqlite3.OperationalError, Error=sqlite3.Error))

        assert "ROWID IN" in _build(mod, _layer(gpkg))

    def test_unregistered_rtree_table_is_ignored(self, tmp_path, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)
        path = tmp_path / "stale.gpkg"
        connection = sqlite3.connect(str(path))
        connection.execute("CREATE TABLE rtree_batiment_geometrie (id INTEGER, minx REAL, maxx REAL, miny REAL, maxy REAL)")
        connection.execute("CREATE TABLE gpkg_extensions (table_name TEXT, column_name TEXT, extension_name TEXT)")
        connection.commit()
        connection.close()

        assert _build(mod, _layer(path)).startswith("ST_Intersects(")

    def test_transient_lookup_failure_is_not_cached(self, gpkg, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)
        monkeypatch.setattr(mod, "sqlite3", SimpleNamespace(
            connect=MagicMock(side_effect=sqlite3.OperationalError("database is locked")),
            OperationalError=sqlite3.OperationalError, Error=sqlite3.Error))
        assert _build(mod, _layer(gpkg)).startswith("ST_Intersects(")

        monkeypatch.undo()
        _install_fake_geometry(monkeypatch)
        assert "ROWID IN" in _build(mod, _layer(gpkg))

    def test_non_finite_box_disables_the_prefilter(self, gpkg, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch, bbox=(float("-inf"), 20.0, float("inf"), 22.0))

        expression = _build(mod, _layer(gpkg))

        assert "ROWID" not in expression and "inf" not in expression

    def test_only_overlap_implying_predicates_get_the_prefilter(self, gpkg, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)

        assert "ROWID IN" in _build(mod, _layer(gpkg), predicates={"within": True, "touches": True})
        assert "ROWID" not in _build(mod, _layer(gpkg), predicates={"intersects": True, "disjoint": True})

    def test_layer_location_parsing(self):
        mod = _load()
        layer = MagicMock()
        layer.source.return_value = "C:/data/bd topo.gpkg|layername=troncon_de_route|geometrytype=LineString"

        assert mod.gpkg_layer_location(layer) == ("C:/data/bd topo.gpkg", "troncon_de_route")
        layer.source.return_value = "/data/x.shp"
        assert mod.gpkg_layer_location(layer) == ("/data/x.shp", None)

    def test_sanitizer_and_geometric_detection_keep_the_clause(self, gpkg, monkeypatch):
        mod = _load()
        _install_fake_geometry(monkeypatch)
        expression = _build(mod, _layer(gpkg))

        assert _sanitizer().sanitize_subset_string(expression) == expression
        assert mod.SpatialiteExpressionBuilder({})._is_geometric_filter(expression) is True

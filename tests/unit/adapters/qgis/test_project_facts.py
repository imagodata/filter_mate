# -*- coding: utf-8 -*-
"""What the welcome of AGENT reads of the project (``adapters/qgis/project_facts.py``), on fake layers (2026-11-22).

The kind of a layer and the rule of a raster that only draws a picture are the plugin's own (``point_cloud_capability``)
and are replaced here by fakes: what they say of real layers is checked in ``tests/qgis_headless/check_agent_chat.py``.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_project_facts_test"


class Geometry:
    POLYGON, POINT = "polygon", "point"


class Layer:
    """A layer as the facts read it: its kind, provider, bands, selection, filter, validity."""

    def __init__(self, kind, provider="ogr", valid=True, selected=0, subset="", bands=1, byte=False, geometry=None,
                 picture=False, name="l"):
        self.kind, self.provider, self.valid, self.selected = kind, provider, valid, selected
        self.subset, self.bands, self.byte, self.geometry, self.picture = subset, bands, byte, geometry, picture
        self.name = name
        self.destroyed = False

    def id(self):
        if self.destroyed:
            raise RuntimeError("wrapped C/C++ object has been deleted")
        return f"id_{self.name}_{id(self)}"

    def isValid(self):
        if self.destroyed:
            raise RuntimeError("wrapped C/C++ object has been deleted")
        return self.valid

    def providerType(self):
        return self.provider

    def selectedFeatureCount(self):
        return self.selected

    def subsetString(self):
        return self.subset

    def bandCount(self):
        return self.bands

    def dataProvider(self):
        return types.SimpleNamespace(dataType=lambda band: "Byte" if self.byte else "Float32")

    def wkbType(self):
        return self.geometry

    def featureCount(self):
        raise AssertionError("the facts never count features")


class Project:
    def __init__(self, *layers):
        self.layers = {layer.id(): layer for layer in layers}

    def mapLayers(self):
        return dict(self.layers)


@pytest.fixture
def facts_module(monkeypatch):
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                       (".core.domain", _ROOT / "core" / "domain"), (".adapters", _ROOT / "adapters"),
                       (".adapters.qgis", _ROOT / "adapters" / "qgis")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        monkeypatch.setitem(sys.modules, _PKG + name, package)
    capability = types.ModuleType(_PKG + ".adapters.qgis.point_cloud_capability")
    kinds = importlib.import_module(_PKG + ".core.domain.layer_kind").LayerKind  # the one the module compares with
    capability.layer_kind_by_class = lambda layer: getattr(kinds, layer.kind)
    capability.is_non_analysis_raster = lambda layer: layer.picture
    monkeypatch.setitem(sys.modules, capability.__name__, capability)
    registry = types.ModuleType(_PKG + ".adapters.qgis.coverage_layers")
    registry.__path__ = []
    monkeypatch.setitem(sys.modules, registry.__name__, registry)
    snapshots = types.ModuleType(_PKG + ".adapters.qgis.coverage_layers.snapshots")
    snapshots.DERIVED = {}
    snapshots.registry = lambda: types.SimpleNamespace(get=lambda layer_id: snapshots.DERIVED.get(layer_id))
    monkeypatch.setitem(sys.modules, snapshots.__name__, snapshots)
    qgis_core = types.ModuleType("qgis.core")
    qgis_core.QgsProject = type("QgsProject", (), {})
    qgis_core.Qgis = types.SimpleNamespace(DataType=types.SimpleNamespace(Byte="Byte"))
    qgis_core.QgsWkbTypes = types.SimpleNamespace(
        geometryType=lambda wkb: wkb,
        GeometryType=types.SimpleNamespace(PolygonGeometry=Geometry.POLYGON))
    monkeypatch.setitem(sys.modules, "qgis.core", qgis_core)
    module = importlib.import_module(_PKG + ".adapters.qgis.project_facts")
    module.snapshots = snapshots
    yield module
    for name in [name for name in sys.modules if name.startswith(_PKG)]:
        sys.modules.pop(name, None)


def vector(**given):
    return Layer("VECTOR", **given)


def raster(**given):
    return Layer("RASTER", provider="gdal", **given)


def read(module, *layers, active=None):
    return module.read_facts(project=Project(*layers), active=active)


def test_an_empty_project_is_known_and_empty(facts_module):
    facts = read(facts_module)
    assert facts.known and facts.layers == 0 and facts.tokens() >= {"no_layers", "no_data", "no_basemap"}


def test_layers_are_counted_by_kind_and_nothing_is_counted_by_features(facts_module):
    cloud = Layer("POINT_CLOUD", provider="pdal")
    facts = read(facts_module, vector(), vector(selected=3, subset="a > 1"), raster(), cloud)
    assert (facts.layers, facts.vectors, facts.rasters, facts.point_clouds) == (4, 2, 1, 1)
    assert (facts.selected, facts.filtered, facts.tiles) == (3, 1, 0)


def test_a_layer_that_is_not_valid_is_not_counted(facts_module):
    """2026-11-22: a project whose terrain model was moved offered to map its slope."""
    moved = raster(valid=False, name="moved")
    facts = read(facts_module, moved, vector(), active=moved)
    assert (facts.layers, facts.rasters, facts.elevations) == (1, 0, 0)
    assert facts.active == "" and "active_elevation" not in facts.tokens()


@pytest.mark.parametrize("layer", [
    Layer("RASTER", provider="wms"),  # a WMS, an XYZ basemap
    Layer("RASTER", provider="gdal", picture=True),  # a WMS described in XML for GDAL
    Layer("RASTER", provider="arcgismapserver"),
    Layer("VECTOR_TILE", provider="xyzvectortiles"),  # a vector tile basemap
])
def test_a_basemap_is_not_data(facts_module, layer):
    facts = read(facts_module, layer, active=layer)
    tokens = facts.tokens()
    assert facts.layers == 1 and facts.tiles == 1 and facts.rasters == 0 and facts.vectors == 0
    assert "no_data" in tokens and "data" not in tokens and "no_basemap" not in tokens
    assert facts.active == "other" and "active_raster" not in tokens


@pytest.mark.parametrize("kind", ["OTHER", "POINT_CLOUD"])
def test_a_mesh_or_a_group_is_a_layer_but_not_data_and_not_a_basemap(facts_module, kind):
    layer = Layer(kind, provider="mdal" if kind == "OTHER" else "pdal")
    facts = read(facts_module, layer)
    if kind == "OTHER":
        assert facts.layers == 1 and "no_data" in facts.tokens() and "no_basemap" in facts.tokens()
    else:
        assert "data" in facts.tokens()


def test_one_band_of_numbers_is_an_elevation_and_a_picture_is_not(facts_module):
    dem, rgb, scan, ortho = (raster(bands=1, name="dem"), raster(bands=3, byte=True, name="rgb"),
                             raster(bands=1, byte=True, name="scan"), raster(bands=3, name="ortho"))
    facts = read(facts_module, dem, rgb, scan, ortho, active=dem)
    assert facts.rasters == 4 and facts.elevations == 1 and facts.active_elevation
    assert {"elevation", "active_elevation", "active_raster"} <= facts.tokens()
    for picture in (rgb, scan, ortho):
        tokens = read(facts_module, picture, active=picture).tokens()
        assert "active_raster" in tokens and not {"elevation", "active_elevation"} & tokens


def test_a_web_service_vector_is_not_read_for_statistics_or_its_selection(facts_module):
    wfs = vector(provider="wfs", selected=5, name="wfs")
    facts = read(facts_module, wfs, active=wfs)
    assert facts.selected == 5 and facts.selected_local == 0 and not facts.active_local
    assert {"selection", "active_vector"} <= facts.tokens()
    assert not {"local_selection", "active_local"} & facts.tokens()
    for provider in ("oapif", "arcgisfeatureserver"):
        assert not read(facts_module, vector(provider=provider, selected=1)).selected_local
    local = vector(selected=2, name="local")
    facts = read(facts_module, wfs, local, active=local)
    assert facts.selected == 7 and facts.selected_local == 2 and {"local_selection", "active_local"} <= facts.tokens()


def test_a_database_layer_is_remote_but_local_for_the_tools(facts_module):
    pg = vector(provider="postgres", selected=1, name="pg")
    facts = read(facts_module, pg, active=pg)
    assert facts.remote == 1 and facts.selected_local == 1 and facts.active_local


def test_only_polygons_count_as_polygons(facts_module):
    assert read(facts_module, vector(geometry=Geometry.POINT)).polygons == 0
    assert read(facts_module, vector(geometry=Geometry.POINT), vector(geometry=Geometry.POLYGON)).polygons == 1


def test_a_layer_filtered_by_a_copy_is_filtered(facts_module):
    """FilterMate filters a raster by cutting it: no subset string, only a derived source in its registry."""
    dem, cloud, plain = raster(name="dem"), Layer("POINT_CLOUD", provider="pdal", name="c"), raster(name="p")
    assert read(facts_module, dem, plain).filtered == 0
    facts_module.snapshots.DERIVED[dem.id()] = object()
    assert read(facts_module, dem, plain).filtered == 1
    facts_module.snapshots.DERIVED[cloud.id()] = object()
    assert read(facts_module, dem, cloud, plain).filtered == 2
    assert "filter" in read(facts_module, dem).tokens()


def test_a_layer_destroyed_meanwhile_is_left_out_and_nothing_is_raised(facts_module):
    gone, kept = vector(name="gone"), vector(name="kept")
    project = Project(gone, kept)
    gone.destroyed = True
    facts = facts_module.read_facts(project=project, active=gone)
    assert facts.known and facts.vectors == 1 and facts.active == ""


def test_a_reading_that_fails_gives_unknown_facts(facts_module):
    class Broken:
        def mapLayers(self):
            raise RuntimeError("the project is closing")

    facts = facts_module.read_facts(project=Broken())
    assert not facts.known and facts.tokens() == frozenset()

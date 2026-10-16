# -*- coding: utf-8 -*-
"""Source geometry of a SpatiaLite / GeoPackage filter, end to end (2026-10-17).

``process_spatialite_geometries`` never simplifies the source any more (it
was cut by up to 100 m, then by 1 m for Intersects / Disjoint): the
expression builder inlines it while that is cheap and hands the layer to the
OGR backend otherwise, both exact. Measured on the real Toulouse Metropole
polygon, a 1 m simplification changed 84 of 98,687 roads and still cost 6 s
per count. Also covered: the geometry cache key. QGIS is mocked; geometries
are duck-typed fakes.
"""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[5]
ROOT = "filter_mate"
SPATIALITE = f"{ROOT}.adapters.backends.spatialite"


def _load(name, path, stubs):
    """Load ``path`` as module ``name`` with ``stubs`` in sys.modules, then restore sys.modules."""
    saved = {key: sys.modules.get(key) for key in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


_history = types.ModuleType(f"{ROOT}.adapters.repositories.history_repository")
_history.HistoryRepository = MagicMock()
executor = _load(
    f"{SPATIALITE}._fm_test_chain_filter_executor",
    PLUGIN_ROOT / "adapters" / "backends" / "spatialite" / "filter_executor.py",
    {
        ROOT: _package(ROOT),
        f"{ROOT}.adapters": _package(f"{ROOT}.adapters"),
        f"{ROOT}.adapters.repositories": _package(f"{ROOT}.adapters.repositories"),
        f"{ROOT}.adapters.repositories.history_repository": _history,
        f"{ROOT}.adapters.backends": _package(f"{ROOT}.adapters.backends"),
        SPATIALITE: _package(SPATIALITE),
    },
)


class _Merged:
    """The dissolved source; ``simplify`` must never be called."""

    def __init__(self, base):
        self.base = base

    def isEmpty(self):
        return False

    def wkbType(self):
        return 5

    def asWkt(self, precision=None):
        return "M" * self.base

    def simplify(self, tolerance):
        raise AssertionError("the source geometry was simplified")


class _Part:
    def isEmpty(self):
        return False

    def isMultipart(self):
        return False


class _Feature:
    def __init__(self, fid):
        self._fid = fid

    def id(self):
        return self._fid

    def hasGeometry(self):
        return True

    def geometry(self):
        return _Part()


@pytest.fixture
def qgis_env(monkeypatch):
    """What process_spatialite_geometries imports, as fakes."""
    merged = {}
    qgis_core = sys.modules["qgis.core"]
    monkeypatch.setattr(qgis_core, "QgsGeometry", lambda geometry: geometry, raising=False)
    wkb_types = MagicMock()
    wkb_types.hasZ.return_value = False
    wkb_types.hasM.return_value = False
    monkeypatch.setattr(qgis_core, "QgsWkbTypes", wkb_types, raising=False)
    monkeypatch.setattr(qgis_core, "QgsCoordinateReferenceSystem", MagicMock(), raising=False)
    monkeypatch.setattr(qgis_core, "QgsCoordinateTransform", MagicMock(), raising=False)

    core_geometry = types.ModuleType(f"{ROOT}.core.geometry")
    core_geometry.validate_geometry = lambda geometry: True
    core_geometry.safe_unary_union = lambda geometries: merged["geometry"]
    core_geometry.safe_collect_geometry = lambda geometries: merged["geometry"]
    core_geometry.safe_as_geometry_collection = lambda geometry: [geometry]
    core_geometry.extract_polygons_from_collection = lambda geometry: []
    core_geometry.get_geometry_type_name = lambda geometry: "MultiLineString"
    monkeypatch.setitem(sys.modules, ROOT, sys.modules.get(ROOT) or _package(ROOT))
    monkeypatch.setitem(sys.modules, f"{ROOT}.core", _package(f"{ROOT}.core"))
    monkeypatch.setitem(sys.modules, f"{ROOT}.core.geometry", core_geometry)
    return merged


FEATURES = [_Feature(i) for i in range(691)]


class TestProcessSpatialiteGeometries:
    @pytest.mark.parametrize("predicates", [["ST_Crosses"], ["ST_Intersects"], ["ST_Disjoint"], None])
    @pytest.mark.parametrize("size", [87_259, 236_398, 2_000_000])
    def test_source_is_never_simplified(self, qgis_env, predicates, size):
        qgis_env["geometry"] = _Merged(size)
        context = executor.SpatialiteSourceContext(
            source_layer_crs_authid="EPSG:2154",
            predicates=predicates,
            geometry_to_wkt=lambda geometry, crs_authid: geometry.asWkt(3),
        )
        wkt = executor.process_spatialite_geometries(FEATURES, context)
        assert len(wkt) == size

    def test_context_has_no_simplification_callback(self):
        assert not hasattr(executor.SpatialiteSourceContext(), "simplify_geometry_adaptive")


class TestGeometryCacheKey:
    def test_variant_holds_the_predicates(self):
        cross = executor._source_cache_variant(executor.SpatialiteSourceContext(predicates=["ST_Crosses"]))
        intersects = executor._source_cache_variant(executor.SpatialiteSourceContext(predicates=["ST_Intersects"]))
        assert cross != intersects
        # Order-insensitive.
        both = executor._source_cache_variant(executor.SpatialiteSourceContext(predicates=["ST_Crosses", "ST_Intersects"]))
        assert both == executor._source_cache_variant(executor.SpatialiteSourceContext(predicates=["ST_Intersects", "ST_Crosses"]))

    def test_entry_for_one_predicate_is_not_served_to_another(self):
        from infrastructure.cache.geometry_cache import SourceGeometryCache

        cache = SourceGeometryCache()
        key_args = dict(layer_id="rivers", subset_string="")
        intersects = executor._source_cache_variant(executor.SpatialiteSourceContext(predicates=["ST_Intersects"]))
        cross = executor._source_cache_variant(executor.SpatialiteSourceContext(predicates=["ST_Crosses"]))
        cache.put(FEATURES, 0.0, "EPSG:2154", {"wkt": "W"}, variant=intersects, **key_args)
        assert cache.get(FEATURES, 0.0, "EPSG:2154", variant=cross, **key_args) is None
        assert cache.get(FEATURES, 0.0, "EPSG:2154", variant=intersects, **key_args) == {"wkt": "W"}

# -*- coding: utf-8 -*-
"""Source geometry of a SpatiaLite / GeoPackage filter, end to end (2026-10-16).

``process_spatialite_geometries`` with the task's predicates, the real
GeometryPreparationAdapter behind the simplification callback (as wired by
FilterEngineTask → GeometryHandler), and the geometry cache key. Regression
for the "Cross on 691 Toulouse rivers" bug: the 236 KB source was cut to
14 KB with a 100 m tolerance. QGIS is mocked; geometries are duck-typed fakes
whose WKT shrinks with the simplification tolerance.
"""
import ast
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
preparation = _load(
    f"{ROOT}.adapters.qgis._fm_test_chain_geometry_preparation",
    PLUGIN_ROOT / "adapters" / "qgis" / "geometry_preparation.py",
    {},
)
preparation.QgsWkbTypes = MagicMock()
preparation.QgsWkbTypes.geometryType = lambda wkb_type: wkb_type


class _FakeCrs:
    def __init__(self, authid=""):
        self._authid = authid

    def isValid(self):
        return self._authid in ("EPSG:2154", "EPSG:4326")

    def isGeographic(self):
        return self._authid == "EPSG:4326"


preparation.QgsCoordinateReferenceSystem = _FakeCrs


def _inline_limit():
    tree = ast.parse((PLUGIN_ROOT / "adapters" / "backends" / "spatialite" / "expression_builder.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "SPATIALITE_WKT_INLINE_MAX_LENGTH":
            return node.value.value
    raise AssertionError("SPATIALITE_WKT_INLINE_MAX_LENGTH not found")


INLINE_LIMIT = _inline_limit()


class _Rect:
    def __init__(self, size):
        self._size = size

    def width(self):
        return self._size

    def height(self):
        return self._size


class _Merged:
    """The dissolved source: WKT length = ``base // (1 + tolerance * shrink)``."""

    def __init__(self, base, tolerance=0.0, shrink=5.0, calls=None):
        self.base = base
        self.tolerance = tolerance
        self.shrink = shrink
        self.calls = [] if calls is None else calls

    def isEmpty(self):
        return False

    def wkbType(self):
        return 5

    def boundingBox(self):
        return _Rect(30_000.0)

    def asWkt(self, precision=None):
        return "M" * int(self.base // (1 + self.tolerance * self.shrink))

    def simplify(self, tolerance):
        self.calls.append(tolerance)
        return _Merged(self.base, tolerance, self.shrink, self.calls)


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
    builder = types.ModuleType(f"{SPATIALITE}.expression_builder")
    builder.SPATIALITE_WKT_SIMPLIFY_THRESHOLD = INLINE_LIMIT
    monkeypatch.setitem(sys.modules, ROOT, sys.modules.get(ROOT) or _package(ROOT))
    monkeypatch.setitem(sys.modules, f"{ROOT}.core", _package(f"{ROOT}.core"))
    monkeypatch.setitem(sys.modules, f"{ROOT}.core.geometry", core_geometry)
    monkeypatch.setitem(sys.modules, f"{SPATIALITE}.expression_builder", builder)
    return merged


def _context(predicates, simplify_calls):
    adapter = preparation.GeometryPreparationAdapter(project=MagicMock())

    def simplify(geometry, max_wkt_length=None, crs_authid=None, predicates=None):
        # FilterEngineTask._simplify_geometry_adaptive → GeometryHandler → adapter
        simplify_calls.append({"max_wkt_length": max_wkt_length, "predicates": predicates})
        result = adapter.simplify_geometry_adaptive(
            geometry=geometry, max_wkt_length=max_wkt_length, crs_authid=crs_authid, predicates=predicates
        )
        return result.geometry if result.success and result.geometry else geometry

    return executor.SpatialiteSourceContext(
        source_layer_crs_authid="EPSG:2154",
        predicates=predicates,
        geometry_to_wkt=lambda geometry, crs_authid: geometry.asWkt(3),
        simplify_geometry_adaptive=simplify,
    )


FEATURES = [_Feature(i) for i in range(691)]


class TestProcessSpatialiteGeometries:
    @pytest.mark.parametrize("predicates", [["ST_Crosses"], ["ST_Touches"], ["ST_Intersects", "ST_Crosses"], None])
    def test_vertex_predicates_keep_the_toulouse_rivers_exact(self, qgis_env, predicates):
        qgis_env["geometry"] = _Merged(236_398)
        calls = []
        wkt = executor.process_spatialite_geometries(FEATURES, _context(predicates, calls))
        assert len(wkt) == 236_398
        assert qgis_env["geometry"].calls == []
        # The task's predicates reached the simplification, with the one threshold.
        assert calls == [{"max_wkt_length": INLINE_LIMIT, "predicates": predicates}]

    def test_intersects_simplified_within_one_metre(self, qgis_env):
        qgis_env["geometry"] = _Merged(236_398, shrink=5.0)
        calls = []
        wkt = executor.process_spatialite_geometries(FEATURES, _context(["ST_Intersects"], calls))
        assert len(wkt) <= INLINE_LIMIT
        assert qgis_env["geometry"].calls
        assert max(qgis_env["geometry"].calls) <= preparation.SOURCE_SIMPLIFY_MAX_TOLERANCE

    def test_small_source_never_reaches_the_simplification(self, qgis_env):
        qgis_env["geometry"] = _Merged(INLINE_LIMIT - 1)
        calls = []
        wkt = executor.process_spatialite_geometries(FEATURES, _context(["ST_Intersects"], calls))
        assert len(wkt) == INLINE_LIMIT - 1
        assert calls == []


class TestGeometryCacheKey:
    def test_variant_holds_the_predicates(self, qgis_env):
        cross = executor._source_cache_variant(executor.SpatialiteSourceContext(predicates=["ST_Crosses"]))
        intersects = executor._source_cache_variant(executor.SpatialiteSourceContext(predicates=["ST_Intersects"]))
        assert cross != intersects
        # Order-insensitive.
        both = executor._source_cache_variant(executor.SpatialiteSourceContext(predicates=["ST_Crosses", "ST_Intersects"]))
        assert both == executor._source_cache_variant(executor.SpatialiteSourceContext(predicates=["ST_Intersects", "ST_Crosses"]))

    def test_wkt_cached_for_intersects_is_not_served_to_cross(self, qgis_env):
        from infrastructure.cache.geometry_cache import SourceGeometryCache

        class _TaskCache:
            """GeometryCache API (core/tasks/cache) over the real SourceGeometryCache."""

            def __init__(self):
                self.inner = SourceGeometryCache()

            def get(self, layer_id, feature_ids=None, buffer_value=None, target_crs_authid=None,
                    subset_string=None, variant=None):
                return self.inner.get(feature_ids or [], buffer_value or 0.0, target_crs_authid,
                                      layer_id=layer_id, subset_string=subset_string, variant=variant)

            def put(self, layer_id, geometry, feature_ids=None, buffer_value=None, target_crs_authid=None,
                    subset_string=None, variant=None):
                self.inner.put(feature_ids or [], buffer_value or 0.0, target_crs_authid, geometry,
                               layer_id=layer_id, subset_string=subset_string, variant=variant)

        cache = _TaskCache()
        key_args = dict(layer_id="rivers", feature_ids=FEATURES, buffer_value=None,
                        target_crs_authid="EPSG:2154", subset_string="")
        intersects = executor.SpatialiteSourceContext(predicates=["ST_Intersects"])
        cache.put(geometry={"wkt": "SIMPLIFIED"}, variant=executor._source_cache_variant(intersects), **key_args)
        cross = executor.SpatialiteSourceContext(predicates=["ST_Crosses"])
        assert cache.get(variant=executor._source_cache_variant(cross), **key_args) is None
        assert cache.get(variant=executor._source_cache_variant(intersects), **key_args) == {"wkt": "SIMPLIFIED"}

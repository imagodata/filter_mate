# -*- coding: utf-8 -*-
"""The OGR backend tests the union of the source, like the SQL backends (2026-10-17).

SpatiaLite / GeoPackage inline one dissolved WKT of the source. The OGR
backend - which also takes over the layers whose source is too costly to
inline - ran select-by-location with one test per source feature: on the
Toulouse rivers, "Cross" returned 702 roads against ~747 for the union (a
road meeting two rivers at a junction crosses the network, not either river)
and ran 691 target requests (98 s for troncon_de_route). Now the source is
dissolved once per task and each target is read once and tested against the
prepared union. These tests pin that semantics for every predicate.
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


class _FakePort:
    def __init__(self, task_params):
        self.task_params = task_params
        self.warnings = []

    def log_debug(self, msg): pass
    def log_info(self, msg): pass
    def log_warning(self, msg): self.warnings.append(msg)
    def log_error(self, msg): pass


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


def _load_builder():
    port = types.ModuleType(f"{ROOT}.core.ports.geometric_filter_port")
    port.GeometricFilterPort = _FakePort
    sql_utils = types.ModuleType(f"{ROOT}.infrastructure.database.sql_utils")
    sql_utils.safe_set_subset_string = MagicMock(return_value=True)
    stubs = {
        ROOT: _package(ROOT),
        f"{ROOT}.core": _package(f"{ROOT}.core"),
        f"{ROOT}.core.ports": _package(f"{ROOT}.core.ports"),
        f"{ROOT}.core.ports.geometric_filter_port": port,
        f"{ROOT}.infrastructure": _package(f"{ROOT}.infrastructure"),
        f"{ROOT}.infrastructure.database": _package(f"{ROOT}.infrastructure.database"),
        f"{ROOT}.infrastructure.database.sql_utils": sql_utils,
        f"{ROOT}.adapters": _package(f"{ROOT}.adapters"),
        f"{ROOT}.adapters.backends": _package(f"{ROOT}.adapters.backends"),
        f"{ROOT}.adapters.backends.ogr": _package(f"{ROOT}.adapters.backends.ogr"),
    }
    saved = {key: sys.modules.get(key) for key in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(
            f"{ROOT}.adapters.backends.ogr._fm_test_union_expression_builder",
            PLUGIN_ROOT / "adapters" / "backends" / "ogr" / "expression_builder.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


ogr_builder = _load_builder()

LINE, MULTILINE, COLLECTION = 2, 5, 7


class _Geom:
    """A geometry known by name; ``relations`` says how it relates to the source union."""

    def __init__(self, name="g", wkb_type=LINE, empty=False):
        self.name = name
        self._type = wkb_type
        self._empty = empty

    def isEmpty(self):
        return self._empty

    def wkbType(self):
        return self._type

    def makeValid(self):
        return self

    def constGet(self):
        return self

    def boundingBox(self):
        return ("bbox", self.name)


class _Feature:
    def __init__(self, fid=0, geometry=None):
        self._fid = fid
        self._geometry = geometry

    def id(self):
        return self._fid

    def hasGeometry(self):
        return self._geometry is not None

    def geometry(self):
        return self._geometry


class _Request:
    def __init__(self):
        self.rect = None
        self.crs = None

    def setNoAttributes(self):
        return self

    def setDestinationCrs(self, crs, context):
        self.crs = crs
        return self

    def setFilterRect(self, rect):
        self.rect = rect
        return self


class _Layer:
    def __init__(self, name, features, wkb_type=LINE, layer_id=None):
        self._name = name
        self.features = list(features)
        self._type = wkb_type
        self._id = layer_id or name
        self.requests = []

    def id(self):
        return self._id

    def name(self):
        return self._name

    def isValid(self):
        return True

    def featureCount(self):
        return len(self.features)

    def getFeatures(self, request=None):
        self.requests.append(request)
        return iter(self.features)

    def wkbType(self):
        return self._type

    def crs(self):
        return "EPSG:2154"

    def fields(self):
        return types.SimpleNamespace(indexOf=lambda name: -1)

    def removeSelection(self):
        pass


class _Engine:
    """Answers from ``relations[target name]`` (a set of predicate names)."""

    def __init__(self, source, relations):
        self.source = source
        self.relations = relations
        self.prepared = False

    def prepareGeometry(self):
        self.prepared = True

    def _has(self, name):
        return lambda geometry: name in self.relations.get(geometry.name, set())

    def __getattr__(self, name):
        if name in ("intersects", "within", "contains", "touches", "overlaps", "crosses", "isEqual"):
            return self._has(name)
        raise AttributeError(name)


@pytest.fixture
def qgis(monkeypatch):
    state = types.SimpleNamespace(unions=[], engines=[], relations={}, union_result=_Geom("union", MULTILINE))

    def _union(geometries):
        state.unions.append(list(geometries))
        return state.union_result

    def _engine(geometry):
        engine = _Engine(geometry, state.relations)
        state.engines.append(engine)
        return engine

    core = types.SimpleNamespace(
        QgsFeatureRequest=_Request,
        QgsGeometry=types.SimpleNamespace(unaryUnion=_union, createGeometryEngine=_engine),
        QgsVectorLayer=_Layer,
        QgsWkbTypes=types.SimpleNamespace(
            geometryType=lambda t: {LINE: "line", MULTILINE: "line", COLLECTION: "unknown"}[t]),
        QgsProject=types.SimpleNamespace(instance=lambda: types.SimpleNamespace(transformContext=lambda: "ctx")),
    )
    state.processing = types.SimpleNamespace(run=MagicMock())
    monkeypatch.setitem(sys.modules, "qgis", types.SimpleNamespace(core=core, processing=state.processing))
    monkeypatch.setitem(sys.modules, "qgis.core", core)
    monkeypatch.setitem(sys.modules, "qgis.processing", state.processing)
    # The module subclassed the conftest's QgsProcessingFeedback mock.
    feedback = MagicMock()
    feedback.return_value.isCanceled.return_value = False
    monkeypatch.setattr(ogr_builder, "CancellableFeedback", feedback)
    return state


def _rivers(count=691):
    return _Layer("cours_d_eau", [_Feature(i, _Geom(f"river{i}")) for i in range(count)], layer_id="rivers")


# Roads: how each relates to the river network (the union), per DE-9IM.
ROADS = {
    1: {"intersects", "crosses"},             # crosses one river
    2: {"intersects", "crosses"},             # meets two rivers at a junction: crosses the network
    3: {"intersects", "touches"},             # ends on a river bank
    4: set(),                                  # far away
    5: {"intersects", "within"},              # source within this target (target contains it)
    6: {"intersects", "contains"},            # target within the source
}


def _roads():
    return _Layer("troncon_de_route", [_Feature(fid, _Geom(f"road{fid}")) for fid in ROADS])


def _apply(qgis, predicate, task_params=None, rivers=None):
    qgis.relations.update({f"road{fid}": rel for fid, rel in ROADS.items()})
    queue = MagicMock()
    params = task_params if task_params is not None else {}
    params["_subset_queue_callback"] = queue
    builder = ogr_builder.OGRExpressionBuilder(task_params=params)
    builder._build_fid_filter = lambda layer, fids: f"fid IN ({', '.join(str(i) for i in sorted(fids))})"
    builder._get_primary_key = lambda layer: "fid"
    builder.source_geom = rivers or _rivers()
    roads = _roads()
    assert builder.apply_filter(roads, f'{{"predicates": ["{predicate}"]}}') is True, builder.last_error
    return queue.call_args.args[1], roads


@pytest.mark.parametrize("predicate, expected", [
    ("ST_Crosses", "fid IN (1, 2)"),
    ("ST_Intersects", "fid IN (1, 2, 3, 5, 6)"),
    ("ST_Touches", "fid IN (3)"),
    ("ST_Disjoint", "fid IN (4)"),
    ("ST_Contains", "fid IN (5)"),   # the target contains the source
    ("ST_Within", "fid IN (6)"),     # the target is within the source
])
def test_targets_are_tested_against_the_union_of_the_source(qgis, predicate, expected):
    subset, roads = _apply(qgis, predicate)
    assert subset == expected
    # One union of the 691 rivers, one prepared engine on it, no select-by-location.
    assert len(qgis.unions) == 1 and len(qgis.unions[0]) == 691
    assert len(qgis.engines) == 1 and qgis.engines[0].source is qgis.union_result and qgis.engines[0].prepared
    qgis.processing.run.assert_not_called()
    # One request through the target (and its subset), in the source CRS.
    (request,) = roads.requests
    assert request.crs == "EPSG:2154"
    assert request.rect == (None if predicate == "ST_Disjoint" else ("bbox", "union"))


def test_union_computed_once_per_task_for_all_targets(qgis):
    task_params = {}
    rivers = _rivers()
    for _target_layer in range(3):
        _apply(qgis, "ST_Crosses", task_params=task_params, rivers=rivers)
    assert len(qgis.unions) == 1


def test_single_feature_source_keeps_select_by_location(qgis):
    builder = ogr_builder.OGRExpressionBuilder(task_params={})
    assert builder._source_union(_rivers(1)) is None
    assert qgis.unions == []


def test_union_of_another_geometry_type_falls_back_with_a_warning(qgis):
    qgis.union_result = _Geom("union", COLLECTION)
    builder = ogr_builder.OGRExpressionBuilder(task_params={})
    assert builder._source_union(_rivers(3)) is None
    assert any("each source feature is tested on its own" in w for w in builder.warnings)


def test_covers_and_coveredby_are_not_intersects():
    codes = ogr_builder.OGRExpressionBuilder.PREDICATE_CODES
    assert codes["covers"] == codes["contains"]
    assert codes["coveredby"] == codes["within"]

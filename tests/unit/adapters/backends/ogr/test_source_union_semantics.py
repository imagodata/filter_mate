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
import json
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
LINE, MULTILINE, COLLECTION, POLYGON, POINT = 2, 5, 7, 3, 1
GEOMETRY_TYPES = {LINE: "line", MULTILINE: "line", COLLECTION: "unknown", POLYGON: "polygon", POINT: "point"}


class _Geom:
    """A geometry known by name; ``relations`` says how it relates to the source union."""

    def __init__(self, name="g", wkb_type=LINE, empty=False, parts=None):
        self.name = name
        self._type = wkb_type
        self._empty = empty
        self.parts = parts or []
        self.buffers = []

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

    # collection API (constGet() of a GeometryCollection)
    def numGeometries(self):
        return len(self.parts)

    def geometryN(self, index):
        return self.parts[index]

    def clone(self):
        return self

    def buffer(self, distance, segments, cap, join, miter):
        self.buffers.append(distance)
        return _Geom(f"{self.name}+buffer{distance}", POLYGON)


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


CLONES = {}


class _Layer:
    """A vector layer: ``features`` visible through ``subset``; ``all_features`` without it.

    Built as ``_Layer("clone:<id>", "<name> (unfiltered)", provider)`` by the
    fake provider registry: the same data read without any subset.
    """

    def __init__(self, name, features=(), wkb_type=LINE, layer_id=None, subset="", all_features=None,
                 storage="ESRI Shapefile"):
        if isinstance(name, str) and name.startswith("clone:"):
            original = CLONES[name[len("clone:"):]]
            name, features, wkb_type, layer_id = original._name, original.all_features, original._type, original._id
            subset, all_features, storage = "", original.all_features, original.storage
            self.is_clone = True
        else:
            self.is_clone = False
        self._name = name
        self.features = list(features)
        self.all_features = list(all_features if all_features is not None else features)
        self._type = wkb_type
        self._id = layer_id or name
        self.subset = subset
        self.storage = storage
        self.requests = []
        CLONES[self._id] = self

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

    def subsetString(self):
        return self.subset

    def source(self):
        return self._id

    def providerType(self):
        return "ogr"

    def dataProvider(self):
        return types.SimpleNamespace(storageType=lambda: self.storage)


class _Engine:
    """Answers from ``relations[target name]`` (a set of predicate names, or 'relate:<matrix>')."""

    def __init__(self, source, relations):
        self.source = source
        self.relations = relations
        self.prepared = False

    def prepareGeometry(self):
        self.prepared = True

    def _has(self, name):
        return lambda geometry: name in self.relations.get(geometry.name, set())

    def relate(self, geometry):
        for item in self.relations.get(geometry.name, set()):
            if item.startswith("relate:"):
                return item[len("relate:"):]
        return "FF*FF****"

    def __getattr__(self, name):
        if name in ("intersects", "within", "contains", "touches", "overlaps", "crosses", "isEqual"):
            return self._has(name)
        raise AttributeError(name)


class _Registry:
    def decodeUri(self, provider, source):
        return {"path": source, "subset": "old"}

    def encodeUri(self, provider, parts):
        assert "subset" not in parts
        return f"clone:{parts['path']}"


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

    class _QgsGeometry:
        unaryUnion = staticmethod(_union)
        createGeometryEngine = staticmethod(_engine)

        def __new__(cls, geometry=None):  # copy constructor
            return geometry

        @staticmethod
        def collectGeometry(geometries):
            return _Geom("collected:" + ",".join(g.name for g in geometries), geometries[0].wkbType())

    wkb_types = types.SimpleNamespace(
        geometryType=lambda t: GEOMETRY_TYPES[t],
        displayString=lambda t: "GeometryCollection" if t == COLLECTION else "MultiLineString",
        GeometryType=types.SimpleNamespace(PolygonGeometry="polygon", LineGeometry="line", PointGeometry="point"),
    )
    core = types.SimpleNamespace(
        QgsFeatureRequest=_Request,
        QgsGeometry=_QgsGeometry,
        QgsVectorLayer=_Layer,
        QgsWkbTypes=wkb_types,
        QgsProject=types.SimpleNamespace(instance=lambda: types.SimpleNamespace(transformContext=lambda: "ctx")),
        QgsProviderRegistry=types.SimpleNamespace(instance=lambda: _Registry()),
        Qgis=types.SimpleNamespace(
            EndCapStyle=types.SimpleNamespace(Round="round", Flat="flat", Square="square"),
            JoinStyle=types.SimpleNamespace(Round="round"),
        ),
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


def _roads(visible=None, subset=""):
    every = [_Feature(fid, _Geom(f"road{fid}")) for fid in ROADS]
    shown = every if visible is None else [f for f in every if f.id() in visible]
    return _Layer("troncon_de_route", shown, subset=subset, all_features=every)


def _builder(qgis, task_params=None, rivers=None):
    qgis.relations.update({f"road{fid}": rel for fid, rel in ROADS.items()})
    params = task_params if task_params is not None else {}
    params["_subset_queue_callback"] = MagicMock()
    builder = ogr_builder.OGRExpressionBuilder(task_params=params)
    builder._build_fid_filter = lambda layer, fids: f"fid IN ({', '.join(str(i) for i in sorted(fids))})"
    builder._get_primary_key = lambda layer: "fid"
    builder.source_geom = rivers or _rivers()
    return builder, params["_subset_queue_callback"]


def _apply(qgis, predicate, task_params=None, rivers=None, roads=None, old_subset=None, operator=None, extra=None):
    builder, queue = _builder(qgis, task_params, rivers)
    roads = roads or _roads()
    payload = {"predicates": [predicate]}
    payload.update(extra or {})
    assert builder.apply_filter(roads, json.dumps(payload), old_subset, operator) is True, builder.last_error
    return queue.call_args.args[1], roads


@pytest.mark.parametrize("predicate, expected", [
    ("ST_Crosses", "fid IN (1, 2)"),
    ("ST_Intersects", "fid IN (1, 2, 3, 5, 6)"),
    ("ST_Touches", "fid IN (3)"),
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
    # One request through the target, in the source CRS, on the source window.
    (request,) = roads.requests
    assert request.crs == "EPSG:2154"
    assert request.rect == ("bbox", "union")


def test_disjoint_is_the_complement_of_the_intersecting_window(qgis):
    # 2026-10-17: NOT (keys of the intersecting features): the key list stays
    # the size of the source window instead of the whole table.
    subset, roads = _apply(qgis, "ST_Disjoint")
    assert subset == "NOT (fid IN (1, 2, 3, 5, 6))"
    (request,) = roads.requests
    assert request.rect == ("bbox", "union")


def test_disjoint_with_nothing_intersecting_keeps_everything(qgis):
    qgis.relations.clear()
    builder, queue = _builder(qgis)
    qgis.relations.clear()  # nothing intersects the source
    assert builder.apply_filter(_roads(), '{"predicates": ["ST_Disjoint"]}') is True
    assert queue.call_args.args[1] == "1 = 1"


@pytest.mark.parametrize("predicate, matrix, expected", [
    # relate(source, target): target covers source <=> source covered by target
    ("ST_Covers", "1FF0FF212", "fid IN (1)"),     # source line inside the target, touching its end
    ("ST_Covers", "1010F0212", ""),                # crossing: not covered
    ("ST_CoveredBy", "1F1F00FF2", "fid IN (1)"),  # source covers the target
])
def test_covers_and_coveredby_are_exact_on_the_union_path(qgis, predicate, matrix, expected):
    qgis.relations.clear()
    roads = _Layer("troncon_de_route", [_Feature(1, _Geom("road1"))])
    builder, queue = _builder(qgis)
    qgis.relations["road1"] = {"intersects", f"relate:{matrix}"}
    assert builder.apply_filter(roads, json.dumps({"predicates": [predicate]})) is True
    assert queue.call_args.args[1] == (expected or "1 = 0")


# ---------------------------------------------------------------------------
# Old subset: the same rules as the SQL backends (2026-10-17)
# ---------------------------------------------------------------------------

def test_or_reads_the_target_without_its_filter(qgis):
    # The layer shows only road 4 (attribute filter "nature" = 'x'); in OR
    # the new keys are those of the whole layer, not of road 4 only.
    roads = _roads(visible={4}, subset='"nature" = \'x\'')
    subset, _ = _apply(qgis, "ST_Crosses", roads=roads, old_subset='"nature" = \'x\'', operator="OR")
    assert subset == '("nature" = \'x\') OR (fid IN (1, 2))'
    assert not roads.requests, "read through a reopened layer without subset"


def test_previous_spatial_filter_is_replaced_not_intersected(qgis):
    # The layer shows roads 4 and 5 (key list of a previous spatial step);
    # the orchestrator passes (old, None): the new filter replaces it.
    roads = _roads(visible={4, 5}, subset='"fid" IN (4, 5)')
    subset, _ = _apply(qgis, "ST_Crosses", roads=roads, old_subset='"fid" IN (4, 5)', operator=None)
    assert subset == "fid IN (1, 2)"


def test_and_with_an_attribute_filter_reads_through_it(qgis):
    roads = _roads(visible={1, 3}, subset='"nature" = \'x\'')
    subset, _ = _apply(qgis, "ST_Crosses", roads=roads, old_subset='"nature" = \'x\'', operator="AND")
    assert subset == '("nature" = \'x\') AND (fid IN (1))'
    assert roads.requests, "AND: reading through the attribute filter gives the same keys"


@pytest.mark.parametrize("operator, expected", [
    ("OR", '("nature" = \'x\') OR (1 = 0)'),
    ("AND", '("nature" = \'x\') AND (1 = 0)'),
    ("AND NOT", '("nature" = \'x\') AND NOT (1 = 0)'),
    (None, "1 = 0"),
])
def test_empty_selection_follows_the_combination_rules(qgis, operator, expected):
    qgis.relations.clear()
    builder, queue = _builder(qgis)
    qgis.relations.clear()
    roads = _roads(subset='"nature" = \'x\'')
    assert builder.apply_filter(roads, '{"predicates": ["ST_Crosses"]}', '"nature" = \'x\'', operator) is True
    assert queue.call_args.args[1] == expected


@pytest.mark.parametrize("old_subset, operator", [
    ('"nature" = \'x\'', "AND"),
    ('"nature" = \'x\'', "OR"),
    ('"nature" = \'x\'', "AND NOT"),
    ('ST_Intersects("geom", ST_GeomFromText(\'POINT(0 0)\', 2154))', "AND"),
    ('"fid" IN (4, 5)', None),
    (None, None),
])
def test_same_combination_on_the_sql_and_the_ogr_paths(qgis, old_subset, operator):
    """The SpatiaLite / GeoPackage SQL path and the OGR path combine identically."""
    ogr = ogr_builder.OGRExpressionBuilder(task_params={})
    ogr_final = ogr._combine_with_old_subset(old_subset, operator, "NEW")
    sql_final = _spatialite_final(old_subset, operator, "NEW")
    assert ogr_final == sql_final


def _spatialite_final(old_subset, operator, expression):
    """What SpatialiteExpressionBuilder.apply_filter queues, read from its source (rule copied verbatim)."""
    import ast
    import textwrap

    source = (PLUGIN_ROOT / "adapters" / "backends" / "spatialite" / "expression_builder.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "apply_filter"
    )
    snippet = ast.get_source_segment(source, method)
    start = snippet.index("            # Combine with existing filter if needed")
    end = snippet.index("            # 2026-04-29 fix: prefer the task's subset queue")
    body = textwrap.dedent(snippet[start:end])
    sql = types.SimpleNamespace(
        _is_geometric_filter=ogr_builder.OGRExpressionBuilder(task_params={})._is_geometric_filter,
        log_info=lambda msg: None,
    )
    scope = {"self": sql, "old_subset": old_subset, "combine_operator": operator, "expression": expression}
    exec(body, {}, scope)  # nosec B102 - test reads the production rule
    return scope["final_expression"]


# ---------------------------------------------------------------------------
# Source geometry as the SQL executor builds it (2026-10-17)
# ---------------------------------------------------------------------------

def test_union_computed_once_per_task_for_all_targets(qgis):
    task_params = {"_parent_task": types.SimpleNamespace()}
    rivers = _rivers()
    for _target_layer in range(3):
        _apply(qgis, "ST_Crosses", task_params=task_params, rivers=rivers)
    assert len(qgis.unions) == 1


def test_caches_do_not_outlive_the_task(qgis):
    stale = {"_ogr_source_union_cache": {"rivers": "old"}, "_ogr_buffered_source_cache": {"k": "v"},
             "_spatialite_source_bbox_cache": {"k": "v"}}
    task_params = dict(stale, _parent_task=types.SimpleNamespace())
    _apply(qgis, "ST_Crosses", task_params=task_params)
    assert not set(stale) & set(task_params), "legacy caches in PROJECT_LAYERS are dropped"
    _apply(qgis, "ST_Crosses", task_params={"_parent_task": types.SimpleNamespace()})
    assert len(qgis.unions) == 2, "a new task computes its own union"


def test_single_feature_source_is_its_own_union(qgis):
    builder = ogr_builder.OGRExpressionBuilder(task_params={})
    rivers = _rivers(1)
    union = builder._source_geometry(rivers)
    assert union is rivers.features[0].geometry()
    assert qgis.unions == []


def test_negative_buffer_applies_to_the_union(qgis):
    # 2026-10-17: like the SQL executor: union first, then the erosion.
    builder = ogr_builder.OGRExpressionBuilder(task_params={"buffer_segments": 8})
    union = builder._source_geometry(_rivers(3), buffer_value=-5.0)
    assert qgis.union_result.buffers == [-5.0]
    assert union.name == "union+buffer-5.0"


def test_mixed_source_keeps_its_highest_dimension(qgis):
    polygon, line = _Geom("poly", POLYGON), _Geom("line", LINE)
    qgis.union_result = _Geom("union", COLLECTION, parts=[line, polygon])
    builder = ogr_builder.OGRExpressionBuilder(task_params={})
    union = builder._source_geometry(_rivers(3))
    assert union.name == "collected:poly"


def test_failed_union_falls_back_with_a_warning(qgis):
    qgis.union_result = None
    builder = ogr_builder.OGRExpressionBuilder(task_params={})
    assert builder._source_geometry(_rivers(3)) is None
    assert any("each source feature is tested on its own" in w for w in builder.warnings)


def test_covers_and_coveredby_codes_are_marked_as_approximations():
    codes = ogr_builder.OGRExpressionBuilder.PREDICATE_CODES
    assert codes["covers"] == codes["contains"]
    assert codes["coveredby"] == codes["within"]
    source = (PLUGIN_ROOT / "adapters" / "backends" / "ogr" / "expression_builder.py").read_text(encoding="utf-8")
    assert "APPROXIMATE" in source


@pytest.mark.parametrize("subset, geometric", [
    ('"st_code" = 3', False),
    ('"name" LIKE \'%contains%\'', False),
    ('"post_status" = \'ok\'', False),
    ('ST_Intersects("geom", X)', True),
    ('Intersects ( "geom", X)', True),
    ('ROWID IN (SELECT id FROM "rtree_t_geom") AND ST_Crosses("geom", X)', True),
])
def test_geometric_filter_detection_uses_function_calls(subset, geometric):
    assert ogr_builder.OGRExpressionBuilder(task_params={})._is_geometric_filter(subset) is geometric


# ---------------------------------------------------------------------------
# Key-list subsets (2026-10-17): QGIS 4.2.3 froze for more than 25 min in
# setSubsetString with "fid" IN (98,687 literals) on a GeoPackage.
# ---------------------------------------------------------------------------

def _gpkg_layer(storage="GPKG"):
    layer = MagicMock()
    layer.dataProvider.return_value.storageType.return_value = storage
    layer.fields.return_value.indexOf.return_value = 0
    return layer


@pytest.mark.parametrize("count, json_form", [(1000, False), (1001, True), (98_687, True)])
def test_large_geopackage_key_list_is_one_json_literal(count, json_form):
    builder = ogr_builder.OGRExpressionBuilder(task_params={})
    clause = builder._build_fid_filter_with_values(_gpkg_layer(), list(range(1, count + 1)), "fid")
    if json_form:
        assert clause.startswith('"fid" IN (SELECT value FROM json_each(\'[1,2,3,')
        assert clause.endswith(f",{count}]'))")
        assert ", " not in clause, "one literal, not a list of SQL tokens"
    else:
        assert clause.startswith('"fid" IN (1, 2, 3')


def test_json_key_list_quotes_text_keys():
    builder = ogr_builder.OGRExpressionBuilder(task_params={})
    clause = builder._json_key_clause('"cleabs"', ["TRON'1", "TRON2"], numeric=False)
    assert clause == '"cleabs" IN (SELECT value FROM json_each(\'["TRON\'\'1","TRON2"]\'))'


@pytest.mark.parametrize("storage, pk_name, expected", [
    ("GPKG", "fid", True),            # GeoPackage FID column: QGIS feature id == value
    ("GPKG", "ogc_fid", False),       # another column named like the asked field
    ("ESRI Shapefile", "fid", False),
])
def test_geopackage_fid_values_are_the_feature_ids(storage, pk_name, expected):
    layer = _gpkg_layer(storage)
    layer.dataProvider.return_value.pkAttributeIndexes.return_value = [0]
    layer.fields.return_value.at.return_value.name.return_value = pk_name
    assert ogr_builder.OGRExpressionBuilder._pk_is_feature_id(layer, "fid") is expected


def test_other_formats_keep_the_plain_list():
    builder = ogr_builder.OGRExpressionBuilder(task_params={})
    clause = builder._build_fid_filter_with_values(_gpkg_layer("ESRI Shapefile"), list(range(2000)), "fid")
    assert clause.startswith('"fid" IN (0, 1, 2')


def _text_key_layer(storage="ESRI Shapefile"):
    """Layer whose key field is a text field (QgsField.isNumeric() False)."""
    layer = _gpkg_layer(storage)
    layer.fields.return_value.__getitem__.return_value.isNumeric.return_value = False
    return layer


def test_text_key_values_are_escaped_literals():
    """2026-10-17: f"'{v}'" let the quote of L'Isle-Jourdain end the literal."""
    builder = ogr_builder.OGRExpressionBuilder(task_params={})
    clause = builder._build_fid_filter_with_values(_text_key_layer(), ["L'Isle-Jourdain", "Auch"], "nom")
    assert clause == "\"nom\" IN ('L''Isle-Jourdain', 'Auch')"


def test_text_key_made_of_digits_stays_quoted():
    """'01001' (INSEE code, text field) was read as the number 1001: the first values decided first."""
    builder = ogr_builder.OGRExpressionBuilder(task_params={})
    clause = builder._build_fid_filter_with_values(_text_key_layer(), ["01001", "31555"], "insee")
    assert clause == "\"insee\" IN ('01001', '31555')"


def _many_roads(count):
    return _Layer("troncon_de_route", [_Feature(fid, _Geom("near")) for fid in range(count)])


@pytest.mark.parametrize("count, applied", [(1500, True), (5000, True), (5001, False)])
def test_plain_key_list_is_bounded_on_other_formats(qgis, count, applied):
    qgis.relations["near"] = {"intersects"}
    queue = MagicMock()
    builder = ogr_builder.OGRExpressionBuilder(task_params={"_subset_queue_callback": queue})
    builder._get_primary_key = lambda layer: "fid"
    builder.source_geom = _rivers(3)
    roads = _many_roads(count)
    assert builder.apply_filter(roads, '{"predicates": ["ST_Intersects"]}') is applied
    if applied:
        queue.assert_called_once()
        assert any("rescans the list" in w for w in builder.warnings)
    else:
        queue.assert_not_called()
        assert "is left unfiltered" in builder.last_error
        # 2026-10-17: the refusal reaches the message bar (user_warnings)
        assert builder.user_warnings == [builder.last_error]


def test_refusal_says_the_previous_filter_is_kept(qgis):
    qgis.relations["near"] = {"intersects"}
    builder = ogr_builder.OGRExpressionBuilder(task_params={"_subset_queue_callback": MagicMock()})
    builder._get_primary_key = lambda layer: "fid"
    builder.source_geom = _rivers(3)
    roads = _many_roads(5001)
    roads.subset = '"nature" = \'x\''
    roads.all_features = roads.features
    assert builder.apply_filter(roads, '{"predicates": ["ST_Intersects"]}', roads.subset, "AND") is False
    assert "keeps its previous filter" in builder.last_error


@pytest.mark.parametrize("provider, storage, bounded", [
    ("ogr", "ESRI Shapefile", True),
    ("ogr", "GeoJSON", True),
    ("ogr", "GPKG", False),
    ("postgres", "PostgreSQL database with PostGIS extension", False),
    ("memory", "Memory storage", True),           # QgsExpression scans the list per feature
    ("WFS", "", False),
])
def test_key_list_bound_only_for_ogr_files(provider, storage, bounded):
    layer = MagicMock()
    layer.providerType.return_value = provider
    layer.dataProvider.return_value.storageType.return_value = storage
    assert ogr_builder.OGRExpressionBuilder._rescans_key_lists(layer) is bounded


@pytest.mark.parametrize("values, numeric, expected", [
    ([1, 2**60 + 1], True, "[1,1152921504606846977]"),        # int64 beyond 2^53 kept exact
    ([3.0, "42", None], True, "[3,42]"),                       # integral float, digit string, None dropped
    ([1.5], True, "[1.5]"),                                  # a non-integral number is not truncated
    (["TRON'1", "Ü"], False, '["TRON\'\'1","Ü"]'),
])
def test_json_key_clause_keeps_the_values(values, numeric, expected):
    clause = ogr_builder.OGRExpressionBuilder(task_params={})._json_key_clause('"k"', values, numeric)
    assert clause == f"\"k\" IN (SELECT value FROM json_each('{expected}'))"

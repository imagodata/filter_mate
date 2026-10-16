# -*- coding: utf-8 -*-
"""Buffer by expression and buffer end caps (2026-10-17).

Story 2 (Muret noise): the buffer ``CASE "importance" 1 -> 300, 2 -> 250``
was replaced by its average (267.5 m) for every road, and the Flat end caps
came out Round: 2,546 buildings instead of 2,753. The distance is now
evaluated on each source feature, the features buffered one by one with the
panel's end cap, then united. Geometries here are measurable fakes: a
segment of length L buffered by d has an area of 2dL (Flat), 2dL + pi d^2
(Round) or 2d(L + 2d) (Square); disjoint parts add up in a union.
"""
import importlib.util
import math
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


def _load(name, path, stubs):
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


_port = types.ModuleType(f"{ROOT}.core.ports.geometric_filter_port")
_port.GeometricFilterPort = _FakePort
_sql_utils = types.ModuleType(f"{ROOT}.infrastructure.database.sql_utils")
_sql_utils.safe_set_subset_string = MagicMock(return_value=True)
ogr_builder = _load(
    f"{ROOT}.adapters.backends.ogr._fm_test_dynamic_buffer_expression_builder",
    PLUGIN_ROOT / "adapters" / "backends" / "ogr" / "expression_builder.py",
    {
        ROOT: _package(ROOT),
        f"{ROOT}.core": _package(f"{ROOT}.core"),
        f"{ROOT}.core.ports": _package(f"{ROOT}.core.ports"),
        f"{ROOT}.core.ports.geometric_filter_port": _port,
        f"{ROOT}.infrastructure": _package(f"{ROOT}.infrastructure"),
        f"{ROOT}.infrastructure.database": _package(f"{ROOT}.infrastructure.database"),
        f"{ROOT}.infrastructure.database.sql_utils": _sql_utils,
        f"{ROOT}.adapters": _package(f"{ROOT}.adapters"),
        f"{ROOT}.adapters.backends": _package(f"{ROOT}.adapters.backends"),
        f"{ROOT}.adapters.backends.ogr": _package(f"{ROOT}.adapters.backends.ogr"),
    },
)

POLYGON, LINE = 3, 2


class _Segment:
    """A straight road of ``length`` metres."""

    def __init__(self, length):
        self.length = length

    def isEmpty(self):
        return False

    def wkbType(self):
        return LINE

    def buffer(self, distance, segments, cap, join, miter):
        if cap == "flat":
            area = 2 * distance * self.length
        elif cap == "square":
            area = 2 * distance * (self.length + 2 * distance)
        else:
            area = 2 * distance * self.length + math.pi * distance ** 2
        return _Area(area, distances=[distance], caps=[cap])


class _Area:
    def __init__(self, area, distances=(), caps=()):
        self.area_value = area
        self.distances = list(distances)
        self.caps = list(caps)

    def area(self):
        return self.area_value

    def isEmpty(self):
        return self.area_value <= 0

    def wkbType(self):
        return POLYGON

    def convertToMultiType(self):
        return True

    def makeValid(self):
        return self


class _Feature:
    def __init__(self, attributes=None, geometry=None):
        self.attributes = dict(attributes or {})
        self._geometry = geometry

    def __getitem__(self, key):
        return self.attributes[key]

    def hasGeometry(self):
        return self._geometry is not None

    def geometry(self):
        return self._geometry

    def setGeometry(self, geometry):
        self._geometry = geometry


class _Layer:
    created = 0

    def __init__(self, uri="", name="", provider="memory", features=None):
        _Layer.created += 1
        self._name = name
        self._id = f"{name}_{_Layer.created}"
        self.features = list(features or [])

    def id(self):
        return self._id

    def name(self):
        return self._name

    def isValid(self):
        return True

    def featureCount(self):
        return len(self.features)

    def getFeatures(self, request=None):
        return iter(self.features)

    def crs(self):
        return "EPSG:2154"

    def setCrs(self, crs):
        pass

    def updateExtents(self):
        pass

    def dataProvider(self):
        return types.SimpleNamespace(addFeatures=lambda features: self.features.extend(features) or True)


class _Expression:
    """``CASE WHEN "importance" = '1' THEN 300 WHEN "importance" = '2' THEN 250 ELSE 100 END``."""

    def __init__(self, text):
        self.text = text

    def hasParserError(self):
        return "CASE" not in self.text

    def parserErrorString(self):
        return "syntax error"

    def prepare(self, context):
        pass

    def evaluate(self, context):
        importance = context.feature["importance"]
        return {"1": 300, "2": 250, None: None}.get(importance, 100)


class _Context:
    feature = None

    def appendScopes(self, scopes):
        pass

    def setFeature(self, feature):
        self.feature = feature


EXPRESSION = "CASE WHEN \"importance\" = '1' THEN 300 WHEN \"importance\" = '2' THEN 250 ELSE 100 END"


@pytest.fixture
def qgis(monkeypatch):
    def _union(geometries):
        return _Area(sum(g.area() for g in geometries),
                     [d for g in geometries for d in g.distances], [c for g in geometries for c in g.caps])

    core = types.SimpleNamespace(
        QgsExpression=_Expression,
        QgsExpressionContext=_Context,
        QgsExpressionContextUtils=types.SimpleNamespace(globalProjectLayerScopes=lambda layer: []),
        QgsFeature=_Feature,
        QgsFeatureRequest=lambda: types.SimpleNamespace(setNoAttributes=lambda: None),
        QgsGeometry=types.SimpleNamespace(unaryUnion=_union),
        QgsVectorLayer=_Layer,
        QgsWkbTypes=types.SimpleNamespace(displayString=lambda t: "MultiPolygon", geometryType=lambda t: t),
        Qgis=types.SimpleNamespace(
            EndCapStyle=types.SimpleNamespace(Round="round", Flat="flat", Square="square"),
            JoinStyle=types.SimpleNamespace(Round="round"),
        ),
    )
    request = MagicMock()
    request.setNoAttributes.return_value = request
    core.QgsFeatureRequest = MagicMock(return_value=request)
    monkeypatch.setitem(sys.modules, "qgis", types.SimpleNamespace(core=core))
    monkeypatch.setitem(sys.modules, "qgis.core", core)
    return core


def _roads():
    # Lengths differ so that an average distance would not give the same area.
    return _Layer(name="roads", features=[
        _Feature({"importance": "1"}, _Segment(1000.0)),
        _Feature({"importance": "2"}, _Segment(3000.0)),
    ])


def _builder(cap="flat"):
    return ogr_builder.OGRExpressionBuilder(task_params={"buffer_segments": 5, "buffer_endcap_style": cap})


def test_each_feature_gets_its_own_distance_then_the_union(qgis):
    union = _builder("flat")._source_geometry(_roads(), buffer_expression=EXPRESSION)
    assert sorted(union.distances) == [250, 300]
    assert union.area() == pytest.approx(2 * 300 * 1000 + 2 * 250 * 3000)
    average = (300 + 250) / 2
    assert union.area() != pytest.approx(2 * average * 4000), "no average distance any more"


@pytest.mark.parametrize("cap, expected", [
    ("flat", 2 * 300 * 1000 + 2 * 250 * 3000),
    ("round", 2 * 300 * 1000 + math.pi * 300 ** 2 + 2 * 250 * 3000 + math.pi * 250 ** 2),
    ("square", 2 * 300 * (1000 + 600) + 2 * 250 * (3000 + 500)),
])
def test_end_cap_of_the_panel_is_applied(qgis, cap, expected):
    union = _builder(cap)._source_geometry(_roads(), buffer_expression=EXPRESSION)
    assert set(union.caps) == {cap}
    assert union.area() == pytest.approx(expected)


def test_flat_is_smaller_than_round(qgis):
    flat = _builder("flat")._source_geometry(_roads(), buffer_expression=EXPRESSION)
    round_ = _builder("round")._source_geometry(_roads(), buffer_expression=EXPRESSION)
    assert flat.area() < round_.area()
    assert round_.area() - flat.area() == pytest.approx(math.pi * (300 ** 2 + 250 ** 2))


def test_feature_without_distance_is_left_out_with_a_warning(qgis):
    roads = _roads()
    roads.features.append(_Feature({"importance": None}, _Segment(5000.0)))
    builder = _builder("flat")
    union = builder._source_geometry(roads, buffer_expression=EXPRESSION)
    assert union.area() == pytest.approx(2 * 300 * 1000 + 2 * 250 * 3000)
    assert any("no distance for 1 source feature" in w for w in builder.warnings)


def test_unparsable_expression_fails_instead_of_guessing(qgis):
    builder = _builder("flat")
    assert builder._apply_buffer_expression_to_layer(_roads(), "300 +") is None
    assert "does not parse" in builder.last_error


def test_no_average_buffer_code_left():
    source = (PLUGIN_ROOT / "adapters" / "backends" / "ogr" / "expression_builder.py").read_text(encoding="utf-8")
    for name in ("_compute_average_buffer", "_fallback_buffer_from_expression", "average buffer", "bufferbym"):
        assert name not in source, name

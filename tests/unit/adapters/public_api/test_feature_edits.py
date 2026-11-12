# -*- coding: utf-8 -*-
"""2026-11-12: an edit refused or failing never leaves the layer in editing mode, nor half of itself in the buffer.

``feature_edits`` put the layer in editing mode before checking the request: an unknown field, a bad WKT or an empty
selection answered 400 with the layer left in editing mode (and a transaction open in a transaction group). An
``addFeatures`` / ``deleteFeatures`` that failed half-way kept what it had done in the buffer while an error was
returned, and a multi-part geometry went into a single-part layer. The buffer of a layer the user was already editing
keeps everything but the failed command.

Loaded inside a private package whose sub-packages point at the repository folders; QGIS is faked.
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_feature_edits_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".core.agent", _ROOT / "core" / "agent"), (".adapters", _ROOT / "adapters"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    operations = types.ModuleType(f"{_PKG}.adapters.public_api.operations")
    operations.busy_reason = lambda: ""
    operations.layer_kind = lambda layer: sys.modules[f"{_PKG}.core.domain.layer_kind"].LayerKind.VECTOR
    operations.resolve_layer = lambda reference: _CURRENT.get(reference)
    sys.modules[operations.__name__] = operations
    importlib.import_module(f"{_PKG}.core.domain.layer_kind")
    return (importlib.import_module(f"{_PKG}.adapters.public_api.feature_edits"),
            importlib.import_module(f"{_PKG}.adapters.public_api.fields_joins"))


_CURRENT = {}
edits, fields_joins = _load()


class _Geometry:
    def __init__(self, wkb="Polygon", parts=1, null=False):
        self.wkb, self.parts, self.null = wkb, parts, null

    def isNull(self):
        return self.null

    def wkbType(self):
        return self.wkb

    def coerceToType(self, wkb):
        if not wkb.startswith("Multi") and self.parts > 1:
            return [_Geometry(wkb) for _ in range(self.parts)]
        return [_Geometry(wkb, 1)]

    @classmethod
    def fromWkt(cls, text):
        if text.startswith("MULTIPOLYGON"):
            return cls("MultiPolygon", parts=text.replace(" ", "").count(")),((") + 1)
        if text.startswith("POLYGON"):
            return cls("Polygon")
        if text.startswith("POINT"):
            return cls("Point")
        return cls(null=True)


class _Feature:
    def __init__(self, fields=None):
        self.geometry, self.attributes = None, {}

    def setGeometry(self, geometry):
        self.geometry = geometry

    def setAttribute(self, index, value):
        self.attributes[index] = value


class _Field:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name

    def convertCompatible(self, value):
        return value


class _Fields:
    def __init__(self, names):
        self.items = [_Field(name) for name in names]

    def __iter__(self):
        return iter(self.items)

    def lookupField(self, name):
        names = [item.name() for item in self.items]
        return names.index(name) if name in names else -1

    def fieldOrigin(self, index):
        return 1

    def at(self, index):
        return self.items[index]


class _Layer:
    """A vector layer with an edit buffer: a command can be destroyed, editing rolled back."""

    def __init__(self, editing=False, buffer=(), add_ok=True, delete_ok=True, wkb="Polygon", selected=()):
        self.editing, self.buffer = editing, list(buffer)
        self.add_ok, self.delete_ok, self.wkb, self.selected = add_ok, delete_ok, wkb, list(selected)
        self.started = self.rolled_back = 0
        self._mark = None
        self.attributes = _Fields(["nom", "class"])
        _CURRENT["routes"] = self

    def name(self):
        return "routes"

    def id(self):
        return "routes"

    def isValid(self):
        return True

    def readOnly(self):
        return False

    def dataProvider(self):
        return SimpleNamespace(capabilities=lambda: 0xFF)

    def isEditable(self):
        return self.editing

    def startEditing(self):
        self.editing, self.started = True, self.started + 1
        return True

    def rollBack(self):
        self.editing, self.buffer, self.rolled_back = False, [], self.rolled_back + 1
        return True

    def beginEditCommand(self, text):
        self._mark = len(self.buffer)

    def destroyEditCommand(self):
        del self.buffer[self._mark:]
        self._mark = None

    def endEditCommand(self):
        self._mark = None

    def isModified(self):
        return bool(self.buffer)

    def fields(self):
        return self.attributes

    def primaryKeyAttributes(self):
        return []

    def crs(self):
        return CRS

    def wkbType(self):
        return self.wkb

    def selectedFeatureCount(self):
        return len(self.selected)

    def selectedFeatureIds(self):
        return list(self.selected)

    def getFeatures(self, request=None):
        return iter([SimpleNamespace(id=lambda fid=fid: fid) for fid in self.selected])

    def addFeatures(self, features):
        self.buffer.append(("add", features[0]))  # the first one goes in, then a failure
        return self.add_ok

    def deleteFeatures(self, ids):
        self.buffer.append(("delete", ids[0]))
        return self.delete_ok

    def addAttribute(self, field):
        self.buffer.append(("field", field))
        return True


CRS = SimpleNamespace(isValid=lambda: True, authid=lambda: "EPSG:2154")


class _Request:
    class Flag:
        NoGeometry = 1

    def setNoAttributes(self):
        return self

    def setFlags(self, flags):
        return self

    def setFilterFids(self, ids):
        return self

    def setFilterExpression(self, expression):
        return self


@pytest.fixture(autouse=True)
def qgis(monkeypatch):
    core = sys.modules["qgis.core"]
    geometry_type = {"Polygon": "polygon", "MultiPolygon": "polygon", "Point": "point"}
    fakes = {
        "QgsVectorDataProvider": SimpleNamespace(Capability=SimpleNamespace(
            AddFeatures=1, DeleteFeatures=2, ChangeAttributeValues=4, AddAttributes=8)),
        "QgsGeometry": _Geometry,
        "QgsFeature": _Feature,
        "QgsFeatureRequest": _Request,
        "QgsExpression": lambda text: SimpleNamespace(hasParserError=lambda: False),
        "QgsCoordinateReferenceSystem": lambda text: CRS,
        "QgsCoordinateTransform": lambda *args: None,
        "QgsProject": SimpleNamespace(instance=lambda: None),
        "QgsWkbTypes": SimpleNamespace(geometryType=lambda wkb: geometry_type.get(wkb, "unknown"),
                                       geometryDisplayString=str, displayString=str,
                                       isMultiType=lambda wkb: wkb.startswith("Multi")),
        "QgsField": lambda name, kind: SimpleNamespace(name=name, setLength=lambda length: None),
        "Qgis": SimpleNamespace(QGIS_VERSION_INT=34400),
    }
    for name, fake in fakes.items():
        monkeypatch.setattr(core, name, fake, raising=False)
    yield
    _CURRENT.clear()


POLYGON = "POLYGON((0 0, 1 0, 1 1, 0 0))"


class TestRefusedBeforeEditing:
    def test_bad_wkt(self):
        layer = _Layer()
        with pytest.raises(ValueError, match="not a WKT geometry"):
            edits.add_features("routes", [{"wkt": "nonsense"}])
        assert layer.started == 0 and not layer.editing

    def test_unknown_field(self):
        layer = _Layer()
        with pytest.raises(ValueError, match="no field 'hauteur'"):
            edits.add_features("routes", [{"wkt": POLYGON, "attributes": {"hauteur": 3}}])
        with pytest.raises(ValueError, match="no field 'hauteur'"):
            edits.update_features("routes", values={"hauteur": 3}, selected_only=True)
        assert layer.started == 0 and not layer.editing

    def test_nothing_selected(self):
        layer = _Layer()
        with pytest.raises(ValueError, match="no feature is selected"):
            edits.delete_features("routes", selected_only=True)
        assert layer.started == 0 and not layer.editing

    def test_multi_part_geometry_in_a_single_part_layer(self):
        layer = _Layer(wkb="Polygon")
        with pytest.raises(ValueError, match="single-part geometries, this one has 2 parts"):
            edits.add_features("routes", [{"wkt": "MULTIPOLYGON(((0 0,1 0,1 1,0 0)),((5 5,6 5,6 6,5 5)))"}])
        assert layer.started == 0 and not layer.editing

    def test_a_field_already_there(self):
        layer = _Layer()
        with pytest.raises(ValueError, match="already has a field 'nom'"):
            fields_joins.add_field("routes", "nom")
        assert layer.started == 0 and not layer.editing


class TestFailureHalfWay:
    def test_add_failure_leaves_the_editing_mode_it_opened(self):
        layer = _Layer(add_ok=False)
        with pytest.raises(ValueError, match="could not be added"):
            edits.add_features("routes", [{"wkt": POLYGON}, {"wkt": POLYGON}])
        assert layer.buffer == [] and not layer.editing and layer.rolled_back == 1

    def test_delete_failure_leaves_the_editing_mode_it_opened(self):
        layer = _Layer(delete_ok=False, selected=[3, 4])
        with pytest.raises(ValueError, match="could not be deleted"):
            edits.delete_features("routes", selected_only=True)
        assert layer.buffer == [] and not layer.editing

    def test_the_users_buffer_is_kept(self):
        layer = _Layer(editing=True, buffer=["the user's change"], add_ok=False)
        with pytest.raises(ValueError):
            edits.add_features("routes", [{"wkt": POLYGON}])
        assert layer.buffer == ["the user's change"] and layer.editing and layer.rolled_back == 0

    def test_a_successful_edit_stays_in_the_buffer(self):
        layer = _Layer(selected=[3])
        answer = edits.delete_features("routes", selected_only=True)
        assert answer["deleted"] == 1 and answer["editing"] and layer.buffer == [("delete", 3)]

    def test_nothing_to_change_does_not_enter_editing_mode(self):
        layer = _Layer()
        layer.getFeatures = lambda request=None: iter([])
        answer = edits.update_features("routes", values={"nom": "x"}, expression='"class" = 1')
        assert answer["changed"] == 0 and answer["editing"] is False and layer.started == 0

    def test_an_update_whose_every_change_fails_leaves_the_editing_mode(self):
        """2026-11-12 (review): every changeAttributeValues refused, the layer stayed in editing mode."""
        layer = _Layer(selected=[3, 4])
        layer.changeAttributeValues = lambda fid, change: False
        with pytest.raises(ValueError, match="could be changed"):
            edits.update_features("routes", values={"nom": "x"}, selected_only=True)
        assert not layer.editing and layer.rolled_back == 1


class TestGeometryType:
    def test_a_single_part_multi_geometry_becomes_single(self):
        layer = _Layer(wkb="Polygon")
        edits.add_features("routes", [{"wkt": "MULTIPOLYGON(((0 0,1 0,1 1,0 0)))"}])
        assert layer.buffer[0][1].geometry.wkbType() == "Polygon"

    def test_a_single_geometry_becomes_multi_in_a_multi_layer(self):
        layer = _Layer(wkb="MultiPolygon")
        edits.add_features("routes", [{"wkt": POLYGON}])
        assert layer.buffer[0][1].geometry.wkbType() == "MultiPolygon"

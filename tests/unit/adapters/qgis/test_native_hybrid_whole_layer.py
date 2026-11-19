# -*- coding: utf-8 -*-
"""The keys of a hybrid subset read on the whole layer (``adapters/qgis/native_filter_translation.py``).

2026-11-18: a second filter that replaced the first one (or was ORed with it) wrote no list of keys, since the
features were read through the first subset, and the former conversion wrote ``bounds_width("geom") > 2`` (refused
by SQLite) where the first filter listed keys. ``_hybrid_subset(whole_layer=True)`` now reads them on a copy of
the layer without its subset, in the context of the layer itself. These tests say which layer is read, in which
context, and when no list is written. QGIS is faked here; the real readings are in
``tests/qgis_headless/check_native_translation.py``.
"""
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "native_filter_translation.py"
_PACKAGE = "fm_native_hybrid_whole_layer_test"
ALL_ATTRIBUTES = "#!allattributes!#"

# QGIS text -> (columns read, functions, variables, value on a feature)
EXPRESSIONS = {
    "big": ({"pop"}, set(), set(), lambda feature: feature["pop"] > 2),
    "all": ({ALL_ATTRIBUTES}, set(), set(), lambda feature: feature["pop"] > 2),
    "virtual": ({"double_pop"}, set(), set(), lambda feature: True),
    "by_id": (set(), {"$id"}, set(), lambda feature: feature["fid"] > 2),
    "geometric": ({"pop"}, set(), set(), lambda feature: feature["pop"] > 2),  # reads the geometry
    "selected": (set(), {"is_selected"}, set(), lambda feature: feature["fid"] > 2),
    "selected_count": (set(), {"num_selected"}, set(), lambda feature: feature["fid"] > 2),
    "by_feature_id": (set(), {"get_feature_by_id", "attribute"}, set(), lambda feature: feature["fid"] > 2),
    "at_id": (set(), {"var"}, {"id"}, lambda feature: feature["fid"] > 2),
    "native_part": ({"pop"}, set(), set(), lambda feature: feature["pop"] >= 0),
    "above_mean": ({"pop"}, {"mean"}, set(), lambda feature: feature["pop"] > 4),
    # a field named like a function reads no function: columns only
    "field_named_like_functions": ({"is_selected", "mean", "eval", "get_feature"}, set(), set(),
                                   lambda feature: feature["pop"] > 2),
    "get_feature": ({"pop"}, {"get_feature", "attribute"}, set(), lambda feature: feature["pop"] > 4),
    "overlay": (set(), {"overlay_intersects"}, set(), lambda feature: feature["pop"] > 4),
    "layer_count": ({"pop"}, {"layer_property"}, set(), lambda feature: feature["pop"] > 4),
    "evaluated": ({"pop"}, {"eval"}, set(), lambda feature: feature["pop"] > 4),
    "feature_id_function": (set(), {"feature_id"}, set(), lambda feature: feature["fid"] > 2),
    "current_feature": (set(), {"$currentfeature", "attribute"}, set(), lambda feature: feature["fid"] > 2),
    "feature_variable": (set(), {"var", "attribute"}, {"feature"}, lambda feature: feature["fid"] > 2),
    "relation_sum": ({"pop"}, {"relation_aggregate", "abs"}, set(), lambda feature: feature["pop"] > 4),
}
# QGIS function -> its groups (QgsExpression.Functions()[i].groups())
GROUPS = {"mean": ["Aggregates"], "relation_aggregate": ["Aggregates"], "abs": ["Math"], "is_selected": ["Record"],
          "num_selected": ["Record"], "get_feature_by_id": ["Record"], "attribute": ["Record"], "var": ["General"],
          "$id": ["Record"], "get_feature": ["Record"], "overlay_intersects": ["GeometryGroup"],
          "layer_property": ["Map Layers"], "eval": ["General"], "feature_id": ["Record"],
          "$currentfeature": ["Record"]}


class _Fields:
    def __init__(self, names):
        self._names = list(names)

    def indexFromName(self, name):
        return self._names.index(name) if name in self._names else -1

    def at(self, index):
        return types.SimpleNamespace(isNumeric=lambda: True)

    def names(self):
        return list(self._names)


class _Layer:
    """A layer of rows {fid, pop}: ``shown`` are the fids its subset keeps."""

    def __init__(self, name, rows, subset="", shown=None, fields=("fid", "pop"), editable=False, wkb=3,
                 primary_key=(0,)):
        self._name, self._rows, self._subset, self._editable, self._wkb = name, rows, subset, editable, wkb
        self._primary_key = primary_key
        self._shown = set(shown) if shown is not None else {row["fid"] for row in rows}
        self._fields = _Fields(fields)
        self.reads = []

    def name(self):
        return self._name

    def subsetString(self):
        return self._subset

    def isEditable(self):
        return self._editable

    def wkbType(self):
        return self._wkb

    def primaryKeyAttributes(self):
        if self._primary_key is RuntimeError:
            raise RuntimeError("no primary key information")
        return list(self._primary_key)

    def fields(self):
        return self._fields

    def dataProvider(self):
        return types.SimpleNamespace(fields=lambda: _Fields([n for n in self._fields.names() if n != "double_pop"]))

    def getFeatures(self, request):
        self.reads.append(request)
        return [dict(row) for row in self._rows if row["fid"] in self._shown]


class _Expression:
    def __init__(self, text):
        self.text = text
        self.columns, self.functions, self.variables, self.value = EXPRESSIONS[text]

    def hasParserError(self):
        return False

    def prepare(self, context):
        return True

    def referencedColumns(self):
        return set(self.columns)

    def referencedFunctions(self):
        return set(self.functions)

    def referencedVariables(self):
        return set(self.variables)

    def needsGeometry(self):
        return self.text == "geometric"

    def evaluate(self, context):
        return self.value(context.feature)

    def hasEvalError(self):
        return False

    @staticmethod
    def functionIndex(name):
        return sorted(GROUPS).index(name) if name in GROUPS else -1

    @staticmethod
    def Functions():
        return [types.SimpleNamespace(groups=lambda groups=GROUPS[name]: groups) for name in sorted(GROUPS)]


class _Context:
    def __init__(self, scopes):
        self.scopes, self.feature = scopes, None

    def setFeature(self, feature):
        self.feature = feature


class _Request:
    ALL_ATTRIBUTES = ALL_ATTRIBUTES
    Flag = types.SimpleNamespace(NoGeometry=1)

    def __init__(self):
        self.attributes, self.fields_of = None, None

    def setFlags(self, flags):
        return self

    def setSubsetOfAttributes(self, names, fields):
        self.attributes, self.fields_of = list(names), fields
        return self


ROWS = [{"fid": fid, "pop": pop} for fid, pop in ((1, 1), (2, 5), (3, 7), (4, 0), (5, 9))]


@pytest.fixture
def translation(monkeypatch):
    package = types.ModuleType(_PACKAGE)
    package.__path__ = []
    probe = types.ModuleType(_PACKAGE + ".source_capability_probe")
    probe.counts = {}
    probe.counted = []
    probe.feature_count_or_none = lambda layer: probe.counted.append(layer.name()) or probe.counts.get(
        layer.name(), len(layer._rows))
    monkeypatch.setitem(sys.modules, _PACKAGE, package)
    monkeypatch.setitem(sys.modules, _PACKAGE + ".source_capability_probe", probe)
    spec = importlib.util.spec_from_file_location(_PACKAGE + ".native_filter_translation", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    core = sys.modules["qgis.core"]
    monkeypatch.setattr(core, "QgsExpression", _Expression, raising=False)
    monkeypatch.setattr(core, "QgsExpressionContext", _Context, raising=False)
    monkeypatch.setattr(core, "QgsExpressionContextUtils", types.SimpleNamespace(
        globalProjectLayerScopes=lambda layer: ("scopes of", layer.name())), raising=False)
    monkeypatch.setattr(core, "QgsFeatureRequest", _Request, raising=False)
    module.dialect = module.SQLITE
    monkeypatch.setattr(module, "native_dialect_for_layer", lambda layer: module.dialect)
    module.copies = []
    module.probe = probe
    return module


def _result():
    return types.SimpleNamespace(predicate=True, native_expression="", native_exact=True, native_columns=frozenset(),
                                 reason="left to QGIS")


def _with_copy(translation, monkeypatch, copy):
    def open_copy(layer):
        translation.copies.append(layer.name())
        return copy
    monkeypatch.setattr(translation, "_unfiltered_copy", open_copy)


def _filtered_layer(**options):
    return _Layer("zones", ROWS, subset='"fid" IN (1, 2)', shown={1, 2}, **options)


def _hybrid(translation, layer, text="big", **options):
    return translation._hybrid_subset(layer, text, _result(), "", "fid", **options)


def test_a_replaced_subset_is_evaluated_on_the_copy_in_the_context_of_the_layer(translation, monkeypatch):
    layer, copy = _filtered_layer(), _Layer("zones (unfiltered)", ROWS)
    _with_copy(translation, monkeypatch, copy)
    contexts = []
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsExpressionContext",
                        lambda scopes: contexts.append(scopes) or _Context(scopes))

    subset = _hybrid(translation, layer, whole_layer=True)

    # fids 3 and 5 are outside the old subset: read anyway, as the first filter read them
    assert subset == '"fid" IS NOT NULL AND "fid" IN (2, 3, 5)'
    assert translation.copies == ["zones"] and layer.reads == [] and len(copy.reads) == 1
    assert contexts == [("scopes of", "zones")]  # the layer's variables, not the copy's
    assert copy.reads[0].fields_of is copy.fields()


def test_and_with_the_same_subset_still_reads_through_the_layer(translation, monkeypatch):
    layer = _filtered_layer()
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    assert _hybrid(translation, layer) == '"fid" IS NOT NULL AND "fid" IN (2)'
    assert translation.copies == [] and len(layer.reads) == 1


def test_a_layer_without_subset_is_read_as_it_is(translation, monkeypatch):
    layer = _Layer("zones", ROWS)
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    assert _hybrid(translation, layer, whole_layer=True) == '"fid" IS NOT NULL AND "fid" IN (2, 3, 5)'
    assert translation.copies == []


def test_no_list_when_the_copy_cannot_be_opened_and_the_layer_is_not_read(translation, monkeypatch):
    layer = _filtered_layer()
    _with_copy(translation, monkeypatch, None)

    with pytest.raises(translation.Unsupported):
        _hybrid(translation, layer, whole_layer=True)
    assert layer.reads == []


def test_an_edited_layer_opens_no_copy(translation, monkeypatch):
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    with pytest.raises(translation.Unsupported):
        _hybrid(translation, _filtered_layer(editable=True), whole_layer=True)
    assert translation.copies == []


def test_without_a_key_the_copy_is_neither_opened_nor_counted(translation, monkeypatch):
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    with pytest.raises(translation.Unsupported):
        translation._hybrid_subset(_filtered_layer(), "big", _result(), "", "no_such_key", whole_layer=True)
    assert translation.copies == [] and translation.probe.counted == []


def test_the_whole_layer_is_counted_against_the_limit(translation, monkeypatch):
    layer, copy = _filtered_layer(), _Layer("zones (unfiltered)", ROWS)
    _with_copy(translation, monkeypatch, copy)
    translation.probe.counts = {"zones": 2, "zones (unfiltered)": translation.HYBRID_MAX_FEATURES + 1}

    with pytest.raises(translation.Unsupported):
        _hybrid(translation, layer, whole_layer=True)
    assert copy.reads == []


@pytest.mark.parametrize("text, fields", [
    ("virtual", ("fid", "pop", "double_pop")),   # a virtual field: not in the copy
    ("all", ("fid", "pop", "double_pop")),       # every attribute, and the layer has one more
])
def test_a_field_the_copy_lacks_gives_no_list(translation, monkeypatch, text, fields):
    layer = _filtered_layer(fields=fields)
    copy = _Layer("zones (unfiltered)", ROWS)
    _with_copy(translation, monkeypatch, copy)

    with pytest.raises(translation.Unsupported):
        _hybrid(translation, layer, text, whole_layer=True)
    assert copy.reads == [] and layer.reads == []
    assert translation.copies == [] and translation.probe.counted == []  # not opened, not counted (review 2)


def test_every_attribute_is_read_on_a_copy_with_the_same_fields(translation, monkeypatch):
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    assert _hybrid(translation, _filtered_layer(), "all", whole_layer=True) == '"fid" IS NOT NULL AND "fid" IN (2, 3, 5)'


def test_a_copy_without_the_geometry_of_the_layer_gives_no_list(translation, monkeypatch):
    copy = _Layer("zones (unfiltered)", ROWS, wkb=100)  # read back without its geometry column
    _with_copy(translation, monkeypatch, copy)

    with pytest.raises(translation.Unsupported):
        _hybrid(translation, _filtered_layer(), "geometric", whole_layer=True)
    assert copy.reads == []
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))
    assert _hybrid(translation, _filtered_layer(), "geometric", whole_layer=True) == (
        '"fid" IS NOT NULL AND "fid" IN (2, 3, 5)')


@pytest.mark.parametrize("text", ["above_mean", "relation_sum"])
def test_an_aggregate_is_never_mixed_with_keys_of_the_whole_layer(translation, monkeypatch, text):
    """QGIS aggregates on the layer of the context, through its subset: no list read on the copy."""
    copy = _Layer("zones (unfiltered)", ROWS)
    _with_copy(translation, monkeypatch, copy)

    with pytest.raises(translation.Unsupported):
        _hybrid(translation, _filtered_layer(), text, whole_layer=True)
    assert translation.copies == []  # refused before the copy is opened
    # through the layer itself (AND with its subset, or no subset), as before
    assert _hybrid(translation, _Layer("zones", ROWS), text, whole_layer=True) == (
        '"fid" IS NOT NULL AND "fid" IN (2, 3, 5)')


FEATURE_ID_READERS = ["by_id", "selected", "selected_count", "by_feature_id", "at_id", "feature_id_function",
                      "current_feature", "feature_variable"]


@pytest.mark.parametrize("text", FEATURE_ID_READERS)
def test_the_feature_id_of_a_postgresql_copy_is_never_read(translation, monkeypatch, text):
    translation.dialect = translation.POSTGRESQL
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    with pytest.raises(translation.Unsupported):
        _hybrid(translation, _filtered_layer(), text, whole_layer=True)
    assert translation.copies == []  # refused before the copy is opened
    # read through the layer itself (AND with its subset), $id is the one its provider gives it
    layer = _Layer("zones", ROWS, subset='"pop" >= 0')
    assert _hybrid(translation, layer, "by_id") == '"fid" IS NOT NULL AND "fid" IN (3, 4, 5)'


@pytest.mark.parametrize("text", FEATURE_ID_READERS)
def test_the_feature_id_of_a_layer_without_a_key_column_is_never_read_on_a_copy(translation, monkeypatch, text):
    """A view without a first integer column: ids 0, 1, 2... that change under a filter (primaryKeyAttributes empty)."""
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    for primary_key in ((), RuntimeError):  # none, or a provider that does not say
        with pytest.raises(translation.Unsupported):
            _hybrid(translation, _filtered_layer(primary_key=primary_key), text, whole_layer=True)
    assert translation.copies == []
    # what does not read the id is read on the copy as before
    assert _hybrid(translation, _filtered_layer(primary_key=()), "big", whole_layer=True) == (
        '"fid" IS NOT NULL AND "fid" IN (2, 3, 5)')


@pytest.mark.parametrize("text", [text for text in FEATURE_ID_READERS if text != "by_feature_id"])
def test_the_feature_id_of_a_geopackage_copy_is_its_fid(translation, monkeypatch, text):
    """The identifier is a column of the table (primaryKeyAttributes): the copy gives the same ids."""
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    assert _hybrid(translation, _filtered_layer(), text, whole_layer=True) == (
        '"fid" IS NOT NULL AND "fid" IN (3, 4, 5)')


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
@pytest.mark.parametrize("text", ["get_feature", "overlay", "layer_count", "evaluated", "by_feature_id"])
def test_a_function_reading_a_layer_is_never_evaluated_on_a_copy(translation, monkeypatch, dialect, text):
    """``get_feature(@layer, ...)``, ``overlay_*``, ``layer_property`` and ``eval`` read the layer through its subset."""
    translation.dialect = dialect
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    with pytest.raises(translation.Unsupported, match="reads a layer|feature id"):
        _hybrid(translation, _filtered_layer(), text, whole_layer=True)
    assert translation.copies == [] and translation.probe.counted == []
    if text != "by_feature_id":  # through the layer itself (AND with its subset), nothing differs from the first filter
        assert _hybrid(translation, _filtered_layer(), text) == '"fid" IS NOT NULL AND "fid" IN (2)'


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
def test_a_field_named_like_a_function_is_no_function(translation, monkeypatch, dialect):
    translation.dialect = dialect
    names = ("fid", "pop", "is_selected", "mean", "eval", "get_feature")
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS, fields=names))

    assert _hybrid(translation, _filtered_layer(fields=names),
                   "field_named_like_functions", whole_layer=True) == '"fid" IS NOT NULL AND "fid" IN (2, 3, 5)'
    assert translation.copies == ["zones"]


def test_under_or_every_key_the_expression_keeps_is_listed(translation, monkeypatch):
    """The list is also the selection the targets are filtered by: never without the keys the old subset keeps."""
    layer = _Layer("zones", ROWS, subset='"fid" IN (2, 3)', shown={2, 3})
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    assert _hybrid(translation, layer, whole_layer=True) == '"fid" IS NOT NULL AND "fid" IN (2, 3, 5)'
    assert layer.reads == []  # the layer itself is not read


def test_the_reading_stops_when_the_task_is_canceled(translation, monkeypatch):
    rows = [{"fid": fid, "pop": fid} for fid in range(1, 11)]
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", rows))
    monkeypatch.setattr(translation, "CANCEL_CHECK_INTERVAL", 3)
    asked = []

    def canceled():
        asked.append(True)
        return len(asked) >= 2  # canceled while the second block is read

    layer = _Layer("zones", rows, subset='"fid" IN (1, 2)', shown={1, 2})
    with pytest.raises(translation.Unsupported, match="canceled after 3 features"):
        _hybrid(translation, layer, whole_layer=True, is_canceled=canceled)
    assert _hybrid(translation, layer, whole_layer=True, is_canceled=lambda: False) == (
        '"fid" IS NOT NULL AND "fid" IN (3, 4, 5, 6, 7, 8, 9, 10)')


def test_a_whole_translation_opens_no_copy(translation, monkeypatch):
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))
    full = types.SimpleNamespace(status=translation.TranslationStatus.FULL, sql='"pop" > 2', composite=False,
                                 geometric=False)
    monkeypatch.setattr(translation, "translate_for_layer", lambda layer, expression, texts_as_like=False: full)
    monkeypatch.setattr(translation, "_survives_sanitizer", lambda layer, sql: True)

    assert translation.subset_for_layer(_filtered_layer(), '"pop" > 2', key_name="fid", evaluate=True,
                                        whole_layer=True) == '"pop" > 2'
    assert translation.copies == []

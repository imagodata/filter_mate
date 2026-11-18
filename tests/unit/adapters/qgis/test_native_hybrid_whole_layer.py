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
}


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

    def __init__(self, name, rows, subset="", shown=None, fields=("fid", "pop"), editable=False, wkb=3):
        self._name, self._rows, self._subset, self._editable, self._wkb = name, rows, subset, editable, wkb
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
    probe.feature_count_or_none = lambda layer: probe.counts.get(layer.name(), len(layer._rows))
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


def test_dollar_id_of_a_postgresql_copy_gives_no_list(translation, monkeypatch):
    translation.dialect = translation.POSTGRESQL
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    with pytest.raises(translation.Unsupported):
        _hybrid(translation, _filtered_layer(), "by_id", whole_layer=True)
    # read through the layer itself (AND with its subset), $id is the one its provider gives it
    layer = _Layer("zones", ROWS, subset='"pop" >= 0')
    assert _hybrid(translation, layer, "by_id") == '"fid" IS NOT NULL AND "fid" IN (3, 4, 5)'


def test_dollar_id_of_a_geopackage_copy_is_its_fid(translation, monkeypatch):
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    assert _hybrid(translation, _filtered_layer(), "by_id", whole_layer=True) == (
        '"fid" IS NOT NULL AND "fid" IN (3, 4, 5)')


def test_under_or_the_keys_the_old_subset_keeps_are_not_listed_again(translation, monkeypatch):
    layer = _Layer("zones", ROWS, subset='"fid" IN (2, 3)', shown={2, 3})
    copy = _Layer("zones (unfiltered)", ROWS)
    _with_copy(translation, monkeypatch, copy)

    assert _hybrid(translation, layer, whole_layer=True, shown_kept=True) == '"fid" IS NOT NULL AND "fid" IN (5)'
    assert len(layer.reads) == 1 and layer.reads[0].attributes == ["fid"]  # the shown keys only


def test_under_or_nothing_new_gives_a_contradiction(translation, monkeypatch):
    layer = _Layer("zones", ROWS, subset='"pop" > 2', shown={2, 3, 5})
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))

    # ( "pop" > 2 ) OR ( "fid" <> "fid" ): the old subset alone
    assert _hybrid(translation, layer, whole_layer=True, shown_kept=True) == '"fid" <> "fid"'


def test_a_whole_translation_opens_no_copy(translation, monkeypatch):
    _with_copy(translation, monkeypatch, _Layer("zones (unfiltered)", ROWS))
    full = types.SimpleNamespace(status=translation.TranslationStatus.FULL, sql='"pop" > 2', composite=False,
                                 geometric=False)
    monkeypatch.setattr(translation, "translate_for_layer", lambda layer, expression, texts_as_like=False: full)
    monkeypatch.setattr(translation, "_survives_sanitizer", lambda layer, sql: True)

    assert translation.subset_for_layer(_filtered_layer(), '"pop" > 2', key_name="fid", evaluate=True,
                                        whole_layer=True) == '"pop" > 2'
    assert translation.copies == []

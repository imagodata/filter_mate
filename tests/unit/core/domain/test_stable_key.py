# -*- coding: utf-8 -*-
"""
Stable key of a layer (2026-10-17).

The Géoplateforme communes (WFS ``ADMINEXPRESS-COG.LATEST:commune``, read
in QGIS 3.44) declare no key and have no ``gml_id`` field: cleabs,
nom_officiel, ..., code_insee (text), population (int). The layer
registration and the OGR backend both took ``population`` ("the first
integer field"): ``"population" IN (...)`` kept every commune sharing a
population with a selected one.

On a local layer a field named like a key is kept only when its values are
proven unique and never NULL; otherwise the QGIS feature id (``$id``, never a
field name: a WFS may expose a real, unreliable ``fid``).

Module tested: core.domain.stable_key, adapters.qgis.source_capability_probe
(key_field_is_unique, stable_key_for_layer), core.tasks.layer_management_task
(search_primary_key_from_layer and the stored-key migration, extracted with ast).
"""
import ast
import importlib.util
import logging
from pathlib import Path

import pytest

from core.domain.stable_key import (
    DECLARED, FEATURE_ID, FEATURE_ID_KEY, NAMED, NONE, choose_key, is_feature_id_key, looks_like_key_name,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
COMMUNE_FIELDS = ['cleabs', 'nom_officiel', 'nom_officiel_en_majuscules', 'statut', 'code_insee', 'population',
                  'date_du_recensement', 'code_postal', 'superficie_cadastrale']
WFS_URI = "typename='ADMINEXPRESS-COG.LATEST:commune' url='https://data.geopf.fr/wfs/ows' version='auto'"


def _unique(*names):
    return lambda name: name in names


class TestChooseKey:
    def test_feature_id_key_is_no_field_name(self):
        assert FEATURE_ID_KEY == '$id'
        assert is_feature_id_key('$id', ['fid']) and is_feature_id_key('fid', ['nom'])
        assert not is_feature_id_key('fid', ['fid', 'nom'])

    def test_declared_key_first(self):
        choice = choose_key(['code', 'id', 'population'], declared=['code'], local=False)
        assert (choice.name, choice.origin) == ('code', DECLARED) and choice.is_field

    def test_local_named_key_needs_proven_unique_values(self):
        choice = choose_key(['NOM', 'ID', 'POPULATION'], is_unique=_unique('ID'))
        assert (choice.name, choice.origin) == ('ID', NAMED)
        assert choose_key(['NOM', 'ID'], is_unique=_unique()).origin == FEATURE_ID      # duplicates / NULL
        assert choose_key(['NOM', 'ID'], is_unique=lambda name: None).origin == FEATURE_ID  # unknown
        assert choose_key(['NOM', 'ID']).origin == FEATURE_ID                           # no checker: no proof

    def test_local_patterns_are_candidates(self):
        choice = choose_key(['nom', 'commune_id', 'population'], is_unique=_unique('commune_id'))
        assert (choice.name, choice.origin) == ('commune_id', NAMED)
        assert choose_key(['nom', 'commune_id'], is_unique=_unique()).origin == FEATURE_ID

    @pytest.mark.parametrize("name, expected", [
        ('id', True), ('ID_COMMUNE', True), ('commune_id', True), ('uuid_bati', True), ('GUID', True),
        ('objectid', True), ('fid', True), ('population', False), ('nom', False), ('identite', False),
    ])
    def test_key_names(self, name, expected):
        assert looks_like_key_name(name) is expected

    def test_never_the_first_integer_field(self):
        assert choose_key(['nom', 'population'], is_unique=_unique('population', 'nom')).origin == FEATURE_ID

    def test_web_service_trusts_known_names_only(self):
        assert choose_key(COMMUNE_FIELDS, local=False).name == 'cleabs'
        assert choose_key(['gml_id', 'population'], local=False).name == 'gml_id'
        for fields in (['fid', 'population'], ['commune_id', 'population'], ['nom', 'population']):
            assert choose_key(fields, local=False).origin == NONE, fields


# ---------------------------------------------------------------------------
# Fake QGIS layers
# ---------------------------------------------------------------------------

class _Field:
    def __init__(self, name, numeric):
        self._name, self._numeric = name, numeric

    def name(self):
        return self._name

    def isNumeric(self):
        return self._numeric

    def typeName(self):
        return 'Integer' if self._numeric else 'String'


class _Fields:
    def __init__(self, fields):
        self._fields = fields

    def __iter__(self):
        return iter(self._fields)

    def __getitem__(self, index):
        return self._fields[index]

    at = __getitem__

    def count(self):
        return len(self._fields)

    def indexFromName(self, name):
        return next((i for i, field in enumerate(self._fields) if field.name() == name), -1)

    indexOf = indexFromName


class _Null:
    """A null QVariant (QGIS 3 / PyQt5 NULL attribute)."""

    def isNull(self):
        return True


class _Layer:
    count = 0

    def __init__(self, provider, source, fields, rows=(), declared=(), subset=''):
        _Layer.count += 1
        self._id = f"layer{_Layer.count}"
        self._provider, self._source, self._subset = provider, source, subset
        self._fields = _Fields([_Field(name, numeric) for name, numeric in fields])
        self._rows = [dict(zip([name for name, _ in fields], row)) for row in rows]
        self._declared = list(declared)
        self.scans = 0

    def id(self):
        return self._id

    def name(self):
        return 'layer'

    def providerType(self):
        return self._provider

    def source(self):
        return self._source

    def subsetString(self):
        return self._subset

    def fields(self):
        return self._fields

    def primaryKeyAttributes(self):
        return self._declared

    def getFeatures(self, request=None):
        self.scans += 1
        return iter(self._rows)

    def featureCount(self):
        raise AssertionError("featureCount() during key detection")


def _probe():
    path = ROOT / "adapters" / "qgis" / "source_capability_probe.py"
    spec = importlib.util.spec_from_file_location("fm_test_stable_key_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROBE = _probe()
COMMUNES = [("L'Isle-Jourdain", '32160', 9000, 1), ('Auch', '32013', 800, 2), ('Ambérieu', '01004', 800, 3)]
COMMUNE_COLUMNS = [('nom', False), ('code', False), ('population', True), ('id', True)]


class TestUniqueness:
    def test_unique_values(self):
        layer = _Layer('ogr', '/data/communes.shp', COMMUNE_COLUMNS, COMMUNES)
        assert PROBE.key_field_is_unique(layer, 'id') is True
        assert PROBE.key_field_is_unique(layer, 'population') is False
        assert PROBE.key_field_is_unique(layer, 'id') is True and layer.scans == 2, "cached"

    def test_null_value_is_no_key(self):
        rows = [('a', '1', 1, 1), ('b', '2', 2, _Null())]
        assert PROBE.key_field_is_unique(_Layer('ogr', '/data/x.shp', COMMUNE_COLUMNS, rows), 'id') is False

    def test_subset_only_proves_duplicates(self):
        layer = _Layer('ogr', '/data/x.shp', COMMUNE_COLUMNS, COMMUNES, subset='"nom" = \'Auch\'')
        assert PROBE.key_field_is_unique(layer, 'id') is None
        assert PROBE.key_field_is_unique(layer, 'population') is False

    def test_web_service_is_never_scanned(self):
        layer = _Layer('WFS', WFS_URI, COMMUNE_COLUMNS, COMMUNES)
        assert PROBE.key_field_is_unique(layer, 'id') is None and layer.scans == 0

    def test_cache_only(self):
        layer = _Layer('ogr', '/data/y.shp', COMMUNE_COLUMNS, COMMUNES)
        assert PROBE.key_field_is_unique(layer, 'id', scan=False) is None and layer.scans == 0

    @pytest.mark.parametrize("provider, source, columns, rows, expected", [
        ('ogr', '/data/communes.shp', COMMUNE_COLUMNS, COMMUNES, ('id', NAMED)),
        ('ogr', '/data/communes.shp', COMMUNE_COLUMNS[:3], COMMUNES, (FEATURE_ID_KEY, FEATURE_ID)),
        ('memory', 'Point?crs=EPSG:2154', [('nom', False), ('population', True)], [('a', 1), ('b', 1)],
         (FEATURE_ID_KEY, FEATURE_ID)),
        ('virtual', '?query=SELECT * FROM mem', [('nom', False), ('population', True)], [], (None, NONE)),
        ('WFS', WFS_URI, [(name, False) for name in COMMUNE_FIELDS], [], ('cleabs', NAMED)),
        ('WFS', WFS_URI, [('fid', True), ('population', True)], [], (None, NONE)),
        ('ogr', '/vsicurl/https://example.org/communes.fgb', [('nom', False)], [], (FEATURE_ID_KEY, FEATURE_ID)),
    ])
    def test_stable_key_for_layer(self, provider, source, columns, rows, expected):
        rows = [row[:len(columns)] for row in rows]
        choice = PROBE.stable_key_for_layer(_Layer(provider, source, columns, rows))
        assert (choice.name, choice.origin) == expected


# ---------------------------------------------------------------------------
# layer_management_task: search_primary_key_from_layer and the stored-key migration
# ---------------------------------------------------------------------------

def _task_class():
    path = ROOT / "core" / "tasks" / "layer_management_task.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "LayersManagementEngineTask")
    wanted = {"search_primary_key_from_layer", "_search_postgresql_key_without_declared_key",
              "_migrate_unreliable_primary_key", "PG_PK_EXACT_NAMES", "PG_UUID_PATTERNS", "PG_ID_PATTERNS"}
    body = [item for item in cls.body
            if (isinstance(item, ast.FunctionDef) and item.name in wanted)
            or (isinstance(item, ast.Assign) and item.targets[0].id in wanted)]
    module = ast.Module(body=[ast.ClassDef(name="Task", bases=[], keywords=[], body=body, decorator_list=[])],
                        type_ignores=[])
    namespace = {"__name__": "core.tasks._fm_test_search_pk", "__package__": "core.tasks",
                 "logger": logging.getLogger("fm.test.search_pk")}
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
    task = namespace["Task"]
    task.isCanceled = lambda self: False
    task._stable_key_choice = staticmethod(PROBE.stable_key_for_layer)
    task._key_field_is_unique = staticmethod(PROBE.key_field_is_unique)
    return task


TASK = _task_class()()


def test_local_layer_without_a_unique_key_is_keyed_by_feature_id():
    """Before: ("population", ...) - the first integer field."""
    layer = _Layer('ogr', '/data/communes.shp', COMMUNE_COLUMNS[:3], [row[:3] for row in COMMUNES])
    assert TASK.search_primary_key_from_layer(layer) == (FEATURE_ID_KEY, -1, 'Integer64', True)


def test_local_layer_with_a_unique_id():
    layer = _Layer('ogr', '/data/communes.shp', COMMUNE_COLUMNS, COMMUNES)
    assert TASK.search_primary_key_from_layer(layer) == ('id', 3, 'Integer', True)


def test_local_id_with_duplicates_is_no_key():
    rows = [('a', '1', 1, 7), ('b', '2', 2, 7)]
    layer = _Layer('ogr', '/data/communes.shp', COMMUNE_COLUMNS, rows)
    assert TASK.search_primary_key_from_layer(layer)[0] == FEATURE_ID_KEY


def test_declared_key_still_wins():
    layer = _Layer('ogr', '/data/x.gpkg|layername=x', [('fid', True), ('population', True)], [(1, 5), (2, 5)],
                   declared=[0])
    assert TASK.search_primary_key_from_layer(layer)[0] == 'fid'


def test_commune_web_service_is_keyed_by_cleabs():
    layer = _Layer('WFS', WFS_URI, [(name, name == 'population') for name in COMMUNE_FIELDS])
    assert TASK.search_primary_key_from_layer(layer) == ('cleabs', 0, 'String', False)


def test_web_service_fid_field_is_not_trusted():
    layer = _Layer('OAPIF', "url='https://example.org/ogcapi' typename='x'", [('fid', True), ('population', True)])
    assert TASK.search_primary_key_from_layer(layer) == (FEATURE_ID_KEY, -1, 'Integer64', True)


@pytest.mark.parametrize("columns, expected", [
    ([('nom', False), ('population', True)], ('ctid', -1, 'tid', False)),
    ([('nom', False), ('commune_id', True)], ('commune_id', 1, 'Integer', True)),     # unchanged PG rules
    ([('code_uuid', False), ('population', True)], ('code_uuid', 0, 'String', False)),
])
def test_postgres_without_declared_key_is_unchanged(columns, expected):
    layer = _Layer('postgres', "dbname='x' table=\"public\".\"v\" (geom)", columns)
    layer.featureCount = lambda: 10
    assert TASK.search_primary_key_from_layer(layer) == expected


@pytest.mark.parametrize("stored, columns, rows, expected", [
    ("population", COMMUNE_COLUMNS[:3], [r[:3] for r in COMMUNES], FEATURE_ID_KEY),   # proven duplicated
    ("population", COMMUNE_COLUMNS, COMMUNES, "id"),                                   # ... a unique id exists
    ("nom", [('nom', False)], [('a',), ('b',)], "nom"),             # unique values: never replaced
    ("virtual_id", [('nom', False)], [('a',)], FEATURE_ID_KEY),     # the field is gone
    ("fid", [('nom', False)], [('a',)], FEATURE_ID_KEY),            # legacy pseudo fid (no field)
])
def test_local_stored_key_replaced_only_when_proven_no_key(stored, columns, rows, expected):
    layer = _Layer('ogr', '/data/communes.shp', columns, rows)
    variables = {"infos": {"primary_key_name": stored}}
    TASK._migrate_unreliable_primary_key(variables, layer)
    assert variables["infos"]["primary_key_name"] == expected


@pytest.mark.parametrize("stored, expected", [
    ("population", "cleabs"),   # not a key name
    ("fid", "cleabs"),          # fid is never trusted on a service
    ("cleabs", "cleabs"),
    ("code_insee", "cleabs"),
])
def test_web_service_stored_key(stored, expected):
    columns = [(name, name == 'population') for name in COMMUNE_FIELDS] + [('fid', True)]
    layer = _Layer('WFS', WFS_URI, columns)
    variables = {"infos": {"primary_key_name": stored}}
    TASK._migrate_unreliable_primary_key(variables, layer)
    assert variables["infos"]["primary_key_name"] == expected


def test_postgres_stored_key_is_kept():
    layer = _Layer('postgres', "dbname='x' table=\"public\".\"t\"", [('nom', False), ('population', True)])
    variables = {"infos": {"primary_key_name": "population"}}
    TASK._migrate_unreliable_primary_key(variables, layer)
    assert variables["infos"]["primary_key_name"] == "population"

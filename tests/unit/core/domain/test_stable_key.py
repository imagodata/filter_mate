# -*- coding: utf-8 -*-
"""
Stable key of a layer (2026-10-17).

The Géoplateforme communes (WFS ``ADMINEXPRESS-COG.LATEST:commune``, read
in QGIS 3.44) declare no key and have no ``gml_id`` field: cleabs,
nom_officiel, ..., code_insee (text), population (int). The layer
registration and the OGR backend both took ``population`` ("the first
integer field"): ``"population" IN (...)`` kept every commune sharing a
population with a selected one.

Module tested: core.domain.stable_key, core.tasks.layer_management_task
(search_primary_key_from_layer, extracted with ast), the OGR backend key.
"""
import ast
import logging
from pathlib import Path

import pytest

from core.domain.stable_key import DECLARED, FEATURE_ID, FEATURE_ID_KEY, NAMED, NONE, choose_key

pytestmark = pytest.mark.unit

COMMUNE_FIELDS = ['cleabs', 'nom_officiel', 'nom_officiel_en_majuscules', 'statut', 'code_insee', 'population',
                  'date_du_recensement', 'code_postal', 'superficie_cadastrale']


class TestChooseKey:
    def test_declared_key_first(self):
        """The provider's key is trusted, whatever its name (and on a web service too)."""
        choice = choose_key(['code', 'id', 'population'], declared=['code'], local=False)
        assert (choice.name, choice.origin) == ('code', DECLARED)
        assert choice.is_field

    def test_known_names_case_insensitive(self):
        choice = choose_key(['NOM', 'ID', 'POPULATION'])
        assert (choice.name, choice.origin) == ('ID', NAMED)

    def test_ign_cleabs_on_the_commune_web_service(self):
        choice = choose_key(COMMUNE_FIELDS, local=False)
        assert (choice.name, choice.origin) == ('cleabs', NAMED)

    def test_gml_id(self):
        assert choose_key(['gml_id', 'nom', 'population'], local=False).name == 'gml_id'

    @pytest.mark.parametrize("fields", [['nom', 'population'], ['population', 'surface_ha'], []])
    def test_local_layer_without_key_uses_the_feature_id(self, fields):
        choice = choose_key(fields, local=True)
        assert (choice.name, choice.origin) == (FEATURE_ID_KEY, FEATURE_ID)
        assert not choice.is_field

    def test_web_service_without_key_has_none(self):
        choice = choose_key(['nom', 'population'], local=False)
        assert (choice.name, choice.origin) == (None, NONE)

    def test_fid_column_is_trusted_on_a_local_layer_only(self):
        assert choose_key(['fid', 'population'], local=True).origin == NAMED
        assert choose_key(['fid', 'population'], local=False).origin == NONE

    def test_never_an_id_like_or_numeric_field(self):
        """commune_id (a foreign key), population: no key."""
        assert choose_key(['commune_id', 'population', 'nom'], local=True).origin == FEATURE_ID


# ---------------------------------------------------------------------------
# layer_management_task.search_primary_key_from_layer
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

    def count(self):
        return len(self._fields)

    def indexFromName(self, name):
        return next((i for i, field in enumerate(self._fields) if field.name() == name), -1)

    indexOf = indexFromName


class _Layer:
    def __init__(self, provider, source, fields, declared=()):
        self._provider, self._source = provider, source
        self._fields = _Fields([_Field(name, numeric) for name, numeric in fields])
        self._declared = list(declared)

    def name(self):
        return 'layer'

    def providerType(self):
        return self._provider

    def source(self):
        return self._source

    def fields(self):
        return self._fields

    def primaryKeyAttributes(self):
        return self._declared

    def featureCount(self):
        raise AssertionError("featureCount() during key detection")


class _Task:
    def isCanceled(self):
        return False


def _search_primary_key_from_layer():
    path = Path(__file__).resolve().parents[4] / "core" / "tasks" / "layer_management_task.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and any(
        isinstance(item, ast.FunctionDef) and item.name == "search_primary_key_from_layer" for item in node.body))
    node = next(item for item in cls.body
                if isinstance(item, ast.FunctionDef) and item.name == "search_primary_key_from_layer")
    namespace = {"__name__": "core.tasks._fm_test_search_pk", "__package__": "core.tasks",
                 "logger": logging.getLogger("fm.test.search_pk")}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["search_primary_key_from_layer"]


WFS_URI = "typename='ADMINEXPRESS-COG.LATEST:commune' url='https://data.geopf.fr/wfs/ows' version='auto'"
SEARCH = _search_primary_key_from_layer()


@pytest.mark.parametrize("provider, source", [
    ("ogr", "/data/communes.shp"),
    ("ogr", "/data/communes.geojson"),
    ("memory", "Polygon?crs=EPSG:2154"),
])
def test_local_layer_without_key_is_keyed_by_feature_id(provider, source):
    """Before: ("population", ...) - the first integer field."""
    layer = _Layer(provider, source, [('nom', False), ('population', True)])
    assert SEARCH(_Task(), layer) == (FEATURE_ID_KEY, -1, 'Integer64', True)


def test_local_layer_with_an_id_field():
    layer = _Layer("ogr", "/data/communes.shp", [('nom', False), ('population', True), ('ID', False)])
    assert SEARCH(_Task(), layer) == ('ID', 2, 'String', False)


def test_declared_key_still_wins():
    layer = _Layer("ogr", "/data/x.gpkg|layername=x", [('fid', True), ('population', True)], declared=[0])
    assert SEARCH(_Task(), layer)[0] == 'fid'


def test_commune_web_service_is_keyed_by_cleabs():
    layer = _Layer("WFS", WFS_URI, [(name, name in ('population', 'superficie_cadastrale')) for name in COMMUNE_FIELDS])
    assert SEARCH(_Task(), layer) == ('cleabs', 0, 'String', False)


def test_web_service_without_key_gets_the_feature_id_pseudo_key():
    """Kept for the picker / exploring (feature ids in the session); the OGR backend refuses key lists."""
    layer = _Layer("OAPIF", "url='https://example.org/ogcapi' typename='x'", [('fid', True), ('population', True)])
    assert SEARCH(_Task(), layer) == (FEATURE_ID_KEY, -1, 'Integer64', True)


def test_postgres_without_key_is_ctid():
    layer = _Layer("postgres", "dbname='x' table=\"public\".\"v\" (geom)", [('nom', False), ('population', True)])
    layer.featureCount = lambda: 10
    assert SEARCH(_Task(), layer) == ('ctid', -1, 'tid', False)

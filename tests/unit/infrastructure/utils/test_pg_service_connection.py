# -*- coding: utf-8 -*-
"""The psycopg2 connection of a layer read through a pg_service.conf service.

2026-11-12: get_datasource_connexion_from_layer read host, port, database and
credentials from the layer's URI and left its ``service`` out. For a layer
``service='fibre' table=...`` libpq then opened its defaults (localhost, the
OS user): no connection (the optimisations of FilterMate skipped, a filter
stopped before the distant layers until #355), or another database.
"""
import importlib
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_PKG = "fmtest_pg_service_pkg"


class FakeUri:
    def __init__(self, service='', host='', database='', username='', password=''):
        self._values = dict(service=service, host=host, port='', database=database,
                            username=username, password=password)

    def __getattr__(self, name):
        values = self.__dict__.get('_values', {})
        if name in values:
            return lambda: values[name]
        raise AttributeError(name)

    def __str__(self):
        return ' '.join(f"{key}='{value}'" for key, value in self._values.items() if value)

    def param(self, key):
        return ''

    def sslMode(self):
        return 'prefer'

    @staticmethod
    def encodeSslMode(mode):
        return mode


def _package(name, path=None):
    module = types.ModuleType(name)
    if path is not None:
        module.__path__ = [str(path)]
    sys.modules[name] = module
    return module


@pytest.fixture
def layer_utils(monkeypatch):
    _package(_PKG, _ROOT)
    _package(f"{_PKG}.infrastructure", _ROOT / "infrastructure")
    _package(f"{_PKG}.infrastructure.utils", _ROOT / "infrastructure" / "utils")
    _package(f"{_PKG}.infrastructure.database", _ROOT / "infrastructure" / "database")
    support = _package(f"{_PKG}.infrastructure.database.postgresql_support")
    support.psycopg2 = None
    name = f"{_PKG}.infrastructure.utils.layer_utils"
    spec = importlib.util.spec_from_file_location(name, _ROOT / "infrastructure" / "utils" / "layer_utils.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    pg_connect = importlib.import_module(f"{_PKG}.infrastructure.database.pg_connect")
    monkeypatch.setattr(module, "QGIS_AVAILABLE", True)
    monkeypatch.setattr(module, "PSYCOPG2_AVAILABLE", True)
    monkeypatch.setattr(module, "psycopg2", object())
    yield module, pg_connect
    for key in [key for key in sys.modules if key == _PKG or key.startswith(f"{_PKG}.")]:
        sys.modules.pop(key, None)


def _layer():
    layer = MagicMock()
    layer.providerType.return_value = "postgres"
    layer.name.return_value = "Zones MRO"
    return layer


def test_the_service_of_the_layer_reaches_psycopg2(layer_utils, monkeypatch):
    module, pg_connect = layer_utils
    seen = []
    monkeypatch.setattr(module, "QgsDataSourceUri", lambda source: FakeUri(service='fibre'))
    monkeypatch.setattr(pg_connect, "pg_connect_with_fallback", lambda kwargs, label='': seen.append(kwargs) or MagicMock())

    connexion, uri = module.get_datasource_connexion_from_layer(_layer())

    assert connexion is not None
    assert seen == [{'service': 'fibre'}]


def test_a_layer_without_service_connects_as_before(layer_utils, monkeypatch):
    module, pg_connect = layer_utils
    seen = []
    monkeypatch.setattr(module, "QgsDataSourceUri",
                        lambda source: FakeUri(host='db', database='gis', username='u', password='p'))
    monkeypatch.setattr(pg_connect, "pg_connect_with_fallback", lambda kwargs, label='': seen.append(kwargs) or MagicMock())

    module.get_datasource_connexion_from_layer(_layer())

    assert seen == [{'host': 'db', 'dbname': 'gis', 'user': 'u', 'password': 'p'}]

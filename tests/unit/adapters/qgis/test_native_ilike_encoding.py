# -*- coding: utf-8 -*-
"""The encoding of a PostgreSQL database decides how an ILIKE is written (``adapters/qgis/native_filter_translation.py``).

2026-11-13: ``ILIKE`` is written ``SIMILAR TO`` with the long s and the Kelvin sign in the classes of ``s`` and
``k``. A LATIN1 database has neither character and refused the pattern, so every ILIKE holding s or k failed
(measured on PostgreSQL 16: fm_latin1). The encoding is read once per connection.
"""
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "native_filter_translation.py"


@pytest.fixture
def translation():
    spec = importlib.util.spec_from_file_location("fm_native_ilike_encoding_test", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _layer(info="host=db dbname=gis"):
    uri = types.SimpleNamespace(connectionInfo=lambda expand=True: info, uri=lambda expand=True: info + " table=t")
    return types.SimpleNamespace(dataProvider=lambda: types.SimpleNamespace(uri=lambda: uri))


def _server(monkeypatch, answer, asked):
    def create(uri, configuration):
        asked.append(uri)
        if isinstance(answer, Exception):
            raise answer
        return types.SimpleNamespace(executeSql=lambda sql: [[answer]])
    registry = types.SimpleNamespace(providerMetadata=lambda name: types.SimpleNamespace(createConnection=create))
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProviderRegistry",
                        types.SimpleNamespace(instance=lambda: registry), raising=False)


@pytest.mark.parametrize("encoding, expected", [
    ("UTF8", True), ("utf8", True), ("LATIN1", False), ("WIN1252", False), ("LATIN9", False),
    ("SQL_ASCII", None), ("EUC_JP", None), ("", None),
])
def test_the_other_cases_follow_the_server_encoding(translation, monkeypatch, encoding, expected):
    _server(monkeypatch, encoding, [])
    assert translation.ilike_other_cases(_layer(), translation.POSTGRESQL) is expected


def test_the_encoding_is_asked_once_per_connection(translation, monkeypatch):
    asked = []
    _server(monkeypatch, "LATIN1", asked)
    assert translation.server_encoding(_layer()) == "LATIN1" and translation.server_encoding(_layer()) == "LATIN1"
    assert len(asked) == 1
    assert translation.server_encoding(_layer("host=other dbname=gis")) == "LATIN1" and len(asked) == 2


def test_a_connection_that_fails_leaves_the_encoding_unknown_and_is_asked_again(translation, monkeypatch):
    asked = []
    _server(monkeypatch, RuntimeError("no route to host"), asked)
    assert translation.ilike_other_cases(_layer(), translation.POSTGRESQL) is None
    _server(monkeypatch, "UTF8", asked)
    assert translation.ilike_other_cases(_layer(), translation.POSTGRESQL) is True and len(asked) == 2


def test_other_dialects_do_not_ask(translation, monkeypatch):
    asked = []
    _server(monkeypatch, "LATIN1", asked)
    assert translation.ilike_other_cases(_layer(), translation.SQLITE) is True and asked == []

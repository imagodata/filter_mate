# -*- coding: utf-8 -*-
"""The URI of the copy of a layer without its subset (``adapters/backends/source_refusal.unfiltered_copy``).

2026-11-18 (review): QGIS 3.22 drops ``checkPrimaryKeyUnicity`` when it reads a PostgreSQL URI back (3.44 keeps
it, measured): on a view whose layer says ``checkPrimaryKeyUnicity='0'``, each copy counted the distinct keys of the
whole view again. The copy gets it back from the layer's URI. QGIS is faked: the URI is a list of ``key=value``.
"""
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "backends" / "source_refusal.py"
SOURCE = "dbname='db' key='id' checkPrimaryKeyUnicity='0' table=\"public\".\"v\" (geom) sql=\"pop\" > 2"


class _Uri:
    """QgsDataSourceUri reduced to its parameters (``name='value'`` words)."""

    def __init__(self, uri):
        self.text = uri

    def hasParam(self, name):
        return f" {name}=" in f" {self.text}"

    def param(self, name):
        return self.text.split(f"{name}='", 1)[1].split("'", 1)[0]

    def setParam(self, name, value):
        self.text = f"{self.text} {name}='{value}'"

    def uri(self, expand=True):
        return self.text


class _Layer:
    def __init__(self, uri, name='v', provider='postgres', options=None):
        self._uri, self._name, self._provider = uri, name, provider

    def providerType(self):
        return self._provider

    def source(self):
        return self._uri

    def name(self):
        return self._name

    def isValid(self):
        return True

    def subsetString(self):
        return ''


@pytest.fixture
def refusal(monkeypatch):
    spec = importlib.util.spec_from_file_location("fm_unfiltered_copy_uri_test", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    core = sys.modules["qgis.core"]
    monkeypatch.setattr(core, "QgsDataSourceUri", _Uri, raising=False)
    layer_class = type("QgsVectorLayer", (_Layer,), {"LayerOptions": lambda *args: types.SimpleNamespace()})
    monkeypatch.setattr(core, "QgsVectorLayer", layer_class, raising=False)
    return module


def _registry(monkeypatch, encoded):
    registry = types.SimpleNamespace(decodeUri=lambda provider, uri: {"table": "v", "subset": '"pop" > 2'},
                                     encodeUri=lambda provider, parts: encoded)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProviderRegistry",
                        types.SimpleNamespace(instance=lambda: registry), raising=False)


def test_qgis_3_22_drops_the_key_check_and_the_copy_gets_it_back(refusal, monkeypatch):
    _registry(monkeypatch, "dbname='db' key='id' table=\"public\".\"v\" (geom)")  # as QGIS 3.22 writes it back

    copy = refusal.unfiltered_copy(_Layer(SOURCE))

    assert "checkPrimaryKeyUnicity='0'" in copy.source() and "sql=" not in copy.source()


def test_a_key_check_kept_by_qgis_is_not_written_twice(refusal, monkeypatch):
    _registry(monkeypatch, "dbname='db' key='id' checkPrimaryKeyUnicity='0' table=\"public\".\"v\" (geom)")

    assert refusal.unfiltered_copy(_Layer(SOURCE)).source().count("checkPrimaryKeyUnicity") == 1


def test_a_layer_without_key_check_gets_none(refusal, monkeypatch):
    _registry(monkeypatch, "dbname='db' key='id' table=\"public\".\"v\" (geom)")

    copy = refusal.unfiltered_copy(_Layer("dbname='db' key='id' table=\"public\".\"v\" (geom) sql=\"pop\" > 2"))

    assert "checkPrimaryKeyUnicity" not in copy.source()

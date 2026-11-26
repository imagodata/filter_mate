# -*- coding: utf-8 -*-
"""same_service (adapters/qgis/stream_copy.py): a copy fits its layer only while the layer still reads the service
it was planned on (audit of 2026-11-24: the copy of a former service of the same kind was applied).

The module loads for real under a synthetic package; qgis.core only gives QgsTask (the class StreamCopyTask
inherits) and QgsDataSourceUri (a stand-in parsing url=), the rest stays mocked by the root conftest.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_stream_copy_service_test"


class _Uri:
    """QgsDataSourceUri stand-in: the url= parameter of a source."""

    def __init__(self, source):
        self._params = {}
        for part in str(source or "").split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                self._params[key.strip().lower()] = value

    def param(self, name):
        return self._params.get(name.lower(), "")


class _Task:
    Flag = types.SimpleNamespace(CanCancel=1)


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".adapters", _ROOT / "adapters"), (".adapters.qgis", _ROOT / "adapters" / "qgis")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    core = sys.modules["qgis.core"]
    saved_task = getattr(core, "QgsTask", None)
    core.QgsTask = _Task
    try:
        return importlib.import_module(f"{_PKG}.adapters.qgis.stream_copy")
    finally:
        if saved_task is None:
            delattr(core, "QgsTask")
        else:
            core.QgsTask = saved_task


stream_copy = _load()


@pytest.fixture(autouse=True)
def data_source_uri(monkeypatch):
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsDataSourceUri", _Uri, raising=False)

WFS_A = "url=https://data.example.org/wfs&typename=communes"
WFS_B = "url=https://other.example.org/wfs&typename=communes"


def test_the_same_service_still_fits():
    assert stream_copy.same_service(WFS_A, "wfs", WFS_A, "wfs")
    # A filter set meanwhile is not in the endpoint: the copy still fits.
    assert stream_copy.same_service(WFS_A + "&filter=pop>1", "WFS", WFS_A, "wfs")


def test_another_service_of_the_same_kind_does_not():
    assert not stream_copy.same_service(WFS_B, "wfs", WFS_A, "wfs")


def test_another_kind_does_not():
    assert not stream_copy.same_service(WFS_A, "oapif", WFS_A, "wfs")


def test_without_an_endpoint_the_provider_decides():
    assert stream_copy.same_service("https://tiles.example.org/{z}/{x}/{y}.png", "xyz",
                                    "https://tiles.example.org/{z}/{x}/{y}.png", "xyz")
    assert not stream_copy.same_service("https://tiles.example.org/{z}/{x}/{y}.png", "xyz",
                                        "https://tiles.example.org/{z}/{x}/{y}.png", "wms")

# -*- coding: utf-8 -*-
"""same_service (adapters/qgis/stream_copy.py): a copy fits its layer only while the layer still reads the service
it was planned on (audit of 2026-11-24: the copy of a former service of the same kind was applied).

The module loads for real under a synthetic package; qgis.core only gives QgsTask (the class StreamCopyTask
inherits) and QgsDataSourceUri (a stand-in parsing url=), the rest stays mocked by the root conftest.
"""
import importlib
import os
import pathlib
import sys
import time
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


class _PruneLayer:
    """A layer reading ``source``; ``customProperty`` explodes when the record is unreadable (2026-11-26)."""

    def __init__(self, layer_id, source, record=None, explode=None):
        self._id, self._source, self._record, self._explode = layer_id, source, record, explode

    def id(self):
        return self._id

    def source(self):
        return self._source

    def customProperty(self, key):
        if self._explode is not None:
            raise self._explode
        return self._record


class _PruneProject:
    def __init__(self, path, layers):
        self._path, self._layers = path, layers

    def absoluteFilePath(self):
        return self._path

    def fileName(self):
        return self._path

    def mapLayers(self):
        return dict(self._layers)


def _prune_setup(monkeypatch, tmp_path, name):
    profile = tmp_path / "profile"
    profile.mkdir()
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsApplication",
                        type("App", (), {"qgisSettingsDirPath": staticmethod(lambda: str(profile))}),
                        raising=False)
    project_file = tmp_path / f"{name}.qgz"
    project_file.touch()
    folder = stream_copy.rules.project_folder(str(project_file))
    os.makedirs(folder, exist_ok=True)
    return str(project_file), folder


def _aged(path):
    old = time.time() - 3600
    os.utime(path, (old, old))


def test_prune_keeps_the_copy_of_an_unreadable_layer(monkeypatch, tmp_path):
    """Fail closed (2026-11-26): record_of raising must not leave an in-use copy unreferenced for the prune."""
    project_file, folder = _prune_setup(monkeypatch, tmp_path, "kept")
    copy = os.path.join(folder, "communes_20240101.gpkg")
    pathlib.Path(copy).touch()
    _aged(copy)
    layer = _PruneLayer("a", copy, explode=ValueError("unreadable"))
    assert stream_copy.prune_copies(_PruneProject(project_file, {"a": layer})) == 0
    assert os.path.isfile(copy)


def test_prune_still_deletes_what_nothing_reads(monkeypatch, tmp_path):
    project_file, folder = _prune_setup(monkeypatch, tmp_path, "gone")
    copy = os.path.join(folder, "communes_20240101.gpkg")
    pathlib.Path(copy).touch()
    _aged(copy)
    layer = _PruneLayer("a", WFS_A, record=None)
    assert stream_copy.prune_copies(_PruneProject(project_file, {"a": layer})) == 1
    assert not os.path.exists(copy)

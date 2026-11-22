# -*- coding: utf-8 -*-
"""
2026-11-20: the layers of the project are read on the main thread for the worker of a task.

``capture_layer_facts`` reads the provider, the source, the id and the name of every layer of the project (and
of the layers a task is given) where it is called; ``detect_layer_provider_type`` and ``capability_for_layer``
then answer in a worker without calling the layer (QGIS 4.3 reports ``providerType()`` called from another
thread than the one the layer lives in).

Modules tested: infrastructure.utils.layer_facts, infrastructure.utils.layer_utils,
adapters.qgis.source_capability_probe
"""
import importlib.util
import sys
import threading
import types
from pathlib import Path

import pytest

from filtermate_core.domain import layer_facts as core_facts

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
_UTILS_DIR = ROOT / "infrastructure" / "utils"
_PKG = "fmtest_layer_facts_pkg"


def _load(name):
    """``infrastructure/utils/<name>.py`` in a package of its own (its relative imports of the plugin fall back)."""
    full = f"{_PKG}.{name}"
    if full in sys.modules:
        return sys.modules[full]
    if _PKG not in sys.modules:
        package = types.ModuleType(_PKG)
        package.__path__ = [str(_UTILS_DIR)]
        package.__package__ = _PKG
        sys.modules[_PKG] = package
    spec = importlib.util.spec_from_file_location(full, _UTILS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


def _probe():
    path = ROOT / "adapters" / "qgis" / "source_capability_probe.py"
    spec = importlib.util.spec_from_file_location("fm_test_layer_facts_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Layer:
    """A layer that notes the thread of each read."""

    def __init__(self, layer_id, provider="ogr", source="/data/bdtopo.gpkg|layername=commune"):
        self.values = {"providerType": provider, "source": source, "id": layer_id, "name": layer_id.upper()}
        self.deleted = False
        self.reads = []

    def _read(self, what):
        self.reads.append((what, threading.current_thread() is threading.main_thread()))
        if self.deleted:
            raise RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted")
        return self.values[what]

    def providerType(self):
        return self._read("providerType")

    def source(self):
        return self._read("source")

    def id(self):
        return self._read("id")

    def name(self):
        return self._read("name")

    def read_off_the_main_thread(self):
        return [what for what, on_main in self.reads if not on_main]


def in_worker(function):
    outcome = {}

    def run():
        try:
            outcome["result"] = function()
        except BaseException as error:  # noqa: B902 - handed back to the test
            outcome["error"] = error

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()
    if "error" in outcome:
        raise outcome["error"]
    return outcome["result"]


@pytest.fixture
def facts(monkeypatch):
    module = _load("layer_facts")
    monkeypatch.setattr(module, "is_sip_deleted", lambda layer: layer.deleted)
    yield module
    with core_facts._LOCK:
        core_facts._SNAPSHOTS[:] = []


def _project(monkeypatch, layers):
    project = types.SimpleNamespace(mapLayers=lambda: {layer.values["id"]: layer for layer in layers})
    monkeypatch.setitem(sys.modules, "qgis.core",
                        types.SimpleNamespace(QgsProject=types.SimpleNamespace(instance=lambda: project)))


def test_the_project_and_the_layers_given_are_read_where_the_task_is_created(facts, monkeypatch):
    zones, pts, added = Layer("zones"), Layer("pts", "postgres", "dbname='gis' table=\"public\".\"pts\""), Layer("new")
    _project(monkeypatch, [zones, pts])
    snapshot = facts.capture_layer_facts([added, "an_id_of_a_removed_layer"])
    assert len(snapshot) == 3
    for layer in (zones, pts, added):
        assert layer.reads == [("providerType", True), ("source", True), ("id", True), ("name", True)]
    assert in_worker(lambda: [core_facts.provider_key_of(layer) for layer in (zones, pts, added)]) == [
        "ogr", "postgres", "ogr"]
    assert in_worker(lambda: (core_facts.id_of(pts), core_facts.name_of(pts))) == ("pts", "PTS")
    assert zones.read_off_the_main_thread() == pts.read_off_the_main_thread() == added.read_off_the_main_thread() == []


def test_a_task_starts_without_a_project(facts, monkeypatch):
    def no_project():
        raise RuntimeError("no project")

    monkeypatch.setitem(sys.modules, "qgis.core",
                        types.SimpleNamespace(QgsProject=types.SimpleNamespace(instance=no_project)))
    assert facts.capture_layer_facts() is None
    facts.release_layer_facts(None)  # finished() of such a task


def test_a_layer_removed_under_the_task_raises_as_before(facts, monkeypatch):
    pts = Layer("pts")
    _project(monkeypatch, [pts])
    snapshot = facts.capture_layer_facts()
    assert in_worker(lambda: core_facts.provider_key_of(pts)) == "ogr"
    pts.deleted = True  # what sip tells once QGIS deleted the layer
    with pytest.raises(RuntimeError):
        in_worker(lambda: core_facts.provider_key_of(pts))
    assert snapshot is not None


def test_released_in_finished_the_layers_answer_for_themselves(facts, monkeypatch):
    pts = Layer("pts")
    _project(monkeypatch, [pts])
    facts.release_layer_facts(facts.capture_layer_facts())
    assert in_worker(lambda: core_facts.facts_of(pts)) is None


@pytest.mark.parametrize("provider, source, expected", [
    ("ogr", "/data/bdtopo.gpkg|layername=commune", "spatialite"),
    ("ogr", "/data/communes.shp", "ogr"),
    ("ogr", "/vsicurl/https://example.org/communes.gpkg|layername=commune", "ogr"),
    ("postgres", "dbname='gis' table=\"public\".\"commune\" (geom)", "postgresql"),
    ("WFS", "url='https://example.org/wfs' typename='commune'", "ogr"),
    ("memory", "Polygon?crs=EPSG:2154", "memory"),
])
def test_the_backend_of_a_layer_is_told_in_a_worker_without_calling_it(facts, monkeypatch, provider, source,
                                                                         expected):
    layer_utils = _load("layer_utils")
    monkeypatch.setattr(layer_utils, "QGIS_AVAILABLE", True)
    monkeypatch.setattr(layer_utils, "QgsVectorLayer", Layer)
    layer = Layer("commune", provider, source)
    on_main = layer_utils.detect_layer_provider_type(layer)
    _project(monkeypatch, [layer])
    snapshot = facts.capture_layer_facts()
    assert in_worker(lambda: layer_utils.detect_layer_provider_type(layer)) == on_main == expected
    assert layer.read_off_the_main_thread() == []
    assert snapshot is not None


def test_the_capability_of_a_layer_is_told_in_a_worker_without_calling_it(facts, monkeypatch):
    probe = _probe()
    layer = Layer("commune", "WFS", "url='https://example.org/wfs' typename='commune'")
    _project(monkeypatch, [layer])
    snapshot = facts.capture_layer_facts()
    capability = in_worker(lambda: probe.capability_for_layer(layer))
    assert capability.is_remote_service
    assert in_worker(lambda: probe.is_remote_layer(layer)) is True
    assert layer.read_off_the_main_thread() == []
    assert probe.capability_for_layer(layer) is capability  # the main thread reads the layer: same classification
    assert snapshot is not None

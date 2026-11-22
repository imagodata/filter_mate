# -*- coding: utf-8 -*-
"""
What the worker of a task knows of a layer without reading it (2026-11-20).

QGIS 4.3 reports each accessor of a layer called from another thread than
the one it lives in; the bench of the lifecycle failed on ``providerType``.
The provider key, the source, the id and the name are read on the main thread
when a task is created, and the worker gets that reading: the layer is not
called from it.

Module tested: filtermate_core.domain.layer_facts, and its readers
(core.domain.source_capability.classify_layer, the Spatialite builder).
"""
import gc
import threading

import pytest

from core.domain.source_capability import Locality, classify_layer
from filtermate_core.domain import layer_facts
from filtermate_core.domain.layer_facts import capture, facts_of, id_of, name_of, provider_key_of, source_of
from filtermate_core.sql.spatialite.expression_builder import gpkg_layer_location

pytestmark = pytest.mark.unit

GPKG = "/data/bdtopo.gpkg|layername=commune"


class Layer:
    """A layer that notes which thread reads it."""

    def __init__(self, provider="ogr", source=GPKG, layer_id="commune_1", name="commune"):
        self.values = {"providerType": provider, "source": source, "id": layer_id, "name": name}
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
    """The result of ``function`` run in another thread (its exception is raised here)."""
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


def everything(layer):
    return provider_key_of(layer), source_of(layer), id_of(layer), name_of(layer)


@pytest.fixture(autouse=True)
def no_snapshot_left():
    yield
    gc.collect()
    with layer_facts._LOCK:
        layer_facts._SNAPSHOTS[:] = []


def test_the_worker_gets_what_the_main_thread_read_and_does_not_call_the_layer():
    layer = Layer()
    snapshot = capture([layer])
    assert len(snapshot) == 1
    assert in_worker(lambda: everything(layer)) == ("ogr", GPKG, "commune_1", "commune")
    assert layer.read_off_the_main_thread() == []


def test_the_main_thread_always_reads_the_layer():
    layer = Layer()
    snapshot = capture([layer])
    layer.values["providerType"] = "postgres"  # repointed since: the main thread sees it
    layer.reads.clear()
    assert facts_of(layer) is None
    assert provider_key_of(layer) == "postgres"
    assert layer.reads == [("providerType", True)]
    assert in_worker(lambda: provider_key_of(layer)) == "ogr"  # the task keeps what it was created with
    assert snapshot is not None


def test_a_layer_the_worker_made_is_read_where_it_lives():
    """A memory copy made in the worker was captured by nobody: it answers for itself, in its thread."""
    known = Layer()
    snapshot = capture([known])

    def work():
        own = Layer(provider="memory", source="Polygon?crs=EPSG:2154", layer_id="copy_1", name="copy")
        return everything(own), own.reads

    values, reads = in_worker(work)
    assert values == ("memory", "Polygon?crs=EPSG:2154", "copy_1", "copy")
    assert [what for what, _ in reads] == ["providerType", "source", "id", "name"]
    assert len(snapshot) == 1


def test_a_deleted_layer_answers_for_itself():
    """A layer removed under a running task raises as before (the callers handle RuntimeError)."""
    layer = Layer()
    snapshot = capture([layer], is_deleted=lambda candidate: candidate.deleted)
    assert in_worker(lambda: provider_key_of(layer)) == "ogr"
    layer.deleted = True
    with pytest.raises(RuntimeError):
        in_worker(lambda: provider_key_of(layer))
    assert in_worker(lambda: classify_layer(layer)).provider_key == ""  # as for a deleted layer before
    assert snapshot is not None


def test_a_released_snapshot_gives_the_layers_back():
    layer = Layer()
    snapshot = capture([layer])
    snapshot.release()
    assert in_worker(lambda: provider_key_of(layer)) == "ogr"
    assert layer.read_off_the_main_thread() == ["providerType"]
    with layer_facts._LOCK:
        assert layer_facts._SNAPSHOTS == []


def test_the_facts_die_with_the_task_that_holds_them():
    """A task that never ran never releases: nothing stays behind it."""
    layer = Layer()
    snapshot = capture([layer])
    del snapshot
    gc.collect()
    assert in_worker(lambda: facts_of(layer)) is None
    capture([])  # the dead references leave at the next capture
    with layer_facts._LOCK:
        assert len(layer_facts._SNAPSHOTS) == 1


def test_the_latest_reading_wins():
    layer = Layer()
    first = capture([layer])
    layer.values["source"] = "/data/other.gpkg|layername=commune"
    second = capture([layer])
    assert in_worker(lambda: source_of(layer)) == "/data/other.gpkg|layername=commune"
    second.release()
    assert in_worker(lambda: source_of(layer)) == GPKG
    first.release()


def test_two_tasks_one_released_the_other_still_answers():
    layer = Layer()
    first, second = capture([layer]), capture([layer])
    first.release()
    assert in_worker(lambda: provider_key_of(layer)) == "ogr"
    assert layer.read_off_the_main_thread() == []
    second.release()


def test_what_is_not_a_layer_or_is_deleted_is_left_out():
    deleted = Layer()
    deleted.deleted = True
    snapshot = capture(["commune_1", None, object(), deleted, Layer()])
    assert len(snapshot) == 1


def test_another_object_never_gets_the_facts_of_a_layer():
    layer, twin = Layer(), Layer(provider="postgres")
    snapshot = capture([layer])
    assert in_worker(lambda: provider_key_of(twin)) == "postgres"
    assert twin.read_off_the_main_thread() == ["providerType"]
    assert snapshot.facts(twin) is None


def test_classify_layer_in_a_worker_does_not_call_the_layer():
    layer = Layer(provider="WFS", source="url='https://example.org/wfs' typename='x'")
    snapshot = capture([layer])
    capability = in_worker(lambda: classify_layer(layer))
    assert capability.locality is Locality.REMOTE_SERVICE
    assert layer.read_off_the_main_thread() == []
    assert classify_layer(layer).locality is Locality.REMOTE_SERVICE  # and still works on the main thread
    assert snapshot is not None


def test_the_spatialite_builder_locates_a_geopackage_without_calling_the_layer():
    layer = Layer()
    snapshot = capture([layer])
    assert in_worker(lambda: gpkg_layer_location(layer)) == ("/data/bdtopo.gpkg", "commune")
    assert layer.read_off_the_main_thread() == []
    assert snapshot is not None

# -*- coding: utf-8 -*-
"""The memory of the agent in its file (adapters/agent/memory_store.py): read, written in one move, never overwritten
when it cannot be read; and the signature of a layer notes are kept under.

The module is loaded for real under a synthetic package (its relative imports reach ``core``); QGIS stays mocked by the
root conftest.
"""
import importlib
import json
import os
import pathlib
import sys
import tempfile
import types
from types import SimpleNamespace

import pytest

from core.agent.memory import ADD, EDIT, REMOVE, SCOPE_SOURCE, SCOPE_USER

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_agent_memory_store_test"


def _load():
    package = types.ModuleType(_PKG)
    package.__path__ = [str(_ROOT)]
    sys.modules[_PKG] = package
    return importlib.import_module(f"{_PKG}.adapters.agent.memory_store")


store = _load()
# The classes as this copy of the module knows them: another package, other classes than ``core.agent.memory``.
Memory, UnreadableMemory = store.Memory, store.UnreadableMemory


def test_no_file_is_an_empty_memory(tmp_path):
    assert store.read_memory(tmp_path / "agent_memory.json").notes == ()
    assert not (tmp_path / "agent_memory.json").exists()  # reading writes nothing


def test_unchanged_shared_memory_is_parsed_once_but_another_session_invalidates_it(tmp_path, monkeypatch):
    path = tmp_path / "agent_memory.json"
    path.write_text('{"notes": [{"text": "first fact"}]}', encoding="utf-8")
    parses = []
    original = store.parse

    def count(text):
        parses.append(text)
        return original(text)

    monkeypatch.setattr(store, "parse", count)
    first = store.read_memory(path)
    assert store.read_memory(path) is first and len(parses) == 1
    # A different session replaces the file atomically. It may preserve its size and modification time.
    previous = path.stat()
    replacement = tmp_path / "from_other_session.json"
    replacement.write_text('{"notes": [{"text": "other fact"}]}', encoding="utf-8")
    os.utime(replacement, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    os.replace(replacement, path)
    second = store.read_memory(path)
    assert second.notes[0].text == "other fact" and len(parses) == 2
    assert store.read_memory(path) is second
    # Deletion and a broken manual edit must never revive the cached facts.
    path.unlink()
    assert store.read_memory(path) == Memory()
    path.write_text("broken JSON", encoding="utf-8")
    with pytest.raises(UnreadableMemory):
        store.read_memory(path)


def test_an_in_place_edit_with_unchanged_mtime_invalidates_shared_memory(tmp_path):
    path = tmp_path / "agent_memory.json"
    path.write_text('{"notes": [{"text": "first fact"}]}', encoding="utf-8")
    store.read_memory(path)
    before = path.stat()
    path.write_text('{"notes": [{"text": "other fact"}]}', encoding="utf-8")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert store.read_memory(path).notes[0].text == "other fact"


def test_a_cached_read_never_loses_another_sessions_notes_on_write(tmp_path):
    path = tmp_path / "agent_memory.json"
    store.change_memory([(ADD, SCOPE_USER, "", "", "first")], path)
    store.read_memory(path)
    other = tmp_path / "other.json"
    other.write_text('{"notes": [{"id": "m1", "text": "first"}, {"id": "m2", "text": "other session"}]}',
                     encoding="utf-8")
    os.replace(other, path)
    kept = store.change_memory([(ADD, SCOPE_USER, "", "", "third")], path)
    assert [note.text for note in kept.notes] == ["first", "other session", "third"]


def test_shared_memory_cache_is_bounded_and_separates_profiles(tmp_path, monkeypatch):
    from collections import OrderedDict
    monkeypatch.setattr(store, "_read_cache", OrderedDict())
    monkeypatch.setattr(store, "MAX_CACHED_FILES", 2)
    for rank in range(3):
        path = tmp_path / f"profile{rank}.json"
        path.write_text(json.dumps({"notes": [{"text": f"profile {rank}"}]}), encoding="utf-8")
        assert store.read_memory(path).notes[0].text == f"profile {rank}"
    assert len(store._read_cache) == 2


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO is POSIX only")
def test_a_memory_pipe_is_refused_without_waiting(tmp_path):
    path = tmp_path / "agent_memory.json"
    os.mkfifo(path)
    with pytest.raises(UnreadableMemory, match="regular file"):
        store.read_memory(path)


def test_a_change_is_written_and_read_back(tmp_path):
    path = tmp_path / "FilterMate" / "agent_memory.json"  # the folder is made with the first note
    memory = store.change_memory([(ADD, SCOPE_USER, "", "", "MRO = zone de mutualisation"),
                                  (ADD, SCOPE_SOURCE, "ogr::troncons", "Tronçons", "aérien = type_infra 'AER'")],
                                 path, today="2026-11-22")
    assert [note.id for note in memory.notes] == ["m1", "m2"]
    assert store.read_memory(path).notes == memory.notes
    held = json.loads(path.read_text(encoding="utf-8"))
    assert held["notes"][1] == {"id": "m2", "scope": "source", "signature": "ogr::troncons", "label": "Tronçons",
                                "text": "aérien = type_infra 'AER'", "updated": "2026-11-22"}
    assert [entry.name for entry in path.parent.iterdir()] == ["agent_memory.json"]  # no temporary file left


def test_a_change_is_made_on_what_another_qgis_wrote_meanwhile(tmp_path):
    path = tmp_path / "agent_memory.json"
    store.change_memory([(ADD, SCOPE_USER, "", "", "a")], path)
    store.change_memory([(ADD, SCOPE_USER, "", "", "from the other QGIS")], path)  # after this one read the file
    after = store.change_memory([(EDIT, "m1", "a, corrected"), (ADD, SCOPE_USER, "", "", "b")], path)
    assert [(note.id, note.text) for note in after.notes] == [("m1", "a, corrected"), ("m2", "from the other QGIS"),
                                                              ("m3", "b")]
    store.change_memory([(REMOVE, "m2")], path)
    assert [note.id for note in store.change_memory([(REMOVE, "m2")], path).notes] == ["m1", "m3"]  # gone already


def test_nothing_to_change_writes_nothing(tmp_path):
    path = tmp_path / "agent_memory.json"
    assert store.change_memory([], path) == Memory() and not path.exists()
    store.change_memory([(ADD, SCOPE_USER, "", "", "a")], path)
    written = path.stat().st_mtime_ns
    store.change_memory([(ADD, SCOPE_USER, "", "", "A")], path)  # the same note: kept once
    assert path.stat().st_mtime_ns == written


@pytest.mark.parametrize("held", ["{ not json", '{"version": 9, "notes": []}',
                                  '{"notes": [{"id": "m1", "text": "' + "a" * 301 + '"}]}'])
def test_a_file_that_cannot_be_read_is_left_as_it_is(tmp_path, held):
    path = tmp_path / "agent_memory.json"
    path.write_text(held, encoding="utf-8")
    with pytest.raises(UnreadableMemory):
        store.read_memory(path)
    with pytest.raises(UnreadableMemory):
        store.change_memory([(ADD, SCOPE_USER, "", "", "a")], path)
    assert path.read_text(encoding="utf-8") == held
    assert [entry.name for entry in tmp_path.iterdir()] == ["agent_memory.json"]


def test_a_change_refused_writes_nothing(tmp_path):
    path = tmp_path / "agent_memory.json"
    store.change_memory([(ADD, SCOPE_USER, "", "", "a")], path)
    before = path.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        store.change_memory([(ADD, SCOPE_USER, "", "", "b"), (ADD, SCOPE_USER, "", "", "x" * 301)], path)
    assert path.read_text(encoding="utf-8") == before and len(list(tmp_path.iterdir())) == 1


def test_another_qgis_writing_makes_this_one_wait_then_say_so(tmp_path, monkeypatch):
    path = tmp_path / "agent_memory.json"
    lock = tmp_path / "agent_memory.json.lock"
    lock.write_text("", encoding="utf-8")  # held by another QGIS
    monkeypatch.setattr(store, "LOCK_WAIT_SECONDS", 0.15)
    with pytest.raises(OSError, match="another QGIS"):
        store.change_memory([(ADD, SCOPE_USER, "", "", "a")], path)
    assert not path.exists() and lock.exists()  # nothing written, and its lock is left to it
    old = lock.stat().st_mtime - store.LOCK_STALE_SECONDS - 5
    os.utime(lock, (old, old))  # a QGIS that died while it wrote
    assert len(store.change_memory([(ADD, SCOPE_USER, "", "", "a")], path).notes) == 1
    assert [entry.name for entry in tmp_path.iterdir()] == ["agent_memory.json"]  # the lock is given back


def test_a_write_keeps_the_link_and_the_permissions_of_the_file(tmp_path):
    real = tmp_path / "synced" / "agent_memory.json"
    real.parent.mkdir()
    real.write_text("", encoding="utf-8")
    real.chmod(0o640)
    link = tmp_path / "profile" / "agent_memory.json"
    link.parent.mkdir()
    try:
        link.symlink_to(real)
    except OSError:
        pytest.skip("no symbolic link on this system")
    store.change_memory([(ADD, SCOPE_USER, "", "", "a")], link)
    assert link.is_symlink() and len(store.read_memory(real).notes) == 1
    if os.name == "posix":
        assert real.stat().st_mode & 0o777 == 0o640
    assert [entry.name for entry in link.parent.iterdir()] == ["agent_memory.json"]


def test_a_write_sweeps_what_one_cut_short_left(tmp_path):
    path = tmp_path / "agent_memory.json"
    left, recent = tmp_path / ".agent_memory.abc.tmp", tmp_path / ".agent_memory.new.tmp"
    for entry in (left, recent):
        entry.write_text("{", encoding="utf-8")
    old = left.stat().st_mtime - store.LOCK_STALE_SECONDS - 5
    os.utime(left, (old, old))
    store.change_memory([(ADD, SCOPE_USER, "", "", "a")], path)
    assert not left.exists() and recent.exists()  # the recent one may be another QGIS writing now


def test_a_file_saved_by_a_windows_editor_is_read(tmp_path):
    path = tmp_path / "agent_memory.json"
    path.write_bytes(b"\xef\xbb\xbf" + '{"notes": [{"text": "réponds en mètres"}]}'.encode("utf-8"))
    assert store.read_memory(path).notes[0].text == "réponds en mètres"
    path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(UnreadableMemory):
        store.read_memory(path)
    path.write_bytes(b" " * (store.MAX_FILE_BYTES + 1))
    with pytest.raises(UnreadableMemory, match="1 MB"):
        store.read_memory(path)


def test_the_file_is_next_to_the_skills_of_the_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "user_folder", lambda: tmp_path / "FilterMate" / "skills")
    assert store.memory_path() == tmp_path / "FilterMate" / "agent_memory.json"
    monkeypatch.setattr(store, "user_folder", lambda: None)
    assert store.memory_path() is None and store.read_memory() == Memory()
    with pytest.raises(OSError):
        store.change_memory([(ADD, SCOPE_USER, "", "", "a")])


# --- the signature of a layer -------------------------------------------------------------------------------------------

def _layer(provider, source, name="Tronçons", layer_id="l1"):
    return SimpleNamespace(providerType=lambda: provider, source=lambda: source, name=lambda: name, id=lambda: layer_id)


def test_the_signature_of_a_layer_is_that_of_the_favorites():
    assert store.source_signature(_layer("ogr", "/data/reseau.gpkg|layername=troncons")) == "ogr::troncons"
    assert store.source_signature(_layer("ogr", "/data/communes.shp")) == "ogr::communes"
    # the letter of a Windows drive is no server (its file name is read by Windows only: not played here)
    assert not store._connection_string("C:\\data\\communes.shp") and not store._connection_string("data/c.shp")
    assert store._connection_string("PG:dbname=gis") and store._connection_string("MySQL:gisdb,tables=parcels")


@pytest.mark.parametrize("provider, source", [
    ("ogr", "MySQL:gisdb,host=db,user=bob,password=s3cret,tables=parcels"),
    ("ogr", "PG:dbname=gis host=db user=bob password=s3cret"),
    ("ogr", "ODBC:bob/s3cret@dsn"),
    ("ogr", "https://bob:s3cret@example.org/data/parcels.geojson"),
    ("ogr", "/vsicurl/https://example.org/api/parcels.geojson?token=abc.def"),
    ("ogr", "/data/parcels.geojson?token=abc"),
])
def test_a_source_that_may_hold_a_password_or_a_token_has_no_signature(provider, source):
    """Nothing of a connection string or an address is ever written to the file (review, 2026-11-22)."""
    assert store.source_signature(_layer(provider, source)) == ""


def test_a_provider_told_by_the_name_of_its_layer_has_no_signature_yet():
    """Renamed, the layer would lose its notes; two layers of one name would share them."""
    for provider, source in (("wfs", "url='https://example.org/wfs' typename='ns:roads'"), ("gdal", "/data/mnt.tif"),
                             ("wms", "url=https://example.org/wms&layers=a"), ("pdal", "/data/dalle.copc.laz"),
                             ("delimitedtext", "file:///data/points.csv?delimiter=;")):
        assert store.source_signature(_layer(provider, source, "Roads")) == "", provider


def test_a_layer_whose_source_is_not_told_again_has_none():
    assert store.source_signature(_layer("memory", "Point?crs=EPSG:2154")) == ""
    assert store.source_signature(_layer("virtual", "?query=select 1")) == ""
    assert store.source_signature(_layer("virtualraster", "?crs=...")) == ""
    scratch = str(pathlib.Path(tempfile.gettempdir()) / "processing_abc" / "OUTPUT.gpkg")
    assert store.source_signature(_layer("ogr", scratch + "|layername=OUTPUT")) == ""
    deeper = str(pathlib.Path(tempfile.gettempdir()) / "processing_abc" / "x1" / "OUTPUT.shp")
    assert store.source_signature(_layer("ogr", deeper)) == ""
    # a file the user keeps in the temporary folder is theirs: only the outputs of Processing are left out
    mine = str(pathlib.Path(tempfile.gettempdir()) / "work" / "reseau.gpkg")
    assert store.source_signature(_layer("ogr", mine + "|layername=troncons")) == "ogr::troncons"
    assert store.source_signature(_layer("ogr", str(pathlib.Path(tempfile.gettempdir()) / "communes.shp"))) \
        == "ogr::communes"
    derived = {"l1": object()}
    assert store.source_signature(_layer("ogr", "/data/communes.shp"), derived) == ""
    assert store.source_signature(_layer("ogr", "/data/communes.shp", layer_id="l2"), derived) == "ogr::communes"
    assert store.source_signature(_layer("ogr", "/data/" + "n" * 400 + ".shp")) == ""  # longer than a signature

    def gone():
        raise RuntimeError("wrapped C/C++ object has been deleted")
    assert store.source_signature(SimpleNamespace(providerType=gone)) == ""


def test_the_temporary_folder_qgis_names_for_processing_is_left_out(monkeypatch, tmp_path):
    folder = tmp_path / "qgis_outputs"  # set by the user in the options of Processing: not named processing_...
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProcessingUtils",
                        SimpleNamespace(tempFolder=lambda: str(folder)), raising=False)
    monkeypatch.setattr(store, "_processing_folder", None)  # read once in a session
    assert store.source_signature(_layer("ogr", str(folder / "OUTPUT.gpkg") + "|layername=OUTPUT")) == ""
    assert store.source_signature(_layer("ogr", str(tmp_path / "data" / "communes.shp"))) == "ogr::communes"


def test_the_sources_of_a_project_in_the_order_asked():
    layers = {"a": _layer("ogr", "/data/communes.shp", "Communes", "a"),
              "b": _layer("memory", "Point", "scratch", "b"),
              "c": _layer("ogr", "/data/reseau.gpkg|layername=troncons", "Tronçons", "c")}
    project = SimpleNamespace(mapLayers=lambda: layers, mapLayer=lambda layer_id: layers.get(layer_id))
    sources, active = store.project_sources(["c", "gone", "b", "a"], "c", project=project)
    assert sources == [("ogr::troncons", "Tronçons"), ("", "scratch"), ("ogr::communes", "Communes")]
    assert active == "ogr::troncons"
    sources, active = store.project_sources(project=project)  # every layer, by name
    assert [name for _signature, name in sources] == ["Communes", "scratch", "Tronçons"] and active == ""

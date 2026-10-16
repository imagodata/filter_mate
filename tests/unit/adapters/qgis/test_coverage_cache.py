# -*- coding: utf-8 -*-
"""FilterMate 5 cache of derived files: session lock, fallback folder, garbage collection, size limit."""
import importlib
import os
import pathlib
import socket
import sys
import time
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_coverage_cache_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".core.services", _ROOT / "core" / "services"), (".adapters", _ROOT / "adapters"),
                       (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    cache_module = importlib.import_module(f"{_PKG}.adapters.qgis.coverage_layers.cache")
    service_module = importlib.import_module(f"{_PKG}.core.services.cross_filter_service")
    state_module = importlib.import_module(f"{_PKG}.core.domain.filter_state")
    return cache_module, service_module, state_module


cache, service_mod, state = _load()

needs_flock = pytest.mark.skipif(os.name == 'nt', reason="the test holds a second lock from the same process")

OLD = 10 * 86400  # older than every age rule


@pytest.fixture
def root(tmp_path):
    folder = tmp_path / "cache"
    cache.set_cache_root(str(folder))
    yield folder
    cache.set_cache_root(None)


def _age(path, seconds):
    stamp = time.time() - seconds
    os.utime(path, (stamp, stamp))


def _session(root, name, host=None, age=0.0):
    """A session folder; ``host`` writes a lock file naming it (None: no lock file)."""
    folder = root / name
    folder.mkdir(parents=True)
    if host is not None:
        (folder / cache.LOCK_NAME).write_text(f"{host}\n1\n")
    if age:
        _age(folder, age)
    return folder


def _files(folder, *names, age=0.0):
    for name in names:
        path = os.path.join(folder, name)
        with open(path, "w") as handle:
            handle.write("x" * 10)
        if age:
            _age(path, age)


class TestSessionLock:

    @needs_flock
    def test_current_session_is_locked_and_names_its_host(self, root):
        folder = cache.session_dir()
        assert cache.session_state(folder) == (True, '')
        with open(os.path.join(folder, cache.LOCK_NAME)) as handle:
            assert handle.readline().strip() == socket.gethostname()

    @needs_flock
    def test_live_session_of_another_instance_is_kept(self, root):
        other = _session(root, "session_other", host=socket.gethostname(), age=OLD)
        handle = open(other / cache.LOCK_NAME, 'a+')
        try:
            assert cache._try_lock(handle)
            cache.session_dir()  # cleans the root on creation
            assert other.exists()
        finally:
            cache._unlock(handle)
            handle.close()

    def test_dead_sessions_of_this_computer_go_after_a_minute(self, root):
        dead = _session(root, "session_dead", host=socket.gethostname(), age=120)
        starting = _session(root, "session_new", host=socket.gethostname())
        cache.session_dir()
        assert not dead.exists()
        assert starting.exists()  # unlocked for less than a minute: may be starting

    def test_unknown_liveness_waits_a_day(self, root):
        other_host = _session(root, "session_remote", host="another-computer", age=3600)
        old = _session(root, "session_old", host="another-computer", age=2 * 86400)
        unrelated = root / "not_a_session"
        unrelated.mkdir(parents=True)
        cache.cleanup_stale_sessions()
        assert other_host.exists() and unrelated.exists()
        assert not old.exists()

    def test_folders_without_the_filtermate_lock_file_are_never_removed(self, root):
        # cache_dir set on a folder shared with other data: a "session_*"
        # folder FilterMate did not create stays, whatever its age.
        foreign = _session(root, "session_2019")
        _files(foreign, "survey.csv")
        _age(foreign, OLD)
        cache.cleanup_stale_sessions()
        assert (foreign / "survey.csv").exists()

    def test_lock_retried_while_another_instance_probes(self, root, monkeypatch):
        answers = iter([False, False, True])
        monkeypatch.setattr(cache, "_try_lock", lambda handle: next(answers, True))
        monkeypatch.setattr(cache.time, "sleep", lambda seconds: None)
        folder = cache.session_dir()
        with open(os.path.join(folder, cache.LOCK_NAME)) as handle:
            assert handle.readline().strip() == socket.gethostname()

    def test_file_system_without_locks_is_not_held(self, root, monkeypatch):
        folder = _session(root, "session_nfs", host=socket.gethostname(), age=3600)
        monkeypatch.setattr(cache, "_try_lock", lambda handle: None)
        assert cache.session_state(str(folder)) == (None, '')
        cache.cleanup_stale_sessions()
        assert folder.exists()  # 24 h rule, not "locked for ever" nor "dead"

    def test_purge_removes_the_session_and_closes_the_cache(self, root):
        folder = cache.session_dir()
        cache.purge_session()
        assert not os.path.exists(folder) and cache.is_closed()
        with pytest.raises(RuntimeError):
            cache.new_path("dtm", ".vrt")
        cache.set_cache_root(str(root))
        assert not cache.is_closed() and os.path.isdir(cache.session_dir())


class TestFallback:

    def test_unwritable_root_falls_back_to_a_user_temp_folder(self, tmp_path, monkeypatch):
        blocker = tmp_path / "file"
        blocker.write_text("not a folder")
        monkeypatch.setattr(cache.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
        cache.set_cache_root(str(blocker / "cache"))
        try:
            path = cache.new_path("dtm", ".vrt")
            assert path.startswith(os.path.join(os.path.dirname(cache.temp_root()), ""))
            assert os.path.isdir(os.path.dirname(path))
        finally:
            cache.set_cache_root(None)

    @staticmethod
    def _fallback_path(tmp_path, monkeypatch, prepare):
        """Cache path with an unwritable root, once ``prepare(user temp folder)`` ran."""
        blocker = tmp_path / "file"
        blocker.write_text("not a folder")
        (tmp_path / "tmp").mkdir()
        monkeypatch.setattr(cache.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
        prepare(os.path.dirname(cache.temp_root()))
        cache.set_cache_root(str(blocker / "cache"))
        try:
            return cache.new_path("dtm", ".vrt")
        finally:
            cache.set_cache_root(None)

    @pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX owners")
    def test_user_temp_folder_owned_by_someone_else_is_not_used(self, tmp_path, monkeypatch):
        user_folder = []

        def other_owner(folder):
            os.makedirs(folder)
            user_folder.append(folder)
            uid = os.getuid()
            monkeypatch.setattr(cache.os, "getuid", lambda: uid + 1)

        path = self._fallback_path(tmp_path, monkeypatch, other_owner)
        assert not path.startswith(os.path.join(user_folder[0], ""))
        assert os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(path)))).startswith("filtermate-")
        assert os.stat(os.path.dirname(os.path.dirname(os.path.dirname(path)))).st_mode & 0o077 == 0

    @pytest.mark.skipif(os.name == "nt", reason="symbolic links need privileges")
    def test_user_temp_folder_that_is_a_link_is_not_followed(self, tmp_path, monkeypatch):
        target = tmp_path / "elsewhere"
        target.mkdir()
        path = self._fallback_path(tmp_path, monkeypatch, lambda folder: os.symlink(str(target), folder))
        assert not os.listdir(target)
        assert not path.startswith(os.path.join(os.path.dirname(cache.temp_root()), ""))

    @pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX modes")
    def test_own_user_temp_folder_is_made_private(self, tmp_path, monkeypatch):
        def loose(folder):
            os.makedirs(folder)
            os.chmod(folder, 0o777)

        path = self._fallback_path(tmp_path, monkeypatch, loose)
        user_folder = os.path.dirname(cache.temp_root())
        assert path.startswith(os.path.join(user_folder, ""))
        assert os.stat(user_folder).st_mode & 0o777 == 0o700


class TestGarbageCollection:

    def test_unreferenced_files_go_side_files_stay(self, root):
        folder = cache.session_dir()
        _files(folder, "dtm_1a2b3c4d.vrt", "dtm_1a2b3c4d.vrt.aux.xml",
               "cloud_5e6f7a8b.laz", "cloud_5e6f7a8b.copc.laz", "old_9c0d1e2f.copc.laz")
        os.mkdir(os.path.join(folder, "cloud_5e6f7a8b_tmp"))  # indexing folder named after the file
        referenced = [os.path.join(folder, "dtm_1a2b3c4d.vrt"),
                      os.path.join(folder, "cloud_5e6f7a8b.laz") + "|option",
                      "/elsewhere/ortho.tif"]
        assert cache.collect_garbage(referenced) == 1
        assert sorted(os.listdir(folder)) == sorted([
            cache.LOCK_NAME, "dtm_1a2b3c4d.vrt", "dtm_1a2b3c4d.vrt.aux.xml",
            "cloud_5e6f7a8b.laz", "cloud_5e6f7a8b.copc.laz", "cloud_5e6f7a8b_tmp"])

    def test_paths_embedded_in_a_virtual_raster_uri_are_kept(self, root):
        folder = cache.session_dir()
        _files(folder, "mnt_0a1b2c3d.vrt", "mnt_4e5f6a7b.vrt")
        uri = ("?crs=EPSG:2154&formula=%22mnt@1%22&mnt:uri="
               + os.path.join(folder, "mnt_0a1b2c3d.vrt").replace("/", "%2F") + "&mnt:provider=gdal")
        assert cache.collect_garbage([uri]) == 1
        assert os.path.exists(os.path.join(folder, "mnt_0a1b2c3d.vrt"))

    def test_file_names_are_ascii(self, root):
        path = cache.new_path("MNT Élévation ²", ".vrt")
        assert os.path.basename(path).isascii()

    def test_files_being_written_are_kept_until_settled(self, root):
        path = cache.new_path("cloud", ".copc.laz")
        _files(os.path.dirname(path), os.path.basename(path))
        assert cache.collect_garbage([]) == 0
        cache.settle([path])
        assert cache.collect_garbage([]) == 1

    def test_no_session_nothing_to_do(self, root):
        assert cache.collect_garbage([]) == 0

    def test_default_limit_is_five_gb(self, root):
        assert cache.max_bytes() == 5 * 1024 ** 3


def _snapshot(layer_id, source):
    return state.LayerSnapshot(layer_id, "raster", source=source, provider="gdal", derived=True,
                               original_source="/data/dtm.tif", original_provider="gdal")


class TestTidyCache:

    @pytest.fixture
    def tidy(self, root, monkeypatch):
        folder = cache.session_dir()
        layers = {}
        monkeypatch.setattr(service_mod, "filtermate_tasks_active", lambda: False)
        monkeypatch.setattr(service_mod, "current_sources", lambda project=None: set(layers.values()))
        monkeypatch.setattr(service_mod, "_SERVICES", type(service_mod._SERVICES)())
        return folder, layers

    @staticmethod
    def _derived(folder, name, size):
        path = os.path.join(folder, name)
        with open(path, "wb") as handle:
            handle.write(b"x" * size)
        return path

    @staticmethod
    def _step(service, source_id, before, after, layer_id="r1"):
        service.history.push(state.CrossOperation(source_id, ((_snapshot(layer_id, before), _snapshot(layer_id, after)),)))

    def test_waits_while_a_task_runs(self, tidy, monkeypatch):
        monkeypatch.setattr(service_mod, "filtermate_tasks_active", lambda: True)
        assert service_mod.tidy_cache() is None

    def test_oldest_undo_steps_go_until_under_the_limit(self, tidy, monkeypatch):
        folder, layers = tidy
        service = service_mod.CrossFilterService()
        paths = [self._derived(folder, f"dtm_0000000{i}.vrt", 100) for i in range(4)]
        for i in range(1, 4):
            self._step(service, "v1", paths[i - 1], paths[i])
        layers["r1"] = paths[3]  # current filter
        monkeypatch.setattr(cache, "max_bytes", lambda: 250.0)
        report = service_mod.tidy_cache()
        assert len(report["dropped"]) == 2 and report["size"] <= 250
        assert all(service is s and step.from_undo for s, step in report["dropped"])
        assert sorted(os.path.basename(p) for p in paths if os.path.exists(p)) == ["dtm_00000002.vrt", "dtm_00000003.vrt"]
        assert service.history.can_undo("v1")

    def test_steps_that_free_nothing_are_kept(self, tidy, monkeypatch):
        folder, layers = tidy
        service = service_mod.CrossFilterService()
        layers["r1"] = self._derived(folder, "dtm_aaaaaaaa.vrt", 400)
        for _ in range(3):  # subset-only steps of another layer: no derived file
            self._step(service, "v1", "/data/parcels.gpkg", "/data/parcels.gpkg", layer_id="p1")
        monkeypatch.setattr(cache, "max_bytes", lambda: 100.0)
        report = service_mod.tidy_cache()
        assert report["size"] > report["limit"] and report["dropped"] == []
        assert len(service.history.operations()) == 3
        assert os.path.exists(layers["r1"])

    def test_only_stacks_holding_files_lose_steps(self, tidy, monkeypatch):
        folder, layers = tidy
        service = service_mod.CrossFilterService()
        self._step(service, "v2", "/data/a.gpkg", "/data/a.gpkg", layer_id="p1")  # oldest, no file
        old, new = self._derived(folder, "dtm_bbbbbbbb.vrt", 300), self._derived(folder, "dtm_cccccccc.vrt", 100)
        self._step(service, "v1", old, new)
        layers["r1"] = new
        monkeypatch.setattr(cache, "max_bytes", lambda: 200.0)
        report = service_mod.tidy_cache()
        assert [step.operation.source_layer_id for _, step in report["dropped"]] == ["v1"]
        assert service.history.can_undo("v2") and not os.path.exists(old)

    def test_histories_of_every_service_are_cleared(self, tidy):
        first, second = service_mod.CrossFilterService(), service_mod.CrossFilterService()
        for service in (first, second):
            self._step(service, "v1", "/a", "/b")
        service_mod.forget_layer_everywhere("r1")
        assert not first.history.operations() and not second.history.operations()

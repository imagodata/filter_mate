"""Memory budgets and project ownership are independent of QGIS/GDAL availability."""
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


def load_store():
    path = Path(__file__).resolve().parents[3] / "adapters/agent/data_store.py"
    spec = importlib.util.spec_from_file_location("agent_data_store_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MemoryFS:
    def __init__(self):
        self.files = {}

    def MkdirRecursive(self, *args):
        pass

    def ReadDirRecursive(self, root):
        return [path[len(root) + 1:] for path in self.files if path.startswith(root + "/")]

    def VSIStatL(self, path):
        return SimpleNamespace(size=len(self.files[path].getvalue())) if path in self.files else None

    def VSIFOpenL(self, path, mode):
        if mode == "wb":
            self.files[path] = io.BytesIO()
        return self.files.get(path)

    def VSIFWriteL(self, data, size, count, handle):
        return handle.write(data)

    def VSIFReadL(self, size, count, handle):
        return handle.read(size * count)

    def VSIFCloseL(self, handle):
        pass

    def RmdirRecursive(self, root):
        self.files = {path: contents for path, contents in self.files.items()
                      if not path.startswith(root + "/")}


@pytest.fixture
def storage(monkeypatch):
    module, filesystem = load_store(), MemoryFS()
    monkeypatch.setattr(module, "_gdal", lambda: filesystem)
    return module, filesystem


def test_budget_is_shared_between_downloads_and_refuses_before_the_next_chunk(storage):
    module, filesystem = storage
    store = module.AgentDataStore(limit=10)
    first, second = store.new_path("one.geojson"), store.new_path("two.geojson")
    with store.writer(first) as write:
        write(b"123456")
    with store.writer(second) as write:
        write(b"789")
        with pytest.raises(ValueError, match="memory budget"):
            write(b"01")
    assert filesystem.files[second].getvalue() == b"789"
    with pytest.raises(ValueError, match="memory budget"):
        store.new_path("large.tif", expected_bytes=2)


def test_closing_a_project_aborts_a_stream_without_deleting_its_live_handle(storage):
    module, filesystem = storage
    store = module.AgentDataStore()
    path = store.new_path("answer.osm")
    with store.writer(path) as write:
        write(b"data")
        store.close()
        assert path in filesystem.files
        with pytest.raises(ValueError, match="project was closed"):
            write(b"more")
    assert not filesystem.files
    with pytest.raises(ValueError, match="project was closed"):
        store.new_path("late.tif")


def test_discard_removes_only_its_asset_and_sidecars(storage):
    module, filesystem = storage
    store = module.AgentDataStore()
    first, second = store.new_path("same.gpkg"), store.new_path("same.gpkg")
    for path in (first, first + "-journal", second):
        with store.writer(path) as write:
            write(b"data")
    module.discard(first)
    assert list(filesystem.files) == [second]
    module.discard("/home/user/my_project/layer.gpkg")
    assert list(filesystem.files) == [second]


def test_a_file_only_output_requires_a_destination_even_when_the_project_has_a_filename(storage, tmp_path):
    module, _ = storage
    store = module.AgentDataStore()
    with pytest.raises(ValueError, match="choose a destination"):
        store.disk_path("cloud.laz")
    assert list(tmp_path.iterdir()) == []
    store.destination = str(tmp_path)
    output = store.disk_path("cloud.laz")
    assert Path(output).parent.parent == tmp_path and Path(output).parent.is_dir()


def test_zip_members_and_provider_options_resolve_to_the_original_asset(storage):
    module, _ = storage
    source = "/vsizip//vsimem/filtermate-agent-a/b/archive.zip/roads.shp|subset=id > 1"
    assert module.memory_path(source) == "/vsimem/filtermate-agent-a/b/archive.zip"
    assert module.memory_path("/home/user/layer.gpkg|layername=x") == ""


def test_asset_names_cannot_choose_a_disk_location(storage):
    module, _ = storage
    store = module.AgentDataStore()
    path = store.new_path("../../folder\\roads.geojson")
    assert path.startswith(store.root + "/") and path.endswith("/roads.geojson")

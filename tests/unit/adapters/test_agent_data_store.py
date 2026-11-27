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


def test_dataset_and_sidecars_share_the_project_folder_without_overwriting_files(storage, tmp_path):
    module, _ = storage
    existing = tmp_path / "roads.dbf"
    existing.write_bytes(b"user data")
    names = ["roads.shp", "roads.shx", "roads.dbf", "roads.shp.xml"]
    reserved = set()
    first = module._asset_destinations(names, "roads.shp", str(tmp_path), reserved)
    second = module._asset_destinations(names, "roads.shp", str(tmp_path), reserved)
    assert {Path(path).parent for path in first.values()} == {tmp_path}
    assert [Path(first[name]).name for name in names] == ["roads_2.shp", "roads_2.shx", "roads_2.dbf", "roads_2.shp.xml"]
    assert [Path(second[name]).name for name in names] == ["roads_3.shp", "roads_3.shx", "roads_3.dbf", "roads_3.shp.xml"]
    assert existing.read_bytes() == b"user data" and list(tmp_path.iterdir()) == [existing]


def test_incomplete_copy_removes_only_its_new_file(storage, tmp_path, monkeypatch):
    module, _ = storage
    store = module.AgentDataStore()
    source = store.new_path("roads.geojson")
    with store.writer(source) as write:
        write(b"complete data")
    destination = tmp_path / "roads.geojson"
    monkeypatch.setattr(module, "size", lambda path: 100)
    with pytest.raises(ValueError, match="incomplete"):
        module._copy_file(source, str(destination))
    assert not destination.exists()


def test_exclusive_copy_never_removes_an_existing_user_file(storage, tmp_path):
    module, _ = storage
    store = module.AgentDataStore()
    source = store.new_path("roads.geojson")
    with store.writer(source) as write:
        write(b"new data")
    destination = tmp_path / "roads.geojson"
    destination.write_bytes(b"user data")
    with pytest.raises(FileExistsError):
        module._copy_file(source, str(destination))
    assert destination.read_bytes() == b"user data"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-be"])
@pytest.mark.parametrize("tag", ["SourceDataset", "SourceFilename"])
def test_vrt_dependencies_and_portable_rewrites_keep_escaped_paths(storage, monkeypatch, tmp_path, encoding, tag):
    module, _ = storage
    source = module.PREFIX + "project/asset/café & terrain.tif"
    xml = (f'<VRTDataset><{tag} relativeToVRT="0">'
           f'{source.replace("&", "&amp;")}</{tag}></VRTDataset>').encode(encoding)
    monkeypatch.setattr(module, "read_bytes", lambda path: xml)
    assert module._dependencies(module.PREFIX + "project/vrt/filter.vrt") == [source]

    vrt_path = tmp_path / "filter.vrt"
    vrt_path.write_bytes(xml)
    destination = tmp_path / "sources" / "café & terrain.tif"
    module._rewrite_vrt(str(vrt_path), {source: str(destination)})
    document = module.ET.fromstring(vrt_path.read_bytes())
    node = document.find(tag)
    assert node.text == "sources/café & terrain.tif"
    assert node.get("relativeToVRT") == "1"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-be"])
@pytest.mark.parametrize("reader", ["memory", "disk"])
@pytest.mark.parametrize("doctype", [
    '<!DOCTYPE VRTDataset>',
    '<!DOCTYPE VRTDataset [<!ENTITY source "expanded">]>',
    '<!DOCTYPE VRTDataset SYSTEM "file:///untrusted-vrt.dtd">',
    '<!DOCTYPE VRTDataset [<!ENTITY source SYSTEM "file:///untrusted-source">]>',
    '<!DOCTYPE VRTDataset [<!ENTITY % external SYSTEM "file:///untrusted-vrt.dtd">%external;]>',
])
def test_vrt_readers_refuse_dtds_before_entities_expand(storage, monkeypatch, tmp_path, encoding, reader, doctype):
    module, _ = storage
    xml = (doctype + '<VRTDataset><SourceFilename>&source;</SourceFilename></VRTDataset>').encode(encoding)
    if reader == "memory":
        monkeypatch.setattr(module, "read_bytes", lambda path: xml)
        with pytest.raises(ValueError, match="must not contain a DTD"):
            module._dependencies(module.PREFIX + "project/asset/filter.vrt")
    else:
        vrt_path = tmp_path / "filter.vrt"
        vrt_path.write_bytes(xml)
        with pytest.raises(ValueError, match="must not contain a DTD"):
            module._rewrite_vrt(str(vrt_path), {})
        assert vrt_path.read_bytes() == xml

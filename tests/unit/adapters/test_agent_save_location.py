"""A proposed save uses project context and real local data, without creating files or remembering a refusal."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def location(monkeypatch, tmp_path):
    path = Path(__file__).resolve().parents[3] / "adapters/agent/save_location.py"
    spec = importlib.util.spec_from_file_location("agent_save_location_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    folders = {name: tmp_path / name for name in ("home", "documents", "runtime", "profile", "previous")}
    for folder in folders.values():
        folder.mkdir()
    settings = {}
    core, qt = sys.modules["qgis.core"], sys.modules["qgis.PyQt.QtCore"]
    monkeypatch.setattr(core, "QgsSettings", lambda: SimpleNamespace(
        value=lambda key, default, **kw: settings.get(key, default), setValue=settings.__setitem__))
    monkeypatch.setattr(core, "QgsApplication", SimpleNamespace(qgisSettingsDirPath=lambda: str(folders["profile"])))
    monkeypatch.setattr(core, "QgsProviderRegistry", SimpleNamespace(instance=lambda: SimpleNamespace(
        decodeUri=lambda provider, source: {})))
    monkeypatch.setattr(qt, "QDir", SimpleNamespace(
        homePath=lambda: str(folders["home"]), tempPath=lambda: str(folders["runtime"])))
    monkeypatch.setattr(qt, "QStandardPaths", SimpleNamespace(StandardLocation=SimpleNamespace(DocumentsLocation=0),
        writableLocation=lambda kind: str(folders["documents"])))
    monkeypatch.setattr(qt, "QUrl", lambda path: SimpleNamespace(isLocalFile=lambda: False))
    project = SimpleNamespace(fileName=lambda: "", title=lambda: "", homePath=lambda: "", mapLayers=lambda: {},
                              pathResolver=lambda: SimpleNamespace(readPath=lambda path: path))
    return module, project, folders, settings


def _layer(path, name="Roads"):
    return SimpleNamespace(source=lambda: str(path), providerType=lambda: "ogr", name=lambda: name)


def test_existing_project_keeps_its_exact_filename_and_folder(location):
    module, project, folders, settings = location
    path = folders["home"] / "Current.qgs"
    path.touch()
    project.fileName = lambda: str(path)
    settings[module.LAST_PROJECT_FOLDER] = str(folders["previous"])
    assert module.suggested_project_path(project) == str(path)


def test_project_working_folder_and_title_take_priority(location):
    module, project, folders, settings = location
    project.homePath = lambda: str(folders["home"])
    project.title = lambda: "Urumea / étude: pente"
    settings[module.LAST_PROJECT_FOLDER] = str(folders["previous"])
    assert module.suggested_project_path(project) == str(folders["home"] / "Urumea _ étude_ pente.qgz")
    assert not list(folders["home"].iterdir())


def test_local_layers_suggest_their_shared_folder_and_skip_runtime_and_remote_data(location, tmp_path):
    module, project, folders, settings = location
    paths = [tmp_path / "data" / "roads" / "roads.gpkg", tmp_path / "data" / "terrain" / "dtm.tif",
             folders["runtime"] / "scratch.gpkg", folders["profile"] / "cache.tif"]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    sources = [str(path) + "|layername=roads" for path in paths]
    sources += ["/vsimem/filtermate-agent-project/asset/layer.gpkg", "https://example.org/remote.tif"]
    project.mapLayers = lambda: {str(i): _layer(source) for i, source in enumerate(sources)}
    settings[module.LAST_PROJECT_FOLDER] = str(folders["previous"])
    pending = [_layer("/vsimem/result", "Pente Urumea")]
    assert module.suggested_project_path(project, pending) == str(tmp_path / "data" / "Pente Urumea.qgz")


def test_provider_paths_are_decoded_and_resolved_relative_to_the_project(location, monkeypatch):
    module, project, folders, _ = location
    source = folders["home"] / "roads.gpkg"
    source.touch()
    registry = SimpleNamespace(decodeUri=lambda provider, uri: {"path": "roads.gpkg"})
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProviderRegistry", SimpleNamespace(instance=lambda: registry))
    project.pathResolver = lambda: SimpleNamespace(readPath=lambda path: str(folders["home"] / path))
    project.mapLayers = lambda: {"roads": _layer("provider-specific-uri")}
    assert Path(module.suggested_project_path(project)).parent == folders["home"]


def test_previous_successful_folder_then_documents_then_home_are_fallbacks(location):
    module, project, folders, settings = location
    settings[module.LAST_PROJECT_FOLDER] = str(folders["previous"])
    assert module.suggested_project_path(project) == str(folders["previous"] / "project.qgz")
    folders["previous"].rmdir()
    assert module.suggested_project_path(project) == str(folders["documents"] / "project.qgz")
    folders["documents"].rmdir()
    assert module.suggested_project_path(project) == str(folders["home"] / "project.qgz")


def test_new_project_suggestion_avoids_an_existing_name(location):
    module, project, folders, settings = location
    project.title = lambda: "Analysis"
    (folders["documents"] / "Analysis.qgz").touch()
    (folders["documents"] / "Analysis_2.qgz").touch()
    assert module.suggested_project_path(project) == str(folders["documents"] / "Analysis_3.qgz")
    assert settings == {}


@pytest.mark.parametrize("title, name", [("CON", "project_CON.qgz"), ("../NUL", "_NUL.qgz"),
                                          ("Étude.qgz", "Étude.qgz"), (". ", "project.qgz")])
def test_project_names_are_portable(location, title, name):
    module, project, folders, _ = location
    project.title = lambda: title
    assert module.suggested_project_path(project) == str(folders["documents"] / name)


def test_only_an_explicit_remember_updates_preferences(location):
    module, project, folders, settings = location
    module.suggested_project_path(project)
    assert not settings
    module.remember_project_folder(str(folders["home"] / "Analysis.qgz"))
    assert settings == {module.LAST_PROJECT_FOLDER: str(folders["home"])}

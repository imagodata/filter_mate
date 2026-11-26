# -*- coding: utf-8 -*-
"""
2026-11-24: the settings a project carries for its layers are read on the main thread when the task that registers
the layers is created (``capture_layer_settings``); on the way, a legacy name the panel wrote until 5.1.2 is moved under
the right one, the names of FilterMate leave the variables of QGIS (they broke the pairing of the user's variables), and
The project is the truth for a layer only when this version wrote its settings (the layer carries
``filterMate/settings_version``) in a project that can be saved (``layer_is_truth``); a setting that changes marks the
project modified (``settings_written``).

Module tested: infrastructure.utils.layer_settings
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_UTILS_DIR = Path(__file__).resolve().parents[4] / "infrastructure" / "utils"
_PKG = "fmtest_layer_settings_pkg"


def _load():
    full = f"{_PKG}.layer_settings"
    if full in sys.modules:
        return sys.modules[full]
    package = types.ModuleType(_PKG)
    package.__path__ = [str(_UTILS_DIR)]
    package.__package__ = _PKG
    sys.modules[_PKG] = package
    spec = importlib.util.spec_from_file_location(full, _UTILS_DIR / "layer_settings.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


layer_settings = _load()


class Layer:
    """The custom properties of a QgsMapLayer."""

    def __init__(self, layer_id, properties=None, deleted=False):
        self._id = layer_id
        self.props = dict(properties or {})
        self.deleted = deleted
        self.writes = []

    def id(self):
        if self.deleted:
            raise RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted")
        return self._id

    def customPropertyKeys(self):
        return list(self.props)

    def customProperty(self, key, default=None):
        return self.props.get(key, default)

    def setCustomProperty(self, key, value):
        self.writes.append(key)
        self.props[key] = value

    def removeCustomProperty(self, key):
        self.writes.append(f"-{key}")
        self.props.pop(key, None)


class Project:
    def __init__(self, path="", layers=(), storage=None):
        self.path = path
        self.storage = storage
        self.dirty = False
        self.layers = {layer.id(): layer for layer in layers}

    def fileName(self):
        return self.path

    def projectStorage(self):
        return self.storage

    def mapLayers(self):
        return dict(self.layers)

    def setDirty(self, dirty=True):
        self.dirty = dirty

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)


def V(name):
    return f"variableValues/{name}"


def capture(layers, **kwargs):
    return layer_settings.capture_layer_settings(layers, **kwargs)


MARKED = {"filterMate/settings_version": 2}


@pytest.fixture
def saved(tmp_path):
    path = tmp_path / "p.qgz"
    path.write_text("x")
    return path


def test_reads_the_settings_of_each_layer():
    parcelles = Layer("parcelles_1", {
        V("filterMate_exploring_single_selection_expression"): '"nom"',
        V("filterMate_filtering_layers_to_filter"): '["routes_1"]',
        V("filterMate_infos_layer_name"): "parcelles",
    })
    routes = Layer("routes_1", {"labeling/enabled": True})
    assert capture([parcelles, routes, "an id"]) == {
        "parcelles_1": {"exploring": {"single_selection_expression": '"nom"'},
                        "filtering": {"layers_to_filter": '["routes_1"]'}}}
    assert parcelles.writes == [] and routes.writes == []  # nothing written: the project stays as it was


def test_a_legacy_name_is_moved_once_and_wins():
    layer = Layer("parcelles_1", {
        V("filterMate_exploring_single_selection_expression"): '"fid"',
        V("exploring_single_selection_expression"): '"nom"',
        V("exploring_is_tracking"): True,
        V("filtering_layers_to_filter"): ["routes_1"],  # a list stored as such: moved as its JSON text
        V("infos_layer_name"): "parcelles",
    })
    captured = capture([layer])
    assert captured == {"parcelles_1": {"exploring": {"single_selection_expression": '"nom"', "is_tracking": True},
                                        "filtering": {"layers_to_filter": ["routes_1"]}}}
    assert layer.props == {
        V("filterMate_exploring_single_selection_expression"): '"nom"',
        V("filterMate_exploring_is_tracking"): True,
        V("filterMate_filtering_layers_to_filter"): '["routes_1"]',
    }
    layer.writes.clear()
    assert capture([layer]) == {"parcelles_1": {"exploring": {"single_selection_expression": '"nom"',
                                                              "is_tracking": True},
                                                "filtering": {"layers_to_filter": '["routes_1"]'}}}
    assert layer.writes == []  # the next reading moves nothing


def test_a_variable_of_the_user_gets_its_value_back():
    """Measured in QGIS 3.44 and 4.3: with FilterMate's names first, the user's 'my_var' showed as
    filterMate_exploring_b = 'hello'."""
    layer = Layer("parcelles_1", {
        V("filterMate_exploring_b"): True, V("filterMate_exploring_i"): 5,
        "variableNames": ["filterMate_exploring_b", "filterMate_exploring_i", "my_var"],
        "variableValues": ["hello"],
    })
    capture([layer])
    assert layer.props["variableNames"] == ["my_var"] and layer.props["variableValues"] == ["hello"]


def test_lists_written_together_by_qgis_keep_their_pairs():
    layer = Layer("parcelles_1", {
        V("exploring_is_linking"): True,
        "variableNames": ["exploring_is_linking", "my_var", "filterMate_exploring_b"],
        "variableValues": ["true", "hello", ""],
    })
    capture([layer])
    assert layer.props["variableNames"] == ["my_var"] and layer.props["variableValues"] == ["hello"]


def test_a_pairing_that_cannot_be_told_keeps_the_names_with_a_value():
    layer = Layer("parcelles_1", {
        "variableNames": ["filterMate_exploring_b", "my_var", "other", "filterMate_exploring_i"],
        "variableValues": ["x"],
    })
    capture([layer])
    assert layer.props["variableNames"] == ["filterMate_exploring_b", "my_var", "other"]  # only a name with no value
    assert layer.props["variableValues"] == ["x"]


def test_the_layers_to_filter_are_read_as_stored():
    """A layer to filter the project does not have is left out in memory only (the task), never in the project."""
    layer = Layer("parcelles_2", {V("filterMate_filtering_layers_to_filter"): '["routes_1", "rivers_of_another"]'})
    assert capture([layer]) == {"parcelles_2": {"filtering": {"layers_to_filter": '["routes_1", "rivers_of_another"]'}}}
    assert layer.writes == []


def test_known_and_deleted_layers_are_left():
    known = Layer("known_1", {V("exploring_is_tracking"): True})
    deleted = Layer("gone_1", {V("filterMate_exploring_is_tracking"): True}, deleted=True)
    assert capture([known, deleted], known={"known_1": {}}) == {}
    assert known.writes == [] and V("exploring_is_tracking") in known.props


def test_no_layers():
    assert layer_settings.capture_layer_settings(None) == {}


class TestTheProjectIsTheTruth:

    def test_for_a_layer_whose_settings_this_version_wrote_in_a_file_it_can_save(self, saved):
        marked, unmarked = Layer("a", MARKED), Layer("b")
        project = Project(str(saved), layers=[marked, unmarked])
        assert layer_settings.layer_is_truth(marked, project) is True
        assert layer_settings.layer_is_truth(unmarked, project) is False  # written by an earlier version
        assert layer_settings.truth_layer_ids([marked, unmarked, "an id"], project) == {"a"}

    def test_not_in_a_read_only_project(self, saved):
        saved.chmod(0o444)
        try:
            assert layer_settings.layer_is_truth(Layer("a", MARKED), Project(str(saved))) is False
        finally:
            saved.chmod(0o644)

    def test_not_in_a_project_without_file(self):
        assert layer_settings.layer_is_truth(Layer("a", MARKED), Project("")) is False

    @pytest.mark.parametrize("uri", ["postgresql:?service=pg&schema=public&project=travaux",
                                     "geopackage:/data/projets.gpkg?projectName=travaux"])
    def test_in_a_project_stored_in_a_database(self, uri):
        assert layer_settings.project_file_writable(Project(uri)) is True
        assert layer_settings.layer_is_truth(Layer("a", MARKED), Project(uri)) is True

    def test_in_a_project_with_a_storage(self):
        assert layer_settings.project_file_writable(Project("travaux", storage=object())) is True

    def test_a_windows_path_is_a_file(self, saved):
        assert layer_settings.project_file_writable(Project("C:/nowhere/p.qgz")) is False


class TestSettingsWritten:

    def test_the_layer_says_it_and_the_project_is_modified(self, saved):
        layer = Layer("parcelles_1")
        project = Project(str(saved), layers=[layer])
        assert layer_settings.settings_written(project, "parcelles_1") is True
        assert project.dirty and layer.props == MARKED

    def test_without_change_nothing_is_written_and_the_project_stays(self, saved):
        """2026-11-24 (audit): stamping the version without a change marked the project modified on opening (in
        QGIS a layer write dirties it). Without a change, neither the stamp nor the flag."""
        layer = Layer("parcelles_1")
        project = Project(str(saved), layers=[layer])
        assert layer_settings.settings_written(project, "parcelles_1", changed=False) is False
        assert not project.dirty and layer.props == {} and layer.writes == []

    def test_nothing_modified_in_a_read_only_project(self, saved):
        saved.chmod(0o444)
        project = Project(str(saved), layers=[Layer("parcelles_1")])
        try:
            assert layer_settings.settings_written(project, "parcelles_1") is False
        finally:
            saved.chmod(0o644)
        assert not project.dirty

    def test_a_change_of_form_only_is_no_change(self):
        layer = Layer("parcelles_1", {V("filterMate_filtering_layers_to_filter"): ["routes_1"],
                                      V("filterMate_exploring_is_linking"): True,
                                      V("filterMate_filtering_buffer_value_property"): 0,
                                      V("filterMate_filtering_geometric_predicates"): None})
        project = Project(layers=[layer])
        change = layer_settings.settings_change
        assert not change("parcelles_1", {"filterMate_filtering_layers_to_filter": '["routes_1"]'}, project)
        assert not change("parcelles_1", {"filterMate_exploring_is_linking": True}, project)
        assert not change("parcelles_1", {"filterMate_filtering_buffer_value_property": False}, project)  # 0 = False
        assert not change("parcelles_1", {"filterMate_filtering_geometric_predicates": "[]"}, project)  # None = []
        assert change("parcelles_1", {"filterMate_exploring_is_linking": False}, project)
        assert change("parcelles_1", {"filterMate_filtering_layers_to_filter": "[]"}, project)
        assert not change("parcelles_1", {"filterMate_infos_layer_name": "other"}, project)  # infos: not carried

    def test_stamping_a_layer_that_carries_no_setting_is_no_change(self, saved):
        """Audit 2026-11-24: opening a project whose layers have no FilterMate settings yet marked it modified
        (QGIS asked to save although the user changed nothing)."""
        layer = Layer("parcelles_1")  # pristine: no stamp, no setting
        project = Project(str(saved), layers=[layer])
        assert layer_settings.settings_change(
            "parcelles_1", {"filterMate_exploring_is_linking": True}, project) is False
        assert not project.dirty

    def test_a_real_change_of_a_stamped_layer_is_a_change(self, saved):
        layer = Layer("parcelles_1", dict(MARKED))
        project = Project(str(saved), layers=[layer])
        assert layer_settings.settings_change(
            "parcelles_1", {"filterMate_exploring_is_linking": True}, project) is True


def test_a_direct_write_since_a_registration_wins():
    queued_at = layer_settings.write_epoch()
    layer_settings.note_direct_write("parcelles_1", "filterMate_exploring_is_linking")
    assert layer_settings.written_since("parcelles_1", "filterMate_exploring_is_linking", queued_at)
    assert not layer_settings.written_since("parcelles_1", "filterMate_exploring_is_tracking", queued_at)
    assert not layer_settings.written_since("parcelles_1", "filterMate_exploring_is_linking",
                                            layer_settings.write_epoch())


def test_a_fresh_reload_clears_the_variables_of_filtermate(saved):
    path = saved
    layer = Layer("parcelles_1", {V("filterMate_exploring_is_linking"): False, V("filterMate_infos_layer_name"): "p",
                                  V("exploring_is_tracking"): True, "variableNames": ["my_var"],
                                  "variableValues": ["hello"], "labeling/enabled": True})
    project = Project(str(path), layers=[layer])
    assert layer_settings.clear_filtermate_variables("parcelles_1", project) == 3
    assert layer.props == {"variableNames": ["my_var"], "variableValues": ["hello"], "labeling/enabled": True,
                           **MARKED}  # the registration that follows writes the defaults
    assert project.dirty

# -*- coding: utf-8 -*-
"""
2026-11-24: a setting changed in the panel is written into the project under the name the project is read from.

``save_single_property`` wrote the layer variable ``<group>_<key>``; the registration of a layer writes and (now) reads
``filterMate_<group>_<key>``, which therefore kept the value of the registration in the saved project. A value saved
during a layer change was never written into the project (only into the SQLite): it is now written once the change
ends. A setting removed from the SQLite goes out of the project too, or the project would bring it back.

Module tested: adapters.variables_manager
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ADAPTERS = Path(__file__).resolve().parents[3] / "adapters"
_PKG = "fmtest_variables_manager_pkg"


def _load():
    full = f"{_PKG}.variables_manager"
    if full in sys.modules:
        return sys.modules[full]
    package = types.ModuleType(_PKG)
    package.__path__ = [str(_ADAPTERS)]
    sys.modules[_PKG] = package
    spec = importlib.util.spec_from_file_location(full, _ADAPTERS / "variables_manager.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


vm = _load()
_SPEC = importlib.util.spec_from_file_location(
    "fmtest_vm_type_utils", Path(__file__).resolve().parents[3] / "infrastructure" / "utils" / "type_utils.py")
_TYPE_UTILS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_TYPE_UTILS)
return_typed_value = _TYPE_UTILS.return_typed_value  # what the app gives the manager


def _load_layer_settings():
    """infrastructure/utils/layer_settings.py in a package of its own (the manager imports it from the plugin)."""
    package_name = "fmtest_vm_utils_pkg"
    package = types.ModuleType(package_name)
    package.__path__ = [str(Path(__file__).resolve().parents[3] / "infrastructure" / "utils")]
    sys.modules[package_name] = package
    spec = importlib.util.spec_from_file_location(f"{package_name}.layer_settings", Path(package.__path__[0]) / "layer_settings.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


layer_settings = _load_layer_settings()


class Layer:
    def __init__(self, layer_id="parcelles_1"):
        self._id = layer_id
        self.props = {}

    def id(self):
        return self._id

    def name(self):
        return "parcelles"

    def customPropertyKeys(self):
        return list(self.props)

    def customProperty(self, key, default=None):
        return self.props.get(key, default)

    def removeCustomProperty(self, key):
        self.props.pop(key, None)


class Project:
    def __init__(self, layer, path):
        self.layer, self.path, self.dirty, self.entries = layer, path, [], {}

    def mapLayer(self, layer_id):
        return self.layer if self.layer is not None and layer_id == self.layer.id() else None

    def fileName(self):
        return self.path

    def readNumEntry(self, scope, key, default=0):
        return self.entries.get(key, default), key in self.entries

    def writeEntry(self, scope, key, value):
        self.entries[key] = value

    def setDirty(self, dirty=True):
        self.dirty.append(dirty)


class Timers:
    """QTimer.singleShot, run by hand."""

    def __init__(self):
        self.queued = []

    def singleShot(self, delay, callback):
        self.queued.append(callback)

    def run(self):
        queued, self.queued = self.queued, []
        for callback in queued:
            callback()


class Cursor:
    def __init__(self):
        self.rows = []

    def execute(self, sql, params=()):
        self.rows.append((sql.split()[0], params))


@pytest.fixture
def env(monkeypatch, tmp_path):
    layer = Layer()
    written = []
    timers = Timers()
    path = tmp_path / "project.qgz"
    path.write_text("x")
    project = Project(layer, str(path))
    dirty = project.dirty
    monkeypatch.setattr(vm, "QgsProject", types.SimpleNamespace(instance=lambda: project), raising=False)
    monkeypatch.setattr(vm, "layer_settings", layer_settings)
    monkeypatch.setattr(layer_settings, "_project", lambda given=None: given or project)
    monkeypatch.setattr(vm, "sip", types.SimpleNamespace(isdeleted=lambda obj: False))
    monkeypatch.setattr(vm, "QTimer", timers, raising=False)
    monkeypatch.setattr(vm, "is_valid_layer", lambda obj: obj is not None)
    monkeypatch.setattr(vm, "is_qgis_alive", lambda: True)

    def batch(layer_id, variables):
        """safe_set_layer_variables_batch: only what changed is written."""
        changed = {name: value for name, value in variables.items() if layer.props.get(f"variableValues/{name}") != value}
        written.append((layer_id, dict(variables)))
        for name, value in changed.items():
            layer.props[f"variableValues/{name}"] = value
        return len(changed), True

    monkeypatch.setattr(vm, "safe_set_layer_variables_batch", batch)
    state = types.SimpleNamespace(changing=False, layer=layer, written=written, timers=timers, cursor=Cursor(),
                                  dirty=dirty, project=project, path=path)

    manager = vm.VariablesPersistenceManager(
        get_spatialite_connection=lambda: None, get_project_uuid=lambda: "p-1",
        get_project_layers=lambda: {layer.id(): {"exploring": {}, "filtering": {}}},
        return_typped_value=return_typed_value, cancel_layer_tasks=lambda layer_id: None,
        is_layer_change_in_progress=lambda: state.changing)
    state.manager = manager
    return state


def test_a_change_is_written_under_the_name_the_project_is_read_from(env):
    assert env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_linking", False) is True
    assert env.written == [("parcelles_1", {"filterMate_exploring_is_linking": False})]
    assert env.cursor.rows == [("INSERT", (env.cursor.rows[0][1][0], "p-1", "parcelles_1", "exploring", "is_linking",
                                           "False"))]
    assert env.dirty == [True]  # QGIS asks to save the project at closing


def test_a_value_already_stored_leaves_the_project_as_it_was(env):
    env.layer.props["variableValues/filterMate_exploring_is_linking"] = False
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_linking", False)
    assert env.dirty == []


def test_a_list_is_written_as_its_json_text(env):
    env.manager.save_single_property(env.layer, env.cursor, "filtering", "layers_to_filter", ["routes_1"])
    assert env.written == [("parcelles_1", {"filterMate_filtering_layers_to_filter": '["routes_1"]'})]


def test_a_change_during_a_layer_change_is_written_once_it_ends(env):
    env.changing = True
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "single_selection_expression", '"fid"')
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "single_selection_expression", '"nom"')
    assert env.written == [] and len(env.timers.queued) == 1  # one wait for both
    assert [row[1][4] for row in env.cursor.rows] == ["single_selection_expression"] * 2  # the SQLite, at once

    env.timers.run()  # the change goes on: wait again
    assert env.written == [] and len(env.timers.queued) == 1

    env.changing = False
    env.timers.run()
    assert env.written == [("parcelles_1", {"filterMate_exploring_single_selection_expression": '"nom"'})]
    assert env.timers.queued == [] and env.dirty == [True]


def test_a_later_change_is_not_overwritten_by_a_deferred_one(env):
    env.changing = True
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_linking", True)
    env.changing = False
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_linking", False)
    env.timers.run()
    assert env.written == [("parcelles_1", {"filterMate_exploring_is_linking": False})]


def test_a_layer_change_that_never_ends_does_not_keep_the_value_out(env):
    env.changing = True
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_tracking", True)
    for _ in range(vm.PENDING_VARIABLES_MAX_ATTEMPTS + 1):
        env.timers.run()
    assert env.written == [("parcelles_1", {"filterMate_exploring_is_tracking": True})]
    assert env.timers.queued == []


def test_a_removed_setting_goes_out_of_the_project(env, monkeypatch):
    env.layer.props = {"variableValues/filterMate_exploring_is_tracking": True,
                       "variableValues/filterMate_exploring_is_linking": False}

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def cursor(self):
            return env.cursor

    env.manager._get_connection = lambda: Conn()
    env.manager._get_project_layers = lambda: {"parcelles_1": {"exploring": {"is_tracking": True, "is_linking": False}}}
    assert env.manager.remove_variables_from_layer(env.layer, [("exploring", "is_tracking")]) is True
    assert env.layer.props == {"variableValues/filterMate_exploring_is_linking": False}
    assert env.dirty == [True]
    assert [row[0] for row in env.cursor.rows] == ["DELETE"]


def test_the_same_value_in_another_form_leaves_the_project_as_it_was(env):
    """A list stored as such by an earlier registration, written again as its JSON text: no change for the user."""
    env.layer.props["variableValues/filterMate_filtering_layers_to_filter"] = ["routes_1"]
    env.manager.save_single_property(env.layer, env.cursor, "filtering", "layers_to_filter", ["routes_1"])
    assert env.layer.props["variableValues/filterMate_filtering_layers_to_filter"] == '["routes_1"]'
    assert env.dirty == []


def test_the_version_of_the_settings_is_written_with_them(env):
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_linking", False)
    assert env.project.entries == {"layer_settings_version": 2}


def test_a_read_only_project_is_not_marked_modified(env):
    env.path.chmod(0o444)
    try:
        env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_linking", False)
    finally:
        env.path.chmod(0o644)
    assert env.layer.props["variableValues/filterMate_exploring_is_linking"] is False  # this session holds it
    assert env.dirty == [] and env.project.entries == {}


def test_a_project_without_file_is_not_marked_modified(env):
    env.project.path = ""
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_linking", False)
    assert env.dirty == []


def test_a_change_is_noted_for_a_registration_queued_before(env):
    queued_at = layer_settings.write_epoch()
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_linking", False)
    assert layer_settings.written_since("parcelles_1", "filterMate_exploring_is_linking", queued_at)


def test_deferred_values_of_another_project_are_never_written(env):
    env.changing = True
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_tracking", True)
    env.changing = False
    env.project.path = str(env.path.with_name("other.qgz"))  # another project opened meanwhile
    env.timers.run()
    assert env.written == [] and env.manager._pending_attempts == 0


def test_deferred_values_of_a_layer_gone_are_never_written(env):
    env.changing = True
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_tracking", True)
    env.changing = False
    env.project.layer = None
    env.timers.run()
    assert env.written == [] and env.manager._pending_attempts == 0


def test_a_failing_write_leaves_the_timer_ready(env, monkeypatch):
    env.changing = True
    env.manager.save_single_property(env.layer, env.cursor, "exploring", "is_tracking", True)
    env.changing = False
    monkeypatch.setattr(vm, "safe_set_layer_variables_batch", lambda *a: (_ for _ in ()).throw(RuntimeError("gone")))
    with pytest.raises(RuntimeError):
        env.timers.run()
    assert env.manager._pending_attempts == 0  # the next deferred value schedules the timer again


def test_a_setting_removed_by_restore_layer_state_goes_out_of_the_project(env):
    """restore_layer_state removes the key from the panel first: the row and the variable stayed."""
    env.layer.props = {"variableValues/filterMate_exploring_is_tracking": True}

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def cursor(self):
            return env.cursor

    env.manager._get_connection = lambda: Conn()
    env.manager._get_project_layers = lambda: {"parcelles_1": {"exploring": {}}}  # the key is gone already
    env.manager.remove_variables_from_layer(env.layer, [("exploring", "is_tracking")])
    assert env.layer.props == {} and [row[0] for row in env.cursor.rows] == ["DELETE"]

# -*- coding: utf-8 -*-
"""
2026-11-24: once saved, the project is the truth for the ``exploring`` and ``filtering`` settings of its layers.

``add_project_layer`` puts the settings the project carries (read on the main thread when the task was created) over
the copy of this computer's SQLite, or over the defaults of a layer this computer never saw (the project opened on
another computer, or moved). The merged settings go to the SQLite, and the variables of the layer are queued so that
the last value queued for each name is the one the panel holds: a setting of the project is queued as stored, so the
variable already right is not written (finished() writes only the values that changed).
"""
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.unit.core.tasks.test_point_cloud_registration_guards import _ROOT, _task, _vector_layer, task_mod

pytestmark = pytest.mark.unit

_SPEC = importlib.util.spec_from_file_location(
    "fmtest_project_layer_settings",
    Path(__file__).resolve().parents[4] / "core" / "domain" / "project_layer_settings.py")
project_layer_settings = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(project_layer_settings)

SQLITE = {
    "infos": {"primary_key_name": "fid", "layer_name": "parcelles"},
    "exploring": {"single_selection_expression": '"fid"', "custom_selection_expression": '"fid"',
                  "is_linking": True, "current_exploring_groupbox": "single_selection"},
    "filtering": {"has_layers_to_filter": False, "layers_to_filter": [], "buffer_value": 0.0},
}
PROJECT = {  # as the custom properties of the layer hold them
    "exploring": {"single_selection_expression": '"nom"', "custom_selection_expression": '"rank" > 10',
                  "is_linking": False},
    "filtering": {"has_layers_to_filter": True, "layers_to_filter": '["routes_1"]', "buffer_value": 12.5},
}


def _typed(value, action=None):
    """return_typed_value('load') for what these tests store."""
    if action == 'load' and isinstance(value, str) and value.startswith('['):
        import json
        return json.loads(value), list
    return value, type(value)


@pytest.fixture
def vector(monkeypatch):
    monkeypatch.setattr(task_mod, "QgsVectorLayer", MagicMock)
    monkeypatch.setattr(task_mod, "is_point_cloud_layer", lambda layer: False)
    monkeypatch.setattr(task_mod, "is_raster_layer", lambda layer: False)
    # The relative import of add_project_layer, under the private package the task module was loaded in
    for name in (_ROOT, f"{_ROOT}.core", f"{_ROOT}.core.domain"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, f"{_ROOT}.core.domain.project_layer_settings", project_layer_settings)


def _registering(existing, project=None, project_wins=True):
    task = _task(existing={group: dict(values) for group, values in existing.items()})
    task._project_settings_win = project_wins
    task.return_typped_value = _typed
    task._migrate_legacy_geometry_field = MagicMock()
    task._migrate_unreliable_primary_key = MagicMock()
    task._project_settings = {"parcelles_1": project} if project else {}
    return task


def _variables(task, layer_id="parcelles_1"):
    """What finished() writes: the last value queued for each name (it batches them per layer)."""
    written = {}
    for queued_id, name, value in task._deferred_layer_variables:
        if queued_id == layer_id and name is not None:
            written[name] = value
    return written


def test_the_project_wins_over_the_sqlite_of_this_computer(vector):
    task = _registering(SQLITE, PROJECT)
    task._load_existing_layer_properties = MagicMock(side_effect=lambda layer: _queued_from_sqlite(task, layer))

    assert task.add_project_layer(_vector_layer("parcelles_1", "parcelles")) is True

    props = task.project_layers["parcelles_1"]
    assert props["exploring"] == {"single_selection_expression": '"nom"', "custom_selection_expression": '"rank" > 10',
                                  "is_linking": False, "current_exploring_groupbox": "single_selection"}
    assert props["filtering"] == {"has_layers_to_filter": True, "layers_to_filter": ["routes_1"], "buffer_value": 12.5}
    assert props["infos"]["primary_key_name"] == "fid"  # infos: from the layer and the SQLite, not the project
    task.insert_properties_to_spatialite.assert_called_once_with("parcelles_1", props)  # the copy follows
    variables = _variables(task)
    assert variables["filterMate_exploring_single_selection_expression"] == '"nom"'
    assert variables["filterMate_filtering_layers_to_filter"] == '["routes_1"]'  # as stored: not written again
    assert variables["filterMate_exploring_current_exploring_groupbox"] == "single_selection"  # from the SQLite
    task._migrate_legacy_geometry_field.assert_called_once()  # the settings of the project are migrated too


def _queued_from_sqlite(task, layer, rows=None):
    """_load_existing_layer_properties: the rows of the SQLite, queued as variables (a list as its JSON text)."""
    rows = rows or SQLITE
    for group, values in rows.items():
        for key, value in values.items():
            stored = json.dumps(value) if isinstance(value, list) else value
            task._deferred_layer_variables.append((layer.id(), f"filterMate_{group}_{key}", stored))
    return {group: dict(values) for group, values in rows.items()}


def test_a_layer_this_computer_never_saw_takes_the_settings_of_the_project(vector):
    defaults = {"infos": {"primary_key_name": "fid"},
                "exploring": {"single_selection_expression": '"fid"', "is_linking": True, "is_tracking": False},
                "filtering": {"has_layers_to_filter": False, "layers_to_filter": []}}
    task = _registering({}, PROJECT)
    task.search_primary_key_from_layer = MagicMock(return_value=("fid", 0, "Integer64", True))
    task._build_new_layer_properties = MagicMock(return_value=defaults)

    assert task.add_project_layer(_vector_layer("parcelles_1", "parcelles")) is True

    props = task.project_layers["parcelles_1"]
    assert props["exploring"]["single_selection_expression"] == '"nom"'
    assert props["exploring"]["is_linking"] is False
    assert props["exploring"]["is_tracking"] is False  # a default the project does not carry
    assert props["filtering"]["layers_to_filter"] == ["routes_1"]
    variables = _variables(task)
    assert variables["filterMate_exploring_is_linking"] is False
    assert variables["filterMate_filtering_layers_to_filter"] == '["routes_1"]'
    assert variables["filterMate_exploring_is_tracking"] is False


def test_without_settings_in_the_project_the_sqlite_gives_them_as_before(vector):
    task = _registering(SQLITE)
    task._load_existing_layer_properties = MagicMock(side_effect=lambda layer: _queued_from_sqlite(task, layer))

    assert task.add_project_layer(_vector_layer("parcelles_1", "parcelles")) is True

    assert task.project_layers["parcelles_1"]["exploring"] == SQLITE["exploring"]
    assert len(task._deferred_layer_variables) == sum(map(len, SQLITE.values()))


def test_a_task_made_without_init_has_no_settings_of_the_project(vector):
    task = _registering(SQLITE)
    del task._project_settings
    task._load_existing_layer_properties = MagicMock(return_value={g: dict(v) for g, v in SQLITE.items()})
    assert task.add_project_layer(_vector_layer("parcelles_1", "parcelles")) is True
    assert task.project_layers["parcelles_1"]["filtering"] == SQLITE["filtering"]


def test_a_project_of_an_earlier_version_does_not_win_over_the_sqlite(vector):
    """No version entry (the first opening after the update): the value under the legacy name may be older than the
    SQLite's. The SQLite wins where it has the setting, and the project gives the others."""
    sqlite = {"infos": {"primary_key_name": "fid"},
              "exploring": {"single_selection_expression": '"rank"', "is_linking": True},
              "filtering": {"layers_to_filter": []}}
    older = {"exploring": {"single_selection_expression": '"nom"', "custom_selection_expression": '"rank" > 10'},
             "filtering": {"layers_to_filter": '["routes_1"]'}}
    task = _registering(sqlite, older, project_wins=False)
    task._load_existing_layer_properties = MagicMock(
        side_effect=lambda layer: _queued_from_sqlite(task, layer, sqlite))

    assert task.add_project_layer(_vector_layer("parcelles_1", "parcelles")) is True

    props = task.project_layers["parcelles_1"]
    assert props["exploring"]["single_selection_expression"] == '"rank"'  # the SQLite's
    assert props["exploring"]["custom_selection_expression"] == '"rank" > 10'  # only the project has it
    assert props["filtering"]["layers_to_filter"] == []  # the SQLite's, empty
    variables = _variables(task)
    assert variables["filterMate_exploring_single_selection_expression"] == '"rank"'  # into the project
    assert variables["filterMate_filtering_layers_to_filter"] == "[]"  # as JSON text: survives the .qgz
    assert variables["filterMate_exploring_custom_selection_expression"] == '"rank" > 10'


def test_a_list_of_the_project_is_queued_as_its_json_text(vector):
    task = _registering({}, {"filtering": {"layers_to_filter": ["routes_1"]}})
    task.search_primary_key_from_layer = MagicMock(return_value=("fid", 0, "Integer64", True))
    task._build_new_layer_properties = MagicMock(return_value={"infos": {}, "exploring": {}, "filtering": {}})
    assert task.add_project_layer(_vector_layer("parcelles_1", "parcelles")) is True
    assert _variables(task)["filterMate_filtering_layers_to_filter"] == '["routes_1"]'
    assert task.project_layers["parcelles_1"]["filtering"]["layers_to_filter"] == ["routes_1"]


def test_a_value_the_panel_wrote_after_the_queue_wins(vector, monkeypatch):
    """finished() writes the queue on the next turn of the event loop: a change the panel saved in between stays."""
    utils = types.ModuleType(f"{_ROOT}.infrastructure.utils")
    for name in (f"{_ROOT}.infrastructure",):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, f"{_ROOT}.infrastructure.utils", utils)
    noted = types.SimpleNamespace(epoch=0, direct=set(), marked=0)
    utils.layer_settings = types.SimpleNamespace(
        write_epoch=lambda: noted.epoch,
        written_since=lambda layer_id, name, epoch: (layer_id, name) in noted.direct,
        settings_change=lambda layer_id, variables: bool(variables),
        settings_written=lambda: setattr(noted, "marked", noted.marked + 1),
        clear_filtermate_variables=MagicMock())
    written = []
    later = []
    monkeypatch.setattr(task_mod, "QTimer", types.SimpleNamespace(singleShot=lambda delay, callback: later.append(callback)))
    monkeypatch.setattr(task_mod, "safe_set_layer_variables_batch",
                        lambda layer_id, variables: (written.append(dict(variables)), (len(variables), True))[1])
    monkeypatch.setattr(task_mod, "is_qgis_alive", lambda: True)
    monkeypatch.setattr(task_mod, "MESSAGE_TASKS_CATEGORIES", {"add_layers": "ManageLayers"})
    task = _registering({})
    task.exception, task.project_layers, task._layer_facts = None, None, None
    task._deferred_layer_variables = [("parcelles_1", "filterMate_exploring_is_linking", True),
                                      ("parcelles_1", "filterMate_exploring_is_tracking", False)]

    task.finished(True)
    noted.direct.add(("parcelles_1", "filterMate_exploring_is_linking"))  # the panel, before the next turn
    for callback in later:
        callback()

    assert written == [{"filterMate_exploring_is_tracking": False}]
    assert noted.marked == 1


def test_an_empty_value_read_back_as_none_is_empty_again(vector):
    """An empty text, or an empty list stored as such, comes back from a .qgz as None (QGIS 3.44 and 4.3)."""
    sqlite = {"infos": {}, "exploring": {}, "filtering": {"buffer_value_expression": "x", "layers_to_filter": ["a"]}}
    task = _registering(sqlite, {"filtering": {"buffer_value_expression": None, "layers_to_filter": None}})
    task._load_existing_layer_properties = MagicMock(return_value={g: dict(v) for g, v in sqlite.items()})
    assert task.add_project_layer(_vector_layer("parcelles_1", "parcelles")) is True
    assert task.project_layers["parcelles_1"]["filtering"] == {"buffer_value_expression": "", "layers_to_filter": []}
    assert _variables(task) == {"filterMate_filtering_buffer_value_expression": "",
                                "filterMate_filtering_layers_to_filter": "[]"}


def test_a_flag_the_sqlite_kept_as_1_is_a_bool_again(vector):
    task = _registering({})
    task._load_existing_layer_properties = types.MethodType(
        task_mod.LayersManagementEngineTask._load_existing_layer_properties, task)
    task.return_typped_value = lambda value, action=None: (int(value), int) if value in ("0", "1") else _typed(value, action)
    task.select_properties_from_spatialite = lambda layer_id: [
        ("exploring", "is_linking", "1"), ("filtering", "has_buffer_value", "0"), ("filtering", "buffer_segments", "1"),
        ("infos", "primary_key_idx", "0")]
    loaded = task._load_existing_layer_properties(_vector_layer("parcelles_1", "parcelles"))
    assert loaded["exploring"]["is_linking"] is True and loaded["filtering"]["has_buffer_value"] is False
    assert loaded["filtering"]["buffer_segments"] == 1 and type(loaded["filtering"]["buffer_segments"]) is int
    assert loaded["infos"]["primary_key_idx"] == 0 and type(loaded["infos"]["primary_key_idx"]) is int


def test_the_lists_of_the_sqlite_are_queued_as_their_json_text(vector):
    """An empty list stored as such comes back from a .qgz as None (QGIS 3.44 and 4.3): JSON text, as the panel."""
    task = _registering({})
    task._load_existing_layer_properties = types.MethodType(
        task_mod.LayersManagementEngineTask._load_existing_layer_properties, task)
    task.select_properties_from_spatialite = lambda layer_id: [
        ("filtering", "layers_to_filter", "[]"), ("filtering", "geometric_predicates", '["Intersect"]'),
        ("exploring", "single_selection_expression", '"nom"')]
    loaded = task._load_existing_layer_properties(_vector_layer("parcelles_1", "parcelles"))
    assert loaded["filtering"]["layers_to_filter"] == []
    assert _variables(task) == {"filterMate_filtering_layers_to_filter": "[]",
                                "filterMate_filtering_geometric_predicates": '["Intersect"]',
                                "filterMate_exploring_single_selection_expression": '"nom"'}

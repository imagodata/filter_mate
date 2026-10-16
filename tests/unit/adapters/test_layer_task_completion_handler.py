# -*- coding: utf-8 -*-
"""
LayerTaskCompletionHandler: end of the add_layers / remove_layers tasks.

- A removed layer loses its stored properties, its filter history rows and its
  undo/redo entries; the first one used to raise AttributeError
  (``HistoryService.remove_history`` did not exist), which skipped the project
  variables, the panel refresh, the datasource update and the other removed layers.

The module is loaded from its file (no package: its optional perf_timer import
falls back to a no-op) and runs against a real sqlite file and a real HistoryService.
"""
import importlib.util
import sqlite3
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.services.history_service import HistoryEntry, HistoryService

_REPO = Path(__file__).resolve().parents[3]


def _load_handler_module():
    spec = importlib.util.spec_from_file_location(
        "_fm_layer_task_completion_handler", _REPO / "adapters" / "layer_task_completion_handler.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


handler_mod = _load_handler_module()

PROJECT = "project-1"


def _create_db(path, layer_ids):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE fm_project_layers_properties (fk_project TEXT, layer_id TEXT, meta_key TEXT)")
    conn.execute("CREATE TABLE fm_subset_history (fk_project TEXT, layer_id TEXT, subset_string TEXT)")
    for layer_id in layer_ids:
        conn.execute("INSERT INTO fm_project_layers_properties VALUES (?, ?, 'infos')", (PROJECT, layer_id))
        conn.execute("INSERT INTO fm_subset_history VALUES (?, ?, 'x = 1')", (PROJECT, layer_id))
    # another project's rows of the same layer id stay
    conn.execute("INSERT INTO fm_project_layers_properties VALUES ('other', 'B', 'infos')")
    conn.commit()
    conn.close()


def _rows(path, table):
    conn = sqlite3.connect(path)
    try:
        return sorted(conn.execute(f"SELECT fk_project, layer_id FROM {table}").fetchall())  # nosec B608
    finally:
        conn.close()


def _layer(layer_id):
    return {"infos": {"layer_id": layer_id, "layer_name": layer_id, "layer_provider_type": "ogr"}}


class _Env:
    """The callbacks FilterMateApp gives the handler, as plain recorders."""

    def __init__(self, tmp_path, registered, db_layers=None):
        self.db_path = str(tmp_path / "fm.sqlite")
        _create_db(self.db_path, db_layers if db_layers is not None else registered)
        self.project_layers = {layer_id: _layer(layer_id) for layer_id in registered}
        self.dockwidget = types.SimpleNamespace(
            PROJECT_LAYERS=dict(self.project_layers),
            widgets={},
            widgets_initialized=False,
            get_project_layers_from_app=MagicMock(),
        )
        self.history = HistoryService()
        self.save_project_variables = MagicMock()
        self.update_datasource = MagicMock()
        self.update_layer_datasource = MagicMock()
        self.remove_layer_datasource = MagicMock()
        self.pending = 0
        self.queue = []
        self.process_queue = MagicMock()
        project = MagicMock()
        project.readPath.return_value = "/data"
        self.handler = handler_mod.LayerTaskCompletionHandler(
            get_spatialite_connection=lambda: sqlite3.connect(self.db_path),
            get_project_uuid=lambda: PROJECT,
            get_project=lambda: project,
            get_dockwidget=lambda: self.dockwidget,
            get_project_layers=lambda: self.project_layers,
            set_project_layers=self._set_project_layers,
            get_history_manager=lambda: self.history,
            save_project_variables_callback=self.save_project_variables,
            update_datasource_callback=self.update_datasource,
            get_env_vars=lambda: {},
            process_add_layers_queue_callback=self.process_queue,
            validate_layer_info_callback=lambda key: self.project_layers.get(key, {}).get("infos"),
            update_datasource_for_layer_callback=self.update_layer_datasource,
            remove_datasource_for_layer_callback=self.remove_layer_datasource,
            pending_tasks_counter_callbacks={
                'get': lambda: self.pending,
                'decrement': self._decrement,
                'get_queue': lambda: self.queue,
            },
        )

    def _set_project_layers(self, layers):
        self.project_layers = layers

    def _decrement(self):
        self.pending -= 1

    def push_history(self, layer_id, expression="x = 1"):
        self.history.push(HistoryEntry.create(expression, [layer_id], [(layer_id, "")]))

    def history_layers(self):
        return [entry.layer_ids for entry in self.history.get_undo_stack()]

    def panel_layers(self):
        return list(self.dockwidget.get_project_layers_from_app.call_args[0][0])


@pytest.mark.unit
class TestRemovedLayersCleanUp:

    def test_removed_layer_is_cleaned_and_the_completion_goes_on(self, tmp_path):
        env = _Env(tmp_path, ["A", "B"])
        env.push_history("A")
        env.push_history("B")

        env.handler.handle_task_completion({"A": env.project_layers["A"]}, "remove_layers")

        assert _rows(env.db_path, "fm_project_layers_properties") == [("other", "B"), (PROJECT, "A")]
        assert _rows(env.db_path, "fm_subset_history") == [(PROJECT, "A")]
        assert env.history_layers() == [("A",)]
        env.save_project_variables.assert_called_once_with()
        assert env.panel_layers() == ["A"]
        env.update_datasource.assert_called_once_with()

    def test_every_removed_layer_of_the_batch_is_cleaned(self, tmp_path):
        env = _Env(tmp_path, ["A", "B", "C"])
        env.push_history("B")
        env.push_history("C")

        env.handler.handle_task_completion({"A": env.project_layers["A"]}, "remove_layers")

        assert _rows(env.db_path, "fm_subset_history") == [(PROJECT, "A")]
        assert env.history.total_entries == 0

    def test_a_failing_layer_does_not_stop_the_others(self, tmp_path):
        env = _Env(tmp_path, ["A", "B", "C"])
        env.history = MagicMock()
        env.history.remove_history.side_effect = [RuntimeError("boom"), 1]

        env.handler.handle_task_completion({"A": env.project_layers["A"]}, "remove_layers")

        assert [c.args[0] for c in env.history.remove_history.call_args_list] == ["B", "C"]
        assert _rows(env.db_path, "fm_subset_history") == [(PROJECT, "A")]
        env.save_project_variables.assert_called_once_with()
        assert env.panel_layers() == ["A"]
        env.update_datasource.assert_called_once_with()

    def test_remaining_layers_keep_their_datasource_bookkeeping(self, tmp_path):
        env = _Env(tmp_path, ["A", "B"])

        env.handler.handle_task_completion({"A": env.project_layers["A"]}, "remove_layers")

        env.remove_layer_datasource.assert_called_once_with(env.project_layers["A"]["infos"])

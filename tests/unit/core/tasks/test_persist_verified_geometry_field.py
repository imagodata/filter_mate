# -*- coding: utf-8 -*-
"""
2026-09-14: a stored layer_geometry_field that no longer matches the layer
URI ('geom' written by an older version, 'geometrie' in the URI) is corrected
once — in the in-memory infos, in the deferred layer variables and in the
FilterMate database — instead of being re-detected and warned about at every
task by LayerOrganizer. The method is extracted from layer_management_task.py
with ast so the task module (heavy QGIS/relative imports) is never imported.
"""
import ast
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_TASK = Path(__file__).resolve().parents[4] / "core" / "tasks" / "layer_management_task.py"


def _extract(name):
    tree = ast.parse(_TASK.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                ns = {"logger": MagicMock()}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_TASK), "exec"), ns)
                return ns[name]
    raise AssertionError(f"{name} not found")


class _Cursor:
    def __init__(self, log):
        self.log = log

    def execute(self, sql, params):
        self.log.append((sql, params))

    def close(self):
        pass


class _Conn:
    def __init__(self, log):
        self.log = log
        self.committed = False

    def cursor(self):
        return _Cursor(self.log)

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _task(sql_log):
    task = types.SimpleNamespace(_deferred_layer_variables=[], project_uuid="p-1")
    conn = _Conn(sql_log)
    task._safe_spatialite_connect = lambda: conn
    task._persist_verified_geometry_field = types.MethodType(_extract("_persist_verified_geometry_field"), task)
    return task, conn


def _layer(provider, geometry_column, layer_id="l-1"):
    layer = MagicMock()
    layer.providerType.return_value = provider
    layer.source.return_value = f"uri geom={geometry_column}"
    layer.id.return_value = layer_id
    layer.name.return_value = "batiment"
    return layer


@pytest.fixture
def uri(monkeypatch):
    """qgis.core.QgsDataSourceUri(source).geometryColumn() reads the fake source."""
    qgis_core = sys.modules["qgis.core"]

    def make(source):
        obj = MagicMock()
        obj.geometryColumn.return_value = source.split("geom=", 1)[1]
        return obj

    monkeypatch.setattr(qgis_core, "QgsDataSourceUri", make, raising=False)


@pytest.mark.unit
class TestPersistVerifiedGeometryField:

    def test_mismatch_is_corrected_in_memory_variables_and_database(self, uri):
        sql_log = []
        task, conn = _task(sql_log)
        infos = {"layer_geometry_field": "geom"}

        task._persist_verified_geometry_field(infos, _layer("postgres", "geometrie"))

        assert infos["layer_geometry_field"] == "geometrie"
        assert task._deferred_layer_variables == [("l-1", "filterMate_infos_layer_geometry_field", "geometrie")]
        assert len(sql_log) == 1
        sql, params = sql_log[0]
        assert "layer_geometry_field" in sql and params == ("geometrie", "p-1", "l-1")
        assert conn.committed is True

    def test_matching_value_is_left_alone(self, uri):
        sql_log = []
        task, _ = _task(sql_log)
        infos = {"layer_geometry_field": "geometrie"}
        task._persist_verified_geometry_field(infos, _layer("postgres", "geometrie"))
        assert infos["layer_geometry_field"] == "geometrie"
        assert task._deferred_layer_variables == [] and sql_log == []

    @pytest.mark.parametrize("stored", [None, "", "NULL", "None"])
    def test_missing_or_null_stored_value_is_not_the_job_of_this_method(self, uri, stored):
        sql_log = []
        task, _ = _task(sql_log)
        infos = {"layer_geometry_field": stored} if stored is not None else {}
        task._persist_verified_geometry_field(infos, _layer("postgres", "geometrie"))
        assert infos.get("layer_geometry_field") == stored
        assert sql_log == []

    def test_ogr_layers_are_skipped(self, uri):
        sql_log = []
        task, _ = _task(sql_log)
        infos = {"layer_geometry_field": "geom"}
        task._persist_verified_geometry_field(infos, _layer("ogr", "geometry"))
        assert infos["layer_geometry_field"] == "geom" and sql_log == []

    def test_database_failure_keeps_the_in_memory_correction(self, uri):
        task, conn = _task([])
        conn.cursor = MagicMock(side_effect=OSError("locked"))
        infos = {"layer_geometry_field": "geom"}
        task._persist_verified_geometry_field(infos, _layer("postgres", "geometrie"))
        assert infos["layer_geometry_field"] == "geometrie"
        assert task._deferred_layer_variables[0][2] == "geometrie"

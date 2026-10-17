# -*- coding: utf-8 -*-
"""
FilterEngineTask._get_valid_postgresql_connection: a task opens its own connection.

ACTIVE_POSTGRESQL was a connection shared by every task (opened for the first
PostgreSQL layer of the project): a project with layers on two databases
filtered the second one through the first one's connection. The setting never
holds a connection now; each task takes one from its own source layer, once.
Method extracted with ast.
"""
import ast
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_MODULE = Path(__file__).resolve().parents[4] / "core" / "tasks" / "filter_task.py"


def _method(opener):
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "_get_valid_postgresql_connection":
                ns = {"logger": MagicMock(), "get_datasource_connexion_from_layer": opener,
                      "QGIS_PROVIDER_POSTGRES": "postgres"}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), ns)
                return ns["_get_valid_postgresql_connection"]
    raise AssertionError("method not found")


class _Layer:
    def __init__(self, database):
        self.database = database

    def providerType(self):
        return "postgres"


def _connection(database):
    connection = MagicMock(closed=False)
    connection.database = database
    return connection


def _task(source_layer, active=None, project_layer=None):
    project = MagicMock()
    project.mapLayer.return_value = project_layer
    task = types.SimpleNamespace(
        task_parameters={"task": {"options": {"ACTIVE_POSTGRESQL": active}}, "infos": {"layer_id": "l1"}},
        source_layer=source_layer, active_connections=[], PROJECT=project)
    return task


def test_a_task_connects_to_the_database_of_its_own_source_layer():
    opened = []

    def opener(layer):
        connection = _connection(layer.database)
        opened.append(connection)
        return connection, None

    get = _method(opener)
    first, second = _task(_Layer("db_one")), _task(_Layer("db_two"))

    assert get(first).database == "db_one"
    assert get(second).database == "db_two"
    assert first.active_connections == [opened[0]] and second.active_connections == [opened[1]]


@pytest.mark.parametrize("active", [_connection("shared_db"), "", None, {"host": "h"}, ["dbname=x password=y"]])
def test_whatever_active_postgresql_holds_is_ignored(active):
    get = _method(lambda layer: (_connection(layer.database), None))

    assert get(_task(_Layer("db_one"), active=active)).database == "db_one"


def test_the_connection_is_opened_once_per_task_and_closed_with_it():
    calls = []

    def opener(layer):
        calls.append(layer)
        return _connection(layer.database), None

    get = _method(opener)
    task = _task(_Layer("db_one"))

    assert get(task) is get(task)
    assert len(calls) == 1


def test_a_closed_connection_is_replaced():
    get = _method(lambda layer: (_connection(layer.database), None))
    task = _task(_Layer("db_one"))
    first = get(task)
    first.closed = True

    second = get(task)

    assert second is not first and not second.closed


def test_no_connection_is_an_error():
    get = _method(lambda layer: (None, None))

    with pytest.raises(Exception, match="No valid PostgreSQL connection"):
        get(_task(_Layer("db_one")))

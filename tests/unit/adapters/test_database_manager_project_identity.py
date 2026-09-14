# -*- coding: utf-8 -*-
"""
2026-09-14: DatabaseManager.save_project_variables copied whatever QgsProject
held at that moment into the row of the session's UUID. fileNameChanged fires
with the next project's name before the UUID is switched, and a closed
project has no name: rows were renamed to another project or emptied, could
never be matched again, and every open created a new fm_projects row and
re-migrated the "orphan" favorites. Method extracted with ast on a temporary
SQLite database.
"""
import ast
import sqlite3
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_MODULE = Path(__file__).resolve().parents[3] / "adapters" / "database_manager.py"


def _save_project_variables():
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "save_project_variables":
                import json
                import os
                from typing import Any, Dict, Optional
                ns = {"logger": MagicMock(), "os": os, "json": json, "Dict": Dict, "Any": Any, "Optional": Optional}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(_MODULE), "exec"), ns)
                return ns["save_project_variables"]
    raise AssertionError("save_project_variables not found")


def _manager(tmp_path, uuid, stored_name, stored_path, qgis_file):
    db = str(tmp_path / "fm.sqlite")
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE fm_projects (project_id TEXT PRIMARY KEY, _created_at TEXT, _updated_at TEXT,
                                  project_name TEXT, project_path TEXT, project_settings TEXT);
    """)
    conn.execute("INSERT INTO fm_projects VALUES (?, '', '', ?, ?, '{}')", (uuid, stored_name, stored_path))
    conn.commit()
    conn.close()
    project = MagicMock()
    project.absoluteFilePath.return_value = qgis_file
    project.absolutePath.return_value = qgis_file.rsplit("/", 1)[0] if qgis_file else ""
    manager = types.SimpleNamespace(_project=project, _project_uuid=uuid,
                                    get_connection=lambda: sqlite3.connect(db),
                                    _clean_for_json=lambda d: d)
    manager.save_project_variables = types.MethodType(_save_project_variables(), manager)
    return manager, db


def _row(db, uuid):
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT project_name, project_path, project_settings FROM fm_projects WHERE project_id=?",
                       (uuid,)).fetchone()
    conn.close()
    return row


@pytest.mark.unit
class TestProjectRowIdentityIsPreserved:

    def test_same_project_saves_settings(self, tmp_path):
        m, db = _manager(tmp_path, "u1", "bdd.qgz", "C:/Users/Simon", "C:/Users/Simon/bdd.qgz")
        assert m.save_project_variables({"CURRENT_PROJECT": {"k": 1}}) is True
        assert _row(db, "u1") == ("bdd.qgz", "C:/Users/Simon", '{"k": 1}')

    def test_next_project_name_does_not_rename_the_row(self, tmp_path):
        # fileNameChanged of the next project fires while the UUID is still the previous one
        m, db = _manager(tmp_path, "u1", "bdd.qgz", "C:/Users/Simon", "C:/Users/Simon/Desktop/31.qgz")
        assert m.save_project_variables({"CURRENT_PROJECT": {"k": 2}}) is False
        assert _row(db, "u1") == ("bdd.qgz", "C:/Users/Simon", "{}")

    def test_closed_project_does_not_empty_the_row(self, tmp_path):
        m, db = _manager(tmp_path, "u1", "bdd.qgz", "C:/Users/Simon", "")
        assert m.save_project_variables({"CURRENT_PROJECT": {"k": 3}}) is False
        assert _row(db, "u1") == ("bdd.qgz", "C:/Users/Simon", "{}")

    def test_unsaved_project_gets_its_name_on_first_save(self, tmp_path):
        m, db = _manager(tmp_path, "u1", "", "", "C:/Users/Simon/new.qgz")
        assert m.save_project_variables({"CURRENT_PROJECT": {}}) is True
        assert _row(db, "u1")[:2] == ("new.qgz", "C:/Users/Simon")

    def test_unsaved_project_stays_unsaved(self, tmp_path):
        m, db = _manager(tmp_path, "u1", "", "", "")
        assert m.save_project_variables({"CURRENT_PROJECT": {"k": 4}}) is True
        assert _row(db, "u1") == ("", "", '{"k": 4}')

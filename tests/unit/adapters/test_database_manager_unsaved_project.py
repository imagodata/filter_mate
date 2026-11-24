# -*- coding: utf-8 -*-
"""
2026-11-24 (review): a project with no file gets an id of its own.

``_load_or_create_project`` reused the most recent row of an unsaved project for every unsaved project: each new
project was bound to that one "bin", whose first "Save as" took the favorites and settings of all the unsaved sessions
before it into its .qgz, and the favorites of the older unsaved rows were reached by no path any more. An unsaved
project now keeps only the id it was given in this session (its project variable, emptied by QgsProject.clear()).
``purge_stale_projects`` keeps an unsaved row that still has favorites.

``database_manager`` runs against a real sqlite file, loaded as in test_purge_stale_projects.
"""
import sqlite3

import pytest

from tests.unit.adapters.test_purge_stale_projects import _DDL, _add_project, _count, _load_database_manager

pytestmark = pytest.mark.unit


class Project:
    """What _load_or_create_project reads of a QgsProject, and the variable it writes."""

    def __init__(self, path="", variables=None):
        self.path, self.variables = path, dict(variables or {})

    def absoluteFilePath(self):  # noqa: N802 - the QGIS name
        return self.path

    def absolutePath(self):  # noqa: N802 - the QGIS name
        return self.path.rsplit("/", 1)[0] if self.path else ""

    def customVariables(self):  # noqa: N802 - the QGIS name
        return dict(self.variables)


class Variables:
    """QgsExpressionContextUtils.setProjectVariable, into the stand-in."""

    @staticmethod
    def setProjectVariable(project, name, value):  # noqa: N802 - the QGIS name
        project.variables[name] = value


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(_DDL + "CREATE TABLE fm_favorites (id TEXT PRIMARY KEY, project_uuid TEXT NOT NULL, name TEXT);")
    yield conn
    conn.close()


def bind(dbm, monkeypatch, db, project):
    monkeypatch.setattr(dbm, "QgsExpressionContextUtils", Variables)
    manager = dbm.DatabaseManager.__new__(dbm.DatabaseManager)
    manager._project, manager._project_uuid = project, None
    manager._load_or_create_project(db.cursor(), {}, {})
    return manager.project_uuid


def test_a_new_project_never_takes_the_row_of_another_unsaved_project(db, monkeypatch):
    dbm = _load_database_manager()
    _add_project(db.cursor(), "orphan-old", "", "", days_old=3)
    _add_project(db.cursor(), "orphan-newest", "", "", days_old=1)
    db.execute("INSERT INTO fm_favorites VALUES ('f1', 'orphan-newest', 'made in an unsaved session')")
    project = Project()
    uuid = bind(dbm, monkeypatch, db, project)
    assert uuid not in ("orphan-old", "orphan-newest")
    assert project.variables["filterMate_db_project_uuid"] == uuid
    assert _count(db, "fm_projects", uuid) == 1


def test_the_same_unsaved_project_bound_again_keeps_its_id(db, monkeypatch):
    """Bound at its creation, then again when a layer is added or the panel opens: its favorites stay its own."""
    dbm = _load_database_manager()
    project = Project()
    first = bind(dbm, monkeypatch, db, project)
    _add_project(db.cursor(), "orphan-of-another-session", "", "", days_old=0)
    assert bind(dbm, monkeypatch, db, project) == first


def test_two_new_projects_have_two_ids(db, monkeypatch):
    """QgsProject.clear() empties the variables: the next new project has none, so an id of its own."""
    dbm = _load_database_manager()
    assert bind(dbm, monkeypatch, db, Project()) != bind(dbm, monkeypatch, db, Project())


def test_a_project_made_from_a_template_does_not_take_the_template_project_row(db, monkeypatch):
    """The template carries the variable of the project it was saved from: that row has a name, it is not reused."""
    dbm = _load_database_manager()
    _add_project(db.cursor(), "saved-row", "travel.qgz", "/work", days_old=0)
    uuid = bind(dbm, monkeypatch, db, Project(variables={"filterMate_db_project_uuid": "saved-row"}))
    assert uuid != "saved-row"


def test_a_saved_project_is_still_found_by_its_file(db, monkeypatch):
    dbm = _load_database_manager()
    _add_project(db.cursor(), "saved-row", "travel.qgz", "/work", days_old=0)
    assert bind(dbm, monkeypatch, db, Project("/work/travel.qgz")) == "saved-row"


def test_an_old_unsaved_row_with_favorites_is_kept(db):
    """Its favorites stay countable (count_orphan_favorites joins fm_projects); the rows without any go."""
    dbm = _load_database_manager()
    cur = db.cursor()
    _add_project(cur, "orphan-with-favorites", "", "", days_old=90)
    _add_project(cur, "orphan-empty", "", "", days_old=90)
    cur.execute("INSERT INTO fm_favorites VALUES ('f1', 'orphan-with-favorites', 'kept')")
    assert dbm.purge_stale_projects(cur, max_age_days=30) == 1
    assert _count(db, "fm_projects", "orphan-with-favorites") == 1
    assert _count(db, "fm_projects", "orphan-empty") == 0

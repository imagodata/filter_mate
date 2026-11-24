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
    conn.executescript(_DDL + "CREATE TABLE fm_favorites (id TEXT PRIMARY KEY, project_uuid TEXT NOT NULL, name TEXT);"
                       "CREATE TABLE fm_favorites_project_files (project_uuid TEXT PRIMARY KEY, file_ids TEXT,"
                       " updated_at TEXT);")
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


def _updated_days_ago(db, uuid):
    return db.execute("SELECT julianday('now') - julianday(_updated_at) FROM fm_projects WHERE project_id = ?",
                      (uuid,)).fetchone()[0]


def test_a_project_found_again_is_not_stale(db, monkeypatch):
    """A project stored in a database (no file: found by its variable) kept the _updated_at of its creation and was
    purged 30 days later, opened every day or not; a saved project is touched too."""
    dbm = _load_database_manager()
    _add_project(db.cursor(), "in-a-database", "", "", days_old=60)
    _add_project(db.cursor(), "saved-row", "travel.qgz", "/work", days_old=60)
    assert bind(dbm, monkeypatch, db, Project(variables={"filterMate_db_project_uuid": "in-a-database"})) == \
        "in-a-database"
    assert bind(dbm, monkeypatch, db, Project("/work/travel.qgz")) == "saved-row"
    assert _updated_days_ago(db, "in-a-database") < 0.01 and _updated_days_ago(db, "saved-row") < 0.01
    assert dbm.purge_stale_projects(db.cursor(), max_age_days=30) == 0


def test_the_purge_removes_what_was_kept_of_the_files_of_the_projects_purged(db):
    dbm = _load_database_manager()
    cur = db.cursor()
    _add_project(cur, "orphan-empty", "", "", days_old=90)
    _add_project(cur, "recent", "", "", days_old=1)
    cur.execute("INSERT INTO fm_favorites_project_files VALUES ('orphan-empty', '[\"f1\"]', '')")
    cur.execute("INSERT INTO fm_favorites_project_files VALUES ('recent', '[\"f2\"]', '')")
    assert dbm.purge_stale_projects(cur, max_age_days=30) == 1
    assert [row[0] for row in db.execute("SELECT project_uuid FROM fm_favorites_project_files")] == ["recent"]


def test_the_id_is_written_only_into_a_project_without_a_file(db, monkeypatch):
    """Read back only there; written into a .qgz, it marked a project from another computer modified at its
    opening (each computer writes its own id)."""
    dbm = _load_database_manager()
    saved = Project("/work/travel.qgz")
    bind(dbm, monkeypatch, db, saved)
    assert "filterMate_db_project_uuid" not in saved.variables
    _add_project(db.cursor(), "saved-row", "other.qgz", "/work", days_old=0)
    found = Project("/work/other.qgz")
    bind(dbm, monkeypatch, db, found)
    assert "filterMate_db_project_uuid" not in found.variables
    unsaved = Project()
    assert bind(dbm, monkeypatch, db, unsaved) == unsaved.variables["filterMate_db_project_uuid"]

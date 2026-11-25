# -*- coding: utf-8 -*-
"""
2026-09-14: each project open that created a new fm_projects row migrated the
previous orphan copies again and the .qgz backup restore added one more, so
the live database held five identical "YONNE" favorites. The migration now
drops an orphan identical (name, expression, layer) to a favorite already in
the target project, or to one migrated in the same batch.
"""
import sqlite3

import pytest

from core.services.favorites_migration_service import FavoritesMigrationService


def _db(tmp_path):
    path = str(tmp_path / "fm.sqlite")
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE fm_projects (project_id TEXT PRIMARY KEY, _created_at TEXT, _updated_at TEXT,
                                  project_name TEXT, project_path TEXT, project_settings TEXT);
        CREATE TABLE fm_favorites (id TEXT PRIMARY KEY, project_uuid TEXT, name TEXT, expression TEXT,
                                   layer_name TEXT, layer_id TEXT, layer_provider TEXT, description TEXT,
                                   tags TEXT, created_at TEXT, updated_at TEXT, use_count INTEGER);
        INSERT INTO fm_projects VALUES ('target', '', '', 'bdd.qgz', 'C:/Users/Simon', '{}');
        INSERT INTO fm_projects VALUES ('orphan1', '', '', '', '', '{}');
        INSERT INTO fm_projects VALUES ('orphan2', '', '', NULL, NULL, '{}');
    """)
    conn.commit()
    conn.close()
    return path


def _add(path, fav_id, project, name, expression="\"dep\" = '89'", layer="departement"):
    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO fm_favorites VALUES (?,?,?,?,?,'','postgres','','','','',0)",
                 (fav_id, project, name, expression, layer))
    conn.commit()
    conn.close()


def _rows(path):
    conn = sqlite3.connect(path)
    rows = conn.execute("SELECT id, project_uuid, name FROM fm_favorites ORDER BY id").fetchall()
    conn.close()
    return rows


@pytest.mark.unit
class TestOrphanMigrationDedupe:

    def test_identical_orphans_are_dropped_not_multiplied(self, tmp_path):
        path = _db(tmp_path)
        _add(path, "f-target", "target", "YONNE")          # restored from the .qgz backup
        _add(path, "f-o1", "orphan1", "YONNE")            # previous copies
        _add(path, "f-o2", "orphan2", "YONNE")
        _add(path, "f-o3", "orphan2", "50m", "\"w\" > 50", "troncon_de_route")  # a real orphan
        service = FavoritesMigrationService(path)

        count, names = service.migrate_orphan_favorites("target")

        assert (count, names) == (1, ["50m"])
        assert _rows(path) == [("f-o3", "target", "50m"), ("f-target", "target", "YONNE")]

    def test_duplicates_inside_the_batch_keep_one_copy(self, tmp_path):
        path = _db(tmp_path)
        _add(path, "f-o1", "orphan1", "YONNE")
        _add(path, "f-o2", "orphan2", "YONNE")
        service = FavoritesMigrationService(path)

        count, names = service.migrate_orphan_favorites("target")

        assert (count, names) == (1, ["YONNE"])
        assert _rows(path) == [("f-o1", "target", "YONNE")]

    def test_different_expression_is_not_a_duplicate(self, tmp_path):
        path = _db(tmp_path)
        _add(path, "f-target", "target", "YONNE", "\"dep\" = '89'")
        _add(path, "f-o1", "orphan1", "YONNE", "\"dep\" = '58'")
        service = FavoritesMigrationService(path)
        count, _ = service.migrate_orphan_favorites("target")
        assert count == 1
        assert len(_rows(path)) == 2


@pytest.mark.unit
class TestInProjectDedupe:

    def test_exact_copies_inside_a_project_are_reduced_to_one(self, tmp_path):
        path = _db(tmp_path)
        for i in range(5):
            _add(path, f"f-{i}", "target", "YONNE")
        _add(path, "f-other", "target", "YONNE", "\"dep\" = '58'")
        conn = sqlite3.connect(path)
        conn.execute("UPDATE fm_favorites SET use_count = 3 WHERE id = 'f-3'")
        conn.commit(); conn.close()
        service = FavoritesMigrationService(path)

        assert service.dedupe_project_favorites("target") == 4
        assert _rows(path) == [("f-3", "target", "YONNE"), ("f-other", "target", "YONNE")]
        assert service.dedupe_project_favorites("target") == 0

    def test_project_load_dedupes_before_migrating(self, tmp_path):
        path = _db(tmp_path)
        _add(path, "f-a", "target", "YONNE")
        _add(path, "f-b", "target", "YONNE")
        _add(path, "f-o", "orphan1", "50m", "\"w\" > 50", "troncon_de_route")
        service = FavoritesMigrationService(path)
        count, names = service.auto_migrate_on_project_load("target")
        assert (count, names) == (1, ["50m"])
        assert sorted(r[2] for r in _rows(path)) == ["50m", "YONNE"]


def test_fresh_database_without_favorites_table_is_quiet(tmp_path, caplog):
    """New profile: the database exists before fm_favorites does (found by the dock smoke test,
    which logged "no such table: fm_favorites" twice at ERROR on every first start)."""
    path = str(tmp_path / "fresh.db")
    sqlite3.connect(path).close()
    service = FavoritesMigrationService(path)
    with caplog.at_level("ERROR"):
        # FilterMateApp._auto_migrate_orphan_favorites calls these two first, then auto_migrate_on_project_load.
        assert service.dedupe_project_favorites("project-1") == 0
        assert service.count_orphan_favorites() == 0
        assert service.auto_migrate_on_project_load("project-1") == (0, [])
    assert not [record for record in caplog.records if record.levelname == "ERROR"]


def test_missing_database_file_is_not_created(tmp_path):
    path = tmp_path / "missing.db"
    service = FavoritesMigrationService(str(path))
    assert service.count_orphan_favorites() == 0
    assert not path.exists()


@pytest.mark.unit
def test_the_favorites_of_an_unsaved_project_opened_are_not_its_own_orphans(tmp_path):
    """Review of 2026-11-24: a project never saved has the shape of an orphan (no name, no path); its own favorites
    were taken for orphans, found identical to themselves, and deleted at the opening."""
    path = _db(tmp_path)
    _add(path, "f-own", "orphan1", "mine")
    _add(path, "f-other", "orphan2", "lost elsewhere", "\"w\" > 50", "troncon_de_route")
    count, names = FavoritesMigrationService(path).migrate_orphan_favorites("orphan1")
    assert ("f-own", "orphan1", "mine") in _rows(path)
    assert names == ["lost elsewhere"]


def test_the_cleanup_of_orphan_projects_keeps_the_project_on_screen(tmp_path):
    """2026-11-24: a project with no file yet has no name: the ★ cleanup removed the row of the project bound."""
    path = _db(tmp_path)
    deleted, ids = FavoritesMigrationService(path).cleanup_orphan_projects(current_project_uuid="orphan1")
    assert ids == ["orphan2"]
    conn = sqlite3.connect(path)
    assert [row[0] for row in conn.execute("SELECT project_id FROM fm_projects ORDER BY project_id")] == \
        ["orphan1", "target"]
    conn.close()


def _db_spatial(tmp_path):
    """A database whose fm_favorites carries the spatial columns, as the manager creates it."""
    path = str(tmp_path / "fm_spatial.sqlite")
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE fm_projects (project_id TEXT PRIMARY KEY, _created_at TEXT, _updated_at TEXT,
                                  project_name TEXT, project_path TEXT, project_settings TEXT);
        CREATE TABLE fm_favorites (id TEXT PRIMARY KEY, project_uuid TEXT, name TEXT, expression TEXT,
                                   layer_name TEXT, layer_id TEXT, layer_provider TEXT, description TEXT,
                                   tags TEXT, created_at TEXT, updated_at TEXT, use_count INTEGER,
                                   last_used_at TEXT, remote_layers TEXT, spatial_config TEXT, owner TEXT);
        INSERT INTO fm_projects VALUES ('target', '', '', 'bdd.qgz', 'C:/Users/Simon', '{}');
    """)
    conn.commit()
    conn.close()
    return path


def _add_spatial(path, fav_id, project, name, expression="\"dep\" = '89'", layer="departement",
                 spatial=None, remote=None):
    import json
    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO fm_favorites (id, project_uuid, name, expression, layer_name, spatial_config,"
                 " remote_layers, use_count) VALUES (?,?,?,?,?,?,?,0)",
                 (fav_id, project, name, expression, layer,
                  json.dumps(spatial, sort_keys=True) if spatial is not None else None,
                  json.dumps(remote, sort_keys=True) if remote is not None else None))
    conn.commit()
    conn.close()


@pytest.mark.unit
class TestDedupeComparesTheBuffer:
    """Audit 2026-11-24: the dedupe compared name, expression and layer: two favorites that only differed by
    buffer lost one, and the deletion went into the .qgz."""

    def test_favorites_that_differ_only_by_buffer_are_kept(self, tmp_path):
        path = _db_spatial(tmp_path)
        _add_spatial(path, "f-plain", "target", "zone")
        _add_spatial(path, "f-buffered", "target", "zone", spatial={"buffer_distance": 50})
        assert FavoritesMigrationService(path).dedupe_project_favorites("target") == 0
        conn = sqlite3.connect(path)
        try:
            assert sorted(row[0] for row in conn.execute("SELECT id FROM fm_favorites")) == \
                ["f-buffered", "f-plain"]
        finally:
            conn.close()

    def test_favorites_that_differ_only_by_remote_layers_are_kept(self, tmp_path):
        path = _db_spatial(tmp_path)
        _add_spatial(path, "f-local", "target", "zone")
        _add_spatial(path, "f-remote", "target", "zone", remote={"wfs": ["topp:states"]})
        assert FavoritesMigrationService(path).dedupe_project_favorites("target") == 0

    def test_byte_identical_copies_are_still_dropped(self, tmp_path):
        path = _db_spatial(tmp_path)
        _add_spatial(path, "f-1", "target", "zone", spatial={"buffer_distance": 50})
        _add_spatial(path, "f-2", "target", "zone", spatial={"buffer_distance": 50})
        assert FavoritesMigrationService(path).dedupe_project_favorites("target") == 1
        conn = sqlite3.connect(path)
        try:
            assert [row[0] for row in conn.execute("SELECT id FROM fm_favorites")] == ["f-1"]
        finally:
            conn.close()

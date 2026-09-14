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

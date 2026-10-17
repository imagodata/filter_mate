# -*- coding: utf-8 -*-
"""
Tests for the FilterMate temporary object naming rules and the SQLite cleanup.

The global "Clear Temp Tables" menu used to DROP every table matching
``LIKE 'fm_temp_%' OR LIKE 'mv_%'`` in the source databases of the project:
``_`` is a wildcard and LIKE ignores the case, so user tables such as
``mvt_reseau`` or ``MVoies`` were destroyed (and the GeoPackage metadata left
inconsistent). Only the names FilterMate really generates may go.

Pure Python: sqlite3 only.
"""
import sqlite3

import pytest

from infrastructure.database.temp_objects import (
    drop_filtermate_temp_tables,
    is_filtermate_pg_temp_object,
    is_filtermate_spatialite_temp_table,
    list_filtermate_temp_tables,
    pg_temp_object_like_patterns,
)

pytestmark = pytest.mark.unit

SID = "ab12cd34"


class TestSpatialiteNames:
    @pytest.mark.parametrize("name", [
        f"fm_temp_{SID}_routes_1234",
        f"mv_{SID}_routes_1234",
    ])
    def test_generated_names_match(self, name):
        assert is_filtermate_spatialite_temp_table(name)

    @pytest.mark.parametrize("name", [
        "mvt_reseau",           # '_' is not a wildcard
        "MVoies",               # LIKE is case-insensitive, the match is not
        "mv_reseau",            # user table with the legacy prefix but no session id
        "MV_ab12cd34_x",        # case differs
        "FM_TEMP_ab12cd34_x",
        "fmXtempXab12cd34_x",
        "fm_temp_",
        f"fm_temp_{SID}_",      # nothing after the session id
        f"fm_temp_{SID.upper()}_x",
        "fm_temp_routes",       # no session id
        "routes",
        f"idx_fm_temp_{SID}_x_geom",
    ])
    def test_user_names_do_not_match(self, name):
        assert not is_filtermate_spatialite_temp_table(name)

    def test_session_scope(self):
        assert is_filtermate_spatialite_temp_table(f"fm_temp_{SID}_x", SID)
        assert not is_filtermate_spatialite_temp_table("fm_temp_00000000_x", SID)
        assert is_filtermate_spatialite_temp_table(f"mv_{SID}_x", SID)

    def test_session_scope_is_literal(self):
        # session ids are matched literally, not as LIKE / glob patterns
        assert not is_filtermate_spatialite_temp_table(f"fm_temp_{SID}_x", "ab12c_34")
        assert not is_filtermate_spatialite_temp_table(f"fm_temp_{SID}_x", "*")


def _make_gpkg_like(path):
    """A minimal GeoPackage-shaped SQLite file with user layers + FM tables."""
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        CREATE TABLE gpkg_contents (table_name TEXT PRIMARY KEY, data_type TEXT);
        CREATE TABLE gpkg_geometry_columns (table_name TEXT, column_name TEXT);
        CREATE TABLE routes (fid INTEGER PRIMARY KEY, geom BLOB);
        CREATE TABLE mvt_reseau (fid INTEGER PRIMARY KEY, geom BLOB);
        CREATE TABLE MVoies (fid INTEGER PRIMARY KEY, geom BLOB);
        CREATE TABLE mv_reseau (fid INTEGER PRIMARY KEY, geom BLOB);
        CREATE TABLE fm_temp_cache (fid INTEGER PRIMARY KEY);
    """)
    for t in ("routes", "mvt_reseau", "MVoies", "mv_reseau", "fm_temp_cache"):
        conn.execute("INSERT INTO gpkg_contents VALUES (?, 'features')", (t,))
    conn.execute(f'CREATE TABLE "fm_temp_{SID}_routes" AS SELECT fid FROM routes')
    conn.execute(f'CREATE TABLE "mv_{SID}_old" AS SELECT fid FROM routes')
    conn.execute('CREATE TABLE "fm_temp_11111111_other" AS SELECT fid FROM routes')
    conn.execute(f'CREATE VIRTUAL TABLE "idx_fm_temp_{SID}_routes_geometry" '
                 f'USING rtree(id, minx, maxx, miny, maxy)')
    conn.commit()
    conn.close()


def _tables(path):
    conn = sqlite3.connect(str(path))
    try:
        return {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


class TestListAndDrop:
    def test_only_generated_tables_are_listed(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        found = list_filtermate_temp_tables(str(db))
        assert sorted(found) == sorted([
            f"fm_temp_{SID}_routes", f"mv_{SID}_old", "fm_temp_11111111_other"])

    def test_session_scoped_listing(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        assert sorted(list_filtermate_temp_tables(str(db), SID)) == sorted(
            [f"fm_temp_{SID}_routes", f"mv_{SID}_old"])

    def test_registered_layers_are_never_listed(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        conn = sqlite3.connect(str(db))
        # a user layer that happens to look like a FilterMate table
        conn.execute(f'CREATE TABLE "fm_temp_{SID}_mine" (fid INTEGER PRIMARY KEY)')
        conn.execute(f"INSERT INTO gpkg_contents VALUES ('fm_temp_{SID}_mine', 'features')")
        conn.commit()
        conn.close()
        assert f"fm_temp_{SID}_mine" not in list_filtermate_temp_tables(str(db))

    def test_listing_does_not_modify_the_file(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        before = db.read_bytes()
        list_filtermate_temp_tables(str(db))
        assert db.read_bytes() == before

    def test_drop_removes_only_filtermate_tables_and_their_index(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        dropped = drop_filtermate_temp_tables(str(db))
        assert sorted(dropped) == sorted(
            [f"fm_temp_{SID}_routes", f"mv_{SID}_old", "fm_temp_11111111_other"])
        remaining = _tables(db)
        assert {"routes", "mvt_reseau", "MVoies", "mv_reseau", "fm_temp_cache",
                "gpkg_contents", "gpkg_geometry_columns"} <= remaining
        assert not [t for t in remaining if t.startswith(("fm_temp_" + SID, "idx_fm_temp_"))]
        assert f"mv_{SID}_old" not in remaining
        conn = sqlite3.connect(str(db))
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # gpkg_contents untouched: no orphan, no missing row
        assert conn.execute("SELECT COUNT(*) FROM gpkg_contents").fetchone()[0] == 5
        conn.close()

    def test_drop_by_session(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        dropped = drop_filtermate_temp_tables(str(db), session_id=SID)
        assert sorted(dropped) == sorted([f"fm_temp_{SID}_routes", f"mv_{SID}_old"])
        assert "fm_temp_11111111_other" in _tables(db)

    def test_drop_refuses_names_that_are_not_generated(self, tmp_path):
        """An explicit list is re-validated: user tables are never dropped."""
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        dropped = drop_filtermate_temp_tables(
            str(db), tables=["mvt_reseau", "MVoies", "routes", "fm_temp_cache",
                             f"fm_temp_{SID}_routes"])
        assert dropped == [f"fm_temp_{SID}_routes"]
        assert {"mvt_reseau", "MVoies", "routes", "fm_temp_cache"} <= _tables(db)

    def test_missing_file_is_a_noop(self, tmp_path):
        missing = str(tmp_path / "nope.gpkg")
        assert list_filtermate_temp_tables(missing) == []
        assert drop_filtermate_temp_tables(missing) == []
        assert not (tmp_path / "nope.gpkg").exists()

    def test_not_a_database_is_a_noop(self, tmp_path):
        junk = tmp_path / "junk.db"
        junk.write_text("this is not sqlite")
        assert list_filtermate_temp_tables(str(junk)) == []
        assert drop_filtermate_temp_tables(str(junk)) == []


class TestPostgresNames:
    @pytest.mark.parametrize("kind,schema,name", [
        ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc"),
        ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc_dump"),
        ("matview", "ref", "fm_temp_src_0123abcd"),
        ("matview", "filtermate_temp", f"fm_temp_chain_{SID}_0123abcd"),
        ("table", "ref", "fm_temp_buf_communes_0123abcd"),
        ("table", "filtermate_temp", "fm_temp_src_sel_0123abcd"),
        ("table", "filter_mate_temp", "fm_temp_tbl_x"),
        # legacy prefixes: only inside FilterMate's own schemas
        ("matview", "filtermate_temp", "fm_mv_abc"),
        ("matview", "filter_mate_temp", "filtermate_mv_src_sel_abc"),
        ("table", "filtermate_temp", "fm_buf_x_0123abcd"),
    ])
    def test_filtermate_objects(self, kind, schema, name):
        assert is_filtermate_pg_temp_object(kind, schema, name)

    @pytest.mark.parametrize("kind,schema,name", [
        ("table", "public", "filtermate_catalog"),     # was matched by filtermate\_%
        ("table", "public", "fm_buf_user"),            # legacy prefix outside our schemas
        ("matview", "public", "fm_mv_user"),
        ("matview", "public", "filtermate_mv_user"),
        ("table", "public", "FM_TEMP_BUF_X"),
        ("table", "public", "fmXtempXbufXx"),
        ("table", "public", "fm_temp_"),
        ("table", "public", "fm_temp_cache"),          # no known kind
        ("table", "ref", "fm_temp_buf_"),
        ("table", "ref", "mv_users"),
    ])
    def test_user_objects(self, kind, schema, name):
        assert not is_filtermate_pg_temp_object(kind, schema, name)

    def test_like_patterns_escape_the_underscore(self):
        patterns = pg_temp_object_like_patterns("table")
        assert patterns
        assert all("\\_" in p and p.endswith("%") for p in patterns)
        assert not any(p.startswith("filtermate\\_%") for p in patterns)

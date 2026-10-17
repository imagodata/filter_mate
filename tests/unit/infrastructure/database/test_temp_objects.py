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
    sqlite_readonly_uri,
)

pytestmark = pytest.mark.unit

SID = "ab12cd34"


class TestSpatialiteNames:
    @pytest.mark.parametrize("name", [
        f"fm_temp_{SID}_routes_1234",
        f"fm_temp_{SID}_x",
    ])
    def test_generated_names_match(self, name):
        assert is_filtermate_spatialite_temp_table(name)

    @pytest.mark.parametrize("name", [
        "mvt_reseau",           # '_' is not a wildcard
        "MVoies",               # LIKE is case-insensitive, the match is not
        "mv_reseau",
        f"mv_{SID}_old",        # legacy name: nothing creates it, and mv_20231231_bati is a user table
        "mv_20231231_bati",     # 8 digits are valid hexadecimal
        "MV_ab12cd34_x",
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
        assert not is_filtermate_spatialite_temp_table(f"mv_{SID}_x", SID)

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
        CREATE TABLE mv_20231231_bati (fid INTEGER PRIMARY KEY, geom BLOB);
        CREATE TABLE fm_temp_cache (fid INTEGER PRIMARY KEY);
    """)
    for t in ("routes", "mvt_reseau", "MVoies", "mv_reseau", "fm_temp_cache"):
        conn.execute("INSERT INTO gpkg_contents VALUES (?, 'features')", (t,))
    conn.execute(f'CREATE TABLE "fm_temp_{SID}_routes" AS SELECT fid FROM routes')
    conn.execute(f'CREATE TABLE "mv_{SID}_old" AS SELECT fid FROM routes')
    conn.execute('CREATE TABLE "fm_temp_11111111_other" AS SELECT fid FROM routes')
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
        assert sorted(found) == sorted([f"fm_temp_{SID}_routes", "fm_temp_11111111_other"])

    def test_session_scoped_listing(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        assert list_filtermate_temp_tables(str(db), SID) == [f"fm_temp_{SID}_routes"]

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
        assert f"fm_temp_{SID}_mine" not in list_filtermate_temp_tables(str(db), SID)

    def test_listing_does_not_modify_the_file(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        before = db.read_bytes()
        list_filtermate_temp_tables(str(db))
        assert db.read_bytes() == before

    def test_drop_removes_only_filtermate_tables(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        dropped = drop_filtermate_temp_tables(str(db))
        assert sorted(dropped) == sorted([f"fm_temp_{SID}_routes", "fm_temp_11111111_other"])
        remaining = _tables(db)
        assert {"routes", "mvt_reseau", "MVoies", "mv_reseau", "mv_20231231_bati", f"mv_{SID}_old",
                "fm_temp_cache", "gpkg_contents", "gpkg_geometry_columns"} <= remaining
        conn = sqlite3.connect(str(db))
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # gpkg_contents untouched: no orphan, no missing row
        assert conn.execute("SELECT COUNT(*) FROM gpkg_contents").fetchone()[0] == 5
        conn.close()

    def test_drop_by_session(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        dropped = drop_filtermate_temp_tables(str(db), session_id=SID)
        assert dropped == [f"fm_temp_{SID}_routes"]
        assert "fm_temp_11111111_other" in _tables(db)

    def test_drop_refuses_names_that_are_not_generated(self, tmp_path):
        """An explicit list is re-validated: user tables are never dropped."""
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        dropped = drop_filtermate_temp_tables(
            str(db), tables=["mvt_reseau", "MVoies", "routes", "fm_temp_cache", "mv_20231231_bati",
                             f"fm_temp_{SID}_routes"])
        assert dropped == [f"fm_temp_{SID}_routes"]
        assert {"mvt_reseau", "MVoies", "routes", "fm_temp_cache", "mv_20231231_bati"} <= _tables(db)

    def test_a_table_a_layer_is_filtered_through_is_kept(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        subsets = [f'"fid" IN (SELECT "fid" FROM fm_temp_{SID}_routes)', "", "fid > 3"]
        assert list_filtermate_temp_tables(str(db), exclude_referenced_by=subsets) == ["fm_temp_11111111_other"]
        assert drop_filtermate_temp_tables(str(db), exclude_referenced_by=subsets) == ["fm_temp_11111111_other"]
        assert f"fm_temp_{SID}_routes" in _tables(db)

    def test_a_longer_table_name_is_not_taken_for_the_one_in_use(self, tmp_path):
        db = tmp_path / "data.gpkg"
        _make_gpkg_like(db)
        conn = sqlite3.connect(str(db))
        conn.execute(f'CREATE TABLE "fm_temp_{SID}_routes_2" (fid INTEGER)')
        conn.commit()
        conn.close()
        subsets = [f'"fid" IN (SELECT "fid" FROM "fm_temp_{SID}_routes")']
        assert f"fm_temp_{SID}_routes_2" in list_filtermate_temp_tables(str(db), exclude_referenced_by=subsets)

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


def _make_native_spatialite(path):
    """A native Spatialite-shaped file: metadata tables + two temp tables with their R-tree index."""
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        CREATE TABLE geometry_columns (f_table_name TEXT, f_geometry_column TEXT, geometry_type INT,
                                       coord_dimension INT, srid INT, spatial_index_enabled INT);
        CREATE TABLE geometry_columns_statistics (f_table_name TEXT, f_geometry_column TEXT, last_verified TEXT);
        CREATE TABLE geometry_columns_field_infos (f_table_name TEXT, f_geometry_column TEXT, ordinal INT);
        CREATE TABLE geometry_columns_time (f_table_name TEXT, f_geometry_column TEXT, last_insert TEXT);
        CREATE TABLE geometry_columns_auth (f_table_name TEXT, f_geometry_column TEXT, read_only INT);
        CREATE TABLE roads (pk INTEGER PRIMARY KEY, geom BLOB);
    """)
    conn.execute("INSERT INTO geometry_columns VALUES ('roads', 'geom', 2, 2, 2154, 1)")
    for table in (f"fm_temp_{SID}_x", f"fm_temp_{SID}_x_y"):
        conn.execute(f'CREATE TABLE "{table}" (pk INTEGER, geom BLOB)')
        conn.execute(f'CREATE VIRTUAL TABLE "idx_{table}_geom" USING rtree(id, minx, maxx, miny, maxy)')
        conn.execute("INSERT INTO geometry_columns VALUES (?, 'geom', 2, 2, 2154, 1)", (table.lower(),))
        for metadata in ("geometry_columns_statistics", "geometry_columns_field_infos",
                         "geometry_columns_time", "geometry_columns_auth"):
            conn.execute(f"INSERT INTO {metadata} VALUES (?, 'geom', NULL)", (table,))
    conn.commit()
    conn.close()


def _rows(path, table):
    conn = sqlite3.connect(str(path))
    try:
        return sorted(r[0] for r in conn.execute(f"SELECT f_table_name FROM {table}"))
    finally:
        conn.close()


class TestNativeSpatialite:
    def test_declared_tables_are_not_candidates_of_the_all_sessions_cleanup(self, tmp_path):
        db = tmp_path / "native.sqlite"
        _make_native_spatialite(db)
        assert list_filtermate_temp_tables(str(db)) == []
        assert drop_filtermate_temp_tables(str(db)) == []
        assert f"fm_temp_{SID}_x" in _tables(db)

    def test_the_running_session_may_drop_its_own_declared_tables(self, tmp_path):
        db = tmp_path / "native.sqlite"
        _make_native_spatialite(db)
        assert sorted(list_filtermate_temp_tables(str(db), SID)) == [f"fm_temp_{SID}_x", f"fm_temp_{SID}_x_y"]

    def test_dropping_a_table_takes_its_own_index_and_metadata_only(self, tmp_path):
        db = tmp_path / "native.sqlite"
        _make_native_spatialite(db)

        dropped = drop_filtermate_temp_tables(str(db), session_id=SID, tables=[f"fm_temp_{SID}_x"])

        assert dropped == [f"fm_temp_{SID}_x"]
        left = _tables(db)
        assert f"idx_fm_temp_{SID}_x_geom" not in left
        # "<table>_y" is another table: its index (same prefix) must survive
        assert f"idx_fm_temp_{SID}_x_y_geom" in left and f"fm_temp_{SID}_x_y" in left
        for metadata in ("geometry_columns", "geometry_columns_statistics", "geometry_columns_field_infos",
                         "geometry_columns_time", "geometry_columns_auth"):
            rows = _rows(db, metadata)
            assert f"fm_temp_{SID}_x".lower() not in [r.lower() for r in rows], metadata
            assert f"fm_temp_{SID}_x_y".lower() in [r.lower() for r in rows], metadata
        assert "roads" in _rows(db, "geometry_columns")

    def test_dropping_everything_leaves_no_orphan_metadata(self, tmp_path):
        db = tmp_path / "native.sqlite"
        _make_native_spatialite(db)

        assert len(drop_filtermate_temp_tables(str(db), session_id=SID)) == 2

        assert _rows(db, "geometry_columns") == ["roads"]
        for metadata in ("geometry_columns_statistics", "geometry_columns_time", "geometry_columns_auth"):
            assert _rows(db, metadata) == []
        assert not [t for t in _tables(db) if t.startswith(("fm_temp_", "idx_fm_temp_"))]


class TestReadonlyUri:
    @pytest.mark.parametrize("path, expected", [
        ("/tmp/a.db", "file:///tmp/a.db?mode=ro"),
        ("/tmp/my data/é.db", "file:///tmp/my%20data/%C3%A9.db?mode=ro"),
        ("/tmp/q?x#y.db", "file:///tmp/q%3Fx%23y.db?mode=ro"),
        ("C:\\data\\base.gpkg", "file:///C:/data/base.gpkg?mode=ro"),
        ("C:/data/with space.gpkg", "file:///C:/data/with%20space.gpkg?mode=ro"),
        ("\\\\server\\share\\dir\\a.gpkg", "file:////server/share/dir/a.gpkg?mode=ro"),
        ("//server/share/a b.gpkg", "file:////server/share/a%20b.gpkg?mode=ro"),
    ])
    def test_shapes(self, path, expected):
        assert sqlite_readonly_uri(path) == expected

    def test_the_uri_opens_a_real_file_read_only(self, tmp_path):
        db = tmp_path / "with space" / "é?.db"
        db.parent.mkdir()
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE t (a)")
        conn.commit()
        conn.close()
        ro = sqlite3.connect(sqlite_readonly_uri(str(db)), uri=True)
        assert ro.execute("SELECT count(*) FROM sqlite_master").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            ro.execute("CREATE TABLE u (a)")
        ro.close()


class TestPostgresNames:
    @pytest.mark.parametrize("kind,schema,name", [
        ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc"),
        ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc_dump"),
        ("matview", "ref", "fm_temp_src_0123abcd"),
        ("matview", "filtermate_temp", f"fm_temp_chain_{SID}_0123abcd"),
        ("table", "ref", "fm_temp_buf_communes_0123abcd"),
        # the buffer table carries the name of its source table, whatever it is
        ("table", "ref", "fm_temp_buf_routes-2024_ab12cd34"),
        ("table", "ref", "fm_temp_buf_Routes Nat_ab12cd34"),
        ("table", "ref", "fm_temp_buf_Bâtiments_ab12cd34"),
        ("table", "ref", 'fm_temp_buf_a"b_ab12cd34'),
        ("table", "filtermate_temp", "fm_temp_src_sel_0123abcd"),
        ("table", "filter_mate_temp", "fm_temp_tbl_x"),
        # legacy prefixes: only inside FilterMate's own schemas
        ("matview", "filtermate_temp", "fm_mv_abc"),
        ("matview", "filter_mate_temp", "filtermate_mv_src_sel_abc"),
        ("matview", "filter_mate_temp", f"mv_{SID}_legacy"),
        ("table", "filtermate_temp", "fm_buf_x_0123abcd"),
    ])
    def test_filtermate_objects(self, kind, schema, name):
        assert is_filtermate_pg_temp_object(kind, schema, name)

    @pytest.mark.parametrize("kind,schema,name", [
        ("table", "public", "filtermate_catalog"),     # was matched by filtermate\_%
        ("table", "public", "fm_buf_user"),            # legacy prefix outside our schemas
        ("matview", "public", "fm_mv_user"),
        ("matview", "public", "filtermate_mv_user"),
        ("matview", "public", f"mv_{SID}_bati"),       # legacy session view outside our schemas
        ("matview", "filter_mate_temp", "mv_users"),
        ("table", "filter_mate_temp", f"mv_{SID}_x"),  # legacy session names are views only
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

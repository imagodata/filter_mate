# -*- coding: utf-8 -*-
"""
Spatialite temp tables: the table created and the table the subset reads are one.

``manage_spatialite_subset`` created ``<session>_<name>`` in the user's
Spatialite / GeoPackage file while ``apply_spatialite_subset`` put the subset
``"pk" IN (SELECT "pk" FROM fm_temp_<session>_<name>)`` on the layer: the
filter pointed at a table that did not exist, and the one that existed did not
carry the ``fm_temp_`` prefix the cleanup looks for, so it was never removed.

The table has to live in the layer's own database: the subset is evaluated by
the layer's provider on its own connection, which cannot see another file.
"""
import importlib.util
import sqlite3
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[5]
_PKG = "fm_sl_naming_test"
SID = "ab12cd34"


def _module(name, path=None, **attrs):
    mod = types.ModuleType(name)
    if path is not None:
        mod.__path__ = [str(path)]
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


@pytest.fixture(scope="module")
def executor():
    full = f"{_PKG}.adapters.backends.spatialite.filter_executor"
    _module(_PKG, _ROOT)
    _module(f"{_PKG}.adapters", _ROOT / "adapters")
    _module(f"{_PKG}.adapters.backends", _ROOT / "adapters" / "backends")
    _module(f"{_PKG}.adapters.backends.spatialite", _ROOT / "adapters" / "backends" / "spatialite")
    _module(f"{_PKG}.adapters.repositories", _ROOT / "adapters" / "repositories")
    _module(f"{_PKG}.adapters.repositories.history_repository", HistoryRepository=MagicMock())
    _module(f"{_PKG}.infrastructure", _ROOT / "infrastructure")
    _module(f"{_PKG}.infrastructure.database", _ROOT / "infrastructure" / "database")
    for name in ("temp_objects",):
        spec = importlib.util.spec_from_file_location(
            f"{_PKG}.infrastructure.database.{name}", _ROOT / "infrastructure" / "database" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    created = MagicMock(return_value=True)
    _module(f"{_PKG}.infrastructure.database.sql_utils",
            create_temp_spatialite_table=created, sanitize_sql_identifier=lambda name: name)
    spec = importlib.util.spec_from_file_location(full, _ROOT / "adapters" / "backends" / "spatialite" / "filter_executor.py")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = f"{_PKG}.adapters.backends.spatialite"
    sys.modules[full] = module
    spec.loader.exec_module(module)
    module.created = created
    return module


class _Layer:
    def id(self):
        return "routes_1234"


def _manage(executor, session_id, name="routes_1234"):
    executor.created.reset_mock()
    executor.build_spatialite_query = lambda **kwargs: "SELECT fid, geom FROM routes"
    queued = []
    ok = executor.manage_spatialite_subset(
        layer=_Layer(), sql_subset_string="1=1", primary_key_name="fid", geom_key_name="geom",
        name=name, session_id=session_id, project_uuid=None,
        queue_subset_func=lambda layer, subset: queued.append(subset),
        get_spatialite_datasource_func=lambda layer: ("/data/reseau.gpkg", "routes", 4326, True))
    return ok, queued


class TestTableAndSubsetAgree:
    def test_created_table_is_the_one_the_subset_reads(self, executor):
        ok, queued = _manage(executor, SID)

        assert ok is True
        created_name = executor.created.call_args.kwargs["table_name"]
        assert created_name == f"fm_temp_{SID}_routes_1234"
        assert queued == [f'"fid" IN (SELECT "fid" FROM {created_name})']

    def test_without_a_session_the_prefix_is_still_there(self, executor):
        ok, queued = _manage(executor, None)

        created_name = executor.created.call_args.kwargs["table_name"]
        assert created_name == "fm_temp_routes_1234"
        assert queued == [f'"fid" IN (SELECT "fid" FROM {created_name})']

    def test_the_created_name_is_one_the_cleanup_recognises(self, executor):
        from importlib import import_module
        temp_objects = import_module(f"{_PKG}.infrastructure.database.temp_objects")
        _manage(executor, SID)
        assert temp_objects.is_filtermate_spatialite_temp_table(
            executor.created.call_args.kwargs["table_name"], SID)


class TestSessionCleanup:
    def _db(self, tmp_path):
        path = tmp_path / "reseau.gpkg"
        conn = sqlite3.connect(str(path))
        conn.executescript(f"""
            CREATE TABLE gpkg_contents (table_name TEXT);
            CREATE TABLE routes (fid INTEGER);
            CREATE TABLE "fm_temp_{SID}_routes" (fid INTEGER);
            CREATE TABLE "mv_{SID}_old" (fid INTEGER);
            CREATE TABLE "fm_temp_11111111_other" (fid INTEGER);
            CREATE TABLE "fmXtempX{SID}Xlookalike" (fid INTEGER);
            CREATE TABLE "MV_{SID}_lookalike" (fid INTEGER);
        """)
        conn.commit()
        conn.close()
        return path

    def _names(self, path):
        conn = sqlite3.connect(str(path))
        try:
            return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()

    def test_only_the_session_tables_go(self, executor, tmp_path):
        path = self._db(tmp_path)

        assert executor.cleanup_session_temp_tables(str(path), SID) == 1

        left = self._names(path)
        # mv_<session>_* is no longer ours in a user's file (mv_20231231_bati is a user table)
        assert {"routes", "fm_temp_11111111_other", f"fmXtempX{SID}Xlookalike", f"MV_{SID}_lookalike",
                f"mv_{SID}_old"} <= left
        assert f"fm_temp_{SID}_routes" not in left

    def test_no_session_id_is_a_noop_not_a_type_error(self, executor, tmp_path):
        """The reset action calls it with the database only."""
        path = self._db(tmp_path)

        assert executor.cleanup_session_temp_tables(str(path)) == 0
        assert f"fm_temp_{SID}_routes" in self._names(path)


class TestCreateTempTableSql:
    """create_temp_spatialite_table quotes the table name and formats its index call."""

    @pytest.fixture
    def recorded(self, monkeypatch):
        spec = importlib.util.spec_from_file_location(
            "infrastructure.database._sql_utils_quote_test", _ROOT / "infrastructure" / "database" / "sql_utils.py",
            submodule_search_locations=None)
        module = importlib.util.module_from_spec(spec)
        module.__package__ = "infrastructure.database"
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        statements = []

        class _Cursor:
            def execute(self, sql, *args):
                statements.append(" ".join(sql.split()))

        class _Connection:
            def enable_load_extension(self, flag):
                pass

            def load_extension(self, name):
                pass

            def cursor(self):
                return _Cursor()

            def commit(self):
                pass

            def close(self):
                pass

        monkeypatch.setattr(sqlite3, "connect", lambda path: _Connection())
        return module, statements

    def test_table_name_is_quoted(self, recorded):
        module, statements = recorded

        assert module.create_temp_spatialite_table("/data/x.sqlite", f"fm_temp_{SID}_routes", "SELECT 1") is True

        assert f'DROP TABLE IF EXISTS "fm_temp_{SID}_routes"' in statements
        assert f'CREATE TABLE "fm_temp_{SID}_routes" AS SELECT 1' in statements

    def test_a_hostile_name_cannot_close_the_quote(self, recorded):
        module, statements = recorded

        module.create_temp_spatialite_table("/data/x.sqlite", 'a"; DROP TABLE users; --', "SELECT 1")

        drop = statements[0]
        assert drop.startswith('DROP TABLE IF EXISTS "') and drop.endswith('"')
        assert ";" not in drop

    def test_by_default_the_table_is_not_declared_as_a_layer(self, recorded):
        """The subset reads the primary key only: no geometry_columns row, trigger or R-tree in the user's file."""
        module, statements = recorded

        module.create_temp_spatialite_table("/data/x.sqlite", f"fm_temp_{SID}_routes", "SELECT 1", "geom", 2154)

        assert not [s for s in statements if "RecoverGeometryColumn" in s or "CreateSpatialIndex" in s]

    def test_spatial_index_call_is_formatted_when_asked_for(self, recorded):
        module, statements = recorded

        module.create_temp_spatialite_table("/data/x.sqlite", f"fm_temp_{SID}_routes", "SELECT 1", "geom", 2154,
                                            register_geometry=True)

        index = [s for s in statements if "CreateSpatialIndex" in s]
        assert index and "{" not in index[0]
        assert f"CreateSpatialIndex( '{'fm_temp_' + SID + '_routes'}', 'geom' )" in index[0]

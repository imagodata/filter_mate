# -*- coding: utf-8 -*-
"""
BackendController: the "Clear Temp Tables" cleanups only remove what FilterMate made.

The global cleanup used to run ``DROP TABLE`` on every ``name LIKE 'fm_temp_%'
OR name LIKE 'mv_%'`` of the source GeoPackages of the project, without asking
("_" is a wildcard and LIKE ignores the case: ``mvt_reseau`` and ``MVoies``
were lost, ``gpkg_contents`` left orphaned), and ``DROP ... CASCADE`` on loose
``filtermate\\_%`` patterns in every PostgreSQL schema.

The controller is loaded by path under a private package, Qt / QGIS / the base
controller are stubs, the name rules (``temp_objects``) are the real module.
"""
import importlib.util
import pathlib
import sqlite3
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_backend_cleanup_test"
SID = "ab12cd34"


class FakeLayer:
    def __init__(self, source, provider="ogr"):
        self._source, self._provider = source, provider

    def providerType(self):
        return self._provider

    def source(self):
        return self._source


class FakeProject:
    layers = []

    @classmethod
    def instance(cls):
        return cls

    @classmethod
    def mapLayers(cls):
        return {str(i): layer for i, layer in enumerate(cls.layers)}


class FakeMessageBox:
    """Records the dialog; the answer is class-level."""

    answer = None
    last = None

    class Icon:
        Warning = "warning"

    class StandardButton:
        Yes = 0x4000
        No = 0x10000

    def __init__(self, parent=None):
        FakeMessageBox.last = self
        self.default = None
        self.text = self.details = ""

    def setIcon(self, icon):
        pass

    def setWindowTitle(self, title):
        pass

    def setText(self, text):
        self.text = text

    def setDetailedText(self, text):
        self.details = text

    def setStandardButtons(self, buttons):
        pass

    def setDefaultButton(self, button):
        self.default = button

    def exec(self):
        return FakeMessageBox.answer


class BaseController:
    def __init__(self, dockwidget, filter_service=None, signal_manager=None):
        self._dockwidget = dockwidget

    @property
    def dockwidget(self):
        return self._dockwidget


@pytest.fixture
def feedback():
    return types.SimpleNamespace(show_info=MagicMock(), show_success=MagicMock(),
                                 show_warning=MagicMock())


@pytest.fixture
def backend_module(monkeypatch, feedback):
    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtcore.pyqtSignal = lambda *args: MagicMock()
    qtwidgets = types.ModuleType("qgis.PyQt.QtWidgets")
    qtwidgets.QMenu = MagicMock()
    qtwidgets.QLabel = MagicMock()
    qtwidgets.QMessageBox = FakeMessageBox
    qgis_core = types.ModuleType("qgis.core")
    qgis_core.QgsVectorLayer = FakeLayer
    qgis_core.QgsProject = FakeProject
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", qtcore)
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtWidgets", qtwidgets)
    monkeypatch.setitem(sys.modules, "qgis.core", qgis_core)
    for name in ("", ".ui", ".ui.controllers", ".infrastructure", ".infrastructure.database"):
        package = types.ModuleType(_PKG + name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, _PKG + name, package)
    base = types.ModuleType(f"{_PKG}.ui.controllers.base_controller")
    base.BaseController = BaseController
    monkeypatch.setitem(sys.modules, base.__name__, base)
    sql_utils = types.ModuleType(f"{_PKG}.infrastructure.database.sql_utils")
    sql_utils.sanitize_sql_identifier = lambda value: value
    monkeypatch.setitem(sys.modules, sql_utils.__name__, sql_utils)
    fb = types.ModuleType(f"{_PKG}.infrastructure.feedback")
    fb.show_info, fb.show_success, fb.show_warning = (
        feedback.show_info, feedback.show_success, feedback.show_warning)
    monkeypatch.setitem(sys.modules, fb.__name__, fb)
    for name, path in (("infrastructure.database.temp_objects", "infrastructure/database/temp_objects.py"),
                       ("ui.controllers.backend_controller", "ui/controllers/backend_controller.py")):
        spec = importlib.util.spec_from_file_location(f"{_PKG}.{name}", _ROOT / path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, spec.name, module)
        spec.loader.exec_module(module)
        last = module
    FakeProject.layers = []
    FakeMessageBox.answer = None
    FakeMessageBox.last = None
    return last


@pytest.fixture
def controller(backend_module):
    dock = MagicMock()
    dock.tr = lambda text: text
    dock._app_ref = types.SimpleNamespace(session_id=SID)
    controller = backend_module.BackendController(dock)
    # no PostgreSQL connection unless a test installs one
    controller.get_pg_session_context = lambda: (None, SID, "filter_mate_temp", None)
    return controller


def _make_gpkg(path):
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        CREATE TABLE gpkg_contents (table_name TEXT PRIMARY KEY, data_type TEXT);
        CREATE TABLE gpkg_geometry_columns (table_name TEXT, column_name TEXT);
        CREATE TABLE routes (fid INTEGER PRIMARY KEY, geom BLOB);
        CREATE TABLE mvt_reseau (fid INTEGER PRIMARY KEY, geom BLOB);
        CREATE TABLE MVoies (fid INTEGER PRIMARY KEY, geom BLOB);
    """)
    for t in ("routes", "mvt_reseau", "MVoies"):
        conn.execute("INSERT INTO gpkg_contents VALUES (?, 'features')", (t,))
    conn.execute(f'CREATE TABLE "fm_temp_{SID}_routes" AS SELECT fid FROM routes')
    conn.execute('CREATE TABLE "fm_temp_11111111_old" AS SELECT fid FROM routes')
    conn.commit()
    conn.close()


def _tables(path):
    conn = sqlite3.connect(str(path))
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


@pytest.fixture
def gpkg(tmp_path):
    db = tmp_path / "reseau.gpkg"
    _make_gpkg(db)
    FakeProject.layers = [FakeLayer(f"{db}|layername=routes"),
                          FakeLayer(f"{db}|layername=mvt_reseau"),
                          FakeLayer("/data/zones.shp")]
    return db


class TestSpatialiteGlobalCleanup:
    def test_user_tables_survive(self, controller, gpkg):
        count = controller.cleanup_temp_tables_global()
        remaining = _tables(gpkg)
        assert count == 2
        assert {"routes", "mvt_reseau", "MVoies", "gpkg_contents"} <= remaining
        assert not [t for t in remaining if t.startswith("fm_temp_")]
        conn = sqlite3.connect(str(gpkg))
        assert conn.execute("SELECT COUNT(*) FROM gpkg_contents").fetchone()[0] == 3
        conn.close()

    def test_session_cleanup_keeps_other_sessions(self, controller, gpkg):
        assert controller._cleanup_spatialite_project_tables() == 1
        remaining = _tables(gpkg)
        assert "fm_temp_11111111_old" in remaining
        assert f"fm_temp_{SID}_routes" not in remaining

    def test_candidates_are_listed_without_touching_anything(self, controller, gpkg):
        before = gpkg.read_bytes()
        candidates = controller.collect_global_cleanup_candidates()
        assert sorted(candidates["spatialite"][str(gpkg)]) == [
            "fm_temp_11111111_old", f"fm_temp_{SID}_routes"]
        assert gpkg.read_bytes() == before

    def test_confirmed_list_is_revalidated(self, controller, gpkg):
        """A candidate list naming user tables does not drop them."""
        candidates = {"spatialite": {str(gpkg): ["mvt_reseau", "MVoies", f"fm_temp_{SID}_routes"]},
                      "postgresql": []}
        assert controller.cleanup_temp_tables_global(candidates) == 1
        assert {"mvt_reseau", "MVoies", "routes"} <= _tables(gpkg)


class TestConfirmation:
    def test_refusing_deletes_nothing(self, controller, gpkg, feedback):
        FakeMessageBox.answer = FakeMessageBox.StandardButton.No
        before = gpkg.read_bytes()
        controller.run_global_cleanup_with_confirmation()
        assert gpkg.read_bytes() == before
        feedback.show_success.assert_not_called()

    def test_accepting_deletes_the_listed_objects(self, controller, gpkg, feedback):
        FakeMessageBox.answer = FakeMessageBox.StandardButton.Yes
        controller.run_global_cleanup_with_confirmation()
        assert not [t for t in _tables(gpkg) if t.startswith("fm_temp_")]
        assert {"routes", "mvt_reseau", "MVoies"} <= _tables(gpkg)
        feedback.show_success.assert_called_once()

    def test_dialog_lists_the_objects_and_defaults_to_no(self, controller, gpkg):
        FakeMessageBox.answer = FakeMessageBox.StandardButton.No
        controller.run_global_cleanup_with_confirmation()
        box = FakeMessageBox.last
        assert box.default == FakeMessageBox.StandardButton.No
        assert f"fm_temp_{SID}_routes" in box.details
        assert "fm_temp_11111111_old" in box.details
        assert "mvt_reseau" not in box.details

    def test_nothing_to_clean_asks_nothing(self, controller, tmp_path, feedback):
        db = tmp_path / "clean.gpkg"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE routes (fid INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        FakeProject.layers = [FakeLayer(f"{db}|layername=routes")]
        controller.run_global_cleanup_with_confirmation()
        assert FakeMessageBox.last is None
        feedback.show_info.assert_called_once()


class FakeCursor:
    """psycopg2-like cursor over a small catalog: [(kind, schema, name), ...]."""

    def __init__(self, catalog, fail_on=()):
        self.catalog = list(catalog)
        self.fail_on = fail_on
        self.executed = []
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        flat = " ".join(sql.split())
        for needle in self.fail_on:
            if needle in flat:
                raise RuntimeError(f"cannot drop: {needle}")
        if "FROM pg_matviews" in flat:
            self._rows = [(s, n) for k, s, n in self.catalog if k == "matview"]
        elif "FROM pg_tables" in flat:
            self._rows = [(s, n) for k, s, n in self.catalog if k == "table"]
        elif "FROM pg_class" in flat:
            schema = params[0]
            self._rows = [(n, {"matview": "m", "table": "r", "view": "v"}[k])
                          for k, s, n in self.catalog if s == schema]
        elif "information_schema.schemata" in flat:
            self._rows = [(1,)]
        else:
            self._rows = []

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0]


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def _pg_controller(controller, catalog, schema="filter_mate_temp", fail_on=()):
    cursor = FakeCursor(catalog, fail_on)
    connection = FakeConnection(cursor)
    controller.get_pg_session_context = lambda: (None, SID, schema, connection)
    return cursor, connection


def _statements(cursor):
    return [" ".join(sql.split()) for sql, _p in cursor.executed
            if sql.lstrip().upper().startswith(("DROP", "CREATE"))]


class TestPostgresGlobalCleanup:
    CATALOG = [
        ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc"),
        ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc_dump"),
        ("table", "ref", "fm_temp_buf_communes_0123abcd"),
        # rows an over-broad pre-selection could return: user objects
        ("table", "public", "filtermate_catalog"),
        ("table", "public", "fm_buf_users"),
        ("matview", "public", "fm_mv_report"),
    ]

    def test_only_filtermate_objects_are_dropped_without_cascade(self, controller):
        cursor, connection = _pg_controller(controller, self.CATALOG, schema="filtermate_temp")
        assert controller._cleanup_postgresql_all_sessions() == 3
        drops = _statements(cursor)
        assert all("CASCADE" not in d for d in drops)
        joined = "\n".join(drops)
        assert "filtermate_catalog" not in joined
        assert "fm_buf_users" not in joined
        assert "fm_mv_report" not in joined
        assert f'"filtermate_temp"."fm_temp_mv_{SID}_abc_dump"' in joined
        assert connection.closed

    def test_dependent_view_is_dropped_before_its_parent(self, controller):
        cursor, _c = _pg_controller(controller, self.CATALOG)
        controller._cleanup_postgresql_all_sessions()
        drops = [d for d in _statements(cursor) if "MATERIALIZED VIEW" in d]
        assert drops.index(next(d for d in drops if d.endswith(f'fm_temp_mv_{SID}_abc_dump";'))) \
            < drops.index(next(d for d in drops if d.endswith(f'fm_temp_mv_{SID}_abc";')))

    def test_preselection_patterns_are_exact(self, controller):
        cursor, _c = _pg_controller(controller, self.CATALOG)
        controller._cleanup_postgresql_all_sessions()
        patterns = [p for sql, params in cursor.executed if params for p in params[0]]
        assert patterns
        assert all("\\_" in p for p in patterns)
        assert "filtermate\\_%" not in patterns

    def test_listing_does_not_drop(self, controller):
        cursor, _c = _pg_controller(controller, self.CATALOG)
        assert len(controller._list_postgresql_temp_objects()) == 3
        assert _statements(cursor) == []

    def test_an_undroppable_object_is_left_in_place(self, controller):
        cursor, connection = _pg_controller(
            controller, self.CATALOG, fail_on=(f'"fm_temp_mv_{SID}_abc"',))
        assert controller._cleanup_postgresql_all_sessions() == 2
        assert connection.rollbacks >= 1  # the aborted transaction is cleaned


class TestPostgresSchemaCleanup:
    def test_user_schema_is_never_dropped(self, controller):
        cursor, connection = _pg_controller(controller, [], schema="public")
        assert controller.cleanup_postgresql_schema_if_empty(force=True) is False
        assert _statements(cursor) == []
        assert connection.closed

    def test_schema_with_a_user_table_is_kept(self, controller):
        catalog = [("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_abc"),
                   ("table", "filter_mate_temp", "my_precious_table")]
        cursor, _c = _pg_controller(controller, catalog)
        assert controller.cleanup_postgresql_schema_if_empty(force=True) is False
        assert _statements(cursor) == []

    def test_filtermate_schema_is_emptied_then_dropped_without_cascade(self, controller):
        catalog = [("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_abc"),
                   ("table", "filter_mate_temp", "fm_temp_src_sel_0123abcd")]
        cursor, _c = _pg_controller(controller, catalog)
        assert controller.cleanup_postgresql_schema_if_empty(force=True) is True
        drops = _statements(cursor)
        assert drops[-1] == 'DROP SCHEMA IF EXISTS "filter_mate_temp";'
        assert len(drops) == 3
        assert all("CASCADE" not in d for d in drops)

    def test_other_sessions_views_block_without_force(self, controller):
        catalog = [("matview", "filter_mate_temp", "fm_temp_mv_99999999_abc")]
        cursor, _c = _pg_controller(controller, catalog)
        assert controller.cleanup_postgresql_schema_if_empty(force=False) is False
        assert _statements(cursor) == []

    def test_schema_preview_lists_objects(self, controller):
        catalog = [("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_abc")]
        _pg_controller(controller, catalog)
        assert controller.list_postgresql_schema_objects() == [
            ("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_abc")]

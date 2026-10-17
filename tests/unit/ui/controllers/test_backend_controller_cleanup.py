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
import re
import sqlite3
import sys
import types
from unittest.mock import MagicMock

import pytest

from tests.unit.pg_fakes import FakeConnection, FakePgCatalog

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_backend_cleanup_test"
SID = "ab12cd34"


class FakeLayer:
    def __init__(self, source, provider="ogr", subset=""):
        self._source, self._provider, self._subset = source, provider, subset

    def providerType(self):
        return self._provider

    def source(self):
        return self._source

    def subsetString(self):
        return self._subset


class FakeDataSourceUri:
    """The one accessor the controller reads: database() of ``dbname='path' ...``."""

    def __init__(self, source):
        match = re.search(r"dbname='([^']*)'", source)
        self._database = match.group(1) if match else ""

    def database(self):
        return self._database


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
    qtcore.QCoreApplication = MagicMock()
    qtwidgets = types.ModuleType("qgis.PyQt.QtWidgets")
    qtwidgets.QMenu = MagicMock()
    qtwidgets.QLabel = MagicMock()
    qtwidgets.QMessageBox = FakeMessageBox
    qgis_core = types.ModuleType("qgis.core")
    qgis_core.QgsVectorLayer = FakeLayer
    qgis_core.QgsProject = FakeProject
    qgis_core.QgsDataSourceUri = FakeDataSourceUri
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


class TestSpatialiteProvider:
    """Native Spatialite databases (the only ones where fm_temp_* is made) are scanned too."""

    def _native(self, tmp_path):
        db = tmp_path / "native.sqlite"
        conn = sqlite3.connect(str(db))
        conn.executescript(f"""
            CREATE TABLE geometry_columns (f_table_name TEXT, f_geometry_column TEXT);
            CREATE TABLE roads (pk INTEGER PRIMARY KEY, geom BLOB);
            CREATE TABLE "fm_temp_{SID}_roads" (pk INTEGER);
            CREATE TABLE mvt_reseau (pk INTEGER);
        """)
        conn.execute("INSERT INTO geometry_columns VALUES ('roads', 'geom')")
        conn.commit()
        conn.close()
        FakeProject.layers = [
            FakeLayer(f"dbname='{db}' table=\"roads\" (geom) sql=", provider="spatialite"),
            FakeLayer("dbname='gis' host=h port=5432 table=\"public\".\"x\" (geom)", provider="postgres")]
        return db

    def test_the_database_of_a_spatialite_layer_is_scanned(self, controller, tmp_path):
        db = self._native(tmp_path)

        assert controller._spatialite_project_databases() == [str(db)]
        # an undeclared fm_temp table of the native database is a candidate, the user ones are not
        assert controller.collect_global_cleanup_candidates()["spatialite"] == {str(db): [f"fm_temp_{SID}_roads"]}

    def test_session_cleanup_drops_its_table_in_a_native_database(self, controller, tmp_path):
        db = self._native(tmp_path)

        assert controller._cleanup_spatialite_project_tables() == 1

        assert f"fm_temp_{SID}_roads" not in _tables(db) and {"roads", "mvt_reseau"} <= _tables(db)

    def test_a_missing_database_is_ignored(self, controller):
        FakeProject.layers = [FakeLayer("dbname='/no/such/file.sqlite' table=\"t\" (g)", provider="spatialite")]

        assert controller._spatialite_project_databases() == []


class TestTablesInUse:
    def test_a_table_a_layer_is_filtered_through_is_not_a_candidate_nor_dropped(self, controller, gpkg):
        FakeProject.layers.append(FakeLayer(
            f"{gpkg}|layername=mvt_reseau", subset=f'"fid" IN (SELECT "fid" FROM fm_temp_{SID}_routes)'))

        candidates = controller.collect_global_cleanup_candidates()
        assert candidates["spatialite"] == {str(gpkg): ["fm_temp_11111111_old"]}

        assert controller.cleanup_temp_tables_global() == 1
        assert f"fm_temp_{SID}_routes" in _tables(gpkg)

    def test_the_session_cleanup_keeps_it_too(self, controller, gpkg):
        FakeProject.layers.append(FakeLayer(
            f"{gpkg}|layername=mvt_reseau", subset=f'"fid" IN (SELECT "fid" FROM fm_temp_{SID}_routes)'))

        assert controller._cleanup_spatialite_project_tables() == 0
        assert f"fm_temp_{SID}_routes" in _tables(gpkg)


def _pg_controller(controller, catalog, schema="filter_mate_temp"):
    connection = FakeConnection(catalog)
    controller.get_pg_session_context = lambda: (None, SID, schema, connection)
    return connection


class TestPostgresGlobalCleanup:
    OBJECTS = [
        ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc"),
        ("matview", "filtermate_temp", f"fm_temp_mv_{SID}_abc_dump"),
        ("table", "ref", "fm_temp_buf_communes_0123abcd"),
        ("table", "ref", "fm_temp_buf_routes-2024_ab12cd34"),
        # user objects the old patterns (or an over-broad listing) could return
        ("table", "public", "filtermate_catalog"),
        ("table", "public", "fm_buf_users"),
        ("matview", "public", "fm_mv_report"),
        ("matview", "public", "mv_20231231_bati"),
    ]

    def _catalog(self, **kwargs):
        return FakePgCatalog(self.OBJECTS, dependents={
            f"fm_temp_mv_{SID}_abc": [f"fm_temp_mv_{SID}_abc_dump"]}, **kwargs)

    @pytest.mark.parametrize("overbroad", [False, True])
    def test_only_filtermate_objects_are_dropped_without_cascade(self, controller, overbroad):
        catalog = self._catalog(overbroad=overbroad)
        connection = _pg_controller(controller, catalog, schema="filtermate_temp")

        assert controller._cleanup_postgresql_all_sessions() == 4

        assert sorted(n for _k, _s, n in catalog.objects) == sorted([
            "filtermate_catalog", "fm_buf_users", "fm_mv_report", "mv_20231231_bati"])
        statements = catalog.statements()
        assert all("CASCADE" not in s for s in statements)
        assert 'DROP TABLE "ref"."fm_temp_buf_routes-2024_ab12cd34"' in statements
        assert connection.closed

    def test_dependent_view_is_dropped_before_its_parent(self, controller):
        catalog = self._catalog()
        _pg_controller(controller, catalog)

        controller._cleanup_postgresql_all_sessions()

        views = [s for s in catalog.statements() if "MATERIALIZED VIEW" in s]
        assert views.index(next(s for s in views if s.endswith(f'fm_temp_mv_{SID}_abc_dump"'))) \
            < views.index(next(s for s in views if s.endswith(f'fm_temp_mv_{SID}_abc"')))

    def test_preselection_patterns_are_exact(self, controller):
        catalog = self._catalog()
        _pg_controller(controller, catalog)
        controller._cleanup_postgresql_all_sessions()
        patterns = [p for sql, params in catalog.executed if params and isinstance(params[0], list)
                    for p in params[0]]
        assert patterns and all("\\_" in p for p in patterns)
        assert "filtermate\\_%" not in patterns

    def test_listing_does_not_drop(self, controller):
        catalog = self._catalog()
        _pg_controller(controller, catalog)

        assert len(controller._list_postgresql_temp_objects()) == 4
        assert catalog.statements() == []

    def test_an_undroppable_object_is_left_in_place_and_not_counted(self, controller):
        catalog = self._catalog(undroppable=[f"fm_temp_mv_{SID}_abc_dump"])
        connection = _pg_controller(controller, catalog)

        assert controller._cleanup_postgresql_all_sessions() == 2
        assert connection.rollbacks >= 1 and catalog.has(f"fm_temp_mv_{SID}_abc_dump")

    def test_what_does_not_disappear_is_not_counted(self, controller):
        catalog = self._catalog(ghosts=["fm_temp_buf_communes_0123abcd"])
        _pg_controller(controller, catalog)

        assert controller._cleanup_postgresql_all_sessions() == 3

    def test_an_emptied_filtermate_schema_is_dropped_without_cascade(self, controller):
        catalog = FakePgCatalog([("table", "filtermate_temp", "fm_temp_tbl_x")], schemas=["filtermate_temp"])
        _pg_controller(controller, catalog)

        controller._cleanup_postgresql_all_sessions()

        assert "filtermate_temp" not in catalog.schemas
        assert 'DROP SCHEMA IF EXISTS "filtermate_temp"' in catalog.statements()


class TestPostgresSchemaCleanup:
    def test_user_schema_is_never_dropped(self, controller):
        catalog = FakePgCatalog(schemas=["public"])
        connection = _pg_controller(controller, catalog, schema="public")

        assert controller.cleanup_postgresql_schema_if_empty(force=True) is False
        assert catalog.statements() == [] and connection.closed

    def test_schema_with_a_user_table_is_kept(self, controller):
        catalog = FakePgCatalog([("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_abc"),
                                 ("table", "filter_mate_temp", "my_precious_table")])
        _pg_controller(controller, catalog)

        assert controller.cleanup_postgresql_schema_if_empty(force=True) is False
        assert catalog.statements() == []

    def test_filtermate_schema_is_emptied_then_dropped_without_cascade(self, controller):
        catalog = FakePgCatalog([("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_abc"),
                                 ("table", "filter_mate_temp", "fm_temp_src_sel_0123abcd")])
        _pg_controller(controller, catalog)

        assert controller.cleanup_postgresql_schema_if_empty(force=True) is True

        drops = catalog.statements()
        assert drops[-1] == 'DROP SCHEMA "filter_mate_temp"' and len(drops) == 3
        assert all("CASCADE" not in d for d in drops)

    def test_a_legacy_session_view_does_not_block_the_drop(self, controller):
        catalog = FakePgCatalog([("matview", "filter_mate_temp", f"mv_{SID}_legacy")])
        _pg_controller(controller, catalog)

        assert controller.cleanup_postgresql_schema_if_empty(force=False) is True

    def test_other_sessions_views_block_without_force(self, controller):
        catalog = FakePgCatalog([("matview", "filter_mate_temp", "fm_temp_mv_99999999_abc")])
        _pg_controller(controller, catalog)

        assert controller.cleanup_postgresql_schema_if_empty(force=False) is False
        assert catalog.statements() == []


class TestSchemaListing:
    def test_ok_lists_the_objects(self, controller):
        catalog = FakePgCatalog([("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_abc")])
        _pg_controller(controller, catalog)

        listing = controller.list_postgresql_schema_objects()

        assert listing["status"] == "ok" and listing["schema"] == "filter_mate_temp"
        assert listing["objects"] == [("matview", "filter_mate_temp", f"fm_temp_mv_{SID}_abc")]

    def test_empty_is_ok_with_no_object(self, controller):
        _pg_controller(controller, FakePgCatalog(schemas=["filter_mate_temp"]))

        listing = controller.list_postgresql_schema_objects()

        assert listing["status"] == "ok" and listing["objects"] == []

    def test_absent(self, controller):
        _pg_controller(controller, FakePgCatalog())

        assert controller.list_postgresql_schema_objects()["status"] == "absent"

    def test_foreign_objects_are_named(self, controller):
        catalog = FakePgCatalog([("table", "filter_mate_temp", "mine")])
        _pg_controller(controller, catalog)

        listing = controller.list_postgresql_schema_objects()

        assert listing["status"] == "foreign" and listing["foreign"] == ["mine"]

    def test_not_a_filtermate_schema_and_no_connection(self, controller):
        _pg_controller(controller, FakePgCatalog(schemas=["public"]), schema="public")
        assert controller.list_postgresql_schema_objects()["status"] == "not_filtermate_schema"
        controller.get_pg_session_context = lambda: (None, SID, "filter_mate_temp", None)
        assert controller.list_postgresql_schema_objects()["status"] == "no_connection"

    @pytest.mark.parametrize("listing, proceed, level, fragment", [
        ({"status": "ok", "schema": "s", "objects": []}, True, None, ""),
        ({"status": "absent", "schema": "s"}, False, "info", "does not exist"),
        ({"status": "foreign", "schema": "s", "foreign": ["mine", "yours"]}, False, "warning", "mine, yours"),
        ({"status": "not_filtermate_schema", "schema": "public"}, False, "warning", "not a FilterMate"),
        ({"status": "no_connection", "schema": None}, False, "warning", "No PostgreSQL connection"),
        ({"status": "error", "schema": "s"}, False, "warning", "failed"),
    ])
    def test_the_reason_is_shown(self, controller, listing, proceed, level, fragment):
        got_proceed, got_level, text = controller.describe_schema_listing(listing)

        assert (got_proceed, got_level) == (proceed, level)
        assert fragment in text

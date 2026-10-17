# -*- coding: utf-8 -*-
"""
PostgresSessionManager.cleanup_schema_if_empty no longer runs ``DROP SCHEMA ... CASCADE``.

The schema is dropped only when it is one of FilterMate's own and holds nothing
but FilterMate objects (emptied one by one, no CASCADE); otherwise the result
says why. The module runs in a private package, Qt and the SQL helpers stubbed.
"""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.unit.pg_fakes import FakeConnection, FakePgCatalog

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_PKG = "_fm_pgsession_pkg"
SID = "ab12cd34"


@pytest.fixture(scope="module")
def manager_class():
    full = f"{_PKG}.core.services.postgres_session_manager"
    if full not in sys.modules:
        for name, path in ((_PKG, _ROOT), (f"{_PKG}.core", _ROOT / "core"),
                           (f"{_PKG}.core.services", _ROOT / "core" / "services"),
                           (f"{_PKG}.infrastructure", _ROOT / "infrastructure"),
                           (f"{_PKG}.infrastructure.database", _ROOT / "infrastructure" / "database")):
            package = types.ModuleType(name)
            package.__path__ = [str(path)]
            sys.modules[name] = package
        qtcore = types.ModuleType("qgis.PyQt.QtCore")
        qtcore.pyqtSignal = lambda *a, **k: MagicMock()
        qtcore.QObject = object
        sys.modules.setdefault("qgis", MagicMock())
        sys.modules.setdefault("qgis.PyQt", MagicMock())
        sys.modules["qgis.PyQt.QtCore"], previous = qtcore, sys.modules.get("qgis.PyQt.QtCore")
        sql_utils = types.ModuleType(f"{_PKG}.infrastructure.database.sql_utils")
        sql_utils.sanitize_sql_identifier = lambda name: name
        sys.modules[sql_utils.__name__] = sql_utils
        temp_spec = importlib.util.spec_from_file_location(
            f"{_PKG}.infrastructure.database.temp_objects", _ROOT / "infrastructure" / "database" / "temp_objects.py")
        temp_module = importlib.util.module_from_spec(temp_spec)
        sys.modules[temp_spec.name] = temp_module
        temp_spec.loader.exec_module(temp_module)
        spec = importlib.util.spec_from_file_location(full, _ROOT / "core" / "services" / "postgres_session_manager.py")
        module = importlib.util.module_from_spec(spec)
        module.__package__ = f"{_PKG}.core.services"
        sys.modules[full] = module
        try:
            spec.loader.exec_module(module)
        finally:
            if previous is not None:
                sys.modules["qgis.PyQt.QtCore"] = previous
            else:
                sys.modules.pop("qgis.PyQt.QtCore", None)
    return sys.modules[full].PostgresSessionManager


def _manager(manager_class, schema="filtermate_temp"):
    manager = manager_class.__new__(manager_class)
    manager._schema = schema
    manager._session_id = SID
    manager._session_views = []
    manager.error_occurred = MagicMock()
    return manager


def test_filtermate_objects_only_schema_is_emptied_and_dropped_without_cascade(manager_class):
    catalog = FakePgCatalog([("matview", "filtermate_temp", f"fm_temp_mv_{SID}_x")])

    result = _manager(manager_class).cleanup_schema_if_empty(FakeConnection(catalog))

    assert result.success and result.schema_dropped
    assert "filtermate_temp" not in catalog.schemas
    assert all("CASCADE" not in s for s in catalog.statements())


def test_other_sessions_views_block_without_force_and_go_with_it(manager_class):
    catalog = FakePgCatalog([("matview", "filtermate_temp", "fm_temp_mv_99999999_x")])
    manager = _manager(manager_class)

    assert not manager.cleanup_schema_if_empty(FakeConnection(catalog)).success
    assert catalog.statements() == []
    assert manager.cleanup_schema_if_empty(FakeConnection(catalog), force=True).schema_dropped is True


def test_a_user_table_keeps_the_schema_and_the_reason_is_given(manager_class):
    catalog = FakePgCatalog([("matview", "filtermate_temp", f"fm_temp_mv_{SID}_x"), ("table", "filtermate_temp", "mine")])

    result = _manager(manager_class).cleanup_schema_if_empty(FakeConnection(catalog), force=True)

    assert not result.success and "mine" in result.error_message
    assert catalog.has("mine") and catalog.statements() == []


def test_a_schema_that_is_not_filtermates_is_refused(manager_class):
    catalog = FakePgCatalog(schemas=["public"])

    result = _manager(manager_class, schema="public").cleanup_schema_if_empty(FakeConnection(catalog), force=True)

    assert not result.success and "not a FilterMate" in result.error_message
    assert "public" in catalog.schemas

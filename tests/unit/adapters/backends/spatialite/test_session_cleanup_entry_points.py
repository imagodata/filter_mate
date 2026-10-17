# -*- coding: utf-8 -*-
"""
The Spatialite reset action and the executor cleanup used to call
``cleanup_session_temp_tables(db_path)`` without the session id (a TypeError that
made the reset report a failure after the filter was cleared).

They now receive the real session id. Without one nothing is dropped, which is also
what happens at the end of a task: the filter just made reads its temp table until
the main thread applies the queued subset, so a task must never sweep its own session.
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
_PKG = "fm_sl_entry_test"
SID = "ab12cd34"


def _module(name, path=None, **attrs):
    mod = types.ModuleType(name)
    if path is not None:
        mod.__path__ = [str(path)]
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


@pytest.fixture(scope="module")
def entry_points():
    base = f"{_PKG}.adapters.backends.spatialite"
    _module(_PKG, _ROOT)
    _module(f"{_PKG}.adapters", _ROOT / "adapters")
    _module(f"{_PKG}.adapters.backends", _ROOT / "adapters" / "backends")
    _module(base, _ROOT / "adapters" / "backends" / "spatialite")
    # the real cleanup, over the real name rules
    _module(f"{_PKG}.infrastructure", _ROOT / "infrastructure")
    _module(f"{_PKG}.infrastructure.database", _ROOT / "infrastructure" / "database")
    spec = importlib.util.spec_from_file_location(
        f"{_PKG}.infrastructure.database.temp_objects", _ROOT / "infrastructure" / "database" / "temp_objects.py")
    temp = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = temp
    spec.loader.exec_module(temp)

    def cleanup_session_temp_tables(db_path, session_id=None, exclude_referenced_by=()):
        if not session_id or not db_path:
            return 0
        return len(temp.drop_filtermate_temp_tables(
            db_path, session_id=session_id, exclude_referenced_by=exclude_referenced_by))

    _module(f"{base}.filter_executor", cleanup_session_temp_tables=cleanup_session_temp_tables)
    qgis_core = types.ModuleType("qgis.core")
    qgis_core.QgsVectorLayer = object
    qgis_core.QgsProject = MagicMock()
    previous = sys.modules.get("qgis.core")
    sys.modules["qgis.core"] = qgis_core
    try:
        spec = importlib.util.spec_from_file_location(f"{base}.filter_actions", _ROOT / "adapters" / "backends" / "spatialite" / "filter_actions.py")
        actions = importlib.util.module_from_spec(spec)
        actions.__package__ = base
        sys.modules[spec.name] = actions
        spec.loader.exec_module(actions)
    finally:
        if previous is not None:
            sys.modules["qgis.core"] = previous
        else:
            sys.modules.pop("qgis.core", None)
    return actions


class _Layer:
    def __init__(self):
        self.subset = "x = 1"

    def name(self):
        return "routes"

    def featureCount(self):
        return 1

    def setSubsetString(self, text):
        self.subset = text
        return True


def _db(tmp_path):
    path = tmp_path / "reseau.sqlite"
    conn = sqlite3.connect(str(path))
    conn.executescript(f"""
        CREATE TABLE routes (fid INTEGER);
        CREATE TABLE "fm_temp_{SID}_routes" (fid INTEGER);
        CREATE TABLE "fm_temp_{SID}_other" (fid INTEGER);
    """)
    conn.commit()
    conn.close()
    return path


def _tables(path):
    conn = sqlite3.connect(str(path))
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def test_reset_with_the_session_id_drops_the_session_tables_no_layer_uses(entry_points, tmp_path):
    path = _db(tmp_path)
    layer = _Layer()

    ok, message = entry_points.execute_reset_action_spatialite(
        layer, "reset", {"session_id": SID, "subsets_in_use": [f'"fid" IN (SELECT "fid" FROM fm_temp_{SID}_other)']},
        {"dbname": str(path)})

    assert ok is True and layer.subset == ""
    left = _tables(path)
    assert f"fm_temp_{SID}_routes" not in left and f"fm_temp_{SID}_other" in left  # still used by another layer


def test_reset_without_a_session_id_succeeds_and_drops_nothing(entry_points, tmp_path):
    path = _db(tmp_path)

    ok, message = entry_points.execute_reset_action_spatialite(_Layer(), "reset", {}, {"dbname": str(path)})

    assert ok is True and "failed" not in message.lower()
    assert f"fm_temp_{SID}_routes" in _tables(path)


def test_cleanup_wrapper_takes_the_session_id_and_the_tables_in_use(entry_points, tmp_path):
    path = _db(tmp_path)

    assert entry_points.cleanup_spatialite_session_tables(str(path)) == 0
    assert entry_points.cleanup_spatialite_session_tables(
        str(path), SID, exclude_referenced_by=[f"... fm_temp_{SID}_routes ..."]) == 1
    assert f"fm_temp_{SID}_routes" in _tables(path) and f"fm_temp_{SID}_other" not in _tables(path)

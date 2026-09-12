# -*- coding: utf-8 -*-
"""Regression tests for `task_completion_handler.apply_pending_subset_requests`.

Focus: 2026-04-29 SQLite-locking fix. When the cascade enqueues 8 distant
layers that all live in the same `server.sqlite` file, the previous tight
loop ran setSubsetString → reload → featureCount → updateExtents →
triggerRepaint per layer with no inter-layer pause. SQLite's single-writer
constraint then surfaced as ``OGR error: sqlite3_step(): unable to open
database file`` during the redraw, and `featureCount()` returned the stale
pre-filter count even though the subset string had been correctly set —
the cascade silently looked like a no-op.

The fix mirrors the throttle already used in
`ParallelFilterExecutor._filter_sequential`: track the previous layer's DB
path; consecutive layers of the same file are applied under a frozen canvas.
"""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Stub the qgis.* modules that task_completion_handler imports at top-level.
# The directory's conftest.py already wires the filter_mate.* tree.
# ---------------------------------------------------------------------------

def _install_qgis_stubs():
    qgis_core = types.SimpleNamespace(
        QgsMessageLog=MagicMock(),
        Qgis=types.SimpleNamespace(
            MessageLevel=types.SimpleNamespace(Info=0, Warning=1, Critical=2)
        ),
        QgsProject=MagicMock(),
    )
    sys.modules.setdefault("qgis", types.SimpleNamespace(
        core=qgis_core,
        utils=types.SimpleNamespace(iface=MagicMock()),
    ))
    sys.modules.setdefault("qgis.core", qgis_core)
    sys.modules.setdefault("qgis.utils", types.SimpleNamespace(iface=MagicMock()))
    sys.modules.setdefault("qgis.PyQt", types.SimpleNamespace(QtCore=MagicMock()))
    sys.modules.setdefault(
        "qgis.PyQt.QtCore",
        types.SimpleNamespace(QTimer=MagicMock()),
    )


_install_qgis_stubs()

from core.tasks import task_completion_handler as _tch
from core.tasks.task_completion_handler import (
    _layer_database_path,
    apply_pending_subset_requests,
)


@pytest.fixture(autouse=True)
def _stub_qgis_symbols_on_module():
    """Re-pin QgsMessageLog/Qgis on the module before each test.

    Sibling test suites swap entries in `sys.modules['qgis.core']` for
    their own MagicMocks; the resolved `QgsMessageLog`/`Qgis` references
    captured in `task_completion_handler` at import time then point to
    a bare MagicMock without `.logMessage` / `.MessageLevel`. Re-pinning
    at the start of every test makes this suite immune to ordering.
    """
    qgs_log = MagicMock()
    qgs_log.logMessage = MagicMock()
    qgs_obj = types.SimpleNamespace(
        MessageLevel=types.SimpleNamespace(Info=0, Warning=1, Critical=2)
    )
    with patch.object(_tch, "QgsMessageLog", qgs_log), \
         patch.object(_tch, "Qgis", qgs_obj):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_layer(name: str, source: str, provider: str = "spatialite"):
    """Build a minimal QgsVectorLayer-shaped MagicMock for the apply loop."""
    layer = MagicMock()
    layer.name.return_value = name
    layer.id.return_value = f"{name}_id"
    layer.isValid.return_value = True
    layer.source.return_value = source
    layer.providerType.return_value = provider
    layer.subsetString.return_value = ""  # no existing filter
    layer.featureCount.return_value = 100
    layer.error.return_value = None
    return layer


# ---------------------------------------------------------------------------
# _layer_database_path: file extraction
# ---------------------------------------------------------------------------

class TestLayerDatabasePath:
    def test_spatialite_dbname_form(self):
        layer = _make_layer("cables", "dbname='/data/server.sqlite' table='cables'")
        assert _layer_database_path(layer) == "/data/server.sqlite"

    def test_spatialite_dbname_double_quote_form(self):
        layer = _make_layer("cables", 'dbname="/data/server.sqlite" table="cables"')
        assert _layer_database_path(layer) == "/data/server.sqlite"

    def test_geopackage_pipe_form(self):
        layer = _make_layer("cables", "/data/world.gpkg|layername=cables")
        assert _layer_database_path(layer) == "/data/world.gpkg"

    def test_returns_lowercased_path(self):
        # Case-insensitive match required for Windows (server.SQLITE vs server.sqlite).
        layer = _make_layer("cables", "/Data/Server.SQLITE|layername=cables")
        assert _layer_database_path(layer) == "/data/server.sqlite"

    def test_non_sqlite_extension_returns_none(self):
        layer = _make_layer("cables", "/data/world.shp")
        assert _layer_database_path(layer) is None

    def test_empty_source_returns_none(self):
        layer = _make_layer("cables", "")
        assert _layer_database_path(layer) is None

    def test_layer_without_source_attr_returns_none(self):
        bare = MagicMock(spec=[])  # no .source attribute
        assert _layer_database_path(bare) is None


# ---------------------------------------------------------------------------
# apply_pending_subset_requests: throttle on shared SQLite
# ---------------------------------------------------------------------------

class TestApplyPendingSharedSqlite:
    """PERF 2026-09-12: the fixed 0.2/0.3/0.5 s pauses between layers of the
    same SQLite file are gone. The canvas is frozen for the whole apply loop
    (no redraw can hold the file between two applies) and a lock error on a
    shared file is retried once after a short pause."""

    def _shared_layers(self, count):
        return [_make_layer(f"l{i}", "dbname='/data/server.sqlite'") for i in range(count)]

    def test_no_fixed_pause_between_shared_layers(self, monkeypatch):
        monkeypatch.setattr(_tch, "iface", MagicMock())
        layers = self._shared_layers(12)
        safe_set = MagicMock(return_value=True)
        with patch("time.sleep") as mock_sleep:
            applied = apply_pending_subset_requests(
                [(l, f"fid IN ({i})") for i, l in enumerate(layers)], safe_set)
        mock_sleep.assert_not_called()
        assert applied == 12

    def test_canvas_frozen_around_the_loop(self, monkeypatch):
        fake_iface = MagicMock()
        canvas = fake_iface.mapCanvas.return_value
        monkeypatch.setattr(_tch, "iface", fake_iface)
        layers = self._shared_layers(3)
        calls = []
        canvas.freeze.side_effect = lambda flag: calls.append(("freeze", flag))
        safe_set = MagicMock(side_effect=lambda *_: calls.append(("apply", None)) or True)

        apply_pending_subset_requests([(l, "1") for l in layers], safe_set)

        assert calls[0] == ("freeze", True)
        assert calls[-1] == ("freeze", False)
        assert calls.count(("apply", None)) == 3
        canvas.refresh.assert_called_once()

    def test_single_request_does_not_freeze(self, monkeypatch):
        fake_iface = MagicMock()
        monkeypatch.setattr(_tch, "iface", fake_iface)
        apply_pending_subset_requests([(_make_layer("solo", "dbname='/data/a.sqlite'"), "1")],
                                      MagicMock(return_value=True))
        fake_iface.mapCanvas.return_value.freeze.assert_not_called()

    def test_lock_error_on_shared_file_is_retried_once(self, monkeypatch):
        monkeypatch.setattr(_tch, "iface", MagicMock())
        first, second = self._shared_layers(2)
        error = MagicMock()
        error.message.return_value = "OGR error: sqlite3_step(): unable to open database file"
        second.error.return_value = error
        outcomes = {second.id(): [False, True]}

        def safe_set(layer, expr):
            queue = outcomes.get(layer.id())
            return queue.pop(0) if queue else True

        with patch("time.sleep") as mock_sleep:
            applied = apply_pending_subset_requests([(first, "1"), (second, "2")], safe_set)

        assert applied == 2
        mock_sleep.assert_called_once_with(0.3)

    def test_lock_error_on_first_layer_of_a_file_is_not_retried(self, monkeypatch):
        monkeypatch.setattr(_tch, "iface", MagicMock())
        a = _make_layer("a", "dbname='/data/a.sqlite'")
        b = _make_layer("b", "dbname='/data/b.sqlite'")
        error = MagicMock()
        error.message.return_value = "database is locked"
        b.error.return_value = error
        safe_set = MagicMock(side_effect=lambda layer, expr: layer is a)

        with patch("time.sleep") as mock_sleep:
            applied = apply_pending_subset_requests([(a, "1"), (b, "2")], safe_set)

        assert applied == 1
        mock_sleep.assert_not_called()

    def test_unrelated_failure_is_not_retried(self, monkeypatch):
        monkeypatch.setattr(_tch, "iface", MagicMock())
        first, second = self._shared_layers(2)
        error = MagicMock()
        error.message.return_value = "syntax error near IN"
        second.error.return_value = error
        safe_set = MagicMock(side_effect=lambda layer, expr: layer is first)

        with patch("time.sleep") as mock_sleep:
            applied = apply_pending_subset_requests([(first, "1"), (second, "2")], safe_set)

        assert applied == 1
        mock_sleep.assert_not_called()
        assert safe_set.call_count == 2

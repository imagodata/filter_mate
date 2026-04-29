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
path and sleep 0.2/0.3/0.5s when consecutive layers share the same file.
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

class TestApplyPendingThrottle:
    """The cascade's main fix: pause between consecutive applies on the
    same SQLite file so the previous setSubsetString+reload releases its
    file lock before the next one opens a new connection."""

    def test_no_sleep_for_single_layer(self):
        layer = _make_layer("cables", "dbname='/data/server.sqlite'")
        safe_set = MagicMock(return_value=True)

        with patch("time.sleep") as mock_sleep:
            apply_pending_subset_requests([(layer, "fid IN (1, 2)")], safe_set)

        mock_sleep.assert_not_called()

    def test_no_sleep_for_distinct_databases(self):
        layer_a = _make_layer("cables", "dbname='/data/a.sqlite'")
        layer_b = _make_layer("ducts", "dbname='/data/b.sqlite'")
        safe_set = MagicMock(return_value=True)

        with patch("time.sleep") as mock_sleep:
            apply_pending_subset_requests(
                [(layer_a, "fid IN (1)"), (layer_b, "fid IN (2)")],
                safe_set,
            )

        mock_sleep.assert_not_called()

    def test_short_delay_for_2_to_5_shared_layers(self):
        # 3 layers in the same SQLite → 0.2s pause between consecutive ones.
        layers = [
            _make_layer(f"l{i}", "dbname='/data/server.sqlite'")
            for i in range(3)
        ]
        safe_set = MagicMock(return_value=True)

        with patch("time.sleep") as mock_sleep:
            apply_pending_subset_requests(
                [(l, f"fid IN ({i})") for i, l in enumerate(layers)],
                safe_set,
            )

        # 2 inter-layer pauses (between layer0→1 and layer1→2).
        assert mock_sleep.call_count == 2
        for call in mock_sleep.call_args_list:
            assert call.args[0] == 0.2

    def test_medium_delay_for_6_to_10_shared_layers(self):
        # 8 layers (the user's exact case) → 0.3s pause.
        layers = [
            _make_layer(f"l{i}", "dbname='/data/server.sqlite'")
            for i in range(8)
        ]
        safe_set = MagicMock(return_value=True)

        with patch("time.sleep") as mock_sleep:
            apply_pending_subset_requests(
                [(l, f"fid IN ({i})") for i, l in enumerate(layers)],
                safe_set,
            )

        assert mock_sleep.call_count == 7
        for call in mock_sleep.call_args_list:
            assert call.args[0] == 0.3

    def test_long_delay_for_more_than_10_shared_layers(self):
        layers = [
            _make_layer(f"l{i}", "dbname='/data/server.sqlite'")
            for i in range(12)
        ]
        safe_set = MagicMock(return_value=True)

        with patch("time.sleep") as mock_sleep:
            apply_pending_subset_requests(
                [(l, f"fid IN ({i})") for i, l in enumerate(layers)],
                safe_set,
            )

        assert mock_sleep.call_count == 11
        for call in mock_sleep.call_args_list:
            assert call.args[0] == 0.5

    def test_throttle_resets_when_layer_switches_database(self):
        # a, a, b, a — only the second 'a' gets a sleep (after the first 'a').
        # Then 'b' breaks the run, and the next 'a' shouldn't sleep because
        # the previous DB was 'b', not 'a'.
        a1 = _make_layer("a1", "dbname='/data/a.sqlite'")
        a2 = _make_layer("a2", "dbname='/data/a.sqlite'")
        b1 = _make_layer("b1", "dbname='/data/b.sqlite'")
        a3 = _make_layer("a3", "dbname='/data/a.sqlite'")
        safe_set = MagicMock(return_value=True)

        with patch("time.sleep") as mock_sleep:
            apply_pending_subset_requests(
                [(a1, "1"), (a2, "2"), (b1, "3"), (a3, "4")],
                safe_set,
            )

        # Only one sleep: between a1 and a2. b1 is a different DB → no sleep.
        # a3 follows b1 (different DB) → no sleep.
        assert mock_sleep.call_count == 1

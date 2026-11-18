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
def _stub_qgis_symbols_on_module(monkeypatch):
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
    # This suite isolates local provider work; real remote count/error guards
    # run in check_stream_vector_filters.py with the actual adapter modules.
    root = _tch.__package__.split('.')[0]
    probe = types.ModuleType(root + '.adapters.qgis.source_capability_probe')
    probe.feature_count_or_none = lambda layer: layer.featureCount()
    errors = types.ModuleType(root + '.adapters.qgis.server_filter_translation')
    errors.last_server_filter_error = lambda layer: ''
    monkeypatch.setitem(sys.modules, probe.__name__, probe)
    monkeypatch.setitem(sys.modules, errors.__name__, errors)
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
        canvas.isFrozen.return_value = False
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

    def test_refused_filters_are_reported(self, monkeypatch):
        """2026-10-17: a filter the provider refused must not end as a silent success."""
        monkeypatch.setattr(_tch, "iface", MagicMock())
        first, second = self._shared_layers(2)
        error = MagicMock()
        error.message.return_value = "no such table: json_each"
        second.error.return_value = error
        safe_set = MagicMock(side_effect=lambda layer, expr: layer is first)
        failures = []

        with patch("time.sleep"):
            applied = apply_pending_subset_requests([(first, "1"), (second, "2")], safe_set, failures=failures)

        assert applied == 1
        assert failures == [f"{second.name()}: no such table: json_each"]


# ---------------------------------------------------------------------------
# PERF 2026-09-12: provider work after a successful setSubsetString
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestApplyPendingProviderWork:
    """No reload() after a successful apply; the count is only read where the
    provider already holds it (OGR computes it inside setSubsetString, a
    PostgreSQL count is a real query with the spatial predicate)."""

    def _apply(self, monkeypatch, layer):
        monkeypatch.setattr(_tch, "iface", MagicMock())
        # the constants module is stubbed in this suite: pin the real provider names
        monkeypatch.setattr(_tch, "QGIS_PROVIDER_POSTGRES", "postgres", raising=False)
        monkeypatch.setattr(_tch, "QGIS_PROVIDER_OGR", "ogr", raising=False)
        monkeypatch.setattr(_tch, "QGIS_PROVIDER_SPATIALITE", "spatialite", raising=False)
        return apply_pending_subset_requests([(layer, "ROWID IN (SELECT 1)")], MagicMock(return_value=True))

    def test_ogr_layer_skips_reload_and_reads_the_cached_count(self, monkeypatch):
        layer = _make_layer("batiment", "/data/bdtopo.gpkg|layername=batiment", provider="ogr")

        assert self._apply(monkeypatch, layer) == 1
        layer.reload.assert_not_called()
        layer.featureCount.assert_called_once()
        layer.updateExtents.assert_called_once()
        layer.triggerRepaint.assert_called_once()

    def test_postgres_layer_skips_reload_count_and_extents(self, monkeypatch):
        layer = _make_layer("batiment", "dbname='bd' table=\"batiment\"", provider="postgres")

        assert self._apply(monkeypatch, layer) == 1
        layer.reload.assert_not_called()
        layer.featureCount.assert_not_called()
        layer.updateExtents.assert_not_called()
        layer.triggerRepaint.assert_called_once()

    def test_spatialite_layer_still_reloads_a_non_empty_subset(self, monkeypatch):
        layer = _make_layer("batiment", "dbname='/data/x.sqlite' table=\"batiment\"", provider="spatialite")

        assert self._apply(monkeypatch, layer) == 1
        layer.reload.assert_called_once()
        layer.featureCount.assert_called_once()

    def test_already_frozen_canvas_is_left_to_its_owner(self, monkeypatch):
        """The task launcher froze the canvas for the whole task: the loop must
        neither thaw it halfway nor refresh (the owner refreshes once)."""
        fake_iface = MagicMock()
        canvas = fake_iface.mapCanvas.return_value
        canvas.isFrozen.return_value = True
        monkeypatch.setattr(_tch, "iface", fake_iface)

        layers = [_make_layer(f"l{i}", "dbname='/data/server.sqlite'") for i in range(3)]
        apply_pending_subset_requests([(l, "1") for l in layers], MagicMock(return_value=True))

        canvas.freeze.assert_not_called()
        canvas.refresh.assert_not_called()
        canvas.stopRendering.assert_called_once()

    def test_already_applied_ogr_subset_is_not_reloaded(self, monkeypatch):
        monkeypatch.setattr(_tch, "iface", MagicMock())
        monkeypatch.setattr(_tch, "QGIS_PROVIDER_POSTGRES", "postgres", raising=False)
        monkeypatch.setattr(_tch, "QGIS_PROVIDER_OGR", "ogr", raising=False)
        monkeypatch.setattr(_tch, "QGIS_PROVIDER_SPATIALITE", "spatialite", raising=False)
        layer = _make_layer("batiment", "/data/bdtopo.gpkg|layername=batiment", provider="ogr")
        layer.subsetString.return_value = "ROWID IN (SELECT 1)"
        safe_set = MagicMock(return_value=True)

        assert apply_pending_subset_requests([(layer, "ROWID IN (SELECT 1)")], safe_set) == 1

        safe_set.assert_not_called()
        layer.reload.assert_not_called()
        layer.featureCount.assert_called_once()
        layer.triggerRepaint.assert_called_once()


# ---------------------------------------------------------------------------
# apply_pending_subset_requests: a web service that refuses the keys of an exact filter
# ---------------------------------------------------------------------------

def _fallback_module():
    """adapters/qgis/extent_fallback.py, pure Python, loaded by its path (its package needs QGIS)."""
    import importlib.util
    import pathlib
    path = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "extent_fallback.py"
    spec = importlib.util.spec_from_file_location("fm_extent_fallback_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestApplyPendingRefusedKeys:
    """2026-11-15: read on a real WFS, a list of about 100 keys is refused (its address is too long for the
    server) where one of 25 is set. The cut by the extent of the source left for the layer is set instead."""

    KEYS = '"id" IN (1, 2, 3)'
    BOX = "intersects_bbox($geometry, geom_from_wkt('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))'))"

    def _run(self, monkeypatch, refused, remembered=True):
        fallback = _fallback_module()
        said = []
        monkeypatch.setattr(_tch, "_extent_fallback", lambda: fallback)
        monkeypatch.setattr(_tch, "_say_cut_by_extent", lambda layer, subset: said.append((layer.name(), subset)))
        layer = _make_layer("communes", "url='https://example.org/wfs' typename='a:b'", provider="WFS")
        if remembered:
            fallback.remember(layer.id(), self.KEYS, self.BOX)
        asked = []

        def safe_set(target, expression):
            asked.append(expression)
            return expression not in refused

        failures = []
        with patch.object(_tch, "_freeze_canvas", return_value=None):
            applied = apply_pending_subset_requests([(layer, self.KEYS)], safe_set, failures=failures)
        return applied, asked, said, failures, fallback

    def test_the_cut_by_extent_is_set_in_place_of_the_keys_the_service_refused(self, monkeypatch):
        applied, asked, said, failures, fallback = self._run(monkeypatch, refused={self.KEYS})
        assert applied == 1 and asked == [self.KEYS, self.BOX]
        assert said == [("communes", self.BOX)] and failures == []
        assert fallback.pending() == 0

    def test_keys_the_service_takes_leave_nothing_behind(self, monkeypatch):
        applied, asked, said, failures, fallback = self._run(monkeypatch, refused=set())
        assert applied == 1 and asked == [self.KEYS] and said == [] and failures == []
        assert fallback.pending() == 0  # forgotten: a later refusal of the same text finds nothing

    def test_a_service_that_refuses_both_is_reported_as_before(self, monkeypatch):
        applied, asked, said, failures, _fallback = self._run(monkeypatch, refused={self.KEYS, self.BOX})
        assert applied == 0 and asked == [self.KEYS, self.BOX] and said == []
        assert len(failures) == 1 and failures[0].startswith("communes:")

    def test_a_filter_with_no_fallback_is_reported_as_before(self, monkeypatch):
        applied, asked, said, failures, _fallback = self._run(monkeypatch, refused={self.KEYS}, remembered=False)
        assert applied == 0 and asked == [self.KEYS] and said == [] and len(failures) == 1


# ---------------------------------------------------------------------------
# apply_pending_subset_requests: the reason of a refused filter
# ---------------------------------------------------------------------------

class TestRefusedFilterReason:
    """2026-11-16: the PostgreSQL server gone, layer.error() empty: the failure line ended with
    "- " and the message bar listed the layers with no reason."""

    @pytest.fixture(autouse=True)
    def _real_watch(self, monkeypatch):
        import importlib.util
        import pathlib
        path = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "subset_failure_reason.py"
        name = _tch.__package__.split('.')[0] + '.adapters.qgis.subset_failure_reason'
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        monkeypatch.setitem(sys.modules, name, module)
        monkeypatch.setattr(_tch, "iface", MagicMock())
        self.reasons = module

    def _refused(self, provider_errors_after):
        layer = _make_layer("Cables", "dbname='wyre' table=\"wyre\".\"cable\"", provider="postgres")
        layer.subsetString.return_value = '"id" > 3'
        provider = layer.dataProvider.return_value
        provider.errors.return_value = []

        def refuse(lyr, expr):
            provider.errors.return_value = provider_errors_after
            return False
        return layer, refuse

    def test_a_lost_connection_is_the_reason(self):
        # What QgsPostgresProvider adds when QgsPostgresConn gets no result (server gone, reset failed)
        layer, refuse = self._refused(['no result buffer'])
        failures = []
        applied = apply_pending_subset_requests([(layer, '')], refuse, failures=failures)
        assert applied == 0
        assert failures == [f"Cables: {self.reasons.CONNECTION_LOST}"]

    def test_the_refused_layers_are_named_by_id(self):
        layer, refuse = self._refused(['no result buffer'])
        refused = []
        apply_pending_subset_requests([(layer, '')], refuse, failures=[], refusals=refused)
        assert refused == [("Cables_id", "Cables", self.reasons.CONNECTION_LOST)]

    def test_never_an_empty_reason(self):
        layer, refuse = self._refused([])
        failures = []
        apply_pending_subset_requests([(layer, '')], refuse, failures=failures)
        assert failures == [f"Cables: {self.reasons.NO_REASON}"]


@pytest.mark.unit
class TestFailureAfterTheSubsetIsSet:
    """2026-11-18: a reload() or a repaint that raised after setSubsetString succeeded counted the layer as
    refused: its history went back to before run() while it carried the new filter, and the message said
    "previous filter kept"."""

    @pytest.fixture(autouse=True)
    def _providers(self, monkeypatch):
        monkeypatch.setattr(_tch, "iface", MagicMock())
        monkeypatch.setattr(_tch, "QGIS_PROVIDER_POSTGRES", "postgres", raising=False)
        monkeypatch.setattr(_tch, "QGIS_PROVIDER_SPATIALITE", "spatialite", raising=False)

    def test_a_repaint_that_raises_after_the_set_is_no_refusal(self):
        layer = _make_layer("cables", "dbname='/data/x.sqlite' table=\"cables\"", provider="spatialite")
        layer.triggerRepaint.side_effect = RuntimeError("wrapped C/C++ object has been deleted")
        failures, refused = [], []
        applied = apply_pending_subset_requests([(layer, '"id" > 3')], MagicMock(return_value=True),
                                                failures=failures, refusals=refused)
        assert (applied, failures, refused) == (1, [], [])

    def test_a_repaint_that_raises_on_a_filter_already_set_is_no_refusal(self):
        layer = _make_layer("cables", "dbname='bd' table=\"cables\"", provider="postgres")
        layer.subsetString.return_value = '"id" > 3'
        layer.triggerRepaint.side_effect = RuntimeError("gone")
        failures, refused = [], []
        assert apply_pending_subset_requests([(layer, '"id" > 3')], MagicMock(return_value=True),
                                             failures=failures, refusals=refused) == 1
        assert (failures, refused) == ([], [])

    def test_a_set_that_raises_is_still_a_refusal(self):
        layer = _make_layer("cables", "dbname='bd' table=\"cables\"", provider="postgres")
        failures, refused = [], []
        applied = apply_pending_subset_requests([(layer, '"id" > 3')], MagicMock(side_effect=RuntimeError("boom")),
                                                failures=failures, refusals=refused)
        assert applied == 0
        assert refused == [("cables_id", "cables", "boom")]

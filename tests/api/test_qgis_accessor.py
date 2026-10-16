# -*- coding: utf-8 -*-
"""Issue #45 — QGISFilterMateAccessor unit tests.

The accessor is constructed in production from the running plugin, so
the QGIS dependencies (QgsProject, QgsVectorLayer, FilterMatePublicAPI,
HistoryService, FavoritesService) are all live there. Here we drive
each method through MagicMock stand-ins; the goal is to pin the
delegation contract and the error-handling envelope so a future PublicAPI
or HistoryService change can't silently desynchronise the bridge.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from filtermate_api.accessor import HistoryStep, LayerSummary  # noqa: E402


# ---------------------------------------------------------------------------
# Per-test qgis.core stubbing.
#
# Module-level qgis stubs would clobber the global mocks installed by
# tests/conftest.py and break sibling test files (test_public_api.py,
# test_expression_*.py) at collection time. We install our stubs lazily,
# inside an autouse fixture, and restore the originals on teardown.
# ---------------------------------------------------------------------------

class _DefaultVectorLayer:
    """Sentinel class registered as ``qgis.core.QgsVectorLayer`` so the
    ``isinstance`` check inside :meth:`QGISFilterMateAccessor.list_layers`
    can be exercised under the test mocks."""


from filtermate_api.qgis_accessor import QGISFilterMateAccessor  # noqa: E402


def _install_qgis_stubs(project, vector_layer_cls):
    """Replace ``sys.modules['qgis.core']`` with a stub returning ``project``
    from ``QgsProject.instance()``. Returns the previously-installed
    modules so a fixture can restore them on teardown.
    """
    snapshot = {
        "qgis": sys.modules.get("qgis"),
        "qgis.core": sys.modules.get("qgis.core"),
    }
    qgis_core = types.ModuleType("qgis.core")
    qgis_core.QgsProject = MagicMock()
    qgis_core.QgsProject.instance = MagicMock(return_value=project)
    qgis_core.QgsVectorLayer = vector_layer_cls
    sys.modules["qgis"] = types.ModuleType("qgis")
    sys.modules["qgis.core"] = qgis_core
    return snapshot


def _restore_qgis_stubs(snapshot):
    for key, module in snapshot.items():
        if module is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = module


@pytest.fixture(autouse=True)
def _qgis_isolation():
    """Restore the global qgis mocks after each test so sibling test
    modules don't see our partial stubs."""
    snapshot = {
        "qgis": sys.modules.get("qgis"),
        "qgis.core": sys.modules.get("qgis.core"),
    }
    yield
    _restore_qgis_stubs(snapshot)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _MockLayer(_DefaultVectorLayer):
    """Real subclass of the stub QgsVectorLayer so isinstance() passes,
    but with arbitrary MagicMock attributes attached for fluent setup."""


def _make_layer(*, layer_id, name, subset="", provider="ogr",
                feature_count=10, geom_type=2, crs_authid="EPSG:2154"):
    layer = _MockLayer()
    layer.id = MagicMock(return_value=layer_id)
    layer.name = MagicMock(return_value=name)
    layer.providerType = MagicMock(return_value=provider)
    layer.featureCount = MagicMock(return_value=feature_count)
    layer.geometryType = MagicMock(return_value=geom_type)
    layer.subsetString = MagicMock(return_value=subset)
    layer.setSubsetString = MagicMock(return_value=True)
    layer.isValid = MagicMock(return_value=True)
    crs = MagicMock()
    crs.authid = MagicMock(return_value=crs_authid)
    layer.crs = MagicMock(return_value=crs)
    return layer


@pytest.fixture
def project_with_layers():
    """Stub QgsProject that exposes a fixed set of vector layers."""
    layer_a = _make_layer(layer_id="L1", name="communes")
    layer_b = _make_layer(layer_id="L2", name="roads", geom_type=1)
    project = MagicMock()
    project.mapLayers.return_value = {"L1": layer_a, "L2": layer_b}
    project.mapLayer = lambda lid: {"L1": layer_a, "L2": layer_b}.get(lid)
    return project, layer_a, layer_b


@pytest.fixture
def public_api():
    """Stub PublicAPI exposing apply_filter / get_active_filters."""
    api = MagicMock()
    api.apply_filter.return_value = True
    api.get_active_filters.return_value = {}
    return api


@pytest.fixture
def plugin():
    """Stub FilterMate plugin, wired like the real one: history_manager and
    favorites_manager live on its application object (``plugin.app``)."""
    app = MagicMock()
    app.history_manager = MagicMock()
    app.favorites_manager = MagicMock()
    app.favorites_manager.get_all_favorites.return_value = []
    return types.SimpleNamespace(app=app)


@pytest.fixture
def accessor(public_api, plugin, project_with_layers):
    project, _, _ = project_with_layers
    _install_qgis_stubs(project, _DefaultVectorLayer)
    return QGISFilterMateAccessor(public_api=public_api, plugin=plugin)


# ---------------------------------------------------------------------------
# list_layers
# ---------------------------------------------------------------------------

class TestListLayers:
    def test_returns_each_vector_layer_as_summary(self, accessor):
        layers = accessor.list_layers()
        assert isinstance(layers, list)
        names = [layer.name for layer in layers]
        assert names == ["communes", "roads"]
        assert all(isinstance(layer, LayerSummary) for layer in layers)

    def test_skips_invalid_layers(self, public_api, plugin):
        good = _make_layer(layer_id="L1", name="ok")
        bad = _make_layer(layer_id="L2", name="broken")
        bad.isValid.return_value = False
        project = MagicMock()
        project.mapLayers.return_value = {"L1": good, "L2": bad}
        _install_qgis_stubs(project, _DefaultVectorLayer)
        accessor = QGISFilterMateAccessor(public_api=public_api, plugin=plugin)
        names = [layer.name for layer in accessor.list_layers()]
        assert names == ["ok"]

    def test_skips_non_vector_layers(self, public_api, plugin):
        # A raster layer (not isinstance of _DefaultVectorLayer) must be ignored.
        raster = MagicMock()  # not a _DefaultVectorLayer instance
        vector = _make_layer(layer_id="L1", name="ok")
        project = MagicMock()
        project.mapLayers.return_value = {"R": raster, "L1": vector}
        _install_qgis_stubs(project, _DefaultVectorLayer)
        accessor = QGISFilterMateAccessor(public_api=public_api, plugin=plugin)
        names = [layer.name for layer in accessor.list_layers()]
        assert names == ["ok"]

    def test_active_filter_flag_reflects_subset_string(self, public_api, plugin):
        layer = _make_layer(layer_id="L1", name="communes", subset='"x" = 1')
        project = MagicMock()
        project.mapLayers.return_value = {"L1": layer}
        _install_qgis_stubs(project, _DefaultVectorLayer)
        accessor = QGISFilterMateAccessor(public_api=public_api, plugin=plugin)
        result = accessor.list_layers()[0]
        assert result.has_active_filter is True
        assert result.active_filter_expression == '"x" = 1'

    def test_overlays_active_filter_from_public_api(self, public_api, plugin):
        # PublicAPI claims a filter on a layer whose subsetString is empty —
        # the API value wins (it's the source of truth for active filters).
        layer = _make_layer(layer_id="L1", name="communes", subset="")
        project = MagicMock()
        project.mapLayers.return_value = {"L1": layer}
        _install_qgis_stubs(project, _DefaultVectorLayer)
        public_api.get_active_filters.return_value = {"communes": '"y" = 2'}
        accessor = QGISFilterMateAccessor(public_api=public_api, plugin=plugin)
        result = accessor.list_layers()[0]
        # subset is empty so the layer-level flag is False, but the API
        # overlay surfaces the expression.
        assert result.active_filter_expression == '"y" = 2'


# ---------------------------------------------------------------------------
# apply_filter / get_active_filters / get_filter_status
# ---------------------------------------------------------------------------

class TestApplyAndStatus:
    def test_apply_delegates_to_public_api(self, accessor, public_api):
        ok = accessor.apply_filter("communes", '"x" = 1', "narractive")
        assert ok is True
        public_api.apply_filter.assert_called_once_with(
            layer_name="communes",
            filter_expr='"x" = 1',
            source_plugin="narractive",
        )

    def test_apply_failure_records_error(self, accessor, public_api):
        public_api.apply_filter.return_value = False
        ok = accessor.apply_filter("ghost", "expr", "rest_api")
        assert ok is False
        status = accessor.get_filter_status()
        assert status.status == "error"
        assert "ghost" in status.last_error

    def test_status_reflects_apply_metadata(self, accessor, public_api):
        public_api.get_active_filters.return_value = {"communes": '"x" = 1'}
        accessor.apply_filter("communes", '"x" = 1', "narractive")
        status = accessor.get_filter_status()
        assert status.status == "completed"
        assert status.active_filters_count == 1
        assert status.last_applied_layer == "communes"
        assert status.last_applied_source == "narractive"
        assert status.last_applied_at is not None

    def test_status_idle_when_no_active_filters(self, accessor):
        status = accessor.get_filter_status()
        assert status.status == "idle"
        assert status.active_filters == {}

    def test_get_active_filters_swallows_exceptions(self, accessor, public_api):
        public_api.get_active_filters.side_effect = RuntimeError("boom")
        # Must not raise — REST API can't 500 because of a plugin glitch.
        assert accessor.get_active_filters() == {}


# ---------------------------------------------------------------------------
# undo / redo
# ---------------------------------------------------------------------------

class TestUndoRedo:
    def test_undo_returns_none_when_history_empty(self, accessor, plugin):
        plugin.app.history_manager.undo.return_value = None
        assert accessor.undo_filter() is None

    def test_undo_reapplies_previous_filters_on_layers(self, accessor, plugin,
                                                      project_with_layers):
        _, layer_a, _ = project_with_layers
        entry = MagicMock()
        entry.previous_filters = (("L1", '"prev" = 1'),)
        entry.expression = '"x" = 1'
        entry.layer_ids = ("L1",)
        plugin.app.history_manager.undo.return_value = entry

        step = accessor.undo_filter()

        assert isinstance(step, HistoryStep)
        layer_a.setSubsetString.assert_called_once_with('"prev" = 1')
        assert step.layer_name == "communes"
        assert step.expression == '"prev" = 1'
        assert step.is_clear is False

    def test_undo_clear_step_marks_is_clear(self, accessor, plugin,
                                            project_with_layers):
        _, layer_a, _ = project_with_layers
        entry = MagicMock()
        entry.previous_filters = (("L1", ""),)
        entry.layer_ids = ("L1",)
        entry.expression = ""
        plugin.app.history_manager.undo.return_value = entry

        step = accessor.undo_filter()
        layer_a.setSubsetString.assert_called_once_with("")
        assert step.is_clear is True

    def test_redo_calls_history_redo(self, accessor, plugin):
        plugin.app.history_manager.redo.return_value = None
        accessor.redo_filter()
        plugin.app.history_manager.redo.assert_called_once()

    def test_undo_handles_missing_history_manager_gracefully(self, public_api,
                                                             plugin):
        # Plugin without history_manager — undo returns None without raising.
        del plugin.app.history_manager
        accessor = QGISFilterMateAccessor(public_api=public_api, plugin=plugin)
        assert accessor.undo_filter() is None


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------

class TestFavorites:
    def _favorite(self, **kwargs):
        fav = MagicMock()
        for key, value in kwargs.items():
            setattr(fav, key, value)
        return fav

    def test_list_favorites_maps_service_entries(self, accessor, plugin):
        plugin.app.favorites_manager.get_all_favorites.return_value = [
            self._favorite(
                favorite_id="fav-1", name="N", description="D",
                layer_name="communes", expression='"x" = 1',
            ),
        ]
        favorites = accessor.list_favorites()
        assert len(favorites) == 1
        assert favorites[0].favorite_id == "fav-1"
        assert favorites[0].layer_name == "communes"

    def test_list_favorites_raises_unavailable_when_service_missing(
        self, public_api, plugin
    ):
        # P1-API-HARDEN (audit 2026-04-29): a missing FavoritesService is
        # "store not ready" — distinct from "no favorites configured".
        # The router translates this to 503 + Retry-After.
        from filtermate_api.accessor import FavoritesUnavailable

        del plugin.app.favorites_manager
        accessor = QGISFilterMateAccessor(public_api=public_api, plugin=plugin)
        with pytest.raises(FavoritesUnavailable):
            accessor.list_favorites()

    def test_apply_favorite_replays_it_through_operations(self, accessor, plugin, public_api, monkeypatch):
        # Audit 2026-10: every favorite (vector ones too) is replayed by
        # operations.apply_favorite, like the dock menu, the Python API and
        # Processing: remote layers, signature / id / name resolution.
        import filtermate_api.qgis_accessor as qgis_accessor
        operations = MagicMock()
        operations.busy_reason.return_value = ""
        operations.apply_favorite.return_value = types.SimpleNamespace(
            error="", done={"L1": "communes", "L2": "roads"}, done_names=["communes", "roads"], details={})
        monkeypatch.setattr(qgis_accessor, "_plugin_module", lambda name: operations)
        plugin.app.favorites_manager.get_favorite.return_value = self._favorite(
            favorite_id="fav-1", layer_name="communes",
            expression='"x" = 1', name="N",
        )
        step = accessor.apply_favorite("fav-1")
        assert step is not None
        assert step.layer_name == "communes"
        assert step.expression == '"x" = 1'
        operations.apply_favorite.assert_called_once_with("fav-1", plugin.app.favorites_manager)
        public_api.apply_filter.assert_not_called()
        # The bridge stamps the apply with `favorite:<id>` in /filters/status.
        assert accessor.get_filter_status().last_applied_source == "favorite:fav-1"

    def test_apply_unknown_favorite_returns_none(self, accessor, plugin):
        plugin.app.favorites_manager.get_favorite.return_value = None
        assert accessor.apply_favorite("nope") is None

    def test_apply_orphan_favorite_returns_none(self, accessor, plugin):
        # Favorite with no layer_name can't be applied.
        plugin.app.favorites_manager.get_favorite.return_value = self._favorite(
            favorite_id="fav-orphan", layer_name="", expression="", name="N",
        )
        assert accessor.apply_favorite("fav-orphan") is None


# ---------------------------------------------------------------------------
# Audit 2026-10 (FilterMate 5)
# ---------------------------------------------------------------------------

class TestServicesOnThePluginApp:
    """The real plugin carries no favorites_manager / history_manager: its app does."""

    def test_plugin_without_app_has_no_favorites_store(self, public_api):
        from filtermate_api.accessor import FavoritesUnavailable
        accessor = QGISFilterMateAccessor(public_api=public_api, plugin=types.SimpleNamespace(app=None))
        with pytest.raises(FavoritesUnavailable):
            accessor.list_favorites()

    def test_services_found_on_the_plugin_itself_too(self, public_api):
        # An embedding that passes the app (or a plugin carrying them) keeps working.
        app = MagicMock()
        app.history_manager.undo.return_value = None
        app.favorites_manager.get_all_favorites.return_value = []
        accessor = QGISFilterMateAccessor(public_api=public_api, plugin=app)
        assert accessor.list_favorites() == []
        assert accessor.undo_filter() is None
        app.history_manager.undo.assert_called_once()


class _MainThreadSpy:
    """Stand-in for run_on_main_thread: records that QGIS is only touched inside it."""

    def __init__(self):
        self.inside = False
        self.calls = 0

    def __call__(self, fn, *args, timeout=None, **kwargs):
        self.calls += 1
        self.inside = True
        try:
            return fn(*args, **kwargs)
        finally:
            self.inside = False

    def guard(self, value=None):
        """side_effect asserting the call happens on the (simulated) main thread."""
        def _check(*_args, **_kwargs):
            assert self.inside, "QGIS touched outside run_on_main_thread"
            return value
        return _check


class TestEverythingOnTheMainThread:
    @pytest.fixture
    def spy(self, monkeypatch):
        import filtermate_api.qgis_accessor as qgis_accessor
        spy = _MainThreadSpy()
        monkeypatch.setattr(qgis_accessor, "run_on_main_thread", spy)
        return spy

    def test_list_layers(self, spy, public_api, plugin, project_with_layers):
        project, layer_a, _ = project_with_layers
        project.mapLayers.side_effect = spy.guard(project.mapLayers.return_value)
        layer_a.featureCount.side_effect = spy.guard(10)
        public_api.get_active_filters.side_effect = spy.guard({})
        _install_qgis_stubs(project, _DefaultVectorLayer)
        accessor = QGISFilterMateAccessor(public_api=public_api, plugin=plugin)
        assert [layer.name for layer in accessor.list_layers()] == ["communes", "roads"]

    def test_active_filters_and_status(self, spy, accessor, public_api):
        public_api.get_active_filters.side_effect = spy.guard({"communes": "x = 1"})
        assert accessor.get_active_filters() == {"communes": "x = 1"}
        assert accessor.get_filter_status().active_filters_count == 1

    def test_favorites(self, spy, accessor, plugin):
        plugin.app.favorites_manager.get_all_favorites.side_effect = spy.guard([])
        plugin.app.favorites_manager.get_favorite.side_effect = spy.guard(None)
        assert accessor.list_favorites() == []
        assert accessor.apply_favorite("fav-1") is None

    def test_undo_and_redo_pop_the_shared_history_on_the_main_thread(self, spy, accessor, plugin):
        # The history is shared with the dock (buttons, change callbacks).
        plugin.app.history_manager.undo.side_effect = spy.guard(None)
        plugin.app.history_manager.redo.side_effect = spy.guard(None)
        assert accessor.undo_filter() is None
        assert accessor.redo_filter() is None
        plugin.app.history_manager.undo.assert_called_once()
        plugin.app.history_manager.redo.assert_called_once()


class TestBusyIsNeverAnsweredAsEmpty:
    @pytest.fixture
    def busy(self, monkeypatch):
        import filtermate_api.qgis_accessor as qgis_accessor
        from filtermate_api.main_thread import QGISBusy

        def _busy(*_args, **_kwargs):
            raise QGISBusy("main thread busy")
        monkeypatch.setattr(qgis_accessor, "run_on_main_thread", _busy)
        return QGISBusy

    def test_filter_state(self, busy, accessor):
        with pytest.raises(busy):
            accessor.get_filter_state()

    def test_active_filters(self, busy, accessor):
        with pytest.raises(busy):
            accessor.get_active_filters()

    def test_layers(self, busy, accessor):
        with pytest.raises(busy):
            accessor.list_layers()


def _operations(**overrides):
    """Fake ``adapters.public_api.operations`` + ``core.domain.api_requests`` for _plugin_module."""
    module = MagicMock()
    module.busy_reason.return_value = ""
    module.raster_selection_from_dict.side_effect = lambda value: value
    module.point_cloud_criteria_from_dict.side_effect = lambda value: value
    for name, value in overrides.items():
        setattr(module, name, value)
    return module


def _report(done=None, failed=None, skipped=None, error="", details=None):
    done = dict(done or {})
    return types.SimpleNamespace(done=done, done_names=list(done.values()), failed=dict(failed or {}),
                                 skipped=dict(skipped or {}), error=error, outputs={}, details=dict(details or {}))


class TestOperationsThroughTheAccessor:
    @pytest.fixture
    def operations(self, monkeypatch):
        import filtermate_api.qgis_accessor as qgis_accessor
        module = _operations()
        monkeypatch.setattr(qgis_accessor, "_plugin_module", lambda name: module)
        return module

    def test_source_resolved_by_id_or_name(self, accessor, operations, project_with_layers):
        _, layer_a, _ = project_with_layers
        operations.resolve_layer.return_value = layer_a
        operations.cross_filter.return_value = _report(done={"L2": "roads"})
        result = accessor.cross_filter("L1", ["roads"], ["Intersect"])
        assert result.filtered == ["roads"]
        assert operations.resolve_layer.call_args.args[0] == "L1"
        assert operations.cross_filter.call_args.args[0] is layer_a

    def test_unknown_source_is_none(self, accessor, operations):
        operations.resolve_layer.return_value = None
        assert accessor.cross_filter("ghost", ["roads"], ["Intersect"]) is None

    def test_skipped_layers_stay_apart_from_failed(self, accessor, operations, project_with_layers):
        operations.resolve_layer.return_value = project_with_layers[1]
        operations.cross_filter.return_value = _report(done={"L2": "roads"}, failed={"mnt": "clip failed"},
                                                       skipped={"ghost": "layer not found"})
        result = accessor.cross_filter("communes", ["roads", "mnt", "ghost"], ["Intersect"])
        assert result.failed == {"mnt": "clip failed"}
        assert result.skipped == {"ghost": "layer not found"}

    def test_busy_report_raises_qgis_busy(self, accessor, operations, project_with_layers):
        from filtermate_api.main_thread import QGISBusy
        operations.resolve_layer.return_value = project_with_layers[1]
        operations.cross_filter.return_value = _report(error="a FilterMate filter is still running",
                                                       details={"busy": True})
        with pytest.raises(QGISBusy, match="still running"):
            accessor.cross_filter("communes", ["roads"], ["Intersect"])

    def test_apply_filter_refused_while_filtermate_is_busy(self, accessor, operations, public_api):
        from filtermate_api.main_thread import QGISBusy
        operations.busy_reason.return_value = "a FilterMate filter is still running"
        with pytest.raises(QGISBusy):
            accessor.apply_filter("communes", "x = 1", "rest_api")
        public_api.apply_filter.assert_not_called()

    def test_undo_refused_while_filtermate_is_busy(self, accessor, operations, plugin):
        from filtermate_api.main_thread import QGISBusy
        operations.busy_reason.return_value = "a FilterMate filter is still running"
        with pytest.raises(QGISBusy):
            accessor.undo_filter()
        plugin.app.history_manager.undo.assert_not_called()

    def test_undo_is_the_dock_undo_whatever_the_api_did_before(self, accessor, operations, plugin,
                                                               project_with_layers):
        # Review 2026-10: no guard pretending the API's changes are in this
        # history (apply_filter records nothing there either): /filters/undo
        # is the dock's vector Undo, documented as such.
        operations.resolve_layer.return_value = project_with_layers[1]
        operations.cross_filter.return_value = _report(done={"L2": "roads"})
        accessor.cross_filter("communes", ["roads"], ["Intersect"])
        plugin.app.history_manager.undo.return_value = None
        assert accessor.undo_filter() is None
        plugin.app.history_manager.undo.assert_called_once()


class TestGeometryTypeNames:
    """QGIS 4 / PyQt6: Qgis.GeometryType is an enum, no longer an int."""

    def test_pyqt6_enum_and_pyqt5_int(self):
        import enum
        from filtermate_api.qgis_accessor import _geometry_type_name

        class GeometryType(enum.Enum):
            Point = 0
            Line = 1
            Polygon = 2

        assert _geometry_type_name(GeometryType.Polygon) == "Polygon"
        assert _geometry_type_name(GeometryType.Line) == "LineString"
        assert _geometry_type_name(2) == "Polygon"
        assert _geometry_type_name(None) == "Unknown"
        assert _geometry_type_name(-1) == "Unknown"

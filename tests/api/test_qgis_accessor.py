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
    """Stub plugin singleton with history_manager + favorites_manager."""
    plug = MagicMock()
    plug.history_manager = MagicMock()
    plug.favorites_manager = MagicMock()
    plug.favorites_manager.get_all_favorites.return_value = []
    return plug


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
        plugin.history_manager.undo.return_value = None
        assert accessor.undo_filter() is None

    def test_undo_reapplies_previous_filters_on_layers(self, accessor, plugin,
                                                      project_with_layers):
        _, layer_a, _ = project_with_layers
        entry = MagicMock()
        entry.previous_filters = (("L1", '"prev" = 1'),)
        entry.expression = '"x" = 1'
        entry.layer_ids = ("L1",)
        plugin.history_manager.undo.return_value = entry

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
        plugin.history_manager.undo.return_value = entry

        step = accessor.undo_filter()
        layer_a.setSubsetString.assert_called_once_with("")
        assert step.is_clear is True

    def test_redo_calls_history_redo(self, accessor, plugin):
        plugin.history_manager.redo.return_value = None
        accessor.redo_filter()
        plugin.history_manager.redo.assert_called_once()

    def test_undo_handles_missing_history_manager_gracefully(self, public_api,
                                                             plugin):
        # Plugin without history_manager — undo returns None without raising.
        del plugin.history_manager
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
        plugin.favorites_manager.get_all_favorites.return_value = [
            self._favorite(
                favorite_id="fav-1", name="N", description="D",
                layer_name="communes", expression='"x" = 1',
            ),
        ]
        favorites = accessor.list_favorites()
        assert len(favorites) == 1
        assert favorites[0].favorite_id == "fav-1"
        assert favorites[0].layer_name == "communes"

    def test_list_favorites_returns_empty_when_service_missing(
        self, public_api, plugin
    ):
        del plugin.favorites_manager
        accessor = QGISFilterMateAccessor(public_api=public_api, plugin=plugin)
        assert accessor.list_favorites() == []

    def test_apply_favorite_delegates_through_public_api(self, accessor,
                                                        plugin, public_api):
        plugin.favorites_manager.get_favorite.return_value = self._favorite(
            favorite_id="fav-1", layer_name="communes",
            expression='"x" = 1', name="N",
        )
        step = accessor.apply_favorite("fav-1")
        assert step is not None
        assert step.layer_name == "communes"
        assert step.expression == '"x" = 1'
        # The bridge stamps the apply with `favorite:<id>` so the plugin
        # can distinguish API-driven applies in its log/signal stream.
        public_api.apply_filter.assert_called_once_with(
            layer_name="communes",
            filter_expr='"x" = 1',
            source_plugin="favorite:fav-1",
        )

    def test_apply_unknown_favorite_returns_none(self, accessor, plugin):
        plugin.favorites_manager.get_favorite.return_value = None
        assert accessor.apply_favorite("nope") is None

    def test_apply_orphan_favorite_returns_none(self, accessor, plugin):
        # Favorite with no layer_name can't be applied.
        plugin.favorites_manager.get_favorite.return_value = self._favorite(
            favorite_id="fav-orphan", layer_name="", expression="", name="N",
        )
        assert accessor.apply_favorite("fav-orphan") is None

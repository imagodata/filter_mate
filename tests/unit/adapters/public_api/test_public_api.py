# -*- coding: utf-8 -*-
"""
Tests for FilterMate Public API Adapter.

These tests mock QGIS dependencies so they run without a QGIS environment.
They verify the public API contract defined in IFilterMatePublicAPI.

Modules tested:
    - adapters.public_api.filter_mate_public_api (FilterMatePublicAPI)
    - core.ports.public_api_port (IFilterMatePublicAPI)
"""
import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock, patch, mock_open, call

import pytest


# =========================================================================
# IFilterMatePublicAPI port tests (pure Python, no QGIS)
# =========================================================================

class TestIFilterMatePublicAPIContract:
    """Tests for the abstract port interface."""

    def test_port_is_abstract(self):
        """IFilterMatePublicAPI cannot be instantiated directly."""
        from core.ports.public_api_port import IFilterMatePublicAPI

        with pytest.raises(TypeError):
            IFilterMatePublicAPI()

    def test_port_defines_required_methods(self):
        """Port defines all expected abstract methods."""
        from core.ports.public_api_port import IFilterMatePublicAPI
        import inspect

        methods = {
            name for name, _ in inspect.getmembers(
                IFilterMatePublicAPI, predicate=inspect.isfunction
            )
        }
        assert "apply_filter" in methods
        assert "get_active_filters" in methods
        assert "clear_filter" in methods
        assert "clear_all_filters" in methods
        assert "get_version" in methods

    def test_concrete_subclass_must_implement_all(self):
        """A subclass missing abstract methods cannot be instantiated."""
        from core.ports.public_api_port import IFilterMatePublicAPI

        class IncompleteAPI(IFilterMatePublicAPI):
            def apply_filter(self, layer_name, filter_expr, source_plugin="external"):
                return True
            # Missing: get_active_filters, clear_filter, clear_all_filters, get_version

        with pytest.raises(TypeError):
            IncompleteAPI()


# =========================================================================
# Module-level loading of FilterMatePublicAPI via spec_from_file_location
# (follows the pattern from tests/unit/adapters/backends/ogr/test_filter_executor.py)
# =========================================================================

ROOT = "filter_mate"


def _ensure_public_api_mocks():
    """Pre-mock all parent modules so relative imports resolve."""
    if ROOT not in sys.modules:
        fm = types.ModuleType(ROOT)
        fm.__path__ = []
        fm.__package__ = ROOT
        sys.modules[ROOT] = fm

    # Mock the infrastructure.logging module
    mock_logger = MagicMock()
    mock_logging_mod = MagicMock()
    mock_logging_mod.get_logger.return_value = mock_logger

    mocks = {
        f"{ROOT}.core": MagicMock(),
        f"{ROOT}.core.ports": MagicMock(),
        f"{ROOT}.core.ports.public_api_port": MagicMock(),
        f"{ROOT}.infrastructure": MagicMock(),
        f"{ROOT}.infrastructure.logging": mock_logging_mod,
        f"{ROOT}.infrastructure.database": MagicMock(),
        f"{ROOT}.infrastructure.database.sql_utils": MagicMock(),
        f"{ROOT}.adapters": MagicMock(),
        f"{ROOT}.adapters.public_api": MagicMock(),
    }

    # Wire up safe_set_subset_string mock
    mocks[f"{ROOT}.infrastructure.database.sql_utils"].safe_set_subset_string = MagicMock(return_value=True)

    # Wire up IFilterMatePublicAPI from the real port module
    from core.ports.public_api_port import IFilterMatePublicAPI
    mocks[f"{ROOT}.core.ports.public_api_port"].IFilterMatePublicAPI = IFilterMatePublicAPI

    for name, mock_obj in mocks.items():
        if name not in sys.modules:
            sys.modules[name] = mock_obj


_ensure_public_api_mocks()

# Load the module file directly
_api_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..",
    "adapters", "public_api", "filter_mate_public_api.py"
))

_spec = importlib.util.spec_from_file_location(
    f"{ROOT}.adapters.public_api.filter_mate_public_api",
    _api_path,
)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = f"{ROOT}.adapters.public_api"
sys.modules[_mod.__name__] = _mod
_spec.loader.exec_module(_mod)

FilterMatePublicAPI = _mod.FilterMatePublicAPI


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def mock_plugin():
    """Return a mock FilterMate plugin instance."""
    plugin = MagicMock()
    plugin.plugin_dir = "/fake/plugin/dir"
    return plugin


def _make_layer(name="test_layer", valid=True, subset="", set_subset_ok=True):
    """Create a mock vector layer."""
    layer = MagicMock()
    layer.name.return_value = name
    layer.isValid.return_value = valid
    layer.subsetString.return_value = subset
    layer.setSubsetString.return_value = set_subset_ok
    return layer


def _make_api(mock_plugin):
    """Create a FilterMatePublicAPI with mocked signals for assertion."""
    api = FilterMatePublicAPI(mock_plugin)
    # Replace mocked signals with fresh MagicMocks so we can assert on emit
    api.filter_applied = MagicMock()
    api.filter_cleared = MagicMock()
    api.error_occurred = MagicMock()
    api.about_to_unload = MagicMock()
    return api


# =========================================================================
# FilterMatePublicAPI adapter tests
# =========================================================================

class TestFilterMatePublicAPIApplyFilter:
    """Tests for apply_filter method."""

    def test_apply_filter_success(self, mock_plugin):
        """apply_filter returns True and emits filter_applied signal."""
        layer = _make_layer("communes", valid=True)

        project = MagicMock()
        project.mapLayersByName.return_value = [layer]

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project
            with patch.object(_mod, "QgsVectorLayer", new=type(layer)):
                api = _make_api(mock_plugin)

                result = api.apply_filter(
                    "communes", "population > 10000", "narractive"
                )

                assert result is True
                api.filter_applied.emit.assert_called_once_with(
                    "communes", "population > 10000", "narractive"
                )

    def test_apply_filter_layer_not_found(self, mock_plugin):
        """apply_filter returns False and emits error when layer not found."""
        project = MagicMock()
        project.mapLayersByName.return_value = []

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project

            api = _make_api(mock_plugin)
            result = api.apply_filter("nonexistent", "id = 1")

            assert result is False
            api.error_occurred.emit.assert_called_once()
            args = api.error_occurred.emit.call_args[0]
            assert "not found" in args[1].lower()

    def test_apply_filter_invalid_layer(self, mock_plugin):
        """apply_filter returns False when layer is invalid."""
        layer = _make_layer("bad_layer", valid=False)

        project = MagicMock()
        project.mapLayersByName.return_value = [layer]

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project
            with patch.object(_mod, "QgsVectorLayer", new=type(layer)):
                api = _make_api(mock_plugin)

                result = api.apply_filter("bad_layer", "id = 1")
                assert result is False
                api.error_occurred.emit.assert_called_once()

    def test_apply_filter_subset_failure(self, mock_plugin):
        """apply_filter returns False when setSubsetString fails."""
        layer = _make_layer("communes", valid=True, set_subset_ok=False)

        project = MagicMock()
        project.mapLayersByName.return_value = [layer]

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project
            with patch.object(_mod, "QgsVectorLayer", new=type(layer)):
                api = _make_api(mock_plugin)
                # Force _safe_set_subset to return False
                api._safe_set_subset = MagicMock(return_value=False)

                result = api.apply_filter("communes", "bad sql")
                assert result is False
                api.error_occurred.emit.assert_called_once()
                api.filter_applied.emit.assert_not_called()

    def test_apply_filter_default_source_plugin(self, mock_plugin):
        """apply_filter uses 'external' as default source_plugin."""
        layer = _make_layer("communes", valid=True)

        project = MagicMock()
        project.mapLayersByName.return_value = [layer]

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project
            with patch.object(_mod, "QgsVectorLayer", new=type(layer)):
                api = _make_api(mock_plugin)
                api.apply_filter("communes", "id = 1")

                api.filter_applied.emit.assert_called_once()
                args = api.filter_applied.emit.call_args[0]
                assert args[2] == "external"


class TestFilterMatePublicAPIClearFilter:
    """Tests for clear_filter method."""

    def test_clear_filter_success(self, mock_plugin):
        """clear_filter returns True and emits filter_cleared signal."""
        layer = _make_layer("communes", valid=True)

        project = MagicMock()
        project.mapLayersByName.return_value = [layer]

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project
            with patch.object(_mod, "QgsVectorLayer", new=type(layer)):
                api = _make_api(mock_plugin)

                result = api.clear_filter("communes")

                assert result is True
                layer.setSubsetString.assert_called_with("")
                api.filter_cleared.emit.assert_called_once_with(
                    "communes", "external"
                )

    def test_clear_filter_layer_not_found(self, mock_plugin):
        """clear_filter returns False when layer not found."""
        project = MagicMock()
        project.mapLayersByName.return_value = []

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project

            api = _make_api(mock_plugin)
            result = api.clear_filter("nonexistent")
            assert result is False
            api.error_occurred.emit.assert_called_once()


class TestFilterMatePublicAPIClearAllFilters:
    """Tests for clear_all_filters method."""

    def test_clear_all_filters(self, mock_plugin):
        """clear_all_filters clears all layers with active filters."""
        filtered_layer = _make_layer("filtered", valid=True, subset="id > 10")
        clean_layer = _make_layer("clean", valid=True, subset="")

        project = MagicMock()
        project.mapLayers.return_value = {
            "l1": filtered_layer, "l2": clean_layer
        }

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project
            with patch.object(
                _mod, "QgsVectorLayer", new=type(filtered_layer)
            ):
                api = _make_api(mock_plugin)
                count = api.clear_all_filters()

                assert count == 1
                filtered_layer.setSubsetString.assert_called_once_with("")
                clean_layer.setSubsetString.assert_not_called()

    def test_clear_all_filters_none_active(self, mock_plugin):
        """clear_all_filters returns 0 when no filters active."""
        project = MagicMock()
        project.mapLayers.return_value = {}

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project

            api = _make_api(mock_plugin)
            count = api.clear_all_filters()
            assert count == 0


class TestFilterMatePublicAPIGetActiveFilters:
    """Tests for get_active_filters method."""

    def test_get_active_filters(self, mock_plugin):
        """get_active_filters returns dict of filtered layers."""
        layer1 = _make_layer("communes", valid=True, subset="population > 5000")
        layer2 = _make_layer("routes", valid=True, subset="")

        project = MagicMock()
        project.mapLayers.return_value = {"l1": layer1, "l2": layer2}

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project
            with patch.object(_mod, "QgsVectorLayer", new=type(layer1)):
                api = _make_api(mock_plugin)
                filters = api.get_active_filters()

                assert filters == {"communes": "population > 5000"}

    def test_get_active_filters_empty(self, mock_plugin):
        """get_active_filters returns empty dict when no filters active."""
        project = MagicMock()
        project.mapLayers.return_value = {}

        with patch.object(_mod, "QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = project

            api = _make_api(mock_plugin)
            filters = api.get_active_filters()
            assert filters == {}


class TestFilterMatePublicAPIGetVersion:
    """Tests for get_version method."""

    def test_get_version_reads_metadata(self, mock_plugin):
        """get_version reads version from metadata.txt."""
        mock_plugin.plugin_dir = "/fake/dir"
        metadata_content = "name=FilterMate\nversion=4.6.1\nauthor=imagodata\n"

        api = _make_api(mock_plugin)

        with patch("builtins.open", mock_open(read_data=metadata_content)):
            with patch("os.path.exists", return_value=True):
                version = api.get_version()
                assert version == "4.6.1"

    def test_get_version_caches_result(self, mock_plugin):
        """get_version caches the version after first read."""
        mock_plugin.plugin_dir = "/fake/dir"
        metadata_content = "version=4.6.1\n"

        api = _make_api(mock_plugin)

        with patch("builtins.open", mock_open(read_data=metadata_content)):
            with patch("os.path.exists", return_value=True):
                v1 = api.get_version()
                v2 = api.get_version()
                assert v1 == v2 == "4.6.1"

    def test_get_version_missing_metadata(self, mock_plugin):
        """get_version returns 'unknown' when metadata.txt not found."""
        mock_plugin.plugin_dir = "/fake/dir"

        api = _make_api(mock_plugin)

        with patch("os.path.exists", return_value=False):
            version = api.get_version()
            assert version == "unknown"

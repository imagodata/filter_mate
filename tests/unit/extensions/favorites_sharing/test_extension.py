# -*- coding: utf-8 -*-
"""
Regression tests for FavoritesSharingExtension dependency gating.

Focus: 2026-04-23 change from ``check_dependencies -> True`` to probing the
QGIS ``resource_sharing`` plugin so the extension surfaces in the
Configuration panel but stays MISSING_DEPS until the companion plugin
is installed (same UX as qfieldcloud).
"""
import sys
import types
from unittest.mock import patch

import pytest

from extensions.favorites_sharing.extension import (
    FavoritesSharingExtension,
    _check_resource_sharing_available,
    reset_resource_sharing_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset availability cache + strip resource_sharing from sys.modules."""
    reset_resource_sharing_cache()
    sys.modules.pop('resource_sharing', None)
    yield
    reset_resource_sharing_cache()
    sys.modules.pop('resource_sharing', None)


class TestMetadataDeclaresHardDep:
    def test_dependencies_contain_resource_sharing(self):
        ext = FavoritesSharingExtension()
        assert 'resource_sharing' in ext.metadata.dependencies

    def test_optional_dependencies_do_not_shadow(self):
        # resource_sharing promoted to hard dep should not linger in optional.
        ext = FavoritesSharingExtension()
        assert 'resource_sharing' not in ext.metadata.optional_dependencies


class TestCheckDependencies:
    def test_returns_false_when_plugin_absent(self):
        ext = FavoritesSharingExtension()
        # Must patch both the qgis.utils registry AND importlib — the
        # developer machine may actually have qgis_resource_sharing
        # installed under the QGIS profile (exactly like the user
        # machine this fix is targeting), and import_module will find
        # it and return True unless we intercept.
        empty_utils = types.SimpleNamespace(plugins={})
        import importlib as _importlib
        real_import_module = _importlib.import_module

        def _blocked(name, package=None):
            from extensions.favorites_sharing.extension import _RESOURCE_SHARING_PLUGIN_NAMES
            if name in _RESOURCE_SHARING_PLUGIN_NAMES:
                raise ImportError(f"blocked for test: {name}")
            return real_import_module(name, package)

        with patch.dict('sys.modules', {'qgis.utils': empty_utils}), \
             patch.object(_importlib, 'import_module', side_effect=_blocked):
            assert ext.check_dependencies() is False

    def test_returns_true_when_qgis_resource_sharing_importable(self):
        # Real-world install: QGIS plugin manager unpacks the official
        # plugin under the ``qgis_resource_sharing`` package name.
        sys.modules['qgis_resource_sharing'] = types.ModuleType('qgis_resource_sharing')
        ext = FavoritesSharingExtension()
        assert ext.check_dependencies() is True

    def test_returns_true_when_legacy_resource_sharing_importable(self):
        # Legacy fork ships as ``resource_sharing`` — must still be accepted.
        sys.modules['resource_sharing'] = types.ModuleType('resource_sharing')
        ext = FavoritesSharingExtension()
        assert ext.check_dependencies() is True

    def test_returns_true_when_plugin_registered_in_qgis_utils(self):
        # Simulate the user having *loaded* qgis_resource_sharing in the
        # QGIS plugin manager — qgis.utils.plugins is populated even if
        # the package is not importable from the current sys.path.
        fake_qgis_utils = types.SimpleNamespace(plugins={'qgis_resource_sharing': object()})
        with patch.dict('sys.modules', {'qgis.utils': fake_qgis_utils}):
            ext = FavoritesSharingExtension()
            assert ext.check_dependencies() is True

    def test_result_is_cached(self):
        ext = FavoritesSharingExtension()
        # Prime cache with "present" using the canonical name
        sys.modules['qgis_resource_sharing'] = types.ModuleType('qgis_resource_sharing')
        assert ext.check_dependencies() is True

        # Remove it from sys.modules — cached result should still hold
        sys.modules.pop('qgis_resource_sharing', None)
        assert _check_resource_sharing_available() is True

        # Reset cache → now reports absent
        reset_resource_sharing_cache()
        # Stub out qgis.utils.plugins AND importlib so the recomputation
        # doesn't accidentally find a real qgis_resource_sharing on disk.
        import importlib as _importlib
        real_import_module = _importlib.import_module

        def _blocked(name, package=None):
            from extensions.favorites_sharing.extension import _RESOURCE_SHARING_PLUGIN_NAMES
            if name in _RESOURCE_SHARING_PLUGIN_NAMES:
                raise ImportError(f"blocked for test: {name}")
            return real_import_module(name, package)

        with patch.dict('sys.modules', {'qgis.utils': types.SimpleNamespace(plugins={})}), \
             patch.object(_importlib, 'import_module', side_effect=_blocked):
            assert _check_resource_sharing_available() is False


class TestMissingDepsHint:
    def test_points_to_plugin_manager_not_pip(self):
        ext = FavoritesSharingExtension()
        hint = ext.missing_deps_hint()
        assert hint.get("method") == "qgis_plugin"
        install_cmd = (hint.get("install_command") or "").lower()
        assert "pip" not in install_cmd
        assert "extensions" in install_cmd or "plugin" in install_cmd
        # Package names both acceptable (users may hit either fork)
        details = (hint.get("details") or "").lower()
        assert "qgis_resource_sharing" in details or "resource_sharing" in details

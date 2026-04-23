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
        # Ensure import fails and qgis.utils.plugins (if present) is empty.
        with patch.dict('sys.modules', {'qgis.utils': types.SimpleNamespace(plugins={})}):
            assert ext.check_dependencies() is False

    def test_returns_true_when_plugin_importable(self):
        # Simulate the resource_sharing package being installed on disk.
        sys.modules['resource_sharing'] = types.ModuleType('resource_sharing')
        ext = FavoritesSharingExtension()
        assert ext.check_dependencies() is True

    def test_returns_true_when_plugin_registered_in_qgis_utils(self):
        # Simulate the user having *loaded* resource_sharing in the QGIS
        # plugin manager — qgis.utils.plugins is populated even if the
        # package is not importable from the current sys.path.
        fake_qgis_utils = types.SimpleNamespace(plugins={'resource_sharing': object()})
        with patch.dict('sys.modules', {'qgis.utils': fake_qgis_utils}):
            ext = FavoritesSharingExtension()
            assert ext.check_dependencies() is True

    def test_result_is_cached(self):
        ext = FavoritesSharingExtension()
        # Prime cache with "present"
        sys.modules['resource_sharing'] = types.ModuleType('resource_sharing')
        assert ext.check_dependencies() is True

        # Remove it from sys.modules — cached result should still hold
        sys.modules.pop('resource_sharing', None)
        assert _check_resource_sharing_available() is True

        # Reset cache → now reports absent
        reset_resource_sharing_cache()
        # Stub out qgis.utils.plugins so cache recomputes False deterministically
        with patch.dict('sys.modules', {'qgis.utils': types.SimpleNamespace(plugins={})}):
            assert _check_resource_sharing_available() is False

# -*- coding: utf-8 -*-
"""Point cloud capability detection (feature flag, QGIS version, layer class).

``adapters/qgis/point_cloud_capability.py`` is loaded by path under a private
synthetic package so its relative imports (``...config.config``,
``...core.domain.point_cloud_support``) resolve to stubs. ``qgis.core`` is
swapped per test for a ``SimpleNamespace`` holding DISTINCT classes, which
is what makes ``isinstance`` meaningful; the conftest's MagicMock module is
also exercised because that is the environment every other unit test runs in.
"""
import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

_PKG = "filter_mate_pc_cap"
_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_MIN_VERSION = 32600


class _FakeVectorLayer:
    def __init__(self, layer_id="vec"):
        self._id = layer_id

    def id(self):
        return self._id


class _FakePointCloudLayer:
    def __init__(self, layer_id="pc"):
        self._id = layer_id

    def id(self):
        return self._id

    def setSubsetString(self, subset):
        return True


class _PointCloudWithoutSubset:
    pass


def _supports_point_cloud_filtering(qgis_version_int, feature_enabled, has_point_cloud_type=True):
    """Contract copy of the WP-A domain rule (kept independent from the real module)."""
    return bool(
        feature_enabled and has_point_cloud_type
        and isinstance(qgis_version_int, int) and not isinstance(qgis_version_int, bool)
        and qgis_version_int >= _MIN_VERSION
    )


def _install_package() -> None:
    if _PKG in sys.modules:
        return

    root = types.ModuleType(_PKG)
    root.__path__ = [_PROJECT_ROOT]
    sys.modules[_PKG] = root

    for sub in ("adapters", "adapters.qgis", "adapters.repositories", "config", "core", "core.domain"):
        full = f"{_PKG}.{sub}"
        mod = types.ModuleType(full)
        mod.__path__ = [os.path.join(_PROJECT_ROOT, *sub.split("."))]
        sys.modules[full] = mod

    config_mod = types.ModuleType(f"{_PKG}.config.config")
    config_mod.ENV_VARS = {"CONFIG_DATA": {}}
    config_mod._get_option_value = lambda option, default=None: (
        default if option is None else option["value"] if isinstance(option, dict) and "value" in option else option
    )
    sys.modules[f"{_PKG}.config.config"] = config_mod

    support_mod = types.ModuleType(f"{_PKG}.core.domain.point_cloud_support")
    support_mod.POINT_CLOUD_MIN_QGIS_VERSION_INT = _MIN_VERSION
    support_mod.supports_point_cloud_filtering = _supports_point_cloud_filtering
    sys.modules[f"{_PKG}.core.domain.point_cloud_support"] = support_mod

    for sub, relpath in (
        ("adapters.qgis.point_cloud_capability", ("adapters", "qgis", "point_cloud_capability.py")),
        ("adapters.repositories.layer_repository", ("adapters", "repositories", "layer_repository.py")),
    ):
        full = f"{_PKG}.{sub}"
        spec = importlib.util.spec_from_file_location(full, os.path.join(_PROJECT_ROOT, *relpath))
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = full.rsplit(".", 1)[0]
        sys.modules[full] = mod
        spec.loader.exec_module(mod)


_install_package()
cap = sys.modules[f"{_PKG}.adapters.qgis.point_cloud_capability"]
repo_mod = sys.modules[f"{_PKG}.adapters.repositories.layer_repository"]
config_mod = sys.modules[f"{_PKG}.config.config"]


def _qgis_core(version=34400, point_cloud_cls=_FakePointCloudLayer, vector_cls=_FakeVectorLayer,
               with_point_cloud=True, with_version=True):
    ns = types.SimpleNamespace(QgsVectorLayer=vector_cls)
    if with_version:
        ns.Qgis = types.SimpleNamespace(QGIS_VERSION_INT=version)
    if with_point_cloud:
        ns.QgsPointCloudLayer = point_cloud_cls
    return ns


def _proxy_model_namespace():
    return types.SimpleNamespace(
        QgsMapLayerProxyModel=types.SimpleNamespace(
            Filter=types.SimpleNamespace(HasGeometry=28, PointCloudLayer=512)
        )
    )


class _Env:
    """Per-test control of the flag and of the mocked QGIS modules."""

    def __init__(self, monkeypatch):
        self._mp = monkeypatch

    def set_flag(self, enabled, wrapped=True):
        option = {"value": enabled, "choices": [True, False], "description": "x"} if wrapped else enabled
        config_mod.ENV_VARS["CONFIG_DATA"] = {"APP": {"OPTIONS": {"POINT_CLOUD": {"enabled": option}}}}

    def set_core(self, namespace):
        self._mp.setitem(sys.modules, "qgis.core", namespace)
        cap.reset_capability_cache()

    def set_gui(self, namespace):
        self._mp.setitem(sys.modules, "qgis.gui", namespace)

    def drop_module(self, name):
        self._mp.delitem(sys.modules, name, raising=False)


@pytest.fixture
def env(monkeypatch):
    config_mod.ENV_VARS["CONFIG_DATA"] = {}
    cap.reset_capability_cache()
    helper = _Env(monkeypatch)
    helper.set_core(_qgis_core())
    helper.set_gui(_proxy_model_namespace())
    yield helper
    config_mod.ENV_VARS["CONFIG_DATA"] = {}
    cap.reset_capability_cache()


class TestFeatureFlag:
    def test_missing_section_is_off(self, env):
        assert cap.is_point_cloud_filtering_enabled() is False

    def test_wrapped_value_true(self, env):
        env.set_flag(True)
        assert cap.is_point_cloud_filtering_enabled() is True

    def test_raw_value_true(self, env):
        env.set_flag(True, wrapped=False)
        assert cap.is_point_cloud_filtering_enabled() is True

    def test_wrapped_value_false(self, env):
        env.set_flag(False)
        assert cap.is_point_cloud_filtering_enabled() is False

    def test_config_data_none_is_off(self, env):
        config_mod.ENV_VARS["CONFIG_DATA"] = None
        assert cap.is_point_cloud_filtering_enabled() is False

    def test_flag_is_read_live_without_cache_reset(self, env):
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer,)
        env.set_flag(True)
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer, _FakePointCloudLayer)
        env.set_flag(False)
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer,)


class TestQgisVersion:
    def test_int_version(self, env):
        assert cap.get_qgis_version_int() == 34400

    def test_magicmock_version_is_zero(self, env):
        env.set_core(_qgis_core(version=MagicMock()))
        assert cap.get_qgis_version_int() == 0

    def test_missing_qgis_class_is_zero(self, env):
        env.set_core(_qgis_core(with_version=False))
        assert cap.get_qgis_version_int() == 0

    def test_bool_version_is_zero(self, env):
        env.set_core(_qgis_core(version=True))
        assert cap.get_qgis_version_int() == 0

    def test_no_qgis_core_is_zero(self, env):
        env.drop_module("qgis.core")
        env.drop_module("qgis")
        assert cap.get_qgis_version_int() == 0


class TestFilterableLayerTypes:
    def test_flag_off_vector_only(self, env):
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer,)
        assert cap.get_point_cloud_layer_type() is None

    def test_flag_on_recent_qgis_both_types(self, env):
        env.set_flag(True)
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer, _FakePointCloudLayer)
        assert cap.get_point_cloud_layer_type() is _FakePointCloudLayer

    def test_flag_on_old_qgis_vector_only(self, env):
        env.set_flag(True)
        env.set_core(_qgis_core(version=32200))
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer,)
        assert cap.get_point_cloud_layer_type() is None

    def test_flag_on_version_just_at_floor(self, env):
        env.set_flag(True)
        env.set_core(_qgis_core(version=_MIN_VERSION))
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer, _FakePointCloudLayer)

    def test_point_cloud_class_as_magicmock_instance_vector_only(self, env):
        env.set_flag(True)
        env.set_core(_qgis_core(point_cloud_cls=MagicMock()))
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer,)
        assert cap.get_point_cloud_layer_type() is None

    def test_version_as_magicmock_vector_only(self, env):
        env.set_flag(True)
        env.set_core(_qgis_core(version=MagicMock()))
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer,)

    def test_point_cloud_class_without_set_subset_string_vector_only(self, env):
        env.set_flag(True)
        env.set_core(_qgis_core(point_cloud_cls=_PointCloudWithoutSubset))
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer,)

    def test_point_cloud_class_missing_vector_only(self, env):
        env.set_flag(True)
        env.set_core(_qgis_core(with_point_cloud=False))
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer,)

    def test_conftest_style_magicmock_module(self, env):
        env.set_flag(True)
        core = MagicMock()
        core.QgsVectorLayer = MagicMock
        env.set_core(core)
        result = cap.get_filterable_layer_types()
        assert result == (MagicMock,)
        assert all(isinstance(t, type) for t in result)

    def test_magicmock_module_without_vector_type_is_empty(self, env):
        env.set_core(MagicMock())
        assert cap.get_filterable_layer_types() == ()

    def test_no_qgis_core_is_empty(self, env):
        env.drop_module("qgis.core")
        env.drop_module("qgis")
        assert cap.get_filterable_layer_types() == ()

    def test_result_only_contains_types(self, env):
        env.set_flag(True)
        for namespace in (_qgis_core(), _qgis_core(point_cloud_cls=MagicMock()), _qgis_core(version=MagicMock())):
            env.set_core(namespace)
            assert all(isinstance(t, type) for t in cap.get_filterable_layer_types())

    def test_reset_cache_picks_up_new_class(self, env):
        env.set_flag(True)
        env.set_core(_qgis_core(point_cloud_cls=MagicMock()))
        assert cap.get_point_cloud_layer_type() is None
        env.set_core(_qgis_core())
        assert cap.get_point_cloud_layer_type() is _FakePointCloudLayer

    def test_domain_rule_missing_disables_support(self, env, monkeypatch):
        env.set_flag(True)
        monkeypatch.setitem(sys.modules, f"{_PKG}.core.domain.point_cloud_support", None)
        assert cap.get_point_cloud_layer_type() is None
        assert cap.get_filterable_layer_types() == (_FakeVectorLayer,)


class TestIsPointCloudLayer:
    def test_true_for_point_cloud_when_enabled(self, env):
        env.set_flag(True)
        assert cap.is_point_cloud_layer(_FakePointCloudLayer()) is True

    def test_false_for_vector_when_enabled(self, env):
        env.set_flag(True)
        assert cap.is_point_cloud_layer(_FakeVectorLayer()) is False

    def test_false_when_flag_off(self, env):
        assert cap.is_point_cloud_layer(_FakePointCloudLayer()) is False

    def test_false_when_qgis_too_old(self, env):
        env.set_flag(True)
        env.set_core(_qgis_core(version=32200))
        assert cap.is_point_cloud_layer(_FakePointCloudLayer()) is False

    def test_false_for_none_and_plain_objects(self, env):
        env.set_flag(True)
        assert cap.is_point_cloud_layer(None) is False
        assert cap.is_point_cloud_layer(object()) is False
        assert cap.is_point_cloud_layer("layer_id") is False

    def test_false_under_conftest_magicmock_module(self, env):
        env.set_flag(True)
        env.set_core(MagicMock())
        assert cap.is_point_cloud_layer(MagicMock()) is False


class TestCurrentLayerComboFilters:
    def test_flag_off_has_geometry_only(self, env):
        assert cap.get_current_layer_combo_filters() == 28

    def test_flag_on_adds_point_cloud_filter(self, env):
        env.set_flag(True)
        assert cap.get_current_layer_combo_filters() == 28 | 512

    def test_flag_on_old_qgis_has_geometry_only(self, env):
        env.set_flag(True)
        env.set_core(_qgis_core(version=32200))
        assert cap.get_current_layer_combo_filters() == 28

    def test_falls_back_to_qgis_core(self, env):
        env.set_flag(True)
        env.set_gui(types.SimpleNamespace())
        core = _qgis_core()
        core.QgsMapLayerProxyModel = _proxy_model_namespace().QgsMapLayerProxyModel
        env.set_core(core)
        assert cap.get_current_layer_combo_filters() == 28 | 512

    def test_none_when_proxy_model_missing_everywhere(self, env):
        env.set_gui(types.SimpleNamespace())
        assert cap.get_current_layer_combo_filters() is None

    def test_none_when_qgis_missing(self, env):
        env.drop_module("qgis.gui")
        env.drop_module("qgis.core")
        env.drop_module("qgis")
        assert cap.get_current_layer_combo_filters() is None


class _FakeProject:
    def __init__(self, layers, fail=False):
        self._layers = {layer.id(): layer for layer in layers}
        self._fail = fail

    def mapLayer(self, layer_id):
        if self._fail:
            raise RuntimeError("project gone")
        return self._layers.get(layer_id)

    def mapLayers(self):
        if self._fail:
            raise RuntimeError("project gone")
        return dict(self._layers)


class TestLayerRepositoryPointCloud:
    """``QGISLayerRepository`` wires the capability; vector accessors stay untouched."""

    @pytest.fixture
    def repo(self, env, monkeypatch):
        self.vec = _FakeVectorLayer("vec")
        self.pc = _FakePointCloudLayer("pc")
        project = _FakeProject([self.vec, self.pc])
        monkeypatch.setattr(repo_mod, "QGIS_AVAILABLE", True)
        monkeypatch.setattr(repo_mod, "QgsVectorLayer", _FakeVectorLayer)
        monkeypatch.setattr(repo_mod, "QgsProject", types.SimpleNamespace(instance=lambda: project))
        return repo_mod.QGISLayerRepository()

    def test_flag_off_returns_nothing(self, repo):
        assert repo.get_all_point_cloud_layers() == []
        assert repo.get_point_cloud_layer("pc") is None

    def test_flag_on_returns_point_cloud_only(self, env, repo):
        env.set_flag(True)
        assert repo.get_all_point_cloud_layers() == [self.pc]
        assert repo.get_point_cloud_layer("pc") is self.pc
        assert repo.get_point_cloud_layer("vec") is None
        assert repo.get_point_cloud_layer("missing") is None

    def test_vector_accessors_unchanged(self, env, repo):
        env.set_flag(True)
        assert repo.get_all_vector_layers() == [self.vec]
        assert repo.get_layer("vec") is self.vec
        assert repo.get_layer("pc") is None

    def test_project_failure_is_swallowed(self, env, repo, monkeypatch):
        env.set_flag(True)
        broken = _FakeProject([], fail=True)
        monkeypatch.setattr(repo_mod, "QgsProject", types.SimpleNamespace(instance=lambda: broken))
        assert repo.get_all_point_cloud_layers() == []
        assert repo.get_point_cloud_layer("pc") is None

    def test_qgis_unavailable(self, env, repo, monkeypatch):
        env.set_flag(True)
        monkeypatch.setattr(repo_mod, "QGIS_AVAILABLE", False)
        assert repo.get_all_point_cloud_layers() == []
        assert repo.get_point_cloud_layer("pc") is None

    def test_capability_module_missing_returns_nothing(self, env, repo, monkeypatch):
        env.set_flag(True)
        monkeypatch.setitem(sys.modules, f"{_PKG}.adapters.qgis.point_cloud_capability", None)
        assert repo.get_all_point_cloud_layers() == []

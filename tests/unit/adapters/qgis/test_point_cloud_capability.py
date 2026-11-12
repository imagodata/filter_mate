# -*- coding: utf-8 -*-
"""Point cloud capability detection (feature flag, QGIS version, layer class).

``adapters/qgis/point_cloud_capability.py`` is loaded by path under a private
synthetic package so its relative imports (``...config.config``,
``...core.domain.point_cloud_support``) resolve to stubs. ``qgis.core`` is
swapped per test for a ``SimpleNamespace`` holding DISTINCT classes, which
is what makes ``isinstance`` meaningful; the conftest's MagicMock module is
also exercised because that is the environment every other unit test runs in.
"""
import ast
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


def _real_option_readers() -> dict:
    """``_get_option_value`` / ``_get_option_bool`` and their constants, from config/config.py."""
    path = os.path.join(_PROJECT_ROOT, "config", "config.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    names = {"_get_option_value", "_get_option_bool", "_FALSE_STRINGS", "_TRUE_STRINGS"}
    body = [node for node in tree.body
            if (isinstance(node, ast.FunctionDef) and node.name in names)
            or (isinstance(node, ast.Assign) and any(getattr(t, "id", None) in names for t in node.targets))]
    namespace = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), path, "exec"), namespace)
    return {name: namespace[name] for name in names}


def _install_package() -> None:
    if _PKG in sys.modules:
        return

    root = types.ModuleType(_PKG)
    root.__path__ = [_PROJECT_ROOT]
    sys.modules[_PKG] = root

    for sub in ("adapters", "adapters.qgis", "adapters.repositories", "adapters.public_api", "config", "core", "core.domain", "core.filter", "core.services"):
        full = f"{_PKG}.{sub}"
        mod = types.ModuleType(full)
        mod.__path__ = [os.path.join(_PROJECT_ROOT, *sub.split("."))]
        sys.modules[full] = mod

    config_mod = types.ModuleType(f"{_PKG}.config.config")
    config_mod.ENV_VARS = {"CONFIG_DATA": {}}
    # The real option readers (config.py itself needs QGIS to import).
    config_mod.__dict__.update(_real_option_readers())
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

    @pytest.mark.parametrize("text", ["false", "False", "0", "no", "off", ""])
    def test_false_text_is_off(self, env, text):
        """A hand-edited config.json: bool("false") is True, the flag read it as on."""
        env.set_flag(text)
        assert cap.is_point_cloud_filtering_enabled() is False

    @pytest.mark.parametrize("text", ["true", "1", "yes"])
    def test_true_text_is_on(self, env, text):
        env.set_flag(text)
        assert cap.is_point_cloud_filtering_enabled() is True

    def test_raster_flag_false_text_is_off(self, env):
        config_mod.ENV_VARS["CONFIG_DATA"] = {"APP": {"OPTIONS": {"RASTER": {"enabled": {"value": "false"}}}}}
        assert cap.is_raster_filtering_enabled() is False

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


class _FakeCombo:
    def __init__(self, excluded=()):
        self.excluded = list(excluded)

    def excludedProviders(self):
        return list(self.excluded)

    def setExcludedProviders(self, providers):
        self.excluded = list(providers)


class TestExcludeNonAnalysisRasters:
    def test_rendered_services_and_wcs_stay_in_dock(self):
        combo = _FakeCombo()
        cap.exclude_non_analysis_rasters(combo)
        assert not {"wms", "wcs", "arcgismapserver"} & set(combo.excluded)
        assert "grassraster" in combo.excluded
        assert not set(combo.excluded) & set(cap.ANALYSIS_RASTER_PROVIDERS)

    def test_existing_exclusions_are_kept_once(self):
        combo = _FakeCombo(excluded=["memory", "wms"])
        cap.exclude_non_analysis_rasters(combo)
        cap.exclude_non_analysis_rasters(combo)
        assert combo.excluded[0] == "memory" and "wms" not in combo.excluded

    def test_combo_without_the_api_is_left_alone(self):
        cap.exclude_non_analysis_rasters(object())  # no exception


class _FakeRasterLayer:
    def __init__(self, provider="gdal", source="/data/dem.tif"):
        self._provider = provider
        self._source = source

    def id(self):
        return str(id(self))

    def providerType(self):
        return self._provider

    def source(self):
        return self._source


GDAL_WMS_XML = ('<GDAL_WMS><Service name="TMS"><ServerUrl>https://tile.openstreetmap.org/${z}/${x}/${y}.png'
                '</ServerUrl></Service></GDAL_WMS>')


class TestIsNonAnalysisRaster:
    """Rendered and unsupported rasters cannot be targets; WCS has values."""

    @pytest.fixture
    def core(self, env):
        env.set_core(types.SimpleNamespace(QgsVectorLayer=_FakeVectorLayer, QgsRasterLayer=_FakeRasterLayer))

    @pytest.mark.parametrize("provider", ["wms", "arcgismapserver", "grassraster"])
    def test_web_and_other_rasters(self, core, provider):
        assert cap.is_non_analysis_raster(_FakeRasterLayer(provider)) is True

    @pytest.mark.parametrize("provider", ["gdal", "virtualraster", "postgresraster", "wcs"])
    def test_analysable_rasters(self, core, provider):
        assert cap.is_non_analysis_raster(_FakeRasterLayer(provider)) is False

    @pytest.mark.parametrize("source", [GDAL_WMS_XML, "WMS:https://example.org/wms?SERVICE=WMS&LAYERS=ortho"])
    def test_gdal_rendered_services_are_not_rasters_of_values(self, core, env, source):
        """2026-10-17: provider 'gdal', but the pixels are a rendered image (TMS / WMS through GDAL)."""
        layer = _FakeRasterLayer("gdal", source)
        assert cap.is_non_analysis_raster(layer) is True
        assert cap.layer_kind_by_class(layer).value == "raster"

    @pytest.mark.parametrize("source", ["/vsicurl/https://example.org/dem.tif", "WCS:https://example.org/wcs"])
    def test_gdal_remote_values_stay_rasters_of_values(self, core, source):
        assert cap.is_non_analysis_raster(_FakeRasterLayer("gdal", source)) is False

    def test_vector_and_none(self, core):
        assert cap.is_non_analysis_raster(_FakeVectorLayer()) is False
        assert cap.is_non_analysis_raster(None) is False

    def test_without_raster_class(self, env):
        assert cap.is_non_analysis_raster(_FakeRasterLayer("wms")) is False

    def test_one_class_for_vectors_and_rasters(self, env):
        """Mocked qgis.core where QgsRasterLayer is QgsVectorLayer: every vector is no basemap."""
        env.set_core(types.SimpleNamespace(QgsVectorLayer=_FakeRasterLayer, QgsRasterLayer=_FakeRasterLayer))
        assert cap.is_non_analysis_raster(_FakeRasterLayer("ogr")) is False

    def test_deleted_layer(self, core):
        layer = _FakeRasterLayer()
        layer.providerType = MagicMock(side_effect=RuntimeError("wrapped C/C++ object deleted"))
        assert cap.is_non_analysis_raster(layer) is False


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


class TestStreamRasterClassification:
    @pytest.fixture
    def rasters(self, env):
        env.set_core(types.SimpleNamespace(QgsVectorLayer=_FakeVectorLayer,
                                          QgsRasterLayer=_FakeRasterLayer,
                                          Qgis=types.SimpleNamespace(QGIS_VERSION_INT=34400)))
        config_mod.ENV_VARS["CONFIG_DATA"] = {"APP": {"OPTIONS": {"RASTER": {"enabled": True}}}}

    @pytest.mark.parametrize("provider,source,raw", [
        ("wms", "type=wmts&url=https://example.org", False),
        ("wms", "type=xyz&url=https://example.org/{z}/{x}/{y}.png", False),
        ("arcgismapserver", "url=https://example.org/MapServer", False),
        ("gdal", GDAL_WMS_XML, False),
        ("gdal", "WMS:https://example.org", False),
        ("wcs", "url=https://example.org/wcs", True),
        ("gdal", "WCS:https://example.org", True),
        ("gdal", "/vsicurl/https://example.org/dem.tif", True),
        ("postgresraster", "dbname=test table=dem", True),
    ])
    def test_dock_and_public_kind_agree_but_rendered_never_targets(self, rasters, provider, source, raw):
        layer = _FakeRasterLayer(provider, source)
        assert cap.is_raster_layer(layer)
        assert cap.get_layer_kind(layer).value == "raster"
        assert cap.layer_kind_by_class(layer).value == "raster"
        assert cap.is_coverage_layer(layer)
        assert not cap.is_unsupported_raster(layer)
        assert cap.is_non_analysis_raster(layer) is (not raw)

    def test_public_kind_ignores_dock_flag(self, rasters):
        config_mod.ENV_VARS["CONFIG_DATA"] = {}
        layer = _FakeRasterLayer("wms")
        assert cap.get_layer_kind(layer).value == "other"
        assert cap.layer_kind_by_class(layer).value == "raster"

    def test_classification_tracks_source_change(self, rasters):
        layer = _FakeRasterLayer()
        assert not cap.is_non_analysis_raster(layer)
        layer._source = GDAL_WMS_XML
        assert cap.is_non_analysis_raster(layer)
        assert cap.is_raster_layer(layer)


class TestStreamRasterTargets:
    rasters = TestStreamRasterClassification.rasters
    @pytest.mark.parametrize("provider,source,allowed", [
        ("wms", "type=xyz&url=https://example.org", False),
        ("arcgismapserver", "url=https://example.org", False),
        ("gdal", GDAL_WMS_XML, False),
        ("wcs", "url=https://example.org", True),
        ("gdal", "/vsicurl/https://example.org/dem.tif", True),
    ])
    def test_automation_target_admission(self, rasters, provider, source, allowed):
        # Processing, Python, REST and MCP all delegate target validation here.
        operations = importlib.import_module(f"{_PKG}.adapters.public_api.operations")
        layer = _FakeRasterLayer(provider, source)
        layer.name = lambda: "raster"
        project = _FakeProject([layer])
        report = operations.OperationReport()
        specs, kept = operations._project_targets([layer], project, None, report)
        assert bool(specs) is allowed
        assert kept == ([layer] if allowed else [])
        if not allowed:
            assert "cannot be a filter target" in report.skipped["raster"]

    def test_dock_targets_reject_rendered_but_allow_as_source(self, rasters):
        path = os.path.join(_PROJECT_ROOT, "ui", "managers", "combobox_population_manager.py")
        tree = ast.parse(open(path, encoding="utf-8").read())
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                     and n.name in ("_is_coverage_layer", "_is_coverage_target")]
        namespace = {"__package__": f"{_PKG}.ui.managers"}
        exec(compile(ast.Module(body=functions, type_ignores=[]), path, "exec"), namespace)
        rendered = _FakeRasterLayer("gdal", GDAL_WMS_XML)
        wcs = _FakeRasterLayer("wcs")
        assert namespace["_is_coverage_layer"](rendered)
        for vector_source in (True, False):
            assert not namespace["_is_coverage_target"](rendered, vector_source)
            assert namespace["_is_coverage_target"](wcs, vector_source)


    @pytest.mark.parametrize("provider,source,allowed", [
        ("wms", "url=https://example.org", False),
        ("gdal", GDAL_WMS_XML, False),
        ("wcs", "url=https://example.org", True),
    ])
    def test_stale_target_selection_is_guarded_before_job_creation(self, rasters, monkeypatch,
                                                                 provider, source, allowed):
        service_module = importlib.import_module(f"{_PKG}.core.services.cross_filter_service")
        cross = importlib.import_module(f"{_PKG}.core.domain.cross_filter")
        kind = cap.layer_kind_by_class(_FakeRasterLayer())
        layer = _FakeRasterLayer(provider, source)
        layer.name = lambda: "raster"
        project = _FakeProject([layer])
        monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject", object, raising=False)
        appliers = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.target_appliers")
        appliers.make_job = MagicMock(return_value=object())
        task_module = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.cross_filter_task")
        task_module.CrossFilterTask = lambda desc, request, source, jobs, done, project=None: types.SimpleNamespace(jobs=jobs)
        snapshots = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.snapshots")
        snapshots.registry = lambda: types.SimpleNamespace(install=lambda project: None)
        for module in (appliers, task_module, snapshots):
            monkeypatch.setitem(sys.modules, module.__name__, module)
        request = cross.CrossFilterRequest("source", kind, targets=(cross.TargetSpec(layer.id(), kind),))
        task = service_module.CrossFilterService().build_task(
            request, types.SimpleNamespace(layer_name="source"), project=project)
        assert appliers.make_job.called is allowed
        if not allowed:
            assert not task.jobs[0].outcome.success
            assert "cannot be a filter target" in task.jobs[0].outcome.message

    def test_target_guard_reuses_capability_probe(self, rasters, monkeypatch):
        probe = importlib.import_module(f"{_PKG}.adapters.qgis.source_capability_probe")
        spy = MagicMock(return_value=types.SimpleNamespace(has_raw_values=False))
        monkeypatch.setattr(probe, "capability_for_layer", spy)
        layer = _FakeRasterLayer()
        assert cap.is_non_analysis_raster(layer)
        spy.assert_called_once_with(layer)


    @pytest.mark.parametrize("provider,source", [
        ("wms", "url=https://example.org"),
        ("gdal", GDAL_WMS_XML),
    ])
    def test_automation_rejects_numeric_rendered_source_before_job_creation(self, rasters, monkeypatch,
                                                                         provider, source):
        operations = importlib.import_module(f"{_PKG}.adapters.public_api.operations")
        jobs = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.source_jobs")
        jobs.RasterSourceJob = MagicMock()
        monkeypatch.setitem(sys.modules, jobs.__name__, jobs)
        layer = _FakeRasterLayer(provider, source)
        with pytest.raises(ValueError, match="local colour capture; numeric pixel selections are unavailable"):
            operations._source_job(layer, cap.layer_kind_by_class(layer), operations.OperationReport(),
                                   selected_only=False, raster_selection=types.SimpleNamespace(band=1),
                                   point_cloud_criteria=None, source_operator=None, filter_source=True,
                                   footprint_resolution=None, max_pixels=1000)
        jobs.RasterSourceJob.assert_not_called()


class _Named:
    """name() / crs() / isSpatial() / isValid() of a project layer listed in the dock."""

    def name(self):
        return self.id()

    def crs(self):
        return types.SimpleNamespace(authid=lambda: "EPSG:31370")

    def isSpatial(self):
        return True

    def isValid(self):
        return True


class _ListedVector(_Named, _FakeVectorLayer):
    pass


class _ListedPointCloud(_Named, _FakePointCloudLayer):
    pass


class _ListedRaster(_Named, _FakeRasterLayer):
    def __init__(self, layer_id, provider="gdal", source="/data/dem.tif"):
        super().__init__(provider, source)
        self._layer_id = layer_id

    def id(self):
        return self._layer_id


class QgsVectorTileLayer(_Named):
    """A vector tile layer is recognized by its class name (target only, never clipped here)."""

    def id(self):
        return "tiles"


OSM_XYZ = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"


def _options(raster=True, point_cloud=True, rasters=True, point_clouds=True, cross_filter=None):
    """CONFIG_DATA with the layer kinds and the two CROSS_FILTER options of the targets of a vector source."""
    if cross_filter is None:
        cross_filter = {
            "vector_source_raster_targets": {"value": raster, "choices": [True, False], "description": "x"},
            "vector_source_point_cloud_targets": {"value": point_cloud, "choices": [True, False], "description": "x"},
        }
    config_mod.ENV_VARS["CONFIG_DATA"] = {"APP": {"OPTIONS": {
        "RASTER": {"enabled": {"value": rasters}}, "POINT_CLOUD": {"enabled": {"value": point_clouds}},
        "CROSS_FILTER": cross_filter}}}


@pytest.fixture
def all_kinds(env):
    """qgis.core with distinct vector, raster and point cloud classes, both kinds on, both options on."""
    env.set_core(types.SimpleNamespace(QgsVectorLayer=_FakeVectorLayer, QgsRasterLayer=_FakeRasterLayer,
                                       QgsPointCloudLayer=_FakePointCloudLayer,
                                       Qgis=types.SimpleNamespace(QGIS_VERSION_INT=34400)))
    _options()
    return env


class TestVectorSourceTargetOptions:
    """APP.OPTIONS.CROSS_FILTER.vector_source_raster_targets / vector_source_point_cloud_targets (2026-11-12)."""

    def test_on_when_unset(self, all_kinds):
        """A configuration the migration has not reached yet: the dock behaves as before the options."""
        _options(cross_filter={})
        assert cap.is_vector_source_raster_targets_enabled() is True
        assert cap.is_vector_source_point_cloud_targets_enabled() is True
        config_mod.ENV_VARS["CONFIG_DATA"] = None
        assert cap.is_vector_source_raster_targets_enabled() is True

    def test_false_text_is_off(self, all_kinds):
        _options(raster="false", point_cloud="off")
        assert cap.is_vector_source_raster_targets_enabled() is False
        assert cap.is_vector_source_point_cloud_targets_enabled() is False

    def test_raster_target_follows_its_option_under_a_vector_source_only(self, all_kinds):
        dem, lidar = _ListedRaster("dem"), _ListedPointCloud("lidar")
        assert cap.is_listed_coverage_target(dem, True)
        _options(raster=False)
        assert not cap.is_listed_coverage_target(dem, True)
        assert cap.is_listed_coverage_target(dem, False)  # a raster source keeps its raster targets
        assert cap.is_listed_coverage_target(lidar, True)  # independent

    def test_point_cloud_target_follows_its_option_under_a_vector_source_only(self, all_kinds):
        dem, lidar = _ListedRaster("dem"), _ListedPointCloud("lidar")
        assert cap.is_listed_coverage_target(lidar, True)
        _options(point_cloud=False)
        assert not cap.is_listed_coverage_target(lidar, True)
        assert cap.is_listed_coverage_target(lidar, False)
        assert cap.is_listed_coverage_target(dem, True)

    def test_the_layer_kind_still_has_to_be_on(self, all_kinds):
        """A raster target needs RASTER.enabled AND the option (same for point clouds)."""
        _options(rasters=False, point_clouds=False)
        assert not cap.is_listed_coverage_target(_ListedRaster("dem"), True)
        assert not cap.is_listed_coverage_target(_ListedPointCloud("lidar"), True)

    def test_vectors_are_not_coverage_targets(self, all_kinds):
        assert not cap.is_listed_coverage_target(_ListedVector("roads"), True)
        assert not cap.is_listed_coverage_target(None, True)

    @pytest.mark.parametrize("provider,source", [("wms", OSM_XYZ), ("wms", "type=wmts&url=https://example.org"),
                                                 ("arcgismapserver", "url=https://example.org/MapServer"),
                                                 ("gdal", GDAL_WMS_XML)])
    def test_rendered_raster_is_never_a_target_but_is_shown_greyed(self, all_kinds, provider, source):
        basemap = _ListedRaster("osm", provider, source)
        for vector_source in (True, False):
            assert not cap.is_listed_coverage_target(basemap, vector_source)
            assert cap.is_listed_rendered_raster(basemap, vector_source)

    def test_greyed_basemaps_go_with_the_raster_targets(self, all_kinds):
        """Shown where the rasters of values are listed, never where rasters were turned off."""
        basemap = _ListedRaster("osm", "wms", OSM_XYZ)
        _options(raster=False)
        assert not cap.is_listed_rendered_raster(basemap, True)
        assert cap.is_listed_rendered_raster(basemap, False)
        _options(rasters=False)
        assert not cap.is_listed_rendered_raster(basemap, False)

    def test_value_rasters_and_vectors_are_not_greyed(self, all_kinds):
        assert not cap.is_listed_rendered_raster(_ListedRaster("dem"), True)
        assert not cap.is_listed_rendered_raster(_ListedRaster("dem", "wcs", "url=https://example.org"), True)
        assert not cap.is_listed_rendered_raster(_ListedVector("roads"), True)

    def test_targets_left_out_at_launch(self, all_kinds):
        dem, lidar, basemap = _ListedRaster("dem"), _ListedPointCloud("lidar"), _ListedRaster("osm", "wms", OSM_XYZ)
        assert not cap.is_unlisted_vector_source_target(dem)
        assert not cap.is_unlisted_vector_source_target(lidar)
        assert cap.is_unlisted_vector_source_target(basemap)
        _options(raster=False, point_cloud=False)
        assert cap.is_unlisted_vector_source_target(dem)
        assert cap.is_unlisted_vector_source_target(lidar)
        # Vector and vector tile targets are never concerned.
        assert not cap.is_unlisted_vector_source_target(_ListedVector("roads"))
        assert not cap.is_unlisted_vector_source_target(QgsVectorTileLayer())
        assert not cap.is_unlisted_vector_source_target(None)


class _TargetList:
    """The FILTERING targets list as both filling paths use it: checkable rows and greyed rows."""

    def __init__(self):
        self.rows, self.greyed = [], []

    def clear(self):
        self.rows, self.greyed = [], []

    def addItem(self, icon, text, data=None):
        self.rows.append(data["layer_id"])

    def add_unfilterable_item(self, icon, text, layer_id):
        self.greyed.append((layer_id, text))

    def model(self):
        return types.SimpleNamespace(item=lambda index: MagicMock())

    def count(self):
        return len(self.rows) + len(self.greyed)


class TestTargetListsFollowTheOptions:
    """FilteringController and its direct fallback (ComboboxPopulationManager) on the real capability module."""

    @pytest.fixture
    def dock(self, all_kinds, monkeypatch):
        layers = [_ListedVector("roads"), _ListedVector("parcels"), _ListedRaster("dem"), _ListedRaster("dtm"),
                  _ListedPointCloud("lidar"), _ListedRaster("osm", "wms", OSM_XYZ)]
        project = _FakeProject(layers)
        core = sys.modules["qgis.core"]
        monkeypatch.setattr(core, "QgsProject", types.SimpleNamespace(instance=lambda: project), raising=False)
        geometry = {"roads": "GeometryType.Line", "parcels": "GeometryType.Polygon", "dem": "GeometryType.Raster",
                    "dtm": "GeometryType.Raster", "lidar": "GeometryType.PointCloud", "osm": "GeometryType.Raster"}
        project_layers = {layer_id: {
            "infos": {"layer_id": layer_id, "layer_name": layer_id, "layer_crs_authid": "EPSG:31370",
                      "layer_geometry_type": geometry_type},
            "filtering": {"has_layers_to_filter": True, "layers_to_filter": ["dem", "lidar", "osm"]},
        } for layer_id, geometry_type in geometry.items()}
        self._stub_dock_modules(monkeypatch)
        return types.SimpleNamespace(
            widgets_initialized=True, has_loaded_layers=True, PROJECT_LAYERS=project_layers, app=None,
            current_layer=layers[0], layers={layer.id(): layer for layer in layers}, project=project,
            widgets={"FILTERING": {"LAYERS_TO_FILTER": {"WIDGET": _TargetList()}}},
            icon_per_geometry_type=lambda geometry_type: None)

    @staticmethod
    def _stub_dock_modules(monkeypatch):
        def module(name, **attributes):
            mod = types.ModuleType(f"{_PKG}.{name}")
            mod.__path__ = []
            mod.__dict__.update(attributes)
            monkeypatch.setitem(sys.modules, mod.__name__, mod)

        class BaseController:
            def __init__(self, dockwidget, filter_service=None, signal_manager=None):
                self._dockwidget = dockwidget

        class SignalBlocker:
            def __init__(self, *widgets):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        for name in ("ui", "ui.controllers", "ui.controllers.mixins", "ui.managers", "infrastructure",
                     "adapters.qgis.coverage_layers"):
            module(name)
        module("ui.controllers.base_controller", BaseController=BaseController)
        module("ui.controllers.mixins.layer_selection_mixin", LayerSelectionMixin=type("LayerSelectionMixin", (), {}))
        module("infrastructure.signal_utils", SignalBlocker=SignalBlocker)
        module("infrastructure.utils", geometry_type_to_string=lambda layer: "GeometryType.Point")
        module("infrastructure.utils.validation_utils",
               is_layer_source_available=lambda layer, require_psycopg2=False: True)
        module("adapters.qgis.coverage_layers.vector_tile_filters", append_targets=lambda *args, **kwargs: None)

    @staticmethod
    def _load(monkeypatch, sub, *relpath):
        full = f"{_PKG}.{sub}"
        spec = importlib.util.spec_from_file_location(full, os.path.join(_PROJECT_ROOT, *relpath))
        mod = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, full, mod)
        spec.loader.exec_module(mod)
        return mod

    def _fill(self, monkeypatch, dock, path, source_id="roads"):
        source = dock.layers[source_id]
        if path == "controller":
            module = self._load(monkeypatch, "ui.controllers.filtering_controller",
                                "ui", "controllers", "filtering_controller.py")
            assert module.FilteringController(dock).populate_layers_checkable_combobox(source) is True
        else:
            module = self._load(monkeypatch, "ui.managers.combobox_population_manager",
                                "ui", "managers", "combobox_population_manager.py")
            assert module.ComboboxPopulationManager(dock).populate_filtering_layers_direct(source) is True
        return dock.widgets["FILTERING"]["LAYERS_TO_FILTER"]["WIDGET"]

    @pytest.mark.parametrize("path", ["controller", "direct"])
    def test_options_on_list_rasters_and_point_clouds(self, monkeypatch, dock, path):
        targets = self._fill(monkeypatch, dock, path)
        assert targets.rows == ["parcels", "dem", "dtm", "lidar"]
        assert targets.greyed == [("osm", "osm [EPSG:31370]")]

    @pytest.mark.parametrize("path", ["controller", "direct"])
    def test_raster_option_off_drops_the_rasters_and_their_greyed_basemaps(self, monkeypatch, dock, path):
        _options(raster=False)
        targets = self._fill(monkeypatch, dock, path)
        assert targets.rows == ["parcels", "lidar"]
        assert targets.greyed == []

    @pytest.mark.parametrize("path", ["controller", "direct"])
    def test_point_cloud_option_off_drops_the_point_clouds(self, monkeypatch, dock, path):
        _options(point_cloud=False)
        targets = self._fill(monkeypatch, dock, path)
        assert targets.rows == ["parcels", "dem", "dtm"]
        assert [layer_id for layer_id, _ in targets.greyed] == ["osm"]

    @pytest.mark.parametrize("path", ["controller", "direct"])
    def test_options_are_for_a_vector_source_only(self, monkeypatch, dock, path):
        _options(raster=False, point_cloud=False)
        targets = self._fill(monkeypatch, dock, path, source_id="dem")
        assert targets.rows == ["roads", "parcels", "dtm", "lidar"]
        assert [layer_id for layer_id, _ in targets.greyed] == ["osm"]

    @pytest.mark.parametrize("path", ["controller", "direct"])
    def test_a_list_of_greyed_basemaps_only_is_filled_all_the_same(self, monkeypatch, dock, path):
        for layer_id in ("parcels", "dem", "dtm", "lidar"):
            del dock.PROJECT_LAYERS[layer_id]
            del dock.project._layers[layer_id]
        targets = self._fill(monkeypatch, dock, path)  # asserts that the filling reports success
        assert targets.rows == [] and [layer_id for layer_id, _ in targets.greyed] == ["osm"]

    @pytest.mark.parametrize("path", ["controller", "direct"])
    def test_a_web_basemap_source_is_not_listed_greyed(self, monkeypatch, dock, path):
        """The source is never among its targets, greyed or not."""
        targets = self._fill(monkeypatch, dock, path, source_id="osm")
        assert "osm" not in targets.rows and targets.greyed == []

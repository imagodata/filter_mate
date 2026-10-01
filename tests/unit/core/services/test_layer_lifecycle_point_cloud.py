# -*- coding: utf-8 -*-
"""
2026-09-18: ``LayerLifecycleService.filter_usable_layers`` no longer rejects
every non-vector layer. The accepted types come from
``adapters.qgis.point_cloud_capability.get_filterable_layer_types()`` (vector
only while the point cloud feature flag is off or the QGIS version is too old,
vector + point cloud otherwise), resolved once per call; a missing capability
module falls back to vector only.

The real module is loaded under a private package chain (``_llspc_sandbox``)
where ``infrastructure.utils`` and the capability module are stubs, so the
service's deferred imports resolve to controllable fakes.
"""
import ast
import importlib.util
import logging
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
_SERVICE = os.path.join(_PLUGIN_ROOT, "core", "services", "layer_lifecycle_service.py")
_ROOT = "_llspc_sandbox"
_CAPABILITY = f"{_ROOT}.adapters.qgis.point_cloud_capability"
_UTILS = f"{_ROOT}.infrastructure.utils"
_LOGGER = "FilterMate.LayerLifecycleService"


class _FakePointCloudLayer:
    """QgsMapLayer surface only: no fields(), featureCount() or geometryType()."""

    def __init__(self, layer_id="pc-1", name="nuage", valid=True):
        self._id = layer_id
        self._name = name
        self._valid = valid

    def id(self):
        return self._id

    def name(self):
        return self._name

    def isValid(self):
        return self._valid

    def providerType(self):
        return "copc"

    def source(self):
        return "/data/nuage.copc.laz"

    def customProperty(self, key, default=None):
        return default


def _vector_layer(layer_id="vec-1", name="communes", provider="ogr"):
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.name.return_value = name
    layer.isValid.return_value = True
    layer.providerType.return_value = provider
    return layer


def _package(name, path):
    pkg = types.ModuleType(name)
    pkg.__path__ = [path]
    return pkg


def _stub_module(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def _install_chain():
    chain = {
        _ROOT: _package(_ROOT, _PLUGIN_ROOT),
        f"{_ROOT}.core": _package(f"{_ROOT}.core", os.path.join(_PLUGIN_ROOT, "core")),
        f"{_ROOT}.core.services": _package(f"{_ROOT}.core.services", os.path.join(_PLUGIN_ROOT, "core", "services")),
        f"{_ROOT}.infrastructure": _package(f"{_ROOT}.infrastructure", os.path.join(_PLUGIN_ROOT, "infrastructure")),
        f"{_ROOT}.infrastructure.database": _package(
            f"{_ROOT}.infrastructure.database", os.path.join(_PLUGIN_ROOT, "infrastructure", "database")),
        _UTILS: _stub_module(
            _UTILS,
            is_sip_deleted=lambda obj: False,
            is_layer_valid=lambda layer: bool(layer.isValid()),
            is_layer_source_available=lambda layer, require_psycopg2=False: True,
            is_filtermate_temp_layer=lambda layer: False,
        ),
        f"{_ROOT}.adapters": _stub_module(f"{_ROOT}.adapters"),
        f"{_ROOT}.adapters.qgis": _stub_module(f"{_ROOT}.adapters.qgis"),
        _CAPABILITY: _stub_module(_CAPABILITY, get_filterable_layer_types=lambda: (MagicMock,)),
    }
    for name, mod in chain.items():
        sys.modules[name] = mod
        if "." in name:
            parent, _, leaf = name.rpartition(".")
            setattr(sys.modules[parent], leaf, mod)
    return chain


def _load_service():
    _install_chain()
    qualname = f"{_ROOT}.core.services.layer_lifecycle_service"
    spec = importlib.util.spec_from_file_location(qualname, _SERVICE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualname] = module
    spec.loader.exec_module(module)
    return module


lls = _load_service()


@pytest.fixture(scope="module", autouse=True)
def _sandbox_lifetime():
    """The chain stays installed while the tests run (deferred imports need it)."""
    yield
    for name in [n for n in sys.modules if n == _ROOT or n.startswith(_ROOT + ".")]:
        sys.modules.pop(name, None)


@pytest.fixture
def capability(monkeypatch):
    """Fresh stubs for each test; returns the capability and utils modules."""
    cap = sys.modules[_CAPABILITY]
    utils = sys.modules[_UTILS]
    monkeypatch.setattr(cap, "get_filterable_layer_types", lambda: (lls.QgsVectorLayer,))
    monkeypatch.setattr(utils, "is_sip_deleted", lambda obj: False)
    monkeypatch.setattr(utils, "is_layer_valid", lambda layer: bool(layer.isValid()))
    monkeypatch.setattr(utils, "is_layer_source_available", lambda layer, require_psycopg2=False: True)
    monkeypatch.setattr(utils, "is_filtermate_temp_layer", lambda layer: False)
    return cap, utils


def _enable_point_clouds(monkeypatch, cap):
    monkeypatch.setattr(cap, "get_filterable_layer_types", lambda: (lls.QgsVectorLayer, _FakePointCloudLayer))


def _service():
    return lls.LayerLifecycleService.__new__(lls.LayerLifecycleService)


@pytest.mark.unit
class TestFilterUsableLayersPointCloud:

    def test_flag_off_keeps_vector_only(self, capability, caplog):
        caplog.set_level(logging.INFO, logger=_LOGGER)
        vec, pc = _vector_layer(), _FakePointCloudLayer()

        assert _service().filter_usable_layers([vec, pc]) == [vec]
        assert "not a filterable layer" in caplog.text
        assert "not a vector layer" not in caplog.text

    def test_flag_on_accepts_point_clouds_in_input_order(self, capability, monkeypatch):
        cap, utils = capability
        _enable_point_clouds(monkeypatch, cap)
        checked = []
        monkeypatch.setattr(utils, "is_layer_source_available",
                            lambda layer, require_psycopg2=False: checked.append(layer) or True)
        vec, pc, vec2 = _vector_layer(), _FakePointCloudLayer(), _vector_layer("vec-2", "routes")

        assert _service().filter_usable_layers([pc, vec, vec2]) == [pc, vec, vec2]
        assert checked == [pc, vec, vec2]

    def test_types_are_resolved_once_per_call(self, capability, monkeypatch):
        cap, _ = capability
        calls = []

        def resolve():
            calls.append(1)
            return (lls.QgsVectorLayer, _FakePointCloudLayer)

        monkeypatch.setattr(cap, "get_filterable_layer_types", resolve)
        layers = [_FakePointCloudLayer(str(i)) for i in range(5)] + [_vector_layer()]
        assert len(_service().filter_usable_layers(layers)) == 6
        assert len(calls) == 1

    def test_missing_capability_module_falls_back_to_vector_only(self, capability, monkeypatch, caplog):
        caplog.set_level(logging.INFO, logger=_LOGGER)
        monkeypatch.setitem(sys.modules, _CAPABILITY, None)
        vec, pc = _vector_layer(), _FakePointCloudLayer()

        assert _service().filter_usable_layers([pc, vec]) == [vec]
        assert "not a filterable layer" in caplog.text

    def test_deleted_point_cloud_is_rejected_before_any_access(self, capability, monkeypatch):
        cap, utils = capability
        _enable_point_clouds(monkeypatch, cap)
        pc = _FakePointCloudLayer()
        pc.name = MagicMock(side_effect=RuntimeError("wrapped C/C++ object deleted"))
        monkeypatch.setattr(utils, "is_sip_deleted", lambda obj: obj is pc)
        vec = _vector_layer()

        assert _service().filter_usable_layers([pc, vec]) == [vec]
        pc.name.assert_not_called()

    def test_invalid_point_cloud_is_rejected(self, capability, monkeypatch, caplog):
        caplog.set_level(logging.INFO, logger=_LOGGER)
        cap, _ = capability
        _enable_point_clouds(monkeypatch, cap)
        pc = _FakePointCloudLayer(valid=False)
        vec = _vector_layer()

        assert _service().filter_usable_layers([pc, vec]) == [vec]
        assert "invalid layer" in caplog.text

    def test_unavailable_point_cloud_source_is_rejected(self, capability, monkeypatch):
        cap, utils = capability
        _enable_point_clouds(monkeypatch, cap)
        pc = _FakePointCloudLayer()
        monkeypatch.setattr(utils, "is_layer_source_available",
                            lambda layer, require_psycopg2=False: layer is not pc)
        vec = _vector_layer()

        assert _service().filter_usable_layers([pc, vec]) == [vec]

    def test_temporary_point_cloud_is_rejected(self, capability, monkeypatch):
        cap, utils = capability
        _enable_point_clouds(monkeypatch, cap)
        pc = _FakePointCloudLayer()
        monkeypatch.setattr(utils, "is_filtermate_temp_layer", lambda layer: layer is pc)

        assert _service().filter_usable_layers([pc]) == []


@pytest.mark.unit
class TestFilterUsableLayersAst:

    def _method(self):
        tree = ast.parse(open(_SERVICE, encoding="utf-8").read())
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "LayerLifecycleService"):
            for node in cls.body:
                if isinstance(node, ast.FunctionDef) and node.name == "filter_usable_layers":
                    return node
        raise AssertionError("filter_usable_layers not found")

    def test_isinstance_uses_the_resolved_filterable_types(self):
        method = self._method()
        second_args = [
            n.args[1] for n in ast.walk(method)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "isinstance" and len(n.args) == 2
        ]
        assert second_args
        assert not any(isinstance(a, ast.Name) and a.id == "QgsVectorLayer" for a in second_args)
        assert any(isinstance(a, ast.Name) and a.id == "filterable_types" for a in second_args)

    def test_capability_is_imported_lazily_with_a_vector_fallback_outside_the_loop(self):
        method = self._method()
        guarded = [n for n in ast.walk(method) if isinstance(n, ast.Try)]
        matching = []
        for node in guarded:
            imports = [s for s in node.body if isinstance(s, ast.ImportFrom)]
            if any(s.module == "adapters.qgis.point_cloud_capability" and s.level == 3 for s in imports):
                matching.append(node)
        assert len(matching) == 1
        node = matching[0]
        assert any(isinstance(h.type, ast.Name) and h.type.id == "ImportError" for h in node.handlers)
        loops = [n for n in ast.walk(method) if isinstance(n, ast.For)]
        assert not any(node in ast.walk(loop) for loop in loops)
        assignments = [
            n for n in ast.walk(node)
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "filterable_types" for t in n.targets)
        ]
        assert len(assignments) == 2

    def test_rejection_reason_names_filterable_layers(self):
        method = self._method()
        joined = {
            v.value for n in ast.walk(method) if isinstance(n, ast.JoinedStr)
            for v in n.values if isinstance(v, ast.Constant) and isinstance(v.value, str)
        }
        assert any("not a filterable layer" in s for s in joined)
        assert not any("not a vector layer" in s for s in joined)

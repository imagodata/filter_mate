# -*- coding: utf-8 -*-
"""
The undo point of a turn of the agent when its project closes, and the count widget on a web service.

``turn_checkpoint`` and ``agent_widgets`` are loaded by path under a private package: the pure domain is the real
one (``core``), QGIS and the other adapters are stand-ins.
"""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_agent_turn_lifecycle_test"


class Layer:
    def __init__(self, layer_id, subset=""):
        self._id, self.subset = layer_id, subset

    def id(self):
        return self._id

    def name(self):
        return self._id

    def isValid(self):
        return True


class Project:
    def __init__(self, layers):
        self.layers = {layer.id(): layer for layer in layers}

    def mapLayers(self):
        return dict(self.layers)

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)


class Effects:
    """EffectsRecorder stand-in: a project note the turn kept, compared at its end."""

    def before_call(self, call):
        pass

    def finish(self):
        return (("notes", "", (), ("a note",)),)


def _module(monkeypatch, name, **attrs):
    module = types.ModuleType(f"{_PKG}{name}")
    module.__path__ = []
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    return module


def _load(monkeypatch, name, rel):
    spec = importlib.util.spec_from_file_location(f"{_PKG}.{name}", _ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def packages(monkeypatch):
    _module(monkeypatch, "")
    core = types.ModuleType(f"{_PKG}.core")
    core.__path__ = [str(_ROOT / "core")]
    monkeypatch.setitem(sys.modules, core.__name__, core)
    for name in (".adapters", ".adapters.agent", ".adapters.public_api", ".adapters.qgis",
                 ".adapters.qgis.coverage_layers"):
        _module(monkeypatch, name)


@pytest.fixture
def checkpoint_module(monkeypatch, packages):
    filter_state = importlib.import_module(f"{_PKG}.core.domain.filter_state")
    layer_kind = importlib.import_module(f"{_PKG}.core.domain.layer_kind")
    service = types.SimpleNamespace(history=filter_state.CrossOperationHistory())
    _module(monkeypatch, ".adapters.public_api.operations", _api_service=lambda: service, busy_reason=lambda: "",
            layer_kind=lambda layer: layer_kind.LayerKind.VECTOR)
    _module(monkeypatch, ".adapters.qgis.coverage_layers.snapshots",
            take_snapshot=lambda layer, kind: filter_state.LayerSnapshot(layer.id(), kind.value, subset=layer.subset))
    _module(monkeypatch, ".adapters.agent.turn_effects", EffectsRecorder=Effects, apply_effects=MagicMock())
    holder = types.SimpleNamespace(project=None)
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject",
                        types.SimpleNamespace(instance=lambda: holder.project), raising=False)
    module = _load(monkeypatch, "adapters.agent.turn_checkpoint", "adapters/agent/turn_checkpoint.py")
    module._test_service, module._test_holder = service, holder
    return module


def test_a_turn_discarded_with_its_project_is_never_recorded(checkpoint_module):
    """2026-11-12: committed after the project changed, the turn compared the closed project with the next one."""
    holder, history = checkpoint_module._test_holder, checkpoint_module._test_service.history
    old = Layer("roads")
    holder.project = Project([old])
    checkpoint = checkpoint_module.TurnCheckpoint()
    checkpoint.begin(types.SimpleNamespace(name="add_project_note", arguments={}))
    old.subset = "x > 1"
    checkpoint.discard()  # the project is cleared while the request runs
    holder.project = Project([Layer("rivers")])  # the next project
    assert checkpoint.commit() == ()  # the end of the cancelled request
    assert not history.can_undo(checkpoint_module.HISTORY_KEY)


def test_a_turn_kept_open_is_recorded(checkpoint_module):
    holder, history = checkpoint_module._test_holder, checkpoint_module._test_service.history
    layer = Layer("roads")
    holder.project = Project([layer])
    checkpoint = checkpoint_module.TurnCheckpoint()
    checkpoint.begin(types.SimpleNamespace(name="apply_filter", arguments={}))
    layer.subset = "x > 1"
    assert list(checkpoint.commit()) == ["roads"]
    assert history.can_undo(checkpoint_module.HISTORY_KEY)

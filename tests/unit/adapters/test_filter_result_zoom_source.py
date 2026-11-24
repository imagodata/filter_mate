# -*- coding: utf-8 -*-
"""After a filter, the map goes to the filtered extent of the source layer (FilterResultHandler._handle_auto_zoom).

2026-11-24: an attribute filter, a Disjoint or a Contain zoomed to the union of the source and its targets;
the source alone is what the user filtered from.
"""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_filter_result_zoom_test"


def _load():
    """Load adapters/filter_result_handler.py inside a package, so its relative imports resolve."""
    for name, path in (("", _ROOT), (".adapters", _ROOT / "adapters"), (".infrastructure", _ROOT / "infrastructure"),
                       (".config", _ROOT / "config")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.filter_result_handler")


def _layer(layer_id):
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.isValid.return_value = True
    return layer


@pytest.mark.parametrize("filtering", [
    {"has_geometric_predicates": False, "geometric_predicates": []},
    {"has_geometric_predicates": True, "geometric_predicates": ["Intersect", "Disjoint"]},
    {"has_geometric_predicates": True, "geometric_predicates": ["Contain"]},
    {"has_geometric_predicates": True, "geometric_predicates": ["Within"], "has_buffer_value": True,
     "buffer_value": 250.0},
])
def test_the_zoom_goes_to_the_source_layer_only(monkeypatch, filtering):
    module = _load()
    auto_zoom = importlib.import_module(f"{_PKG}.adapters.auto_zoom")
    calls = []
    monkeypatch.setattr(auto_zoom, "auto_zoom_to_filtered", lambda layers, *a, **k: calls.append((layers, k)))
    source, cables, demand = _layer("source"), _layer("cables"), _layer("demand")
    project = MagicMock()
    project.mapLayer.side_effect = {"cables": cables, "demand": demand}.get
    monkeypatch.setattr(module.QgsProject, "instance", lambda: project, raising=False)

    handler = module.FilterResultHandler(get_iface_callback=lambda: MagicMock())
    handler._handle_auto_zoom(source, {
        "filtering": filtering,
        "task": {"layers": [{"layer_id": "cables"}, {"layer_id": "demand"}]},
        "_subset_change_token": 3,
    })

    assert len(calls) == 1
    layers, kwargs = calls[0]
    assert layers == [source]
    assert kwargs["expected_token"] == 3
    assert "grow_by" not in kwargs

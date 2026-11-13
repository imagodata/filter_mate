# -*- coding: utf-8 -*-
"""Undo and redo give each layer its own filter, never the source's (user log, PostgreSQL project).

One undo stack holds the filters of every layer. An entry's ``expression`` belongs to its source
(``layer_ids[0]``); the subset of each target is in ``metadata['remote_layers']``. Taking the last entry
of a layer that was only a target of it gave that layer the source's expression:
``SELECT * FROM "wyre"."zone_pop" WHERE "zone_mro"."id" IN (...)``, rejected by PostgreSQL (missing
FROM-clause entry for table "zone_mro").
"""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

from core.services.history_service import HistoryService

pytestmark = pytest.mark.unit


_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_undo_cross_layer_test"

MRO_EXPR = '"zone_mro"."id" IN (\'8a\')'
POP_EXPR = 'EXISTS (SELECT 1 FROM "wyre"."zone_mro" AS __source WHERE x)'
FEED_EXPR = 'EXISTS (SELECT 1 FROM "wyre"."zone_mro" AS __source WHERE f)'
POP_ALONE = '("code" = 1) AND (EXISTS (SELECT 1 FROM "wyre"."zone_mro" AS __source WHERE x))'


def _load():
    """Load adapters/undo_redo_handler.py inside a package, so its relative imports resolve."""
    for name, path in (("", _ROOT), (".adapters", _ROOT / "adapters"), (".infrastructure", _ROOT / "infrastructure"),
                       (".core", _ROOT / "core")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.undo_redo_handler")


def _layer(layer_id, subset):
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.name.return_value = layer_id
    layer.isValid.return_value = True
    layer.subsetString.return_value = subset
    return layer


@pytest.fixture
def env(monkeypatch):
    """Zones MRO filtered from a picked feature, Zones POP and the feeders as targets."""
    module = _load()
    layers = {"mro": _layer("mro", MRO_EXPR), "pop": _layer("pop", POP_EXPR), "feed": _layer("feed", FEED_EXPR)}
    project = types.SimpleNamespace(mapLayer=layers.get)
    monkeypatch.setattr(module, "QgsProject", types.SimpleNamespace(instance=lambda: project))
    monkeypatch.setattr(module, "is_layer_source_available", lambda layer: layer is not None)
    applied = []

    def restore(layer, expression, errors=None):
        applied.append((layer.id(), expression))
        layer.subsetString.return_value = expression
        return True

    monkeypatch.setattr(module, "_restore_history_subset", restore)
    history = HistoryService()
    project_layers = {layer_id: {"infos": {}} for layer_id in layers}
    handler = module.UndoRedoHandler(history, lambda: project_layers, lambda: project, lambda: None, lambda *a: None)
    monkeypatch.setattr(handler, "_refresh_affected_layers", lambda *a: None)
    history.push_global_state("mro", MRO_EXPR, 1, {"pop": (POP_EXPR, 9), "feed": (FEED_EXPR, 4)},
                              previous_expressions={"mro": "", "pop": "", "feed": ""})
    return handler, history, layers, applied


def test_undo_of_a_former_target_filtered_alone(env):
    """The user's case: Zones POP, a target of the filter from Zones MRO, then filtered alone; Undo."""
    handler, history, layers, applied = env
    layers["pop"].subsetString.return_value = POP_ALONE
    handler.push_filter_to_history(layers["pop"], {"task": {"layers": []}}, 3, "postgresql", 1)

    assert handler.handle_undo(layers["pop"], [], False)

    assert applied == [("pop", POP_EXPR)]


def test_previous_expression_of_a_new_source_that_was_a_target(env):
    handler, history, layers, applied = env
    layers["pop"].subsetString.return_value = POP_ALONE  # the new filter is applied when it is recorded

    assert handler._collect_previous_expressions("pop", ["feed"]) == {"pop": POP_EXPR, "feed": FEED_EXPR}


def test_previous_expression_of_a_target_that_was_the_source(env):
    handler, history, layers, applied = env
    layers["mro"].subsetString.return_value = "EXISTS (new)"  # the new filter is applied when it is recorded

    assert handler._collect_previous_expressions("pop", ["mro"])["mro"] == MRO_EXPR


def test_global_redo_with_another_current_layer(env):
    """Filter from Zones MRO with targets, Undo, Zones POP current, Redo: every layer gets its own filter back."""
    handler, history, layers, applied = env
    history.undo()
    applied.clear()

    assert handler.handle_redo(layers["pop"], [], False)

    assert sorted(applied) == [("feed", FEED_EXPR), ("mro", MRO_EXPR), ("pop", POP_EXPR)]
    assert history.can_redo is False


def test_global_redo_with_a_current_layer_outside_the_entry(env):
    handler, history, layers, applied = env
    history.undo()
    other = MagicMock()
    other.id.return_value = "other"

    assert handler._perform_global_redo(other, {})

    assert sorted(applied) == [("feed", FEED_EXPR), ("mro", MRO_EXPR), ("pop", POP_EXPR)]


def test_layer_redo_goes_to_the_layer_of_the_entry(env):
    """Zones POP filtered alone, Undo, Zones MRO current, Redo: Zones POP gets its filter back, MRO keeps its own."""
    handler, history, layers, applied = env
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)
    history.undo()

    assert handler.handle_redo(layers["mro"], [], False)

    assert applied == [("pop", POP_ALONE)]
    assert history.peek_undo().layer_ids == ("pop",)


def test_layer_undo_leaves_an_entry_without_the_current_layer(env):
    """The last entry is Zones POP's: an Undo of the feeders alone neither clears them nor drops it."""
    handler, history, layers, applied = env
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)
    last = history.peek_undo()

    assert not handler.handle_undo(layers["feed"], [], False)

    assert applied == []
    assert history.peek_undo() is last

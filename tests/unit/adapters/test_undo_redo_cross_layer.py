# -*- coding: utf-8 -*-
"""Undo and redo give each layer its own filter, never the source's (user log, PostgreSQL project).

One undo stack holds the filters of every layer. An entry's ``expression`` belongs to its source
(``layer_ids[0]``); the subset of each target is in ``metadata['remote_layers']``. Taking the last entry
of a layer that was only a target of it gave that layer the source's expression:
``SELECT * FROM "wyre"."zone_pop" WHERE "zone_mro"."id" IN (...)``, rejected by PostgreSQL (missing
FROM-clause entry for table "zone_mro").
"""
import ast
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


def test_redo_from_each_layer_gives_it_its_own_filter(env):
    """Filter from Zones MRO with targets, Undo, Redo from Zones POP, then MRO, then the feeders, without the layers
    to filter: each gets its own filter back (2026-11-14: its own part only, the scope of Undo)."""
    handler, history, layers, applied = env
    history.undo()
    applied.clear()

    for layer_id in ("pop", "mro", "feed"):
        assert handler.handle_redo(layers[layer_id], [], False)

    assert applied == [("pop", POP_EXPR), ("mro", MRO_EXPR), ("feed", FEED_EXPR)]
    assert history.can_redo is False


def test_global_redo_with_a_current_layer_outside_the_entry(env):
    handler, history, layers, applied = env
    history.undo()
    other = MagicMock()
    other.id.return_value = "other"

    assert handler._perform_global_redo(other, {})

    assert sorted(applied) == [("feed", FEED_EXPR), ("mro", MRO_EXPR), ("pop", POP_EXPR)]


def test_layer_redo_leaves_the_entry_of_another_layer(env):
    """Zones POP filtered alone, Undo, Zones MRO current, Redo: neither layer changes, POP's entry waits for POP."""
    handler, history, layers, applied = env
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)
    history.undo()
    pending = history.peek_redo()

    assert not handler.handle_redo(layers["mro"], [], False)

    assert applied == []
    assert history.peek_redo() is pending

    assert handler.handle_redo(layers["pop"], [], False)

    assert applied == [("pop", POP_ALONE)]
    assert history.peek_undo() is pending


def test_layer_undo_leaves_an_entry_without_the_current_layer(env):
    """The last entry is Zones POP's: an Undo of the feeders alone neither clears them nor drops it."""
    handler, history, layers, applied = env
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)
    last = history.peek_undo()

    assert not handler.handle_undo(layers["feed"], [], False)

    assert applied == []
    assert history.peek_undo() is last


# Undo with "layers to filter" on restores the current layer and the checked layers only: an entry with
# another layer is left whole, else that layer keeps its filter and loses its undo step.

def test_filtered_undo_leaves_the_entry_of_a_layer_outside_the_selection(env):
    """Zones POP filtered alone; Zones MRO current, the feeders checked, Undo: nothing restored, nothing dropped."""
    handler, history, layers, applied = env
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)
    last = history.peek_undo()

    assert not handler.handle_undo(layers["mro"], ["feed"], True)

    assert applied == []
    assert history.peek_undo() is last and history.peek_redo() is None


def test_filtered_undo_leaves_an_entry_whose_source_is_not_selected(env):
    """The filter from Zones MRO had POP as target; POP current, the feeders checked: MRO cannot be restored."""
    handler, history, layers, applied = env
    last = history.peek_undo()

    assert not handler.handle_undo(layers["pop"], ["feed"], True)

    assert applied == []
    assert history.peek_undo() is last and history.peek_redo() is None


def test_filtered_undo_and_redo_of_an_entry_inside_the_selection(env):
    """Every layer of the entry selected: Undo restores them all, Redo gives each its filter back."""
    handler, history, layers, applied = env

    assert handler.handle_undo(layers["pop"], ["mro", "feed"], True)

    assert sorted(applied) == [("feed", ""), ("mro", ""), ("pop", "")]
    assert history.peek_undo() is None
    applied.clear()

    assert handler.handle_redo(layers["pop"], ["mro", "feed"], True)

    assert sorted(applied) == [("feed", FEED_EXPR), ("mro", MRO_EXPR), ("pop", POP_EXPR)]


def test_filtered_undo_and_redo_of_a_checked_layer_filtered_alone(env):
    """Zones POP filtered alone; MRO current with POP checked: Undo and Redo both reach POP's entry."""
    handler, history, layers, applied = env
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)

    assert handler.handle_undo(layers["mro"], ["pop"], True)
    assert handler.handle_redo(layers["mro"], ["pop"], True)

    assert applied == [("pop", POP_EXPR), ("pop", POP_ALONE)]


def test_redo_with_layers_to_filter_leaves_an_entry_with_a_layer_outside_the_selection(env):
    """Undone from Zones MRO with every layer; the feeders unchecked since: Redo would filter them again."""
    handler, history, layers, applied = env
    history.undo()

    assert not handler.handle_redo(layers["mro"], ["pop"], True)

    assert applied == []
    assert history.can_redo


# The Undo / Redo buttons are enabled when the click would take the step.

def _buttons(handler, layer, layers_to_filter):
    undo_button, redo_button = MagicMock(), MagicMock()
    handler.update_button_states(layer, layers_to_filter, undo_button, redo_button)
    return undo_button.setEnabled.call_args.args[0], redo_button.setEnabled.call_args.args[0]


def test_buttons_of_a_layer_whose_entry_is_not_the_last(env):
    """MRO's filter (with POP and the feeders), then POP filtered alone: the feeders have a history, not the last step."""
    handler, history, layers, applied = env
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)

    assert _buttons(handler, layers["feed"], []) == (False, False)
    assert _buttons(handler, layers["pop"], []) == (True, False)

    history.undo()

    assert _buttons(handler, layers["feed"], []) == (True, False)  # the last step is MRO's again, it had the feeders
    assert _buttons(handler, layers["mro"], []) == (True, False)
    assert _buttons(handler, layers["pop"], []) == (True, True)


def test_buttons_with_layers_to_filter(env):
    handler, history, layers, applied = env

    assert _buttons(handler, layers["pop"], ["feed"]) == (False, False)  # MRO's entry: MRO not selected
    assert _buttons(handler, layers["pop"], ["mro", "feed"]) == (True, False)


def _compiled(file_name, class_name, method_name, **names):
    """A method of the plugin, compiled alone (its module is not imported); ``names``: the globals it reads."""
    tree = ast.parse((_ROOT / file_name).read_text(encoding="utf-8"))
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    func = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
    namespace = {"logger": MagicMock(), **names}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[func], type_ignores=[])), file_name, "exec"), namespace)
    return namespace[method_name]


def test_buttons_follow_the_layers_to_filter_button(env):
    """Zones POP filtered alone; MRO current, POP checked in its layers to filter: Undo reaches POP's entry only
    when the layers to filter button is on, with the layers checked on screen (FilterMateApp._handle_undo_redo):
    a click in the list does not save them."""
    handler, history, layers, applied = env
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)
    targets_button = MagicMock()
    dock = types.SimpleNamespace(
        pushButton_action_undo_filter=MagicMock(), pushButton_action_redo_filter=MagicMock(),
        agent_has_focus=lambda: False, refresh_undo_tips=lambda *a: None, tabTools_current_index=0,
        _controller_integration=None, current_layer=layers["mro"],
        PROJECT_LAYERS={"mro": {"filtering": {"layers_to_filter": []}}}, get_layers_to_filter=lambda: ["pop"],
        pushButton_checkable_filtering_layers_to_filter=targets_button)
    app = types.SimpleNamespace(dockwidget=dock, _undo_redo_handler=handler)
    update = _compiled("filter_mate_app.py", "FilterMateApp", "update_undo_redo_buttons")

    targets_button.isChecked.return_value = False
    update(app)
    dock.pushButton_action_undo_filter.setEnabled.assert_called_with(False)

    targets_button.isChecked.return_value = True
    update(app)
    dock.pushButton_action_undo_filter.setEnabled.assert_called_with(True)


# The raster / point cloud targets of a vector source follow its Undo / Redo (launchTaskEvent): their steps
# pair with the filters of that source, so only a vector step taken on one of its entries reaches them.

def _launch_task_event():
    return _compiled("filter_mate_dockwidget.py", "FilterMateDockWidget", "launchTaskEvent")


def _dock(handler, history, layer, layers_to_filter=(), use_global=False):
    """The dock on ``layer``, a raster target among its layers to filter; the app runs the vector step."""
    integration = MagicMock()
    integration.delegate_point_cloud_task.return_value = False
    integration.delegate_split_coverage_targets.return_value = (list(layers_to_filter), ["raster"])
    integration.coverage_controller.vector_source_busy.return_value = False
    app = types.SimpleNamespace(appTasks={"filter": None, "unfilter": None, "reset": None}, history_manager=history,
                                _initializing_project=False, _loading_new_project=False)

    def emit(task_name):  # FilterMateApp._handle_undo_redo, run synchronously by the signal
        step = handler.handle_undo if task_name == "undo" else handler.handle_redo
        step(layer, list(layers_to_filter), use_global)

    dock = types.SimpleNamespace(_controller_integration=integration, widgets_initialized=True, current_layer=layer,
                                 PROJECT_LAYERS={layer.id(): {"filtering": {}}},
                                 get_layers_to_filter=lambda: list(layers_to_filter) + ["raster"],
                                 setLayerVariableEvent=lambda *a: None, launchingTask=types.SimpleNamespace(emit=emit),
                                 filter_mate_app=app)
    return dock, integration


def test_raster_targets_follow_only_the_undo_steps_of_their_source(env):
    """The feeders filtered with a raster target, then Zones POP alone; the feeders current, Undo: the vector
    step is refused (POP's entry is the last one), the raster target keeps its clip as well."""
    handler, history, layers, applied = env
    history.get_or_create_history("feed").push_state("f2", 2)
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)
    launch = _launch_task_event()

    dock, integration = _dock(handler, history, layers["feed"])
    launch(dock, None, "undo")
    assert applied == []
    integration.delegate_vector_source_coverage_task.assert_not_called()

    dock, integration = _dock(handler, history, layers["pop"])
    launch(dock, None, "undo")
    integration.delegate_vector_source_coverage_task.assert_called_once_with("undo", layers["pop"], ["raster"])

    dock, integration = _dock(handler, history, layers["feed"])
    launch(dock, None, "undo")
    assert applied == [("pop", POP_EXPR), ("feed", FEED_EXPR)]
    integration.delegate_vector_source_coverage_task.assert_called_once_with("undo", layers["feed"], ["raster"])


def test_raster_targets_follow_only_the_redo_steps_of_their_source(env):
    handler, history, layers, applied = env
    history.get_or_create_history("feed").push_state("f2", 2)
    history.undo()
    launch = _launch_task_event()

    dock, integration = _dock(handler, history, layers["mro"])
    launch(dock, None, "redo")
    assert applied == []
    integration.delegate_vector_source_coverage_task.assert_not_called()

    dock, integration = _dock(handler, history, layers["feed"])
    launch(dock, None, "redo")
    assert applied == [("feed", "f2")]
    integration.delegate_vector_source_coverage_task.assert_called_once_with("redo", layers["feed"], ["raster"])


def test_raster_targets_stay_when_undo_takes_the_step_of_a_checked_layer(env):
    """Zones POP filtered alone; MRO current with POP checked, Undo restores POP: MRO's raster target stays."""
    handler, history, layers, applied = env
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)

    dock, integration = _dock(handler, history, layers["mro"], ["pop"], True)
    _launch_task_event()(dock, None, "undo")

    assert applied == [("pop", POP_EXPR)]
    integration.delegate_vector_source_coverage_task.assert_not_called()


def test_compare_shows_the_raster_targets_undo_restores(env):
    """Compare shows the state Undo brings back: the raster target of POP and of MRO, clipped by their last runs,
    only with an entry of that source (CompareController.last_operation)."""
    import dataclasses
    from core.domain.compare_states import BeforeMap, from_cross_operation, map_from_history_entry, map_from_operation
    handler, history, layers, applied = env
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)
    clip = types.SimpleNamespace(op_id=7, changes=((types.SimpleNamespace(layer_id="raster", subset="", source="dem.tif",
                                                                          provider="gdal"),
                                                    types.SimpleNamespace(source="clip.vrt")),))
    coverage = types.SimpleNamespace(active_layer=None, _linked_runs={"pop": [object()], "mro": [object()]},
                                     service=types.SimpleNamespace(history=types.SimpleNamespace(peek_undo=lambda i: clip)),
                                     _run_is_next=lambda run, operation: True)
    last_operation = _compiled("ui/controllers/compare_controller.py", "CompareController", "last_operation",
                               BeforeMap=BeforeMap, map_from_history_entry=map_from_history_entry,
                               map_from_operation=map_from_operation, from_cross_operation=from_cross_operation,
                               replace=dataclasses.replace)

    def compared(layer, layers_to_filter):
        targets_button = MagicMock()
        targets_button.isChecked.return_value = bool(layers_to_filter)
        dock = types.SimpleNamespace(agent_has_focus=lambda: False, current_layer=layer,
                                     filter_mate_app=types.SimpleNamespace(history_manager=history),
                                     pushButton_checkable_filtering_layers_to_filter=targets_button,
                                     get_layers_to_filter=lambda: list(layers_to_filter))
        controller = types.SimpleNamespace(_dock=dock, _integration=types.SimpleNamespace(coverage_controller=coverage))
        return sorted(state.layer_id for state in last_operation(controller).states)

    assert compared(layers["pop"], []) == ["pop", "raster"]
    assert compared(layers["mro"], ["pop"]) == ["pop"]  # Undo takes POP's entry: MRO's raster target stays

    # 2026-11-14: POP's entry undone, then MRO's part of its filter: what is left is headed by POP, yet no run of POP
    assert handler.handle_undo(layers["pop"], [], False) and handler.handle_undo(layers["mro"], [], False)
    assert compared(layers["pop"], []) == ["pop"]


def test_undo_gives_back_what_the_layer_held_before_the_filter_not_what_the_history_last_said(env):
    """2026-11-14: a layer changed outside the dock (a turn of the agent, a raster source, the query builder of
    QGIS), then filtered in the dock. The entry took its previous filter from the last entry of the history, so
    Undo went past the change made outside, and the history panel drew the map before that filter without it."""
    handler, history, layers, applied = env
    pop = layers["pop"]
    parameters = {"infos": {"layer_provider_type": "ogr"}, "task": {"layers": []}}
    handler.initialize_filter_history(pop, [], parameters)
    pop.subsetString.return_value = "A"
    handler.push_filter_to_history(pop, parameters, 5, "ogr", 1)
    pop.subsetString.return_value = "OUTSIDE"  # not through the dock: the history knows nothing of it
    handler.initialize_filter_history(pop, [], parameters)
    pop.subsetString.return_value = "B"
    handler.push_filter_to_history(pop, parameters, 5, "ogr", 1)
    assert history.peek_undo().previous_filters == (("pop", "OUTSIDE"),)
    assert handler.handle_undo(pop, [], False, None) is True
    assert applied[-1] == ("pop", "OUTSIDE")


def test_a_run_that_did_not_read_the_layers_takes_nothing_from_the_run_before(env):
    """What was read before a run is for that run alone: the next push without a reading falls back on the history."""
    handler, history, layers, applied = env
    pop = layers["pop"]
    parameters = {"infos": {"layer_provider_type": "ogr"}, "task": {"layers": []}}
    handler.initialize_filter_history(pop, [], parameters)
    pop.subsetString.return_value = "A"
    handler.push_filter_to_history(pop, parameters, 5, "ogr", 1)
    pop.subsetString.return_value = "B"
    handler.push_filter_to_history(pop, parameters, 5, "ogr", 1)  # no initialize before this one
    assert history.peek_undo().previous_filters == (("pop", "A"),)


def _global_run(handler, layers, monkeypatch, after):
    """One filter from Zones MRO with Zones POP as its target, as the dock runs it: read, filter, record."""
    mro, pop = layers["mro"], layers["pop"]
    monkeypatch.setattr(handler, "_get_project", lambda: types.SimpleNamespace(mapLayer=layers.get, mapLayers=lambda: layers))
    targets = [{"layer_id": "pop", "layer_provider_type": "ogr"}]
    parameters = {"infos": {"layer_provider_type": "ogr"}, "task": {"layers": targets}}
    handler.initialize_filter_history(mro, targets, parameters)
    mro.subsetString.return_value, pop.subsetString.return_value = after
    monkeypatch.setattr(handler, "_collect_remote_layers_history", lambda *args: {"pop": (after[1], 3)})
    handler.push_filter_to_history(mro, parameters, 5, "ogr", 2)


def test_a_change_made_outside_the_dock_is_never_undone_as_a_step_of_the_dock(env, monkeypatch):
    """A review of 2026-11-14. The "Pre-filter state" entry of a run took its previous filters from the history: the
    second Undo gave Zones POP the filter of the run before, undoing what the agent had set meanwhile as if the dock
    had done it."""
    handler, history, layers, applied = env
    mro, pop = layers["mro"], layers["pop"]
    pop.subsetString.return_value = "OUTSIDE"
    _global_run(handler, layers, monkeypatch, ("M2", "P2"))
    assert dict(history.peek_undo().previous_filters) == {"mro": MRO_EXPR, "pop": "OUTSIDE"}
    assert handler.handle_undo(mro, ["pop"], True, None) is True
    assert pop.subsetString() == "OUTSIDE" and mro.subsetString() == MRO_EXPR
    del applied[:]
    assert handler.handle_undo(mro, ["pop"], True, None) is True  # the state before the run: nothing changes
    assert pop.subsetString() == "OUTSIDE" and mro.subsetString() == MRO_EXPR, applied


def test_the_first_filter_of_a_layer_never_takes_away_a_filter_set_outside_the_dock(env):
    """A review of 2026-11-14: "Initial state" had "" as its previous filter, so a second Undo emptied a layer whose
    filter the dock had never set."""
    handler, history, layers, applied = env
    history.clear()
    feed = layers["feed"]
    feed.subsetString.return_value = "X"  # set in QGIS, before any filter of the dock
    parameters = {"infos": {"layer_provider_type": "ogr"}, "task": {"layers": []}}
    handler.initialize_filter_history(feed, [], parameters)
    feed.subsetString.return_value = "X AND y"
    handler.push_filter_to_history(feed, parameters, 5, "ogr", 1)
    assert handler.handle_undo(feed, [], False, None) is True and feed.subsetString() == "X"
    handler.handle_undo(feed, [], False, None)
    assert feed.subsetString() == "X"


def test_the_reading_of_a_run_goes_with_its_parameters_not_with_the_handler(env):
    """A review of 2026-11-14: a run refused after its layers were read left its reading to the run that ended next."""
    handler, history, layers, applied = env
    pop, feed = layers["pop"], layers["feed"]
    first = {"infos": {"layer_provider_type": "ogr"}, "task": {"layers": []}}
    handler.initialize_filter_history(pop, [], first)
    pop.subsetString.return_value = "A"
    refused = {"infos": {"layer_provider_type": "ogr"}, "task": {"layers": []}}
    handler.initialize_filter_history(feed, [], refused)  # read, then never run
    handler.push_filter_to_history(pop, first, 5, "ogr", 1)
    assert history.peek_undo().previous_filters == (("pop", POP_EXPR),)
    assert "before_run" not in first["task"]


# 2026-11-14: Undo without the layers to filter restores the current layer alone. Of the filter from Zones MRO it
# popped the whole entry: Zones POP and the feeders kept their filter and lost their step. Their part stays to undo.

def _stacks(history):
    return ([entry.layer_ids for entry in history.get_undo_stack()], [entry.layer_ids for entry in history.get_redo_stack()])


def test_the_part_of_the_source_undone_then_the_rest_from_the_other_layers(env):
    handler, history, layers, applied = env

    assert handler.handle_undo(layers["mro"], [], False)

    assert applied == [("mro", "")]
    assert layers["pop"].subsetString() == POP_EXPR and layers["feed"].subsetString() == FEED_EXPR
    assert _stacks(history) == ([("pop", "feed")], [("mro",)])
    assert _buttons(handler, layers["mro"], []) == (False, True)  # the rest is not MRO's: its Undo waits
    assert _buttons(handler, layers["pop"], []) == (True, False)
    assert _buttons(handler, layers["feed"], []) == (True, False)

    assert handler.handle_undo(layers["pop"], [], False)
    assert handler.handle_undo(layers["feed"], [], False)

    assert applied == [("mro", ""), ("pop", ""), ("feed", "")]
    assert _stacks(history) == ([], [("mro",), ("pop",), ("feed",)])


def test_the_part_of_a_target_undone_then_the_source(env):
    handler, history, layers, applied = env

    assert handler.handle_undo(layers["pop"], [], False)

    assert applied == [("pop", "")] and layers["mro"].subsetString() == MRO_EXPR
    rest = history.peek_undo()
    assert rest.layer_ids == ("mro", "feed") and rest.expression_for("mro") == MRO_EXPR
    assert rest.expression_for("feed") == FEED_EXPR

    assert handler.handle_undo(layers["mro"], [], False)
    assert handler.handle_undo(layers["feed"], [], False)

    assert applied == [("pop", ""), ("mro", ""), ("feed", "")]
    # Redo walks back the other way, each layer its own part, each with its own filter
    assert not handler.handle_redo(layers["pop"], [], False)  # the feeders' part is next
    for layer_id in ("feed", "mro", "pop"):
        assert handler.handle_redo(layers[layer_id], [], False)
    assert applied[3:] == [("feed", FEED_EXPR), ("mro", MRO_EXPR), ("pop", POP_EXPR)]
    assert _stacks(history) == ([("feed",), ("mro",), ("pop",)], [])


def test_the_part_undone_then_redone(env):
    handler, history, layers, applied = env

    assert handler.handle_undo(layers["mro"], [], False)
    assert handler.handle_redo(layers["mro"], [], False)

    assert applied == [("mro", ""), ("mro", MRO_EXPR)]
    assert _stacks(history) == ([("pop", "feed"), ("mro",)], [])  # alone, on top of the rest of its step
    assert _buttons(handler, layers["pop"], []) == (False, False)  # MRO's part goes first again

    assert handler.handle_undo(layers["mro"], [], False)
    assert handler.handle_undo(layers["pop"], [], False)
    assert applied[2:] == [("mro", ""), ("pop", "")]


def test_the_part_undone_redone_then_undone_with_every_layer(env):
    """MRO's part undone and redone, then Undo with the layers to filter on, every layer checked: the part redone is
    a step of its own (not joined again to the rest), the next Undo takes the rest of the filter, Redo the same."""
    handler, history, layers, applied = env
    handler.handle_undo(layers["mro"], [], False)
    handler.handle_redo(layers["mro"], [], False)
    del applied[:]

    assert handler.handle_undo(layers["mro"], ["pop", "feed"], True)
    assert applied == [("mro", "")]
    assert handler.handle_undo(layers["mro"], ["pop", "feed"], True)
    assert sorted(applied[1:]) == [("feed", ""), ("pop", "")]
    assert history.can_undo is False

    assert handler.handle_redo(layers["mro"], ["pop", "feed"], True)
    assert sorted(applied[3:]) == [("feed", FEED_EXPR), ("pop", POP_EXPR)]
    assert handler.handle_redo(layers["mro"], ["pop", "feed"], True)
    assert applied[5:] == [("mro", MRO_EXPR)]
    assert history.can_redo is False


def test_a_new_filter_after_a_part_undone_clears_the_redo_stack(env):
    handler, history, layers, applied = env
    handler.handle_undo(layers["mro"], [], False)

    history.get_or_create_history("mro").push_state('"zone_mro"."id" IN (\'9b\')', 1)

    assert history.can_redo is False
    assert _stacks(history) == ([("pop", "feed"), ("mro",)], [])
    assert handler.handle_undo(layers["mro"], [], False) and applied[-1] == ("mro", "")


def test_a_part_whose_layer_refuses_its_filter_stays(env, monkeypatch):
    handler, history, layers, applied = env
    entry = history.peek_undo()
    monkeypatch.setattr(_load(), "_restore_history_subset", lambda *args, **kwargs: False)

    assert not handler.handle_undo(layers["pop"], [], False)

    assert history.peek_undo() is entry and history.can_redo is False


def test_raster_targets_follow_the_part_of_their_source_only(env):
    """MRO filtered Zones POP, the feeders and a raster target: its undo steps pair with MRO's runs. MRO's part undone
    takes them along; what is left of the entry, now headed by POP, is no run of POP (whose own raster steps stay)."""
    handler, history, layers, applied = env
    launch = _launch_task_event()

    dock, integration = _dock(handler, history, layers["mro"])
    launch(dock, None, "undo")
    assert applied == [("mro", "")]
    integration.delegate_vector_source_coverage_task.assert_called_once_with("undo", layers["mro"], ["raster"])

    dock, integration = _dock(handler, history, layers["pop"])
    launch(dock, None, "undo")
    assert applied[-1] == ("pop", "")
    integration.delegate_vector_source_coverage_task.assert_not_called()

    dock, integration = _dock(handler, history, layers["mro"])
    launch(dock, None, "redo")  # POP's part is next: nothing
    assert applied[-1] == ("pop", "")
    integration.delegate_vector_source_coverage_task.assert_not_called()

    dock, integration = _dock(handler, history, layers["pop"])
    launch(dock, None, "redo")
    assert applied[-1] == ("pop", POP_EXPR)
    integration.delegate_vector_source_coverage_task.assert_not_called()

    dock, integration = _dock(handler, history, layers["mro"])
    launch(dock, None, "redo")
    assert applied[-1] == ("mro", MRO_EXPR)
    integration.delegate_vector_source_coverage_task.assert_called_once_with("redo", layers["mro"], ["raster"])


def test_raster_targets_stay_when_a_target_part_is_undone_first(env):
    handler, history, layers, applied = env
    launch = _launch_task_event()

    dock, integration = _dock(handler, history, layers["pop"])
    launch(dock, None, "undo")
    assert applied == [("pop", "")]
    integration.delegate_vector_source_coverage_task.assert_not_called()

    dock, integration = _dock(handler, history, layers["mro"])
    launch(dock, None, "undo")
    assert applied[-1] == ("mro", "")
    integration.delegate_vector_source_coverage_task.assert_called_once_with("undo", layers["mro"], ["raster"])


def test_the_history_panel_reads_the_rest_and_the_part_undone(env):
    """The panel lists what is left of the filter (applied, POP and the feeders, the states before them) and MRO's
    part (undone); the raster step of MRO's run pairs with that part, never with the rest headed by POP."""
    from core.domain.history_timeline import UndoFocus, linked_pairs, mark, vector_items
    handler, history, layers, applied = env
    original = history.peek_undo()
    handler.handle_undo(layers["mro"], [], False)

    items = vector_items(history.get_undo_stack(), history.get_redo_stack(), lambda layer_id: layer_id.upper())
    assert [(item.label, item.layers, item.applied, item.count) for item in items] == [
        (original.description, ("POP", "FEED"), True, "9"), (original.description, ("MRO",), False, "1")]
    assert {state.layer_id for state in items[0].befores} == {"pop", "feed"} and items[1].befores == ()
    assert items[0].time == items[1].time  # one step
    focus = UndoFocus("vector", undo=(history.peek_undo(),), redo=(history.peek_redo(),))
    assert [mark(item, focus) for item in items] == ["undo", "redo"]

    clip = types.SimpleNamespace(op_id=7)
    assert linked_pairs(history.get_undo_stack(), "pop", [7], [clip]) == []
    assert linked_pairs(history.get_redo_stack(), "mro", [7], [clip]) == [(history.peek_redo(), clip)]


def test_the_steps_left_to_undo_stop_at_an_entry_of_several_layers(env):
    """POP filtered alone before the filter from MRO: Undo from POP, without the layers to filter, takes POP's part
    of MRO's filter, then stops (the rest stays next, without POP); the history says one step left, not two."""
    handler, history, layers, applied = env
    mro_filter = history.peek_undo()
    history.clear()
    history.get_or_create_history("pop").push_state(POP_ALONE, 3)
    history.push(mro_filter)
    from core.domain.history_timeline import KIND_VECTOR, UndoFocus, walkable
    # Its relative import of _entry_in_scope resolves in the package _load() made
    focus = _compiled("ui/controllers/history_controller.py", "HistoryController", "_vector_focus",
                      UndoFocus=UndoFocus, walkable=walkable, KIND_VECTOR=KIND_VECTOR,
                      __package__=f"{_PKG}.ui.controllers")

    def undo_left(layer_id, targets):
        button = MagicMock()
        button.isChecked.return_value = bool(targets)
        dock = types.SimpleNamespace(current_layer=layers[layer_id], PROJECT_LAYERS=dict.fromkeys(layers),
                                     pushButton_checkable_filtering_layers_to_filter=button,
                                     get_layers_to_filter=lambda: list(targets))
        controller = types.SimpleNamespace(
            _dock=dock, _app=lambda: types.SimpleNamespace(history_manager=history, _undo_redo_handler=handler))
        return focus(controller, None).undo_left

    assert undo_left("pop", []) == 1
    assert undo_left("pop", ["mro", "feed"]) == 2
    assert handler.handle_undo(layers["pop"], [], False) and not handler.handle_undo(layers["pop"], [], False)
    assert applied == [("pop", "")]

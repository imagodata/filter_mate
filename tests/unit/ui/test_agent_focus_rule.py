# -*- coding: utf-8 -*-
"""Undo and Redo of the action bar: the steps of the agent, or the filters of the dock.

One rule for what the buttons show and for what a click does (``FilterMateDockWidget.agent_has_focus``). 2026-11-17,
review of EXPLORING in its own panel: the buttons showed the history of the filters and a click undid a step of the
agent, the click having kept the older rule.
"""
import ast
import pathlib
import types
from unittest.mock import MagicMock

_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _dock_functions():
    """``agent_has_focus`` and ``launchTaskEvent`` of the dock, compiled alone with the ``_apart`` they read."""
    tree = ast.parse((_ROOT / "filter_mate_dockwidget.py").read_text(encoding="utf-8"))
    apart = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_apart")
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateDockWidget")
    wanted = [node for node in owner.body if isinstance(node, ast.FunctionDef)
              and node.name in ("agent_has_focus", "launchTaskEvent")]
    namespace = {"logger": MagicMock()}
    module = ast.Module(body=[apart] + wanted, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), "filter_mate_dockwidget.py", "exec"), namespace)
    return namespace["agent_has_focus"], namespace["launchTaskEvent"]


def _dock(open_above="agent", below=None, apart=(), chat=True):
    sections = types.SimpleNamespace(detached=set(apart), is_open=lambda key: key == open_above,
                                     bottom_key=lambda: below)
    return types.SimpleNamespace(_agent_chat=MagicMock() if chat else None, _fm_sections=sections)


def test_agent_open_in_the_dock_takes_undo_and_redo():
    focus, _launch = _dock_functions()
    assert focus(_dock()) is True
    assert focus(_dock(open_above="exploring")) is False
    assert focus(_dock(chat=False)) is False


def test_agent_or_filtering_in_its_own_panel_leaves_them_to_the_filters():
    focus, _launch = _dock_functions()
    assert focus(_dock(apart=["agent"])) is False
    assert focus(_dock(apart=["filtering"])) is False


def test_with_exploring_in_its_own_panel_they_follow_what_is_open_below():
    """AGENT and FILTERING can be open together then: the buttons sit with FILTERING and are its own. With
    FILTERING folded, or another section open below, they walk the steps of the agent as in the dock."""
    focus, _launch = _dock_functions()
    assert focus(_dock(apart=["exploring"], below="filtering")) is False
    assert focus(_dock(apart=["exploring"], below=None)) is True
    assert focus(_dock(apart=["exploring"], below="exporting")) is True
    assert focus(_dock(below="filtering")) is True  # never met in the dock: AGENT open folds FILTERING


def test_a_click_does_what_the_buttons_show():
    focus, launch = _dock_functions()
    for apart, below, to_agent in (((), None, True), (("exploring",), "filtering", False),
                                   (("exploring",), None, True), (("filtering",), None, False)):
        dock = _dock(apart=apart, below=below)
        dock.agent_has_focus = lambda dock=dock: focus(dock)
        dock._controller_integration = MagicMock()  # the filters: the first thing asked of it ends the call
        dock._controller_integration.delegate_point_cloud_task.return_value = True
        launch(dock, None, "undo")
        assert dock._agent_chat._on_undo.called is to_agent, (apart, below)
        assert dock._controller_integration.delegate_point_cloud_task.called is not to_agent, (apart, below)

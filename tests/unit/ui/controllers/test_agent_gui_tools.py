# -*- coding: utf-8 -*-
"""Labels and handlers of the five visible-automation tools of the chat.

Same harness as test_agent_turn_limit_and_names.py: the controller is loaded by path, the window behind the
handlers is a stand-in.
"""
import importlib.util
import pathlib
import sys

import pytest

from .test_agent_chat_lifecycle import (  # noqa: F401 (fixtures)
    _PKG, _ROOT, _engine, _tool_turn, controller, ctrl_module, dock,
)

pytestmark = pytest.mark.unit


def _messages():
    return sys.modules[f"{_PKG}.core.agent.messages"]


def _failures():
    return sys.modules[f"{_PKG}.core.agent.tool_executor"].ToolFailure


def _controls(monkeypatch):
    """The real gui_control under the harness package (its parent and operations there are stand-ins)."""
    from .test_agent_chat_lifecycle import _module as _stub_module
    _stub_module(monkeypatch, ".adapters.public_api.operations")
    name = f"{_PKG}.adapters.public_api.gui_control"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, pathlib.Path(_ROOT) / "adapters" / "public_api" / "gui_control.py")
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
    return sys.modules[name]


def test_labels_say_what_the_user_will_see(controller):  # noqa: F811
    calls = _messages().ToolCallPart
    assert controller._describe(calls("c1", "open_layout", {"name": "Carte"})) == "Layout Carte"
    assert controller._describe(calls("c2", "preview_atlas", {"layout": "Carte"})) == "Atlas of Carte"
    assert controller._describe(calls("c3", "flash_features", {"layer": "communes"})) == "Flashing communes"
    assert controller._describe(calls("c4", "set_active_layer", {"layer": "communes"})) == "Active layer: communes"
    assert controller._describe(calls("c5", "show_message", {"text": "Filtre appliqué."})) == "Message: Filtre appliqué."


def test_handlers_answer_what_the_window_did(controller, monkeypatch):  # noqa: F811
    controls = _controls(monkeypatch)
    monkeypatch.setattr(controls, "open_layout", lambda name: {"name": name, "opened": True})
    monkeypatch.setattr(controls, "flash_features", lambda layer, expression, limit=500: {"flashed": 2})
    monkeypatch.setattr(controls, "set_active_layer", lambda layer, reveal=True: {"active": True})
    monkeypatch.setattr(controls, "show_message", lambda text, level="info", duration=5: {"shown": True})
    monkeypatch.setattr(controls, "preview_atlas", lambda layout, action="next", preview=True: {"page": 2})
    assert controller._open_layout_tool({"name": "Carte"}) == {"name": "Carte", "opened": True}
    assert controller._flash_features_tool({"layer": "c", "expression": '"a" = 1'}) == {"flashed": 2}
    assert controller._set_active_layer_tool({"layer": "c"}) == {"active": True}
    assert controller._show_message_tool({"text": "hi"}) == {"shown": True}
    assert controller._preview_atlas_tool({"layout": "Carte"}) == {"page": 2}


def test_handlers_refuse_as_tool_failures(controller, monkeypatch):  # noqa: F811
    controls = _controls(monkeypatch)

    def refuse(*args, **kwargs):
        raise ValueError("QGIS has no window here")

    monkeypatch.setattr(controls, "open_layout", refuse)
    monkeypatch.setattr(controls, "flash_features", refuse)
    monkeypatch.setattr(controls, "set_active_layer", refuse)
    monkeypatch.setattr(controls, "show_message", refuse)
    monkeypatch.setattr(controls, "preview_atlas", refuse)
    ToolFailure = _failures()
    with pytest.raises(ToolFailure, match="no window"):
        controller._open_layout_tool({"name": "Carte"})
    with pytest.raises(ToolFailure, match="no window"):
        controller._flash_features_tool({"layer": "c", "expression": '"a" = 1'})
    with pytest.raises(ToolFailure, match="no window"):
        controller._set_active_layer_tool({"layer": "c"})
    with pytest.raises(ToolFailure, match="no window"):
        controller._show_message_tool({"text": "hi"})
    with pytest.raises(ToolFailure, match="no window"):
        controller._preview_atlas_tool({"layout": "Carte"})

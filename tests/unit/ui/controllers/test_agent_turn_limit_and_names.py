# -*- coding: utf-8 -*-
"""2026-11-22, a map of the Ile de Re made from one sentence: the request reached its number of steps at its last
one and the thread said so as an error in red, and the cards of the steps named the relief by its layer id."""
import sys
import types

import pytest

from .test_agent_chat_lifecycle import (  # noqa: F401 (fixtures)
    _PKG, FakeQgsProject, _engine, _tool_turn, controller, ctrl_module, dock,
)

pytestmark = pytest.mark.unit


def _messages():
    return sys.modules[f"{_PKG}.core.agent.messages"]


def _limited(controller, turns):  # noqa: F811
    session = controller._engine._session
    session._limits = type(session._limits)(max_model_turns=turns, warn_turns_left=0)


def test_the_limit_of_steps_is_a_pause_with_a_button_to_go_on(ctrl_module, controller):  # noqa: F811
    _engine(ctrl_module, controller, lambda arguments: {})
    _limited(controller, 2)
    controller.panel.input.text.return_value = ""
    controller._on_send("make a map of the island")
    transport_starts = controller._engine._transport.starts
    transport_starts[0](_tool_turn(ctrl_module))
    transport_starts[1](_tool_turn(ctrl_module))
    controller.panel.show_error.assert_not_called()
    assert "paused after many steps" in controller.panel.add_note.call_args[0][0]
    label, go_on = controller.panel.add_link.call_args[0]
    assert label == "Continue"
    sent = []
    controller._on_send = sent.append
    go_on()
    go_on()  # a second click sends nothing more
    assert sent == ["Go on with what is left of the request."]


def test_the_button_does_nothing_while_a_request_runs(ctrl_module, controller):  # noqa: F811
    _engine(ctrl_module, controller, lambda arguments: {})
    controller._offer_to_go_on()
    _label, go_on = controller.panel.add_link.call_args[0]
    sent = []
    controller._on_send = sent.append
    controller.chat_busy = lambda: True
    go_on()
    assert sent == []


def test_a_refusal_is_still_an_error(ctrl_module, controller):  # noqa: F811
    title, _detail = controller._stop_words("refused")
    assert "declined" in title


def test_a_layer_named_by_its_id_is_shown_by_its_name(ctrl_module, controller):  # noqa: F811
    relief = types.SimpleNamespace(name=lambda: "Relief (MNS Copernicus)")
    FakeQgsProject.project.layers = {"Relief__MNS_Copernicus__ada11928": relief}
    call = _messages().ToolCallPart("c1", "set_layer_style", {"layer": "Relief__MNS_Copernicus__ada11928"})
    assert controller._describe(call) == "Style of Relief (MNS Copernicus)"
    assert controller._layer_names(call) == ("Relief (MNS Copernicus)",)


def test_a_layer_named_by_its_name_or_unknown_stays_as_written(ctrl_module, controller):  # noqa: F811
    FakeQgsProject.project.layers = {}
    call = _messages().ToolCallPart("c1", "set_layer_style", {"layer": "Milieux naturels"})
    assert controller._describe(call) == "Style of Milieux naturels"
    many = _messages().ToolCallPart("c2", "set_layer_options", {"layers": [{"layer": "a"}, "b"]})
    assert controller._layer_names(many) == ("a", "b")

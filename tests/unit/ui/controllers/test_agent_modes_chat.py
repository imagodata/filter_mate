# -*- coding: utf-8 -*-
"""The modes under the line of the chat in the controller (2026-11-22): the level a request runs at, what the model is
told, the Go that carries out a plan in Act."""
import sys

import pytest

from .test_agent_chat_lifecycle import (  # noqa: F401 (fixtures)
    _PKG, _end_turn, _engine, controller, ctrl_module, dock,
)

pytestmark = pytest.mark.unit


def _modes():
    return sys.modules[f"{_PKG}.core.agent.modes"]


def _permissions():
    return sys.modules[f"{_PKG}.core.agent.permissions"]


def _send(ctrl_module, controller, text="what is in the project?"):  # noqa: F811
    _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send(text)
    return controller._engine._transport.starts


def test_ask_runs_at_the_advisor_level_and_tells_the_model(ctrl_module, controller, monkeypatch):  # noqa: F811
    saved = []
    monkeypatch.setattr(sys.modules[f"{_PKG}.ui.controllers.agent_chat_controller"], "write_mode", saved.append)
    controller._on_mode_changed("ask")
    assert saved == ["ask"]
    _send(ctrl_module, controller)
    assert controller._policy.level == _permissions().ADVISOR
    assert controller._level_part() == _modes().mode_note("ask")


def test_act_runs_at_the_level_of_the_autonomy_tab(ctrl_module, controller):  # noqa: F811
    controller._mode = "act"
    _send(ctrl_module, controller)
    level = sys.modules[f"{_PKG}.ui.controllers.agent_chat_controller"].load_settings().autonomy
    assert controller._policy.level == _permissions().level_or_default(level)
    assert controller._level_part() == _permissions().level_note(controller._policy.level)


def test_a_plan_ends_with_go_that_carries_it_out_in_act(ctrl_module, controller):  # noqa: F811
    controller._mode = "plan"
    starts = _send(ctrl_module, controller, "make a map of the island")
    starts[0](_end_turn(ctrl_module))
    label, go = controller.panel.add_link.call_args[0]
    assert label == "Go"
    sent = []
    controller._on_send = lambda text, mode="": sent.append((text, mode))
    go()
    go()  # once
    assert sent == [("Go: carry out the plan above, step by step.", "act")]


def test_no_go_after_an_answer_in_ask_or_act(ctrl_module, controller):  # noqa: F811
    for mode in ("ask", "act"):
        controller.panel.add_link.reset_mock()
        controller._mode = mode
        starts = _send(ctrl_module, controller)
        starts[0](_end_turn(ctrl_module))
        controller.panel.add_link.assert_not_called()


def test_the_go_of_a_plan_keeps_the_mode_picked_for_later(ctrl_module, controller):  # noqa: F811
    controller._mode = "plan"
    _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("carry it out", mode="act")
    assert controller._request_mode == "act" and controller._mode == "plan"


def test_answer_reads_and_propose_shows_each_change_first(ctrl_module, controller):  # noqa: F811
    controller._on_posture_changed("respond")
    assert controller._mode == "ask"
    _send(ctrl_module, controller)
    assert controller._policy.level == _permissions().ADVISOR
    controller._on_posture_changed("propose")
    assert controller._mode == "plan"
    _send(ctrl_module, controller)
    assert controller._policy.level == _permissions().CAREFUL


def test_act_keeps_the_level_of_the_autonomy_tab(ctrl_module, controller):  # noqa: F811
    controller._on_posture_changed("act")
    assert controller._mode == "act"
    _send(ctrl_module, controller)
    level = sys.modules[f"{_PKG}.ui.controllers.agent_chat_controller"].load_settings().autonomy
    assert controller._policy.level == _permissions().level_or_default(level)


def test_the_go_of_a_propose_plan_runs_at_the_saved_level(ctrl_module, controller):  # noqa: F811
    controller._on_posture_changed("propose")
    _engine(ctrl_module, controller, lambda arguments: {})
    controller.panel.input.text.return_value = ""
    controller._on_send("carry it out", mode="act")
    level = sys.modules[f"{_PKG}.ui.controllers.agent_chat_controller"].load_settings().autonomy
    assert controller._request_mode == "act"
    assert controller._policy.level == _permissions().level_or_default(level)

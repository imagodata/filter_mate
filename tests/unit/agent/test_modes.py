# -*- coding: utf-8 -*-
"""The modes of the agent under the line of the chat (2026-11-22): Ask and Plan read and change nothing, Act runs at
the level of the Autonomy tab."""
import pytest

from core.agent.modes import ACT, ASK, DEFAULT_MODE, MODES, PLAN, level_for, mode_note, mode_or_default
from core.agent.permissions import ADVISOR, AUTONOMOUS, CAREFUL, STANDARD

pytestmark = pytest.mark.unit


def test_three_modes_and_act_by_default():
    assert MODES == (ASK, PLAN, ACT) and DEFAULT_MODE == ACT


@pytest.mark.parametrize("value, mode", [("ask", ASK), (" Plan ", PLAN), ("ACT", ACT), ("", ACT), (None, ACT),
                                         ("auto", ACT), (3, ACT)])
def test_a_saved_value_is_read_as_a_mode(value, mode):
    assert mode_or_default(value) == mode


@pytest.mark.parametrize("level", [ADVISOR, CAREFUL, STANDARD, AUTONOMOUS])
def test_ask_and_plan_read_only_whatever_the_level_and_act_keeps_it(level):
    assert level_for(ASK, level) == ADVISOR
    assert level_for(PLAN, level) == ADVISOR
    assert level_for(ACT, level) == level


def test_the_notes_say_what_the_model_does_in_each_mode():
    assert "change nothing" in mode_note(ASK) and "Act mode" in mode_note(ASK)
    plan = mode_note(PLAN)
    assert "numbered list" in plan and "Go button" in plan and "change nothing" in plan.lower()
    assert mode_note(ACT) == "" and mode_note("unknown") == ""

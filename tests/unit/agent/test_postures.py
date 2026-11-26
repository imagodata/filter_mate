# -*- coding: utf-8 -*-
"""One posture under the line sets the mode and the level together (core/agent/postures.py)."""
import pytest

from core.agent.modes import ACT, ASK, PLAN
from core.agent.permissions import ADVISOR, AUTONOMOUS, CAREFUL, STANDARD
from core.agent.postures import (
    ACT as POSTURE_ACT,
)
from core.agent.postures import (
    DEFAULT_POSTURE,
    POSTURES,
    PROPOSE,
    RESPOND,
    is_posture,
    posture_from_mode,
    posture_level,
    posture_or_default,
    posture_to_mode,
)

pytestmark = pytest.mark.unit


def test_three_postures_and_act_by_default():
    assert POSTURES == (RESPOND, PROPOSE, POSTURE_ACT) and DEFAULT_POSTURE == POSTURE_ACT


@pytest.mark.parametrize("value, posture", [("respond", RESPOND), (" Propose ", PROPOSE), ("ACT", POSTURE_ACT),
                                            ("", POSTURE_ACT), (None, POSTURE_ACT), ("ask", POSTURE_ACT)])
def test_a_saved_value_is_read_as_a_posture(value, posture):
    assert posture_or_default(value) == posture


def test_legacy_modes_migrate_to_postures():
    assert posture_from_mode(ASK) == RESPOND
    assert posture_from_mode(PLAN) == PROPOSE
    assert posture_from_mode(ACT) == POSTURE_ACT
    assert posture_from_mode("unknown") == POSTURE_ACT


def test_each_posture_runs_the_mode_it_names():
    assert posture_to_mode(RESPOND) == ASK
    assert posture_to_mode(PROPOSE) == PLAN
    assert posture_to_mode(POSTURE_ACT) == ACT


def test_answer_reads_propose_shows_each_change_act_keeps_the_saved_level():
    from core.agent.modes import level_for

    assert posture_level(RESPOND) == ADVISOR
    assert posture_level(PROPOSE) == CAREFUL
    assert posture_level(POSTURE_ACT) is None
    for level in (ADVISOR, CAREFUL, STANDARD, AUTONOMOUS):
        assert level_for(posture_to_mode(POSTURE_ACT), level) == level


def test_only_respond_and_propose_are_unambiguous_postures():
    assert is_posture(RESPOND) and is_posture(PROPOSE)
    assert not is_posture(POSTURE_ACT) and not is_posture(ASK) and not is_posture("unknown")


@pytest.mark.parametrize("name", ["apply_filter", "zoom_to", "save_recipe", "undo_agent_step", "change_settings"])
def test_respond_refuses_changes_even_with_a_saved_allow_rule(name):
    from core.agent.permissions import REFUSE, PermissionPolicy
    from core.agent.tool_catalog import ToolSpec

    policy = PermissionPolicy(ADVISOR, rules={name: "allow"})
    policy.set_posture(RESPOND)
    assert policy.verdict(ToolSpec(name, "A change", {})) == REFUSE


@pytest.mark.parametrize("name", ["apply_filter", "zoom_to", "save_recipe", "undo_agent_step", "change_settings"])
def test_propose_asks_for_each_change_even_after_allowing_it(name):
    from core.agent.permissions import ASK as ASK_PERMISSION, PermissionPolicy
    from core.agent.tool_catalog import ToolSpec

    policy = PermissionPolicy(AUTONOMOUS, rules={name: "allow"})
    policy.set_posture(PROPOSE)
    policy.grant(name)
    tool = ToolSpec(name, "A change", {})
    assert policy.verdict(tool) == ASK_PERMISSION
    assert not policy.grantable(tool)


@pytest.mark.parametrize("posture", [RESPOND, PROPOSE, POSTURE_ACT])
def test_a_memory_proposal_only_shows_a_card_but_a_disabled_tool_stays_disabled(posture):
    from core.agent.permissions import RUN, TURNED_OFF, PermissionPolicy
    from core.agent.tool_catalog import ToolSpec

    tool = ToolSpec("add_project_note", "Keep a note", {})
    policy = PermissionPolicy(ADVISOR)
    policy.set_posture(posture)
    assert policy.verdict(tool, {"scope": "user", "text": "RD means route départementale"}) == RUN
    policy.rules[tool.name] = "never"
    assert policy.verdict(tool, {"scope": "user"}) == TURNED_OFF

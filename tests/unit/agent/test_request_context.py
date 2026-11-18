# -*- coding: utf-8 -*-
"""The context sent with each request of the user (core/agent/request_context.py): composed as the chat did it, then
only what changed (token diet, lot 3)."""
import pytest

from core.agent.request_context import ContextParts, compose, decided_part, protected_part, widgets_part

pytestmark = pytest.mark.unit


def test_compose_keeps_the_order_and_drops_the_empty():
    parts = ContextParts(summary="S", notes="", widgets="W", recipes="R", protected="", decided="D", level="L")
    assert compose(parts) == "S\n\nW\n\nR\n\nD\n\nL"
    assert compose(ContextParts()) == ""


def test_the_parts_read_as_before():
    assert widgets_part([{"id": "w1"}]) == 'Widgets of the panel (data, made with create_widget): [{"id": "w1"}]'
    assert widgets_part([]) == ""
    assert protected_part(["Communes"]) == ("Layers the user protected from the agent (read them, use them as a "
                                            'source, never change them): ["Communes"]')
    assert protected_part([]) == ""
    assert decided_part(["a: yes", "b: no"]) == ("Settings changes you proposed, as the user decided them in the "
                                                 "thread: a: yes; b: no")
    assert decided_part([]) == ""


# --- what changed only (lot 3) --------------------------------------------------------------------------------------

from core.agent.project_summary import UNCHANGED, project_state, project_update  # noqa: E402
from core.agent.request_context import ContextMemory  # noqa: E402

ROWS = [{"layer_id": "c1", "name": "communes", "layer_kind": "vector", "feature_count": 10,
         "active_filter_expression": ""}]


def test_unchanged_project_is_one_line():
    before = project_state(ROWS, [], {})
    assert project_update(ROWS, [], {}, before) == UNCHANGED == "Project unchanged since the last request."


def test_a_changed_layer_is_listed():
    before = project_state(ROWS, [], {})
    now = [dict(ROWS[0], active_filter_expression='"dept" = \'31\'')]
    update = project_update(now, [], {}, before)
    assert update.startswith("Changed in QGIS since your last answer") and "communes" in update


def test_notes_go_once_until_they_change():
    memory = ContextMemory()
    parts = ContextParts(summary="S", notes="N1", widgets="W", level="")
    assert memory.delta(parts, full=False) == parts  # nothing sent yet: everything
    memory.sent()
    assert memory.delta(ContextParts(summary="U", notes="N1", widgets="W"), full=False) == ContextParts(summary="U")
    memory.sent()
    assert memory.delta(ContextParts(summary="U", notes="N2", widgets="W"), full=False).notes == "N2"
    memory.sent()
    gone = memory.delta(ContextParts(summary="U", notes="", widgets="W"), full=False)
    assert gone.notes == "The notes of this project were all removed." and gone.widgets == ""


def test_a_failed_request_sends_its_parts_again():
    memory = ContextMemory()
    memory.delta(ContextParts(summary="S", notes="N"), full=True)
    memory.sent()
    memory.delta(ContextParts(summary="U", notes="N2"), full=False)  # the request fails: not sent()
    assert memory.delta(ContextParts(summary="U", notes="N2"), full=False).notes == "N2"


def test_a_new_conversation_sends_everything():
    memory = ContextMemory()
    memory.delta(ContextParts(summary="S", notes="N"), full=True)
    memory.sent()
    memory.forget()
    assert memory.empty and memory.delta(ContextParts(summary="S", notes="N"), full=False).notes == "N"


def test_back_to_the_standard_level_is_told_once():
    from core.agent.permissions import ADVISOR, STANDARD, level_note
    memory = ContextMemory()
    memory.delta(ContextParts(summary="S", level=level_note(ADVISOR)), full=False)
    memory.sent()
    back = memory.delta(ContextParts(summary="U", level=level_note(STANDARD)), full=False)
    assert back.level.startswith("Level of autonomy chosen by the user: standard again")
    memory.sent()
    assert memory.delta(ContextParts(summary="U", level=level_note(STANDARD)), full=False).level == ""


def test_drop_keeps_what_the_earlier_requests_sent():
    from core.agent.permissions import ADVISOR, STANDARD, level_note
    memory = ContextMemory()
    memory.delta(ContextParts(summary="S", protected="P", level=level_note(ADVISOR)), full=False)
    memory.sent()
    memory.delta(ContextParts(summary="U", level=level_note(STANDARD)), full=False)
    memory.drop()  # the request that carried that delta left the conversation
    assert not memory.empty
    again = memory.delta(ContextParts(summary="U", level=level_note(STANDARD)), full=False)
    assert again.level.startswith("Level of autonomy chosen by the user: standard again")
    assert again.protected == "No layer is protected from the agent any more."
    memory.forget()
    assert memory.empty

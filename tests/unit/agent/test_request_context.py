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

# -*- coding: utf-8 -*-
"""The context sent with each request of the user: the state of the project, the notes, the widgets, the recipes, the
layers protected, the settings decided, the level of autonomy.

Plain Python, out of ui/controllers/agent_chat_controller.py (token diet, lot 3, 2026-11-16) so that the measuring
scripts compose it as the chat does.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, fields
from typing import Any, Sequence


@dataclass
class ContextParts:
    """The parts of the context, in the order they are sent."""

    summary: str = ""
    notes: str = ""
    widgets: str = ""
    recipes: str = ""
    protected: str = ""
    decided: str = ""
    level: str = ""


def compose(parts: ContextParts) -> str:
    """The parts that say something, one paragraph each, in their order."""
    return "\n\n".join(getattr(parts, item.name) for item in fields(parts) if getattr(parts, item.name))


def widgets_part(widgets: Sequence[Any]) -> str:
    return ("Widgets of the panel (data, made with create_widget): " + json.dumps(list(widgets), ensure_ascii=False)
            if widgets else "")


def protected_part(names: Sequence[str]) -> str:
    return ("Layers the user protected from the agent (read them, use them as a source, never change them): "
            + json.dumps(list(names), ensure_ascii=False) if names else "")


def decided_part(outcomes: Sequence[str]) -> str:
    return ("Settings changes you proposed, as the user decided them in the thread: " + "; ".join(outcomes)
            if outcomes else "")

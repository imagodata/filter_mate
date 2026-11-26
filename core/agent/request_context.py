# -*- coding: utf-8 -*-
"""The context sent with each request of the user: the state of the project, the notes, the memory kept from one
project to the next, the widgets, the recipes, the layers protected, the settings decided, the level of autonomy.

Plain Python, out of ui/controllers/agent_chat_controller.py (token diet, lot 3, 2026-11-16) so that the measuring
scripts compose it as the chat does.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, fields, replace
from typing import Any, Optional, Sequence


@dataclass
class ContextParts:
    """The parts of the context, in the order they are sent."""

    summary: str = ""
    notes: str = ""
    memory: str = ""  # core/agent/memory.py: the notes kept from one project to the next, for this project
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
    return ("What you proposed on a card, as the user decided it in the thread: " + "; ".join(outcomes)
            if outcomes else "")


# Said once when a part that was sent is gone, instead of nothing (the model would keep the last one it read).
REMOVED = {"notes": "The notes of this project were all removed.",
           "memory": "The notes kept from one project to the next are no longer sent: do not rely on them.",
           "widgets": "The widgets of the panel were all removed.",
           "recipes": "No recipe is kept in this project any more.",
           "protected": "No layer is protected from the agent any more.",
           "level": ("Level of autonomy chosen by the user: standard again. The tools that change the project run as "
                     "usual, so act when asked instead of only describing the steps; the user confirms what needs it.")}
# Sent again only when they changed; the state of the project (summary) and the settings decided are the caller's.
_REPEATED = ("notes", "memory", "widgets", "recipes", "protected", "level")


class ContextMemory:
    """What the requests of a conversation sent already, so that the next one sends only what changed (lot 3)."""

    def __init__(self) -> None:
        self._sent: Optional[ContextParts] = None
        self._pending: Optional[ContextParts] = None

    @property
    def empty(self) -> bool:
        """Nothing sent yet in this conversation: the next request carries everything."""
        return self._sent is None

    def delta(self, parts: ContextParts, full: bool) -> ContextParts:
        """``parts`` without what the conversation was sent already and did not change; everything when ``full`` or
        nothing was sent yet. Held until ``sent()``: a request that fails sends it again."""
        self._pending = parts
        sent = self._sent
        if full or sent is None:
            return parts
        changes = {}
        for name in _REPEATED:
            now, before = getattr(parts, name), getattr(sent, name)
            changes[name] = "" if now == before else (now or REMOVED.get(name, ""))
        return replace(parts, **changes)

    def sent(self) -> None:
        """The request went to the model: what it carried is known from now on."""
        if self._pending is not None:
            self._sent, self._pending = self._pending, None

    def drop(self) -> None:
        """The request was taken out of the conversation with its context: what it was to send was never said. What
        the earlier requests sent stays known, and the next one tells what changed since (the removals too)."""
        self._pending = None

    def forget(self) -> None:
        """Another conversation with the model: it knows nothing yet."""
        self._sent = self._pending = None

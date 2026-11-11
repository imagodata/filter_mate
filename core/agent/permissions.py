# -*- coding: utf-8 -*-
"""How far the agent of the chat goes alone: risk classes of the tools and levels of autonomy the user chooses.

Plain Python. Each tool falls in one risk class, from what it can break and how it is undone:

- ``READ``: it reads, nothing changes;
- ``VIEW``: the map moves, layers are shown or hidden, features selected;
- ``PROJECT``: filters, styles, layers added, CRS, layouts: undone with the turn;
- ``BUFFER``: data changed in the edit buffer: undone with the turn, gone for good once the user saves;
- ``LOCAL``: what cannot be undone here: files written, layers removed, features deleted once saved;
- ``OUTSIDE``: what brings the outside in or runs code: the network, external connectors, Python.

A level says up to which class a tool runs without asking. Above it the user is asked, except at ``advisor`` where
nothing that changes the project runs at all: the model is told to describe what it would do. The user may also
allow one tool for the rest of a conversation, from the question itself; code is asked again at every run.

``standard`` is what the chat did before the levels existed: it asks for ``LOCAL`` and ``OUTSIDE`` only.
"""
from __future__ import annotations

from typing import Iterable, Optional, Set

READ, VIEW, PROJECT, BUFFER, LOCAL, OUTSIDE = range(6)
RISK_NAMES = ("read", "view", "project", "edit buffer", "irreversible", "outside")

ADVISOR = "advisor"
CAREFUL = "careful"
STANDARD = "standard"
AUTONOMOUS = "autonomous"
LEVELS = (ADVISOR, CAREFUL, STANDARD, AUTONOMOUS)
DEFAULT_LEVEL = STANDARD

RUN = "run"
ASK = "ask"
REFUSE = "refuse"

# The highest class that runs without asking, at each level.
_RUNS_ALONE = {ADVISOR: READ, CAREFUL: VIEW, STANDARD: BUFFER, AUTONOMOUS: LOCAL}

# How the project shows, not what it holds: the map, the layer tree, the selection, the map themes.
VIEW_TOOLS = frozenset({"zoom_to", "select_features", "set_layers_visibility", "group_layers", "map_theme"})
BUFFER_TOOLS = frozenset({"update_features", "add_features", "add_field"})
# Code written by the model: outside at every level, and asked at every run (each one is new code).
CODE_TOOLS = frozenset({"run_pyqgis"})
# What the user asks of the agent about its own work: its history and its notes. They run at every level.
AGENT_OWN = frozenset({"undo_agent_step", "add_project_note", "remove_project_note"})

ADVISOR_REFUSAL = ("Not done: the user set the agent to advise only, so nothing that changes the project runs. "
                   "Tell them, step by step, what you would do and with which tools, so they can do it themselves or "
                   "choose another level in the settings of the agent. Do not try another tool to do it.")

_LEVEL_NOTES = {
    ADVISOR: ("Level of autonomy chosen by the user: advisor. Only the tools that read run; every change is refused. "
              "Answer the question, and for a change describe the steps and the tools you would use."),
    CAREFUL: ("Level of autonomy chosen by the user: careful. Every change of the project, filters included, is shown "
              "to the user before it runs; a declined one is their choice: ask what they want instead."),
    AUTONOMOUS: ("Level of autonomy chosen by the user: autonomous. Exports, removals and deletions run without a "
                 "question; the network, connectors and code are still confirmed. Say what you wrote or removed."),
}


def level_or_default(value: Optional[str]) -> str:
    return value if value in LEVELS else DEFAULT_LEVEL


def risk_of(spec) -> int:
    """The risk class of a tool (a ``ToolSpec``), from its name first, then from what its flags say it does."""
    if spec.name in CODE_TOOLS:
        return OUTSIDE
    if spec.read_only:
        return READ
    if spec.open_world:
        return OUTSIDE
    if spec.destructive:
        return LOCAL
    if spec.name in VIEW_TOOLS:
        return VIEW
    if spec.name in BUFFER_TOOLS:
        return BUFFER
    return PROJECT


def level_note(level: str) -> str:
    """What the model is told of the level, with each request; "" at the usual level."""
    return _LEVEL_NOTES.get(level_or_default(level), "")


class PermissionPolicy:
    """The level of the chat and what the user allowed for the conversation under way."""

    def __init__(self, level: str = DEFAULT_LEVEL, granted: Iterable[str] = ()) -> None:
        self.level = level_or_default(level)
        self._granted: Set[str] = set(granted)

    def verdict(self, spec) -> str:
        """``RUN``, ``ASK`` or ``REFUSE`` for a call of the tool ``spec``."""
        if spec.name in AGENT_OWN:
            return RUN
        risk = risk_of(spec)
        if risk <= _RUNS_ALONE[self.level] and spec.name not in CODE_TOOLS:
            return RUN
        if self.level == ADVISOR:
            return REFUSE
        if spec.name in self._granted and self.grantable(spec):
            return RUN
        return ASK

    @staticmethod
    def grantable(spec) -> bool:
        """Can the user allow this tool for the rest of the conversation? Never code."""
        return spec.name not in CODE_TOOLS

    def grant(self, name: str) -> None:
        self._granted.add(name)

    @property
    def granted(self) -> frozenset:
        return frozenset(self._granted)

    def forget(self) -> None:
        """A new conversation, another project, another level: what was allowed is asked again."""
        self._granted.clear()

    def set_level(self, level: str) -> None:
        level = level_or_default(level)
        if level != self.level:
            self.level = level
            self.forget()

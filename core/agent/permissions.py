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

from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Set

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
# A layer the user protected would change: refused at every level, never turned into a question.
PROTECTED = "protected"
# The user turned this tool off in the Tools tab: refused at every level, never turned into a question.
TURNED_OFF = "off"

# Exceptions of the Tools tab, by tool: they override the level for that tool alone.
RULE_ASK, RULE_ALLOW, RULE_NEVER = "ask", "allow", "never"
RULES = (RULE_ASK, RULE_ALLOW, RULE_NEVER)

# The arguments that name the layers a tool changes (its filter, style, data, name, or the layer itself). A layer only
# read (the source of a cross filter, the table of a join, an input of Processing) or only shown (zoom, selection,
# visibility, place in the tree) is not changed.
CHANGED_LAYERS = {
    "apply_filter": ("layer_name",), "cross_filter": ("target_layers",), "geometry_filter": ("target_layers",),
    "point_cloud_filter": ("layers",), "clear_filters": ("layers",), "set_layer_style": ("layer",),
    "set_labels": ("layer",), "update_features": ("layer",), "delete_features": ("layer",),
    "add_features": ("layer",), "add_field": ("layer",), "join_layers": ("layer",), "rename_layer": ("layer",),
    "remove_layers": ("layers",),
}
# Without any layer named, these act on every layer.
ALL_WHEN_NONE = frozenset({"clear_filters"})

# The highest class that runs without asking, at each level.
_RUNS_ALONE = {ADVISOR: READ, CAREFUL: VIEW, STANDARD: BUFFER, AUTONOMOUS: LOCAL}

# How the project shows, not what it holds: the map, the layer tree, the selection, the map themes.
VIEW_TOOLS = frozenset({"zoom_to", "select_features", "set_layers_visibility", "group_layers", "map_theme",
                        "bookmark"})
BUFFER_TOOLS = frozenset({"update_features", "add_features", "add_field"})
# Code written by the model: outside at every level, and asked at every run (each one is new code).
CODE_TOOLS = frozenset({"run_pyqgis"})
# What the user asks of the agent about its own work: its history, its notes and its recipes. They run at every level.
AGENT_OWN = frozenset({"undo_agent_step", "add_project_note", "remove_project_note", "save_recipe", "remove_recipe"})

PROTECTED_REFUSAL = ("Not done: the user protected {} from the agent in this project. Read them, use them as a source, "
                     "zoom to them, but never change them (filter, style, edit, rename, remove). Tell the user; do not "
                     "try another tool to change them.")

TURNED_OFF_REFUSAL = ("Not done: the user turned the tool {} off for the agent. Tell them; do not try another tool to "
                      "do the same thing.")

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


class Protection(Protocol):
    """The layers the user protected from the agent, in the open project."""

    def name_of(self, reference: str) -> Optional[str]:
        """The name of the layer ``reference`` (an id or a name) when it is protected, else None."""

    def names(self) -> Sequence[str]:
        """The names of every protected layer."""

    def favorite_layers(self, favorite_id: str) -> Sequence[str]:
        """The ids of the layers a favorite would change: they are in the favorite, not in the call."""


def changed_layers(name: str, arguments: Dict[str, Any]) -> Optional[List[str]]:
    """The layer references a call changes; None when it changes every layer (a clear without layers)."""
    if name == "rename_layer" and arguments.get("group"):
        return []  # a group of the tree, not a layer
    references: List[str] = []
    for key in CHANGED_LAYERS.get(name, ()):
        value = arguments.get(key)
        if isinstance(value, str) and value:
            references.append(value)
        elif isinstance(value, list):
            references.extend(item for item in value if isinstance(item, str) and item)
    if not references and name in ALL_WHEN_NONE:
        return None
    return references


def clean_rules(rules: Any) -> Dict[str, str]:
    """The exceptions of the Tools tab as ``{tool: rule}``, what cannot be read left out; never allow code."""
    if not isinstance(rules, dict):
        return {}
    cleaned = {str(name): rule for name, rule in rules.items() if rule in RULES and name not in AGENT_OWN}
    for name in CODE_TOOLS:
        if cleaned.get(name) == RULE_ALLOW:
            del cleaned[name]  # code is read and confirmed at every run, whatever the user ticks
    return cleaned


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

    def __init__(self, level: str = DEFAULT_LEVEL, granted: Iterable[str] = (),
                 protector: Optional[Protection] = None, rules: Optional[Dict[str, str]] = None) -> None:
        self.level = level_or_default(level)
        self._granted: Set[str] = set(granted)
        self.protector = protector
        self.rules = clean_rules(rules or {})

    def turned_off(self, name: str) -> bool:
        return self.rules.get(name) == RULE_NEVER

    def refusal_text(self, name: str, arguments: Dict[str, Any]) -> str:
        """What the model is told of a call that is not run: a protected layer, a tool turned off, the level."""
        return (self.protection_refusal(name, arguments)
                or (TURNED_OFF_REFUSAL.format(repr(name)) if self.turned_off(name) else "")
                or ADVISOR_REFUSAL)

    def protection_refusal(self, name: str, arguments: Dict[str, Any]) -> str:
        """What the model is told when the call would change a protected layer; "" when it would not."""
        if self.protector is None:
            return ""
        arguments = arguments if isinstance(arguments, dict) else {}
        if name == "apply_favorite":
            resolve = getattr(self.protector, "favorite_layers", None)
            references = list(resolve(str(arguments.get("favorite_id", "")))) if resolve is not None else []
        else:
            references = changed_layers(name, arguments)
        if references is None:
            protected = list(self.protector.names())
        else:
            protected = [found for found in (self.protector.name_of(reference) for reference in references) if found]
        if not protected:
            return ""
        return PROTECTED_REFUSAL.format(", ".join(repr(item) for item in dict.fromkeys(protected)))

    def verdict(self, spec) -> str:
        """``RUN``, ``ASK`` or ``REFUSE`` for a call of the tool ``spec``."""
        if spec.name in AGENT_OWN:
            return RUN
        rule = self.rules.get(spec.name)
        if rule == RULE_NEVER:
            return TURNED_OFF
        risk = risk_of(spec)
        if rule == RULE_ASK:  # at every call, what was allowed for the conversation included
            return REFUSE if self.level == ADVISOR and risk > READ else ASK
        if rule == RULE_ALLOW and spec.name not in CODE_TOOLS and not (self.level == ADVISOR and risk > READ):
            return RUN
        if risk <= _RUNS_ALONE[self.level] and spec.name not in CODE_TOOLS:
            return RUN
        if self.level == ADVISOR:
            return REFUSE
        if spec.name in self._granted and self.grantable(spec):
            return RUN
        return ASK

    def grantable(self, spec) -> bool:
        """Can the user allow this tool for the rest of the conversation? Never code, nor a tool always asked."""
        return spec.name not in CODE_TOOLS and self.rules.get(spec.name) != RULE_ASK

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

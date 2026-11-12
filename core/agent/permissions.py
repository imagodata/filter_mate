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
# visibility, place in the tree) is not changed. The source of a cross filter is changed when the call masks it
# (filter_source) or gives it point cloud criteria, which stay in its subset after the run (see changed_layers).
CHANGED_LAYERS = {
    "apply_filter": ("layer_name",), "cross_filter": ("target_layers",), "geometry_filter": ("target_layers",),
    "point_cloud_filter": ("layers",), "clear_filters": ("layers",), "set_layer_style": ("layer",),
    "set_labels": ("layer",), "update_features": ("layer",), "delete_features": ("layer",),
    "add_features": ("layer",), "add_field": ("layer",), "join_layers": ("layer",), "rename_layer": ("layer",),
    "remove_layers": ("layers",),
}
# Without any layer named, these act on every layer.
ALL_WHEN_NONE = frozenset({"clear_filters"})
# QGIS takes a removed layer out of the joins of the layers that join it: those change too. Editing a joined layer
# writes nothing in the layers that join it (an editable join writes from the layer that holds it into the joined one,
# and a cascaded delete goes the same way): they only show its new values, as from a source.
JOINED_CHANGES = frozenset({"remove_layers"})

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
# The settings of FilterMate itself (config.json, a file of this machine, kept beyond the project): always shown to
# the user before and after, at every level, advisor included (2026-11-12, decided with the user); at the autonomous
# level, how the panel looks changes without a question. The settings of the agent are refused by the tool itself.
SETTINGS_TOOLS = frozenset({"change_settings", "apply_settings_profile"})

PROTECTED_REFUSAL = ("Not done: the user protected {} from the agent in this project. Read them, use them as a source, "
                     "zoom to them, but never change them (filter, style, edit, rename, remove). Tell the user; do not "
                     "try another tool to change them.")
# The layers the user protected cannot be read now (a project closing, favorites unavailable): nothing is changed.
PROTECTION_UNREADABLE = ("Not done: the layers the user protected from the agent could not be read now, so no layer is "
                         "changed. Tell the user; try again once the project is open and ready.")

TURNED_OFF_REFUSAL = ("Not done: the user turned the tool {} off for the agent. Tell them; do not try another tool to "
                      "do the same thing.")

ADVISOR_REFUSAL = ("Not done: the user set the agent to advise only, so nothing that changes the project runs. "
                   "Tell them, step by step, what you would do and with which tools, so they can do it themselves or "
                   "choose another level in the settings of the agent. Do not try another tool to do it.")

_LEVEL_NOTES = {
    ADVISOR: ("Level of autonomy chosen by the user: advisor. Only the tools that read run; every change is refused, "
              "except change_settings, which the user reads and confirms. Answer the question, and for a change "
              "describe the steps and the tools you would use."),
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

    def theme_layers(self, name: str) -> Sequence[str]:
        """The ids of the layers applying the map theme ``name`` would restyle (current style, legend items)."""

    def layers_joining(self, references: Sequence[str]) -> Sequence[str]:
        """The ids of the layers that join one of ``references`` (a vector join)."""


def changed_layers(name: str, arguments: Dict[str, Any]) -> Optional[List[str]]:
    """The layer references a call changes; None when it changes every layer (a clear without layers)."""
    if name == "rename_layer" and arguments.get("group"):
        return []  # a group of the tree, not a layer
    references: List[str] = []  # "" too: it resolves to the first layer whose name is empty
    for key in CHANGED_LAYERS.get(name, ()):
        value = arguments.get(key)
        if isinstance(value, str):
            references.append(value)
        elif isinstance(value, list):
            references.extend(item for item in value if isinstance(item, str))
    source = arguments.get("source_layer")
    if name == "cross_filter" and isinstance(source, str) and (
            arguments.get("filter_source") or _keeps_points(arguments.get("point_cloud_criteria"))):
        references.append(source)
    if not references and name in ALL_WHEN_NONE:
        return None
    return references


def changes_layers(name: str, arguments: Any) -> bool:
    """Whether a call may change a layer: one it names, every layer (a clear without layers), those of a favorite or
    of a map theme applied (its current styles and legend items)."""
    arguments = arguments if isinstance(arguments, dict) else {}
    if name == "map_theme":
        return arguments.get("action") == "apply"
    return name == "apply_favorite" or changed_layers(name, arguments) != []


def _keeps_points(criteria: Any) -> bool:
    """Point cloud criteria that keep something in particular: a cross filter makes them the subset of its source."""
    if isinstance(criteria, dict):
        return any(value not in (None, [], {}) and (not isinstance(value, str) or value.strip())
                   for value in criteria.values())
    if isinstance(criteria, str):
        return bool(criteria.strip())
    return bool(criteria)


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
    if spec.name in SETTINGS_TOOLS:
        return LOCAL
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


def _display_only(arguments: Optional[Dict[str, Any]]) -> bool:
    """Whether a change_settings call only changes how the panel looks (APP.DOCKWIDGET)."""
    changes = (arguments or {}).get("changes") if isinstance(arguments, dict) else None
    if not isinstance(changes, list) or not changes:
        return False
    paths = [str(change.get("path", "")).strip().upper() for change in changes if isinstance(change, dict)]
    return len(paths) == len(changes) and all(path.startswith("APP.DOCKWIDGET.") and path not in _NOT_LOOK
                                              for path in paths)


# Under APP.DOCKWIDGET but not how the panel looks: fewer messages may hide a warning the user should read.
_NOT_LOOK = frozenset({"APP.DOCKWIDGET.FEEDBACK_LEVEL"})


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
        """What the model is told when the call would change a protected layer; "" when it would not.

        A call that changes layers is refused when the protected layers cannot be read: never let through unchecked.
        """
        if self.protector is None or not changes_layers(name, arguments):
            return ""  # no protection, or nothing changed: nothing to read
        arguments = arguments if isinstance(arguments, dict) else {}
        try:
            references = self._references(name, arguments)
            if references is None:
                protected = list(self.protector.names())
            else:
                protected = [found for found in (self.protector.name_of(reference) for reference in references)
                             if found is not None]  # a protected layer may have an empty name
        except Exception:  # a project closing, favorites that cannot be read: refused rather than unchecked
            return PROTECTION_UNREADABLE
        if not protected:
            return ""
        return PROTECTED_REFUSAL.format(", ".join(repr(item) for item in dict.fromkeys(protected)))

    def _references(self, name: str, arguments: Dict[str, Any]) -> Optional[List[str]]:
        """The layers the call changes, read in the project where the call does not name them: those of a favorite,
        of a map theme, those that join a layer removed. None: every layer."""
        if name in ("apply_favorite", "map_theme"):
            method, key = ("favorite_layers", "favorite_id") if name == "apply_favorite" else ("theme_layers", "name")
            resolve = getattr(self.protector, method, None)
            return list(resolve(str(arguments.get(key, "")))) if resolve is not None else []
        references = changed_layers(name, arguments)
        joining = getattr(self.protector, "layers_joining", None)
        if references and name in JOINED_CHANGES and joining is not None:
            references = references + list(joining(references))
        return references

    def verdict(self, spec, arguments: Optional[Dict[str, Any]] = None) -> str:
        """``RUN``, ``ASK`` or ``REFUSE`` for a call of the tool ``spec`` with ``arguments``."""
        if spec.name in AGENT_OWN:
            return RUN
        rule = self.rules.get(spec.name)
        if rule == RULE_NEVER:
            return TURNED_OFF
        if spec.name in SETTINGS_TOOLS:
            return self._settings_verdict(spec, rule, arguments)
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

    def _settings_verdict(self, spec, rule: Optional[str], arguments: Optional[Dict[str, Any]]) -> str:
        """A change of the settings of FilterMate: asked at every level (advisor too: the user reads it and says yes),
        run alone at the autonomous level when it only changes how the panel looks, or when the user allowed it
        always (tab Tools) above advisor. Never allowed for the conversation: each change is shown."""
        if rule == RULE_ASK or self.level == ADVISOR:
            return ASK
        if rule == RULE_ALLOW:
            return RUN
        if self.level == AUTONOMOUS and _display_only(arguments):
            return RUN
        return ASK

    def grantable(self, spec) -> bool:
        """Can the user allow this tool for the rest of the conversation? Never code, nor a tool always asked."""
        return spec.name not in CODE_TOOLS and spec.name not in SETTINGS_TOOLS and self.rules.get(spec.name) != RULE_ASK

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

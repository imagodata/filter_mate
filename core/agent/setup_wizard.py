# -*- coding: utf-8 -*-
"""The setup of FilterMate asked in the AGENT thread with no model: a few cards of choices, then the settings.

Plain Python, no QGIS: the panel draws each step (ui/controllers/setup_wizard.py gives the words), the user ticks,
and ``changes`` turns every answer into settings of ``config.default.json``. The card that follows shows each one
before and after; nothing changes until Apply. No model reads or chooses anything here: the answers are the user's
own, which is why the setup may turn the AGENT section off (settings_reference.plan(by_user=True)).

A step is a list of questions; a question has a key, one or several choices, and the choices ticked when it opens:
the settings as they are, so answering without touching anything changes nothing.

One answer is not a setting: where the sections go (all in the FilterMate panel, or in panels of QGIS,
ui/layout/section_panels.py). QGIS keeps the place of its panels itself; ``layout_wanted`` says what to move, and
the panel moves it when the settings are applied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from ..domain import exploring_tools

OPTIONS = "APP.OPTIONS."
FILTERING_ON = OPTIONS + "FILTERING.enabled"
EXPORTING_ON = OPTIONS + "EXPORTING.enabled"
AGENT_ON = OPTIONS + "AGENT.enabled"
RASTER_ON = OPTIONS + "RASTER.enabled"
POINT_CLOUD_ON = OPTIONS + "POINT_CLOUD.enabled"
THEME = "APP.DOCKWIDGET.COLORS.ACTIVE_THEME"
UI_PROFILE = "APP.DOCKWIDGET.UI_PROFILE"
LANGUAGE = "APP.DOCKWIDGET.LANGUAGE"
ACTION_BAR = "APP.DOCKWIDGET.ACTION_BAR_POSITION"
SECTION_HEADERS = "APP.DOCKWIDGET.SECTION_HEADERS"
SECTION_HEIGHT = "APP.DOCKWIDGET.SECTION_HEIGHT"
AUTO_ZOOM = OPTIONS + "EXPLORATION.auto_zoom_on_filter"
PERSIST_HISTORY = OPTIONS + "HISTORY.persist_history"
HINTS = OPTIONS + "AUTO_OPTIMIZATION.show_optimization_hints"
AUTO_STRATEGY = OPTIONS + "AUTO_OPTIMIZATION.auto_strategy_selection"
RASTER_TARGETS = OPTIONS + "CROSS_FILTER.vector_source_raster_targets"
POINT_CLOUD_TARGETS = OPTIONS + "CROSS_FILTER.vector_source_point_cloud_targets"
GPKG_GROUPS = OPTIONS + "GPKG_PRESERVE_GROUPS"
KML_GROUPS = OPTIONS + "KML_PRESERVE_GROUPS"
RASTER_FORMAT = OPTIONS + "CROSS_FILTER.raster_export_format"
POINT_CLOUD_FORMAT = OPTIONS + "CROSS_FILTER.point_cloud_export_format"

# Steps, in the order they come; FILTERING and EXPORTING only when the section is kept.
FEATURES, LOOK, LAYOUT, EXPLORING, FILTERING, EXPORTING = ("features", "look", "layout", "exploring", "filtering",
                                                            "exporting")
STEPS = (FEATURES, LOOK, LAYOUT, EXPLORING, FILTERING, EXPORTING)

# The tools the rail of EXPLORING shows for each kind of layer: one question per kind (vector layers always, rasters
# and point clouds when the data is ticked), a choice per button that can be hidden, the shown ones ticked. The
# setting holds the hidden ones (core/domain/exploring_tools.py).
TOOL_KINDS = exploring_tools.KINDS
TOOL_SETTINGS = dict(exploring_tools.SETTING_PATHS)
TOOLS_DATA = {exploring_tools.RASTER: "rasters", exploring_tools.POINT_CLOUD: "point_clouds"}

# Several choices, each one a setting on or off.
SECTION_SWITCHES = {"filtering": FILTERING_ON, "exporting": EXPORTING_ON, "agent": AGENT_ON}
DATA_SWITCHES = {"rasters": RASTER_ON, "point_clouds": POINT_CLOUD_ON}
AFTER_FILTER_SWITCHES = {"zoom": AUTO_ZOOM, "history": PERSIST_HISTORY, "hints": HINTS, "auto": AUTO_STRATEGY}
TARGET_SWITCHES = {"rasters": RASTER_TARGETS, "point_clouds": POINT_CLOUD_TARGETS}
GROUP_SWITCHES = {"gpkg": GPKG_GROUPS, "kml": KML_GROUPS}
# One choice, the value of a setting (the choices of config.default.json, a few of them).
THEMES = ("auto", "light", "dark", "default")
PROFILES = ("auto", "compact", "normal", "hidpi")
LANGUAGES = ("auto", "en", "fr")
ACTION_BARS = ("bottom", "top", "left", "right", "sections")  # sections: each section shows its own buttons
HEADERS = ("rail", "stacked")  # a rail of chips per stack (the default), or the headers one above the other
HEIGHTS = ("fill", "fit")  # the rows of FILTERING / EXPORTING spread (the default), or one gap apart at the top
# Where the sections are: in the FilterMate panel, in panels of QGIS, or some of them apart (as they are now).
IN_DOCK, IN_PANELS, AS_NOW = "dock", "panels", "as_now"
LAYOUTS = (IN_DOCK, IN_PANELS)
RASTER_FORMATS = ("COG", "GTiff")
POINT_CLOUD_FORMATS = ("LAZ", "LAS", "COPC")

# How big the layers are: what each size sets. "keep" sets nothing; "medium" is the defaults.
SIZES = ("small", "medium", "large", "keep")
DEBOUNCE = OPTIONS + "UI_RESPONSIVENESS.expression_debounce_ms"
PG_TIMEOUT = OPTIONS + "QUERY_TIMEOUTS.postgresql_timeout_seconds"
LOCAL_TIMEOUT = OPTIONS + "QUERY_TIMEOUTS.local_timeout_seconds"
SPATIALITE_TIMEOUT = OPTIONS + "SPATIALITE.query_timeout_seconds"
LARGE_WARNING = OPTIONS + "OPTIMIZATION_THRESHOLDS.large_dataset_warning"
PROGRESSIVE = OPTIONS + "PROGRESSIVE_FILTERING.enabled"
STREAMING = OPTIONS + "STREAMING_EXPORT.enabled"
WFS_TIMEOUT = OPTIONS + "SERVER_FILTER.wfs_timeout_seconds"
REMOTE_TIMEOUT = OPTIONS + "REMOTE_MATERIALIZATION.timeout_seconds"
_MEDIUM = {DEBOUNCE: 450, LOCAL_TIMEOUT: 30.0, SPATIALITE_TIMEOUT: 120, LARGE_WARNING: 50000,
           PROGRESSIVE: True, STREAMING: True}
SIZE_VALUES: Dict[str, Dict[str, Any]] = {
    "small": {**_MEDIUM, DEBOUNCE: 300},
    "medium": dict(_MEDIUM),
    # Large layers: longer waits before a query gives up, no warning at every filter, the typing waited for.
    "large": {**_MEDIUM, DEBOUNCE: 700, LOCAL_TIMEOUT: 120.0, SPATIALITE_TIMEOUT: 300, LARGE_WARNING: 500000},
}
# PostgreSQL and web services (WFS) with large layers: the server is given longer too. Defaults otherwise. Set only
# when that kind of data is ticked.
POSTGRES_VALUES = {"large": {PG_TIMEOUT: 180.0}, "other": {PG_TIMEOUT: 60.0}}
WEB_VALUES = {"large": {WFS_TIMEOUT: 120, REMOTE_TIMEOUT: 180}, "other": {WFS_TIMEOUT: 60, REMOTE_TIMEOUT: 90}}

# Every setting the setup may change: the values it reads first.
PATHS = tuple(sorted({*SECTION_SWITCHES.values(), *DATA_SWITCHES.values(), *AFTER_FILTER_SWITCHES.values(),
                      *TARGET_SWITCHES.values(), *GROUP_SWITCHES.values(), THEME, UI_PROFILE, LANGUAGE, ACTION_BAR,
                      SECTION_HEADERS, SECTION_HEIGHT, *TOOL_SETTINGS.values(),
                      RASTER_FORMAT, POINT_CLOUD_FORMAT, *_MEDIUM, *WEB_VALUES["large"],
                      *POSTGRES_VALUES["large"]}))


@dataclass(frozen=True)
class ProjectFacts:
    """What the open project holds, for what the setup ticks first and says beside a choice; and where the sections
    of the panel are now (``IN_DOCK``, ``IN_PANELS``, ``AS_NOW`` when some are apart), "" when they cannot move."""

    rasters: int = 0
    point_clouds: int = 0
    postgres: int = 0
    web: int = 0
    layout: str = ""


@dataclass(frozen=True)
class Choice:
    key: str
    selected: bool = False


@dataclass(frozen=True)
class Ask:
    """One question of a step: its key, one or several of its choices."""

    key: str
    choices: Tuple[Choice, ...]
    multi: bool = False


@dataclass
class Answers:
    """What was ticked so far: per step, per question, the keys of the choices."""

    by_step: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)

    def record(self, step: str, chosen: Mapping[str, Sequence[str]]) -> None:
        self.by_step[step] = {key: set(keys) for key, keys in chosen.items()}

    def get(self, step: str, question: str) -> Optional[Set[str]]:
        return self.by_step.get(step, {}).get(question)


_FALSE_STRINGS = frozenset({"false", "0", "no", "off", ""})
_TRUE_STRINGS = frozenset({"true", "1", "yes", "on"})
# Read where the plugin reads them: the sections as ``section_enabled`` (ui/layout/dock_chrome.py), AGENT as
# ``agent_enabled`` (ui/controllers/agent_chat_controller.py), the others as ``_get_option_bool``
# (config/config.py). The setup reads the value of a switch exactly so, which is what makes answering without
# touching anything change nothing, whatever a hand-edited config.json holds. tests/unit/agent/test_setup_wizard.py
# compares each with the real reader.
SECTION_READ = frozenset({FILTERING_ON, EXPORTING_ON})
# What an unset switch reads as for the others (RASTER and POINT_CLOUD: off when unset, as their readers say).
_UNSET_OFF = frozenset({RASTER_ON, POINT_CLOUD_ON, GPKG_GROUPS, KML_GROUPS})


def _option_bool(value: Any, default: bool) -> bool:
    """``config.config._get_option_bool`` on a value already taken out of its ``{"value": ...}``."""
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _FALSE_STRINGS:
            return False
        if text in _TRUE_STRINGS:
            return True
        return default
    return default if value is None else bool(value)


ABSENT = object()  # a setting config.json does not hold at all, which is not the same as a null


def read_switch(path: str, value: Any = ABSENT) -> bool:
    """Whether the setting ``path``, holding ``value`` in config.json (``ABSENT`` when it has none), reads as on for
    the plugin."""
    if path in SECTION_READ:  # off on a value that says no, on for anything else
        if value is None or value is ABSENT:
            return True
        if isinstance(value, str):
            return value.strip().lower() not in ("false", "0", "no", "off")
        return value is not False and value != 0
    if path == AGENT_ON:  # on only for True, and when it is not there at all (a null is off)
        return value is ABSENT or value is True
    return _option_bool(None if value is ABSENT else value, path not in _UNSET_OFF)


SWITCHES = frozenset({*SECTION_SWITCHES.values(), *DATA_SWITCHES.values(), *AFTER_FILTER_SWITCHES.values(),
                      *TARGET_SWITCHES.values(), *GROUP_SWITCHES.values()})


def is_on(values: Mapping[str, Any], path: str) -> bool:
    """Whether the switch ``path`` of ``values`` (the settings as config.json holds them) reads as on."""
    return read_switch(path, values.get(path, ABSENT))


def _switches(key: str, switches: Mapping[str, str], values: Mapping[str, Any]) -> Ask:
    return Ask(key, tuple(Choice(name, is_on(values, path)) for name, path in switches.items()), multi=True)


def _one_of(key: str, keys: Sequence[str], current: Any) -> Ask:
    """One choice among ``keys``; the value of now added when it is another one of the setting, ticked."""
    listed = list(keys)
    if current not in listed and isinstance(current, str) and current:
        listed.append(current)
    return Ask(key, tuple(Choice(name, name == current) for name in listed))


def tools_key(kind: str) -> str:
    """The key of the question about the tools shown for ``kind`` (``tools_vector``, ``tools_point_cloud``)."""
    return f"tools_{kind}"


def _tools(kind: str, values: Mapping[str, Any]) -> Ask:
    """The buttons of the rail of ``kind`` that can be hidden, ticked when the setting shows them now."""
    shown = set(exploring_tools.shown_for(kind, values.get(TOOL_SETTINGS[kind])))
    names = [name for name in exploring_tools.tools_of(kind) if name not in exploring_tools.LOCKED]
    return Ask(tools_key(kind), tuple(Choice(name, name in shown) for name in names), multi=True)


def kept_sections(values: Mapping[str, Any], answers: Answers) -> Set[str]:
    """The sections kept: as answered, or as they are before the first step is answered."""
    chosen = answers.get(FEATURES, "sections")
    if chosen is not None:
        return set(chosen)
    return {name for name, path in SECTION_SWITCHES.items() if read_switch(path, values.get(path, ABSENT))}


def kept_data(values: Mapping[str, Any], answers: Answers) -> Set[str]:
    chosen = answers.get(FEATURES, "data")
    if chosen is not None:
        return set(chosen)
    return {name for name, path in DATA_SWITCHES.items() if read_switch(path, values.get(path, ABSENT))}


def step_questions(step: str, values: Mapping[str, Any], facts: ProjectFacts, answers: Answers) -> List[Ask]:
    """The questions of ``step``, their choices ticked as the settings are now."""
    if step == FEATURES:
        data = [Choice("rasters", is_on(values, RASTER_ON)), Choice("point_clouds", is_on(values, POINT_CLOUD_ON)),
                Choice("postgres", facts.postgres > 0), Choice("web", facts.web > 0)]
        return [_switches("sections", SECTION_SWITCHES, values), Ask("data", tuple(data), multi=True),
                Ask("size", tuple(Choice(size, size == "keep") for size in SIZES))]
    if step == LOOK:
        return [_one_of("theme", THEMES, values.get(THEME)), _one_of("profile", PROFILES, values.get(UI_PROFILE)),
                _one_of("language", LANGUAGES, values.get(LANGUAGE))]
    if step == LAYOUT:
        questions = [_one_of("panels", LAYOUTS, facts.layout)] if facts.layout else []
        if isinstance(values.get(SECTION_HEADERS), str):  # a configuration from before the rails has no such setting
            questions.append(_one_of("headers", HEADERS, values.get(SECTION_HEADERS)))
        if isinstance(values.get(SECTION_HEIGHT), str):  # nor one from before the height of the rows
            questions.append(_one_of("height", HEIGHTS, values.get(SECTION_HEIGHT)))
        return questions + [_one_of("action_bar", ACTION_BARS, values.get(ACTION_BAR))]
    if step == EXPLORING:
        data = kept_data(values, answers)  # a kind of data turned off in FEATURES has no rail to ask about
        return [_tools(kind, values) for kind in TOOL_KINDS if kind not in TOOLS_DATA or TOOLS_DATA[kind] in data]
    if step == FILTERING:
        questions = [_switches("after", AFTER_FILTER_SWITCHES, values)]
        data = kept_data(values, answers)
        targets = {name: path for name, path in TARGET_SWITCHES.items() if name in data}
        if targets:
            questions.append(_switches("targets", targets, values))
        return questions
    if step == EXPORTING:
        questions = [_switches("groups", GROUP_SWITCHES, values)]
        data = kept_data(values, answers)
        if "rasters" in data:
            questions.append(_one_of("raster_format", RASTER_FORMATS, values.get(RASTER_FORMAT)))
        if "point_clouds" in data:
            questions.append(_one_of("point_cloud_format", POINT_CLOUD_FORMATS, values.get(POINT_CLOUD_FORMAT)))
        return questions
    raise ValueError(f"no step {step!r}")


def next_step(done: Sequence[str], values: Mapping[str, Any], answers: Answers) -> Optional[str]:
    """The step after those ``done``; None when the setup has asked everything."""
    sections = kept_sections(values, answers)
    for step in STEPS:
        if step in done:
            continue
        if step in (FILTERING, EXPORTING) and step not in sections:
            continue
        return step
    return None


def changes(values: Mapping[str, Any], answers: Answers) -> List[Dict[str, Any]]:
    """The settings the answers ask, as change_settings takes them (``[{path, value}]``): only those that would
    really change. A question not asked (its section turned off, its data not used) changes nothing."""
    wanted: Dict[str, Any] = {}

    def switches(step: str, question: str, mapping: Mapping[str, str]) -> None:
        chosen = answers.get(step, question)
        if chosen is not None:
            for name, path in mapping.items():
                wanted[path] = name in chosen

    def one(step: str, question: str, path: str) -> None:
        chosen = answers.get(step, question)
        if chosen:
            wanted[path] = sorted(chosen)[0]

    switches(FEATURES, "sections", SECTION_SWITCHES)
    switches(FEATURES, "data", DATA_SWITCHES)
    size = sorted(answers.get(FEATURES, "size") or ["keep"])[0]
    if size in SIZE_VALUES:
        wanted.update(SIZE_VALUES[size])
        data = answers.get(FEATURES, "data") or ()
        for kind, values_of in (("postgres", POSTGRES_VALUES), ("web", WEB_VALUES)):
            if kind in data:
                wanted.update(values_of["large" if size == "large" else "other"])
    one(LOOK, "theme", THEME)
    one(LOOK, "profile", UI_PROFILE)
    one(LOOK, "language", LANGUAGE)
    one(LAYOUT, "headers", SECTION_HEADERS)
    one(LAYOUT, "height", SECTION_HEIGHT)
    one(LAYOUT, "action_bar", ACTION_BAR)
    for kind, path in TOOL_SETTINGS.items():
        chosen = answers.get(EXPLORING, tools_key(kind))
        if chosen is not None:  # an empty answer hides every button that can be
            wanted[path] = exploring_tools.setting_from_shown(kind, chosen)
    switches(FILTERING, "after", AFTER_FILTER_SWITCHES)
    data = answers.get(FEATURES, "data")
    switches(FILTERING, "targets", {name: path for name, path in TARGET_SWITCHES.items()
                                    if data is None or name in data})
    switches(EXPORTING, "groups", GROUP_SWITCHES)
    one(EXPORTING, "raster_format", RASTER_FORMAT)
    one(EXPORTING, "point_cloud_format", POINT_CLOUD_FORMAT)
    return [{"path": path, "value": value} for path, value in wanted.items() if not _unchanged(values, path, value)]


_TOOL_KIND_OF = {path: kind for kind, path in TOOL_SETTINGS.items()}


def _unchanged(values: Mapping[str, Any], path: str, value: Any) -> bool:
    """Whether the setting ``path`` already reads as ``value``: a switch as the plugin reads it, the tools of a rail
    by the buttons they hide (``"identify,zoom"`` and ``"zoom, identify"`` hide the same ones, and a name no button
    has hides none), the others by their value."""
    if path in SWITCHES:
        return read_switch(path, values.get(path, ABSENT)) is value
    kind = _TOOL_KIND_OF.get(path)
    if kind is not None:
        now = exploring_tools.format_hidden(kind, exploring_tools.hidden_for(kind, values.get(path)))
        return now == value
    return _same(values.get(path), value)


def layout_wanted(facts: ProjectFacts, answers: Answers) -> Optional[str]:
    """Where the sections go when the answer moves them: ``IN_DOCK`` or ``IN_PANELS``. None when they stay where
    they are: the question was not asked, or the answer is how they are now."""
    chosen = answers.get(LAYOUT, "panels")
    wanted = sorted(chosen)[0] if chosen else None
    return wanted if wanted in LAYOUTS and wanted != facts.layout else None


def _same(now: Any, value: Any) -> bool:
    """60 and 60.0 are the same timeout; true and 1 are not the same switch."""
    if isinstance(now, bool) or isinstance(value, bool):
        return now is value
    return now == value

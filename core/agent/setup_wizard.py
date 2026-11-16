# -*- coding: utf-8 -*-
"""The setup of FilterMate asked in the AGENT thread with no model: a few cards of choices, then the settings.

Plain Python, no QGIS: the panel draws each step (ui/controllers/setup_wizard.py gives the words), the user ticks,
and ``changes`` turns every answer into settings of ``config.default.json``. The card that follows shows each one
before and after; nothing changes until Apply. No model reads or chooses anything here: the answers are the user's
own, which is why the setup may turn the AGENT section off (settings_reference.plan(by_user=True)).

A step is a list of questions; a question has a key, one or several choices, and the choices ticked when it opens:
the settings as they are, so answering without touching anything changes nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

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
FEATURES, LOOK, FILTERING, EXPORTING = "features", "look", "filtering", "exporting"
STEPS = (FEATURES, LOOK, FILTERING, EXPORTING)

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
ACTION_BARS = ("bottom", "top", "left", "right")
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
_MEDIUM = {DEBOUNCE: 450, PG_TIMEOUT: 60.0, LOCAL_TIMEOUT: 30.0, SPATIALITE_TIMEOUT: 120, LARGE_WARNING: 50000,
           PROGRESSIVE: True, STREAMING: True}
SIZE_VALUES: Dict[str, Dict[str, Any]] = {
    "small": {**_MEDIUM, DEBOUNCE: 300},
    "medium": dict(_MEDIUM),
    # Large layers: longer waits before a query gives up, no warning at every filter, the typing waited for.
    "large": {**_MEDIUM, DEBOUNCE: 700, PG_TIMEOUT: 180.0, LOCAL_TIMEOUT: 120.0, SPATIALITE_TIMEOUT: 300,
              LARGE_WARNING: 500000},
}
# Web services (WFS) with large layers: the server is given longer too. Defaults otherwise.
WEB_VALUES = {"large": {WFS_TIMEOUT: 120, REMOTE_TIMEOUT: 180}, "other": {WFS_TIMEOUT: 60, REMOTE_TIMEOUT: 90}}

# Every setting the setup may change: the values it reads first.
PATHS = tuple(sorted({*SECTION_SWITCHES.values(), *DATA_SWITCHES.values(), *AFTER_FILTER_SWITCHES.values(),
                      *TARGET_SWITCHES.values(), *GROUP_SWITCHES.values(), THEME, UI_PROFILE, LANGUAGE, ACTION_BAR,
                      RASTER_FORMAT, POINT_CLOUD_FORMAT, *_MEDIUM, *WEB_VALUES["large"]}))


@dataclass(frozen=True)
class ProjectFacts:
    """What the open project holds, for what the setup ticks first and says beside a choice."""

    rasters: int = 0
    point_clouds: int = 0
    postgres: int = 0
    web: int = 0


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


def _on(values: Mapping[str, Any], path: str) -> bool:
    return values.get(path) is True


def _switches(key: str, switches: Mapping[str, str], values: Mapping[str, Any]) -> Ask:
    return Ask(key, tuple(Choice(name, _on(values, path)) for name, path in switches.items()), multi=True)


def _one_of(key: str, keys: Sequence[str], current: Any) -> Ask:
    """One choice among ``keys``; the value of now added when it is another one of the setting, ticked."""
    listed = list(keys)
    if current not in listed and isinstance(current, str) and current:
        listed.append(current)
    return Ask(key, tuple(Choice(name, name == current) for name in listed))


def kept_sections(values: Mapping[str, Any], answers: Answers) -> Set[str]:
    """The sections kept: as answered, or as they are before the first step is answered."""
    chosen = answers.get(FEATURES, "sections")
    if chosen is not None:
        return set(chosen)
    return {name for name, path in SECTION_SWITCHES.items() if values.get(path) is not False}


def kept_data(values: Mapping[str, Any], answers: Answers) -> Set[str]:
    chosen = answers.get(FEATURES, "data")
    if chosen is not None:
        return set(chosen)
    return {name for name, path in DATA_SWITCHES.items() if values.get(path) is not False}


def step_questions(step: str, values: Mapping[str, Any], facts: ProjectFacts, answers: Answers) -> List[Ask]:
    """The questions of ``step``, their choices ticked as the settings are now."""
    if step == FEATURES:
        data = [Choice("rasters", _on(values, RASTER_ON)), Choice("point_clouds", _on(values, POINT_CLOUD_ON)),
                Choice("postgres", facts.postgres > 0), Choice("web", facts.web > 0)]
        return [_switches("sections", SECTION_SWITCHES, values), Ask("data", tuple(data), multi=True),
                Ask("size", tuple(Choice(size, size == "keep") for size in SIZES))]
    if step == LOOK:
        return [_one_of("theme", THEMES, values.get(THEME)), _one_of("profile", PROFILES, values.get(UI_PROFILE)),
                _one_of("language", LANGUAGES, values.get(LANGUAGE)),
                _one_of("action_bar", ACTION_BARS, values.get(ACTION_BAR))]
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
        if "web" in (answers.get(FEATURES, "data") or ()):
            wanted.update(WEB_VALUES["large" if size == "large" else "other"])
    one(LOOK, "theme", THEME)
    one(LOOK, "profile", UI_PROFILE)
    one(LOOK, "language", LANGUAGE)
    one(LOOK, "action_bar", ACTION_BAR)
    switches(FILTERING, "after", AFTER_FILTER_SWITCHES)
    data = answers.get(FEATURES, "data")
    switches(FILTERING, "targets", {name: path for name, path in TARGET_SWITCHES.items()
                                    if data is None or name in data})
    switches(EXPORTING, "groups", GROUP_SWITCHES)
    one(EXPORTING, "raster_format", RASTER_FORMAT)
    one(EXPORTING, "point_cloud_format", POINT_CLOUD_FORMAT)
    return [{"path": path, "value": value} for path, value in wanted.items() if not _same(values.get(path), value)]


def _same(now: Any, value: Any) -> bool:
    """60 and 60.0 are the same timeout; true and 1 are not the same switch."""
    if isinstance(now, bool) or isinstance(value, bool):
        return now is value
    return now == value

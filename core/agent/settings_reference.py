# -*- coding: utf-8 -*-
"""The settings of FilterMate as the agent reads them: one row per setting of ``config.default.json``.

Plain Python, no QGIS. ``config.default.json`` is the schema: each setting is a ``{"value": ...}`` leaf with a
description, and often choices or bounds. The value comes from the configuration the plugin runs with; a setting
missing there takes its default.

Only the ``APP`` part holds settings of the user: ``CURRENT_PROJECT`` is the state of the open project and the
hidden leaves (``_hidden``) are internal. A few values stay on this machine (``PRIVATE``): a name, local paths.
"""
from __future__ import annotations

import difflib
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "config.default.json"
ROOT = "APP"
# Their value names the user or their disk (a username in a path): the agent learns whether one is set, not what.
PRIVATE = frozenset({"APP.USER_IDENTITY", "APP.OPTIONS.CROSS_FILTER.cache_dir", "APP.OPTIONS.CROSS_FILTER.pdal_path"})
PRIVATE_SET, PRIVATE_EMPTY = "(set, kept on this machine)", "(empty)"
MAX_LISTED = 60
DEFAULT_LISTED = 25
_META_KEYS = frozenset({"value", "description", "choices", "min", "max", "_hidden", "_display_name", "applies_to"})


@dataclass(frozen=True)
class Setting:
    """One setting: where it is, what it holds and what it may hold."""

    path: str
    value: Any
    default: Any
    description: str
    where: str
    section_note: str = ""
    choices: Optional[Tuple[Any, ...]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    applies_to: str = ""

    @property
    def section(self) -> str:
        return self.path.rsplit(".", 1)[0]

    @property
    def private(self) -> bool:
        return self.path in PRIVATE

    @property
    def changed(self) -> bool:
        return self.value != self.default

    def row(self, detailed: bool = False) -> Dict[str, Any]:
        """What a tool answers about it; private values are said set or empty only."""
        row: Dict[str, Any] = {"path": self.path, "value": self._shown(self.value), "description": self.description}
        if self.changed:
            row["default"] = self._shown(self.default)
        if self.choices is not None:
            row["choices"] = list(self.choices)
        if self.minimum is not None:
            row["min"] = self.minimum
        if self.maximum is not None:
            row["max"] = self.maximum
        if detailed:
            row["where"] = self.where
            if self.section_note:
                row["section"] = self.section_note
            if self.applies_to:
                row["applies_to"] = self.applies_to
            row["changed"] = self.changed
        return row

    def _shown(self, value: Any) -> Any:
        if not self.private:
            return value
        return PRIVATE_SET if value not in (None, "") else PRIVATE_EMPTY


def load_default(path: Optional[Path] = None) -> Dict[str, Any]:
    with open(path or DEFAULT_CONFIG_PATH, encoding="utf-8") as stream:
        return json.load(stream)


def _current(config: Any, keys: Sequence[str]) -> Tuple[bool, Any]:
    """(found, value) of a leaf in the configuration in use, wrapped (``{"value": ...}``) or raw."""
    node = config
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return False, None
        node = node[key]
    if isinstance(node, dict):
        return ("value" in node), node.get("value")
    return True, node


def _number(value: Any) -> Optional[float]:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def read_settings(current: Optional[Dict[str, Any]], default: Optional[Dict[str, Any]] = None) -> List[Setting]:
    """Every setting of the user, in the order of ``config.default.json``."""
    schema = default if default is not None else load_default()
    rows: List[Setting] = []

    def walk(node: Dict[str, Any], keys: List[str], titles: List[str], note: str) -> None:
        for key, child in node.items():
            if key.startswith("_") or not isinstance(child, dict) or child.get("_hidden"):
                continue
            path = keys + [key]
            if "value" in child:
                found, value = _current(current or {}, path)
                choices = child.get("choices")
                rows.append(Setting(
                    path=".".join(path), value=value if found else child["value"], default=child["value"],
                    description=str(child.get("description", "")), where=" > ".join(titles + [key]),
                    section_note=note, choices=tuple(choices) if isinstance(choices, list) else None,
                    minimum=_number(child.get("min")), maximum=_number(child.get("max")),
                    applies_to=str(child.get("applies_to", ""))))
            elif not set(child) <= _META_KEYS:
                title = str(child.get("_display_name") or key)
                walk(child, path, titles + [title], str(child.get("description", "")) or note)

    root = schema.get(ROOT, {})
    walk(root, [ROOT], [str(root.get("_display_name") or ROOT)], "")
    return rows


def _folded(text: str) -> str:
    """Lower case, without accents, separators as spaces: 'Thème' finds 'theme', 'query cache' finds QUERY_CACHE."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii").lower()
    return "".join(char if char.isalnum() else " " for char in text)


def _haystack(setting: Setting) -> str:
    return _folded(" ".join((setting.path, setting.where, setting.description, setting.section_note)))


def find(settings: Sequence[Setting], query: str = "", section: str = "") -> List[Setting]:
    """The settings whose path, place or description hold every word of ``query``, under ``section`` when given;
    when no setting holds them all, those holding the most of them."""
    scope = list(settings)
    if section.strip():
        prefix = _section_key(settings, section)
        scope = [item for item in scope if item.path.upper() == prefix or item.path.upper().startswith(prefix + ".")]
    words = _folded(query).split()
    if not words:
        return scope
    scored = []
    for item in scope:
        haystack = _haystack(item)
        hits = sum(1 for word in words if word in haystack)
        if hits:
            scored.append((hits, item))
    if not scored:
        return []
    best = max(hits for hits, _item in scored)
    if best == len(words):
        return [item for hits, item in scored if hits == best]
    return [item for _hits, item in sorted(scored, key=lambda pair: -pair[0])]


def _section_key(settings: Sequence[Setting], section: str) -> str:
    """A section given as a path (APP.OPTIONS.QUERY_CACHE), its last part (QUERY_CACHE) or a title (Interface)."""
    wanted = section.strip().upper()
    sections = {item.section.upper() for item in settings}
    if wanted in sections or any(item.path.upper() == wanted for item in settings):
        return wanted
    for name in sorted(sections, key=len):
        if name.rsplit(".", 1)[-1] == wanted.replace(" ", "_"):
            return name
    for item in settings:
        titles = [part.strip().upper() for part in item.where.split(">")]
        if wanted in titles:
            parts = item.path.upper().split(".")
            return ".".join(parts[:titles.index(wanted) + 1])
    return wanted


def sections(settings: Sequence[Setting]) -> List[Dict[str, Any]]:
    """The sections, in order, with what they hold."""
    listed: Dict[str, Dict[str, Any]] = {}
    for item in settings:
        entry = listed.setdefault(item.section, {"section": item.section, "where": item.where.rsplit(" > ", 1)[0],
                                                 "description": item.section_note, "settings": 0, "changed": 0})
        entry["settings"] += 1
        entry["changed"] += int(item.changed)
    return list(listed.values())


def describe(settings: Sequence[Setting], query: str = "", section: str = "",
             changed_only: bool = False, limit: int = DEFAULT_LISTED) -> Dict[str, Any]:
    """The answer of ``describe_settings``: the sections when nothing is asked, else the settings found."""
    limit = max(1, min(int(limit or DEFAULT_LISTED), MAX_LISTED))
    if not query.strip() and not section.strip() and not changed_only:
        return {"sections": sections(settings), "settings_total": len(settings),
                "hint": "Give a query (words of the setting) or a section to list settings."}
    found = find(settings, query, section)
    if changed_only:
        found = [item for item in found if item.changed]
    answer: Dict[str, Any] = {"settings": [item.row() for item in found[:limit]], "matched": len(found)}
    if len(found) > limit:
        answer["more"] = f"{len(found) - limit} more: narrow the query or give a section."
    if not found:
        answer["hint"] = "Nothing matches: try other words (English names of the settings) or describe_settings alone."
    return answer


def get(settings: Sequence[Setting], path: str) -> Dict[str, Any]:
    """The answer of ``get_setting``; ``LookupError`` with the closest paths when there is none."""
    wanted = path.strip().upper()
    for item in settings:
        if item.path.upper() == wanted:
            return item.row(detailed=True)
    endings = [item for item in settings if item.path.upper().endswith("." + wanted)]
    if len(endings) == 1:
        return endings[0].row(detailed=True)
    paths = [item.path for item in settings]
    close = [item.path for item in endings] or difflib.get_close_matches(path.strip(), paths, n=5, cutoff=0.5)
    hint = f" Did you mean: {', '.join(close)}?" if close else " describe_settings finds a setting by words."
    raise LookupError(f"No setting {path.strip()!r}.{hint}")


# --- Changes the agent may propose (change_settings) ----------------------------------------------------------------

# The settings of the AGENT itself: an agent never widens what it may reach (platforms allowed, the section shown).
# The user changes them in the configuration tree; the agent tells them where.
AGENT_SECTION = "APP.OPTIONS.AGENT"
# How the panel looks: what the autonomous level changes without asking. Every other change is asked first.
DISPLAY_SECTION = "APP.DOCKWIDGET"
# Applied at once by the panel (ConfigModelManager.apply_settings); the others are read at their next use.
LIVE = frozenset({
    "APP.DOCKWIDGET.COLORS.ACTIVE_THEME", "APP.DOCKWIDGET.UI_PROFILE", "APP.DOCKWIDGET.ACTION_BAR_POSITION",
    "APP.DOCKWIDGET.ACTION_BAR_VERTICAL_ALIGNMENT", "APP.OPTIONS.POINT_CLOUD.enabled", "APP.OPTIONS.RASTER.enabled",
    "APP.OPTIONS.CROSS_FILTER.vector_source_raster_targets",
    "APP.OPTIONS.CROSS_FILTER.vector_source_point_cloud_targets",
    "APP.OPTIONS.UI_RESPONSIVENESS.expression_debounce_ms", "APP.DOCKWIDGET.LANGUAGE",
})
# Read once, when the panel is built.
ON_RESTART = frozenset({"APP.DOCKWIDGET.DOCK_POSITION",
                        "APP.DOCKWIDGET.PushButton.ICONS_SIZES.ACTION", "APP.DOCKWIDGET.PushButton.ICONS_SIZES.OTHERS"})
EFFECT_NOW, EFFECT_NEXT_USE, EFFECT_RESTART = "now", "next use", "after restarting QGIS"
MAX_CHANGES = 10
MAX_TEXT = 500


def refusal(setting: Setting) -> str:
    """Why the agent may not change ``setting``; "" when it may."""
    if setting.path == AGENT_SECTION or setting.path.startswith(AGENT_SECTION + "."):
        return (f"{setting.path} is a setting of the agent itself: only the user changes it, in the configuration "
                f"tree ({setting.where}). Tell them where; do not change it another way.")
    if setting.private:
        return f"{setting.path} holds a name or a path of this machine: only the user sets it ({setting.where})."
    return ""


def effect(path: str) -> str:
    return EFFECT_NOW if path in LIVE else EFFECT_RESTART if path in ON_RESTART else EFFECT_NEXT_USE


def checked_value(setting: Setting, value: Any) -> Any:
    """``value`` as ``setting`` takes it; ``ValueError`` saying what it may hold otherwise."""
    if setting.choices is not None:
        for choice in setting.choices:
            if value == choice and type(value) is type(choice):
                return choice
        if isinstance(value, str):  # a choice written in another case
            for choice in setting.choices:
                if isinstance(choice, str) and choice.lower() == value.strip().lower():
                    return choice
        raise ValueError(f"{setting.path} takes one of {json.dumps(list(setting.choices), ensure_ascii=False)}, "
                         f"not {json.dumps(value, ensure_ascii=False)}")
    default = setting.default
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise ValueError(f"{setting.path} takes true or false")
        return value
    if isinstance(default, (int, float)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{setting.path} takes a number")
        if isinstance(default, int) and not float(value).is_integer():
            raise ValueError(f"{setting.path} takes a whole number")
        number = int(value) if isinstance(default, int) else float(value)
        if setting.minimum is not None and number < setting.minimum:
            raise ValueError(f"{setting.path} is {setting.minimum} at least")
        if setting.maximum is not None and number > setting.maximum:
            raise ValueError(f"{setting.path} is {setting.maximum} at most")
        if setting.minimum is None and number < 0:
            raise ValueError(f"{setting.path} is not negative")
        return number
    if isinstance(default, str):
        if not isinstance(value, str) or len(value) > MAX_TEXT or any(ord(char) < 32 for char in value):
            raise ValueError(f"{setting.path} takes one line of text, {MAX_TEXT} characters at most")
        return value
    raise ValueError(f"{setting.path} is not a setting the agent changes")


def plan(settings: Sequence[Setting], changes: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The changes asked, checked: ``[{path, where, before, after, effect}]``, one per setting (the last value
    asked wins; ``before == after`` when it already holds it); ``ValueError`` listing every problem when one is
    wrong (nothing is changed then)."""
    if not changes:
        raise ValueError("no change given")
    if len(changes) > MAX_CHANGES:
        raise ValueError(f"{MAX_CHANGES} changes at most in one call")
    by_path = {item.path.upper(): item for item in settings}
    problems: List[str] = []
    planned: Dict[str, Dict[str, Any]] = {}
    for change in changes:
        path = str(change.get("path", "")).strip()
        setting = by_path.get(path.upper())
        if setting is None:
            try:
                setting = by_path[get(settings, path)["path"].upper()]
            except LookupError as exc:
                problems.append(str(exc))
                continue
        why = refusal(setting)
        if why:
            problems.append(why)
            continue
        try:
            value = checked_value(setting, change.get("value"))
        except ValueError as exc:
            problems.append(str(exc))
            continue
        planned[setting.path] = {"path": setting.path, "where": setting.where, "before": setting.value,
                                 "after": value, "effect": effect(setting.path)}
    if problems:
        raise ValueError("Nothing changed. " + " ".join(problems))
    return list(planned.values())


def display_only(paths: Iterable[str]) -> bool:
    """Whether every path is a setting of how the panel looks (what the autonomous level changes alone)."""
    paths = list(paths)
    return bool(paths) and all(path.startswith(DISPLAY_SECTION + ".") for path in paths)


def leaf_values(config: Dict[str, Any], paths: Iterable[str]) -> Dict[str, Any]:
    """The values of ``paths`` in a configuration (wrapped or raw leaves); a missing one is left out."""
    values = {}
    for path in paths:
        found, value = _current(config, path.split("."))
        if found:
            values[path] = value
    return values


def set_leaf(config: Dict[str, Any], path: str, value: Any) -> None:
    """Write ``value`` at ``path`` of a configuration in place, keeping a wrapped leaf wrapped."""
    keys = path.split(".")
    node = config
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    leaf = node.get(keys[-1])
    if isinstance(leaf, dict) and "value" in leaf:
        leaf["value"] = value
    elif isinstance(leaf, dict) or leaf is None:
        node[keys[-1]] = {**(leaf or {}), "value": value}
    else:
        node[keys[-1]] = value


def _cell(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else (value or "(empty)")
    return text.replace("|", "\\|")


def reference_markdown(settings: Iterable[Setting]) -> str:
    """The reference of every setting, generated from ``config.default.json`` (``scripts/export_config_reference.py``)."""
    lines = ["# FilterMate — settings reference", "",
             "> Generated from `config/config.default.json` by `scripts/export_config_reference.py`: do not edit by "
             "hand. Each setting is edited in the configuration tree of the panel (Settings), or by the AGENT, which "
             "reads them with `describe_settings` and `get_setting`.", ""]
    current = None
    for item in settings:
        if item.section != current:
            current = item.section
            lines += ["", f"## {item.where.rsplit(' > ', 1)[0]}", "", f"`{item.section}`", ""]
            if item.section_note:
                lines += [item.section_note, ""]
            lines += ["| Setting | Default | Allowed | Description |", "|---|---|---|---|"]
        allowed = ""
        if item.choices is not None:
            allowed = ", ".join(_cell(choice) for choice in item.choices)
        elif item.minimum is not None or item.maximum is not None:
            allowed = f"{_cell(item.minimum) if item.minimum is not None else ''}–" \
                      f"{_cell(item.maximum) if item.maximum is not None else ''}"
        default = PRIVATE_EMPTY if item.private and item.default in (None, "") else _cell(item.default)
        lines.append(f"| `{item.path.rsplit('.', 1)[-1]}` | {default} | {allowed} | "
                     f"{item.description.replace('|', '/')} |")
    return "\n".join(lines).replace("\n\n\n", "\n\n") + "\n"

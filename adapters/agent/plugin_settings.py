# -*- coding: utf-8 -*-
"""The settings of FilterMate (config.json) for the tools of the agent: the configuration the plugin runs with.

The rows come from ``core.agent.settings_reference``; the values from ``config.config.ENV_VARS["CONFIG_DATA"]``,
the configuration loaded at startup and kept up to date by the configuration tree. A change goes through the
panel (``ConfigModelManager.apply_settings``, set with ``set_applier``), as an edit of the user in the tree would.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from ...core.agent.settings_reference import (
    Setting, describe, get, leaf_values, load_default, plan, read_settings)
from ...core.agent import settings_profile, skills
from ...core.agent.performance import summary as performance_summary
from ...core.agent.tool_catalog import (
    APPLY_SETTINGS_PROFILE, CHANGE_SETTINGS, DESCRIBE_SETTINGS, DIAGNOSE_PERFORMANCE, EXPORT_SETTINGS_PROFILE, GET_SETTING,
    LOAD_SKILL)
from ...core.agent.tool_executor import ToolFailure

logger = logging.getLogger("FilterMate")
LOG_TAIL_BYTES = 512 * 1024  # the end of the log: the timings of the last filters, not of last month
_DEFAULT: Optional[Dict[str, Any]] = None
# Applies {path: value} in the panel and returns the paths it applied; None while no panel is there.
Applier = Callable[[Dict[str, Any]], List[str]]
_applier: Optional[Applier] = None
# The values the agent applied, by path, since the recorder of the turn last took them (turn_effects): the value
# "after" of an undo is what the agent set, not what the setting holds at the end of the turn (the user may have
# changed it meanwhile, and an undo must then leave it).
_applied: Dict[str, Any] = {}


def take_applied() -> Dict[str, Any]:
    """The values the agent applied since the last call, and forget them."""
    taken = dict(_applied)
    _applied.clear()
    return taken


def set_applier(applier: Optional[Applier]) -> None:
    """The panel that applies a change (its ConfigModelManager.apply_settings)."""
    global _applier
    _applier = applier


def clear_applier(applier: Optional[Applier]) -> None:
    """The panel of ``applier`` goes away: forget it, unless a newer panel set its own meanwhile (a reload)."""
    global _applier
    if _applier == applier:
        _applier = None


def current_config() -> Dict[str, Any]:
    """The configuration in use; empty before the plugin loaded it (every setting then reads as its default)."""
    try:
        from ...config.config import ENV_VARS
    except ImportError:
        return {}
    data = ENV_VARS.get("CONFIG_DATA")
    return data if isinstance(data, dict) else {}


def _default() -> Dict[str, Any]:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = load_default()
    return _DEFAULT


def settings_rows(config: Optional[Dict[str, Any]] = None) -> List[Setting]:
    return read_settings(current_config() if config is None else config, _default())


def current_values(paths) -> Dict[str, Any]:
    """The values of ``paths`` now, defaults included: what an undo of the turn puts back."""
    wanted = set(paths)
    return {row.path: row.value for row in settings_rows() if row.path in wanted}


def apply_values(values: Dict[str, Any]) -> List[str]:
    """Apply ``values`` in the panel; RuntimeError when no panel can."""
    if not values:
        return []
    if _applier is None:
        raise RuntimeError("the FilterMate panel is not open")
    return _applier(dict(values))


def _describe(arguments: Dict[str, Any]) -> Dict[str, Any]:
    return describe(settings_rows(), query=arguments.get("query") or "", section=arguments.get("section") or "",
                    changed_only=bool(arguments.get("changed_only")), limit=arguments.get("limit") or 25)


def _get(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return get(settings_rows(), arguments.get("path") or "")
    except LookupError as exc:
        raise ToolFailure(str(exc)) from None


def planned(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The changes a call asks, checked against the settings now; ``ValueError`` when one is wrong."""
    return plan(settings_rows(), arguments.get("changes") or [])


PROFILES_FOLDER = "profiles"


def _profiles_folder():
    from ...filtermate_api.config import _default_export_root
    from ...filtermate_api.export_root import prepare_export_root, resolve_export_folder
    return resolve_export_folder(prepare_export_root(_default_export_root()), PROFILES_FOLDER)


def _profile_file(arguments: Dict[str, Any]):
    """The file a call of apply_settings_profile names; ``ValueError`` when it names none or a wrong one."""
    from pathlib import Path
    if arguments.get("path"):
        path = Path(str(arguments["path"])).expanduser()
        if path.suffix.lower() != ".json":
            raise ValueError("a profile is a .json file")
        return path
    if arguments.get("name"):
        return _profiles_folder() / settings_profile.file_name(str(arguments["name"]))
    raise ValueError("give the name of a profile or the path of its file")


def planned_profile(arguments: Dict[str, Any]):
    """(rows of plan, left out, name) of the profile a call names; ``ValueError`` when it cannot be read."""
    path = _profile_file(arguments)
    try:
        if path.stat().st_size > settings_profile.MAX_BYTES:
            raise ValueError(f"a profile is {settings_profile.MAX_BYTES // 1024} KB at most")
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValueError(f"no profile {path.name}") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"the profile {path.name} cannot be read ({type(exc).__name__})") from None
    name, values = settings_profile.read(text)
    rows, left_out = settings_profile.changes(settings_rows(), values)
    return rows, left_out, name or path.stem


def planned_any(name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The rows a settings tool would change: change_settings or apply_settings_profile."""
    if name == APPLY_SETTINGS_PROFILE:
        return planned_profile(arguments)[0]
    return planned(arguments)


def _export_profile(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        file = settings_profile.file_name(str(arguments.get("name", "")))
        folder = _profiles_folder()
    except (ValueError, OSError) as exc:
        raise ToolFailure(str(exc)) from None
    profile = settings_profile.build(settings_rows(), str(arguments["name"]))
    try:
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        (folder / file).write_text(settings_profile.dumps(profile), encoding="utf-8")
    except OSError as exc:
        raise ToolFailure(f"The profile could not be written ({type(exc).__name__}).") from None
    return {"path": str(folder / file), "name": profile["name"], "settings": len(profile["settings"])}


def _apply_profile(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        rows, left_out, name = planned_profile(arguments)
    except ValueError as exc:
        raise ToolFailure(str(exc)) from None
    answer = _apply_rows(rows)
    answer["profile"] = name
    if left_out:
        answer["left_out"] = left_out
    return answer


def _change(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        rows = planned(arguments)
    except ValueError as exc:
        raise ToolFailure(str(exc)) from None
    return _apply_rows(rows)


def _apply_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    changes = [row for row in rows if row["before"] != row["after"]]
    unchanged = [row["path"] for row in rows if row["before"] == row["after"]]
    if not changes:
        return {"changed": [], "unchanged": unchanged, "note": "Every setting already had this value."}
    try:
        apply_values({change["path"]: change["after"] for change in changes})
    except RuntimeError as exc:  # apply_settings put the configuration back
        raise ToolFailure(f"Nothing changed: {exc}.") from None
    _applied.update({change["path"]: change["after"] for change in changes})
    now = leaf_values(current_config(), [change["path"] for change in changes])
    answer: Dict[str, Any] = {
        "changed": [{key: change[key] for key in ("path", "before", "after", "effect")} for change in changes
                    if now.get(change["path"]) == change["after"]],
        "unchanged": unchanged}
    failed = [change["path"] for change in changes if now.get(change["path"]) != change["after"]]
    if failed:
        answer["failed"] = failed
    return answer


def _log_lines() -> List[str]:
    """The last lines of the log of FilterMate (infrastructure/logging), [] when there is none."""
    try:
        from ...infrastructure.logging import _LOG_FILE
    except ImportError:
        return []
    if not _LOG_FILE:
        return []
    try:
        with open(_LOG_FILE, "rb") as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - LOG_TAIL_BYTES))
            data = stream.read()
    except OSError:
        return []
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[1:] if size > LOG_TAIL_BYTES else lines  # the first one is cut


def _diagnose(_arguments: Dict[str, Any]) -> Dict[str, Any]:
    return performance_summary(_log_lines())


def _load_skill(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return skills.load(str(arguments.get("name", "")))
    except KeyError:
        raise ToolFailure(f"No skill {arguments.get('name')!r}: {', '.join(skills.NAMES)}.") from None


def settings_handlers() -> Dict[str, Callable[[Dict[str, Any]], Any]]:
    """The handlers of the settings and skill tools, by name."""
    return {DESCRIBE_SETTINGS: _describe, GET_SETTING: _get, CHANGE_SETTINGS: _change,
            DIAGNOSE_PERFORMANCE: _diagnose, LOAD_SKILL: _load_skill,
            EXPORT_SETTINGS_PROFILE: _export_profile, APPLY_SETTINGS_PROFILE: _apply_profile}

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


# Calls the chat showed to the user as a card instead of running them (the controller marks them before they run):
# their handler only says what is proposed. Keyed by the tool and its arguments.
_deferred: List[str] = []


def _key(name: str, arguments: Dict[str, Any]) -> str:
    import json
    return name + json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str)


def defer(name: str, arguments: Dict[str, Any]) -> None:
    """The next call of ``name`` with ``arguments`` proposes instead of changing: the user decides in the thread."""
    _deferred.append(_key(name, arguments))


def _take_deferred(name: str, arguments: Dict[str, Any]) -> bool:
    key = _key(name, arguments)
    if key in _deferred:
        _deferred.remove(key)
        return True
    return False


# The plan the user saw (a card or a dialog), by call: a profile changed on disk between the question and the run
# is refused rather than applied unseen.
_frozen: Dict[str, List[Dict[str, Any]]] = {}


def freeze(name: str, arguments: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
    _frozen[_key(name, arguments)] = [dict(row) for row in rows]


def _check_frozen(name: str, arguments: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
    shown = _frozen.pop(_key(name, arguments), None)
    if shown is not None and [(row["path"], row["after"]) for row in shown] != [(row["path"], row["after"]) for row in rows]:
        raise ToolFailure("Nothing changed: the profile changed since the user saw it. Tell them; call again to show "
                          "it anew.")


PROPOSED_NOTE = ("Shown to the user in the thread, with Apply and Cancel: nothing changed yet. Do not call it again; "
                 "the next request says what they chose.")


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
    """The file of the profile a call names, in profiles/ of the export folder only: a team copies a profile there.
    Never a path the model gives: it could point at another machine (a share) or probe which files exist."""
    return _profiles_folder() / settings_profile.file_name(str(arguments.get("name", "")))


def planned_profile(arguments: Dict[str, Any]):
    """(rows of plan, left out, name) of the profile a call names; ``ValueError`` when it cannot be read."""
    import stat
    from ...filtermate_api.export_root import ExportRootError
    import os
    try:
        path = _profile_file(arguments)
    except (ExportRootError, RuntimeError) as exc:  # the export folder cannot be used (RuntimeError: a loop of links)
        raise ValueError(str(exc)) from None
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):  # a link, a pipe, a device: never read
            raise ValueError(f"no profile {path.name}")
        # Opened without following a link and without waiting, then checked again: one put there since lstat
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        with os.fdopen(os.open(str(path), flags), "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError(f"no profile {path.name}")
            data = stream.read(settings_profile.MAX_BYTES + 1)
        text = data.decode("utf-8-sig")  # Notepad saves UTF-8 with a mark at the start
    except FileNotFoundError:
        raise ValueError(f"no profile {path.name}") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"the profile {path.name} cannot be read ({type(exc).__name__})") from None
    name, values = settings_profile.read(text)
    rows, left_out = settings_profile.changes(settings_rows(), values)
    return rows, left_out, name or path.stem


def _export_profile(arguments: Dict[str, Any]) -> Dict[str, Any]:
    import os
    import stat
    from ...filtermate_api.export_root import ExportRootError
    try:
        file = settings_profile.file_name(str(arguments.get("name", "")))
        folder = _profiles_folder()
    except (ValueError, OSError, ExportRootError, RuntimeError) as exc:
        raise ToolFailure(str(exc)) from None
    target = folder / file
    try:
        info = target.lstat()
    except FileNotFoundError:
        info = None
    except OSError as exc:
        raise ToolFailure(f"The profile could not be written ({type(exc).__name__}).") from None
    if info is not None and stat.S_ISLNK(info.st_mode):
        # 2026-11-13: a link in profiles/ (dangling: not seen by exists()) was followed, and the profile written
        # wherever it pointed. The reading already refuses a link.
        raise ToolFailure(f"{file} is a link, not a profile: the user removes it, or choose another name.")
    if info is not None and not stat.S_ISREG(info.st_mode):  # a pipe would hold QGIS until someone reads it
        raise ToolFailure(f"{file} is not a file: the user removes it, or choose another name.")
    if info is not None and not arguments.get("replace"):
        raise ToolFailure(f"A profile {file} exists already: ask the user, then call again with replace true to "
                          f"replace it, or choose another name.")
    profile = settings_profile.build(settings_rows(), str(arguments["name"]))
    try:
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        # O_NOFOLLOW where the system has it: a link put there between the check and the write is refused too.
        # O_BINARY on Windows: the descriptor in text mode would turn the \r\n of the stream into \r\r\n.
        flags = (os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
                 | getattr(os, "O_BINARY", 0))
        descriptor = os.open(str(target), flags, 0o600)
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)  # a profile written before, readable by others, is the user's alone too
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(settings_profile.dumps(profile))
    except OSError as exc:
        raise ToolFailure(f"The profile could not be written ({type(exc).__name__}).") from None
    return {"file": f"{PROFILES_FOLDER}/{file}", "folder": "the export folder", "name": profile["name"],
            "settings": len(profile["settings"])}


def _row_out(row: Dict[str, Any]) -> Dict[str, Any]:
    return {key: row[key] for key in ("path", "before", "after", "effect")}


def _apply_profile(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        rows, left_out, name = planned_profile(arguments)
    except ValueError as exc:
        raise ToolFailure(str(exc)) from None
    _check_frozen(APPLY_SETTINGS_PROFILE, arguments, rows)
    if _take_deferred(APPLY_SETTINGS_PROFILE, arguments):
        answer: Dict[str, Any] = {"proposed": [_row_out(row) for row in rows if row["before"] != row["after"]],
                                  "note": PROPOSED_NOTE}
    else:
        answer = apply_planned(rows)
    answer["profile"] = name
    if left_out:
        answer["left_out"] = left_out
    return answer


def _change(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        rows = planned(arguments)
    except ValueError as exc:
        raise ToolFailure(str(exc)) from None
    if _take_deferred(CHANGE_SETTINGS, arguments):
        return {"proposed": [_row_out(row) for row in rows if row["before"] != row["after"]], "note": PROPOSED_NOTE}
    return apply_planned(rows)


def apply_planned(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply rows of ``plan`` (checked already): the answer of change_settings; ToolFailure when nothing changed."""
    changes = [row for row in rows if row["before"] != row["after"]]
    unchanged = [row["path"] for row in rows if row["before"] == row["after"]]
    if not changes:
        return {"changed": [], "unchanged": unchanged, "note": "Every setting already had this value."}
    try:
        apply_values({change["path"]: change["after"] for change in changes})
    except RuntimeError as exc:  # apply_settings put the configuration back
        raise ToolFailure(f"Nothing changed: {exc}.") from None
    now = leaf_values(current_config(), [change["path"] for change in changes])
    # What the agent really set, for the undo of the turn (a path the panel did not take is not recorded).
    _applied.update({change["path"]: change["after"] for change in changes if now.get(change["path"]) == change["after"]})
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


# Asks the user whether a skill from elsewhere may guide the agent (the text shown in full); None: never allowed.
SkillApprover = Callable[["skills.Skill"], bool]


def skill_loader(offered: Optional[set], approve: Optional[SkillApprover] = None, audience: str = "chat"):
    """The handler of load_skill for ``audience``: the chat, or ``mcp`` for another application.

    A skill from elsewhere is of the chat only (``skills.set_extra``): another application is never asked about one
    and never receives one. 2026-11-13: the MCP server of the plugin served the handler of the chat, so a client
    listed these skills, opened the question of the chat ("The agent wants to follow...") and got the text.
    """
    def load_skill(arguments: Dict[str, Any]) -> Dict[str, Any]:
        name = str(arguments.get("name", ""))
        skill = skills.all_skills().get(name)
        try:
            # What the skill needs is checked before the user is asked: a yes kept for a skill then refused
            # ("No skill") asked for nothing (2026-11-13).
            if skill is None or audience not in skill.audience \
                    or (offered is not None and not set(skill.requires) <= offered):
                raise KeyError(name)
            if skill.trust != "builtin":
                from .skill_sources import approved, decline, declined, remember
                if not approved(skill):
                    if declined(skill) or approve is None or not approve(skill):
                        if approve is not None:
                            decline(skill)  # not asked again until QGIS restarts or its text changes
                        raise ToolFailure(f"The user did not allow the skill {name!r} (it comes from {skill.trust}, "
                                          f"not from FilterMate). Go on without it; do not ask for it again.")
                    remember(skill)
            # The skill the user was asked about, not one read again by name while the question was open.
            return skills.answer(skill, offered, audience)
        except KeyError:
            raise ToolFailure(f"No skill {name!r}: {', '.join(skills.names(offered, audience))}.") from None
    return load_skill


def settings_handlers(offered: Optional[set] = None,
                      approve: Optional[SkillApprover] = None) -> Dict[str, Callable[[Dict[str, Any]], Any]]:
    """The handlers of the settings and skill tools, by name; ``offered``: the tools offered (load_skill offers only
    the skills whose required tools are among them); ``approve``: asks the user before a skill from elsewhere."""
    return {DESCRIBE_SETTINGS: _describe, GET_SETTING: _get, CHANGE_SETTINGS: _change,
            DIAGNOSE_PERFORMANCE: _diagnose, LOAD_SKILL: skill_loader(offered, approve),
            EXPORT_SETTINGS_PROFILE: _export_profile, APPLY_SETTINGS_PROFILE: _apply_profile}

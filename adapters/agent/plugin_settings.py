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
from ...core.agent import skills
from ...core.agent.performance import summary as performance_summary
from ...core.agent.tool_catalog import CHANGE_SETTINGS, DESCRIBE_SETTINGS, DIAGNOSE_PERFORMANCE, GET_SETTING, LOAD_SKILL
from ...core.agent.tool_executor import ToolFailure

logger = logging.getLogger("FilterMate")
LOG_TAIL_BYTES = 512 * 1024  # the end of the log: the timings of the last filters, not of last month
_DEFAULT: Optional[Dict[str, Any]] = None
# Applies {path: value} in the panel and returns the paths it applied; None while no panel is there.
Applier = Callable[[Dict[str, Any]], List[str]]
_applier: Optional[Applier] = None


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


def _change(arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        rows = planned(arguments)
    except ValueError as exc:
        raise ToolFailure(str(exc)) from None
    changes = [row for row in rows if row["before"] != row["after"]]
    unchanged = [row["path"] for row in rows if row["before"] == row["after"]]
    if not changes:
        return {"changed": [], "unchanged": unchanged, "note": "Every setting already had this value."}
    try:
        apply_values({change["path"]: change["after"] for change in changes})
    except RuntimeError as exc:  # apply_settings put the configuration back
        raise ToolFailure(f"Nothing changed: {exc}.") from None
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
            DIAGNOSE_PERFORMANCE: _diagnose, LOAD_SKILL: _load_skill}

# -*- coding: utf-8 -*-
"""Profiles of settings: the settings of FilterMate a user changed, as a small JSON file to share with a team.

Plain Python. A profile holds only settings that differ from the default and that the agent may change: never the
settings of the agent (APP.OPTIONS.AGENT), a name or a local path (``settings_reference.refusal``), never a key, a
token or an account (they are not in config.json). Applying one goes through ``settings_reference.plan``: each value
is checked against its setting, and what a profile may not set is reported, not applied.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Sequence, Tuple

from .settings_reference import Setting, plan, refusal

FORMAT = "filtermate-settings-profile"
VERSION = 1
MAX_BYTES = 256 * 1024
MAX_SETTINGS = 200
# What one profile may change at once: every row is shown to the user before anything changes.
MAX_CHANGES = 40
MAX_PATH = 200
MAX_LEFT_OUT = 20
_NAME = re.compile(r"[A-Za-z0-9 _.-]{1,60}")
_RESERVED = re.compile(r"(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?", re.I)  # device names on Windows


def file_name(name: str) -> str:
    """The file of a profile named ``name``; ``ValueError`` for a name that is not a plain short name."""
    name = name.strip()
    if not _NAME.fullmatch(name) or name.startswith(".") or _RESERVED.fullmatch(name.replace(" ", "_")):
        raise ValueError("a profile name is 1 to 60 letters, digits, spaces, dots, dashes or underscores")
    return name.replace(" ", "_") + ".json"


def build(settings: Sequence[Setting], name: str) -> Dict[str, Any]:
    """The profile of the settings changed from their default, those the agent may not change left out."""
    chosen = {item.path: item.value for item in settings if item.changed and not refusal(item)}
    return {"format": FORMAT, "version": VERSION, "name": name.strip(), "settings": chosen}


def dumps(profile: Dict[str, Any]) -> str:
    return json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def read(text: str) -> Tuple[str, Dict[str, Any]]:
    """(name, settings) of a profile; ``ValueError`` when the text is not a profile of FilterMate."""
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError(f"a profile is {MAX_BYTES // 1024} KB at most")
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        raise ValueError("not a profile of FilterMate (not JSON)") from None
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("not a profile of FilterMate")
    if type(data.get("version")) is not int or data.get("version") != VERSION:
        raise ValueError(f"a profile of version {data.get('version')!r}: this FilterMate reads version {VERSION}")
    settings = data.get("settings")
    if not isinstance(settings, dict) or len(settings) > MAX_SETTINGS \
            or not all(isinstance(path, str) for path in settings):
        raise ValueError("the settings of the profile cannot be read")
    name = data.get("name") if isinstance(data.get("name"), str) else ""
    return name[:60], settings


def changes(settings: Sequence[Setting], profile_settings: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """The changes a profile asks, checked: (rows of ``plan``, why each setting left out was left out).

    A setting unknown here, one the agent may not change, or a value its setting refuses is left out with its
    reason; the others are applied together."""
    by_path: Dict[str, Dict[str, Any]] = {}  # one row per setting: a key written twice keeps its last value
    left_out: List[str] = []
    for path, value in profile_settings.items():
        if len(path) > MAX_PATH:
            left_out.append("a setting name too long")
            continue
        try:
            for row in plan(settings, [{"path": path, "value": value}]):
                by_path.pop(row["path"], None)
                by_path[row["path"]] = row
        except ValueError as exc:
            left_out.append(str(exc).replace("Nothing changed. ", "", 1)[:MAX_PATH])
    rows = list(by_path.values())
    if sum(1 for row in rows if row["before"] != row["after"]) > MAX_CHANGES:
        raise ValueError(f"a profile changes {MAX_CHANGES} settings at most")
    if len(left_out) > MAX_LEFT_OUT:
        left_out = left_out[:MAX_LEFT_OUT] + [f"and {len(left_out) - MAX_LEFT_OUT} more"]
    return rows, left_out

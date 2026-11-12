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
_NAME = re.compile(r"[A-Za-z0-9 _.-]{1,60}")


def file_name(name: str) -> str:
    """The file of a profile named ``name``; ``ValueError`` for a name that is not a plain short name."""
    name = name.strip()
    if not _NAME.fullmatch(name) or name.startswith("."):
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
    if data.get("version") != VERSION:
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
    rows: List[Dict[str, Any]] = []
    left_out: List[str] = []
    for path, value in profile_settings.items():
        try:
            rows.extend(plan(settings, [{"path": path, "value": value}]))
        except ValueError as exc:
            left_out.append(str(exc).replace("Nothing changed. ", "", 1))
    return rows, left_out

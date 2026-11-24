# -*- coding: utf-8 -*-
"""The favorites of a project as its .qgz carries them (``FilterMate/favorites_backup``), and how they meet the copy
the SQLite of a computer keeps.

Decided 2026-11-24: once a project is saved, its file is the truth for its favorites. A favorite removed or changed on
one computer is removed or changed on every computer that opens the project; the SQLite is a working copy. The usage
of a favorite (how often, when last) belongs to each computer and stays out of the file.

Pure: plain dicts in, plain dicts and text out (the service reads and writes the project).
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

SCOPE = "FilterMate"
KEY = "favorites_backup"  # the name of before: operations.py and the Processing algorithm read it
VERSION = "2.0"
LOCAL_ONLY = ("use_count", "last_used_at")

Favorite = Dict[str, Any]


EMPTY = (None, "", [], {})


def _portable(favorite: Favorite) -> Favorite:
    """What of a favorite the project carries: no usage, no empty value (the SQLite gives None where a favorite made
    in memory has {}: the same favorite must give the same text)."""
    return {key: value for key, value in favorite.items()
            if key not in LOCAL_ONLY and not any(value is empty or value == empty for empty in EMPTY
                                                 if not isinstance(value, bool))}


def project_payload(favorites: List[Favorite]) -> str:
    """The text written in the project: the same favorites always give the same text, so that writing it only when
    it differs leaves an unchanged project clean."""
    rows = [_portable(favorite) for favorite in favorites]
    rows.sort(key=lambda row: (str(row.get("id") or ""), str(row.get("name") or "")))
    return json.dumps({"version": VERSION, "authoritative": True, "favorites": rows}, ensure_ascii=False,
                      sort_keys=True)


def read_payload(text: Optional[str]) -> Tuple[Optional[List[Favorite]], bool]:
    """The favorites a project carries and whether it is the truth for them; ``(None, False)`` when it carries none
    (a project saved before FilterMate kept favorites in it, or an entry that cannot be read)."""
    if not text:
        return None, False
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None, False
    if not isinstance(data, dict) or not isinstance(data.get("favorites"), list):
        return None, False
    rows = [{**row, "expression": row.get("expression") or ""}  # NOT NULL in the SQLite
            for row in data["favorites"] if isinstance(row, dict) and row.get("name")]
    return rows, data.get("authoritative") is True


def file_ids(stored: Optional[List[Favorite]]) -> List[str]:
    """The ids a project file carries: what this computer remembers of it, to tell a favorite removed elsewhere from
    one made here and never saved."""
    return sorted({str(row["id"]) for row in stored or [] if row.get("id")})


def reconcile(local: List[Favorite], stored: Optional[List[Favorite]], authoritative: bool,
              known: Optional[List[str]] = None) -> List[Favorite]:
    """The favorites of the project once opened on this computer.

    - No entry in the project: what this computer has.
    - The entry of a saved project (``authoritative``): what the project has, with this computer's usage; plus the
      favorites of this computer the file never had (``known``: the ids of the file when this computer last read or
      saved it), made here and not saved yet (QGIS closed without saving, a project it cannot write). A favorite the
      file had and no longer has was removed elsewhere: it goes.
    - The backup of before (written at the opening, one session late): both, without copies; a favorite of the same
      id, or else of the same name, is kept once, in its newer version, under the id of this computer.
    """
    if stored is None:
        return [dict(row) for row in local]
    by_id = {row.get("id"): row for row in local if row.get("id")}
    if authoritative:
        result = []
        for row in stored:
            row = dict(row)
            row["id"] = row.get("id") or str(uuid.uuid4())
            mine = by_id.get(row["id"])
            for key in LOCAL_ONLY:
                if mine is not None and key in mine:
                    row[key] = mine[key]
                else:
                    row.pop(key, None)
            result.append(row)
        stored_ids = {row["id"] for row in result}
        remembered = set(known or [])
        result += [dict(row) for row in local if row.get("id") not in stored_ids and row.get("id") not in remembered]
        return result
    result = [dict(row) for row in local]
    for row in stored:
        index = next((position for position, mine in enumerate(result) if row.get("id") and mine.get("id") == row["id"]),
                     None)
        if index is None:
            index = next((position for position, mine in enumerate(result) if mine.get("name") == row.get("name")),
                         None)
        if index is None:
            row = dict(row)
            row["id"] = row.get("id") or str(uuid.uuid4())
            result.append(row)
            continue
        match = result[index]
        if str(row.get("updated_at") or "") > str(match.get("updated_at") or ""):
            kept = {key: match[key] for key in ("id", *LOCAL_ONLY) if key in match}
            result[index] = {**row, **kept}
    return result

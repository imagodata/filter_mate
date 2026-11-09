# -*- coding: utf-8 -*-
"""What the panel showed, kept from one session to the next. Pure: the storage is the caller's."""
from __future__ import annotations

import json
from typing import Any, Dict, List

KINDS = ("user", "action", "text", "note")
MAX_CHARS = 60_000
_MAX_FIELD = 4_000


def entry(kind: str, text: str, ok: bool = True, detail: str = "", count: str = "") -> Dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(kind)
    return {"kind": kind, "text": text[:_MAX_FIELD], "ok": bool(ok), "detail": detail[:_MAX_FIELD], "count": count[:64]}


def trim(entries: List[Dict[str, Any]], max_chars: int = MAX_CHARS) -> List[Dict[str, Any]]:
    """The newest entries that fit, whole; the oldest go first."""
    kept: List[Dict[str, Any]] = []
    size = 0
    for item in reversed(entries):
        size += len(item.get("text", "")) + len(item.get("detail", "")) + 40
        if size > max_chars:
            break
        kept.append(item)
    kept.reverse()
    return kept


def to_json(entries: List[Dict[str, Any]]) -> str:
    return json.dumps(trim(entries), ensure_ascii=False)


def from_json(text: str) -> List[Dict[str, Any]]:
    """Entries of a stored transcript; anything odd is left out, and nothing is ever interpreted."""
    try:
        data = json.loads(text or "[]")
    except ValueError:
        return []
    entries = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict) or item.get("kind") not in KINDS or not isinstance(item.get("text"), str):
            continue
        entries.append(entry(item["kind"], item["text"], bool(item.get("ok", True)),
                             str(item.get("detail") or ""), str(item.get("count") or "")))
    return entries

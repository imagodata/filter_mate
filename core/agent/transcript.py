# -*- coding: utf-8 -*-
"""What the panel showed, kept from one session to the next. Pure: the storage is the caller's."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

KINDS = ("user", "action", "text", "note")
MAX_CHARS = 60_000
_MAX_FIELD = 4_000
_MAX_STRONG = 8  # names shown in bold in a card: the layers it is about


def entry(kind: str, text: str, ok: bool = True, detail: str = "", count: str = "",
          strong: Sequence[str] = ()) -> Dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(kind)
    item = {"kind": kind, "text": text[:_MAX_FIELD], "ok": bool(ok), "detail": detail[:_MAX_FIELD], "count": count[:64]}
    names = [name[:200] for name in strong if isinstance(name, str) and name][:_MAX_STRONG]
    if names:
        item["strong"] = names
    return item


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
        strong = item.get("strong")
        entries.append(entry(item["kind"], item["text"], bool(item.get("ok", True)),
                             str(item.get("detail") or ""), str(item.get("count") or ""),
                             strong if isinstance(strong, list) else ()))
    return entries

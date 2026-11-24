# -*- coding: utf-8 -*-
"""Order of the favorites list of the favorites manager.

Pure helper (no Qt): it sorts favorite objects, project and global ones
together, by name, by last use or by number of uses.
"""

from __future__ import annotations

from typing import Any, Iterable, List

SORT_NAME = "name"
SORT_LAST_USED = "last_used"
SORT_MOST_USED = "most_used"


def _name_key(favorite: Any) -> str:
    return (favorite.name or "").casefold()


def sorted_favorites(favorites: Iterable[Any], sort_key: str = SORT_NAME) -> List[Any]:
    """``favorites`` ordered by ``sort_key``; ties and unknown keys fall back to the name.

    - ``"last_used"``: most recent ``last_used_at`` first, never used last.
    - ``"most_used"``: highest ``use_count`` first.

    The sort is stable: favorites equal on every key keep their input order
    (so a project favorite stays before a global one of the same name).
    """
    ordered = sorted(favorites, key=_name_key)
    if sort_key == SORT_LAST_USED:
        used = [f for f in ordered if getattr(f, "last_used_at", None)]
        used.sort(key=lambda f: str(f.last_used_at), reverse=True)
        never = [f for f in ordered if not getattr(f, "last_used_at", None)]
        return used + never
    if sort_key == SORT_MOST_USED:
        ordered.sort(key=lambda f: int(getattr(f, "use_count", 0) or 0), reverse=True)
    return ordered

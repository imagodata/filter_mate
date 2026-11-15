# -*- coding: utf-8 -*-
"""The cut by extent that replaces an exact filter a web service refused.

2026-11-15, read on a real WFS (IGN Géoplateforme): the exact filter of a target is the list of the keys of its
matching features, which QGIS writes in the address of every request, about 190 bytes a key. A list of 25 keys was
set; one of about 100 keys, far under the 500 FilterMate sends, was refused ("subset rejected by the provider"): a
server stops reading an address at a length of its own, which nothing tells beforehand.

Whoever computes such a filter leaves here the subset that cuts the layer by the extent of the source
(``source_capability.extent_subset``); whoever sets the filter and sees it refused takes it from here and sets it
instead, saying so. The dock computes in a task and sets on the main thread, one after the other: both sides only
share the id of the layer and the text of the filter, which is what this holds.

Pure Python, no QGIS: safe from any thread.
"""
import threading
from collections import OrderedDict
from typing import Optional

_LOCK = threading.Lock()
_PENDING: 'OrderedDict[tuple, str]' = OrderedDict()
# A fallback is taken or forgotten when its filter is set; this bound is for the ones whose task was canceled.
MAX_PENDING = 64


def remember(layer_id: str, subset: str, fallback: str) -> None:
    """Leave ``fallback`` for the day ``subset`` is refused on the layer ``layer_id``.

    Args:
        layer_id: Id of the target layer.
        subset: The exact filter about to be set, as it will be given to the provider.
        fallback: The whole subset to set instead (the previous filter already combined in it).
    """
    if not layer_id or not subset or not fallback or subset == fallback:
        return
    with _LOCK:
        _PENDING.pop((layer_id, subset), None)
        _PENDING[(layer_id, subset)] = fallback
        while len(_PENDING) > MAX_PENDING:
            _PENDING.popitem(last=False)


def take(layer_id: str, subset: str) -> Optional[str]:
    """The fallback left for ``subset`` on that layer, removed from here; None when there is none."""
    with _LOCK:
        return _PENDING.pop((layer_id, subset), None)


def forget(layer_id: str) -> None:
    """Drop what was left for a layer: its filter was set, or the layer is gone."""
    with _LOCK:
        for key in [key for key in _PENDING if key[0] == layer_id]:
            del _PENDING[key]


def pending() -> int:
    """How many fallbacks are held (tests)."""
    with _LOCK:
        return len(_PENDING)

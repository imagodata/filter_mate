# -*- coding: utf-8 -*-
"""
Layer facts - what the worker of a task knows of a layer without reading it.

A layer belongs to the thread it lives in (the main thread for a layer of the
project): QGIS 4.3 reports each accessor called from another thread, and a
layer removed meanwhile is read while it is deleted. A task therefore reads
the provider key, the source, the id and the name of its layers on the main
thread, when it is created (:func:`capture`), and what runs in its worker asks
them here (:func:`provider_key_of`, :func:`source_of`, :func:`id_of`,
:func:`name_of`) instead of the layer.

The layer itself still answers, exactly as before:

- on the main thread (nothing is cached there: a layer repointed is read again);
- for a layer no living task captured (a layer the worker created lives in the
  worker's thread, and is read there);
- for a deleted layer (its accessors raise ``RuntimeError``, which the callers
  already handle).

This is a PURE PYTHON module with NO QGIS dependencies: layers are duck-typed
(``providerType()``, ``source()``, ``id()``, ``name()``) and the host says how
a deleted layer is told (``is_deleted``).
"""
import threading
import weakref
from typing import Any, Callable, Dict, Iterable, List, NamedTuple, Optional, Tuple


class LayerFacts(NamedTuple):
    """What was read of a layer when its task was created."""

    provider_key: Any
    source: Any
    layer_id: Any
    name: Any


class LayerFactsSnapshot:
    """The facts of the layers of one task. The task keeps it, and releases it when it ends."""

    def __init__(self, layers: Iterable[Any], is_deleted: Optional[Callable[[Any], bool]] = None):
        """Read ``layers`` now (call it on the thread they live in).

        Args:
            layers: Layers to read; what is not a layer, or is deleted, is left out.
            is_deleted: Tells a layer deleted since (``sip.isdeleted`` in QGIS); None: never.
        """
        self._is_deleted = is_deleted
        # The layer is kept with its facts: the id() of a living object is never given to another one
        self._entries: Dict[int, Tuple[Any, LayerFacts]] = {}
        for layer in layers:
            try:
                facts = LayerFacts(layer.providerType(), layer.source(), layer.id(), layer.name())
            except (AttributeError, RuntimeError):
                continue
            self._entries[id(layer)] = (layer, facts)

    def __len__(self) -> int:
        return len(self._entries)

    def facts(self, layer: Any) -> Optional[LayerFacts]:
        """The facts read of ``layer``, None when it was not read here or is deleted since."""
        entry = self._entries.get(id(layer))
        if entry is None or entry[0] is not layer:
            return None
        if self._is_deleted is not None:
            try:
                if self._is_deleted(layer):
                    return None
            except (TypeError, RuntimeError):
                return None
        return entry[1]

    def release(self) -> None:
        """Forget the layers (the task ended): they answer themselves again."""
        self._entries = {}
        with _LOCK:
            _SNAPSHOTS[:] = [ref for ref in _SNAPSHOTS if ref() not in (None, self)]


_LOCK = threading.Lock()
# The snapshots of the living tasks, the latest last. Weak: a task that never ran keeps nothing here.
_SNAPSHOTS: List[Any] = []


def capture(layers: Iterable[Any], is_deleted: Optional[Callable[[Any], bool]] = None) -> LayerFactsSnapshot:
    """Read ``layers`` for a task being created, on the thread they live in.

    Returns:
        The snapshot: the task keeps it (the facts are forgotten with it) and
        calls :meth:`LayerFactsSnapshot.release` when it ends.
    """
    snapshot = LayerFactsSnapshot(layers, is_deleted)
    with _LOCK:
        _SNAPSHOTS[:] = [ref for ref in _SNAPSHOTS if ref() is not None]
        _SNAPSHOTS.append(weakref.ref(snapshot))
    return snapshot


def facts_of(layer: Any) -> Optional[LayerFacts]:
    """The facts a living task read of ``layer``; None on the main thread (the layer answers there)."""
    if threading.get_ident() == threading.main_thread().ident:
        return None
    with _LOCK:
        references = list(_SNAPSHOTS)
    for reference in reversed(references):  # the latest reading first
        snapshot = reference()
        facts = snapshot.facts(layer) if snapshot is not None else None
        if facts is not None:
            return facts
    return None


def provider_key_of(layer: Any) -> Any:
    """``layer.providerType()``, from the facts of its task in a worker."""
    facts = facts_of(layer)
    return layer.providerType() if facts is None else facts.provider_key


def source_of(layer: Any) -> Any:
    """``layer.source()``, from the facts of its task in a worker (the source it had when the task was created)."""
    facts = facts_of(layer)
    return layer.source() if facts is None else facts.source


def id_of(layer: Any) -> Any:
    """``layer.id()``, from the facts of its task in a worker."""
    facts = facts_of(layer)
    return layer.id() if facts is None else facts.layer_id


def name_of(layer: Any) -> Any:
    """``layer.name()``, from the facts of its task in a worker (the name it had when the task was created)."""
    facts = facts_of(layer)
    return layer.name() if facts is None else facts.name
